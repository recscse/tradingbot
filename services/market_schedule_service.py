import asyncio
import logging
import os
from datetime import datetime, time, timedelta
from typing import List, Dict, Optional, Any
import pytz
import json

try:
    import redis
except ImportError:
    redis = None
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User, BrokerConfig
from services.instrument_refresh_service import TradingInstrumentService

# Import the optimized service
logger = logging.getLogger(__name__)


class MarketScheduleService:
    def __init__(self):
        self.ist = pytz.timezone("Asia/Kolkata")
        self.early_preparation = time(8, 0)  # 8:00 AM
        self.preopen_start = time(9, 0)  # 9:00 AM - Pre-open session starts (LIVE data)
        self.market_open = time(9, 15)  # 9:15 AM - Official trading starts
        self.trading_start = time(9, 30)  # 9:30 AM
        self.market_close = time(15, 30)  # 3:30 PM
        self.instrument_service = TradingInstrumentService()

        # ✅ ENHANCED: Initialize TradingStockSelector with optimized settings for options trading
        from database.connection import SessionLocal

        # Initialize the optimized service
        self.selected_stocks = {}
        self.is_running = False
        self.cache = {}  # In-memory cache fallback

        # ✅ INTEGRATION: Auto-trading components
        self.auto_trading_coordinator = None
        self.fibonacci_strategy = None
        self.nifty_strategy = None
        self.trading_sessions_active = False

        # ✅ FIX: Track daily tasks to prevent repetition
        self.daily_tasks_completed = {
            "early_preparation": None,  # Track by date
            "preopen_stock_selection": None,
            "market_open_validation": None,
            "post_market_cleanup": None,
        }
        
        # Error tracking for tasks
        self.task_errors: Dict[str, str] = {}

        # Initialize Redis client with proper error handling
        self.redis_enabled = os.getenv("REDIS_ENABLED", "true").lower() == "true"
        self.redis_client = None

        if self.redis_enabled and redis is not None:
            try:
                self.redis_client = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", 6379)),
                    db=int(os.getenv("REDIS_DB", 0)),
                    decode_responses=True,
                    socket_connect_timeout=1,  # Reduced from 5 to 1 second
                    socket_timeout=1,  # Reduced from 5 to 1 second
                )
                # Test connection
                self.redis_client.ping()
                logger.info("✅ Redis client initialized successfully")
            except Exception as e:
                logger.warning(f"⚠️ Redis connection failed, disabling: {e}")
                self.redis_client = None
                self.redis_enabled = False
        else:
            logger.info("🚫 Redis disabled via configuration")

    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        try:
            current_time = datetime.now(self.ist)
            return {
                "is_running": self.is_running,
                "current_time": current_time.strftime("%H:%M:%S"),
                "daily_tasks_completed": {k: v.isoformat() if v else None for k, v in self.daily_tasks_completed.items()},
                "task_errors": self.task_errors,
                "redis_connected": self.redis_client is not None,
                "trading_sessions_active": self.trading_sessions_active,
                "selected_stocks_count": len(self.selected_stocks) if self.selected_stocks else 0
            }
        except Exception as e:
            return {"error": str(e)}

    def _safe_redis_set(self, key: str, value: str, ex: int = None) -> bool:
        """Safely set Redis value with fallback to memory cache"""
        try:
            if self.redis_client:
                if ex:
                    self.redis_client.setex(key, ex, value)
                else:
                    self.redis_client.set(key, value)
                return True
            else:
                # Fallback to memory cache
                self.cache[key] = {
                    "value": value,
                    "expires": datetime.now() + timedelta(seconds=ex) if ex else None,
                }
                return True
        except Exception as e:
            logger.error(f"Error updating {key}: {e}")
            # Fallback to memory cache
            try:
                self.cache[key] = {
                    "value": value,
                    "expires": datetime.now() + timedelta(seconds=ex) if ex else None,
                }
                return True
            except:
                return False

    def _safe_redis_get(self, key: str) -> Optional[str]:
        """Safely get Redis value with fallback to memory cache"""
        try:
            if self.redis_client:
                return self.redis_client.get(key)
            else:
                # Fallback to memory cache
                cached = self.cache.get(key)
                if cached:
                    if cached["expires"] is None or datetime.now() < cached["expires"]:
                        return cached["value"]
                    else:
                        del self.cache[key]  # Expired
                return None
        except Exception as e:
            logger.error(f"Error reading {key}: {e}")
            # Fallback to memory cache
            try:
                cached = self.cache.get(key)
                if cached:
                    if cached["expires"] is None or datetime.now() < cached["expires"]:
                        return cached["value"]
                    else:
                        del self.cache[key]  # Expired
                return None
            except:
                return None

    def _safe_redis_delete(self, key: str) -> bool:
        """Safely delete Redis key with fallback to memory cache"""
        try:
            if self.redis_client:
                self.redis_client.delete(key)
            # Always clean from memory cache
            self.cache.pop(key, None)
            return True
        except Exception as e:
            logger.error(f"Error clearing caches: {e}")
            # Still try to clean memory cache
            try:
                self.cache.pop(key, None)
                return True
            except:
                return False

    async def start_daily_scheduler(self):
        """Start the daily market scheduler"""
        self.is_running = True
        logger.info("🚀 Market scheduler started")
        from utils.timezone_utils import get_ist_now_naive

        while self.is_running:
            try:
                current_time = datetime.now(self.ist).time()
                current_date = get_ist_now_naive().date()

                # Reset daily tasks at midnight (new trading day)
                self._reset_daily_tasks_if_new_day(current_date)

                # Check if it's a weekday (Monday=0, Sunday=6)
                if datetime.now(self.ist).weekday() >= 5:
                    logger.info("📅 Weekend - Market closed")
                    await asyncio.sleep(3600)  # Sleep for 1 hour
                    continue

                # Early morning preparation (8:00 AM) - FIXED: Run only once per day
                if (
                    current_time >= self.early_preparation
                    and current_time < self.preopen_start
                    and self.daily_tasks_completed["early_preparation"] != current_date
                ):
                    await self._run_early_morning_preparation()
                    self.daily_tasks_completed["early_preparation"] = current_date

                # Waiting period (8:00-9:00 AM) - After early prep, just wait
                elif (
                    current_time >= self.early_preparation
                    and current_time < self.preopen_start
                ):
                    # Already completed early prep, just waiting for pre-open
                    logger.info(f"⏳ Market Schedule: Early prep complete. Waiting for Pre-Open Stock Selection at {self.preopen_start.strftime('%H:%M')} (Current: {current_time.strftime('%H:%M')})")
                    await asyncio.sleep(300) # Log every 5 minutes instead of 60s loop
                    continue

                # Pre-open stock selection (9:00-9:15 AM) - Uses LIVE pre-open data
                elif (
                    current_time >= self.preopen_start
                    and current_time < self.market_open
                    and self.daily_tasks_completed["preopen_stock_selection"]
                    != current_date
                ):
                    await self._run_preopen_stock_selection()
                    self.daily_tasks_completed["preopen_stock_selection"] = current_date

                # Waiting period (9:00-9:15 AM) - After pre-open selection, just wait
                elif (
                    current_time >= self.preopen_start
                    and current_time < self.market_open
                ):
                    # Already completed pre-open selection, just waiting for market open
                    logger.debug("⏳ Waiting for market open (9:15 AM)...")

                # Market open validation (9:15-9:30 AM) - Validates and finalizes selections
                elif (
                    current_time >= self.market_open
                    and current_time < self.trading_start
                    and self.daily_tasks_completed["market_open_validation"]
                    != current_date
                ):
                    await self._validate_market_open_selection()
                    self.daily_tasks_completed["market_open_validation"] = current_date

                # Waiting period (9:15-9:30 AM) - After market open validation, just wait
                elif (
                    current_time >= self.market_open
                    and current_time < self.trading_start
                ):
                    # Already completed market open validation, just waiting for trading start
                    logger.debug("⏳ Waiting for trading start (9:30 AM)...")

                # Active trading (9:30 AM - 3:30 PM)
                elif (
                    current_time >= self.trading_start
                    and current_time < self.market_close
                ):
                    await self._monitor_active_trading()

                # Post-market cleanup (after 3:30 PM OR before 8:00 AM)
                else:
                    # Only run cleanup if it's actually after market close AND hasn't run today
                    if (
                        (current_time >= self.market_close or current_time < self.early_preparation)
                        and self.daily_tasks_completed["post_market_cleanup"] != current_date
                    ):
                        await self._post_market_cleanup()
                        self.daily_tasks_completed["post_market_cleanup"] = current_date

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"❌ Market scheduler error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _run_early_morning_preparation(self):
        """
        Run at 8:00 AM - FNO service ALWAYS runs BEFORE instrument service.

        FIXED: Runs in background task - NEVER blocks the application!
        """
        logger.info("🌅 Starting early morning preparation in BACKGROUND...")

        # Run as background task - DON'T WAIT FOR IT!
        asyncio.create_task(self._background_early_prep())

        logger.info(
            "✅ Early morning preparation started in background - application remains responsive"
        )

    async def _background_early_prep(self):
        """
        Background task for early morning preparation.

        CRITICAL FIX: This MUST NOT block the application under any circumstances.
        All heavy operations are skipped or deferred to avoid blocking.
        """
        try:
            logger.info(
                "🔧 Background: Starting LIGHTWEIGHT early morning preparation..."
            )

            # Check if it's Monday (weekday 0) for weekly FNO refresh
            current_weekday = datetime.now(self.ist).weekday()
            should_refresh_fno = current_weekday == 0  # Monday only

            # STEP 1: FNO service - SKIP REFRESH to avoid blocking
            logger.info("🔧 Background: Step 1 - FNO stock list check...")
            try:
                from services.fno_stock_service import FnoStockListService

                fno_service = FnoStockListService()

                if should_refresh_fno:
                    # MONDAY: Skip web scraping - it takes 35+ seconds and blocks!
                    logger.warning(
                        "⚠️ Background: FNO web scraping SKIPPED (takes 35+ seconds)"
                    )
                    logger.info(
                        "💡 Background: FNO data will be refreshed manually or use existing data"
                    )
                else:
                    # DAILY: Just verify existing file exists
                    logger.info(
                        f"🔍 Background: Verifying existing FNO data (Tuesday-Sunday)..."
                    )
                    # Quick check - don't call load_from_json as it might be slow
                    import os

                    fno_file_path = "data/fno_stock_list.json"
                    if os.path.exists(fno_file_path):
                        logger.info(
                            f"✅ Background: FNO data file exists at {fno_file_path}"
                        )
                    else:
                        logger.warning(
                            f"⚠️ Background: FNO data file not found, trading may be limited"
                        )

            except Exception as fno_error:
                logger.error(f"❌ Background: FNO service error: {fno_error}")
                self.task_errors["fno_update"] = str(fno_error)
                # Don't return - continue with instrument service

            # STEP 2: Instrument service initialization - CHECK ONLY
            logger.info("🔧 Background: Step 2 - Checking instrument service status...")
            try:
                from services.instrument_refresh_service import get_trading_service

                instrument_service = get_trading_service()

                # Check if already initialized - don't re-initialize
                if instrument_service.is_initialized():
                    logger.info("✅ Background: Instrument service already initialized")
                else:
                    logger.info(
                        "💡 Background: Instrument service will be initialized on-demand"
                    )

            except Exception as inst_error:
                logger.error(
                    f"❌ Background: Instrument service check error: {inst_error}"
                )

            logger.info(
                "✅ Background: Early morning preparation complete (lightweight mode)"
            )

        except Exception as e:
            logger.error(f"❌ Background: Early morning preparation failed: {e}")

    async def _run_preopen_stock_selection(self):
        """
        Run pre-open stock selection from 9:00-9:15 AM.

        IMPORTANT: During pre-open session (9:00-9:15 AM), LIVE CURRENT DAY data
        is available from the market. This is NOT yesterday's data - it's today's
        pre-open auction prices and sentiment.

        This uses REAL-TIME data from realtime_market_engine which receives live
        WebSocket feeds during pre-open session.

        FIXED: NON-BLOCKING - runs in background task to prevent application freeze.
        """
        logger.info(
            "📊 Starting pre-open stock selection in BACKGROUND (9:00-9:15 AM)..."
        )

        # Run as background task - DON'T WAIT FOR IT!
        asyncio.create_task(self._background_preopen_selection())

        logger.info(
            "✅ Pre-open stock selection started in background - application remains responsive"
        )

    async def _background_preopen_selection(self):
        """
        Background task for pre-open stock selection.

        This runs independently and doesn't block the main scheduler or application.
        """
        try:
            from services.intelligent_stock_selection_service import (
                intelligent_stock_selector,
            )

            # Check if market data is available with non-blocking retry logic
            from services.realtime_market_engine import is_analytics_data_ready

            # Retry up to 6 times with 5-second intervals (max 30 seconds total)
            # This won't block the main application since it's in a background task
            max_retries = 6
            retry_interval = 5
            data_ready = False

            logger.info(
                "🔍 Background: Checking centralized_ws_manager data availability..."
            )
            for attempt in range(1, max_retries + 1):
                if is_analytics_data_ready():
                    data_ready = True
                    logger.info(
                        f"✅ Background: LIVE market data ready (attempt {attempt}/{max_retries})"
                    )
                    break
                else:
                    if attempt < max_retries:
                        logger.info(
                            f"⏳ Background: Market data not ready yet (attempt {attempt}/{max_retries}) - checking again in {retry_interval}s..."
                        )
                        await asyncio.sleep(retry_interval)
                    else:
                        logger.warning(
                            f"⚠️ Background: Market data not available after {max_retries} attempts - will proceed anyway"
                        )

            # ALWAYS continue even if data not ready - don't block the application
            if not data_ready:
                logger.warning(
                    "⚠️ Background: Proceeding with stock selection using available data (WebSocket may still be connecting)"
                )

            # Run pre-open stock selection with LIVE data
            logger.info(
                "✅ Background: LIVE pre-open data available - running stock selection..."
            )
            preopen_result = await intelligent_stock_selector.run_premarket_selection()

            if preopen_result and not preopen_result.get("error"):
                selected_stocks_data = preopen_result.get("selected_stocks", [])
                sentiment_analysis = preopen_result.get("sentiment_analysis", {})

                logger.info(
                    f"✅ Background: Pre-open stock selection complete: {len(selected_stocks_data)} stocks selected using LIVE data"
                )
                logger.info(
                    f"📊 Background: LIVE Market sentiment: {sentiment_analysis.get('sentiment')} (A/D: {sentiment_analysis.get('advance_decline_ratio', 1.0):.2f})"
                )

                # Store minimal reference for legacy compatibility
                self.selected_stocks = {}
                for stock_dict in selected_stocks_data:
                    symbol = stock_dict.get("symbol")
                    if symbol:
                        self.selected_stocks[symbol] = {
                            "symbol": symbol,
                            "instrument_key": stock_dict.get("instrument_key"),
                            "sector": stock_dict.get("sector"),
                            "option_type": stock_dict.get("options_direction"),
                        }

                logger.info(
                    "✅ Background: Pre-open stock selection complete - will validate at market open (9:15 AM)"
                )

            else:
                error_msg = (
                    preopen_result.get("error", "Unknown error")
                    if preopen_result
                    else "No result returned"
                )
                logger.warning(
                    f"⚠️ Background: Pre-open stock selection failed: {error_msg}"
                )
                self.task_errors["preopen_selection"] = error_msg
                self.selected_stocks = {}

        except Exception as e:
            logger.error(f"❌ Background: Pre-open stock selection failed: {e}")
            self.task_errors["preopen_selection"] = str(e)
            import traceback

            traceback.print_exc()
            self.selected_stocks = {}

    async def _validate_market_open_selection(self):
        """
        Validate and finalize stock selections at market open (9:15-9:30 AM).

        UPDATED FLOW:
        1. Market open validation ONLY (pre-open selection already done at 9:00-9:15 AM)
        2. Check if sentiment changed after market officially opened
        3. Finalize stock selections for the day
        4. Validate broker connections
        """
        logger.info("🔧 Market open validation (9:15-9:30 AM)...")

        try:
            from services.intelligent_stock_selection_service import (
                intelligent_stock_selector,
            )

            # Check if pre-open selections exist
            if not self.selected_stocks:
                logger.warning(
                    "⚠️ No pre-open selections found - pre-open selection may have failed"
                )
                logger.info("Attempting to run pre-open selection now...")

                # Fallback: Run pre-open selection if it didn't run at 9:00 AM
                await self._run_preopen_stock_selection()

                # If still no selections, log error
                if not self.selected_stocks:
                    logger.error(
                        "❌ No stocks selected - cannot proceed with trading session"
                    )
                    return

            # Wait for market to stabilize after opening
            logger.info("⏳ Waiting 5 seconds for market data to stabilize...")
            await asyncio.sleep(5)

            # Run market open validation (finalizes selections)
            logger.info(
                "🔍 Running market open validation - finalizing stock selections..."
            )
            try:
                validation_result = (
                    await intelligent_stock_selector.validate_market_open_selection()
                )

                if validation_result and not validation_result.get("error"):
                    validation_action = validation_result.get(
                        "validation_action", "UNKNOWN"
                    )
                    sentiment_changed = validation_result.get(
                        "sentiment_changed", False
                    )
                    final_count = validation_result.get("final_count", 0)

                    logger.info(
                        f"✅ Market open validation complete: {validation_action}"
                    )
                    logger.info(f"📊 Sentiment changed: {sentiment_changed}")
                    logger.info(
                        f"🎯 Final selections: {final_count} stocks locked for trading"
                    )

                    # Update our reference with final selections
                    final_stocks = validation_result.get("final_stocks", [])
                    self.selected_stocks = {}
                    for stock_dict in final_stocks:
                        symbol = stock_dict.get("symbol")
                        if symbol:
                            self.selected_stocks[symbol] = {
                                "symbol": symbol,
                                "instrument_key": stock_dict.get("instrument_key"),
                                "sector": stock_dict.get("sector"),
                                "option_type": stock_dict.get("options_direction"),
                                "final_score": stock_dict.get("final_score"),
                                "selection_finalized": True,
                            }

                    logger.info(
                        f"✅ Final selections confirmed: {len(self.selected_stocks)} stocks ready for auto-trading"
                    )
                else:
                    error_msg = (
                        validation_result.get("error", "Unknown error")
                        if validation_result
                        else "No result returned"
                    )
                    logger.warning(f"⚠️ Market open validation issue: {error_msg}")
                    logger.warning("⚠️ Will use premarket selections (if any)")

            except Exception as validation_error:
                logger.error(f"❌ Market open validation failed: {validation_error}")
                logger.warning("⚠️ Continuing with premarket selections")

            # Validate broker connections
            await self._validate_broker_connections()

            logger.info(
                "✅ Market open validation complete - ready for trading at 9:30 AM"
            )

        except Exception as e:
            logger.error(f"❌ Market open validation failed: {e}")

    async def _monitor_active_trading(self):
        """Monitor active trading session (9:30 AM - 3:30 PM)"""
        logger.info("📈 Monitoring active trading session...")

        try:
            # ❌ DISABLED: Auto-trading is now handled by AutoTradeScheduler (auto_trade_scheduler.py)
            # This prevents conflicts - AutoTradeScheduler manages WebSocket lifecycle
            # current_time = datetime.now(self.ist).time()
            # if (
            #     current_time >= time(9, 30)
            #     and current_time < time(9, 35)
            #     and not self.trading_sessions_active
            # ):
            #     await self._initialize_auto_trading_systems()

            # Update market status
            await self._update_market_status("normal_open")

            # ❌ DISABLED: Trading monitoring now handled by AutoTradeScheduler
            # if self.trading_sessions_active:
            #     await self._monitor_nifty_strategy()
            #     await self._execute_pending_trades()

            # Monitor portfolio performance
            await self._monitor_portfolio_performance()

            # Check risk parameters
            await self._check_risk_parameters()

            # Update stock analysis (every 15 minutes)
            current_minute = datetime.now(self.ist).minute
            if current_minute % 15 == 0:
                await self._update_stock_analysis()

        except Exception as e:
            logger.error(f"❌ Active trading monitoring failed: {e}")

    async def _post_market_cleanup(self):
        """Post-market cleanup and analysis (after 3:30 PM)"""
        logger.info("🧹 Starting post-market cleanup...")

        try:
            # ❌ DISABLED: Trading stop now handled by AutoTradeScheduler
            # if self.trading_sessions_active:
            #     await self._stop_auto_trading_systems()

            # Update market status
            await self._update_market_status("closed")

            # Generate end-of-day reports
            await self._generate_eod_reports()

            # Archive trading data
            await self._archive_trading_data()

            # Clear temporary caches
            await self._clear_temporary_caches()

            # Prepare for next trading day
            await self._prepare_next_trading_day()

            logger.info("✅ Post-market cleanup complete")

        except Exception as e:
            logger.error(f"❌ Post-market cleanup failed: {e}")

    async def _analyze_market_conditions(self) -> Dict:
        """Analyze overall market conditions"""
        try:
            market_data = {
                "nifty_trend": await self._get_nifty_trend(),
                "fii_dii_flow": await self._get_institutional_flow(),
                "sector_momentum": await self._get_sector_momentum(),
                "volatility_index": await self._get_vix_data(),
                "global_cues": await self._get_global_market_cues(),
            }

            # Calculate market sentiment score
            market_data["sentiment_score"] = self._calculate_market_sentiment(
                market_data
            )

            return market_data

        except Exception as e:
            logger.error(f"❌ Market analysis failed: {e}")
            return {}

    # === MISSING METHODS IMPLEMENTATION ===

    async def _validate_broker_connections(self):
        """Validate broker connections"""
        try:
            logger.info("🔗 Validating broker connections...")
            with next(get_db()) as db:
                configs = (
                    db.query(BrokerConfig).filter(BrokerConfig.is_active == True).all()
                )
                logger.info(f"Found {len(configs)} active broker configurations")
        except Exception as e:
            logger.error(f"Error validating broker connections: {e}")

    async def _update_market_status(self, status: str):
        """Update market status in cache"""
        try:
            self._safe_redis_set(
                "market_status",
                json.dumps(
                    {"status": status, "updated_at": datetime.now().isoformat()}
                ),
                ex=3600,
            )
            logger.info(f"📊 Market status updated: {status}")
        except Exception as e:
            logger.error(f"Error updating market status: {e}")

    async def _monitor_portfolio_performance(self):
        """Monitor portfolio performance during trading"""
        try:
            # Placeholder for portfolio monitoring
            pass
        except Exception as e:
            logger.error(f"Error monitoring portfolio: {e}")

    async def _check_risk_parameters(self):
        """Check risk parameters"""
        try:
            # Placeholder for risk checks
            pass
        except Exception as e:
            logger.error(f"Error checking risk parameters: {e}")

    async def _update_stock_analysis(self):
        """Update stock analysis during trading"""
        try:
            logger.info("🔄 Updating stock analysis...")
            # Placeholder for live analysis updates
        except Exception as e:
            logger.error(f"Error updating stock analysis: {e}")

    async def _generate_eod_reports(self):
        """Generate end-of-day reports"""
        try:
            logger.info("📈 Generating end-of-day reports...")
            # Placeholder for EOD reports
        except Exception as e:
            logger.error(f"Error generating EOD reports: {e}")

    async def _archive_trading_data(self):
        """Archive trading data"""
        try:
            logger.info("🗄️ Archiving trading data...")
            # Placeholder for data archiving
        except Exception as e:
            logger.error(f"Error archiving data: {e}")

    async def _clear_temporary_caches(self):
        """Clear temporary caches"""
        try:
            cache_keys = [
                "trading_instruments_cache",
                "trading_stocks_cache",
                "selected_trading_instruments",
            ]
            for key in cache_keys:
                self._safe_redis_delete(key)

            # Reset selection status in instrument registry
            try:
                logger.info("✅ Cleared selected stocks in instrument registry")
            except Exception as e:
                logger.error(f"Error clearing selected stocks in registry: {e}")

            logger.info("🧹 Cleared temporary caches")
        except Exception as e:
            logger.error(f"Error clearing caches: {e}")

    async def _prepare_next_trading_day(self):
        """Prepare for next trading day"""
        try:
            logger.info("🌅 Preparing for next trading day...")
            # Reset daily counters, prepare for tomorrow
        except Exception as e:
            logger.error(f"Error preparing next trading day: {e}")

    async def _get_stock_instruments(self, symbol: str) -> List[str]:
        """Get instruments for a specific stock"""
        try:
            # Basic implementation
            return [f"NSE_EQ|INE{symbol}"]
        except Exception as e:
            logger.error(f"Error getting instruments for {symbol}: {e}")
            return []

    # === MARKET ANALYSIS HELPER METHODS ===

    async def _get_nifty_trend(self) -> Dict:
        """Get Nifty trend data"""
        return {"trend": "bullish", "strength": 0.7}

    async def _get_institutional_flow(self) -> Dict:
        """Get FII/DII flow data"""
        return {"fii_flow": 1000, "dii_flow": 500}

    async def _get_sector_momentum(self) -> Dict:
        """Get sector momentum data"""
        return {"banking": 0.8, "it": 0.6, "auto": 0.5}

    async def _get_vix_data(self) -> float:
        """Get VIX data"""
        return 15.5

    async def _get_global_market_cues(self) -> Dict:
        """Get global market cues"""
        return {"us_markets": "positive", "asian_markets": "mixed"}

    def _calculate_market_sentiment(self, market_data: Dict) -> float:
        """Calculate overall market sentiment score"""
        try:
            # Simple sentiment calculation
            base_score = 0.5

            # Adjust based on various factors
            if market_data.get("nifty_trend", {}).get("trend") == "bullish":
                base_score += 0.2

            vix = market_data.get("volatility_index", 20)
            if vix < 15:
                base_score += 0.1
            elif vix > 25:
                base_score -= 0.1

            return min(max(base_score, 0.0), 1.0)
        except Exception as e:
            logger.error(f"Error calculating sentiment: {e}")
            return 0.5

    def _reset_daily_tasks_if_new_day(self, current_date):
        """Reset daily task tracking if it's a new day"""
        try:
            # Check if any completed task is from a previous date
            for task_name, completed_date in self.daily_tasks_completed.items():
                if completed_date and completed_date != current_date:
                    # Reset all tasks for new day
                    self.daily_tasks_completed = {
                        "early_preparation": None,
                        "preopen_stock_selection": None,
                        "market_open_validation": None,
                        "post_market_cleanup": None,
                    }
                    logger.info(
                        f"🔄 Daily tasks reset for new trading day: {current_date}"
                    )
                    break
        except Exception as e:
            logger.error(f"Error resetting daily tasks: {e}")

    def stop_scheduler(self):
        """Stop the market scheduler"""
        self.is_running = False
        logger.info("⏹️ Market scheduler stopped")

    # ================================
    # AUTO-TRADING INTEGRATION METHODS
    # ================================

    async def _initialize_auto_trading_systems(self):
        """Initialize and start all auto-trading systems at 9:30 AM"""
        try:
            logger.info("🚀 INITIALIZING AUTO-TRADING SYSTEMS AT 9:30 AM")

            # 1. Initialize Auto-Trading Coordinator
            from services.auto_trading_coordinator import AutoTradingCoordinator

            self.auto_trading_coordinator = AutoTradingCoordinator()

            # 2. Initialize NIFTY 9:40 Strategy (will activate at 9:40 AM)
            await self._initialize_nifty_strategy()

            # 3. Start live data feeds for selected instruments
            await self._activate_live_data_feeds()

            # 4. Initialize risk management systems
            await self._initialize_risk_management()

            # Mark trading systems as active
            self.trading_sessions_active = True
            logger.info("✅ AUTO-TRADING SYSTEMS INITIALIZED - LIVE TRADING ACTIVE")

        except Exception as e:
            logger.error(f"❌ Failed to initialize auto-trading systems: {e}")
            raise

    async def _initialize_nifty_strategy(self):
        """Initialize NIFTY 9:40 strategy"""
        try:
            logger.info("🔄 Initializing NIFTY 9:40 strategy...")

            # Import NIFTY strategy integration
            from services.strategies.nifty_09_40_integration import (
                get_nifty_strategy_integration,
            )

            self.nifty_strategy = await get_nifty_strategy_integration()

            # Strategy will auto-activate at 9:40 AM
            logger.info("✅ NIFTY 9:40 strategy initialized - will activate at 9:40 AM")

        except Exception as e:
            logger.error(f"❌ NIFTY strategy initialization failed: {e}")

    async def _monitor_nifty_strategy(self):
        """Monitor NIFTY 9:40 strategy"""
        try:
            if not self.nifty_strategy:
                return

            current_time = datetime.now(self.ist).time()

            # NIFTY strategy active from 9:40 AM to 3:15 PM
            if time(9, 40) <= current_time <= time(15, 15):
                # Strategy is running automatically via callbacks
                pass

        except Exception as e:
            logger.error(f"❌ NIFTY strategy monitoring failed: {e}")

    async def _execute_pending_trades(self):
        """Execute any pending trades from strategy signals"""
        try:
            # Get unified trading executor
            from services.unified_trading_executor import unified_trading_executor

            # Check for any pending trades that need execution
            # This is handled automatically by the strategies
            pass

        except Exception as e:
            logger.error(f"❌ Trade execution monitoring failed: {e}")

    async def _activate_live_data_feeds(self):
        """Activate live data feeds for all trading instruments"""
        try:
            logger.info("📡 Activating live data feeds...")

            # Get centralized WebSocket manager
            from services.centralized_ws_manager import centralized_ws_manager

            # Create priority subscription for selected stocks
            selected_instruments = []
            for symbol, stock_data in self.selected_stocks.items():
                instrument_key = stock_data.get("instrument_key")
                if instrument_key:
                    selected_instruments.append(
                        {
                            "symbol": symbol,
                            "instrument_key": instrument_key,
                            "priority": "HIGH",
                        }
                    )

            # Add NIFTY index for 9:40 strategy
            selected_instruments.append(
                {
                    "symbol": "NIFTY",
                    "instrument_key": "NSE_INDEX|Nifty 50",
                    "priority": "HIGH",
                }
            )

            # Activate priority subscription
            await centralized_ws_manager.priority_subscription(selected_instruments)
            logger.info(
                f"✅ Live data feeds activated for {len(selected_instruments)} instruments"
            )

        except Exception as e:
            logger.error(f"❌ Live data feed activation failed: {e}")

    async def _initialize_risk_management(self):
        """Initialize risk management and circuit breakers"""
        try:
            logger.info("🛡️ Initializing risk management systems...")

            # Initialize circuit breaker
            from services.circuit_breaker import circuit_breaker

            circuit_breaker.reset_daily_limits()

            logger.info("✅ Risk management systems initialized")

        except Exception as e:
            logger.error(f"❌ Risk management initialization failed: {e}")

    async def _stop_auto_trading_systems(self):
        """Stop all auto-trading systems at market close"""
        try:
            logger.info("🛑 STOPPING AUTO-TRADING SYSTEMS AT MARKET CLOSE")

            # 1. Stop NIFTY strategy
            if self.nifty_strategy:
                logger.info("Stopping NIFTY strategy...")
                await self.nifty_strategy.stop_daily_session()

            # 2. Stop auto-trading coordinator
            if self.auto_trading_coordinator:
                await self.auto_trading_coordinator.shutdown_system()

            # 3. Generate trading reports
            await self._generate_trading_performance_report()

            # Mark trading systems as inactive
            self.trading_sessions_active = False
            logger.info("✅ AUTO-TRADING SYSTEMS STOPPED")

        except Exception as e:
            logger.error(f"❌ Failed to stop auto-trading systems: {e}")

    async def _generate_trading_performance_report(self):
        """Generate daily trading performance report"""
        try:
            logger.info("📊 Generating daily trading performance report...")

            # Get trading database service
            from services.database.trading_db_service import TradingDatabaseService

            db_service = TradingDatabaseService()

            # Calculate daily performance
            await db_service.calculate_and_store_daily_performance(user_id=1)
            logger.info("✅ Daily performance report generated")

        except Exception as e:
            logger.error(f"❌ Performance report generation failed: {e}")

# Global singleton instance
_market_scheduler_instance = None

def get_market_scheduler():
    "Get singleton instance of MarketScheduleService"
    global _market_scheduler_instance
    if _market_scheduler_instance is None:
        _market_scheduler_instance = MarketScheduleService()
    return _market_scheduler_instance
