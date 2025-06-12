# ===== YOUR CURRENT ws_client.py IS PERFECT! =====
# No changes required for basic functionality
# These are OPTIONAL enhancements for better integration

import asyncio, json, ssl, logging, functools, inspect, requests, websockets
from websockets.exceptions import InvalidStatus
from google.protobuf.json_format import MessageToDict
import services.upstox.MarketDataFeed_pb2 as pb

logger = logging.getLogger("ws_client")

received_ltp = False  # ✅ Flag to track if LTP was received


def sync_fetch_feed_url(access_token: str):
    url = "https://api.upstox.com/v3/feed/market-data-feed/authorize"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    return response.json()


class UpstoxWebSocketClient:
    def __init__(
        self,
        access_token,
        instrument_keys,
        callback,
        stop_callback=None,
        on_auth_error=None,
        max_retries=5,
        # OPTIONAL: Add these parameters for better control
        connection_type="default",  # "dashboard", "trading", "legacy"
        subscription_mode="full",  # "full", "ltpc", "quote"
    ):
        self.access_token = access_token
        self.instrument_keys = instrument_keys
        self.callback = callback
        self.stop_callback = stop_callback
        self.on_auth_error = on_auth_error
        self.websocket = None
        self.should_run = True
        self.retry_count = 0
        self.max_retries = max_retries
        self.auth_error_sent = False
        self.last_ws_url = None
        self.market_closed = False  # ✅ Flag if market is closed
        self.received_ltp = False  # ✅ Flag if LTP was received

        # OPTIONAL: Add these for better tracking
        self.connection_type = connection_type
        self.subscription_mode = subscription_mode
        self.connection_id = f"{connection_type}_{id(self)}"  # Unique ID for logging

    async def get_feed_authorized_url(self):
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, functools.partial(sync_fetch_feed_url, self.access_token)
        )
        logger.info(f"🔐 Feed Auth Response for {self.connection_type}: {result}")
        if result.get("status") != "success":
            if self.on_auth_error and not self.auth_error_sent:
                await self.on_auth_error()
                self.auth_error_sent = True
            raise PermissionError("Access token expired")

        new_url = result["data"]["authorized_redirect_uri"]
        if new_url == self.last_ws_url:
            logger.warning(
                f"⚠️ Reused WebSocket URL detected for {self.connection_type}, skipping."
            )
            raise InvalidStatus(403)
        self.last_ws_url = new_url
        return new_url

    async def connect_and_stream(self):
        logger.info(
            f"🚀 Starting {self.connection_type} WebSocket with {len(self.instrument_keys)} instruments"
        )

        while self.should_run and self.retry_count <= self.max_retries:
            try:
                ws_url = await self.get_feed_authorized_url()
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                async with websockets.connect(ws_url, ssl=ssl_context) as conn:
                    self.websocket = conn
                    self.retry_count = 0
                    self.auth_error_sent = False
                    self.market_closed = False
                    self.received_ltp = False

                    logger.info(
                        f"✅ {self.connection_type.title()} WebSocket connected."
                    )
                    await self._send_subscription()

                    while self.should_run:
                        raw = await conn.recv()
                        msg = pb.FeedResponse()
                        msg.ParseFromString(raw)
                        parsed = MessageToDict(msg)

                        msg_type = parsed.get("type")
                        # OPTIONAL: More detailed logging
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"📥 {self.connection_type} Tick: {msg_type}")

                        if msg_type == "market_info":
                            status = (
                                parsed.get("marketInfo", {})
                                .get("segmentStatus", {})
                                .get("NSE_EQ", "")
                            )
                            logger.info(
                                f"📊 {self.connection_type} Market status: {status}"
                            )
                            await self.callback(
                                {"type": "market_info", "status": status}
                            )
                            if (
                                status in ["NORMAL_CLOSE", "CLOSING_END"]
                                and self.received_ltp
                            ):
                                logger.info(
                                    f"📴 {self.connection_type}: Market closed and LTP received. Stopping."
                                )
                                self.market_closed = True

                        elif msg_type == "ltpc":
                            symbol = parsed.get("symbol") or parsed.get("ltpc", {}).get(
                                "symbol"
                            )
                            if not symbol:
                                logger.warning(
                                    f"⚠️ {self.connection_type}: Missing symbol in tick"
                                )
                                continue

                            self.received_ltp = True
                            # OPTIONAL: Less verbose logging for high-frequency data
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug(
                                    f"✅ {self.connection_type}: Processing symbol {symbol}"
                                )

                            await self.callback(
                                {"type": "live_feed", "data": {symbol: parsed}}
                            )

                            if self.market_closed:
                                logger.info(
                                    f"📴 {self.connection_type}: Market closed & LTP received. Stopping."
                                )
                                self.should_run = False

                        elif "feeds" in parsed:
                            feeds = parsed.get("feeds", {})
                            if not feeds:
                                logger.warning(
                                    f"⚠️ {self.connection_type}: Received 'feeds' payload but it's empty."
                                )
                                continue
                            self.received_ltp = True

                            # OPTIONAL: Better logging for batch data
                            logger.info(
                                f"✅ {self.connection_type}: Processing {len(feeds)} batched instruments"
                            )

                            await self.callback({"type": "live_feed", "data": feeds})

                            if self.market_closed:
                                logger.info(
                                    f"📴 {self.connection_type}: Market closed & batched LTP received. Stopping."
                                )
                                self.should_run = False
                        else:
                            logger.warning(
                                f"⚠️ {self.connection_type}: Unknown message type: {msg_type}"
                            )

            except PermissionError:
                logger.error(
                    f"🔐 {self.connection_type}: Permission error - token expired"
                )
                await self.callback({"type": "error", "reason": "token_expired"})
                self.should_run = False
                break

            except InvalidStatus as e:
                logger.error(f"❌ {self.connection_type}: WebSocket rejected: {e}")
                if getattr(e, "status", None) == 403:
                    if self.on_auth_error and not self.auth_error_sent:
                        await self.on_auth_error()
                        self.auth_error_sent = True
                break

            except Exception as e:
                logger.error(f"🔥 {self.connection_type}: Unexpected error: {e}")
                self.retry_count += 1

                # OPTIONAL: Exponential backoff for retries
                backoff_delay = min(
                    3 * (2 ** (self.retry_count - 1)), 30
                )  # Max 30 seconds
                logger.info(
                    f"⏳ {self.connection_type}: Retrying in {backoff_delay}s (attempt {self.retry_count}/{self.max_retries})"
                )
                await asyncio.sleep(backoff_delay)

        await self._trigger_stop_callback()

    async def _send_subscription(self):
        if not self.websocket:
            return

        # OPTIONAL: Adjust subscription based on connection type
        guid = f"{self.connection_type}-{self.connection_id}"

        # OPTIONAL: Different modes for different connection types
        if self.connection_type == "trading":
            mode = "full"  # Full market depth for trading
        elif self.connection_type == "dashboard":
            mode = "ltpc"  # Just LTP for dashboard (though we use API now)
        else:
            mode = self.subscription_mode

        payload = {
            "guid": guid,
            "method": "sub",
            "data": {
                "mode": mode,
                "instrumentKeys": self.instrument_keys[:1500],  # Upstox limit
            },
        }

        await self.websocket.send(json.dumps(payload).encode("utf-8"))
        logger.info(
            f"📩 {self.connection_type.title()}: Subscription sent for {len(self.instrument_keys[:1500])} instruments in '{mode}' mode"
        )

    async def _trigger_stop_callback(self):
        if self.stop_callback:
            if inspect.iscoroutinefunction(self.stop_callback):
                await self.stop_callback()
            else:
                self.stop_callback()

    def stop(self):
        logger.info(f"🛑 {self.connection_type.title()}: WebSocket manually stopped.")
        self.should_run = False

    # OPTIONAL: Add health check method
    def is_connected(self):
        """Check if WebSocket is currently connected"""
        return self.websocket is not None and self.websocket.open and self.should_run

    # OPTIONAL: Add status method
    def get_status(self):
        """Get current connection status"""
        return {
            "connection_type": self.connection_type,
            "is_connected": self.is_connected(),
            "instruments_count": len(self.instrument_keys),
            "received_ltp": self.received_ltp,
            "retry_count": self.retry_count,
            "market_closed": self.market_closed,
        }


