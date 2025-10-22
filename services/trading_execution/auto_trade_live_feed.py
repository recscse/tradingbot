"""
Auto-Trading Live Feed Service
Simple, focused WebSocket service for auto-trading execution

This module:
1. Gets live feed ONLY for selected stocks + their ATM option instruments
2. Feeds data to strategy engine in real-time
3. Auto-executes trades based on strategy signals
4. Manages trailing stop loss
5. Tracks live PnL

Architecture:
- One dedicated WebSocket connection for auto-trading
- Subscribes ONLY to selected instruments (spot + option)
- Runs strategy on live spot data
- Calculates Greeks from option premium
- Auto-executes on valid signals
- Manages positions with trailing SL
"""

import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal
import ssl
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

import requests

from database.connection import SessionLocal, get_db
from database.models import (
    BrokerConfig,
    SelectedStock,
    ActivePosition,
    AutoTradeExecution,
    User,
)
from services.upstox.ws_client import UpstoxWebSocketClient
from services.trading_execution.strategy_engine import (
    strategy_engine,
    SignalType,
    TradingSignal,
)
from services.trading_execution.execution_handler import execution_handler
from services.trading_execution.trade_prep import trade_prep_service, TradingMode
from services.centralized_ws_manager import CentralizedWebSocketManager
import websockets
from services.upstox import MarketDataFeed_pb2 as pb
from google.protobuf.json_format import MessageToDict


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TradeState(Enum):
    """Auto-trade execution state"""

    MONITORING = "monitoring"  # Watching for signal
    SIGNAL_FOUND = "signal_found"  # Valid signal detected
    EXECUTING = "executing"  # Executing trade
    POSITION_OPEN = "position_open"  # Trade executed, managing position
    POSITION_CLOSED = "position_closed"  # Position closed
    ERROR = "error"  # Error state


@dataclass
class AutoTradeInstrument:
    """
    Instrument being monitored for auto-trading

    Attributes:
        stock_symbol: Stock symbol (e.g., "RELIANCE")
        spot_instrument_key: Spot/equity instrument key for strategy
        option_instrument_key: Option contract instrument key for trading
        option_type: CE or PE
        strike_price: Strike price
        expiry_date: Expiry date
        lot_size: Lot size
        user_id: User identifier
        state: Current trade state
        live_spot_price: Live spot price for strategy
        live_option_premium: Live option premium
        historical_spot_data: OHLC data for strategy (last 50 candles)
        last_signal: Last strategy signal
        active_position_id: Active position ID if trade executed
    """

    stock_symbol: str
    spot_instrument_key: str
    option_instrument_key: str
    option_type: str
    strike_price: Decimal
    expiry_date: str
    lot_size: int
    user_id: int

    # State tracking
    state: TradeState = TradeState.MONITORING

    # Live data
    live_spot_price: Decimal = Decimal("0")
    live_option_premium: Decimal = Decimal("0")
    premium_at_selection: Decimal = Decimal("0")  # Premium when stock was selected

    # Historical data for strategy (rolling window)
    historical_spot_data: Dict[str, List[float]] = field(
        default_factory=lambda: {
            "open": [],
            "high": [],
            "low": [],
            "close": [],
            "volume": [],
        }
    )

    # Signal tracking
    last_signal: Optional[TradingSignal] = None
    signal_confidence_threshold: Decimal = Decimal("0.65")

    # Position tracking
    active_position_id: Optional[int] = None
    entry_price: Decimal = Decimal("0")
    current_stop_loss: Decimal = Decimal("0")
    target_price: Decimal = Decimal("0")


