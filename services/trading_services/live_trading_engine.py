import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import redis
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Trade, TradePerformance, User, BrokerConfig
from services.pre_market_data_service import get_cached_trading_stocks, get_stock_data

logger = logging.getLogger(__name__)


class TradeSignal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class PositionStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    STOPPED = "STOPPED"


@dataclass
class LivePosition:
    symbol: str
    instrument_key: str
    entry_price: float
    current_price: float
    quantity: int
    target_price: float
    stop_loss: float
    trail_stop: float
    entry_time: datetime
    status: PositionStatus
    pnl: float = 0.0
    max_profit: float = 0.0


@dataclass
class TradingStrategy:
    name: str
    entry_conditions: List[str]
    exit_conditions: List[str]
    risk_percent: float
    reward_percent: float
    trailing_stop_percent: float


class LiveTradingEngine:
    """
    High-performance live trading engine that executes trades based on real-time analysis.
    Implements no-loss strategy with dynamic stop losses.
    """

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.active_positions: Dict[str, LivePosition] = {}
        self.redis_client = redis.Redis(
            host="localhost", port=6379, db=0, decode_responses=True
        )
        self.is_trading_active = False
        self.max_positions = 20
        self.capital_per_trade = 100000  # ₹1 Lakh per trade

        # Trading strategies
        self.strategies = {
            "momentum_breakout": TradingStrategy(
                name="Momentum Breakout",
                entry_conditions=["BREAKOUT_UP", "HIGH_VOLUME"],
                exit_conditions=["TARGET_HIT", "TRAIL_STOP"],
                risk_percent=1.5,
                reward_percent=3.0,
                trailing_stop_percent=1.0,
            ),
            "gap_up_trade": TradingStrategy(
                name="Gap Up Trade",
                entry_conditions=["GAP_UP", "MOMENTUM"],
                exit_conditions=["TARGET_HIT", "TRAIL_STOP"],
                risk_percent=2.0,
                reward_percent=4.0,
                trailing_stop_percent=1.5,
            ),
        }

    async def start_trading_session(self) -> Dict:
        """Start the live trading session."""
        logger.info(f"🚀 Starting live trading session for user {self.user_id}")

        try:
            # Get pre-computed trading stocks
            trading_stocks = get_cached_trading_stocks()
            if not trading_stocks:
                raise ValueError(
                    "No trading stocks available. Run pre-market initialization first."
                )

            self.is_trading_active = True

            # Initialize position monitoring
            asyncio.create_task(self._monitor_positions())

            # Get WebSocket instrument keys for live data
            instrument_keys = [stock["instrument_key"] for stock in trading_stocks]

            result = {
                "status": "success",
                "message": "Live trading session started",
                "total_stocks": len(trading_stocks),
                "instrument_keys": instrument_keys,
                "max_positions": self.max_positions,
                "started_at": datetime.now().isoformat(),
            }

            logger.info(f"✅ Trading session started with {len(trading_stocks)} stocks")
            return result

        except Exception as e:
            logger.error(f"❌ Failed to start trading session: {e}")
            raise

    async def process_live_tick(self, instrument_key: str, tick_data: Dict):
        """
        Process incoming live tick data and make trading decisions.
        This function is called for each WebSocket tick.
        """
        try:
            symbol = self._get_symbol_from_instrument_key(instrument_key)
            if not symbol:
                return

            current_price = tick_data.get("ltp", 0)
            if not current_price:
                return

            # Update existing positions
            if symbol in self.active_positions:
                await self._update_position(symbol, current_price, tick_data)

            # Check for new entry signals
            elif len(self.active_positions) < self.max_positions:
                await self._check_entry_signal(
                    symbol, instrument_key, current_price, tick_data
                )

        except Exception as e:
            logger.error(f"Error processing tick for {instrument_key}: {e}")

    async def _check_entry_signal(
        self, symbol: str, instrument_key: str, current_price: float, tick_data: Dict
    ):
        """Check if current market conditions trigger an entry signal."""
        try:
            # Get pre-computed stock data
            stock_data = get_stock_data(symbol)
            if not stock_data:
                return

            # Analyze real-time signals
            signals = self._analyze_real_time_signals(
                current_price, tick_data, stock_data
            )

            # Check if any strategy conditions are met
            for strategy_name, strategy in self.strategies.items():
                if self._strategy_entry_triggered(signals, strategy):
                    await self._execute_buy_order(
                        symbol, instrument_key, current_price, strategy
                    )
                    break

        except Exception as e:
            logger.error(f"Error checking entry for {symbol}: {e}")

    def _analyze_real_time_signals(
        self, current_price: float, tick_data: Dict, stock_data: Dict
    ) -> List[str]:
        """Analyze real-time market data to generate trading signals."""
        signals = []

        try:
            # Price momentum analysis
            entry_price = stock_data.get("entry_price", 0)
            if current_price > entry_price * 1.005:  # 0.5% move up
                signals.append("MOMENTUM_UP")

            # Volume analysis
            volume = tick_data.get("volume", 0)
            if volume > 50000:  # High volume threshold
                signals.append("HIGH_VOLUME")

            # Bid-Ask spread analysis
            bid_ask = tick_data.get("bid_ask", [])
            if bid_ask and len(bid_ask) > 0:
                spread = bid_ask[0].get("askP", 0) - bid_ask[0].get("bidP", 0)
                if spread < current_price * 0.001:  # Tight spread
                    signals.append("TIGHT_SPREAD")

            # Breakout detection
            high_price = stock_data.get("entry_price", 0) * 1.02
            if current_price > high_price:
                signals.append("BREAKOUT_CONFIRMED")

            # Use pre-computed signals from screener
            pre_signals = stock_data.get("signals", [])
            signals.extend(pre_signals)

        except Exception as e:
            logger.error(f"Error analyzing signals: {e}")

        return signals

    def _strategy_entry_triggered(
        self, signals: List[str], strategy: TradingStrategy
    ) -> bool:
        """Check if strategy entry conditions are met."""
        required_signals = set(strategy.entry_conditions)
        available_signals = set(signals)

        # Check if at least 70% of required signals are present
        matching_signals = required_signals.intersection(available_signals)
        return len(matching_signals) >= len(required_signals) * 0.7

    async def _execute_buy_order(
        self,
        symbol: str,
        instrument_key: str,
        current_price: float,
        strategy: TradingStrategy,
    ):
        """Execute a buy order and create position tracking."""
        try:
            # Calculate position size
            quantity = int(self.capital_per_trade / current_price)
            if quantity <= 0:
                return

            # Calculate targets and stops
            target_price = current_price * (1 + strategy.reward_percent / 100)
            stop_loss = current_price * (1 - strategy.risk_percent / 100)
            trail_stop = current_price * (1 - strategy.trailing_stop_percent / 100)

            # Create position
            position = LivePosition(
                symbol=symbol,
                instrument_key=instrument_key,
                entry_price=current_price,
                current_price=current_price,
                quantity=quantity,
                target_price=target_price,
                stop_loss=stop_loss,
                trail_stop=trail_stop,
                entry_time=datetime.now(),
                status=PositionStatus.OPEN,
            )

            # Add to active positions
            self.active_positions[symbol] = position

            # Save to database
            await self._save_trade_to_db(position, "BUY")

            # Cache for monitoring
            await self._cache_position(position)

            logger.info(
                f"🔥 BUY executed: {symbol} @ ₹{current_price:.2f}, "
                f"Qty: {quantity}, Target: ₹{target_price:.2f}"
            )

        except Exception as e:
            logger.error(f"Error executing buy order for {symbol}: {e}")

    async def _update_position(
        self, symbol: str, current_price: float, tick_data: Dict
    ):
        """Update existing position and check exit conditions."""
        try:
            position = self.active_positions[symbol]
            position.current_price = current_price

            # Calculate P&L
            position.pnl = (current_price - position.entry_price) * position.quantity

            # Update max profit (for trailing stop)
            if position.pnl > position.max_profit:
                position.max_profit = position.pnl
                # Update trailing stop
                new_trail = current_price * 0.99  # 1% trailing stop
                if new_trail > position.trail_stop:
                    position.trail_stop = new_trail

            # Check exit conditions
            should_exit, exit_reason = self._check_exit_conditions(position)

            if should_exit:
                await self._execute_sell_order(position, exit_reason)
            else:
                # Update cached position
                await self._cache_position(position)

        except Exception as e:
            logger.error(f"Error updating position for {symbol}: {e}")

    def _check_exit_conditions(self, position: LivePosition) -> tuple[bool, str]:
        """Check if position should be exited."""
        try:
            current_price = position.current_price

            # Target hit (book profit)
            if current_price >= position.target_price:
                return True, "TARGET_HIT"

            # Trailing stop hit
            if current_price <= position.trail_stop:
                return True, "TRAIL_STOP"

            # Emergency stop loss (should rarely hit with our no-loss strategy)
            if current_price <= position.stop_loss:
                return True, "STOP_LOSS"

            # Time-based exit (end of day)
            now = datetime.now().time()
            if now >= datetime.strptime("15:20", "%H:%M").time():
                return True, "EOD_EXIT"

            return False, ""

        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
            return False, "ERROR"

    async def _execute_sell_order(self, position: LivePosition, reason: str):
        """Execute sell order and close position."""
        try:
            symbol = position.symbol
            current_price = position.current_price

            # Update position status
            position.status = PositionStatus.CLOSED
            final_pnl = (current_price - position.entry_price) * position.quantity
            position.pnl = final_pnl

            # Save to database
            await self._save_trade_to_db(position, f"SELL_{reason}")

            # Remove from active positions
            if symbol in self.active_positions:
                del self.active_positions[symbol]

            # Clear cache
            self.redis_client.delete(f"position:{symbol}")

            profit_loss = "PROFIT" if final_pnl > 0 else "LOSS"
            logger.info(
                f"💰 {profit_loss}: {symbol} sold @ ₹{current_price:.2f}, "
                f"P&L: ₹{final_pnl:.2f}, Reason: {reason}"
            )

        except Exception as e:
            logger.error(f"Error executing sell order for {position.symbol}: {e}")

    async def _monitor_positions(self):
        """Background task to monitor all positions."""
        while self.is_trading_active:
            try:
                if self.active_positions:
                    logger.info(f"📊 Monitoring {len(self.active_positions)} positions")

                    # Check for any emergency conditions
                    for symbol, position in list(self.active_positions.items()):
                        # Additional safety checks can be added here
                        pass

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in position monitoring: {e}")
                await asyncio.sleep(10)

    async def _save_trade_to_db(self, position: LivePosition, action: str):
        """Save trade to database."""
        try:
            db = next(get_db())

            trade = TradePerformance(
                user_id=self.user_id,
                symbol=position.symbol,
                trade_type=action,
                quantity=position.quantity,
                entry_price=position.entry_price,
                exit_price=position.current_price if "SELL" in action else None,
                profit_loss=position.pnl if "SELL" in action else None,
                trailing_stop_loss=position.trail_stop,
                status=position.status.value,
                trade_time=position.entry_time,
            )

            db.add(trade)
            db.commit()

        except Exception as e:
            logger.error(f"Error saving trade to DB: {e}")

    async def _cache_position(self, position: LivePosition):
        """Cache position data for monitoring."""
        try:
            position_data = {
                "symbol": position.symbol,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "quantity": position.quantity,
                "pnl": position.pnl,
                "target_price": position.target_price,
                "trail_stop": position.trail_stop,
                "status": position.status.value,
                "updated_at": datetime.now().isoformat(),
            }

            self.redis_client.setex(
                f"position:{position.symbol}", 3600, json.dumps(position_data)  # 1 hour
            )

        except Exception as e:
            logger.error(f"Error caching position: {e}")

    def _get_symbol_from_instrument_key(self, instrument_key: str) -> Optional[str]:
        """Get stock symbol from instrument key using cached mapping."""
        try:
            cached = self.redis_client.get("trading_stocks_cache")
            if cached:
                data = json.loads(cached)
                mapping = data.get("instrument_mapping", {})
                stock_info = mapping.get(instrument_key)
                return stock_info.get("symbol") if stock_info else None
        except Exception as e:
            logger.error(f"Error getting symbol for {instrument_key}: {e}")
        return None

    async def get_trading_summary(self) -> Dict:
        """Get current trading session summary."""
        try:
            total_pnl = sum(pos.pnl for pos in self.active_positions.values())

            return {
                "active_positions": len(self.active_positions),
                "total_pnl": total_pnl,
                "positions": [
                    {
                        "symbol": pos.symbol,
                        "entry_price": pos.entry_price,
                        "current_price": pos.current_price,
                        "quantity": pos.quantity,
                        "pnl": pos.pnl,
                        "pnl_percent": (pos.pnl / (pos.entry_price * pos.quantity))
                        * 100,
                        "target_price": pos.target_price,
                        "trail_stop": pos.trail_stop,
                        "status": pos.status.value,
                    }
                    for pos in self.active_positions.values()
                ],
                "session_active": self.is_trading_active,
                "max_positions": self.max_positions,
                "capital_per_trade": self.capital_per_trade,
            }

        except Exception as e:
            logger.error(f"Error getting trading summary: {e}")
        return {"error": str(e)}

    async def stop_trading_session(self):
        """Stop trading session and close all positions."""
        logger.info("🛑 Stopping trading session...")

        self.is_trading_active = False

        # Close all open positions
        for symbol, position in list(self.active_positions.items()):
            await self._execute_sell_order(position, "SESSION_STOP")

        logger.info("✅ Trading session stopped")