# ===== OPTIONAL: Enhanced Factory Functions =====


def create_dashboard_websocket_client(
    access_token, instrument_keys, callback, **kwargs
):
    """
    OPTIONAL: Factory function for dashboard WebSocket
    (Though dashboard now uses LTP API, this is for backward compatibility)
    """
    return UpstoxWebSocketClient(
        access_token=access_token,
        instrument_keys=instrument_keys,
        callback=callback,
        connection_type="dashboard",
        subscription_mode="ltpc",  # Lighter mode for dashboard
        **kwargs,
    )


def create_trading_websocket_client(access_token, instrument_keys, callback, **kwargs):
    """
    OPTIONAL: Factory function for focused trading WebSocket
    """
    return UpstoxWebSocketClient(
        access_token=access_token,
        instrument_keys=instrument_keys,
        callback=callback,
        connection_type="trading",
        subscription_mode="full",  # Full market depth for trading
        max_retries=10,  # More retries for critical trading connection
        **kwargs,
    )


def create_legacy_websocket_client(access_token, instrument_keys, callback, **kwargs):
    """
    OPTIONAL: Factory function for legacy WebSocket (backward compatibility)
    """
    return UpstoxWebSocketClient(
        access_token=access_token,
        instrument_keys=instrument_keys,
        callback=callback,
        connection_type="legacy",
        subscription_mode="full",
        **kwargs,
    )


# ===== USAGE EXAMPLES IN YOUR market_ws.py =====

"""
In your market_ws.py, you can now use the enhanced client like this:

# For trading WebSocket (in trading_data_websocket function):
client = create_trading_websocket_client(
    access_token=broker.access_token,
    instrument_keys=trading_instruments,
    callback=lambda data: asyncio.create_task(send_trading_data(data)),
    stop_callback=lambda: logger.info("🛑 Trading WS stream stopped."),
    on_auth_error=lambda: asyncio.create_task(handle_auth_failure_and_close(token)),
)

# For legacy WebSocket (in market_data_websocket function):
client = create_legacy_websocket_client(
    access_token=broker.access_token,
    instrument_keys=chunk,
    callback=lambda data: asyncio.create_task(broadcast(token, data)),
    stop_callback=lambda: logger.info("🛑 One WS stream stopped."),
    on_auth_error=lambda: asyncio.create_task(handle_auth_failure_and_close(token)),
)

# You can also check connection status:
if client.is_connected():
    status = client.get_status()
    logger.info(f"Connection status: {status}")
"""
