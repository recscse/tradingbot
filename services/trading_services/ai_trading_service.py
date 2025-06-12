# services/trading_services/ai_trading_service.py
# COMPLETE FIXED VERSION - Works with your existing StrategyService

import asyncio
import logging
from datetime import datetime, time
from typing import Dict, List
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import TradeSignal, User, BrokerConfig
from services.strategy_service import StrategyService

logger = logging.getLogger(__name__)


class AITradingService:
    def __init__(self):
        self.is_active = False
        self.selected_stocks = {}
        self.live_data_service = None
        self.strategy_service = None
        self.trading_signals = {}
        self.analysis_interval = 300  # 5 minutes between analyses per stock
        self.last_analysis_time = {}
        self.error_count = {}
        self.max_errors_per_stock = 3

    async def start_trading(self, selected_stocks: Dict, live_data_service):
        """Start AI trading for selected stocks with enhanced error handling"""
        try:
            self.is_active = True
            self.selected_stocks = selected_stocks
            self.live_data_service = live_data_service

            # Initialize strategy service with your existing database
            db = next(get_db())
            self.strategy_service = StrategyService(db)

            logger.info(f"🤖 AI Trading started for {len(selected_stocks)} stocks")
            logger.info(
                f"📊 Using existing data sources: PreMarket cache, Live cache, Upstox API"
            )

            # Log available stocks
            stock_symbols = list(selected_stocks.keys())[:5]  # First 5 stocks
            logger.info(f"🎯 Sample stocks: {stock_symbols}")

            # Start trading loop
            await self._trading_loop()

        except Exception as e:
            logger.error(f"❌ AI Trading startup failed: {e}")
            raise

    async def _trading_loop(self):
        """Main AI trading loop with enhanced error handling"""
        consecutive_errors = 0
        max_consecutive_errors = 5

        while self.is_active:
            try:
                current_time = datetime.now().time()

                # Only trade during market hours (9:30 AM - 3:30 PM)
                if time(9, 30) <= current_time <= time(15, 30):
                    await self._process_trading_signals()
                    consecutive_errors = 0  # Reset error count on success

                    # Log periodic status
                    if datetime.now().minute % 15 == 0:  # Every 15 minutes
                        await self._log_status()
                else:
                    if datetime.now().minute == 0:  # Log once per hour outside market
                        logger.info("📈 Outside market hours - AI trading on standby")

                # Adaptive sleep intervals
                if time(9, 30) <= current_time <= time(15, 30):
                    await asyncio.sleep(180)  # 3 minutes during market hours
                else:
                    await asyncio.sleep(600)  # 10 minutes outside market hours

            except Exception as e:
                consecutive_errors += 1
                logger.error(f"❌ AI trading loop error #{consecutive_errors}: {e}")

                if consecutive_errors >= max_consecutive_errors:
                    logger.error(
                        f"❌ Too many consecutive errors ({consecutive_errors}). Stopping AI trading."
                    )
                    self.is_active = False
                    break

                # Exponential backoff on errors
                sleep_time = min(300 * consecutive_errors, 1800)  # Max 30 minutes
                logger.info(f"⏳ Waiting {sleep_time} seconds before retry...")
                await asyncio.sleep(sleep_time)

    async def _process_trading_signals(self):
        """Process trading signals with improved error handling"""
        try:
            if not self.selected_stocks:
                logger.warning("⚠️ No stocks selected for AI analysis")
                return

            current_time = datetime.now().timestamp()
            processed_count = 0
            success_count = 0
            error_count = 0

            logger.info(
                f"🔍 Processing {len(self.selected_stocks)} stocks for signals..."
            )

            for symbol, stock_data in self.selected_stocks.items():
                try:
                    # Check if enough time has passed since last analysis
                    last_analysis = self.last_analysis_time.get(symbol, 0)
                    if current_time - last_analysis < self.analysis_interval:
                        continue

                    # Check error count for this stock
                    if self.error_count.get(symbol, 0) >= self.max_errors_per_stock:
                        if datetime.now().minute % 30 == 0:  # Log every 30 minutes
                            logger.warning(
                                f"⚠️ Skipping {symbol} - too many errors ({self.error_count[symbol]})"
                            )
                        continue

                    # Analyze stock with timeout
                    logger.debug(f"📊 Analyzing {symbol}...")

                    try:
                        # Use clean symbol (your StrategyService expects this)
                        clean_symbol = symbol.replace(".NS", "")

                        analysis = await asyncio.wait_for(
                            self.strategy_service.analyze_stock(clean_symbol),
                            timeout=30.0,  # 30 second timeout per stock
                        )

                        # Reset error count on success
                        self.error_count[symbol] = 0

                        # Check if signal meets criteria
                        if (
                            analysis
                            and analysis.get("signal") in ["BUY", "SELL"]
                            and analysis.get("confidence", 0) > 0.7
                        ):

                            await self._generate_trading_signal(clean_symbol, analysis)
                            success_count += 1

                            logger.info(
                                f"✅ {clean_symbol}: {analysis['signal']} "
                                f"(confidence: {analysis['confidence']:.2f}, "
                                f"source: {analysis.get('data_source', 'unknown')})"
                            )
                        else:
                            # Log for debugging
                            signal = (
                                analysis.get("signal", "UNKNOWN")
                                if analysis
                                else "NO_ANALYSIS"
                            )
                            confidence = (
                                analysis.get("confidence", 0) if analysis else 0
                            )
                            logger.debug(
                                f"📊 {clean_symbol}: {signal} (confidence: {confidence:.2f}) - Below threshold"
                            )

                        # Update last analysis time
                        self.last_analysis_time[symbol] = current_time
                        processed_count += 1

                        # Rate limiting between stocks
                        await asyncio.sleep(1)  # 1 second between stocks

                    except asyncio.TimeoutError:
                        logger.warning(f"⏱️ Analysis timeout for {symbol}")
                        self._increment_error_count(symbol)
                        error_count += 1

                    except Exception as stock_error:
                        logger.error(
                            f"❌ Signal processing failed for {symbol}: {stock_error}"
                        )
                        self._increment_error_count(symbol)
                        error_count += 1

                except Exception as e:
                    logger.error(f"❌ Unexpected error processing {symbol}: {e}")
                    error_count += 1

            # Log summary
            total_stocks = len(self.selected_stocks)
            logger.info(
                f"📈 AI Analysis Summary: {processed_count}/{total_stocks} processed, "
                f"{success_count} signals generated, {error_count} errors"
            )

            # Warning for high error rates
            if error_count > total_stocks * 0.3:  # More than 30% errors
                logger.warning(
                    f"⚠️ High error rate: {error_count}/{total_stocks} stocks failed"
                )

        except Exception as e:
            logger.error(f"❌ Trading signal processing failed: {e}")

    def _increment_error_count(self, symbol: str):
        """Increment error count for a stock"""
        self.error_count[symbol] = self.error_count.get(symbol, 0) + 1
        if self.error_count[symbol] >= self.max_errors_per_stock:
            logger.warning(
                f"⚠️ {symbol} reached max error count ({self.max_errors_per_stock})"
            )

    async def _generate_trading_signal(self, symbol: str, analysis: Dict):
        """Generate and store trading signal with enhanced error handling"""
        db = None
        try:
            db = next(get_db())

            # Get all active users
            active_users = db.query(User).filter(User.is_active == True).all()

            if not active_users:
                logger.warning("⚠️ No active users found for signal generation")
                return

            signals_created = 0
            for user in active_users:
                try:
                    signal = TradeSignal(
                        user_id=user.id,
                        symbol=symbol,
                        trade_type=analysis["signal"],
                        confidence=analysis["confidence"],
                        execution_status="PENDING",
                        created_at=datetime.now(),
                    )

                    db.add(signal)
                    signals_created += 1

                except Exception as user_error:
                    logger.error(
                        f"❌ Failed to create signal for user {user.id}: {user_error}"
                    )
                    continue

            if signals_created > 0:
                db.commit()
                logger.info(
                    f"📊 Generated {analysis['signal']} signal for {symbol} "
                    f"(confidence: {analysis['confidence']:.2f}, "
                    f"users: {signals_created}, "
                    f"reason: {analysis.get('reason', 'N/A')}, "
                    f"source: {analysis.get('data_source', 'unknown')})"
                )
            else:
                logger.warning(f"⚠️ No signals created for {symbol}")

        except Exception as e:
            logger.error(f"❌ Signal generation failed for {symbol}: {e}")
            if db:
                db.rollback()
        finally:
            if db:
                db.close()

    async def _log_status(self):
        """Log periodic status information"""
        try:
            total_stocks = len(self.selected_stocks)
            analyzed_stocks = len(self.last_analysis_time)
            error_stocks = len(
                [s for s, count in self.error_count.items() if count > 0]
            )

            logger.info(f"🤖 AI Trading Status:")
            logger.info(f"   📊 Total stocks: {total_stocks}")
            logger.info(f"   ✅ Analyzed: {analyzed_stocks}")
            logger.info(f"   ❌ With errors: {error_stocks}")

            # Log stocks with errors
            if error_stocks > 0:
                error_list = [
                    f"{symbol}({count})"
                    for symbol, count in self.error_count.items()
                    if count > 0
                ]
                logger.info(f"   🚫 Error stocks: {error_list[:5]}")  # First 5

        except Exception as e:
            logger.error(f"❌ Error logging status: {e}")

    async def stop_trading(self):
        """Stop AI trading with cleanup"""
        try:
            self.is_active = False

            # Log final statistics
            total_stocks = len(self.selected_stocks)
            analyzed_stocks = len(self.last_analysis_time)
            error_stocks = len(
                [s for s, count in self.error_count.items() if count > 0]
            )

            logger.info(f"⏹️ AI Trading stopped - Final stats:")
            logger.info(f"   📊 Total stocks: {total_stocks}")
            logger.info(f"   ✅ Analyzed: {analyzed_stocks}")
            logger.info(f"   ❌ With errors: {error_stocks}")

            # Clear state
            self.selected_stocks = {}
            self.last_analysis_time = {}
            self.error_count = {}

        except Exception as e:
            logger.error(f"❌ Error during AI trading shutdown: {e}")

    def get_status(self) -> Dict:
        """Get AI trading service status"""
        try:
            return {
                "is_active": self.is_active,
                "selected_stocks_count": len(self.selected_stocks),
                "analyzed_stocks": len(self.last_analysis_time),
                "error_stocks": {
                    symbol: count
                    for symbol, count in self.error_count.items()
                    if count > 0
                },
                "analysis_interval_seconds": self.analysis_interval,
                "data_sources": ["premarket_cache", "live_cache", "upstox_api"],
                "last_update": datetime.now().isoformat(),
            }
        except Exception as e:
            return {"error": str(e)}
