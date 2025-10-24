"""
Auto-Trading Live Feed Service
Robust version that uses UpstoxWebSocketClient for the feed.
- Loads admin Upstox token from DB (no user_id required)
- Subscribes only to today's SelectedStock rows with option_contract
- Routes parsed feed => _handle_market_data (keeps your strategy & execution)
"""

import asyncio
import json
import logging
from datetime import datetime, date
from decimal import Decimal
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from google.protobuf.json_format import MessageToDict

# Use your existing UpstoxWebSocketClient (the one you provided)
from services.upstox.ws_client import UpstoxWebSocketClient

# DB / models / services (unchanged)
from database.connection import SessionLocal, get_db
from database.models import (
    BrokerConfig,
    SelectedStock,
    ActivePosition,
    AutoTradeExecution,
    User,
)
from services.trading_execution.strategy_engine import (
    strategy_engine,
    SignalType,
    TradingSignal,
)
from services.trading_execution.execution_handler import execution_handler
from services.trading_execution.trade_prep import trade_prep_service, TradingMode

# broadcast helper used by original code
from router.unified_websocket_routes import broadcast_to_clients

logger = logging.getLogger("auto_trade_live_feed")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class TradeState(Enum):
    MONITORING = "monitoring"
    SIGNAL_FOUND = "signal_found"
    EXECUTING = "executing"
    POSITION_OPEN = "position_open"
    POSITION_CLOSED = "position_closed"
    ERROR = "error"


@dataclass
class AutoTradeInstrument:
    stock_symbol: str
    spot_instrument_key: str
    option_instrument_key: str
    option_type: str
    strike_price: Decimal
    expiry_date: str
    lot_size: int
    user_id: Optional[int]

    state: TradeState = TradeState.MONITORING

    live_spot_price: Decimal = Decimal("0")
    live_option_premium: Decimal = Decimal("0")
    premium_at_selection: Decimal = Decimal("0")

    historical_spot_data: Dict[str, List[float]] = field(
        default_factory=lambda: {
            "open": [],
            "high": [],
            "low": [],
            "close": [],
            "volume": [],
        }
    )

    last_signal: Optional[TradingSignal] = None
    signal_confidence_threshold: Decimal = Decimal("0.65")

    active_position_id: Optional[int] = None
    entry_price: Decimal = Decimal("0")
    current_stop_loss: Decimal = Decimal("0")
    target_price: Decimal = Decimal("0")


