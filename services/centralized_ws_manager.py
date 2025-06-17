# services/centralized_ws_manager.py - FIXED VERSION
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set, Optional, Callable
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from services.upstox.ws_client import UpstoxWebSocketClient
from database.connection import get_db
from database.models import BrokerConfig, User

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CentralizedWebSocketManager:
    """
    Singleton WebSocket manager that maintains one connection to Upstox
    and broadcasts data to multiple users
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.admin_token: Optional[str] = None
            self.admin_user_id: Optional[int] = None
            self.ws_client: Optional[UpstoxWebSocketClient] = None
            self.is_running = False
            self.reconnect_attempts = 0
            self.max_reconnect_attempts = 10

            # Client management
            self.dashboard_clients: Dict[str, WebSocket] = {}  # token -> websocket
            self.trading_clients: Dict[str, WebSocket] = {}
            self.legacy_clients: Dict[str, WebSocket] = {}

            # User subscriptions
            self.user_subscriptions: Dict[str, Set[str]] = (
                {}
            )  # token -> instrument_keys
            self.all_instrument_keys: Set[str] = set()

            # Data caching
            self.latest_market_data: Dict[str, dict] = {}  # instrument_key -> data
            self.market_status = "unknown"
            self.last_data_received = None

            # Admin monitoring
            self.admin_callbacks: Dict[str, Callable] = {}

            CentralizedWebSocketManager._initialized = True

    async def initialize(self):
        """Initialize the manager with admin token from database"""
        try:
            db = next(get_db())

            # Find admin user with Upstox broker config
            admin_broker = (
                db.query(BrokerConfig)
                .join(User, BrokerConfig.user_id == User.id)
                .filter(
                    User.role == "admin",
                    BrokerConfig.broker_name.ilike("upstox"),
                    BrokerConfig.access_token.isnot(None),
                )
                .first()
            )

            if not admin_broker:
                logger.error("❌ No admin user with Upstox access token found!")
                return False

            self.admin_token = admin_broker.access_token
            self.admin_user_id = admin_broker.user_id

            logger.info(
                f"✅ Centralized manager initialized with admin user ID: {self.admin_user_id}"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize centralized manager: {e}")
            return False

    async def start_connection(self):
        """Start the centralized WebSocket connection"""
        if self.is_running:
            logger.warning("⚠️ Connection already running")
            return

        if not self.admin_token:
            if not await self.initialize():
                return

        # Load all possible instrument keys
        await self._load_all_instruments()

        if not self.all_instrument_keys:
            logger.error("❌ No instrument keys available")
            return

        self.is_running = True
        self.reconnect_attempts = 0

        # Start the connection with retry logic
        asyncio.create_task(self._maintain_connection())

        logger.info(
            f"🚀 Centralized WebSocket started with {len(self.all_instrument_keys)} instruments"
        )

    async def _maintain_connection(self):
        """Maintain WebSocket connection with auto-reconnect"""
        while self.is_running and self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                await self._start_ws_client()

                # If we reach here, connection was successful
                self.reconnect_attempts = 0

            except Exception as e:
                logger.error(f"❌ WebSocket connection failed: {e}")
                self.reconnect_attempts += 1

                if self.reconnect_attempts < self.max_reconnect_attempts:
                    backoff_delay = min(
                        5 * (2**self.reconnect_attempts), 60
                    )  # Max 60 seconds
                    logger.info(
                        f"⏳ Reconnecting in {backoff_delay}s (attempt {self.reconnect_attempts})"
                    )
                    await asyncio.sleep(backoff_delay)
                else:
                    logger.error("❌ Max reconnection attempts reached")
                    self.is_running = False

    async def _start_ws_client(self):
        """Start the actual WebSocket client"""
        try:
            # Refresh admin token if needed
            await self._refresh_admin_token()

            # Create WebSocket client
            self.ws_client = UpstoxWebSocketClient(
                access_token=self.admin_token,
                instrument_keys=list(self.all_instrument_keys),
                callback=self._handle_market_data,
                stop_callback=self._handle_connection_stop,
                on_auth_error=self._handle_auth_error,
                connection_type="centralized_admin",
                subscription_mode="full",
                max_retries=3,
            )

            # Start streaming
            await self.ws_client.connect_and_stream()

        except Exception as e:
            logger.error(f"❌ Failed to start WebSocket client: {e}")
            raise

    async def _handle_market_data(self, data: dict):
        """Handle incoming market data and broadcast to clients - ENHANCED VERSION"""
        try:
            msg_type = data.get("type")
            self.last_data_received = datetime.now()

            logger.debug(f"📊 Received market data: {msg_type}")

            if msg_type == "market_info":
                self.market_status = data.get("status", "unknown").lower()
                logger.info(f"📈 Market status updated: {self.market_status}")
                await self._broadcast_market_status()

            elif msg_type == "live_feed":
                # Update cache
                feed_data = data.get("data", {})

                # Enhanced logging for debugging
                if feed_data:
                    logger.info(
                        f"📊 Received live feed for {len(feed_data)} instruments"
                    )

                    # Log first few instruments for debugging
                    sample_keys = list(feed_data.keys())[:3]
                    for key in sample_keys:
                        tick_data = feed_data[key]
                        logger.debug(f"   {key}: {tick_data}")
                else:
                    logger.warning("⚠️ Received empty live feed data")

                for instrument_key, tick_data in feed_data.items():
                    self.latest_market_data[instrument_key] = {
                        **tick_data,
                        "timestamp": datetime.now().isoformat(),
                        "source": "centralized_ws",
                    }

                # Broadcast to all clients
                await self._broadcast_live_data(feed_data)

            elif msg_type == "error":
                logger.error(f"❌ Market data error: {data}")
                await self._broadcast_error(data)

            elif msg_type == "connection_status":
                logger.info(f"🔗 Connection status: {data}")
                await self._broadcast_connection_status(data)

            else:
                logger.debug(f"🔍 Unknown message type: {msg_type}")

        except Exception as e:
            logger.error(f"❌ Error handling market data: {e}")

    async def _broadcast_market_status(self):
        """Broadcast market status to all connected clients"""
        status_data = {
            "type": "market_info",
            "marketStatus": self.market_status,
            "source": "centralized",
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"📡 Broadcasting market status: {self.market_status}")
        await self._send_to_all_clients(status_data)

    async def _broadcast_connection_status(self, status_data: dict):
        """Broadcast connection status to all clients"""
        broadcast_data = {
            "type": "connection_status",
            "status": status_data.get("status", "unknown"),
            "message": status_data.get("message", "Connection status update"),
            "source": "centralized",
            "timestamp": datetime.now().isoformat(),
        }

        await self._send_to_all_clients(broadcast_data)

    async def _broadcast_live_data(self, feed_data: dict):
        """Broadcast live data to subscribed clients - ENHANCED VERSION"""
        if not feed_data:
            logger.warning("⚠️ No feed data to broadcast")
            return

        logger.info(f"📡 Broadcasting live data to {self._get_total_clients()} clients")

        # Send to dashboard clients (all data)
        dashboard_payload = {
            "type": "dashboard_update",
            "data": feed_data,
            "market_open": self.market_status == "open",
            "data_source": "CENTRALIZED_WS",
            "timestamp": datetime.now().isoformat(),
            "total_instruments": len(self.all_instrument_keys),
            "received_instruments": len(feed_data),
        }

        dashboard_sent = await self._send_to_client_group(
            self.dashboard_clients, dashboard_payload
        )
        logger.debug(
            f"   📊 Dashboard clients: {dashboard_sent}/{len(self.dashboard_clients)}"
        )

        # Send to trading clients (filtered data)
        trading_sent = 0
        for token, ws in self.trading_clients.items():
            user_instruments = self.user_subscriptions.get(token, set())
            if user_instruments:
                filtered_data = {
                    key: value
                    for key, value in feed_data.items()
                    if key in user_instruments
                }
                if filtered_data:
                    trading_payload = {
                        "type": "trading_update",
                        "data": filtered_data,
                        "instruments_count": len(user_instruments),
                        "filtered_instruments": len(filtered_data),
                        "timestamp": datetime.now().isoformat(),
                    }
                    if await self._send_to_client(ws, trading_payload):
                        trading_sent += 1

        logger.debug(
            f"   🎯 Trading clients: {trading_sent}/{len(self.trading_clients)}"
        )

        # Send to legacy clients (backward compatibility)
        legacy_payload = {
            "type": "live_feed",
            "data": self._parse_legacy_format(feed_data),
            "market_open": self.market_status == "open",
            "timestamp": datetime.now().isoformat(),
        }

        legacy_sent = await self._send_to_client_group(
            self.legacy_clients, legacy_payload
        )
        logger.debug(f"   🔄 Legacy clients: {legacy_sent}/{len(self.legacy_clients)}")

    async def _broadcast_error(self, error_data: dict):
        """Broadcast errors to all clients"""
        await self._send_to_all_clients(
            {
                "type": "error",
                "reason": error_data.get("reason", "unknown"),
                "message": error_data.get("message", "An error occurred"),
                "source": "centralized",
                "timestamp": datetime.now().isoformat(),
            }
        )

    async def _send_to_all_clients(self, data: dict):
        """Send data to all connected clients"""
        total_sent = 0
        total_sent += await self._send_to_client_group(self.dashboard_clients, data)
        total_sent += await self._send_to_client_group(self.trading_clients, data)
        total_sent += await self._send_to_client_group(self.legacy_clients, data)

        logger.debug(
            f"📤 Sent to {total_sent}/{self._get_total_clients()} total clients"
        )

    async def _send_to_client_group(self, client_group: dict, data: dict) -> int:
        """Send data to a group of clients and return success count"""
        if not client_group:
            return 0

        disconnected_tokens = []
        sent_count = 0

        for token, ws in client_group.items():
            success = await self._send_to_client(ws, data)
            if success:
                sent_count += 1
            else:
                disconnected_tokens.append(token)

        # Clean up disconnected clients
        for token in disconnected_tokens:
            await self.remove_client(token)
            logger.info(f"🧹 Removed disconnected client: {token}")

        return sent_count

    async def _send_to_client(self, ws: WebSocket, data: dict) -> bool:
        """Send data to a single client with proper error handling"""
        try:
            # Check if WebSocket is still connected
            if ws.client_state != WebSocketState.CONNECTED:
                return False

            await ws.send_json(data)
            return True

        except Exception as e:
            logger.warning(f"⚠️ Failed to send data to client: {e}")
            return False

    def _parse_legacy_format(self, raw_data: dict) -> dict:
        """Parse data for legacy format compatibility"""
        parsed = {}
        for instrument_key, details in raw_data.items():
            try:
                # Handle different data formats
                if isinstance(details, dict):
                    # Check if it's already in the format we expect
                    if "fullFeed" in details:
                        feed = details.get("fullFeed", {}).get("marketFF", {})
                        ltpc = feed.get("ltpc", {})
                        parsed[instrument_key] = {
                            "ltp": ltpc.get("ltp"),
                            "ltq": ltpc.get("ltq"),
                            "cp": ltpc.get("cp"),
                            "last_trade_time": ltpc.get("ltt"),
                            "bid_ask": feed.get("marketLevel", {}).get(
                                "bidAskQuote", []
                            ),
                            "greeks": feed.get("optionGreeks", {}),
                            "ohlc": feed.get("marketOHLC", {}).get("ohlc", []),
                            "atp": feed.get("atp"),
                            "oi": feed.get("oi"),
                            "iv": feed.get("iv"),
                            "tbq": feed.get("tbq"),
                            "tsq": feed.get("tsq"),
                        }
                    else:
                        # Direct format
                        parsed[instrument_key] = details
                else:
                    # Fallback
                    parsed[instrument_key] = {"ltp": details}

            except Exception as e:
                logger.warning(
                    f"⚠️ Failed to parse legacy tick for {instrument_key}: {e}"
                )
                parsed[instrument_key] = {"error": "parse_failed"}

        return parsed

    async def _handle_connection_stop(self):
        """Handle WebSocket connection stop"""
        logger.warning("🛑 Centralized WebSocket connection stopped")
        self.ws_client = None

        # Notify all clients
        await self._send_to_all_clients(
            {
                "type": "connection_status",
                "status": "disconnected",
                "message": "Centralized connection lost, attempting to reconnect...",
                "timestamp": datetime.now().isoformat(),
            }
        )

    async def _handle_auth_error(self):
        """Handle authentication errors"""
        logger.error("🔐 Admin token authentication failed")

        # Try to refresh admin token
        if await self._refresh_admin_token():
            logger.info("✅ Admin token refreshed successfully")
            return

        # If refresh fails, notify all clients
        await self._send_to_all_clients(
            {
                "type": "error",
                "reason": "admin_token_expired",
                "message": "Admin authentication failed. Please contact administrator.",
                "timestamp": datetime.now().isoformat(),
            }
        )

        self.is_running = False

    async def _refresh_admin_token(self) -> bool:
        """Refresh admin token from database"""
        try:
            db = next(get_db())
            admin_broker = (
                db.query(BrokerConfig)
                .join(User, BrokerConfig.user_id == User.id)
                .filter(
                    User.role == "admin",
                    BrokerConfig.broker_name.ilike("upstox"),
                    BrokerConfig.user_id == self.admin_user_id,
                )
                .first()
            )

            if admin_broker and admin_broker.access_token:
                old_token = (
                    self.admin_token[:10] + "..." if self.admin_token else "None"
                )
                new_token = admin_broker.access_token[:10] + "..."

                if admin_broker.access_token != self.admin_token:
                    self.admin_token = admin_broker.access_token
                    logger.info(f"🔄 Admin token refreshed: {old_token} -> {new_token}")
                    return True
                else:
                    logger.debug("ℹ️ Admin token unchanged")
                    return True

            logger.error("❌ Failed to refresh admin token - no valid token found")
            return False

        except Exception as e:
            logger.error(f"❌ Error refreshing admin token: {e}")
            return False

    async def _load_all_instruments(self):
        """Load all instrument keys for the connection"""
        try:
            from pathlib import Path
            from tempfile import gettempdir

            file_path = Path(gettempdir()) / "today_instrument_keys.json"

            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    if isinstance(content, list):
                        self.all_instrument_keys = set(content)
                    elif isinstance(content, dict):
                        if content.get("timestamp") == datetime.now().strftime(
                            "%Y-%m-%d"
                        ):
                            self.all_instrument_keys = set(content.get("keys", []))

            # Limit to Upstox's maximum (3000 total, we'll use 1500 to be safe)
            if len(self.all_instrument_keys) > 1500:
                instrument_list = list(self.all_instrument_keys)
                self.all_instrument_keys = set(instrument_list[:1500])
                logger.info(
                    f"⚠️ Limited instruments to 1500 (from {len(instrument_list)})"
                )

            logger.info(f"📊 Loaded {len(self.all_instrument_keys)} instrument keys")

            # Log a sample of instruments for debugging
            sample_instruments = list(self.all_instrument_keys)[:5]
            logger.debug(f"📋 Sample instruments: {sample_instruments}")

        except Exception as e:
            logger.error(f"❌ Failed to load instrument keys: {e}")
            self.all_instrument_keys = set()

    def _get_total_clients(self) -> int:
        """Get total numbe