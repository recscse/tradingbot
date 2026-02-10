# services/upstox/ws_client.py

import asyncio
import json
import ssl
import logging
import functools
import inspect
import requests
import websockets
import traceback
from datetime import datetime
from websockets.exceptions import InvalidStatus
from google.protobuf.json_format import MessageToDict
import services.upstox.MarketDataFeed_pb2 as pb

logger = logging.getLogger(__name__)


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
        connection_type="default",  # "dashboard", "trading", "legacy", "centralized_admin"
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
        self.market_closed = False
        self.received_ltp = False
        self.connection_type = connection_type
        self.subscription_mode = subscription_mode
        self.connection_id = f"{connection_type}_{id(self)}"

        # Message sequence tracking
        self.got_market_status = False  # Track if we've received initial market status
        self.got_snapshot = False  # Track if we've received initial snapshot

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
        """Connect to Upstox WebSocket and handle the message sequence properly"""
        logger.info(
            f"🚀 Starting {self.connection_type} WebSocket with {len(self.instrument_keys)} instruments"
        )

        # Apply combined limit (safest approach)
        max_keys = 1500
        if len(self.instrument_keys) > max_keys:
            logger.warning(f"⚠️ Truncating to combined limit: {max_keys} keys")
            self.instrument_keys = self.instrument_keys[:max_keys]

        while self.should_run and self.retry_count <= self.max_retries:
            try:
                ws_url = await self.get_feed_authorized_url()
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                # Connect with explicit parameters
                async with websockets.connect(
                    ws_url,
                    ssl=ssl_context,
                    ping_interval=30,
                    ping_timeout=90,
                    close_timeout=10,
                    max_size=None,
                ) as conn:
                    self.websocket = conn
                    self.retry_count = 0
                    self.auth_error_sent = False
                    self.market_closed = False
                    self.received_ltp = False
                    self.got_market_status = False
                    self.got_snapshot = False

                    logger.info(
                        f"✅ {self.connection_type.title()} WebSocket connected."
                    )

                    # Add delay before subscription
                    await asyncio.sleep(1)
                    await self._send_subscription()

                    # Set up connection monitoring
                    last_activity = datetime.now().timestamp()
                    message_sequence = 0  # Track message sequence

                    while self.should_run:
                        try:
                            # Add timeout to detect stalled connections
                            raw = await asyncio.wait_for(conn.recv(), timeout=60)
                            last_activity = datetime.now().timestamp()
                            message_sequence += 1

                            # Parse binary protobuf message
                            msg = pb.FeedResponse()
                            msg.ParseFromString(raw)
                            parsed = MessageToDict(msg)

                            # Log full parsed data for first few messages to debug
                            if message_sequence <= 3:
                                logger.info(f"Parsed data for ws client - {parsed}")

                            # Process message based on type and sequence
                            msg_type = parsed.get("type")

                            # FIRST MESSAGE: market_info (segment status)
                            if msg_type == "market_info":
                                # First tick should be market status information
                                segment_status = parsed.get("marketInfo", {}).get(
                                    "segmentStatus", {}
                                )
                                logger.info(
                                    f"📊 Market segment statuses: {segment_status}"
                                )

                                # Mark that we've received market status
                                self.got_market_status = True

                                # Process market phases and determine if market is open/closed
                                active_segments, all_markets_closed = (
                                    self._process_market_status(segment_status)
                                )

                                # Send complete data to callback
                                await self.callback(
                                    {
                                        "type": "market_info",
                                        "marketInfo": {"segmentStatus": segment_status},
                                        "active_segments": active_segments,
                                        "all_markets_closed": all_markets_closed,
                                        "currentTs": parsed.get(
                                            "currentTs",
                                            str(int(datetime.now().timestamp() * 1000)),
                                        ),
                                    }
                                )

                                # Check if all markets are closed
                                if all_markets_closed:
                                    logger.info(
                                        f"📴 {self.connection_type}: All markets closed."
                                    )
                                    self.market_closed = True

                            # SECOND MESSAGE: feeds data (prices)
                            elif "feeds" in parsed:
                                # This is the common format for price data
                                feeds = parsed.get("feeds", {})
                                currentTs = parsed.get("currentTs")

                                if not feeds:
                                    logger.warning(
                                        f"⚠️ {self.connection_type}: Received feeds data but it's empty."
                                    )
                                    continue

                                # Mark that we've received LTP data
                                self.received_ltp = True

                                # If this is the first data message, it's the initial snapshot
                                is_snapshot = not self.got_snapshot
                                if is_snapshot:
                                    self.got_snapshot = True
                                    logger.info(
                                        f"📸 {self.connection_type}: Received initial market data snapshot with {len(feeds)} instruments"
                                    )

                                # Log exchange breakdown
                                self._log_exchange_summary(feeds)

                                # Send data to callback - forward the entire parsed message
                                # This preserves the exact format expected by centralized manager
                                await self.callback(parsed)

                                # Check if market is closed and we should stop
                                if self.market_closed and self.received_ltp:
                                    logger.info(
                                        f"📴 {self.connection_type}: Market closed & live data received. Stopping."
                                    )
                                    self.should_run = False

                            # ALTERNATIVE: live_feed message type (older format)
                            elif msg_type == "live_feed":
                                # This is the old format with explicit type
                                feeds = parsed.get("data", {})
                                if not feeds:
                                    logger.warning(
                                        f"⚠️ {self.connection_type}: Received 'live_feed' payload but it's empty."
                                    )
                                    continue

                                # Mark that we've received LTP data
                                self.received_ltp = True

                                # If this is the first data message, it's the initial snapshot
                                is_snapshot = not self.got_snapshot
                                if is_snapshot:
                                    self.got_snapshot = True
                                    logger.info(
                                        f"📸 {self.connection_type}: Received initial market data snapshot with {len(feeds)} instruments"
                                    )

                                # Log exchange breakdown
                                self._log_exchange_summary(feeds)

                                # Send data to callback
                                await self.callback(
                                    {
                                        "type": "live_feed",
                                        "data": feeds,
                                        "is_snapshot": is_snapshot,
                                        "timestamp": parsed.get(
                                            "currentTs",
                                            str(int(datetime.now().timestamp() * 1000)),
                                        ),
                                    }
                                )

                                # Check if market is closed and we should stop
                                if self.market_closed and self.received_ltp:
                                    logger.info(
                                        f"📴 {self.connection_type}: Market closed & live data received. Stopping."
                                    )
                                    self.should_run = False

                            # HEARTBEAT: Keep-alive messages
                            elif msg_type == "heartbeat":
                                logger.debug(
                                    f"💓 {self.connection_type}: Received heartbeat"
                                )

                            # UNKNOWN: Any other message type
                            else:
                                # If we get here, log the message type
                                if any(key for key in parsed if "|" in key):
                                    # This looks like direct instrument data (rare format)
                                    logger.warning(
                                        f"⚠️ {self.connection_type}: Received direct instrument data format."
                                    )
                                    await self.callback(parsed)
                                else:
                                    logger.warning(
                                        f"⚠️ {self.connection_type}: Unknown message type: {msg_type}"
                                    )

                        except asyncio.TimeoutError:
                            # No data received for 60 seconds - check connection
                            inactive_time = datetime.now().timestamp() - last_activity
                            logger.warning(
                                f"⚠️ No data received for {inactive_time:.1f}s - checking connection"
                            )

                            try:
                                # Send manual ping to check connection
                                pong_waiter = await conn.ping()
                                await asyncio.wait_for(pong_waiter, timeout=10)
                                logger.info("✅ Connection ping successful")
                                last_activity = datetime.now().timestamp()
                            except Exception as ping_err:
                                logger.error(f"❌ Connection ping failed: {ping_err}")
                                raise ConnectionError(
                                    "Connection appears dead - reconnecting"
                                )

                    # This line will only execute if the websocket closed gracefully
                    logger.info(
                        f"🔌 {self.connection_type} WebSocket closed gracefully"
                    )

            except PermissionError:
                logger.error(
                    f"🔐 {self.connection_type}: Permission error - token expired"
                )
                await self.callback({"type": "error", "reason": "token_expired"})

                # Don't immediately retry on auth errors
                await asyncio.sleep(5)

                if self.on_auth_error and not self.auth_error_sent:
                    await self.on_auth_error()
                    self.auth_error_sent = True

                self.should_run = False
                break  # Add break to exit the retry loop for permission errors

            except websockets.exceptions.InvalidStatusCode as e:
                status = getattr(e, "status", None)
                logger.error(
                    f"❌ {self.connection_type}: WebSocket rejected: HTTP {status}: {e}"
                )

                if status == 403:
                    if self.on_auth_error and not self.auth_error_sent:
                        await self.on_auth_error()
                        self.auth_error_sent = True

                    # For 403 errors, wait longer before retry
                    await asyncio.sleep(5)

                # Increment retry counter
                self.retry_count += 1

            except (websockets.exceptions.ConnectionClosed, ConnectionError) as e:
                # Handle websocket connection closed errors
                logger.error(f"🔌 {self.connection_type}: Connection closed: {e}")
                self.retry_count += 1

            except Exception as e:
                error_message = str(e)

                # Check if it's a network connectivity issue
                is_network_error = any(
                    keyword in error_message.lower()
                    for keyword in [
                        "getaddrinfo failed",
                        "name resolution",
                        "connection refused",
                        "timeout",
                        "network",
                    ]
                )

                if is_network_error:
                    logger.error(
                        f"🌐 {self.connection_type}: Network connectivity error: {error_message[:100]}"
                    )
                    logger.warning(
                        f"⚠️ {self.connection_type}: Network appears to be down - application will continue running without live market data"
                    )
                    # For network errors, use longer backoff to avoid spamming logs
                    self.retry_count += 1
                    if self.retry_count >= self.max_retries:
                        logger.error(
                            f"❌ {self.connection_type}: Max retries reached due to network issues - WebSocket will remain disconnected until network is restored"
                        )
                        self.should_run = False
                        break
                else:
                    logger.error(f"🔥 {self.connection_type}: Unexpected error: {e}")
                    logger.error(traceback.format_exc())
                    self.retry_count += 1

            # Apply retry backoff only if we're still supposed to run
            if self.should_run and self.retry_count <= self.max_retries:
                # More aggressive backoff for repeated failures
                backoff_delay = min(
                    5 * (2 ** (self.retry_count - 1)), 60
                )  # Max 60 seconds
                logger.info(
                    f"⏳ {self.connection_type}: Retrying in {backoff_delay}s (attempt {self.retry_count}/{self.max_retries})"
                )
                await asyncio.sleep(backoff_delay)

        # After the while loop
        await self._trigger_stop_callback()

    def _process_market_status(self, segment_status):
        """Process market status information and determine if markets are open/closed"""
        # Define market phases based on status
        OPEN_STATUSES = ["NORMAL_OPEN", "PRE_OPEN_START", "PRE_OPEN_END"]
        CLOSING_STATUSES = ["CLOSING_START", "CLOSING_END", "NORMAL_CLOSE"]

        # Check instrument segments - MCX is now handled by dedicated MCX WebSocket service
        has_nse = any("NSE_" in key for key in self.instrument_keys if key)
        has_bse = any("BSE_" in key for key in self.instrument_keys if key)

        # Extract relevant segment statuses - focus only on NSE and BSE
        nse_eq_status = segment_status.get("NSE_EQ", "")
        nse_fo_status = segment_status.get("NSE_FO", "")
        nse_index_status = segment_status.get("NSE_INDEX", "")
        bse_eq_status = segment_status.get("BSE_EQ", "")

        # Determine market phase for each segment
        nse_status = (
            "open"
            if nse_eq_status in OPEN_STATUSES
            else ("closed" if nse_eq_status in CLOSING_STATUSES else "unknown")
        )
        bse_status = (
            "open"
            if bse_eq_status in OPEN_STATUSES
            else ("closed" if bse_eq_status in CLOSING_STATUSES else "unknown")
        )

        # Log market status details - no MCX since it's handled separately
        logger.info(
            f"📊 {self.connection_type}: Market Status - "
            f"NSE: {nse_eq_status} ({nse_status}), "
            f"BSE: {bse_eq_status} ({bse_status})"
        )

        # Determine active segments and overall market status
        active_segments = []
        if has_nse and nse_status == "open":
            active_segments.append("NSE")
        if has_bse and bse_status == "open":
            active_segments.append("BSE")

        # For trading logic - are ALL of our markets closed? (NSE/BSE only)
        all_markets_closed = (not has_nse or nse_status == "closed") and (
            not has_bse or bse_status == "closed"
        )

        return active_segments, all_markets_closed

    def _log_exchange_summary(self, feeds):
        """Log a summary of instruments by exchange - MCX handled by dedicated service"""
        nse_instruments = [k for k in feeds.keys() if k.startswith("NSE_")]
        bse_instruments = [k for k in feeds.keys() if k.startswith("BSE_")]

        # Prepare exchange summary for logging - NSE and BSE only
        exchange_summary = []
        if nse_instruments:
            exchange_summary.append(f"NSE: {len(nse_instruments)}")
        if bse_instruments:
            exchange_summary.append(f"BSE: {len(bse_instruments)}")

        # Log with segment information - MCX instruments should not appear here
        # as they are handled by the dedicated MCX WebSocket service
        logger.info(
            f"✅ {self.connection_type}: Processing {len(feeds)} instruments ({', '.join(exchange_summary)})"
        )

        # Log warning if MCX instruments are detected (they shouldn't be here)
        mcx_instruments = [k for k in feeds.keys() if k.startswith("MCX_")]
        if mcx_instruments:
            logger.warning(
                f"⚠️ {self.connection_type}: Detected {len(mcx_instruments)} MCX instruments - these should be handled by dedicated MCX service"
            )

    async def update_subscriptions(self, new_keys: list):
        """Dynamically update subscriptions without reconnecting"""
        if not self.is_connected():
            self.instrument_keys = new_keys
            return

        # Find keys to add and remove
        old_keys_set = set(self.instrument_keys)
        new_keys_set = set(new_keys)
        
        to_add = list(new_keys_set - old_keys_set)
        to_remove = list(old_keys_set - new_keys_set)
        
        if to_remove:
            logger.info(f"🔄 Unsubscribing from {len(to_remove)} keys")
            await self._send_unsubscription(to_remove)
            
        if to_add:
            logger.info(f"🔄 Subscribing to {len(to_add)} new keys")
            self.instrument_keys = new_keys # Update internal list
            await self._send_subscription(keys=to_add)
        else:
            self.instrument_keys = new_keys

    async def _send_unsubscription(self, keys: list):
        """Send unsubscription request"""
        if not self.websocket or not self.websocket.open:
            return
            
        payload = {
            "guid": f"unsub-{self.connection_id}",
            "method": "unsub",
            "data": {
                "instrumentKeys": keys[:1500]
            }
        }
        await self.websocket.send(json.dumps(payload).encode("utf-8"))

    async def _send_subscription(self, keys: list = None):
        """Send subscription request to WebSocket with enhanced error handling"""
        if not self.websocket:
            logger.error(
                f"❌ {self.connection_type}: Cannot send subscription - no active WebSocket"
            )
            return False

        # Use provided keys or default to self.instrument_keys
        keys_to_subscribe = keys if keys is not None else self.instrument_keys
        if not keys_to_subscribe:
            return True

        # Create unique identifier for this subscription
        guid = f"{self.connection_type}-{self.connection_id}"

        # Determine subscription mode based on connection type
        mode = self.subscription_mode
        if self.connection_type == "trading":
            mode = "full"  # Full market depth for trading
        elif self.connection_type == "dashboard":
            mode = "ltpc"  # Just LTP for dashboard
        elif self.connection_type == "centralized_admin":
            mode = "full"  # Full data for centralized admin

        payload = {
            "guid": guid,
            "method": "sub",
            "data": {
                "mode": mode,
                "instrumentKeys": keys_to_subscribe[:1500],  # Upstox limit
            },
        }

        # Convert to binary data once to avoid repeated encoding
        encoded_payload = json.dumps(payload).encode("utf-8")

        # Try up to 3 times to send the subscription
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                await self.websocket.send(encoded_payload)
                logger.info(
                    f"📩 {self.connection_type.title()}: Subscription sent for {len(keys_to_subscribe[:1500])} instruments in '{mode}' mode"
                )
                return True
            except websockets.exceptions.ConnectionClosed:
                logger.error(
                    f"❌ {self.connection_type}: WebSocket closed while sending subscription (attempt {attempt+1}/{max_attempts})"
                )
                if attempt < max_attempts - 1:
                    await asyncio.sleep(1)  # Brief pause before retry
                    continue
                else:
                    raise  # Re-raise on final attempt
            except Exception as e:
                logger.error(
                    f"❌ {self.connection_type}: Failed to send subscription (attempt {attempt+1}/{max_attempts}): {e}"
                )
                if attempt < max_attempts - 1:
                    await asyncio.sleep(1)  # Brief pause before retry
                    continue
                else:
                    raise  # Re-raise on final attempt

        logger.error(f"❌ {self.connection_type}: All subscription attempts failed")
        return False

    async def _trigger_stop_callback(self):
        """Trigger the stop callback if provided"""
        if self.stop_callback:
            if inspect.iscoroutinefunction(self.stop_callback):
                await self.stop_callback()
            else:
                self.stop_callback()

    def stop(self):
        """Stop the WebSocket client"""
        logger.info(f"🛑 {self.connection_type.title()}: WebSocket manually stopped.")
        self.should_run = False

    def is_connected(self):
        """Check if WebSocket is currently connected"""
        return self.websocket is not None and self.websocket.open and self.should_run

    def get_status(self):
        """Get current connection status"""
        return {
            "connection_type": self.connection_type,
            "is_connected": self.is_connected(),
            "instruments_count": len(self.instrument_keys),
            "received_ltp": self.received_ltp,
            "got_market_status": self.got_market_status,
            "got_snapshot": self.got_snapshot,
            "retry_count": self.retry_count,
            "market_closed": self.market_closed,
        }
