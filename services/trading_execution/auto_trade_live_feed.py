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

from sqlalchemy.orm import Session

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
    SharedInstrument,
)
from router.unified_websocket_routes import broadcast_to_clients
from services.notifications.telegram_service import telegram_notifier
from utils.market_hours import is_market_open
from utils.timezone_utils import get_ist_now_naive, get_ist_isoformat
from utils.logging_utils import (
    log_signal_generation,
    log_trade_attempt,
    log_trade_result,
    generate_trace_id,
    log_structured,
    log_to_db,
)

logger = logging.getLogger("auto_trade_live_feed")
# Removed basicConfig to avoid overriding global settings


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
        self.last_error: Optional[str] = None

        # Statistics
        self.stats = {
            "signals_generated": 0,
            "trades_executed": 0,
            "positions_closed": 0,
            "errors": 0,
            "last_signal_time": None,
            "last_trade_time": None,
            "last_error_time": None
        }

        # Detailed Error Tracking
        self.service_errors = {
            "websocket": None,
            "strategy": None,
            "execution": None,
            "registry": None
        }

        # WebSocket client
        self.upstox_client: Optional[UpstoxWebSocketClient] = None
        
        # Data flow tracking
        self.tick_counter = 0
        self.last_tick_time: Optional[datetime] = None

        # Active user positions tracking (user_id -> {option_key -> position_data})
        self.active_user_positions: Dict[int, Dict[str, Dict[str, Any]]] = {}

        # Cooldown tracking (user_id -> {stock_symbol -> last_exit_time})
        self.user_last_exit_times: Dict[int, Dict[str, datetime]] = {}

        logger.info("Auto-Trading Live Feed Service (REFACTORED) initialized")

    def _set_service_error(self, component: str, error: str):
        """Set component-specific error and update global stats"""
        self.service_errors[component] = {
            "error": error,
            "timestamp": get_ist_isoformat()
        }
        self.stats["errors"] += 1
        self.stats["last_error_time"] = get_ist_isoformat()
        self.last_error = f"[{component}] {error}"

    # ============================================================================
    # PUBLIC API
    # ============================================================================

    async def start_auto_trading(self, trading_mode: TradingMode = TradingMode.PAPER):
        """
        Start auto-trading with shared instrument architecture

        Args:
            trading_mode: Trading mode (PAPER or LIVE)
        """
        try:
            # If already running, just reload instruments and user subscriptions
            if self.is_running:
                logger.info(
                    "AutoTradeLiveFeed already running - reloading instruments and subscriptions"
                )
                await self._load_instruments_and_subscriptions()

                # Update subscriptions in existing WebSocket client
                if self.upstox_client and shared_registry.instruments:
                    keys_to_subscribe = shared_registry.get_all_instrument_keys()
                    logger.info(
                        f"Updating WebSocket subscriptions: {len(keys_to_subscribe)} instrument keys"
                    )
                    # WebSocket client will handle re-subscription
                return

            self.is_running = True
            self.default_trading_mode = trading_mode
            self.last_error = None
            self.service_errors = {k: None for k in self.service_errors} # Reset errors

            # Load admin access token (common for all users)
            self.access_token = await self.load_upstox_access_token()
            if not self.access_token:
                logger.error("No Upstox access token found - aborting start")
                self.is_running = False
                self._set_service_error("websocket", "No access token found")
                return

            # Load instruments and user subscriptions
            await self._load_instruments_and_subscriptions()

            if not shared_registry.instruments:
                logger.warning("No instruments to monitor - stopping")
                self.is_running = False
                self._set_service_error("registry", "No instruments to monitor")
                log_to_db(
                    component="auto_trade_live_feed",
                    message="Startup FAILED: No instruments to monitor",
                    level="ERROR"
                )
                return

            # Get all unique keys to subscribe
            keys_to_subscribe = shared_registry.get_all_instrument_keys()

            logger.info(
                f"Starting auto-trade: {len(shared_registry.instruments)} instruments, "
                f"{len(shared_registry.user_subscriptions)} users, "
                f"{len(keys_to_subscribe)} subscription keys"
            )

            log_to_db(
                component="auto_trade_live_feed",
                message=f"Live feed STARTING: {len(shared_registry.instruments)} instruments monitored",
                level="INFO",
                additional_data={
                    "instruments": len(shared_registry.instruments),
                    "users": len(shared_registry.user_subscriptions),
                    "trading_mode": trading_mode.value
                }
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

            # Load active positions from database into memory for exit signal eligibility
            await self._sync_active_positions_from_db()
            logger.info(f"Synced active positions from database into memory")

            logger.info(f"Auto-trading started in {trading_mode.value} mode")
            
            # Send Telegram Alert
            asyncio.create_task(telegram_notifier.send_system_alert(
                "AutoTradeLiveFeed", 
                f"Auto-trading STARTED in {trading_mode.value} mode with {len(shared_registry.instruments)} instruments",
                level="INFO"
            ))
        except Exception as e:
            self.is_running = False
            self._set_service_error("execution", str(e))
            logger.error(f"Error starting auto-trading: {e}")
            
            # Send Telegram Error
            asyncio.create_task(telegram_notifier.send_system_alert(
                "AutoTradeLiveFeed", 
                f"CRITICAL STARTUP ERROR: {str(e)}",
                level="ERROR"
            ))
            
            log_to_db(
                component="auto_trade_live_feed",
                message=f"CRITICAL STARTUP ERROR: {str(e)}",
                level="ERROR"
            )
            
            import traceback

            logger.error(traceback.format_exc())

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

        log_to_db(
            component="auto_trade_live_feed",
            message="Live feed STOPPED",
            level="INFO",
            additional_data=self.stats
        )

        logger.info("Auto-trading stopped")
        logger.info(f"Final Stats: {self.stats}")

        # Clear shared registry
        shared_registry.clear()
        self.active_user_positions.clear()
        self.upstox_client = None

    def get_status(self) -> Dict[str, Any]:
        """Get auto-trading service status for system health dashboard"""
        # Determine service health from errors
        service_status = "healthy"
        critical_errors = [e for k, e in self.service_errors.items() if e is not None]
        if critical_errors:
            service_status = "error" if self.is_running else "degraded"

        return {
            "status": service_status,
            "is_running": self.is_running,
            "websocket_connected": (
                self.upstox_client.is_connected() if self.upstox_client else False
            ),
            "trading_mode": (
                self.default_trading_mode.value
                if hasattr(self.default_trading_mode, "value")
                else str(self.default_trading_mode)
            ),
            "stats": self.stats,
            "service_errors": self.service_errors,
            "active_users": len(self.active_user_positions),
            "instruments_tracked": len(shared_registry.instruments),
            "last_error": getattr(self, "last_error", None),
            "last_tick_time": self.last_tick_time.isoformat() if self.last_tick_time else None,
            "tick_counter": self.tick_counter,
            "timestamp": get_ist_isoformat(),
        }

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
                        SelectedStock.selection_date == get_ist_now_naive().date(),
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

            if not stocks:
                logger.warning(
                    f"No selected stocks found for today ({get_ist_now_naive().date()})"
                )
                logger.info(
                    "HINT: Has the 'Intelligent Stock Selection' service run for today? Check 'selected_stocks' table."
                )
                # Don't return yet, we might want to see broker configs or retry?
                # Actually if no stocks, we can't do anything.
                return

            if not broker_configs:
                logger.warning("No active broker configurations found")
                return

            # Create user-broker mapping
            user_broker_map = {}
            for bc in broker_configs:
                if bc.user_id not in user_broker_map:
                    user_broker_map[bc.user_id] = bc

            logger.info(f"Found {len(user_broker_map)} users with active brokers")
            
            log_to_db(
                component="auto_trade_live_feed",
                message=f"Loading instruments: Found {len(stocks)} stocks and {len(user_broker_map)} active users",
                level="DEBUG"
            )

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

                # EXTRACT POSITION SIZE (LOTS) from enhanced metadata if available
                target_lots = 1
                try:
                    if stock.score_breakdown:
                        if isinstance(stock.score_breakdown, str):
                            try:
                                metadata = json.loads(stock.score_breakdown)
                            except json.JSONDecodeError:
                                # Fallback for single-quoted string dicts
                                import ast
                                metadata = ast.literal_eval(stock.score_breakdown)
                        else:
                            metadata = stock.score_breakdown
                            
                        target_lots = int(metadata.get("position_size_lots", 1))
                except Exception as e:
                    logger.error(f"Error extracting position_size_lots: {e}")
                    logger.warning(f"Could not extract target_lots for {stock.symbol}")

                # REGISTER INSTRUMENT ONCE (shared across all users)
                instrument = shared_registry.register_instrument(
                    stock_symbol=stock.symbol,
                    spot_key=spot_key,
                    option_key=option_key,
                    option_type=option_type,
                    strike_price=Decimal(str(option_data.get("strike_price", 0))),
                    expiry_date=stock.option_expiry_date
                    or option_data.get("expiry_date"),
                    lot_size=option_data.get("lot_size", 1),
                    target_lots=target_lots,
                )

                # SUBSCRIBE ALL USERS to this instrument
                for user_id, broker_config in user_broker_map.items():
                    shared_registry.subscribe_user(
                        user_id=user_id,
                        option_key=option_key,
                        broker_name=broker_config.broker_name,
                        broker_config_id=broker_config.id,
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
        market_close_notified = False
        heartbeat_counter = 0

        while self.is_running:
            try:
                # Heartbeat every 15 minutes
                heartbeat_counter += 1
                if heartbeat_counter >= 180: # 180 * 5s = 900s = 15m
                    logger.info(f"💓 Auto-Trade Live Feed Heartbeat: Monitoring loop active at {get_ist_now_naive().strftime('%H:%M:%S')} IST")
                    heartbeat_counter = 0

                # CRITICAL: Check if market is open
                if not is_market_open():
                    if not market_close_notified:
                        logger.info(
                            "Market is closed - auto-trading WebSocket will pause until market opens"
                        )
                        market_close_notified = True

                        # Broadcast market closed status
                        await broadcast_to_clients(
                            "market_status_update",
                            {
                                "status": "closed",
                                "message": "Market is closed - auto-trading paused",
                                "timestamp": get_ist_isoformat(),
                            },
                        )

                    # Sleep for 60 seconds and check again
                    await asyncio.sleep(60)
                    continue
                else:
                    # Market is open
                    if market_close_notified:
                        logger.info("Market is open - resuming auto-trading WebSocket")
                        market_close_notified = False

                        await broadcast_to_clients(
                            "market_status_update",
                            {
                                "status": "open",
                                "message": "Market is open - auto-trading active",
                                "timestamp": get_ist_isoformat(),
                            },
                        )

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

            # DEBUG LOGGING (Selective)
            feeds = normalized.get("feeds", {})
            if feeds:
                sample_key = next(iter(feeds))
                logger.debug(
                    f"📥 Received feed for {len(feeds)} instruments (Sample: {sample_key})"
                )

                # Check if any of our monitored instruments are in this tick
                monitored_keys = shared_registry.get_all_instrument_keys()
                found_monitored = [k for k in feeds if k in monitored_keys]
                if found_monitored:
                    logger.info(
                        f"🎯 Received data for {len(found_monitored)} monitored instruments: {found_monitored[:3]}"
                    )

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
            
            # Increment tick counter for heartbeat
            self.tick_counter += 1
            self.last_tick_time = get_ist_now_naive()
            
            # Periodically log heartbeat (every 500 ticks)
            if self.tick_counter % 500 == 0:
                logger.info(f"💓 Live Data Heartbeat: Received {self.tick_counter} ticks so far. Last tick at {self.last_tick_time.strftime('%H:%M:%S')}")

            for instrument_key, feed_data in feeds.items():
                # Update spot data (if applicable)
                await self._update_shared_spot_data(instrument_key, feed_data)

                # Update option data (if applicable)
                await self._update_shared_option_data(instrument_key, feed_data)

        except Exception:
            logger.exception("Error handling market data")

    async def _update_shared_spot_data(self, instrument_key: str, feed_data: Dict):
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
                (market_ff.get("marketOHLC") or {}).get("ohlc", []) if market_ff else []
            )

            ltp = ltpc.get("ltp", 0)
            if not ltp or float(ltp) <= 0:
                return

            # Update shared registry (updates ALL instruments with this spot key)
            shared_registry.update_spot_price(
                spot_key=instrument_key, price=Decimal(str(ltp)), ohlc_data=ohlc_data
            )

            # Run strategy for instruments with sufficient historical data
            # Strategy requires: max(EMA period, SuperTrend period) + 10 = max(20, 10) + 10 = 30 candles
            for instrument in shared_registry.instruments.values():
                if instrument.spot_instrument_key == instrument_key:
                    if len(instrument.historical_spot_data["close"]) >= 30:
                        await self._run_strategy_and_broadcast(instrument)

        except Exception:
            logger.exception("Error updating shared spot data")

    async def _update_shared_option_data(self, instrument_key: str, feed_data: Dict):
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
            # CRITICAL FIX: IV is a direct field of marketFF, NOT inside optionGreeks
            # Confirmed via MarketDataFeed.proto (MarketFullFeed field 8 is iv)
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

            # Prepare Greeks with enhanced validation
            greeks = None
            if option_greeks_data and any(option_greeks_data.values()):
                try:
                    # CRITICAL FIX: Validate Greeks before using them
                    delta_val = option_greeks_data.get("delta", 0)
                    theta_val = option_greeks_data.get("theta", 0)
                    gamma_val = option_greeks_data.get("gamma", 0)
                    vega_val = option_greeks_data.get("vega", 0)
                    rho_val = option_greeks_data.get("rho", 0)

                    # Ensure all values are valid numbers
                    if delta_val is not None and theta_val is not None:
                        greeks = {
                            "delta": float(delta_val),
                            "theta": float(theta_val),
                            "gamma": float(gamma_val) if gamma_val is not None else 0.0,
                            "vega": float(vega_val) if vega_val is not None else 0.0,
                            "rho": float(rho_val) if rho_val is not None else 0.0,
                        }

                        # VALIDATION: Delta should be between -1 and 1
                        if not (-1 <= greeks["delta"] <= 1):
                            logger.warning(
                                f"Invalid Delta value {greeks['delta']} for {instrument_key} - discarding Greeks"
                            )
                            greeks = None
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Greeks conversion failed for {instrument_key}: {e}"
                    )
                    greeks = None

            # Safely convert volume with logging
            volume_val = None
            if vol is not None:
                try:
                    volume_val = (
                        float(vol) if isinstance(vol, (int, float)) else float(str(vol))
                    )
                except (ValueError, TypeError) as e:
                    # CRITICAL FIX: Log volume conversion failures for debugging
                    logger.warning(
                        f"Volume conversion failed for {instrument_key}: vol={vol}, type={type(vol)}, error={e}"
                    )
                    volume_val = None

            # Update shared registry
            shared_registry.update_option_data(
                option_key=instrument_key,
                premium=Decimal(str(premium)),
                greeks=greeks,
                implied_vol=float(implied_vol) if implied_vol else None,
                open_interest=float(open_int) if open_int else None,
                volume=volume_val,
                bid_price=float(bid_price_val) if bid_price_val else None,
                ask_price=float(ask_price_val) if ask_price_val else None,
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
            # CRITICAL: Check if market is open before generating signals
            if not is_market_open():
                logger.debug(
                    f"Market is closed - skipping signal generation for {instrument.stock_symbol}"
                )
                return

            # STEP 1: Generate SPOT-BASED signal (trend detection on underlying)
            spot_signal = strategy_engine.generate_signal(
                current_price=instrument.live_spot_price,
                historical_data=instrument.historical_spot_data,
                option_type=instrument.option_type,
            )

            # STEP 2: Convert SPOT signal to PREMIUM signal (for actual trading)
            # This is CRITICAL: Strategy runs on spot for trend, but we trade options
            option_delta = None
            if hasattr(instrument, "option_greeks") and instrument.option_greeks:
                option_delta = instrument.option_greeks.get("delta")

            premium_signal = strategy_engine.convert_spot_signal_to_premium(
                signal=spot_signal,
                spot_price=instrument.live_spot_price,
                option_premium=instrument.live_option_premium,
                option_delta=option_delta,
            )

            # Store PREMIUM signal (this is what we'll use for trading)
            instrument.last_signal = premium_signal
            self.stats["signals_generated"] += 1

            trace_id = generate_trace_id()

            log_signal_generation(
                symbol=instrument.stock_symbol,
                signal_type=premium_signal.signal_type.value,
                confidence=float(premium_signal.confidence),
                strategy="SuperTrend+EMA",
                price=float(premium_signal.price),
                trace_id=trace_id,
            )

            logger.info(
                f"Signal for {instrument.stock_symbol}: "
                f"Spot({spot_signal.signal_type.value}) → "
                f"Premium({premium_signal.signal_type.value}, SL={premium_signal.stop_loss:.2f})"
            )
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
            await broadcast_to_clients(
                "trading_signal",
                {
                    "symbol": instrument.stock_symbol,
                    "signal_type": premium_signal.signal_type.value,
                    "confidence": float(premium_signal.confidence),
                    "price": float(premium_signal.price),
                    "entry_price": float(premium_signal.entry_price),
                    "stop_loss": float(premium_signal.stop_loss),
                    "target_price": float(premium_signal.target_price),
                    "reason": premium_signal.reason,
                    "timestamp": premium_signal.timestamp,
                },
            )

            # Check if signal is valid
            if not self._is_valid_signal(premium_signal, instrument.option_type):
                logger.debug(
                    f"Signal {premium_signal.signal_type.value} for {instrument.stock_symbol} did not pass validation "
                    f"(confidence: {premium_signal.confidence}, option_type: {instrument.option_type})"
                )
                return

            logger.info(
                f"✅ Valid signal for {instrument.stock_symbol}: "
                f"{premium_signal.signal_type.value} (Conf: {premium_signal.confidence})"
            )

            # Notify Admin of Signal
            from services.notifications.alert_manager import alert_manager
            asyncio.create_task(alert_manager.send_admin_system_status(
                "Strategy Engine", 
                "SIGNAL", 
                f"{premium_signal.signal_type.value.upper()} signal for {instrument.stock_symbol} @ {premium_signal.price:.2f} (Conf: {premium_signal.confidence:.2f})"
            ))

            # Get all users subscribed to this instrument
            subscribed_users = shared_registry.get_instrument_subscribers(
                instrument.option_instrument_key
            )

            if not subscribed_users:
                logger.info(
                    f"No users currently subscribed to {instrument.stock_symbol}"
                )
                return

            # CRITICAL FIX: Filter users based on signal type and position state
            # EXIT signals should only go to users WITH positions
            # ENTRY signals should only go to users WITHOUT positions
            eligible_users = []

            # Quick check using in-memory positions first (fast path)
            for user_id in subscribed_users:
                has_position_in_memory = (
                    user_id in self.active_user_positions
                    and instrument.option_instrument_key
                    in self.active_user_positions[user_id]
                )

                # For critical decisions, also check database (slower but accurate)
                # This ensures correctness after service restarts
                has_position = has_position_in_memory

                # If memory says no position but this is an EXIT signal, double-check DB
                # to avoid missing positions after service restart
                if not has_position and premium_signal.signal_type in (
                    SignalType.EXIT_LONG,
                    SignalType.EXIT_SHORT,
                ):
                    db = SessionLocal()
                    try:
                        db_position = (
                            db.query(ActivePosition)
                            .join(
                                AutoTradeExecution,
                                ActivePosition.trade_execution_id
                                == AutoTradeExecution.id,
                            )
                            .filter(
                                AutoTradeExecution.user_id == user_id,
                                AutoTradeExecution.instrument_key
                                == instrument.option_instrument_key,
                                ActivePosition.is_active == True,
                            )
                            .first()
                        )
                        has_position = db_position is not None
                    finally:
                        db.close()

                # Check signal type vs position state
                if premium_signal.signal_type in (
                    SignalType.EXIT_LONG,
                    SignalType.EXIT_SHORT,
                ):
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
                # ENHANCED LOGGING: Show why no users are eligible for better debugging
                logger.info(
                    f"No eligible users for {premium_signal.signal_type.value} signal on {instrument.stock_symbol} "
                    f"(total subscribed: {len(subscribed_users)})"
                )

                # Debug: Show position state for each subscribed user
                for user_id in subscribed_users:
                    has_position_in_memory = (
                        user_id in self.active_user_positions
                        and instrument.option_instrument_key
                        in self.active_user_positions[user_id]
                    )
                    logger.debug(
                        f"  User {user_id}: has_position_in_memory={has_position_in_memory}, "
                        f"signal_type={premium_signal.signal_type.value}, "
                        f"instrument_key={instrument.option_instrument_key}"
                    )

                return

            # Execute trade for EACH eligible user
            logger.info(
                f"Broadcasting {premium_signal.signal_type.value} signal to {len(eligible_users)}/{len(subscribed_users)} users for {instrument.stock_symbol}"
            )

            for user_id in eligible_users:
                # Execute in background to avoid blocking other users
                asyncio.create_task(
                    self._execute_trade_for_user(instrument, premium_signal, user_id)
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

            # EXIT signals: Valid for both CE and PE (closing long positions)
            if signal.signal_type in (SignalType.EXIT_LONG, SignalType.EXIT_SHORT):
                logger.info(f"Valid EXIT signal for {option_type}")
                return True

            # ENTRY signals: Both CE and PE use BUY signals ONLY
            # STANDARDIZED: We're BUYING options (long positions), never selling
            # - BUY CE = Long Call = Bullish bet
            # - BUY PE = Long Put = Bearish bet
            # The option_type (CE/PE) determines direction, signal type is always BUY for entry
            if signal.signal_type == SignalType.BUY:
                logger.info(f"Valid BUY signal for {option_type} option")
                return True

            # REJECT SELL signals (no longer supported for either CE or PE)
            # Removed legacy PE+SELL support for consistency
            if signal.signal_type == SignalType.SELL:
                logger.info(
                    f"Signal rejected: SELL signal not valid (we only BUY options for long positions)"
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
        self, instrument: SharedInstrument, signal: TradingSignal, user_id: int
    ):
        """
        Execute trade for a specific user with their capital and broker

        Args:
            instrument: Shared instrument
            signal: Trading signal
            user_id: User ID to execute trade for
        """
        import asyncio
        logger.info(f"Executing trade for user {user_id}: {instrument.stock_symbol}")

        # CRITICAL: Check if market is open before executing trades
        if not is_market_open():
            logger.warning(
                f"Market is closed - cannot execute trade for user {user_id}, {instrument.stock_symbol}"
            )
            await broadcast_to_clients(
                "trade_error",
                {
                    "symbol": instrument.stock_symbol,
                    "error": "Market is closed - trading not allowed",
                    "user_id": user_id,
                    "timestamp": get_ist_isoformat(),
                },
            )
            return

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
                and instrument.option_instrument_key
                in self.active_user_positions[user_id]
            )

            # Check database for active position (critical for service restarts)
            db_position = (
                db.query(ActivePosition)
                .join(
                    AutoTradeExecution,
                    ActivePosition.trade_execution_id == AutoTradeExecution.id,
                )
                .filter(
                    AutoTradeExecution.user_id == user_id,
                    AutoTradeExecution.instrument_key
                    == instrument.option_instrument_key,
                    ActivePosition.is_active == True,
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
                    self.active_user_positions[user_id][
                        instrument.option_instrument_key
                    ] = {
                        "position_id": db_position.id,
                        "entry_price": Decimal(str(trade.entry_price)),
                        "stop_loss": (
                            Decimal(str(trade.initial_stop_loss))
                            if trade.initial_stop_loss
                            else Decimal("0")
                        ),
                        "target": (
                            Decimal(str(trade.target_1))
                            if trade.target_1
                            else Decimal("0")
                        ),
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
                    await broadcast_to_clients(
                        "signal_skipped",
                        {
                            "symbol": instrument.stock_symbol,
                            "signal_type": signal.signal_type.value,
                            "reason": "No active position to exit",
                            "user_id": user_id,
                            "timestamp": get_ist_isoformat(),
                        },
                    )
                    return
                else:
                    # ENHANCED EXIT VALIDATION: Check profit AND hold time to prevent premature exits
                    # This prevents booking unnecessary losses

                    if db_position:
                        trade_entry = (
                            db.query(AutoTradeExecution)
                            .filter(
                                AutoTradeExecution.id == db_position.trade_execution_id
                            )
                            .first()
                        )

                        if trade_entry:
                            from services.trading_execution.strategy_engine import (
                                strategy_engine,
                            )

                            # Validate if exit should be allowed
                            current_price = instrument.live_option_premium
                            entry_price = Decimal(str(trade_entry.entry_price))
                            entry_time = trade_entry.entry_time

                            # Calculate current PnL percentage
                            current_pnl_percent = (
                                (current_price - entry_price) / entry_price
                            ) * Decimal("100")

                            # Use strategy engine's exit validation
                            allow_exit, exit_reason = (
                                strategy_engine.should_allow_exit_signal(
                                    current_price=current_price,
                                    entry_price=entry_price,
                                    entry_time=entry_time,
                                    current_pnl_percent=current_pnl_percent,
                                )
                            )

                            if not allow_exit:
                                logger.info(
                                    f"🚫 EXIT signal BLOCKED for {instrument.stock_symbol}: {exit_reason}"
                                )
                                # Broadcast exit blocked message to UI
                                await broadcast_to_clients(
                                    "exit_signal_blocked",
                                    {
                                        "symbol": instrument.stock_symbol,
                                        "signal_type": signal.signal_type.value,
                                        "reason": exit_reason,
                                        "user_id": user_id,
                                        "current_pnl_percent": float(
                                            current_pnl_percent
                                        ),
                                        "timestamp": get_ist_isoformat(),
                                    },
                                )
                                return

                    logger.info(
                        f"🔄 Processing EXIT signal for {instrument.stock_symbol} - closing position for user {user_id}"
                    )

                    # FIXED: Actually close the position with confirmation
                    exit_price = instrument.live_option_premium
                    exit_reason = f"SIGNAL_{signal.signal_type.value}"

                    closure_result = await self._close_position_for_user(
                        user_id=user_id,
                        instrument=instrument,
                        exit_price=exit_price,
                        exit_reason=exit_reason,
                        db=db,
                    )

                    if not closure_result.get("success"):
                        logger.error(
                            f"❌ Failed to close position for user {user_id}: {closure_result.get('error')}"
                        )
                        # Broadcast failure to UI
                        await broadcast_to_clients(
                            "position_close_failed",
                            {
                                "symbol": instrument.stock_symbol,
                                "signal_type": signal.signal_type.value,
                                "user_id": user_id,
                                "error": closure_result.get("error"),
                                "timestamp": get_ist_isoformat(),
                            },
                        )
                        return

                    logger.info(
                        f"✅ Position closed for user {user_id}: {instrument.stock_symbol} @ {exit_price}, "
                        f"PnL: ₹{closure_result.get('pnl', 0):.2f}"
                    )
                    return
            else:
                # ENTRY signal (BUY/SELL): Only process if no position exists
                if has_position:
                    logger.info(
                        f"⏭️ User {user_id} already has position in {instrument.stock_symbol} - skipping entry signal"
                    )
                    await broadcast_to_clients(
                        "signal_skipped",
                        {
                            "symbol": instrument.stock_symbol,
                            "signal_type": signal.signal_type.value,
                            "reason": "Position already exists",
                            "user_id": user_id,
                            "timestamp": get_ist_isoformat(),
                        },
                    )
                    return

            logger.info(
                f"🎯 Processing ENTRY signal for {instrument.stock_symbol} - opening position for user {user_id}"
            )

            # PERFORMANCE MEASURE: Calculate latency between signal and processing
            signal_time = datetime.fromisoformat(signal.timestamp)
            latency_ms = (get_ist_now_naive() - signal_time).total_seconds() * 1000
            logger.info(
                f"⏱️ Signal Latency: {latency_ms:.2f}ms for {instrument.stock_symbol}"
            )

            # Validate data availability
            current_candles = len(instrument.historical_spot_data.get("close", []))

            if instrument.live_option_premium <= 0:
                logger.error(
                    f"No premium data for {instrument.stock_symbol} "
                    f"(premium: {instrument.live_option_premium})"
                )
                self.stats["errors"] += 1
                await broadcast_to_clients(
                    "trade_error",
                    {
                        "symbol": instrument.stock_symbol,
                        "error": "No premium data available",
                        "user_id": user_id,
                        "premium": float(instrument.live_option_premium),
                        "timestamp": get_ist_isoformat(),
                    },
                )
                return

            # Strategy requires minimum 30 candles: max(EMA 20, SuperTrend 10) + 10 = 30
            if current_candles < 30:
                logger.warning(
                    f"Insufficient historical data for {instrument.stock_symbol} "
                    f"(have {current_candles} candles, need 30 minimum for SuperTrend+EMA strategy)"
                )
                self.stats["errors"] += 1
                await broadcast_to_clients(
                    "trade_error",
                    {
                        "symbol": instrument.stock_symbol,
                        "error": f"Insufficient historical data ({current_candles}/30 candles)",
                        "user_id": user_id,
                        "candles_available": current_candles,
                        "timestamp": get_ist_isoformat(),
                    },
                )
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
                ask_price=instrument.ask_price,
                target_lots=instrument.target_lots,
            )

            prepared_status = getattr(prepared_trade, "status", None)
            prepared_status_value = (
                getattr(prepared_status, "value", "") if prepared_status else "unknown"
            )

            logger.info(
                f"Trade preparation result: status={prepared_status_value}, "
                f"symbol={instrument.stock_symbol}"
            )

            if prepared_status_value == "ready":
                investment = (
                    float(prepared_trade.total_investment)
                    if hasattr(prepared_trade, "total_investment")
                    else 0
                )
                logger.info(
                    f"Executing trade for user {user_id}: "
                    f"{instrument.stock_symbol} {instrument.option_type} @ {instrument.strike_price}, "
                    f"investment=Rs.{investment:,.2f}"
                )

                # Execute trade
                try:
                    exec_result = await asyncio.to_thread(
                        execution_handler.execute_trade,
                        prepared_trade,
                        db,
                        None,  # parent_trade_id
                        broker_name,
                        broker_config_id,
                        investment,
                    )
                except NameError as ne:
                    logger.error(f"❌ Critical NameError in execution for user {user_id}: {ne}")
                    import asyncio as _asyncio
                    exec_result = await _asyncio.to_thread(
                        execution_handler.execute_trade,
                        prepared_trade,
                        db,
                        None,
                        broker_name,
                        broker_config_id,
                        investment,
                    )
                except Exception as e:
                    logger.exception(f"❌ Async execution failed for user {user_id}: {e}")
                    raise

                if getattr(exec_result, "success", False):
                    trade_id = getattr(exec_result, "trade_id", "unknown")

                    # CRITICAL: Ensure database commit succeeded before broadcasting
                    try:
                        db.commit()
                        logger.info(f"Database commit successful for trade {trade_id}")

                        log_trade_result(
                            user_id=str(user_id),
                            trade_id=str(trade_id),
                            status="SUCCESS",
                        )
                    except Exception as commit_error:
                        logger.error(
                            f"Database commit failed for trade {trade_id}: {commit_error}"
                        )
                        db.rollback()

                        log_trade_result(
                            user_id=str(user_id),
                            trade_id=str(trade_id),
                            status="FAILED",
                            error=f"DB Commit Failed: {str(commit_error)}",
                        )

                        # Don't broadcast if commit failed - data inconsistency
                        self.stats["errors"] += 1
                        await broadcast_to_clients(
                            "trade_error",
                            {
                                "symbol": instrument.stock_symbol,
                                "error": f"Database commit failed: {str(commit_error)}",
                                "user_id": user_id,
                                "timestamp": get_ist_isoformat(),
                            },
                        )
                        return

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

                    self.active_user_positions[user_id][
                        instrument.option_instrument_key
                    ] = {
                        "position_id": getattr(exec_result, "active_position_id", None),
                        "entry_price": Decimal(
                            str(
                                getattr(
                                    exec_result,
                                    "entry_price",
                                    instrument.live_option_premium,
                                )
                            )
                        ),
                        "stop_loss": getattr(signal, "stop_loss", Decimal("0")),
                        "target": getattr(signal, "target_price", Decimal("0")),
                    }

                    self.stats["trades_executed"] += 1

                    # Broadcast to UI - Trade Executed Event
                    await broadcast_to_clients(
                        "trade_executed",
                        {
                            "trade_id": getattr(exec_result, "trade_id", "unknown"),
                            "symbol": instrument.stock_symbol,
                            "option_type": instrument.option_type,
                            "strike_price": float(instrument.strike_price),
                            "entry_price": float(
                                self.active_user_positions[user_id][
                                    instrument.option_instrument_key
                                ]["entry_price"]
                            ),
                            "stop_loss": float(signal.stop_loss),
                            "target_price": float(signal.target_price),
                            "lot_size": instrument.lot_size,
                            "user_id": user_id,
                            "broker_name": broker_name,
                            "trading_mode": self.default_trading_mode.value,
                            "timestamp": get_ist_isoformat(),
                        },
                    )

                    # Broadcast Active Position Created Event (for UI position list)
                    await broadcast_to_clients(
                        "active_position_created",
                        {
                            "position_id": getattr(
                                exec_result, "active_position_id", None
                            ),
                            "trade_id": getattr(exec_result, "trade_id", "unknown"),
                            "symbol": instrument.stock_symbol,
                            "instrument_key": instrument.option_instrument_key,
                            "option_type": instrument.option_type,
                            "strike_price": float(instrument.strike_price),
                            "entry_price": float(
                                self.active_user_positions[user_id][
                                    instrument.option_instrument_key
                                ]["entry_price"]
                            ),
                            "current_price": float(
                                self.active_user_positions[user_id][
                                    instrument.option_instrument_key
                                ]["entry_price"]
                            ),
                            "stop_loss": float(signal.stop_loss),
                            "target": float(signal.target_price),
                            "quantity": instrument.lot_size
                            * getattr(exec_result, "quantity", 0)
                            // instrument.lot_size,
                            "user_id": user_id,
                            "broker_name": broker_name,
                            "trading_mode": self.default_trading_mode.value,
                            "current_pnl": 0.0,
                            "current_pnl_percentage": 0.0,
                            "timestamp": get_ist_isoformat(),
                        },
                    )

                    logger.info(
                        f"Broadcasted trade_executed and active_position_created events for user {user_id}, "
                        f"position_id={getattr(exec_result, 'active_position_id', None)}"
                    )
                else:
                    error_msg = getattr(exec_result, "message", "unknown")
                    logger.error(f"❌ Execution failed for user {user_id}: {error_msg}")
                    self.stats["errors"] += 1
                    await broadcast_to_clients(
                        "trade_error",
                        {
                            "symbol": instrument.stock_symbol,
                            "error": error_msg,
                            "user_id": user_id,
                            "timestamp": get_ist_isoformat(),
                        },
                    )
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
                await broadcast_to_clients(
                    "trade_preparation_failed",
                    {
                        "symbol": instrument.stock_symbol,
                        "status": prepared_status_value,
                        "reason": error_reason,
                        "user_id": user_id,
                        "timestamp": get_ist_isoformat(),
                    },
                )
                
                log_to_db(
                    component="auto_trade_live_feed",
                    message=f"Trade Prep FAILED for {instrument.stock_symbol}: {error_reason}",
                    level="WARNING",
                    user_id=user_id,
                    symbol=instrument.stock_symbol
                )

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
            # 1. Identify users who need updates (in-memory check first for speed)
            users_to_update = []
            for user_id, positions in self.active_user_positions.items():
                if instrument.option_instrument_key in positions:
                    users_to_update.append(user_id)

            if not users_to_update:
                return

            current_price = instrument.live_option_premium

            # 2. Perform DB updates in a thread to avoid blocking event loop
            def update_pnl_db_job(user_ids, price):
                db = SessionLocal()
                exits_to_process = []
                try:
                    for uid in user_ids:
                        position_data = self.active_user_positions[uid].get(
                            instrument.option_instrument_key
                        )
                        if not position_data:
                            continue

                        position_id = position_data.get("position_id")
                        if not position_id:
                            continue

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

                        entry_price = position_data["entry_price"]

                        # Get quantity
                        trade = (
                            db.query(AutoTradeExecution)
                            .filter(
                                AutoTradeExecution.id == position.trade_execution_id
                            )
                            .first()
                        )

                        if not trade:
                            continue

                        quantity = trade.quantity
                        pnl = (price - entry_price) * Decimal(str(quantity))
                        pnl_percent = (
                            ((price - entry_price) / entry_price * 100)
                            if entry_price > 0
                            else Decimal("0")
                        )

                        # Update position
                        position.current_price = float(price)
                        position.current_pnl = float(pnl)
                        position.current_pnl_percentage = float(pnl_percent)
                        position.last_updated = get_ist_now_naive()

                        # Check exit conditions
                        should_exit, reason = self._check_exit_conditions_for_user(
                            uid, instrument, price, position_data
                        )

                        if should_exit:
                            exits_to_process.append((uid, reason))

                    db.commit()
                    return exits_to_process
                except Exception as e:
                    db.rollback()
                    logger.error(f"DB Error in _update_positions_pnl: {e}")
                    return []
                finally:
                    db.close()

            # Run DB update in thread
            exits_needed = await asyncio.to_thread(
                update_pnl_db_job, users_to_update, current_price
            )

            # 3. Process exits (if any) - these involve more DB ops but are infrequent
            if exits_needed:
                db_session = SessionLocal()
                try:
                    for uid, reason in exits_needed:
                        await self._close_position_for_user(
                            user_id=uid,
                            instrument=instrument,
                            exit_price=current_price,
                            exit_reason=reason,
                            db=db_session,
                        )
                    db_session.commit()
                finally:
                    db_session.close()

        except Exception:
            logger.exception("Error updating positions PnL")

    def _check_exit_conditions_for_user(
        self,
        user_id: int,
        instrument: SharedInstrument,
        current_price: Decimal,
        position_data: Dict[str, Any],
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

            # SMART TIME-BASED EXIT with expiry day handling
            from utils.timezone_utils import get_ist_now

            now_ist = get_ist_now()
            now_t = now_ist.time()
            now_date = now_ist.date()
            entry_price_decimal = position_data.get("entry_price", Decimal("0"))

            # Parse expiry date
            try:
                if hasattr(instrument, "expiry_date") and instrument.expiry_date:
                    if isinstance(instrument.expiry_date, str):
                        from datetime import datetime as dt

                        expiry_date = dt.strptime(
                            instrument.expiry_date, "%Y-%m-%d"
                        ).date()
                    else:
                        expiry_date = instrument.expiry_date
                    is_expiry_day = expiry_date == now_date
                else:
                    is_expiry_day = False
            except Exception as e:
                logger.warning(f"Could not parse expiry date: {e}")
                is_expiry_day = False

            # EXPIRY DAY EXIT: Close earlier (3:00 PM)
            if is_expiry_day:
                if (now_t.hour, now_t.minute) >= (15, 0):
                    logger.info(
                        f"Expiry day exit triggered for {instrument.stock_symbol} at {now_t}"
                    )
                    return True, "EXPIRY_DAY_EXIT_3PM"

            # NORMAL DAY EXIT: Standard 3:20 PM exit
            if (now_t.hour, now_t.minute) >= (15, 20):
                logger.info(
                    f"Standard market close exit for {instrument.stock_symbol} at {now_t}"
                )
                return True, "TIME_BASED_EXIT_3_20PM"

            # EMERGENCY LOSS EXIT: After 3:10 PM, exit if down more than 10%
            if (now_t.hour, now_t.minute) >= (15, 10):
                if entry_price_decimal > 0 and current_price > 0:
                    pnl_percent = (
                        (current_price - entry_price_decimal)
                        / entry_price_decimal
                        * 100
                    )
                    if pnl_percent < -10:
                        logger.warning(
                            f"Emergency loss exit for {instrument.stock_symbol}: "
                            f"PnL {pnl_percent:.2f}% at {now_t}"
                        )
                        return True, "EMERGENCY_LOSS_EXIT_3_10PM"

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
        db: Session,
    ) -> Dict[str, Any]:
        """
        Close position for specific user

        Args:
            user_id: User ID
            instrument: Shared instrument
            exit_price: Exit price
            exit_reason: Exit reason
            db: Database session

        Returns:
            Dict with success status, pnl, and other details
        """
        try:
            # 1. Get position data from memory (Main Thread)
            if (
                user_id not in self.active_user_positions
                or instrument.option_instrument_key
                not in self.active_user_positions[user_id]
            ):
                return {"success": False, "error": "Position not found in memory"}

            position_data = self.active_user_positions[user_id][
                instrument.option_instrument_key
            ]
            position_id = position_data.get("position_id")
            entry_price_mem = Decimal(str(position_data["entry_price"]))

            if not position_id:
                return {"success": False, "error": "Invalid position ID"}

            # 2. Define DB Job (Thread)
            def db_job(pid, price, reason):
                try:
                    position = (
                        db.query(ActivePosition)
                        .filter(ActivePosition.id == pid)
                        .first()
                    )
                    if not position:
                        return None

                    trade = (
                        db.query(AutoTradeExecution)
                        .filter(AutoTradeExecution.id == position.trade_execution_id)
                        .first()
                    )
                    if not trade:
                        return None

                    # ACTUAL EXIT PRICE WITH SLIPPAGE FOR PAPER TRADING
                    final_exit_price = price
                    if trade.trading_mode == "paper":
                        slippage = price * Decimal("0.0005")
                        final_exit_price = price - slippage
                        logger.info(
                            f"📝 Paper exit slippage applied: {price} -> {final_exit_price}"
                        )

                    entry_price = Decimal(str(trade.entry_price))
                    quantity = trade.quantity

                    buy_value = entry_price * Decimal(str(quantity))
                    sell_value = final_exit_price * Decimal(str(quantity))
                    gross_pnl = sell_value - buy_value
                    turnover = buy_value + sell_value

                    # CHARGES
                    brokerage_flat = Decimal("40.0")
                    taxes = turnover * Decimal("0.001")
                    total_charges = brokerage_flat + taxes
                    net_pnl = gross_pnl - total_charges

                    pnl_percent = (
                        (net_pnl / Decimal(str(trade.total_investment)) * 100)
                        if trade.total_investment and trade.total_investment > 0
                        else Decimal("0")
                    )

                    # Update trade
                    trade.exit_time = get_ist_now_naive()
                    trade.exit_price = float(final_exit_price)
                    trade.exit_reason = reason
                    trade.gross_pnl = float(gross_pnl)
                    trade.net_pnl = float(net_pnl)
                    trade.pnl_percentage = float(pnl_percent)
                    trade.status = "CLOSED"

                    # Deactivate position
                    position.is_active = False
                    position.last_updated = get_ist_now_naive()

                    # UPDATE PAPER TRADING ACCOUNT
                    if trade.trading_mode == "paper":
                        from database.models import PaperTradingAccount

                        paper_account = (
                            db.query(PaperTradingAccount)
                            .filter(PaperTradingAccount.user_id == user_id)
                            .first()
                        )
                        if paper_account:
                            release_amount = float(sell_value - total_charges)
                            paper_account.available_margin += release_amount
                            paper_account.current_balance += release_amount
                            paper_account.used_margin -= float(trade.total_investment)
                            paper_account.total_pnl += float(net_pnl)
                            paper_account.daily_pnl += float(net_pnl)
                            paper_account.positions_count = max(
                                0, paper_account.positions_count - 1
                            )
                            paper_account.updated_at = get_ist_now_naive()

                    db.commit()

                    return {
                        "success": True,
                        "pnl": float(net_pnl),
                        "pnl_percent": float(pnl_percent),
                        "exit_price": float(final_exit_price),
                        "position_id": pid,
                    }
                except Exception as e:
                    db.rollback()
                    logger.error(f"DB Error closing position: {e}")
                    raise e

            # 3. Execute DB Job
            result = await asyncio.to_thread(
                db_job, position_id, exit_price, exit_reason
            )

            if not result:
                return {"success": False, "error": "Position or Trade not found"}

            # 4. Update Memory & Broadcast (Main Thread)
            if (
                user_id in self.active_user_positions
                and instrument.option_instrument_key
                in self.active_user_positions[user_id]
            ):
                del self.active_user_positions[user_id][
                    instrument.option_instrument_key
                ]

            self.stats["positions_closed"] += 1

            # Update in-memory paper service if needed
            if result.get("success"):
                try:
                    # We can't easily sync in-memory service here without DB access or duplicating logic
                    # Rely on DB source of truth or eventual sync
                    pass
                except Exception:
                    pass

            logger.info(
                f"Position closed for user {user_id}: Net PnL = Rs.{result['pnl']:.2f} ({result['pnl_percent']:.2f}%)"
            )

            # Broadcast to UI
            await broadcast_to_clients(
                "position_closed",
                {
                    "user_id": user_id,
                    "symbol": instrument.stock_symbol,
                    "exit_price": result["exit_price"],
                    "exit_reason": exit_reason,
                    "pnl": result["pnl"],
                    "pnl_percent": result["pnl_percent"],
                    "timestamp": get_ist_isoformat(),
                },
            )

            return result

        except Exception as e:
            logger.exception(f"Error closing position for user {user_id}")
            return {"success": False, "error": str(e), "pnl": 0}

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
                "timestamp": get_ist_isoformat(),
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
                    ),
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

            def db_job():
                from database.connection import SessionLocal
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
                    if (
                        not token
                        or not isinstance(token, str)
                        or len(token.strip()) < 20
                    ):
                        logger.error("Invalid token format")
                        return ""

                    logger.info("Loaded Upstox access token from database")
                    return token.strip()
                except Exception as e:
                    logger.error(f"Error loading admin token: {e}")
                    return ""
                finally:
                    db.close()

            return await asyncio.to_thread(db_job)

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

    async def _sync_active_positions_from_db(self):
        """
        Sync active positions from database into memory on startup

        This ensures exit signals can find eligible users after service restart

        Critical for:
        - Service restarts don't lose position tracking
        - Exit signals can properly identify users with active positions
        - Memory state matches database state
        """

        def db_job():
            db = SessionLocal()
            try:
                # Get all active positions with trade execution details
                active_positions = (
                    db.query(ActivePosition)
                    .join(
                        AutoTradeExecution,
                        ActivePosition.trade_execution_id == AutoTradeExecution.id,
                    )
                    .filter(ActivePosition.is_active == True)
                    .all()
                )

                result = []
                for pos in active_positions:
                    trade = (
                        db.query(AutoTradeExecution)
                        .filter(AutoTradeExecution.id == pos.trade_execution_id)
                        .first()
                    )
                    if trade:
                        result.append(
                            {
                                "user_id": trade.user_id,
                                "instrument_key": trade.instrument_key,
                                "position_id": pos.id,
                                "entry_price": Decimal(str(trade.entry_price)),
                                "stop_loss": (
                                    Decimal(str(trade.initial_stop_loss))
                                    if trade.initial_stop_loss
                                    else Decimal("0")
                                ),
                                "target": (
                                    Decimal(str(trade.target_1))
                                    if trade.target_1
                                    else Decimal("0")
                                ),
                            }
                        )
                return result
            finally:
                db.close()

        try:
            positions = await asyncio.to_thread(db_job)

            # Populate memory dictionary
            for pos_data in positions:
                user_id = pos_data["user_id"]
                instrument_key = pos_data["instrument_key"]

                if user_id not in self.active_user_positions:
                    self.active_user_positions[user_id] = {}

                self.active_user_positions[user_id][instrument_key] = {
                    "position_id": pos_data["position_id"],
                    "entry_price": pos_data["entry_price"],
                    "stop_loss": pos_data["stop_loss"],
                    "target": pos_data["target"],
                }

            logger.info(
                f"Synced {len(positions)} active positions from database into memory "
                f"for {len(self.active_user_positions)} users"
            )

        except Exception:
            logger.exception("Error syncing active positions from database")


# Singleton instance
auto_trade_live_feed = AutoTradeLiveFeed()
