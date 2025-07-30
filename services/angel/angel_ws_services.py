# Angel WebSocket Service - Use existing tokens from DB
import logging
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from database.connection import get_db
from database.models import BrokerConfig, User
from datetime import datetime

logger = logging.getLogger(__name__)


class AngelWebSocketManager:
    def __init__(self):
        self.live_data = {}
        self.is_connected = False
        self.sws = None
        self.subscribed_tokens = []

    async def initialize_and_start(self) -> bool:
        """Start Angel WebSocket using existing tokens from DB"""
        try:
            # Get tokens from database
            tokens = await self._get_tokens_from_db()
            if not tokens:
                return False

            # Create WebSocket with existing tokens - exact format
            self.sws = SmartWebSocketV2(
                tokens["auth_token"],
                tokens["api_key"],
                tokens["client_code"],
                tokens["feed_token"],
            )

            # Assign callbacks - exact format
            self.sws.on_open = self._on_open
            self.sws.on_data = self._on_data
            self.sws.on_error = self._on_error
            self.sws.on_close = self._on_close

            # Connect in background (non-blocking)
            import threading

            connect_thread = threading.Thread(target=self.sws.connect, daemon=True)
            connect_thread.start()

            # Return True immediately - connection happens in background
            logger.info("Angel WebSocket connecting in background...")
            return True

        except Exception as e:
            logger.error(f"Angel WebSocket failed: {e}")
            return False

    async def _get_tokens_from_db(self):
        """Get existing auth tokens from database"""
        try:
            db = next(get_db())

            # Get Angel config for admin user
            config = (
                db.query(BrokerConfig)
                .join(BrokerConfig.user)
                .filter(
                    BrokerConfig.broker_name.ilike("%angel%"),
                    BrokerConfig.is_active == True,
                    User.role == "admin",
                )
                .first()
            )

            if not config:
                logger.error("No Angel config found for admin")
                return None

            # Validate tokens exist
            if not all(
                [
                    config.access_token,
                    config.feed_token,
                    config.api_key,
                    config.client_id,
                ]
            ):
                logger.error("Missing required tokens in database")
                return None

            # Return existing tokens
            return {
                "auth_token": config.access_token,
                "feed_token": config.feed_token,
                "api_key": config.api_key,
                "client_code": config.client_id,
            }

        except Exception as e:
            logger.error(f"Error getting tokens from DB: {e}")
            return None
        finally:
            db.close()

    def _on_open(self, wsapp):
        """WebSocket opened"""
        self.is_connected = True
        logger.info("Angel WebSocket connected successfully")

        # Subscribe - exact format
        correlation_id = "live_feed_123"
        mode = 1  # LTP mode
        token_list = [{"exchangeType": 1, "tokens": ["26009", "26000", "11915"]}]

        self.sws.subscribe(correlation_id, mode, token_list)
        self.subscribed_tokens = ["26009", "26000", "11915"]
        logger.info(f"Subscribed to {len(self.subscribed_tokens)} tokens")

    def _on_data(self, wsapp, message):
        """Handle live data"""
        try:
            # Store data with better key handling
            if isinstance(message, dict):
                token = str(message.get("token", message.get("tk", "")))
                if token:
                    # Add timestamp and clean data
                    message["received_at"] = datetime.now().isoformat()
                    self.live_data[token] = message

                    # Log less frequently to avoid spam
                    if len(self.live_data) % 10 == 1:  # Log every 10th update
                        logger.debug(
                            f"Live data updated for {len(self.live_data)} symbols"
                        )
        except Exception as e:
            logger.error(f"Error processing live data: {e}")

    def _on_error(self, wsapp, error):
        """Handle errors"""
        logger.error(f"Angel WebSocket error: {error}")
        self.is_connected = False

    def _on_close(self, wsapp):
        """Handle close"""
        logger.warning("Angel WebSocket connection closed")
        self.is_connected = False

    def close_connection(self):
        """Close connection"""
        if self.sws:
            try:
                self.sws.close_connection()
                logger.info("Angel WebSocket connection closed")
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")

    def get_live_data(self):
        """Get all live data"""
        return self.live_data.copy()

    def get_symbol_data(self, token: str):
        """Get data for specific token"""
        return self.live_data.get(token)

    def get_status(self):
        """Get detailed status"""
        return {
            "is_connected": self.is_connected,
            "subscribed_tokens": len(self.subscribed_tokens),
            "live_symbols": len(self.live_data),
            "tokens": self.subscribed_tokens,
            "last_update": (
                max([data.get("received_at", "") for data in self.live_data.values()])
                if self.live_data
                else None
            ),
        }

    async def stop(self):
        """Stop WebSocket"""
        self.close_connection()


# Global instance
_angel_websocket = None


async def initialize_angel_websocket():
    """Initialize Angel WebSocket"""
    global _angel_websocket
    try:
        _angel_websocket = AngelWebSocketManager()
        success = await _angel_websocket.initialize_and_start()
        if success:
            logger.info("✅ Angel WebSocket service started successfully")
        return success
    except Exception as e:
        logger.error(f"❌ Angel WebSocket init failed: {e}")
        return False


def get_angel_websocket():
    """Get Angel WebSocket instance"""
    return _angel_websocket