class AutoTradeLiveFeed:
    """
    Simple auto-trading live feed service

    Manages WebSocket connection for selected stocks and executes trades
    based on real-time strategy signals
    """

    def __init__(self):
        """Initialize auto-trading live feed service"""
        self.is_running = False
        self.ws_task: Optional[asyncio.Task] = None
        self.trading_mode: TradingMode = TradingMode.PAPER  # Default to paper trading
        self.access_token: str = ""

        # Instruments being monitored
        self.monitored_instruments: Dict[str, AutoTradeInstrument] = {}

        # WebSocket subscription keys
        self.subscribed_keys: Set[str] = set()

        # Performance tracking
        self.stats = {
            "signals_generated": 0,
            "trades_executed": 0,
            "positions_closed": 0,
            "errors": 0,
        }

        logger.info("Auto-Trading Live Feed Service initialized")

    async def start_auto_trading(
        self,
        user_id: int,
        access_token: str,
        trading_mode: TradingMode = TradingMode.PAPER,
    ):
        """
        Start auto-trading for user's selected stocks

        Args:
            user_id: User identifier
            access_token: Upstox access token
            trading_mode: Paper or Live trading
        """
        try:
            self.is_running = True
            self.trading_mode = trading_mode  # Store trading mode for use in execution

            self.access_token = await self.load_upstox_access_token()

            # Step 1: Load selected stocks from database
            await self._load_selected_instruments(user_id)

            if not self.monitored_instruments:
                logger.warning(f"No selected stocks found for user {user_id}")
                return

            # Step 2: Prepare instrument keys for WebSocket subscription
            instrument_keys = self._prepare_subscription_keys()

            logger.info(
                f"🚀 Starting auto-trading for {len(self.monitored_instruments)} stocks"
            )
            logger.info(f"   Subscribing to {len(instrument_keys)} instrument keys")

            # Step 3: Start WebSocket connection
            await self.self_mananged_ws_connection()

            # Step 4: Connect and stream in background
            if not self.ws_task or self.ws_task.done():
                self.ws_task = asyncio.create_task(self._ws_connection_loop())

        except Exception as e:
            logger.error(f"Error starting auto-trading: {e}")
            self.is_running = False

    async def _ws_connection_loop(self):
        """Background WebSocket loop with automatic reconnect"""
        while self.is_running:
            try:
                await self.self_mananged_ws_connection()
            except Exception as e:
                logger.error(f"Websocket conenction error: {e}")
            logger.warning("WebSocket disconnected, retrying in 5 seconds...")
            await asyncio.sleep(5)

    async def _load_selected_instruments(self, user_id: int):
        """
        Load selected stocks from database

        Args:
            user_id: User identifier
        """
        try:
            db = SessionLocal()

            try:
                # Get today's selected stocks
                from datetime import date

                selected_stocks = (
                    db.query(SelectedStock)
                    .filter(
                        SelectedStock.selection_date == date.today(),
                        SelectedStock.is_active == True,
                        SelectedStock.option_contract.isnot(None),
                    )
                    .all()
                )

                for stock in selected_stocks:
                    # Parse option contract
                    import json

                    option_data = {}
                    if stock.option_contract:
                        try:
                            option_data = (
                                json.loads(stock.option_contract)
                                if isinstance(stock.option_contract, str)
                                else stock.option_contract
                            )
                        except:
                            continue

                    # Get spot instrument key (for strategy)
                    spot_key = stock.instrument_key or f"NSE_EQ|{stock.symbol}"

                    # Get option instrument key (for trading)
                    option_key = option_data.get("option_instrument_key")

                    if not option_key:
                        logger.warning(f"No option instrument key for {stock.symbol}")
                        continue

                    # Determine option type - CRITICAL: Never use defaults
                    option_type = stock.option_type or option_data.get("option_type")

                    if not option_type or option_type not in ["CE", "PE"]:
                        logger.error(
                            f"Invalid or missing option_type for {stock.symbol} - "
                            f"stock.option_type={stock.option_type}, "
                            f"option_data.option_type={option_data.get('option_type')} - SKIPPING"
                        )
                        continue

                    # Create auto-trade instrument
                    instrument = AutoTradeInstrument(
                        stock_symbol=stock.symbol,
                        spot_instrument_key=spot_key,
                        option_instrument_key=option_key,
                        option_type=option_type,
                        strike_price=Decimal(str(option_data.get("strike_price", 0))),
                        expiry_date=stock.option_expiry_date
                        or option_data.get("expiry_date"),
                        lot_size=option_data.get("lot_size", 1),
                        user_id=user_id,
                        premium_at_selection=Decimal(
                            str(option_data.get("premium", 0))
                        ),  # Store original premium
                    )

                    # Store by option instrument key for quick lookup
                    self.monitored_instruments[option_key] = instrument

                    logger.info(
                        f"✅ Loaded {stock.symbol} {stock.option_type} {option_data.get('strike_price')}"
                    )

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error loading selected instruments: {e}")

    async def self_mananged_ws_connection(self):
        """
        Manage WebSocket connection for auto trading

        Args:
            access_token: User access token
            instrument_keys: List of instrument keys to subscribe
        """

        try:

            access_token = self.access_token
            if not access_token:
                logger.error("No access token available for WebSocket connection")
                return
            headers = {"Authorization": f"Bearer {access_token}"}
            url = "https://api.upstox.com/v3/feed/market-data-feed/authorize"
            response = requests.get(url=url, headers=headers)

            if response.status_code != 200:
                logger.error("Failed to authorize market data feed")
                return
            websocket_url = (
                response.json().get("data", {}).get("authorized_redirect_uri")
            )
            if not websocket_url:
                logger.error("No authorized_redirect_uri in response")
                return
            instrument_keys = list(self.subscribed_keys)

            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            async with websockets.connect(websocket_url, ssl=ssl_context) as websocket:
                logger.info("WebSocket connection established")
                # Subscribe to instrument keys
                subscribe_message = {
                    "guide": "auto_trade_feed",
                    "method": "subscribe",
                    "data": {"mode": "full", "instrumentKeys": instrument_keys},
                }
                await websocket.send(json.dumps(subscribe_message).encode("utf-8"))
                logger.info(f"Subscribed to {len(instrument_keys)} instrument keys")
                while self.is_running:
                    message = await websocket.recv()
                    feed_response = pb.FeedResponse()
                    feed_response.ParseFromString(message)
                    data_dict = MessageToDict(feed_response)
                    await self._handle_market_data(data_dict)

        except Exception as e:
            logger.error(f"Error in self managed ws connection: {e}")
            return

    def _prepare_subscription_keys(self) -> List[str]:
        """
        Prepare instrument keys for WebSocket subscription

        Returns:
            List of instrument keys (spot + option for each stock)
        """
        keys = set()

        for instrument in self.monitored_instruments.values():
            # Add spot instrument (for strategy)
            keys.add(instrument.spot_instrument_key)

            # Add option instrument (for premium and Greeks)
            keys.add(instrument.option_instrument_key)

        self.subscribed_keys = keys
        return list(keys)

    async def _handle_market_data(self, data: Dict):
        """
        Handle incoming market data from WebSocket

        Args:
            data: Market data from Upstox
        """
        try:
            if not data or "feeds" not in data:
                return

            feeds = data.get("feeds", {})

            for instrument_key, feed_data in feeds.items():
                # Update spot price if this is a spot instrument
                await self._update_spot_data(instrument_key, feed_data)

                # Update option premium if this is an option instrument
                await self._update_option_data(instrument_key, feed_data)

        except Exception as e:
            logger.error(f"Error handling market data: {e}")

    async def _update_spot_data(self, instrument_key: str, feed_data: Dict):
        """
        Update spot price data for strategy

        Args:
            instrument_key: Instrument key
            feed_data: Feed data from WebSocket
        """
        try:
            # Find instrument by spot key
            instrument = None
            for inst in self.monitored_instruments.values():
                if inst.spot_instrument_key == instrument_key:
                    instrument = inst
                    break

            if not instrument:
                return

            # Extract LTPC from feed
            full_feed = feed_data.get("fullFeed", {})
            market_ff = full_feed.get("marketFF", {})
            ltpc = market_ff.get("ltpc", {})
            ohlc_data = market_ff.get("marketOHLC", {}).get("ohlc", [])

            ltp = ltpc.get("ltp", 0)
            if ltp <= 0:
                return

            # Update live spot price
            instrument.live_spot_price = Decimal(str(ltp))

            # Update historical data (for strategy indicators)
            # Find 1-minute interval OHLC
            for candle in ohlc_data:
                if candle.get("interval") == "I1":  # 1-minute interval
                    # Add to rolling window (keep last 50 candles)
                    instrument.historical_spot_data["open"].append(
                        float(candle.get("open", ltp))
                    )
                    instrument.historical_spot_data["high"].append(
                        float(candle.get("high", ltp))
                    )
                    instrument.historical_spot_data["low"].append(
                        float(candle.get("low", ltp))
                    )
                    instrument.historical_spot_data["close"].append(
                        float(candle.get("close", ltp))
                    )
                    instrument.historical_spot_data["volume"].append(
                        int(candle.get("vol", 0))
                    )

                    # Keep only last 50 candles
                    for key in instrument.historical_spot_data:
                        if len(instrument.historical_spot_data[key]) > 50:
                            instrument.historical_spot_data[key] = (
                                instrument.historical_spot_data[key][-50:]
                            )

                    break

            # Run strategy if we have enough historical data
            if len(instrument.historical_spot_data["close"]) >= 30:
                await self._run_strategy(instrument)

        except Exception as e:
            logger.error(f"Error updating spot data: {e}")

    async def _update_option_data(self, instrument_key: str, feed_data: Dict):
        """
        Update option premium data

        Args:
            instrument_key: Instrument key
            feed_data: Feed data from WebSocket
        """
        try:
            # Find instrument by option key
            instrument = self.monitored_instruments.get(instrument_key)

            if not instrument:
                return

            # Extract option premium
            full_feed = feed_data.get("fullFeed", {})
            market_ff = full_feed.get("marketFF", {})
            ltpc = market_ff.get("ltpc", {})

            premium = ltpc.get("ltp", 0)
            if premium <= 0:
                return

            # Update live option premium
            instrument.live_option_premium = Decimal(str(premium))

            # Broadcast live price update to UI
            await self._broadcast_live_price_update(instrument)

            # Update position PnL if position is open
            if (
                instrument.state == TradeState.POSITION_OPEN
                and instrument.active_position_id
            ):
                await self._update_position_pnl(instrument)

        except Exception as e:
            logger.error(f"Error updating option data: {e}")

    async def _run_strategy(self, instrument: AutoTradeInstrument):
        """
        Run strategy on live data and check for signals

        Args:
            instrument: Auto-trade instrument
        """
        try:
            # Only run strategy if monitoring (not in position)
            if instrument.state != TradeState.MONITORING:
                return

            # Generate signal using strategy engine
            signal = strategy_engine.generate_signal(
                current_price=instrument.live_spot_price,
                historical_data=instrument.historical_spot_data,
                option_type=instrument.option_type,
            )

            instrument.last_signal = signal
            self.stats["signals_generated"] += 1

            # Validate signal for auto-execution
            if self._is_valid_signal(signal, instrument.option_type):
                logger.info(
                    f"✅ Valid signal for {instrument.stock_symbol}: {signal.signal_type.value} "
                    f"(Confidence: {signal.confidence:.2f})"
                )

                instrument.state = TradeState.SIGNAL_FOUND

                # Auto-execute trade
                await self._execute_trade(instrument, signal)

        except Exception as e:
            logger.error(f"Error running strategy for {instrument.stock_symbol}: {e}")

    def _is_valid_signal(self, signal: TradingSignal, option_type: str) -> bool:
        """
        Validate if signal is ready for execution

        Args:
            signal: Trading signal
            option_type: CE or PE

        Returns:
            True if valid for execution
        """
        # Check 1: Not HOLD signal
        if signal.signal_type == SignalType.HOLD:
            return False

        # Check 2: Signal type matches option direction
        if option_type == "CE" and signal.signal_type not in [SignalType.BUY]:
            return False

        if option_type == "PE" and signal.signal_type not in [SignalType.SELL]:
            return False

        # Check 3: Confidence threshold
        if signal.confidence < Decimal("0.65"):  # 65% minimum
            return False

        return True

    async def _execute_trade(
        self, instrument: AutoTradeInstrument, signal: TradingSignal
    ):
        """
        Auto-execute trade based on signal

        Args:
            instrument: Auto-trade instrument
            signal: Trading signal
        """
        try:
            instrument.state = TradeState.EXECUTING

            logger.info(f"🚀 Executing trade for {instrument.stock_symbol}")

            db = SessionLocal()

            try:
                # Prepare trade using existing service
                prepared_trade = await trade_prep_service.prepare_trade(
                    user_id=instrument.user_id,
                    stock_symbol=instrument.stock_symbol,
                    option_instrument_key=instrument.option_instrument_key,
                    option_type=instrument.option_type,
                    strike_price=instrument.strike_price,
                    expiry_date=instrument.expiry_date,
                    lot_size=instrument.lot_size,
                    db=db,
                    trading_mode=self.trading_mode,  # Use stored trading mode
                )

                # Execute trade
                if prepared_trade.status.value == "ready":
                    execution_result = execution_handler.execute_trade(
                        prepared_trade, db
                    )

                    if execution_result.success:
                        logger.info(f"✅ Trade executed: {execution_result.trade_id}")

                        # Update instrument state
                        instrument.state = TradeState.POSITION_OPEN
                        instrument.active_position_id = (
                            execution_result.active_position_id
                        )
                        instrument.entry_price = execution_result.entry_price
                        instrument.current_stop_loss = signal.stop_loss
                        instrument.target_price = signal.target_price

                        self.stats["trades_executed"] += 1
                    else:
                        logger.error(f"Execution failed: {execution_result.message}")
                        instrument.state = TradeState.ERROR
                        self.stats["errors"] += 1
                else:
                    logger.warning(f"Trade not ready: {prepared_trade.status.value}")
                    instrument.state = TradeState.MONITORING

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            instrument.state = TradeState.ERROR
            self.stats["errors"] += 1

    async def _update_position_pnl(self, instrument: AutoTradeInstrument):
        """
        Update position PnL and check exit conditions

        Args:
            instrument: Auto-trade instrument
        """
        try:
            if not instrument.active_position_id:
                return

            db = SessionLocal()

            try:
                # Get active position
                position = (
                    db.query(ActivePosition)
                    .filter(
                        ActivePosition.id == instrument.active_position_id,
                        ActivePosition.is_active == True,
                    )
                    .first()
                )

                if not position:
                    return

                # Calculate PnL
                current_price = instrument.live_option_premium
                entry_price = Decimal(str(position.entry_price))
                quantity = position.quantity

                pnl = (current_price - entry_price) * Decimal(str(quantity))
                pnl_percent = (
                    ((current_price - entry_price) / entry_price * 100)
                    if entry_price > 0
                    else Decimal("0")
                )

                # Update position
                position.current_price = float(current_price)
                position.current_pnl = float(pnl)
                position.current_pnl_percentage = float(pnl_percent)
                position.last_updated = datetime.now()

                # Update trailing stop loss
                new_sl = self._calculate_trailing_sl(
                    current_price=current_price,
                    entry_price=entry_price,
                    current_sl=instrument.current_stop_loss,
                    option_type=instrument.option_type,
                )

                if new_sl != instrument.current_stop_loss:
                    instrument.current_stop_loss = new_sl
                    position.current_stop_loss = float(new_sl)
                    logger.info(
                        f"📈 Trailing SL updated: {instrument.stock_symbol} -> {new_sl}"
                    )

                # Check exit conditions
                should_exit, reason = self._check_exit_conditions(
                    instrument, current_price
                )

                if should_exit:
                    await self._close_position(instrument, current_price, reason, db)

                db.commit()

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error updating position PnL: {e}")

    def _calculate_trailing_sl(
        self,
        current_price: Decimal,
        entry_price: Decimal,
        current_sl: Decimal,
        option_type: str,
    ) -> Decimal:
        """
        Calculate trailing stop loss

        Args:
            current_price: Current option premium
            entry_price: Entry price
            current_sl: Current stop loss
            option_type: CE or PE

        Returns:
            Updated stop loss
        """
        try:
            # 2% trailing for options
            trailing_percent = Decimal("0.02")

            if option_type == "CE":
                # For calls, trail below current price if in profit
                if current_price > entry_price:
                    potential_sl = current_price * (Decimal("1") - trailing_percent)
                    return max(current_sl, potential_sl)
            else:
                # For puts, trail above current price if in profit
                if current_price < entry_price:
                    potential_sl = current_price * (Decimal("1") + trailing_percent)
                    return min(current_sl, potential_sl)

            return current_sl

        except Exception as e:
            logger.error(f"Error calculating trailing SL: {e}")
            return current_sl

    def _check_exit_conditions(
        self, instrument: AutoTradeInstrument, current_price: Decimal
    ) -> tuple[bool, Optional[str]]:
        """
        Check if position should be exited

        Args:
            instrument: Auto-trade instrument
            current_price: Current option premium

        Returns:
            Tuple of (should_exit, exit_reason)
        """
        try:
            # Check stop loss hit
            if instrument.option_type == "CE":
                if current_price <= instrument.current_stop_loss:
                    return True, "STOP_LOSS_HIT"
            else:
                if current_price >= instrument.current_stop_loss:
                    return True, "STOP_LOSS_HIT"

            # Check target hit
            if instrument.option_type == "CE":
                if current_price >= instrument.target_price:
                    return True, "TARGET_HIT"
            else:
                if current_price <= instrument.target_price:
                    return True, "TARGET_HIT"

            # Check time-based exit (3:20 PM)
            current_time = datetime.now().time()
            if current_time.hour >= 15 and current_time.minute >= 20:
                return True, "TIME_BASED_EXIT"

            return False, None

        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
            return False, None

    async def _close_position(
        self, instrument: AutoTradeInstrument, exit_price: Decimal, exit_reason: str, db
    ):
        """
        Close position

        Args:
            instrument: Auto-trade instrument
            exit_price: Exit price
            exit_reason: Reason for exit
            db: Database session
        """
        try:
            logger.info(
                f"🚪 Closing position: {instrument.stock_symbol} - {exit_reason}"
            )

            # Get position
            position = (
                db.query(ActivePosition)
                .filter(ActivePosition.id == instrument.active_position_id)
                .first()
            )

            if not position:
                return

            # Get trade execution
            trade = (
                db.query(AutoTradeExecution)
                .filter(AutoTradeExecution.id == position.trade_execution_id)
                .first()
            )

            if not trade:
                return

            # Calculate final PnL
            entry_price = Decimal(str(trade.entry_price))
            quantity = trade.quantity
            pnl = (exit_price - entry_price) * Decimal(str(quantity))
            pnl_percent = (
                ((exit_price - entry_price) / entry_price * 100)
                if entry_price > 0
                else Decimal("0")
            )

            # Update trade execution
            trade.exit_time = datetime.now()
            trade.exit_price = float(exit_price)
            trade.exit_reason = exit_reason
            trade.net_pnl = float(pnl)
            trade.pnl_percentage = float(pnl_percent)
            trade.status = "CLOSED"

            # Deactivate position
            position.is_active = False
            position.last_updated = datetime.now()

            # Update instrument state
            instrument.state = TradeState.POSITION_CLOSED
            instrument.active_position_id = None

            self.stats["positions_closed"] += 1

            logger.info(f"✅ Position closed: PnL = ₹{pnl:.2f} ({pnl_percent:.2f}%)")

            db.commit()

        except Exception as e:
            logger.error(f"Error closing position: {e}")
            db.rollback()

    async def check_all_positions_closed(self) -> bool:
        """
        Check if all positions are closed

        Returns:
            True if all positions closed, False otherwise
        """
        try:
            # Check if any instrument has active position
            for instrument in self.monitored_instruments.values():
                if instrument.state == TradeState.POSITION_OPEN:
                    return False

            # All positions closed
            return True

        except Exception as e:
            logger.error(f"Error checking positions: {e}")
            return False

    async def _broadcast_live_price_update(self, instrument: AutoTradeInstrument):
        """
        Broadcast live price update to WebSocket clients

        Args:
            instrument: Instrument with updated live price
        """
        try:
            # Calculate PnL based on state
            unrealized_pnl = Decimal("0")
            unrealized_pnl_percent = Decimal("0")
            price_change = Decimal("0")
            price_change_percent = Decimal("0")

            if instrument.live_option_premium > 0:
                if (
                    instrument.state == TradeState.POSITION_OPEN
                    and instrument.entry_price
                ):
                    unrealized_pnl = (
                        instrument.live_option_premium - instrument.entry_price
                    ) * instrument.lot_size
                    unrealized_pnl_percent = (
                        (
                            (instrument.live_option_premium - instrument.entry_price)
                            / instrument.entry_price
                            * 100
                        )
                        if instrument.entry_price > 0
                        else Decimal("0")
                    )
                elif instrument.premium_at_selection > 0:
                    unrealized_pnl = (
                        instrument.live_option_premium - instrument.premium_at_selection
                    ) * instrument.lot_size
                    unrealized_pnl_percent = (
                        (
                            instrument.live_option_premium
                            - instrument.premium_at_selection
                        )
                        / instrument.premium_at_selection
                        * 100
                    )

                if instrument.premium_at_selection > 0:
                    price_change = (
                        instrument.live_option_premium - instrument.premium_at_selection
                    )
                    price_change_percent = (
                        price_change / instrument.premium_at_selection * 100
                    )

            # Prepare update data
            update_data = {
                "symbol": instrument.stock_symbol,
                "option_instrument_key": instrument.option_instrument_key,
                "option_type": instrument.option_type,
                "strike_price": float(instrument.strike_price),
                "live_spot_price": float(instrument.live_spot_price),
                "live_option_premium": float(instrument.live_option_premium),
                "premium_at_selection": float(instrument.premium_at_selection),
                "price_change": float(price_change),
                "price_change_percent": float(price_change_percent),
                "unrealized_pnl": float(unrealized_pnl),
                "unrealized_pnl_percent": float(unrealized_pnl_percent),
                "state": instrument.state.value,
                "timestamp": datetime.now().isoformat(),
            }

            # Broadcast to WebSocket clients
            from router.unified_websocket_routes import broadcast_to_clients

            await broadcast_to_clients("selected_stock_price_update", update_data)

        except Exception as e:
            logger.error(f"Error broadcasting live price update: {e}")

    async def load_upstox_access_token(self) -> str:
        """
        Load the admin Upstox access token from the DB.
        Returns empty string on failure.
        """
        try:
            # get_db yields a session generator in your codebase — use next() and close properly
            try:
                db = next(get_db())
            except Exception:
                # fallback to SessionLocal if get_db generator not available
                db = SessionLocal()

            try:
                admin_broker = (
                    db.query(BrokerConfig)
                    .join(User, BrokerConfig.user_id == User.id)
                    .filter(
                        User.role == "admin",
                        BrokerConfig.broker_name.ilike("upstox"),
                        BrokerConfig.access_token.isnot(None),
                    )
                    .order_by(
                        BrokerConfig.updated_at.desc()
                        if hasattr(BrokerConfig, "updated_at")
                        else BrokerConfig.id.desc()
                    )
                    .first()
                )

                if not admin_broker:
                    logger.error("❌ No admin user with Upstox access token found!")
                    return ""

                token = admin_broker.access_token
                if not token or not isinstance(token, str) or len(token.strip()) < 20:
                    logger.error(
                        f"❌ Invalid token format in database (length: {len(token) if token else 0})"
                    )
                    return ""

                logger.info("✅ Loaded Upstox access token from DB")
                return token.strip()
            finally:
                try:
                    db.close()
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Error loading Upstox access token: {e}", exc_info=True)
            return ""

    def get_live_prices(self) -> List[Dict[str, Any]]:
        """
        Get live prices for all monitored instruments

        Returns:
            List of dictionaries with live price data
        """
        live_data = []

        for instrument in self.monitored_instruments.values():
            # Calculate unrealized PnL based on state
            unrealized_pnl = Decimal("0")
            unrealized_pnl_percent = Decimal("0")
            price_change = Decimal("0")
            price_change_percent = Decimal("0")

            if instrument.live_option_premium > 0:
                if (
                    instrument.state == TradeState.POSITION_OPEN
                    and instrument.entry_price
                ):
                    # For active positions: PnL relative to entry price
                    unrealized_pnl = (
                        instrument.live_option_premium - instrument.entry_price
                    ) * instrument.lot_size
                    unrealized_pnl_percent = (
                        (
                            (instrument.live_option_premium - instrument.entry_price)
                            / instrument.entry_price
                            * 100
                        )
                        if instrument.entry_price > 0
                        else Decimal("0")
                    )
                elif instrument.premium_at_selection > 0:
                    # For monitoring state: Show hypothetical PnL if entered at selection
                    unrealized_pnl = (
                        instrument.live_option_premium - instrument.premium_at_selection
                    ) * instrument.lot_size
                    unrealized_pnl_percent = (
                        (
                            instrument.live_option_premium
                            - instrument.premium_at_selection
                        )
                        / instrument.premium_at_selection
                        * 100
                    )

                # Calculate price change from selection
                if instrument.premium_at_selection > 0:
                    price_change = (
                        instrument.live_option_premium - instrument.premium_at_selection
                    )
                    price_change_percent = (
                        price_change / instrument.premium_at_selection * 100
                    )

            live_data.append(
                {
                    "symbol": instrument.stock_symbol,
                    "spot_instrument_key": instrument.spot_instrument_key,
                    "option_instrument_key": instrument.option_instrument_key,
                    "option_type": instrument.option_type,
                    "strike_price": float(instrument.strike_price),
                    "expiry_date": instrument.expiry_date,
                    "lot_size": instrument.lot_size,
                    "live_spot_price": float(instrument.live_spot_price),
                    "live_option_premium": float(instrument.live_option_premium),
                    "premium_at_selection": float(instrument.premium_at_selection),
                    "price_change": float(price_change),
                    "price_change_percent": float(price_change_percent),
                    "state": instrument.state.value,
                    "active_position_id": instrument.active_position_id,
                    "unrealized_pnl": float(unrealized_pnl),
                    "unrealized_pnl_percent": float(unrealized_pnl_percent),
                    "last_updated": datetime.now().isoformat(),
                }
            )

        return live_data

    async def stop(self):
        """Stop auto-trading service"""
        self.is_running = False

        if self.ws_task:
            self.ws_task.cancel()
            try:
                await self.ws_task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 Auto-trading live feed stopped")
        logger.info(f"📊 Final Stats: {self.stats}")

        # Clear monitored instruments
        self.monitored_instruments.clear()
        self.subscribed_keys.clear()


# Singleton instance
auto_trade_live_feed = AutoTradeLiveFeed()
