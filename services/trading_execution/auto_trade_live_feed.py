"""
Auto-Trading Live Feed Service (REFACTORED)
Uses shared instrument registry to avoid per-user duplication

KEY ARCHITECTURAL CHANGES:
1. Instruments stored ONCE in shared registry (not per-user)
2. User subscriptions managed separately
3. Signals broadcast to ALL subscribed users
4. Trade execution happens per-user with their capital/broker
"""

import asyncio
import json
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

from services.upstox.ws_client import UpstoxWebSocketClient
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
from services.trading_execution.shared_instrument_registry import (
    shared_registry,
    SharedInstrument
)
from router.unified_websocket_routes import broadcast_to_clients

logger = logging.getLogger("auto_trade_live_feed")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class AutoTradeLiveFeed:
    """
    Refactored Auto-Trading Live Feed Service

    Architecture:
    - COMMON LAYER: Single WebSocket, shared instruments, signal generation
    - USER LAYER: Per-user subscriptions, capital, execution, PnL tracking
    """

    def __init__(self):
        """Initialize auto-trading live feed service"""
        self.is_running = False
        self.ws_task: Optional[asyncio.Task] = None
        self.ws_client_task: Optional[asyncio.Task] = None
        self.pnl_task: Optional[asyncio.Task] = None
        self.default_trading_mode: TradingMode = TradingMode.PAPER
        self.access_token: str = ""

        # Statistics
        self.stats = {
            "signals_generated": 0,
            "trades_executed": 0,
            "positions_closed": 0,
            "errors": 0,
        }

        # WebSocket client
        self.upstox_client: Optional[UpstoxWebSocketClient] = None

        # Active user positions tracking (user_id -> {option_key -> position_data})
        self.active_user_positions: Dict[int, Dict[str, Dict[str, Any]]] = {}

        logger.info("Auto-Trading Live Feed Service (REFACTORED) initialized")

    # ============================================================================
    # PUBLIC API
    # ============================================================================

    async def start_auto_trading(
        self,
        trading_mode: TradingMode = TradingMode.PAPER
    ):
        """
        Start auto-trading with shared instrument architecture

        Args:
            trading_mode: Trading mode (PAPER or LIVE)
        """
        # If already running, just reload instruments and user subscriptions
        if self.is_running:
            logger.info("AutoTradeLiveFeed already running - reloading instruments and subscriptions")
            await self._load_instruments_and_subscriptions()

            # Update subscriptions in existing WebSocket client
            if self.upstox_client and shared_registry.instruments:
                keys_to_subscribe = shared_registry.get_all_instrument_keys()
                logger.info(f"Updating WebSocket subscriptions: {len(keys_to_subscribe)} instrument keys")
                # WebSocket client will handle re-subscription
            return

        self.is_running = True
        self.default_trading_mode = trading_mode

        # Load admin access token (common for all users)
        self.access_token = await self.load_upstox_access_token()
        if not self.access_token:
            logger.error("No Upstox access token found - aborting start")
            self.is_running = False
            return

        # Load instruments and user subscriptions
        await self._load_instruments_and_subscriptions()

        if not shared_registry.instruments:
            logger.warning("No instruments to monitor - stopping")
            self.is_running = False
            return

        # Get all unique keys to subscribe
        keys_to_subscribe = shared_registry.get_all_instrument_keys()

        logger.info(
            f"Starting auto-trade: {len(shared_registry.instruments)} instruments, "
            f"{len(shared_registry.user_subscriptions)} users, "
            f"{len(keys_to_subscribe)} subscription keys"
        )

        # Create WebSocket client
        self.upstox_client = UpstoxWebSocketClient(
            access_token=self.access_token,
            instrument_keys=keys_to_subscribe,
            callback=self._incoming_feed_callback,
            stop_callback=self._on_client_stopped,
            on_auth_error=self._on_auth_error,
            connection_type="centralized_admin",
            subscription_mode="full",
            max_retries=10,
        )

        # Start WebSocket client in background
        loop = asyncio.get_event_loop()
        self.ws_client_task = loop.create_task(
            self.upstox_client.connect_and_stream()
        )

        # Start monitoring loop
        if not self.ws_task or self.ws_task.done():
            self.ws_task = asyncio.create_task(self._ws_connection_loop())

        # Start PnL tracking using singleton tracker from pnl_tracker module
        if not self.pnl_task or self.pnl_task.done():
            from services.trading_execution.pnl_tracker import pnl_tracker
            self.pnl_task = asyncio.create_task(pnl_tracker.start_tracking())
            logger.info("Started real-time PnL tracking (using singleton tracker)")

        logger.info(f"Auto-trading started in {trading_mode.value} mode")

    async def stop(self):
        """Stop auto-trading service"""
        self.is_running = False

        # Stop WebSocket client
        try:
            if self.upstox_client:
                self.upstox_client.stop()
        except Exception:
            logger.exception("Error stopping WebSocket client")

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

        # Stop PnL tracking using singleton tracker
        if self.pnl_task:
            from services.trading_execution.pnl_tracker import pnl_tracker
            pnl_tracker.stop_tracking()
            self.pnl_task.cancel()
            try:
                await self.pnl_task
            except asyncio.CancelledError:
                pass

        logger.info("Auto-trading stopped")
        logger.info(f"Final Stats: {self.stats}")

        # Clear shared registry
        shared_registry.clear()
        self.active_user_positions.clear()
        self.upstox_client = None

    # ============================================================================
    # INSTRUMENT LOADING (COMMON LAYER)
    # ============================================================================

    async def _load_instruments_and_subscriptions(self):
        """
        Load instruments ONCE and manage user subscriptions separately

        KEY CHANGE: Instruments are NOT duplicated per user
        """
        def db_job():
            db = SessionLocal()
            try:
                # Get selected stocks for today
                stocks = (
                    db.query(SelectedStock)
                    .filter(
                        SelectedStock.selection_date == date.today(),
                        SelectedStock.is_active == True,
                        SelectedStock.option_contract.isnot(None),
                    )
                    .all()
                )

                # Get all active broker configs
                broker_configs = (
                    db.query(BrokerConfig)
                    .filter(
                        BrokerConfig.is_active == True,
                        BrokerConfig.access_token.isnot(None),
                    )
                    .all()
                )

                return stocks, broker_configs
            finally:
                db.close()

        try:
            stocks, broker_configs = await asyncio.to_thread(db_job)

            if not broker_configs:
                logger.warning("No active broker configurations found")
                return

            # Create user-broker mapping
            user_broker_map = {}
            for bc in broker_configs:
                if bc.user_id not in user_broker_map:
                    user_broker_map[bc.user_id] = bc

            logger.info(f"Found {len(user_broker_map)} users with active brokers")

            # Process each stock - register ONCE, subscribe ALL users
            for stock in stocks:
                option_data = {}
                if stock.option_contract:
                    try:
                        option_data = (
                            json.loads(stock.option_contract)
                            if isinstance(stock.option_contract, str)
                            else stock.option_contract
                        )
                    except Exception:
                        logger.exception(f"Bad option_contract for {stock.symbol}")
                        continue

                spot_key = stock.instrument_key or f"NSE_EQ|{stock.symbol}"
                option_key = option_data.get("option_instrument_key")
                if not option_key:
                    logger.warning(f"No option_instrument_key for {stock.symbol}")
                    continue

                option_type = stock.option_type or option_data.get("option_type")
                if option_type not in ("CE", "PE"):
                    logger.error(f"Invalid option_type for {stock.symbol}")
                    continue

                # REGISTER INSTRUMENT ONCE (shared across all users)
                instrument = shared_registry.register_instrument(
                    stock_symbol=stock.symbol,
                    spot_key=spot_key,
                    option_key=option_key,
                    option_type=option_type,
                    strike_price=Decimal(str(option_data.get("strike_price", 0))),
                    expiry_date=stock.option_expiry_date or option_data.get("expiry_date"),
                    lot_size=option_data.get("lot_size", 1)
                )

                # SUBSCRIBE ALL USERS to this instrument
                for user_id, broker_config in user_broker_map.items():
                    shared_registry.subscribe_user(
                        user_id=user_id,
                        option_key=option_key,
                        broker_name=broker_config.broker_name,
                        broker_config_id=broker_config.id
                    )

                logger.info(
                    f"Registered {stock.symbol} {option_type} {option_data.get('strike_price')} "
                    f"for {len(user_broker_map)} users"
                )

        except Exception:
            logger.exception("Error loading instruments and subscriptions")

    # ============================================================================
    # WEBSOCKET CONNECTION MANAGEMENT
    # ============================================================================

    async def _ws_connection_loop(self):
        """Monitor and restart WebSocket client if needed"""
        backoff = 1
        while self.is_running:
            try:
                if self.ws_client_task and self.ws_client_task.done():
                    exc = None
                    try:
                        self.ws_client_task.result()
                    except Exception as e:
                        exc = e
                    logger.warning(
                        f"WebSocket client task finished (exc={exc}), restarting in {backoff}s"
                    )

                    if not self.is_running:
                        break

                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 30)

                    # Recreate client
                    if self.access_token:
                        keys_to_subscribe = shared_registry.get_all_instrument_keys()
                        self.upstox_client = UpstoxWebSocketClient(
                            access_token=self.access_token,
                            instrument_keys=keys_to_subscribe,
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
                logger.exception("Error in WebSocket connection loop")
                await asyncio.sleep(5)

    async def _incoming_feed_callback(self, parsed: Dict[str, Any]):
        """
        Handle incoming WebSocket feed data

        Args:
            parsed: Parsed feed data from WebSocket client
        """
        try:
            if not parsed:
                return

            # Normalize feed data structure
            if parsed.get("type") == "live_feed" and "data" in parsed:
                normalized = {"feeds": parsed["data"]}
            elif "feeds" in parsed:
                normalized = parsed
            elif parsed.get("data", {}).get("feeds"):
                normalized = {"feeds": parsed["data"]["feeds"]}
            else:
                if any("|" in k for k in parsed.keys()):
                    normalized = {"feeds": parsed}
                else:
                    return

            await self._handle_market_data(normalized)

        except Exception:
            logger.exception("Error in incoming feed callback")

    async def _on_client_stopped(self):
        """WebSocket client stop callback"""
        logger.info("WebSocket client stop callback triggered")

    async def _on_auth_error(self):
        """WebSocket authentication error callback"""
        logger.warning("WebSocket authentication error - token expired")
        await self.stop()

    # ============================================================================
    # MARKET DATA PROCESSING (COMMON LAYER)
    # ============================================================================

    async def _handle_market_data(self, data: Dict):
        """
        Process market data and update shared instruments

        Args:
            data: Market data from WebSocket feed
        """
        try:
            if not data:
                return

            feeds = data.get("feeds", {})
            if not feeds:
                return

            for instrument_key, feed_data in feeds.items():
                # Update spot data (if applicable)
                await self._update_shared_spot_data(instrument_key, feed_data)

                # Update option data (if applicable)
                await self._update_shared_option_data(instrument_key, feed_data)

        except Exception:
            logger.exception("Error handling market data")

    async def _update_shared_spot_data(
        self,
        instrument_key: str,
        feed_data: Dict
    ):
        """
        Update spot price in shared registry

        Args:
            instrument_key: Instrument key from feed
            feed_data: Feed data
        """
        try:
            # Extract price data
            full_feed = feed_data.get("fullFeed", {}) or {}
            market_ff = full_feed.get("marketFF", {}) or {}
            ltpc = market_ff.get("ltpc", {}) or {}
            ohlc_data = (
                (market_ff.get("marketOHLC") or {}).get("ohlc", [])
                if market_ff
                else []
            )

            ltp = ltpc.get("ltp", 0)
            if not ltp or float(ltp) <= 0:
                return

            # Update shared registry (updates ALL instruments with this spot key)
            shared_registry.update_spot_price(
                spot_key=instrument_key,
                price=Decimal(str(ltp)),
                ohlc_data=ohlc_data
            )

            # Run strategy for instruments with sufficient historical data
            # Strategy requires: max(EMA period, SuperTrend period) + 10 = max(20, 10) + 10 = 30 candles
            for instrument in shared_registry.instruments.values():
                if instrument.spot_instrument_key == instrument_key:
                    if len(instrument.historical_spot_data["close"]) >= 30:
                        await self._run_strategy_and_broadcast(instrument)

        except Exception:
            logger.exception("Error updating shared spot data")

    async def _update_shared_option_data(
        self,
        instrument_key: str,
        feed_data: Dict
    ):
        """
        Update option data in shared registry

        Args:
            instrument_key: Instrument key from feed
            feed_data: Feed data
        """
        try:
            full_feed = feed_data.get("fullFeed", {}) or {}
            market_ff = full_feed.get("marketFF", {}) or {}
            ltpc = market_ff.get("ltpc", {}) or {}

            premium = ltpc.get("ltp", 0)
            if not premium or float(premium) <= 0:
                return

            # Extract Greeks and market data
            option_greeks_data = market_ff.get("optionGreeks", {})
            implied_vol = market_ff.get("iv")
            open_int = market_ff.get("oi")
            vol = market_ff.get("vtt")

            # Extract bid/ask
            market_level = market_ff.get("marketLevel", {})
            bid_ask_quotes = market_level.get("bidAskQuote", [])
            bid_price_val = None
            ask_price_val = None

            if bid_ask_quotes and len(bid_ask_quotes) > 0:
                first_quote = bid_ask_quotes[0]
                bid_price_val = first_quote.get("bidP")
                ask_price_val = first_quote.get("askP")

            # Prepare Greeks
            greeks = None
            if option_greeks_data and any(option_greeks_data.values()):
                greeks = {
                    "delta": float(option_greeks_data.get("delta", 0)),
                    "theta": float(option_greeks_data.get("theta", 0)),
                    "gamma": float(option_greeks_data.get("gamma", 0)),
                    "vega": float(option_greeks_data.get("vega", 0)),
                    "rho": float(option_greeks_data.get("rho", 0))
                }

            # Safely convert volume
            volume_val = None
            if vol is not None:
                try:
                    volume_val = float(vol) if isinstance(vol, (int, float)) else float(str(vol))
                except (ValueError, TypeError):
                    pass

            # Update shared registry
            shared_registry.update_option_data(
                option_key=instrument_key,
                premium=Decimal(str(premium)),
                greeks=greeks,
                implied_vol=float(implied_vol) if implied_vol else None,
                open_interest=float(open_int) if open_int else None,
                volume=volume_val,
                bid_price=float(bid_price_val) if bid_price_val else None,
                ask_price=float(ask_price_val) if ask_price_val else None
            )

            # Broadcast price update to UI
            instrument = shared_registry.get_instrument(instrument_key)
            if instrument:
                await self._broadcast_price_update(instrument)

                # Update PnL for all users with active positions in this instrument
                await self._update_positions_pnl(instrument)

        except Exception:
            logger.exception("Error updating shared option data")

    # ============================================================================
    # STRATEGY EXECUTION (COMMON LAYER - Signal Generation)
    # ============================================================================

    async def _run_strategy_and_broadcast(self, instrument: SharedInstrument):
        """
        Run strategy on shared instrument and broadcast signal to ALL subscribed users

        Args:
            instrument: Shared instrument
        """
        try:
            # Generate signal (common for all users)
            signal = strategy_engine.generate_signal(
                current_price=instrument.live_spot_price,
                historical_data=instrument.historical_spot_data,
                option_type=instrument.option_type,
            )

            instrument.last_signal = signal
            self.stats["signals_generated"] += 1
        except ValueError as e:
            # Handle insufficient data error gracefully (e.g., "Need at least 30 candles")
            if "candles" in str(e).lower():
                logger.debug(
                    f"Skipping strategy for {instrument.stock_symbol}: {e} "
                    f"(have {len(instrument.historical_spot_data.get('close', []))} candles)"
                )
                return
            else:
                raise
        except Exception:
            logger.exception(f"Error generating signal for {instrument.stock_symbol}")
            return

        try:

            # Broadcast signal to UI (even if not acted upon)
            await broadcast_to_clients("trading_signal", {
                "symbol": instrument.stock_symbol,
                "signal_type": signal.signal_type.value,
                "confidence": float(signal.confidence),
                "price": float(signal.price),
                "entry_price": float(signal.entry_price),
                "stop_loss": float(signal.stop_loss),
                "target_price": float(signal.target_price),
                "reason": signal.reason,
                "timestamp": signal.timestamp
            })

            # Check if signal is valid
            if not self._is_valid_signal(signal, instrument.option_type):
                logger.debug(
                    f"Signal {signal.signal_type.value} for {instrument.stock_symbol} did not pass validation "
                    f"(confidence: {signal.confidence}, option_type: {instrument.option_type})"
                )
                return

            logger.info(
                f"✅ Valid signal for {instrument.stock_symbol}: "
                f"{signal.signal_type.value} (Conf: {signal.confidence})"
            )

            # Get all users subscribed to this instrument
            subscribed_users = shared_registry.get_instrument_subscribers(
                instrument.option_instrument_key
            )

            if not subscribed_users:
                logger.info(f"No users currently subscribed to {instrument.stock_symbol}")
                return

            # CRITICAL FIX: Filter users based on signal type and position state
            # EXIT signals should only go to users WITH positions
            # ENTRY signals should only go to users WITHOUT positions
            eligible_users = []

            # Quick check using in-memory positions first (fast path)
            for user_id in subscribed_users:
                has_position_in_memory = (
                    user_id in self.active_user_positions
                    and instrument.option_instrument_key in self.active_user_positions[user_id]
                )

                # For critical decisions, also check database (slower but accurate)
                # This ensures correctness after service restarts
                has_position = has_position_in_memory

                # If memory says no position but this is an EXIT signal, double-check DB
                # to avoid missing positions after service restart
                if not has_position and signal.signal_type in (SignalType.EXIT_LONG, SignalType.EXIT_SHORT):
                    db = SessionLocal()
                    try:
                        db_position = (
                            db.query(ActivePosition)
                            .join(AutoTradeExecution, ActivePosition.trade_execution_id == AutoTradeExecution.id)
                            .filter(
                                AutoTradeExecution.user_id == user_id,
                                AutoTradeExecution.instrument_key == instrument.option_instrument_key,
                                ActivePosition.is_active == True
                            )
                            .first()
                        )
                        has_position = db_position is not None
                    finally:
                        db.close()

                # Check signal type vs position state
                if signal.signal_type in (SignalType.EXIT_LONG, SignalType.EXIT_SHORT):
                    # EXIT signal: only for users WITH positions
                    if has_position:
                        eligible_users.append(user_id)
                    else:
                        logger.debug(
                            f"Skipping EXIT signal for user {user_id} on {instrument.stock_symbol} - no position"
                        )
                else:
                    # ENTRY signal (BUY/SELL): only for users WITHOUT positions
                    if not has_position:
                        eligible_users.append(user_id)
                    else:
                        logger.debug(
                            f"Skipping ENTRY signal for user {user_id} on {instrument.stock_symbol} - already has position"
                        )

            if not eligible_users:
                logger.info(
                    f"No eligible users for {signal.signal_type.value} signal on {instrument.stock_symbol} "
                    f"(total subscribed: {len(subscribed_users)})"
                )
                return

            # Execute trade for EACH eligible user
            logger.info(
                f"Broadcasting {signal.signal_type.value} signal to {len(eligible_users)}/{len(subscribed_users)} users for {instrument.stock_symbol}"
            )

            for user_id in eligible_users:
                # Execute in background to avoid blocking other users
                asyncio.create_task(
                    self._execute_trade_for_user(instrument, signal, user_id)
                )

        except Exception:
            logger.exception("Error running strategy and broadcasting")

    def _is_valid_signal(self, signal: TradingSignal, option_type: str) -> bool:
        """
        Validate trading signal

        Args:
            signal: Trading signal
            option_type: Option type (CE/PE)

        Returns:
            True if signal is valid
        """
        try:
            logger.info(
                f"Validating signal: type={signal.signal_type.value}, "
                f"confidence={signal.confidence:.2f}, option_type={option_type}"
            )

            if signal.signal_type == SignalType.HOLD:
                logger.info(f"Signal rejected: HOLD signal for {option_type}")
                return False

            # Check confidence threshold (reduced from 65% to 55%)
            if Decimal(str(signal.confidence)) < Decimal("0.55"):
                logger.info(
                    f"Signal rejected: confidence {signal.confidence:.2f} < 0.55 threshold"
                )
                return False

            # CRITICAL FIX: Allow EXIT signals for closing positions
            # Exit signals: EXIT_LONG, EXIT_SHORT (valid for both CE/PE)
            if signal.signal_type in (SignalType.EXIT_LONG, SignalType.EXIT_SHORT):
                logger.info(f"Valid EXIT signal for {option_type}")
                return True

            # ENTRY signals: Both CE and PE use BUY signals
            # Reasoning: We're BUYING options (long position), not shorting
            # - BUY CE = Long Call = Bullish bet
            # - BUY PE = Long Put = Bearish bet
            # The option_type (CE/PE) determines direction, not signal type
            if signal.signal_type == SignalType.BUY:
                logger.info(f"Valid BUY signal for {option_type} option")
                return True

            # LEGACY SUPPORT: PE with SELL signal (backward compatibility)
            # Note: This should ideally be BUY for both CE and PE
            if option_type == "PE" and signal.signal_type == SignalType.SELL:
                logger.warning(
                    f"PE with SELL signal (legacy mapping) - ideally should be BUY"
                )
                return True

            # CE with SELL signal (invalid for buying calls)
            if option_type == "CE" and signal.signal_type == SignalType.SELL:
                logger.info(
                    f"Signal rejected: SELL signal not valid for CE (buying calls)"
                )
                return False

            logger.info(
                f"Signal rejected: {signal.signal_type.value} not valid for {option_type}"
            )
            return False

        except Exception as e:
            logger.exception(f"Signal validation error: {e}")
            return False

    # ============================================================================
    # TRADE EXECUTION (USER-SPECIFIC LAYER)
    # ============================================================================

    async def _execute_trade_for_user(
        self,
        instrument: SharedInstrument,
        signal: TradingSignal,
        user_id: int
    ):
        """
        Execute trade for a specific user with their capital and broker

        Args:
            instrument: Shared instrument
            signal: Trading signal
            user_id: User ID to execute trade for
        """
        logger.info(
            f"Executing trade for user {user_id}: {instrument.stock_symbol}"
        )

        # Get user metadata
        user_metadata = shared_registry.get_user_metadata(user_id)
        broker_name = user_metadata.get("broker_name")
        broker_config_id = user_metadata.get("broker_config_id")

        if not broker_name or not broker_config_id:
            logger.error(f"Missing broker info for user {user_id}")
            self.stats["errors"] += 1
            return

        db = SessionLocal()
        try:
            # Check if user has active position in both memory AND database for accuracy
            has_position_in_memory = (
                user_id in self.active_user_positions
                and instrument.option_instrument_key in self.active_user_positions[user_id]
            )

            # Check database for active position (critical for service restarts)
            db_position = (
                db.query(ActivePosition)
                .join(AutoTradeExecution, ActivePosition.trade_execution_id == AutoTradeExecution.id)
                .filter(
                    AutoTradeExecution.user_id == user_id,
                    AutoTradeExecution.instrument_key == instrument.option_instrument_key,
                    ActivePosition.is_active == True
                )
                .first()
            )

            has_position = has_position_in_memory or (db_position is not None)

            # Sync memory with database if needed
            if db_position and not has_position_in_memory:
                logger.info(
                    f"Syncing memory: Found active DB position for user {user_id}, {instrument.stock_symbol}"
                )
                if user_id not in self.active_user_positions:
                    self.active_user_positions[user_id] = {}

                # Get trade execution details
                trade = (
                    db.query(AutoTradeExecution)
                    .filter(AutoTradeExecution.id == db_position.trade_execution_id)
                    .first()
                )

                if trade:
                    self.active_user_positions[user_id][instrument.option_instrument_key] = {
                        "position_id": db_position.id,
                        "entry_price": Decimal(str(trade.entry_price)),
                        "stop_loss": Decimal(str(trade.stop_loss)) if trade.stop_loss else Decimal("0"),
                        "target": Decimal(str(trade.target_price)) if trade.target_price else Decimal("0"),
                    }
                    logger.info(f"Memory sync complete for user {user_id}")

            # CRITICAL: Handle ENTRY vs EXIT signals differently
            if signal.signal_type in (SignalType.EXIT_LONG, SignalType.EXIT_SHORT):
                # EXIT signal: Only process if position exists
                if not has_position:
                    logger.info(
                        f"⏭️ EXIT signal for {instrument.stock_symbol} but no active position for user {user_id} - skipping"
                    )
                    # Broadcast to UI that exit signal was generated but no position exists
                    await broadcast_to_clients("signal_skipped", {
                        "symbol": instrument.stock_symbol,
                        "signal_type": signal.signal_type.value,
                        "reason": "No active position to exit",
                        "user_id": user_id,
                        "timestamp": datetime.now().isoformat()
                    })
                    return
                else:
                    logger.info(
                        f"🔄 Processing EXIT signal for {instrument.stock_symbol} - closing position for user {user_id}"
                    )

                    # FIXED: Actually close the position instead of just broadcasting
                    exit_price = instrument.live_option_premium
                    exit_reason = f"SIGNAL_{signal.signal_type.value}"

                    await self._close_position_for_user(
                        user_id=user_id,
                        instrument=instrument,
                        exit_price=exit_price,
                        exit_reason=exit_reason,
                        db=db
                    )

                    logger.info(
                        f"✅ Position closed for user {user_id}: {instrument.stock_symbol} @ {exit_price}"
                    )
                    return
            else:
                # ENTRY signal (BUY/SELL): Only process if no position exists
                if has_position:
                    logger.info(
                        f"⏭️ User {user_id} already has position in {instrument.stock_symbol} - skipping entry signal"
                    )
                    await broadcast_to_clients("signal_skipped", {
                        "symbol": instrument.stock_symbol,
                        "signal_type": signal.signal_type.value,
                        "reason": "Position already exists",
                        "user_id": user_id,
                        "timestamp": datetime.now().isoformat()
                    })
                    return

                logger.info(
                    f"🎯 Processing ENTRY signal for {instrument.stock_symbol} - opening position for user {user_id}"
                )

            # Validate data availability
            current_candles = len(instrument.historical_spot_data.get("close", []))

            if instrument.live_option_premium <= 0:
                logger.error(
                    f"No premium data for {instrument.stock_symbol} "
                    f"(premium: {instrument.live_option_premium})"
                )
                self.stats["errors"] += 1
                await broadcast_to_clients("trade_error", {
                    "symbol": instrument.stock_symbol,
                    "error": "No premium data available",
                    "user_id": user_id,
                    "premium": float(instrument.live_option_premium),
                    "timestamp": datetime.now().isoformat()
                })
                return

            # Strategy requires minimum 30 candles: max(EMA 20, SuperTrend 10) + 10 = 30
            if current_candles < 30:
                logger.warning(
                    f"Insufficient historical data for {instrument.stock_symbol} "
                    f"(have {current_candles} candles, need 30 minimum for SuperTrend+EMA strategy)"
                )
                self.stats["errors"] += 1
                await broadcast_to_clients("trade_error", {
                    "symbol": instrument.stock_symbol,
                    "error": f"Insufficient historical data ({current_candles}/30 candles)",
                    "user_id": user_id,
                    "candles_available": current_candles,
                    "timestamp": datetime.now().isoformat()
                })
                return

            logger.info(
                f"Data validation passed for {instrument.stock_symbol}: "
                f"Premium={instrument.live_option_premium:.2f}, "
                f"HistData={current_candles} candles, "
                f"SpotPrice={instrument.live_spot_price:.2f}"
            )

            logger.info(
                f"Preparing trade for user {user_id}: {instrument.stock_symbol} "
                f"{instrument.option_type} {instrument.strike_price}"
            )

            # Prepare trade with user-specific capital
            prepared_trade = await trade_prep_service.prepare_trade_with_live_data(
                user_id=user_id,
                stock_symbol=instrument.stock_symbol,
                option_instrument_key=instrument.option_instrument_key,
                option_type=instrument.option_type,
                strike_price=instrument.strike_price,
                expiry_date=instrument.expiry_date,
                lot_size=instrument.lot_size,
                current_premium=instrument.live_option_premium,
                historical_data=instrument.historical_spot_data,
                db=db,
                trading_mode=self.default_trading_mode,
                broker_name=broker_name,
                option_greeks=instrument.option_greeks,
                implied_volatility=instrument.implied_volatility,
                open_interest=instrument.open_interest,
                volume=instrument.volume,
                bid_price=instrument.bid_price,
                ask_price=instrument.ask_price
            )

            prepared_status = getattr(prepared_trade, "status", None)
            prepared_status_value = getattr(prepared_status, "value", "") if prepared_status else "unknown"

            logger.info(
                f"Trade preparation result: status={prepared_status_value}, "
                f"symbol={instrument.stock_symbol}"
            )

            if prepared_status_value == "ready":
                investment = float(prepared_trade.total_investment) if hasattr(prepared_trade, 'total_investment') else 0
                logger.info(
                    f"Executing trade for user {user_id}: "
                    f"{instrument.stock_symbol} {instrument.option_type} @ {instrument.strike_price}, "
                    f"investment=Rs.{investment:,.2f}"
                )

                # Execute trade
                exec_result = await asyncio.to_thread(
                    execution_handler.execute_trade,
                    prepared_trade,
                    db,
                    None,  # parent_trade_id
                    broker_name,
                    broker_config_id,
                    investment
                )

                if getattr(exec_result, "success", False):
                    trade_id = getattr(exec_result, 'trade_id', 'unknown')
                    logger.info(
                        f"Trade executed successfully for user {user_id}: "
                        f"trade_id={trade_id}, "
                        f"symbol={instrument.stock_symbol} {instrument.option_type} {instrument.strike_price}, "
                        f"entry={instrument.live_option_premium:.2f}, "
                        f"lots={instrument.lot_size}"
                    )

                    # Track active position
                    if user_id not in self.active_user_positions:
                        self.active_user_positions[user_id] = {}

                    self.active_user_positions[user_id][instrument.option_instrument_key] = {
                        "position_id": getattr(exec_result, "active_position_id", None),
                        "entry_price": Decimal(str(getattr(exec_result, "entry_price", instrument.live_option_premium))),
                        "stop_loss": getattr(signal, "stop_loss", Decimal("0")),
                        "target": getattr(signal, "target_price", Decimal("0")),
                    }

                    self.stats["trades_executed"] += 1

                    # Broadcast to UI
                    await broadcast_to_clients("trade_executed", {
                        "trade_id": getattr(exec_result, 'trade_id', 'unknown'),
                        "symbol": instrument.stock_symbol,
                        "option_type": instrument.option_type,
                        "strike_price": float(instrument.strike_price),
                        "entry_price": float(self.active_user_positions[user_id][instrument.option_instrument_key]["entry_price"]),
                        "stop_loss": float(signal.stop_loss),
                        "target_price": float(signal.target_price),
                        "lot_size": instrument.lot_size,
                        "user_id": user_id,
                        "broker_name": broker_name,
                        "trading_mode": self.default_trading_mode.value,
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    error_msg = getattr(exec_result, 'message', 'unknown')
                    logger.error(
                        f"❌ Execution failed for user {user_id}: {error_msg}"
                    )
                    self.stats["errors"] += 1
                    await broadcast_to_clients("trade_error", {
                        "symbol": instrument.stock_symbol,
                        "error": error_msg,
                        "user_id": user_id,
                        "timestamp": datetime.now().isoformat()
                    })
            else:
                # Trade preparation failed or not ready
                metadata = getattr(prepared_trade, "metadata", {})
                error_reason = metadata.get("error", "Unknown reason")
                logger.warning(
                    f"Trade not ready for user {user_id}: "
                    f"status={prepared_status_value}, "
                    f"symbol={instrument.stock_symbol}, "
                    f"reason={error_reason}"
                )
                await broadcast_to_clients("trade_preparation_failed", {
                    "symbol": instrument.stock_symbol,
                    "status": prepared_status_value,
                    "reason": error_reason,
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat()
                })

        except Exception:
            logger.exception(f"Error executing trade for user {user_id}")
            self.stats["errors"] += 1
        finally:
            db.close()

    # ============================================================================
    # POSITION MANAGEMENT (USER-SPECIFIC LAYER)
    # ============================================================================

    async def _update_positions_pnl(self, instrument: SharedInstrument):
        """
        Update PnL for all users with active positions in this instrument

        Args:
            instrument: Shared instrument
        """
        try:
            # Get all users with active positions in this instrument
            for user_id, positions in self.active_user_positions.items():
                if instrument.option_instrument_key not in positions:
                    continue

                position_data = positions[instrument.option_instrument_key]
                position_id = position_data.get("position_id")

                if not position_id:
                    continue

                # Update PnL in database
                db = SessionLocal()
                try:
                    position = (
                        db.query(ActivePosition)
                        .filter(
                            ActivePosition.id == position_id,
                            ActivePosition.is_active == True,
                        )
                        .first()
                    )

                    if not position:
                        continue

                    current_price = instrument.live_option_premium
                    entry_price = position_data["entry_price"]

                    # Get quantity from trade execution
                    trade = (
                        db.query(AutoTradeExecution)
                        .filter(AutoTradeExecution.id == position.trade_execution_id)
                        .first()
                    )

                    if not trade:
                        continue

                    quantity = trade.quantity

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

                    # Check exit conditions
                    should_exit, reason = self._check_exit_conditions_for_user(
                        user_id,
                        instrument,
                        current_price,
                        position_data
                    )

                    if should_exit:
                        await self._close_position_for_user(
                            user_id,
                            instrument,
                            current_price,
                            reason,
                            db
                        )

                    db.commit()

                except Exception:
                    db.rollback()
                    logger.exception(f"Error updating PnL for user {user_id}")
                finally:
                    db.close()

        except Exception:
            logger.exception("Error updating positions PnL")

    def _check_exit_conditions_for_user(
        self,
        user_id: int,
        instrument: SharedInstrument,
        current_price: Decimal,
        position_data: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Check exit conditions for user position

        Args:
            user_id: User ID
            instrument: Shared instrument
            current_price: Current price
            position_data: Position data

        Returns:
            Tuple of (should_exit, exit_reason)
        """
        try:
            stop_loss = position_data.get("stop_loss", Decimal("0"))
            target = position_data.get("target", Decimal("0"))

            # Check stop loss
            if instrument.option_type == "CE":
                if current_price <= stop_loss:
                    return True, "STOP_LOSS_HIT"
            else:
                if current_price >= stop_loss:
                    return True, "STOP_LOSS_HIT"

            # Check target
            if instrument.option_type == "CE":
                if target and current_price >= target:
                    return True, "TARGET_HIT"
            else:
                if target and current_price <= target:
                    return True, "TARGET_HIT"

            # Time-based exit
            now_t = datetime.now().time()
            if (now_t.hour, now_t.minute) >= (15, 20):
                return True, "TIME_BASED_EXIT"

            return False, None

        except Exception:
            logger.exception("Error checking exit conditions")
            return False, None

    async def _close_position_for_user(
        self,
        user_id: int,
        instrument: SharedInstrument,
        exit_price: Decimal,
        exit_reason: str,
        db
    ):
        """
        Close position for specific user

        Args:
            user_id: User ID
            instrument: Shared instrument
            exit_price: Exit price
            exit_reason: Exit reason
            db: Database session
        """
        try:
            position_data = self.active_user_positions[user_id][instrument.option_instrument_key]
            position_id = position_data.get("position_id")

            position = (
                db.query(ActivePosition)
                .filter(ActivePosition.id == position_id)
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

            entry_price = position_data["entry_price"]
            quantity = trade.quantity
            pnl = (exit_price - entry_price) * Decimal(str(quantity))
            pnl_percent = (
                ((exit_price - entry_price) / entry_price * 100)
                if entry_price > 0
                else Decimal("0")
            )

            # Update trade
            trade.exit_time = datetime.now()
            trade.exit_price = float(exit_price)
            trade.exit_reason = exit_reason
            trade.net_pnl = float(pnl)
            trade.pnl_percentage = float(pnl_percent)
            trade.status = "CLOSED"

            # Deactivate position
            position.is_active = False
            position.last_updated = datetime.now()

            # Remove from active positions
            del self.active_user_positions[user_id][instrument.option_instrument_key]

            self.stats["positions_closed"] += 1
            db.commit()

            logger.info(
                f"Position closed for user {user_id}: PnL = Rs.{pnl:.2f} ({pnl_percent:.2f}%)"
            )

            # Broadcast to UI
            await broadcast_to_clients("position_closed", {
                "user_id": user_id,
                "symbol": instrument.stock_symbol,
                "exit_price": float(exit_price),
                "exit_reason": exit_reason,
                "pnl": float(pnl),
                "pnl_percent": float(pnl_percent),
                "timestamp": datetime.now().isoformat()
            })

        except Exception:
            logger.exception(f"Error closing position for user {user_id}")
            db.rollback()

    # ============================================================================
    # UI BROADCASTING
    # ============================================================================

    async def _broadcast_price_update(self, instrument: SharedInstrument):
        """
        Broadcast price update to UI for all subscribed users

        Args:
            instrument: Shared instrument
        """
        try:
            update_data = {
                "symbol": instrument.stock_symbol,
                "option_instrument_key": instrument.option_instrument_key,
                "option_type": instrument.option_type,
                "strike_price": float(instrument.strike_price),
                "live_spot_price": float(instrument.live_spot_price),
                "live_option_premium": float(instrument.live_option_premium),
                "state": instrument.state.value,
                "timestamp": datetime.now().isoformat(),
            }

            await broadcast_to_clients("selected_stock_price_update", update_data)

        except Exception:
            logger.exception("Error broadcasting price update")

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def get_live_prices(self) -> List[Dict[str, Any]]:
        """
        Get live prices for all monitored instruments

        Returns:
            List of live price data for each instrument
        """
        try:
            live_prices = []

            for option_key, instrument in shared_registry.instruments.items():
                price_data = {
                    "symbol": instrument.stock_symbol,
                    "option_instrument_key": instrument.option_instrument_key,
                    "option_type": instrument.option_type,
                    "strike_price": float(instrument.strike_price),
                    "live_spot_price": float(instrument.live_spot_price),
                    "live_option_premium": float(instrument.live_option_premium),
                    "state": instrument.state.value,
                    "last_signal": (
                        instrument.last_signal.signal_type.value
                        if instrument.last_signal
                        else None
                    ),
                    "implied_volatility": instrument.implied_volatility,
                    "open_interest": instrument.open_interest,
                    "volume": instrument.volume,
                    "bid_price": instrument.bid_price,
                    "ask_price": instrument.ask_price,
                    "last_updated": (
                        instrument.last_update_time.isoformat()
                        if instrument.last_update_time
                        else None
                    )
                }

                # Add option Greeks if available
                if instrument.option_greeks:
                    price_data["greeks"] = instrument.option_greeks

                live_prices.append(price_data)

            return live_prices

        except Exception:
            logger.exception("Error getting live prices")
            return []

    async def load_upstox_access_token(self) -> str:
        """
        Load admin Upstox access token from database

        Returns:
            Access token string
        """
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
                    logger.error("No admin Upstox access token found")
                    return ""

                token = admin_broker.access_token
                if not token or not isinstance(token, str) or len(token.strip()) < 20:
                    logger.error("Invalid token format")
                    return ""

                logger.info("Loaded Upstox access token from database")
                return token.strip()

            finally:
                try:
                    db.close()
                except Exception:
                    pass

        except Exception:
            logger.exception("Error loading Upstox access token")
            return ""

    # ============================================================================
    # PNL TRACKING (REAL-TIME)
    # ============================================================================
    # PnL tracking is handled by the singleton RealTimePnLTracker from pnl_tracker module
    # The tracker:
    # - Creates its own database sessions
    # - Monitors all active positions
    # - Calculates live PnL from market engine
    # - Updates trailing stop losses
    # - Checks exit conditions (SL/Target hit)
    # - Broadcasts updates via WebSocket
    # - Auto-closes positions when conditions met


# Singleton instance
auto_trade_live_feed = AutoTradeLiveFeed()