class AutoTradeLiveFeed:
    def __init__(self):
        self.is_running = False
        self.ws_task: Optional[asyncio.Task] = None
        self.ws_client_task: Optional[asyncio.Task] = None
        self.trading_mode: TradingMode = TradingMode.PAPER
        self.access_token: str = ""

        self.monitored_instruments: Dict[str, AutoTradeInstrument] = {}
        self.subscribed_keys: Set[str] = set()

        self.stats = {
            "signals_generated": 0,
            "trades_executed": 0,
            "positions_closed": 0,
            "errors": 0,
        }

        # Upstox client instance (created when starting)
        self.upstox_client: Optional[UpstoxWebSocketClient] = None

        logger.info("Auto-Trading Live Feed Service initialized")

    # ------------------------------
    # Public control
    # ------------------------------
    async def start_auto_trading(self, trading_mode: TradingMode = TradingMode.PAPER):
        """
        Start auto-trading using admin access token (no user_id required).
        Creates and starts UpstoxWebSocketClient in background.
        """
        if self.is_running:
            logger.warning("AutoTradeLiveFeed already running")
            return

        self.is_running = True
        self.trading_mode = trading_mode

        # Load admin token
        self.access_token = await self.load_upstox_access_token()
        if not self.access_token:
            logger.error("No Upstox access token found in DB — aborting start")
            self.is_running = False
            return

        # Load selected instruments
        await self._load_selected_instruments()

        if not self.monitored_instruments:
            logger.warning(
                "No selected instruments to monitor; stopping auto-trade start"
            )
            self.is_running = False
            return

        # Prepare keys (do not mutate original instrument storage)
        keys_to_subscribe = self._prepare_subscription_keys()
        self.subscribed_keys = set(keys_to_subscribe)

        logger.info(
            f"Starting auto-trade: {len(self.monitored_instruments)} instruments, subscribing {len(keys_to_subscribe)} keys"
        )

        # Create Upstox client and start it in background
        self.upstox_client = UpstoxWebSocketClient(
            access_token=self.access_token,
            instrument_keys=keys_to_subscribe,
            callback=self._incoming_feed_callback,  # callback receives parsed dicts from client
            stop_callback=self._on_client_stopped,
            on_auth_error=self._on_auth_error,
            connection_type="centralized_admin",
            subscription_mode="full",
            max_retries=10,
        )

        # run connect_and_stream in background
        loop = asyncio.get_event_loop()
        self.ws_client_task = loop.create_task(self.upstox_client.connect_and_stream())

        # Also run a monitoring background task to ensure client_task keeps running / restart if necessary
        if not self.ws_task or self.ws_task.done():
            self.ws_task = asyncio.create_task(self._ws_connection_loop())

    async def stop(self):
        """Stop auto-trading service and the underlying Upstox client."""
        self.is_running = False

        # Stop the upstox client if running
        try:
            if self.upstox_client:
                self.upstox_client.stop()
        except Exception:
            logger.exception("Error stopping upstox client")

        # Cancel background tasks
        if self.ws_client_task:
            self.ws_client_task.cancel()
            try:
                await self.ws_client_task
            except asyncio.CancelledError:
                pass

        if self.ws_task:
            self.ws_task.cancel()
            try:
                await self.ws_task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 Auto-trading live feed stopped")
        logger.info(f"📊 Final Stats: {self.stats}")
        self.monitored_instruments.clear()
        self.subscribed_keys.clear()
        self.upstox_client = None

    # ------------------------------
    # Background monitor to restart client if it dies unexpectedly
    # ------------------------------
    async def _ws_connection_loop(self):
        backoff = 1
        while self.is_running:
            try:
                # If client task finished (with error), attempt restart
                if self.ws_client_task and self.ws_client_task.done():
                    exc = None
                    try:
                        self.ws_client_task.result()
                    except Exception as e:
                        exc = e
                    logger.warning(
                        f"Upstox client task finished. exc={exc}; restarting in {backoff}s"
                    )
                    # recreate Upstox client with current keys
                    if not self.is_running:
                        break
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 30)
                    # recreate the client
                    if self.access_token:
                        self.upstox_client = UpstoxWebSocketClient(
                            access_token=self.access_token,
                            instrument_keys=list(self.subscribed_keys),
                            callback=self._incoming_feed_callback,
                            stop_callback=self._on_client_stopped,
                            on_auth_error=self._on_auth_error,
                            connection_type="centralized_admin",
                            subscription_mode="full",
                            max_retries=10,
                        )
                        self.ws_client_task = asyncio.create_task(
                            self.upstox_client.connect_and_stream()
                        )
                else:
                    backoff = 1
                    await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in _ws_connection_loop; will continue")
                await asyncio.sleep(5)

    # ------------------------------
    # Load instruments
    # ------------------------------
    async def _load_selected_instruments(self):
        """
        Load active SelectedStock rows for today that have option_contract.
        No user_id required (admin service).
        """

        def db_job():
            db = SessionLocal()
            try:
                return (
                    db.query(SelectedStock)
                    .filter(
                        SelectedStock.selection_date == date.today(),
                        SelectedStock.is_active == True,
                        SelectedStock.option_contract.isnot(None),
                    )
                    .all()
                )
            finally:
                db.close()

        try:
            rows = await asyncio.to_thread(db_job)
            for stock in rows:
                option_data = {}
                if stock.option_contract:
                    try:
                        option_data = (
                            json.loads(stock.option_contract)
                            if isinstance(stock.option_contract, str)
                            else stock.option_contract
                        )
                    except Exception:
                        logger.exception(
                            f"Bad option_contract JSON for {getattr(stock,'symbol', 'unknown')}; skipping"
                        )
                        continue

                spot_key = stock.instrument_key or f"NSE_EQ|{stock.symbol}"
                option_key = option_data.get("option_instrument_key")
                if not option_key:
                    logger.warning(
                        f"No option_instrument_key for {stock.symbol}; skipping"
                    )
                    continue

                option_type = stock.option_type or option_data.get("option_type")
                if option_type not in ("CE", "PE"):
                    logger.error(f"Invalid option_type for {stock.symbol}; skipping")
                    continue

                instrument = AutoTradeInstrument(
                    stock_symbol=stock.symbol,
                    spot_instrument_key=spot_key,
                    option_instrument_key=option_key,
                    option_type=option_type,
                    strike_price=Decimal(str(option_data.get("strike_price", 0))),
                    expiry_date=stock.option_expiry_date
                    or option_data.get("expiry_date"),
                    lot_size=option_data.get("lot_size", 1),
                    user_id=getattr(stock, "user_id", None),
                    premium_at_selection=Decimal(str(option_data.get("premium", 0))),
                )
                # store by option key for fast lookup in option updates
                self.monitored_instruments[option_key] = instrument
                # Also store spot key -> the same instrument for spot updates (option_key used for primary lookup)
                self.monitored_instruments.setdefault(spot_key, instrument)
                logger.info(
                    f"✅ Loaded: {stock.symbol} spot={spot_key} option={option_key}"
                )
        except Exception:
            logger.exception("Error loading selected instruments")

    def _prepare_subscription_keys(self) -> List[str]:
        """
        Return deduplicated instrument keys to subscribe.
        Use copy of keys to avoid mutating internal sets.
        """
        keys = set()
        for inst in self.monitored_instruments.values():
            # every instrument object might have been saved twice under spot and option key; ensure uniqueness
            if inst.spot_instrument_key:
                keys.add(inst.spot_instrument_key)
            if inst.option_instrument_key:
                keys.add(inst.option_instrument_key)
        # Respect Upstox limit: send max 1500 (client also truncates)
        return list(keys)

    # ------------------------------
    # Upstox client callback
    # ------------------------------
    async def _incoming_feed_callback(self, parsed: Dict[str, Any]):
        """
        This callback is passed to UpstoxWebSocketClient.
        The client already parses protobuf frames into dict via MessageToDict.
        We route the parsed dict into our _handle_market_data.
        """
        try:
            # Some messages might be in the shape {"type":"market_info", ...}
            # Our handler expects a dict with 'feeds' key (like parsed proto -> dict).
            # Normalize common shapes here:
            if not parsed:
                return

            # If client sends {"type":"live_feed", "data": { ...feeds... }} unify it
            if parsed.get("type") == "live_feed" and "data" in parsed:
                normalized = {"feeds": parsed["data"]}
            elif "feeds" in parsed:
                normalized = parsed
            elif parsed.get("data", {}).get("feeds"):
                normalized = {"feeds": parsed["data"]["feeds"]}
            else:
                # Unknown shape: still attempt to pass through if it looks like feeds map
                # sometimes older payloads might be a raw dict of instrument -> payload
                if any("|" in k for k in parsed.keys()):
                    normalized = {"feeds": parsed}
                else:
                    # ignore non-price messages here; Upstox client already handles market_info separately
                    return

            await self._handle_market_data(normalized)
        except Exception:
            logger.exception("Error in incoming feed callback")

    async def _on_client_stopped(self):
        logger.info("Upstox client stop callback triggered")

    async def _on_auth_error(self):
        logger.warning(
            "Upstox client reported auth error (token expired). Stopping auto-trade."
        )
        # stop service so operator can refresh token
        await self.stop()

    # ------------------------------
    # Market data handling (mostly unchanged logic)
    # ------------------------------
    async def _handle_market_data(self, data: Dict):
        try:
            if not data:
                return
            feeds = data.get("feeds", {})
            if not feeds:
                return

            for instrument_key, feed_data in feeds.items():
                # update spot then option (both safe)
                await self._update_spot_data(instrument_key, feed_data)
                await self._update_option_data(instrument_key, feed_data)
        except Exception:
            logger.exception("Error handling market data")

    async def _update_spot_data(self, instrument_key: str, feed_data: Dict):
        try:
            # locate instrument by matching spot_instrument_key
            instrument = None
            # faster lookup: check direct key then find any instrument with matching spot key
            inst = self.monitored_instruments.get(instrument_key)
            if inst and inst.spot_instrument_key == instrument_key:
                instrument = inst
            else:
                # fallback scan (rare)
                for i in self.monitored_instruments.values():
                    if i.spot_instrument_key == instrument_key:
                        instrument = i
                        break
            if not instrument:
                return

            full_feed = feed_data.get("fullFeed", {}) or {}
            market_ff = full_feed.get("marketFF", {}) or {}
            ltpc = market_ff.get("ltpc", {}) or {}
            ohlc_data = (
                (market_ff.get("marketOHLC") or {}).get("ohlc", []) if market_ff else []
            )

            ltp = ltpc.get("ltp", 0)
            if not ltp or float(ltp) <= 0:
                return

            instrument.live_spot_price = Decimal(str(ltp))

            # append 1-min candle if present (rolling window)
            for candle in ohlc_data:
                if candle.get("interval") == "I1":
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
                    # keep only last 50
                    for k in instrument.historical_spot_data:
                        if len(instrument.historical_spot_data[k]) > 50:
                            instrument.historical_spot_data[k] = (
                                instrument.historical_spot_data[k][-50:]
                            )
                    break

            # run strategy when we have enough history
            if len(instrument.historical_spot_data["close"]) >= 30:
                await self._run_strategy(instrument)
        except Exception:
            logger.exception("Error updating spot data")

    async def _update_option_data(self, instrument_key: str, feed_data: Dict):
        try:
            # primary lookup is by option instrument key
            instrument = self.monitored_instruments.get(instrument_key)
            if not instrument:
                return

            full_feed = feed_data.get("fullFeed", {}) or {}
            market_ff = full_feed.get("marketFF", {}) or {}
            ltpc = market_ff.get("ltpc", {}) or {}

            premium = ltpc.get("ltp", 0)
            if not premium or float(premium) <= 0:
                return

            instrument.live_option_premium = Decimal(str(premium))

            # broadcast live update
            try:
                await self._broadcast_live_price_update(instrument)
            except Exception:
                logger.exception("Broadcast failed")

            if (
                instrument.state == TradeState.POSITION_OPEN
                and instrument.active_position_id
            ):
                await self._update_position_pnl(instrument)
        except Exception:
            logger.exception("Error updating option data")

    # ------------------------------
    # Strategy / execution (kept your logic, wrapped blocking calls)
    # ------------------------------
    async def _run_strategy(self, instrument: AutoTradeInstrument):
        try:
            if instrument.state != TradeState.MONITORING:
                return

            # strategy_engine.generate_signal might be sync — run in thread if it blocks
            try:
                signal = strategy_engine.generate_signal(
                    current_price=instrument.live_spot_price,
                    historical_data=instrument.historical_spot_data,
                    option_type=instrument.option_type,
                )
            except Exception:
                signal = await asyncio.to_thread(
                    strategy_engine.generate_signal,
                    instrument.live_spot_price,
                    instrument.historical_spot_data,
                    instrument.option_type,
                )

            instrument.last_signal = signal
            self.stats["signals_generated"] += 1

            if self._is_valid_signal(signal, instrument.option_type):
                logger.info(
                    f"✅ Valid signal for {instrument.stock_symbol}: {signal.signal_type.value} (Conf: {signal.confidence})"
                )
                instrument.state = TradeState.SIGNAL_FOUND
                await self._execute_trade(instrument, signal)
        except Exception:
            logger.exception("Error running strategy")

    def _is_valid_signal(self, signal: TradingSignal, option_type: str) -> bool:
        try:
            if signal.signal_type == SignalType.HOLD:
                return False
            if option_type == "CE" and signal.signal_type not in (SignalType.BUY,):
                return False
            if option_type == "PE" and signal.signal_type not in (SignalType.SELL,):
                return False
            if Decimal(str(signal.confidence)) < Decimal("0.65"):
                return False
            return True
        except Exception:
            logger.exception("Signal validation error")
            return False

    async def _execute_trade(
        self, instrument: AutoTradeInstrument, signal: TradingSignal
    ):
        instrument.state = TradeState.EXECUTING
        logger.info(f"🚀 Executing trade for {instrument.stock_symbol}")

        # prepare_trade might be async; if blocking it will run in thread
        db = SessionLocal()
        try:
            try:
                prepared_trade = await trade_prep_service.prepare_trade(
                    user_id=1,
                    stock_symbol=instrument.stock_symbol,
                    option_instrument_key=instrument.option_instrument_key,
                    option_type=instrument.option_type,
                    strike_price=instrument.strike_price,
                    expiry_date=instrument.expiry_date,
                    lot_size=instrument.lot_size,
                    db=db,
                    trading_mode=self.trading_mode,
                )
            except Exception:
                prepared_trade = await asyncio.to_thread(
                    trade_prep_service.prepare_trade,
                    instrument.user_id,
                    instrument.stock_symbol,
                    instrument.option_instrument_key,
                    instrument.option_type,
                    instrument.strike_price,
                    instrument.expiry_date,
                    instrument.lot_size,
                    db,
                    self.trading_mode,
                )

            if (
                getattr(prepared_trade, "status", None)
                and getattr(prepared_trade.status, "value", "") == "ready"
            ):
                # execute trade in thread if blocking
                exec_result = await asyncio.to_thread(
                    execution_handler.execute_trade, prepared_trade, db
                )
                if getattr(exec_result, "success", False):
                    logger.info(
                        f"✅ Trade executed: {getattr(exec_result, 'trade_id', 'unknown')}"
                    )
                    instrument.state = TradeState.POSITION_OPEN
                    instrument.active_position_id = getattr(
                        exec_result, "active_position_id", None
                    )
                    instrument.entry_price = Decimal(
                        str(
                            getattr(
                                exec_result,
                                "entry_price",
                                instrument.live_option_premium,
                            )
                        )
                    )
                    instrument.current_stop_loss = getattr(
                        signal, "stop_loss", instrument.current_stop_loss
                    )
                    instrument.target_price = getattr(
                        signal, "target_price", instrument.target_price
                    )
                    self.stats["trades_executed"] += 1
                else:
                    logger.error(
                        f"Execution failed: {getattr(exec_result, 'message', 'unknown')}"
                    )
                    instrument.state = TradeState.ERROR
                    self.stats["errors"] += 1
            else:
                logger.warning("Prepared trade not ready; monitoring continues")
                instrument.state = TradeState.MONITORING
        except Exception:
            logger.exception("Error executing trade")
            instrument.state = TradeState.ERROR
            self.stats["errors"] += 1
        finally:
            try:
                db.close()
            except Exception:
                pass

    # ------------------------------
    # Position management (unchanged)
    # ------------------------------
    async def _update_position_pnl(self, instrument: AutoTradeInstrument):
        try:
            if not instrument.active_position_id:
                return

            def db_get_pos():
                db = SessionLocal()
                try:
                    return (
                        db.query(ActivePosition)
                        .filter(
                            ActivePosition.id == instrument.active_position_id,
                            ActivePosition.is_active == True,
                        )
                        .first()
                    )
                finally:
                    db.close()

            position = await asyncio.to_thread(db_get_pos)
            if not position:
                return

            current_price = instrument.live_option_premium
            entry_price = Decimal(str(position.entry_price))
            quantity = position.quantity

            pnl = (current_price - entry_price) * Decimal(str(quantity))
            pnl_percent = (
                ((current_price - entry_price) / entry_price * 100)
                if entry_price > 0
                else Decimal("0")
            )

            def db_update():
                db = SessionLocal()
                try:
                    p = (
                        db.query(ActivePosition)
                        .filter(ActivePosition.id == position.id)
                        .first()
                    )
                    if not p:
                        return False
                    p.current_price = float(current_price)
                    p.current_pnl = float(pnl)
                    p.current_pnl_percentage = float(pnl_percent)
                    p.last_updated = datetime.now()
                    new_sl = self._calculate_trailing_sl(
                        current_price=current_price,
                        entry_price=entry_price,
                        current_sl=instrument.current_stop_loss,
                        option_type=instrument.option_type,
                    )
                    changed = False
                    if new_sl != instrument.current_stop_loss:
                        instrument.current_stop_loss = new_sl
                        p.current_stop_loss = float(new_sl)
                        changed = True
                    db.commit()
                    return changed
                except Exception:
                    db.rollback()
                    raise
                finally:
                    db.close()

            changed = await asyncio.to_thread(db_update)
            if changed:
                logger.info(
                    f"📈 Trailing SL updated for {instrument.stock_symbol} -> {instrument.current_stop_loss}"
                )

            should_exit, reason = self._check_exit_conditions(instrument, current_price)
            if should_exit:
                db2 = SessionLocal()
                try:
                    await self._close_position(instrument, current_price, reason, db2)
                finally:
                    db2.close()
        except Exception:
            logger.exception("Error updating position PnL")

    def _calculate_trailing_sl(
        self,
        current_price: Decimal,
        entry_price: Decimal,
        current_sl: Decimal,
        option_type: str,
    ) -> Decimal:
        try:
            trailing_percent = Decimal("0.02")
            if option_type == "CE":
                if current_price > entry_price:
                    potential_sl = current_price * (Decimal("1") - trailing_percent)
                    return max(current_sl, potential_sl)
            else:
                if current_price < entry_price:
                    potential_sl = current_price * (Decimal("1") + trailing_percent)
                    return min(current_sl, potential_sl)
            return current_sl
        except Exception:
            logger.exception("Error calculating trailing SL")
            return current_sl

    def _check_exit_conditions(
        self, instrument: AutoTradeInstrument, current_price: Decimal
    ):
        try:
            if instrument.option_type == "CE":
                if current_price <= instrument.current_stop_loss:
                    return True, "STOP_LOSS_HIT"
            else:
                if current_price >= instrument.current_stop_loss:
                    return True, "STOP_LOSS_HIT"

            if instrument.option_type == "CE":
                if instrument.target_price and current_price >= instrument.target_price:
                    return True, "TARGET_HIT"
            else:
                if instrument.target_price and current_price <= instrument.target_price:
                    return True, "TARGET_HIT"

            now_t = datetime.now().time()
            if (now_t.hour, now_t.minute) >= (15, 20):
                return True, "TIME_BASED_EXIT"
            return False, None
        except Exception:
            logger.exception("Error checking exit conditions")
            return False, None

    async def _close_position(
        self, instrument: AutoTradeInstrument, exit_price: Decimal, exit_reason: str, db
    ):
        try:
            position = (
                db.query(ActivePosition)
                .filter(ActivePosition.id == instrument.active_position_id)
                .first()
            )
            if not position:
                return
            trade = (
                db.query(AutoTradeExecution)
                .filter(AutoTradeExecution.id == position.trade_execution_id)
                .first()
            )
            if not trade:
                return

            entry_price = Decimal(str(trade.entry_price))
            quantity = trade.quantity
            pnl = (exit_price - entry_price) * Decimal(str(quantity))
            pnl_percent = (
                ((exit_price - entry_price) / entry_price * 100)
                if entry_price > 0
                else Decimal("0")
            )

            trade.exit_time = datetime.now()
            trade.exit_price = float(exit_price)
            trade.exit_reason = exit_reason
            trade.net_pnl = float(pnl)
            trade.pnl_percentage = float(pnl_percent)
            trade.status = "CLOSED"

            position.is_active = False
            position.last_updated = datetime.now()

            instrument.state = TradeState.POSITION_CLOSED
            instrument.active_position_id = None

            self.stats["positions_closed"] += 1
            db.commit()
            logger.info(f"✅ Position closed: PnL = ₹{pnl:.2f} ({pnl_percent:.2f}%)")
        except Exception:
            logger.exception("Error closing position")
            try:
                db.rollback()
            except Exception:
                pass

    # ------------------------------
    # Broadcast UI updates
    # ------------------------------
    async def _broadcast_live_price_update(self, instrument: AutoTradeInstrument):
        try:
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
                            (
                                instrument.live_option_premium
                                - instrument.premium_at_selection
                            )
                            / instrument.premium_at_selection
                            * 100
                        )
                        if instrument.premium_at_selection > 0
                        else Decimal("0")
                    )

                if instrument.premium_at_selection > 0:
                    price_change = (
                        instrument.live_option_premium - instrument.premium_at_selection
                    )
                    price_change_percent = (
                        (price_change / instrument.premium_at_selection * 100)
                        if instrument.premium_at_selection > 0
                        else Decimal("0")
                    )

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

            await broadcast_to_clients("selected_stock_price_update", update_data)
        except Exception:
            logger.exception("Error broadcasting live price update")

    # ------------------------------
    # Token loader (admin token)
    # ------------------------------
    async def load_upstox_access_token(self) -> str:
        try:
            try:
                db = next(get_db())
            except Exception:
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
                    logger.error("❌ Invalid token format in database")
                    return ""
                logger.info("✅ Loaded Upstox access token from DB")
                return token.strip()
            finally:
                try:
                    db.close()
                except Exception:
                    pass
        except Exception:
            logger.exception("Error loading Upstox access token")
            return ""


# Singleton
auto_trade_live_feed = AutoTradeLiveFeed()
