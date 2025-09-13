"""
WebSocket client template for broker integrations.
Follows trading application patterns for real-time data handling.
"""
import asyncio
import json
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from enum import Enum
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """WebSocket connection status enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class WebSocketClient:
    """
    Template WebSocket client for broker integrations.

    Features:
    - Automatic reconnection with exponential backoff
    - Heartbeat mechanism for connection health
    - Event-driven message handling
    - Proper error handling and logging
    - Connection lifecycle management
    """

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        reconnect_interval: float = 5.0,
        max_reconnect_attempts: int = 10,
        heartbeat_interval: float = 30.0
    ) -> None:
        """
        Initialize WebSocket client.

        Args:
            url: WebSocket URL
            headers: Connection headers
            reconnect_interval: Reconnection interval in seconds
            max_reconnect_attempts: Maximum reconnection attempts
            heartbeat_interval: Heartbeat interval in seconds
        """
        self.url = url
        self.headers = headers or {}
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.heartbeat_interval = heartbeat_interval

        # Connection state
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.status = ConnectionStatus.DISCONNECTED
        self.reconnect_count = 0
        self.last_heartbeat = None

        # Event handlers
        self.on_connect: Optional[Callable] = None
        self.on_disconnect: Optional[Callable] = None
        self.on_message: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None

        # Tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None

    async def connect(self) -> bool:
        """
        Connect to WebSocket server.

        Returns:
            True if connection successful, False otherwise
        """
        if self.status == ConnectionStatus.CONNECTED:
            logger.warning("Already connected to WebSocket")
            return True

        try:
            self.status = ConnectionStatus.CONNECTING
            logger.info(f"Connecting to WebSocket: {self.url}")

            self.websocket = await websockets.connect(
                self.url,
                extra_headers=self.headers,
                ping_interval=self.heartbeat_interval,
                ping_timeout=10,
                close_timeout=10
            )

            self.status = ConnectionStatus.CONNECTED
            self.reconnect_count = 0
            self.last_heartbeat = datetime.utcnow()

            logger.info("WebSocket connected successfully")

            # Start heartbeat monitoring
            self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())

            # Notify connection
            if self.on_connect:
                await self.on_connect()

            return True

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            logger.error(f"WebSocket connection failed: {e}")

            if self.on_error:
                await self.on_error(e)

            return False

    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        if self.status == ConnectionStatus.DISCONNECTED:
            return

        logger.info("Disconnecting WebSocket")

        # Cancel tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None

        # Close connection
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

        self.status = ConnectionStatus.DISCONNECTED

        # Notify disconnection
        if self.on_disconnect:
            await self.on_disconnect()

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send message to WebSocket server.

        Args:
            message: Message dictionary to send

        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.is_connected():
            logger.error("Cannot send message: WebSocket not connected")
            return False

        try:
            message_json = json.dumps(message)
            await self.websocket.send(message_json)
            logger.debug(f"Message sent: {message_json}")
            return True

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            await self._handle_connection_error(e)
            return False

    async def listen(self) -> None:
        """Listen for incoming messages."""
        if not self.is_connected():
            logger.error("Cannot listen: WebSocket not connected")
            return

        try:
            async for message in self.websocket:
                try:
                    # Parse message
                    data = json.loads(message)
                    self.last_heartbeat = datetime.utcnow()

                    # Handle message
                    if self.on_message:
                        await self.on_message(data)

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {e}")
            await self._handle_connection_error(e)
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            await self._handle_connection_error(e)
        except Exception as e:
            logger.exception(f"Unexpected error in listen: {e}")
            await self._handle_connection_error(e)

    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return (
            self.status == ConnectionStatus.CONNECTED and
            self.websocket is not None and
            not self.websocket.closed
        )

    async def _handle_connection_error(self, error: Exception) -> None:
        """Handle connection errors with automatic reconnection."""
        logger.error(f"Connection error: {error}")
        self.status = ConnectionStatus.ERROR

        if self.on_error:
            await self.on_error(error)

        # Attempt reconnection
        if self.reconnect_count < self.max_reconnect_attempts:
            await self._schedule_reconnect()
        else:
            logger.error("Max reconnection attempts reached")
            await self.disconnect()

    async def _schedule_reconnect(self) -> None:
        """Schedule reconnection attempt."""
        if self._reconnect_task and not self._reconnect_task.done():
            return

        self.status = ConnectionStatus.RECONNECTING
        self.reconnect_count += 1

        # Exponential backoff
        delay = min(self.reconnect_interval * (2 ** (self.reconnect_count - 1)), 60)
        logger.info(f"Scheduling reconnection attempt {self.reconnect_count} in {delay} seconds")

        self._reconnect_task = asyncio.create_task(self._reconnect_after_delay(delay))

    async def _reconnect_after_delay(self, delay: float) -> None:
        """Reconnect after specified delay."""
        try:
            await asyncio.sleep(delay)

            # Close existing connection
            if self.websocket:
                await self.websocket.close()
                self.websocket = None

            # Attempt reconnection
            success = await self.connect()
            if success:
                # Resume listening
                await self.listen()

        except asyncio.CancelledError:
            logger.info("Reconnection cancelled")
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            await self._handle_connection_error(e)

    async def _heartbeat_monitor(self) -> None:
        """Monitor connection health with heartbeat."""
        try:
            while self.is_connected():
                await asyncio.sleep(self.heartbeat_interval)

                if not self.last_heartbeat:
                    continue

                time_since_heartbeat = (datetime.utcnow() - self.last_heartbeat).total_seconds()

                if time_since_heartbeat > (self.heartbeat_interval * 2):
                    logger.warning("Heartbeat timeout detected")
                    raise ConnectionError("Heartbeat timeout")

        except asyncio.CancelledError:
            logger.info("Heartbeat monitor cancelled")
        except Exception as e:
            logger.error(f"Heartbeat monitor error: {e}")
            await self._handle_connection_error(e)


# Example usage for market data client
class MarketDataWebSocketClient(WebSocketClient):
    """Market data specific WebSocket client."""

    def __init__(self, url: str, auth_token: str) -> None:
        headers = {
            'Authorization': f'Bearer {auth_token}',
            'User-Agent': 'TradingApp/1.0'
        }
        super().__init__(url, headers)

        # Set event handlers
        self.on_connect = self._on_connect_handler
        self.on_message = self._on_message_handler
        self.on_error = self._on_error_handler

    async def subscribe_to_instruments(self, instruments: List[str]) -> bool:
        """Subscribe to market data for instruments."""
        message = {
            'type': 'subscribe',
            'instruments': instruments,
            'mode': 'full'
        }
        return await self.send_message(message)

    async def _on_connect_handler(self) -> None:
        """Handle connection established."""
        logger.info("Market data WebSocket connected")

    async def _on_message_handler(self, data: Dict[str, Any]) -> None:
        """Handle incoming market data message."""
        if data.get('type') == 'live_feed':
            await self._process_market_data(data)

    async def _process_market_data(self, data: Dict[str, Any]) -> None:
        """Process market data with proper decimal precision."""
        feeds = data.get('feeds', {})

        for instrument, feed_data in feeds.items():
            try:
                # Extract price data with Decimal precision
                ltpc = feed_data.get('fullFeed', {}).get('marketFF', {}).get('ltpc', {})

                if ltpc:
                    price_data = {
                        'instrument': instrument,
                        'ltp': Decimal(str(ltpc.get('ltp', 0))),
                        'prev_close': Decimal(str(ltpc.get('cp', 0))),
                        'timestamp': datetime.utcnow()
                    }

                    logger.debug(f"Processed market data: {price_data}")

            except Exception as e:
                logger.error(f"Error processing market data for {instrument}: {e}")

    async def _on_error_handler(self, error: Exception) -> None:
        """Handle WebSocket errors."""
        logger.error(f"Market data WebSocket error: {error}")


# Usage example
async def main():
    """Example usage of WebSocket client."""
    client = MarketDataWebSocketClient(
        url="wss://api.broker.com/ws",
        auth_token="your_auth_token"
    )

    try:
        # Connect
        if await client.connect():
            # Subscribe to instruments
            await client.subscribe_to_instruments(['NSE_EQ|INE062A01020'])

            # Start listening
            await client.listen()

    except KeyboardInterrupt:
        logger.info("Shutting down WebSocket client")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())