"""
LiveTradingEngine with Centralized WebSocket Integration

Manages live trading for individual users with support for
the centralized WebSocket data system.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set

# Import necessary modules
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User, BrokerConfig, TradeSignal

logger = logging.getLogger(__name__)


class LiveTradingEngine:
    """
    LiveTradingEngine manages trading operations for a specific user
    with support for centralized WebSocket data
    """

    def __init__(self, user_id: int):
        """Initialize LiveTradingEngine for a specific user"""
        self.user_id = user_id
        self.is_running = False
        self.active_stocks = {}  # Symbol -> Stock data
        self.price_history = {}  # Symbol -> [price points]
        self.signals = {}  # Symbol -> Signal data
        self.last_processed = {}  # Symbol -> last processed time
        self.broker_config = None
        self.centralized_manager = None
        self.broker_token = None

    async def start_trading_session(self, centralized_manager=None):
        """
        Start trading session for the user

        Now supports the centralized WebSocket manager
        """
        try:
            logger.info(f"🚀 Starting LiveTradingEngine for user {self.user_id}")

            # Store centralized manager reference if provided
            self.centralized_manager = centralized_manager

            # Get user's broker configuration
            await self._load_broker_config()

            if not self.broker_config:
                logger.warning(f"⚠️ No broker configuration for user {self.user_id}")
                return {"status": "error", "message": "No broker configuration found"}

            # Store broker token for API calls
            self.broker_token = self.broker_config.access_token

            # Load user's active stocks
            await self._load_active_stocks()

            if not self.active_stocks:
                logger.warning(f"⚠️ No active stocks for user {self.user_id}")
                return {"status": "warning", "message": "No active stocks found"}

            # Initialize price history
            for symbol in self.active_stocks:
                self.price_history[symbol] = []
                self.last_processed[symbol] = datetime.now()

            # Set engine as running
            self.is_running = True

            # Log data source
            if self.centralized_manager:
                logger.info(f"📊 User {self.user_id} using centralized WebSocket data")
            else:
                logger.info(f"📊 User {self.user_id} using legacy data service")

            logger.info(
                f"✅ LiveTradingEngine started for user {self.user_id} with {len(self.active_stocks)} stocks"
            )
            return {
                "status": "success",
                "active_stocks": len(self.active_stocks),
                "broker": self.broker_config.broker_name,
                "centralized_data": self.centralized_manager is not None,
            }

        except Exception as e:
            logger.error(
                f"❌ Failed to start LiveTradingEngine for user {self.user_id}: {e}"
            )
            return {"status": "error", "message": str(e)}

    async def _load_broker_config(self):
        """Load user's broker configuration"""
        db = None
        try:
            db = next(get_db())

            # Get user's active broker
            broker_config = (
                db.query(BrokerConfig)
                .filter(
                    BrokerConfig.user_id == self.user_id,
                    BrokerConfig.is_active == True,
                    BrokerConfig.access_token.isnot(None),
                )
                .first()
            )

            if broker_config:
                self.broker_config = broker_config
                logger.info(
                    f"✅ Loaded broker config for user {self.user_id}: {broker_config.broker_name}"
                )
            else:
                logger.warning(f"⚠️ No active broker found for user {self.user_id}")

        except Exception as e:
            logger.error(f"❌ Error loading broker config for user {self.user_id}: {e}")
        finally:
            if db:
                db.close()

    async def _load_active_stocks(self):
        """Load user's active stocks for trading"""
        db = None
        try:
            db = next(get_db())

            # Get user record to check preferences
            user = db.query(User).filter(User.id == self.user_id).first()

            if not user:
                logger.warning(f"⚠️ User {self.user_id} not found")
                return

            # Get user's active signals
            active_signals = (
                db.query(TradeSignal)
                .filter(
                    TradeSignal.user_id == self.user_id, TradeSignal.is_active == True
                )
                .all()
            )

            # Process signals to get active stocks
            for signal in active_signals:
                symbol = signal.symbol

                if symbol not in self.active_stocks:
                    self.active_stocks[symbol] = {
                        "symbol": symbol,
                        "signals": [],
                        "instrument_key": signal.instrument_key,
                        "exchange": signal.exchange,
                    }

                # Add signal to stock's signals list
                self.active_stocks[symbol]["signals"].append(
                    {
                        "id": signal.id,
                        "signal_type": signal.signal_type,
                        "entry_price": signal.entry_price,
                        "target_price": signal.target_price,
                        "stop_loss": signal.stop_loss,
                        "quantity": signal.quantity,
                        "created_at": (
                            signal.created_at.isoformat() if signal.created_at else None
                        ),
                    }
                )

            logger.info(
                f"✅ Loaded {len(self.active_stocks)} active stocks for user {self.user_id}"
            )

            # If no active signals but user has trading preferences, load default stocks
            if (
                not self.active_stocks
                and hasattr(user, "trading_preferences")
                and user.trading_preferences
            ):
                await self._load_default_stocks(user.trading_preferences)

        except Exception as e:
            logger.error(f"❌ Error loading active stocks for user {self.user_id}: {e}")
        finally:
            if db:
                db.close()

    async def _load_default_stocks(self, preferences):
        """Load default stocks based on user preferences"""
        try:
            # This would load default stocks based on user preferences
            # For now, just log that it would happen
            logger.info(f"📋 Would load default stocks based on user preferences")

            # Mock implementation
            default_stocks = ["RELIANCE", "TCS", "HDFCBANK"]

            for symbol in default_stocks:
                self.active_stocks[symbol] = {
                    "symbol": symbol,
                    "signals": [],
                    "source": "default_preferences",
                }

            logger.info(
                f"✅ Loaded {len(default_stocks)} default stocks for user {self.user_id}"
            )

        except Exception as e:
            logger.error(f"❌ Error loading default stocks: {e}")

    async def process_price_update(self, symbol: str, price: float, price_data: Dict):
        """
        Process price update for a symbol

        This method is called by the TradingEngine when it receives price updates
        from the centralized WebSocket manager
        """
        try:
            if not self.is_running or symbol not in self.active_stocks:
                return

            # Add to price history
            self.price_history.setdefault(symbol, []).append(
                {"price": price, "timestamp": datetime.now().isoformat()}
            )

            # Keep history manageable (last 500 points)
            if len(self.price_history[symbol]) > 500:
                self.price_history[symbol] = self.price_history[symbol][-500:]

            # Check if we should process this update
            last_processed = self.last_processed.get(symbol, datetime.min)
            now = datetime.now()

            # Only process every few seconds to avoid excessive processing
            if (now - last_processed) < timedelta(seconds=5):
                return

            # Update last processed time
            self.last_processed[symbol] = now

            # Process active signals
            await self._process_signals(symbol, price)

        except Exception as e:
            logger.error(f"❌ Error processing price update for {symbol}: {e}")

    async def _process_signals(self, symbol: str, price: float):
        """Process active signals for a stock"""
        try:
            if symbol not in self.active_stocks:
                return

            stock_data = self.active_stocks[symbol]
            signals = stock_data.get("signals", [])

            if not signals:
                return

            # Process each signal
            for signal in signals:
                signal_type = signal.get("signal_type")
                entry_price = signal.get("entry_price")
                target_price = signal.get("target_price")
                stop_loss = signal.get("stop_loss")

                if not all([signal_type, entry_price, target_price, stop_loss]):
                    continue

                # Check for target hit
                if signal_type == "BUY" and price >= target_price:
                    await self._signal_target_hit(symbol, signal, price)
                elif signal_type == "SELL" and price <= target_price:
                    await self._signal_target_hit(symbol, signal, price)

                # Check for stop loss hit
                if signal_type == "BUY" and price <= stop_loss:
                    await self._signal_stop_loss_hit(symbol, signal, price)
                elif signal_type == "SELL" and price >= stop_loss:
                    await self._signal_stop_loss_hit(symbol, signal, price)

        except Exception as e:
            logger.error(f"❌ Error processing signals for {symbol}: {e}")

    async def _signal_target_hit(self, symbol: str, signal: Dict, price: float):
        """Handle signal target price hit"""
        try:
            logger.info(
                f"🎯 Target hit for {symbol} signal {signal['id']} at price {price}"
            )

            # Update signal in database
            db = None
            try:
                db = next(get_db())
                db_signal = (
                    db.query(TradeSignal).filter(TradeSignal.id == signal["id"]).first()
                )

                if db_signal:
                    db_signal.status = "TARGET_HIT"
                    db_signal.exit_price = price
                    db_signal.exit_time = datetime.now()
                    db_signal.is_active = False
                    db.commit()

                    logger.info(f"✅ Signal {signal['id']} updated: TARGET_HIT")

            except Exception as e:
                logger.error(f"❌ Database error updating signal {signal['id']}: {e}")
            finally:
                if db:
                    db.close()

        except Exception as e:
            logger.error(f"❌ Error handling target hit for {symbol}: {e}")

    async def _signal_stop_loss_hit(self, symbol: str, signal: Dict, price: float):
        """Handle signal stop loss hit"""
        try:
            logger.info(
                f"🛑 Stop loss hit for {symbol} signal {signal['id']} at price {price}"
            )

            # Update signal in database
            db = None
            try:
                db = next(get_db())
                db_signal = (
                    db.query(TradeSignal).filter(TradeSignal.id == signal["id"]).first()
                )

                if db_signal:
                    db_signal.status = "STOP_LOSS_HIT"
                    db_signal.exit_price = price
                    db_signal.exit_time = datetime.now()
                    db_signal.is_active = False
                    db.commit()

                    logger.info(f"✅ Signal {signal['id']} updated: STOP_LOSS_HIT")

            except Exception as e:
                logger.error(f"❌ Database error updating signal {signal['id']}: {e}")
            finally:
                if db:
                    db.close()

        except Exception as e:
            logger.error(f"❌ Error handling stop loss hit for {symbol}: {e}")

    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price for a symbol"""
        # Method 1: Check price history
        if symbol in self.price_history and self.price_history[symbol]:
            return self.price_history[symbol][-1]["price"]

        # Method 2: Try centralized manager
        if self.centralized_manager and symbol in self.active_stocks:
            instrument_key = self.active_stocks[symbol].get("instrument_key")
            if instrument_key:
                return self.centralized_manager.get_latest_price(instrument_key)

        return None

    async def get_engine_status(self):
        """Get status of the LiveTradingEngine"""
        try:
            # Get centralized WebSocket status if available
            centralized_status = {}
            if self.centralized_manager:
                try:
                    status = self.centralized_manager.get_status()
                    centralized_status = {
                        "available": True,
                        "connected": status.get("ws_connected", False),
                        "market_status": status.get("market_status", "unknown"),
                    }
                except Exception as e:
                    centralized_status = {"available": True, "error": str(e)}
            else:
                centralized_status = {"available": False}

            return {
                "user_id": self.user_id,
                "is_running": self.is_running,
                "active_stocks_count": len(self.active_stocks),
                "broker": (
                    self.broker_config.broker_name if self.broker_config else None
                ),
                "centralized_websocket": centralized_status,
                "active_stocks": list(self.active_stocks.keys()),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"❌ Error getting LiveTradingEngine status: {e}")
            return {"error": str(e)}

    async def stop_trading_session(self):
        """Stop the trading session"""
        try:
            logger.info(f"🛑 Stopping LiveTradingEngine for user {self.user_id}")

            # Set flag to stop processing
            self.is_running = False

            # Clean up resources
            self.active_stocks = {}
            self.price_history = {}
            self.signals = {}
            self.last_processed = {}

            logger.info(f"✅ LiveTradingEngine stopped for user {self.user_id}")
            return {"status": "success"}

        except Exception as e:
            logger.error(f"❌ Error stopping LiveTradingEngine: {e}")
            return {"status": "error", "message": str(e)}
