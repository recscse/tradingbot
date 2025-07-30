# services/angel/angel_service_factory.py - Angel service factory
"""
Angel WebSocket Service Factory
"""
import logging
from typing import Optional

from typing import Any
from core.config import settings

logger = logging.getLogger(__name__)


def __init__(self):
    # Get credentials from settings instead of os.getenv
    self.client_code = settings.ANGEL_CLIENT_ID
    self.api_key = settings.ANGEL_API_KEY
    self.username = settings.ANGEL_USERNAME
    self.password = settings.ANGEL_PASSWORD
    self.totp_token = getattr(settings, "ANGEL_TOTP_TOKEN", None)

    # Validate credentials
    if not all([self.client_code, self.api_key, self.username, self.password]):
        raise ValueError("Missing Angel credentials in settings")


class AngelServiceFactory:
    """Factory for creating Angel WebSocket service"""

    @staticmethod
    async def create_service() -> Optional[Any]:
        """Create Angel WebSocket service"""

        # Check if credentials are available
        if not all(
            [
                settings.ANGEL_CLIENT_ID,
                settings.ANGEL_API_KEY,
                settings.ANGEL_USERNAME,
                settings.ANGEL_PASSWORD,
                # settings.ANGEL_TOTP_TOKEN,  # Uncomment if TOTP is used
                # settings.ANGEL_REDIRECT_URI,  # Uncomment if redirect URI is used
            ]
        ):
            logger.warning("⚠️ Angel credentials not configured")
            return None

        try:
            from services.angel.angel_ws_services import (
                initialize_angel_websocket,
                get_angel_websocket,
            )

            success = await initialize_angel_websocket()
            if success:
                return get_angel_websocket()
            else:
                logger.error("❌ Angel WebSocket initialization failed")
                return None

        except ImportError as e:
            logger.warning(f"⚠️ Angel WebSocket service not available: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Angel WebSocket service error: {e}")
            return None
