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
from services.optimized_instrument_service import OptimizedInstrumentService
from services.stock_analyzer import StockAnalyzer
from services.instrument_refresh_service import InstrumentRefreshService
from utils.instrument_key_cache import save_instrument_keys, load_instrument_keys

logger = logging.getLogger(__name__)


class MarketScheduleService:
    def __init__(self):
        self.ist = pytz.timezone("Asia/Kolkata")
        self.premarket_start = time(9, 0)  # 9:00 AM
        self.market_open = time(9, 15)  # 9:15 AM
        self.trading_start = time(9, 30)  # 9:30 AM
        self.market_close = time(15, 30)  # 3:30 PM

        self.stock_analyzer = StockAnalyzer()
        self.instrument_service = InstrumentRefreshService()
        self.optimized_service = OptimizedInstrumentService()
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

    async def _run_premarket_analysis(self):
        """Run pre-market analysis from 9:00-9:15 AM"""
        logger.info("📊 Starting pre-market analysis...")

        try:
            # 1. Refresh instrument keys
            await self.instrument_service.refresh_daily_instruments()
            await self.optimized_service.initialize_instruments_system()

            # 2. Analyze market conditions
            market_analysis = await self._analyze_market_conditions()

            # 3. Select top stocks for trading
            self.selected_stocks = await self._select_trading_stocks(market_analysis)

            # 4. Prepare instrument keys for selected stocks
            await self._prepare_selected_stock_instruments()
            await self._prepare_selected_stock_instruments_enhanced()

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
        """Select stocks for trading based on analysis"""
        try:
            # Get all available stocks
            all_stocks = await self.stock_analyzer.get_all_tradeable_stocks()

            selected = {}

            for stock in all_stocks:
                try:
                    # Analyze individual stock
                    stock_score = await self.stock_analyzer.analyze_stock_for_trading(
                        stock, market_analysis
                    )

                    # Select top scoring stocks
                    if stock_score["score"] > 0.7:  # Threshold for selection
                        selected[stock["symbol"]] = {
                            "stock_data": stock,
                            "analysis": stock_score,
                            "instruments": await self._get_stock_instruments(
                                stock["symbol"]
                            ),
                        }

                    # Limit to top 20 stocks
                    if len(selected) >= 20:
                        break

                except Exception as e:
                    logger.error(f"❌ Error analyzing {stock.get('symbol')}: {e}")
                    continue

            return selected

        except Exception as e:
            logger.error(f"❌ Stock selection failed: {e}")
            return {}

    async def _prepare_selected_stock_instruments_enhanced(self):
        """ENHANCED: Use OptimizedInstrumentService for comprehensive instrument keys"""
        try:
            if not self.selected_stocks:
                logger.warning("No stocks selected for instrument preparation")
                return

            from services.optimized_instrument_service import fast_retrieval

            all_trading_instruments = []

            for symbol, stock_data in self.selected_stocks.items():
                try:
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
                                all_trading_instruments.append(future["instrument_key"])

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

                        logger.info(f"📋 Generated instruments for {symbol}")

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

    async def _cache_trading_instruments(self, instruments: List[str]):
        """Cache trading instruments for WebSocket and other services"""
        try:
            # Cache for WebSocket access
            self.redis_client.setex(
                "trading_instruments_cache",
                3600,
                json.dumps(
                    {
                        "instruments": instruments,
                        "cached_at": datetime.now().isoformat(),
                        "count": len(instruments),
                    }
                ),
            )

            # Cache selected stocks data
            selected_stocks_data = {
                "selected_stocks": [
                    {
                        "symbol": symbol,
                        "stock_data": data.get("stock_data", {}),
                        "analysis": data.get("analysis", {}),
                        "instrument_key": data.get("stock_data", {}).get(
                            "instrument_key", f"NSE_EQ|{symbol}"
                        ),
                    }
                    for symbol, data in self.selected_stocks.items()
                ],
                "cached_at": datetime.now().isoformat(),
            }
            self.redis_client.setex(
                "trading_stocks_cache", 3600, json.dumps(selected_stocks_data)
            )

            logger.info(
                f"💾 Cached {len(instruments)} instruments and {len(self.selected_stocks)} selected stocks"
            )

        except Exception as e:
            logger.error(f"Error caching trading data: {e}")

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
