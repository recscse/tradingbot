import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import List, Dict, Optional
import pytz
import json
import redis
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User, BrokerConfig
from services.stock_analyzer import StockAnalyzer
from services.instrument_refresh_service import TradingInstrumentService
from services.trading_stock_selector import TradingStockSelector

# Import the optimized service

logger = logging.getLogger(__name__)


class MarketScheduleService:
    def __init__(self):
        self.ist = pytz.timezone("Asia/Kolkata")
        self.early_preparation = time(8, 0)  # 8:00 AM
        self.premarket_start = time(9, 0)  # 9:00 AM
        self.market_open = time(9, 15)  # 9:15 AM
        self.trading_start = time(9, 30)  # 9:30 AM
        self.market_close = time(15, 30)  # 3:30 PM

        self.stock_analyzer = StockAnalyzer()
        self.instrument_service = TradingInstrumentService()
        
        # ✅ ENHANCED: Initialize TradingStockSelector with optimized settings for options trading
        from services.enhanced_market_analytics import enhanced_analytics
        from database.connection import SessionLocal
        
        self.stock_selector = TradingStockSelector(
            analytics=enhanced_analytics,  # Use enhanced analytics with real-time data
            db_session_factory=SessionLocal,  # Use proper session factory
            option_service=None,  # Will use default upstox_option_service
            sectors_to_pick=1,  # Pick only the TOP performing sector
            per_sector_limit=2,  # Exactly 2 stocks per sector
            max_total_stocks=2,  # Maximum 2 stocks total for focused trading
            user_id=1,  # Default admin user - will be parameterized later
        )
        # Initialize the optimized service
        self.selected_stocks = {}
        self.is_running = False

        # Initialize Redis client
        self.redis_client = redis.Redis(
            host="localhost", port=6379, db=0, decode_responses=True
        )

    async def start_daily_scheduler(self):
        """Start the daily market scheduler"""
        self.is_running = True
        logger.info("🚀 Market scheduler started")

        while self.is_running:
            try:
                current_time = datetime.now(self.ist).time()
                current_date = datetime.now(self.ist).date()

                # Check if it's a weekday (Monday=0, Sunday=6)
                if datetime.now(self.ist).weekday() >= 5:
                    logger.info("📅 Weekend - Market closed")
                    await asyncio.sleep(3600)  # Sleep for 1 hour
                    continue

                # Early morning preparation (8:00 AM) - ADD THIS BLOCK
                if (
                    current_time >= self.early_preparation
                    and current_time < self.premarket_start
                ):
                    await self._run_early_morning_preparation()

                # Pre-market analysis (9:00 AM)
                if (
                    current_time >= self.premarket_start
                    and current_time < self.market_open
                ):
                    await self._run_premarket_analysis()

                # Trading preparation (9:15-9:30 AM)
                elif (
                    current_time >= self.market_open
                    and current_time < self.trading_start
                ):
                    await self._prepare_trading_session()

                # Active trading (9:30 AM - 3:30 PM)
                elif (
                    current_time >= self.trading_start
                    and current_time < self.market_close
                ):
                    await self._monitor_active_trading()

                # Post-market cleanup (after 3:30 PM)
                else:
                    await self._post_market_cleanup()

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"❌ Market scheduler error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _run_early_morning_preparation(self):
        """FIXED: Run at 8:00 AM - FNO service ALWAYS runs BEFORE instrument service"""
        logger.info("🌅 Starting early morning preparation...")

        try:
            # Check if it's Monday (weekday 0) for weekly FNO refresh
            current_weekday = datetime.now(self.ist).weekday()
            should_refresh_fno = current_weekday == 0  # Monday only

            # FIXED: ALWAYS run FNO service first (either refresh or verify existing data)
            logger.info("🔧 Step 1: FNO stock list preparation...")
            from services.fno_stock_service import FnoStockListService

            fno_service = FnoStockListService()

            if should_refresh_fno:
                # WEEKLY: Full refresh on Mondays
                logger.info("📊 Running weekly FNO stock list refresh (Monday)...")
                fno_result = fno_service.update_fno_list()

                if fno_result["status"] == "success":
                    logger.info(
                        f"✅ Weekly FNO refresh: {fno_result['total_stocks']} stocks"
                    )
                else:
                    logger.error(
                        f"❌ Weekly FNO refresh failed: {fno_result.get('error')}"
                    )
                    # Don't continue if FNO data is corrupted
                    return
            else:
                # DAILY: Verify existing FNO data is available
                logger.info(f"🔍 Verifying existing FNO data (Tuesday-Sunday)...")
                existing_stocks = fno_service.load_from_json()

                if not existing_stocks:
                    logger.warning(
                        "⚠️ No existing FNO data found, running emergency refresh..."
                    )
                    fno_result = fno_service.update_fno_list()
                    if fno_result["status"] != "success":
                        logger.error(
                            f"❌ Emergency FNO refresh failed: {fno_result.get('error')}"
                        )
                        return
                else:
                    logger.info(
                        f"✅ FNO data verified: {len(existing_stocks)} stocks available"
                    )

            # FIXED: Step 2 now ALWAYS runs AFTER FNO service has completed successfully
            logger.info(
                "🔧 Step 2: Building instrument service (depends on FNO data)..."
            )
            from services.instrument_refresh_service import get_trading_service

            instrument_service = get_trading_service()
            result = await instrument_service.initialize_service()

            if result.status == "success":
                logger.info(
                    f"✅ Instrument service ready with {result.websocket_instruments} keys"
                )
            else:
                logger.error(f"❌ Instrument service failed: {result.error}")

            logger.info("✅ Early morning preparation complete")

        except Exception as e:
            logger.error(f"❌ Early morning preparation failed: {e}")

    async def _run_premarket_analysis(self):
        """Run pre-market analysis from 9:00-9:15 AM"""
        logger.info("📊 Starting pre-market analysis...")

        try:
            # 1. Refresh instrument keys
            # from services.instrument_refresh_service import get_trading_service

            # instrument_service = get_trading_service()

            # Re-initialize the service (this will download fresh data and rebuild everything)
            # result = await instrument_service.initialize_service()

            # if result.status == "success":
            #     logger.info(
            #         f"✅ Instrument service re-initialized successfully with {result.websocket_instruments} WebSocket keys"
            #     )
            # else:
            #     logger.error(
            #         f"❌ Instrument service re-initialization failed: {result.error}"
            #     )

            # 2. Initialize instrument registry with new data
            try:
                from services.instrument_registry import instrument_registry

                await instrument_registry.initialize_registry()

                registry_stats = instrument_registry.get_stats()
                logger.info(
                    f"✅ Instrument registry initialized with {registry_stats['spot_instruments']} spot instruments, "
                    f"{registry_stats['fno_instruments']} F&O instruments"
                )
            except Exception as e:
                logger.error(f"❌ Failed to initialize instrument registry: {e}")

            # 3. Refresh the centralized WebSocket manager to use the new keys
            from services.centralized_ws_manager import centralized_manager

            if centralized_manager:
                # Tell the WebSocket manager to reload instrument keys
                await centralized_manager.initialize()
                logger.info("✅ WebSocket manager refreshed with new keys")

            # 4. Analyze market conditions
            market_analysis = await self._analyze_market_conditions()

            # 5. Select top stocks for trading
            self.selected_stocks = await self._select_trading_stocks(market_analysis)

            # 6. Prepare instrument keys for selected stocks
            await self._prepare_selected_stock_instruments()
            await self._prepare_selected_stock_instruments_enhanced()

            # 7. Update instrument registry with selected stocks
            try:
                from services.instrument_registry import instrument_registry

                # Flag these stocks as selected in the registry
                for symbol in self.selected_stocks.keys():
                    instrument_registry.mark_stock_as_selected(symbol)

                logger.info(
                    f"✅ Updated instrument registry with {len(self.selected_stocks)} selected stocks"
                )
            except Exception as e:
                logger.error(f"❌ Failed to update selected stocks in registry: {e}")

            logger.info(
                f"✅ Pre-market analysis complete. Selected {len(self.selected_stocks)} stocks"
            )

        except Exception as e:
            logger.error(f"❌ Pre-market analysis failed: {e}")

    async def _prepare_trading_session(self):
        """Prepare for trading session (9:15-9:30 AM)"""
        logger.info("🔧 Preparing trading session...")

        try:
            # Generate OHLC data for dashboard
            await self._generate_dashboard_ohlc()

            # Validate broker connections
            await self._validate_broker_connections()

            # Final stock selection confirmation
            await self._confirm_stock_selection()

            logger.info("✅ Trading session preparation complete")

        except Exception as e:
            logger.error(f"❌ Trading preparation failed: {e}")

    async def _monitor_active_trading(self):
        """Monitor active trading session (9:30 AM - 3:30 PM)"""
        logger.info("📈 Monitoring active trading session...")

        try:
            # Update market status
            await self._update_market_status("normal_open")

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

    async def _select_trading_stocks(self, market_analysis: Dict) -> Dict:
        """🚀 ENHANCED: Select stocks using TradingStockSelector with OPTIONS INTEGRATION"""
        try:
            logger.info("🔍 Running advanced stock selection with options integration...")
            
            # ✅ STEP 1: Use the advanced TradingStockSelector with options support
            # This selector integrates with enhanced analytics and includes option chain data
            selected_candidates = self.stock_selector.run_selection_sync()
            
            if not selected_candidates:
                logger.warning("❌ No stocks selected by TradingStockSelector")
                return {}
            
            logger.info(f"✅ TradingStockSelector found {len(selected_candidates)} candidates")
            
            # ✅ STEP 2: Convert to the expected format with enhanced data
            selected = {}
            
            for candidate in selected_candidates:
                try:
                    symbol = candidate.get("symbol")
                    if not symbol:
                        continue
                    
                    # ✅ STEP 3: Prepare comprehensive stock data with options
                    stock_data = {
                        "symbol": symbol,
                        "instrument_key": candidate.get("instrument_key"),
                        "sector": candidate.get("sector"),
                        "price_at_selection": candidate.get("price_at_selection"),
                        "selection_score": candidate.get("selection_score"),
                        "selection_reason": candidate.get("selection_reason"),
                        
                        # ✅ OPTIONS DATA - Ready for trading
                        "option_type": candidate.get("option_type"),  # CE/PE based on market sentiment
                        "option_contract": candidate.get("option_contract"),  # ATM contract details
                        "option_chain_data": candidate.get("option_chain_data"),  # Complete chain
                        "option_expiry_date": candidate.get("option_expiry_date"),  # Nearest expiry
                        "option_expiry_dates": candidate.get("option_expiry_dates", []),  # All expiries
                        "option_contracts_available": candidate.get("option_contracts_available", 0),
                        
                        # Enhanced metadata
                        "strategy_score": candidate.get("strategy_score", 0),
                        "strategy_details": candidate.get("strategy_details", {}),
                        "has_option_chain": candidate.get("option_chain_data") is not None,
                        "selected_at": datetime.now(self.ist).isoformat(),
                    }
                    
                    # ✅ STEP 4: Get instrument keys for both stock and options
                    stock_instruments = await self._get_stock_instruments(symbol)
                    stock_data["instruments"] = stock_instruments
                    
                    # ✅ STEP 5: Add option instrument keys if available
                    if candidate.get("option_contract"):
                        option_instrument_key = candidate["option_contract"].get("instrument_key")
                        if option_instrument_key:
                            stock_data["option_instrument_key"] = option_instrument_key
                            stock_data["instruments"]["option"] = option_instrument_key
                            logger.info(f"✅ {symbol}: Stock + Option instruments ready")
                    
                    selected[symbol] = {
                        "stock_data": stock_data,
                        "analysis": {
                            "score": candidate.get("selection_score", 0),
                            "sector_performance": candidate.get("sector"),
                            "market_sentiment_aligned": True,  # Selected based on sentiment
                            "has_options": stock_data["has_option_chain"],
                            "option_type_recommendation": candidate.get("option_type"),
                        },
                        "instruments": stock_instruments,
                        "options_ready": stock_data["has_option_chain"],
                    }
                    
                    logger.info(f"📊 {symbol}: Selected with {candidate.get('option_contracts_available', 0)} option contracts")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing selected stock {candidate.get('symbol')}: {e}")
                    continue
            
            # ✅ STEP 6: Store selection results for later access
            self._store_selection_results(selected_candidates)
            
            logger.info(f"🎯 SELECTION COMPLETE: {len(selected)} stocks with options integration")
            for symbol, data in selected.items():
                option_status = "✅ Options Ready" if data["options_ready"] else "❌ No Options"
                logger.info(f"  📈 {symbol} ({data['stock_data']['sector']}) - {option_status}")
            
            return selected

        except Exception as e:
            logger.error(f"❌ Enhanced stock selection failed: {e}")
            # Fallback to empty selection rather than crash
            return {}

    def _store_selection_results(self, selected_candidates: List[Dict]):
        """🗃️ Store selection results in Redis for easy access"""
        try:
            if not selected_candidates:
                return
            
            # Store individual stock data
            for candidate in selected_candidates:
                symbol = candidate.get("symbol")
                if symbol:
                    key = f"selected_stock:{symbol}:{datetime.now(self.ist).date().isoformat()}"
                    self.redis_client.setex(key, 86400, json.dumps(candidate))  # 24 hour expiry
            
            # Store summary data
            summary_data = {
                "selection_date": datetime.now(self.ist).date().isoformat(),
                "selection_time": datetime.now(self.ist).time().isoformat(),
                "total_selected": len(selected_candidates),
                "stocks": [c.get("symbol") for c in selected_candidates],
                "sectors": list(set(c.get("sector") for c in selected_candidates if c.get("sector"))),
                "options_ready_count": sum(1 for c in selected_candidates if c.get("option_chain_data")),
            }
            
            summary_key = f"stock_selection_summary:{datetime.now(self.ist).date().isoformat()}"
            self.redis_client.setex(summary_key, 86400, json.dumps(summary_data))
            
            logger.info(f"✅ Stored selection results in Redis: {len(selected_candidates)} stocks")
            
        except Exception as e:
            logger.error(f"❌ Failed to store selection results: {e}")

    def get_selected_stocks_from_storage(self, date_str: str = None) -> List[Dict]:
        """📖 Retrieve stored selection results from Redis"""
        try:
            if not date_str:
                date_str = datetime.now(self.ist).date().isoformat()
            
            # Get summary first
            summary_key = f"stock_selection_summary:{date_str}"
            summary_data = self.redis_client.get(summary_key)
            
            if not summary_data:
                logger.warning(f"No selection summary found for {date_str}")
                return []
            
            summary = json.loads(summary_data)
            stocks = summary.get("stocks", [])
            
            # Get individual stock data
            selected_stocks = []
            for symbol in stocks:
                stock_key = f"selected_stock:{symbol}:{date_str}"
                stock_data = self.redis_client.get(stock_key)
                
                if stock_data:
                    selected_stocks.append(json.loads(stock_data))
            
            logger.info(f"📖 Retrieved {len(selected_stocks)} selected stocks from storage")
            return selected_stocks
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve selection results: {e}")
            return []

    async def _prepare_selected_stock_instruments_enhanced(self):
        """ENHANCED: Use instrument registry for comprehensive instrument keys"""
        try:
            if not self.selected_stocks:
                logger.warning("No stocks selected for instrument preparation")
                return

            from services.instrument_registry import instrument_registry

            all_trading_instruments = []

            for symbol, stock_data in self.selected_stocks.items():
                try:
                    # Get trading keys from registry
                    trading_keys = instrument_registry.get_instrument_keys_for_trading(
                        symbol
                    )

                    if trading_keys:
                        all_trading_instruments.extend(trading_keys)
                        logger.info(
                            f"📋 Added {len(trading_keys)} instruments for {symbol} from registry"
                        )
                    else:
                        # Fallback to fast retrieval if registry doesn't have the data
                        from services.optimized_instrument_service import fast_retrieval

                        stock_mapping = fast_retrieval.get_stock_instruments(symbol)
                        if stock_mapping:
                            instruments = stock_mapping.get("instruments", {})
                            primary_key = stock_mapping.get("primary_instrument_key")
                            if primary_key:
                                all_trading_instruments.append(primary_key)

                            # Add futures
                            futures = instruments.get("FUT", [])[:3]
                            for future in futures:
                                if future.get("instrument_key"):
                                    all_trading_instruments.append(
                                        future["instrument_key"]
                                    )

                            # Add options
                            current_price = stock_data.get("analysis", {}).get(
                                "current_price", 0
                            )
                            if current_price > 0:
                                atm_strike = round(current_price / 50) * 50
                                min_strike = atm_strike - 1000
                                max_strike = atm_strike + 1000

                                for option_type in ["CE", "PE"]:
                                    for option in instruments.get(option_type, []):
                                        strike = option.get("strike_price", 0)
                                        if min_strike <= strike <= max_strike:
                                            if option.get("instrument_key"):
                                                all_trading_instruments.append(
                                                    option["instrument_key"]
                                                )

                            logger.info(
                                f"📋 Generated instruments for {symbol} from fast retrieval"
                            )

                except Exception as e:
                    logger.error(f"Error getting instruments for {symbol}: {e}")
                    continue

            unique_instruments = list(set(all_trading_instruments))
            await self._cache_trading_instruments(unique_instruments)

            logger.info(
                f"✅ Prepared {len(unique_instruments)} unique trading instruments"
            )

        except Exception as e:
            logger.error(f"❌ Failed to prepare enhanced trading instruments: {e}")

    # === MISSING METHODS IMPLEMENTATION ===

    async def _prepare_selected_stock_instruments(self):
        """Basic instrument preparation (legacy method)"""
        try:
            if not self.selected_stocks:
                return

            instruments = []
            for symbol in self.selected_stocks.keys():
                # Add basic spot instrument
                instruments.append(f"NSE_EQ|INE{symbol}")

            await self._cache_selected_instruments(instruments)
            logger.info(f"📋 Prepared {len(instruments)} basic instruments")

        except Exception as e:
            logger.error(f"Error preparing basic instruments: {e}")

    async def _cache_selected_instruments(self, instruments):
        """Cache selected instruments for WebSocket access"""
        try:
            self.redis_client.setex(
                "selected_trading_instruments", 3600, json.dumps(instruments)
            )
            logger.info(f"💾 Cached {len(instruments)} selected instruments")
        except Exception as e:
            logger.error(f"Error caching selected instruments: {e}")

    async def _generate_dashboard_ohlc(self):
        """Generate OHLC data for dashboard"""
        try:
            logger.info("📊 Generating dashboard OHLC data...")
            # Implementation for OHLC generation
            await asyncio.sleep(1)  # Placeholder
        except Exception as e:
            logger.error(f"Error generating OHLC: {e}")

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

    async def _confirm_stock_selection(self):
        """Confirm final stock selection"""
        try:
            logger.info(f"✅ Confirmed {len(self.selected_stocks)} stocks for trading")
        except Exception as e:
            logger.error(f"Error confirming stock selection: {e}")

    async def _update_market_status(self, status: str):
        """Update market status in cache"""
        try:
            self.redis_client.setex(
                "market_status",
                3600,
                json.dumps(
                    {"status": status, "updated_at": datetime.now().isoformat()}
                ),
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
                self.redis_client.delete(key)

            # Reset selection status in instrument registry
            try:
                from services.instrument_registry import instrument_registry

                instrument_registry.clear_selected_stocks()
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

    def stop_scheduler(self):
        """Stop the market scheduler"""
        self.is_running = False
        logger.info("⏹️ Market scheduler stopped")
