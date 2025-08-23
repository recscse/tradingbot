"""
Centralized WebSocket Manager for Trading System

This module implements a singleton WebSocket manager that maintains one
persistent connection to Upstox and broadcasts data to all components.

FIXED VERSION - Resolves circular import issues and removes redundancies
"""

import asyncio
import json
import logging
import os
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, Set, List, Optional, Callable, Any, Union
import aiohttp
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from core.config import ADMIN_EMAIL

# Configure logging first
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import Redis manager with error handling
try:
    from services.trading_red import TradingSafeRedisManager

    redis_manager = TradingSafeRedisManager()
except ImportError as e:
    logger.warning(f"⚠️ Redis manager not available: {e}")
    redis_manager = None

try:
    from services.market_data_queue import get_market_queue_service

    QUEUE_SERVICE_AVAILABLE = True
    logger.info("✅ Market Data Queue Service available for integration")
except ImportError:
    QUEUE_SERVICE_AVAILABLE = False
    logger.warning("⚠️ Market Data Queue Service not available")


# Import instrument service with proper error handling
def get_instrument_service():
    """Safely get instrument service instance"""
    try:
        from services.instrument_refresh_service import get_trading_service

        return get_trading_service()
    except ImportError:
        return None


def get_instrument_keys_safely():
    """Safely get instrument keys from various sources"""
    try:
        from services.instrument_refresh_service import (
            get_websocket_keys,
            get_dashboard_keys,
            get_optimized_realtime_subscription,
        )

        # Try optimized subscription first
        try:
            optimized = get_optimized_realtime_subscription()
            if optimized and "all_keys" in optimized and optimized["all_keys"]:
                return optimized["all_keys"]
        except Exception:
            pass

        # Try dashboard keys
        try:
            dashboard_keys = get_dashboard_keys()
            if dashboard_keys:
                return dashboard_keys
        except Exception:
            pass

        # Try websocket keys
        try:
            ws_keys = get_websocket_keys()
            if ws_keys:
                return ws_keys
        except Exception:
            pass

    except ImportError:
        pass

    return []


# Import WebSocket client with fallback
try:
    from services.upstox.ws_client import UpstoxWebSocketClient
except ImportError:
    logger.warning("⚠️ UpstoxWebSocketClient not available - using dummy implementation")

    class UpstoxWebSocketClient:
        def __init__(self, **kwargs):
            self.is_connected = False

        async def connect_and_stream(self):
            pass

        def stop(self):
            pass

        def is_connected(self):
            return False


# Import database functions with error handling
try:
    from database.connection import get_db
    from database.models import BrokerConfig, User
except ImportError:
    logger.warning("⚠️ Database models not available - using dummy implementations")

    def get_db():
        yield None

    class BrokerConfig:
        pass

    class User:
        pass


# Import email service with error handling
try:
    from services.email.email_service import email_service
except ImportError:
    logger.warning("⚠️ Email service not available")

    class DummyEmailService:
        def send_notification(self, *args, **kwargs):
            return False

    email_service = DummyEmailService()

# Import market data service with error handling
try:
    from services.live_market_data_service import LiveMarketDataService
except ImportError:
    logger.warning("⚠️ LiveMarketDataService not available")

    class DummyMarketDataService:
        def __init__(self):
            pass

    LiveMarketDataService = DummyMarketDataService

# Callback type definition
CallbackFunction = Callable[[Dict[str, Any]], Any]


class CentralizedWebSocketManager:
    """
    Singleton WebSocket manager that maintains one connection to Upstox
    and broadcasts data to multiple components
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Connection state
        self.admin_token: Optional[str] = None
        self.admin_user_id: Optional[int] = None
        self.ws_client: Optional[UpstoxWebSocketClient] = None
        self.is_running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.last_connection_attempt = None
        self.last_websocket_url = None
        self._shutdown_scheduled = False

        # Subscription management
        self.all_instrument_keys: Set[str] = set()
        self.active_instrument_keys: Set[str] = set()
        self.primary_instruments: Set[str] = set()
        self.connection_ready = asyncio.Event()

        # Data caching
        self.market_data_cache: Dict[str, dict] = {}
        self.market_status = "unknown"
        self.market_segment_status = {}
        self.market_phases = {}
        self.active_segments = []
        self.all_markets_closed = True
        self.last_data_received = None
        self.data_count = 0
        self.update_count = 0

        # Client management
        self.dashboard_clients: Dict[str, WebSocket] = {}
        self.trading_clients: Dict[str, WebSocket] = {}
        self.client_subscriptions: Dict[str, Set[str]] = {}

        # Callback registration
        self.callbacks: Dict[str, List[CallbackFunction]] = {
            "price_update": [],
            "market_status": [],
            "connection_status": [],
            "error": [],
        }

        # Performance metrics
        self.performance_metrics = {
            "messages_received": 0,
            "updates_processed": 0,
            "callbacks_executed": 0,
            "clients_updated": 0,
            "reconnection_count": 0,
            "last_latency_ms": 0,
            "avg_latency_ms": 0,
        }

        # Background tasks
        self.background_tasks = set()

        # Initialize market data service
        self.market_data = LiveMarketDataService()

        self._initialized = True
        logger.info("✅ Centralized WebSocket manager initialized")

        if QUEUE_SERVICE_AVAILABLE:
            try:
                self.queue_service = get_market_queue_service()
                self.queue_integration_enabled = True
                logger.info("✅ Queue service integration enabled")
            except Exception as e:
                logger.error(f"❌ Failed to initialize queue service: {e}")
                self.queue_service = None
                self.queue_integration_enabled = False
        else:
            self.queue_service = None
            self.queue_integration_enabled = False

    async def initialize(self) -> bool:
        """Initialize the manager with admin token from database"""
        try:
            logger.info("🔧 Initializing Centralized WebSocket manager...")

            # Reset connection event and shutdown flag
            self.connection_ready.clear()
            self._shutdown_scheduled = False

            # Load admin token
            if not await self._load_admin_token():
                logger.error("❌ Failed to load admin token")
                return False

            # Load instrument keys
            await self._load_instrument_keys()

            # Verify we have keys
            if not self.all_instrument_keys:
                logger.error(
                    "❌ No instrument keys loaded - WebSocket initialization failed"
                )
                return False

            logger.info(f"✅ Loaded {len(self.all_instrument_keys)} instrument keys")

            # Load the latest market snapshot
            snapshot_loaded = await self._load_market_snapshot()

            # Determine market hours
            current_time = datetime.now().time()
            current_day = datetime.now().weekday()
            market_should_be_open = (
                current_day < 5  # Weekday check (0=Monday, 4=Friday)
                and current_time >= datetime.strptime("09:15:00", "%H:%M:%S").time()
                and current_time <= datetime.strptime("15:30:00", "%H:%M:%S").time()
            )

            # Update connection status
            self.is_running = True
            logger.info(
                f"✅ Centralized WebSocket manager initialized with {len(self.all_instrument_keys)} instruments"
            )

            # Stop existing connection if any
            if (
                self.ws_client
                and hasattr(self.ws_client, "is_connected")
                and self.ws_client.is_connected()
            ):
                logger.info("🔄 Restarting existing WebSocket connection with new keys")
                self.ws_client.stop()

            # Start connection based on market hours
            if market_should_be_open:
                logger.info("🔄 Market should be open - starting WebSocket connection")
                task = asyncio.create_task(self._maintain_connection())
                self.background_tasks.add(task)
                task.add_done_callback(self.background_tasks.discard)
            else:
                logger.info(
                    "💤 Market is likely closed - using snapshot data until market reopens"
                )
                self._schedule_market_open_check()

            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize centralized manager: {e}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return False

    async def _validate_token_expiry(self, broker_config) -> dict:
        """Validate token expiry and return detailed status"""
        try:
            now = datetime.now()
            expiry = broker_config.access_token_expiry
            
            if not expiry:
                return {
                    "valid": False,
                    "reason": "no_expiry_info",
                    "message": "Token expiry information not available"
                }
            
            if expiry <= now:
                minutes_expired = int((now - expiry).total_seconds() / 60)
                return {
                    "valid": False,
                    "reason": "expired",
                    "message": f"Token expired {minutes_expired} minutes ago",
                    "expired_minutes": minutes_expired
                }
            
            minutes_until_expiry = int((expiry - now).total_seconds() / 60)
            
            if minutes_until_expiry <= 10:
                return {
                    "valid": False,
                    "reason": "expiring_soon",
                    "message": f"Token expires in {minutes_until_expiry} minutes",
                    "minutes_remaining": minutes_until_expiry
                }
            
            return {
                "valid": True,
                "reason": "valid",
                "message": f"Token valid for {minutes_until_expiry} minutes",
                "minutes_remaining": minutes_until_expiry
            }
            
        except Exception as e:
            return {
                "valid": False,
                "reason": "validation_error",
                "message": f"Error validating token: {str(e)}"
            }

    async def _load_admin_token(self) -> bool:
        """Load admin token from database"""
        try:
            db = next(get_db())
            if db is None:
                logger.error("❌ Database not available")
                return False

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

            # Validate token format
            token = admin_broker.access_token
            if not token or len(token.strip()) < 20:
                logger.error(
                    f"❌ Invalid token format in database (length: {len(token) if token else 0})"
                )
                return False

            # Validate token expiry BEFORE storing
            validation_result = await self._validate_token_expiry(admin_broker)
            
            # If token is expired or expiring soon, refresh it BEFORE storing
            if not validation_result["valid"] and validation_result["reason"] in ["expired", "expiring_soon"]:
                reason = validation_result["reason"]
                message = validation_result["message"]
                
                if reason == "expired":
                    logger.error(f"❌ Admin token expired: {message}")
                elif reason == "expiring_soon":
                    logger.warning(f"⚠️ Admin token expiring soon: {message}")
                
                logger.info(f"🤖 Attempting automated token refresh for {reason} token BEFORE storing...")
                
                try:
                    refresh_success = await self._try_automated_refresh()
                    if refresh_success:
                        logger.info("✅ Automated token refresh completed - reloading fresh token")
                        # Recursively reload to get the fresh token
                        return await self._load_admin_token()
                    else:
                        logger.warning("⚠️ Automated token refresh failed - will store expired token and retry on connection failure")
                        # Fall through to store the expired token as fallback
                except Exception as refresh_error:
                    logger.error(f"❌ Error during automated token refresh: {refresh_error}")
                    # Fall through to store the expired token as fallback
            
            # Store token and user ID (only reached if valid OR refresh failed)
            self.admin_token = token.strip()
            self.admin_user_id = admin_broker.user_id
            self._token_validation_status = validation_result

            # Log with masked token for security
            token_preview = (
                f"{self.admin_token[:5]}...{self.admin_token[-5:]}"
                if len(self.admin_token) > 10
                else "***"
            )
            
            if validation_result["valid"]:
                logger.info(
                    f"✅ Admin token loaded for user ID: {self.admin_user_id} - Token: {token_preview}"
                )
                logger.info(f"ℹ️ {validation_result['message']}")
            else:
                reason = validation_result["reason"]
                message = validation_result["message"]
                logger.info(f"⚠️ Admin token loaded with issues for user ID: {self.admin_user_id} - {message}")
                
            # Set automation trigger flag for future cycles
            if not validation_result["valid"] and validation_result["reason"] in ["expired", "expiring_soon"]:
                self._needs_token_refresh = True
                if validation_result["reason"] == "expired":
                    logger.info("🔄 Token expired but loaded for refresh attempt")
            else:
                self._needs_token_refresh = False
                
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load admin token: {e}")
            traceback.print_exc()
            return False
            
    async def _try_automated_refresh(self) -> bool:
        """
        Attempt automated token refresh using the automation service
        """
        try:
            logger.info("🤖 Attempting automated token refresh...")
            
            # Import automation service dynamically to avoid circular imports
            from services.upstox_automation_service import UpstoxAutomationService
            
            automation_service = UpstoxAutomationService()
            # ✅ FIX: Add emergency bypass for expired tokens
            result = await automation_service.refresh_admin_upstox_token(emergency_bypass=True)
            
            if result.get("success", False):
                logger.info("✅ Automated token refresh completed successfully")
                
                # ✅ FIX: Add delay before reloading to ensure database is updated
                logger.info("⏳ Waiting for database update to complete...")
                await asyncio.sleep(2)
                
                # Reload the admin token after successful refresh
                token_reloaded = await self._load_admin_token()
                if token_reloaded:
                    logger.info("✅ Admin token reloaded after automated refresh")
                    return True
                else:
                    logger.error("❌ Failed to reload token after automated refresh")
                    return False
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"❌ Automated token refresh failed: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error during automated token refresh: {e}")
            return False


    async def _validate_and_refresh_token(self) -> bool:
        """Proactively validate token and refresh if needed"""
        try:
            if not self.admin_token:
                logger.warning("⚠️ No admin token available, loading...")
                return await self._load_admin_token()
            
            # Check token expiry from database
            from database.connection import SessionLocal
            from database.models import BrokerConfig
            from core.config import ADMIN_EMAIL
            
            with SessionLocal() as db:
                admin_user = db.query(BrokerConfig).filter(
                    BrokerConfig.user.has(email=ADMIN_EMAIL),
                    BrokerConfig.broker_name.ilike("upstox"),
                    BrokerConfig.is_active == True,
                ).first()
                
                if not admin_user or not admin_user.access_token_expiry:
                    logger.warning("⚠️ No admin broker config found")
                    return await self._load_admin_token()
                
                # Check if token is expired or expires soon (within 10 minutes)
                from datetime import datetime, timedelta
                now = datetime.now()
                buffer_time = timedelta(minutes=10)
                
                if admin_user.access_token_expiry <= (now + buffer_time):
                    logger.info(f"🔄 Token expires soon ({admin_user.access_token_expiry}), refreshing...")
                    
                    # Try automatic refresh
                    refresh_success = await self._try_automated_refresh()
                    if refresh_success:
                        # Reload the new token
                        return await self._load_admin_token()
                    else:
                        logger.error("❌ Proactive token refresh failed")
                        return False
                
                logger.debug(f"✅ Token valid until {admin_user.access_token_expiry}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error validating token: {e}")
            return False

    async def reload_admin_token(self) -> bool:
        """
        Reload admin token after successful refresh
        This method should be called by the automation service after token refresh
        """
        try:
            logger.info("🔄 Reloading admin token after successful refresh...")
            
            # Clear current token
            old_token = self.admin_token
            self.admin_token = None
            self.admin_user_id = None
            
            # Load fresh token from database
            token_loaded = await self._load_admin_token()
            
            if token_loaded and self.admin_token != old_token:
                logger.info("✅ Admin token successfully reloaded with new value")
                
                # Stop existing WebSocket connection if any
                if self.ws_client:
                    logger.info("🔄 Stopping existing WebSocket connection to use new token...")
                    self.ws_client.stop()
                    
                # Clear connection ready flag to trigger reconnection
                self.connection_ready.clear()
                
                # Reset reconnect attempts to allow fresh connection with new token
                self.reconnect_attempts = 0
                
                # Start fresh connection with new token
                await self.start_connection()
                
                return True
            elif token_loaded:
                logger.warning("⚠️ Token reloaded but value unchanged")
                return True
            else:
                logger.error("❌ Failed to reload admin token")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error reloading admin token: {e}")
            return False
    
    async def force_reconnect(self) -> bool:
        """
        Force reconnection with current token - useful after token refresh
        """
        try:
            logger.info("🔄 Forcing WebSocket reconnection...")
            
            # Stop existing connection
            if self.ws_client:
                self.ws_client.stop()
            
            # Clear connection state
            self.connection_ready.clear()
            self.reconnect_attempts = 0
            
            # Wait a moment for cleanup
            await asyncio.sleep(1)
            
            # Start fresh connection
            await self.start_connection()
            
            logger.info("✅ Force reconnection initiated")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during force reconnection: {e}")
            return False

    async def _load_instrument_keys(self):
        """Load instrument keys - CLEAN & SIMPLE approach with service initialization"""
        try:
            logger.info("🔄 Loading focused instrument keys...")

            # Ensure instrument service is initialized first
            from services.instrument_refresh_service import get_trading_service, get_focused_instrument_keys
            
            service = get_trading_service()
            if not getattr(service, '_service_initialized', False):
                logger.info("🔧 Initializing instrument service for WebSocket...")
                try:
                    init_result = await service.initialize_service()
                    logger.info(f"✅ Service initialization: {init_result.status if hasattr(init_result, 'status') else 'completed'}")
                except Exception as init_error:
                    logger.warning(f"⚠️ Service initialization failed, continuing with available data: {init_error}")

            # Get all focused keys (now with initialized service)
            focused_data = get_focused_instrument_keys()

            if focused_data and focused_data.get("keys"):
                self.all_instrument_keys = set(focused_data["keys"])

                # Simple logging
                total = len(self.all_instrument_keys)
                breakdown = focused_data.get("breakdown", {})

                logger.info(f"✅ Loaded {total} focused instrument keys:")
                logger.info(f"   F&O Spots: {breakdown.get('fno_equity_spots', 0)}")
                logger.info(f"   Indices: {breakdown.get('selected_indices', 0)}")
                logger.info(f"   MCX Futures: {breakdown.get('mcx_futures', 0)}")
                logger.info(f"   MCX Options: {breakdown.get('mcx_options', 0)}")

                return True
            else:
                logger.error("❌ Failed to load focused instrument keys")
                # Simple fallback
                return await self._load_fallback_keys()

        except Exception as e:
            logger.error(f"❌ Error loading instrument keys: {e}")
            return await self._load_fallback_keys()

    async def _load_fallback_keys(self):
        """Simple fallback implementation"""
        try:
            instrument_service = get_instrument_service()
            if not instrument_service:
                logger.error("❌ Instrument service not available")
                return False

            # Get spot keys only
            spot_keys = instrument_service.get_spot_instrument_keys()
            if spot_keys:
                self.all_instrument_keys = set(spot_keys)
                logger.info(f"✅ Fallback loaded {len(spot_keys)} spot keys")
                return True

            # Emergency fallback - Include FNO stocks and indices
            from services.fno_stock_service import get_fno_stocks_from_file
            emergency_keys = ["NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank", "BSE_INDEX|SENSEX"]
            
            # Add top FNO stocks for better data coverage
            try:
                fno_stocks = get_fno_stocks_from_file()
                if fno_stocks:
                    # Add top 50 FNO stocks by volume/activity
                    top_fno = [stock for stock in fno_stocks if stock.get('symbol') and stock.get('exchange') == 'NSE'][:50]
                    for stock in top_fno:
                        if stock.get('symbol'):
                            # Use NSE_EQ format for equity stocks
                            emergency_keys.append(f"NSE_EQ|{stock['symbol']}")
                    
                    logger.info(f"✅ Added {len(top_fno)} top FNO stocks to emergency fallback")
            except Exception as e:
                logger.warning(f"⚠️ Could not load FNO stocks for fallback: {e}")
            
            self.all_instrument_keys = set(emergency_keys)
            logger.warning(
                f"⚠️ Emergency fallback: {len(self.all_instrument_keys)} keys (indices + FNO stocks)"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Fallback failed: {e}")
            return False

    async def start_connection(self):
        """Start the centralized WebSocket connection"""
        if not self.is_running:
            if not await self.initialize():
                logger.error("❌ Failed to initialize manager, cannot start connection")
                return False

        # Reset for fresh start
        self.reconnect_attempts = 0
        self.last_connection_attempt = datetime.now()

        # Start connection in background task
        task = asyncio.create_task(self._maintain_connection())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

        logger.info("🚀 Centralized WebSocket connection starting...")
        return True

    async def _check_network_connectivity(self) -> bool:
        """Check if basic network connectivity is available"""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5)
            ) as session:
                async with session.get("https://www.google.com") as response:
                    return response.status == 200
        except Exception as e:
            logger.warning(f"⚠️ Network connectivity check failed: {e}")
            return False

    async def _maintain_connection(self):
        """Maintain WebSocket connection with auto-reconnect"""
        while self.is_running and self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                # Check network connectivity
                if not await self._check_network_connectivity():
                    logger.warning(
                        "⚠️ Network connectivity issues detected - waiting before retry"
                    )
                    await asyncio.sleep(60)
                    continue

                # Refresh admin token if needed
                if self.reconnect_attempts > 0:
                    await self._load_admin_token()

                # Start WebSocket client
                await self._start_ws_client()

                # Wait for connection to end
                await asyncio.sleep(
                    3600
                )  # Long sleep, will be interrupted by exceptions

            except asyncio.CancelledError:
                logger.info("🛑 Connection maintenance task cancelled")
                break

            except Exception as e:
                self.reconnect_attempts += 1
                self.performance_metrics["reconnection_count"] += 1
                logger.error(f"❌ WebSocket connection failed: {e}")

                # Reset connection event
                self.connection_ready.clear()

                if self.reconnect_attempts < self.max_reconnect_attempts:
                    backoff_delay = min(
                        5 * (2**self.reconnect_attempts), 300
                    )  # Max 5 minutes
                    logger.info(
                        f"⏳ Reconnecting in {backoff_delay}s (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})"
                    )

                    # Send warning email if approaching max attempts
                    if self.reconnect_attempts == self.max_reconnect_attempts - 2:
                        await self._send_reconnection_warning_email()

                    await asyncio.sleep(backoff_delay)
                else:
                    logger.error("❌ Max reconnection attempts reached")
                    self.is_running = False
                    await self._send_max_reconnections_email()
                    await self._broadcast_connection_status(
                        {
                            "status": "failed",
                            "message": "Max reconnection attempts reached",
                        }
                    )

    async def _start_ws_client(self):
        """Start the actual WebSocket client"""
        try:
            # Validate and refresh token before starting connection
            await self._validate_and_refresh_token()
            
            # Stop existing client
            if self.ws_client:
                self.ws_client.stop()

            # Limit instrument keys to Upstox maximum (~1500)
            active_keys = list(self.all_instrument_keys)
            if len(active_keys) > 1500:
                active_keys = active_keys[:1500]
                logger.warning(
                    f"⚠️ Limited to 1500 instruments (from {len(self.all_instrument_keys)})"
                )

            self.active_instrument_keys = set(active_keys)

            # Create client
            self.ws_client = UpstoxWebSocketClient(
                access_token=self.admin_token,
                instrument_keys=active_keys,
                callback=self._handle_market_data,
                stop_callback=self._handle_connection_stop,
                on_auth_error=self._handle_auth_error,
                connection_type="centralized_admin",
                subscription_mode="full",
                max_retries=3,
            )

            # Reset data count
            self.data_count = 0
            self.last_connection_attempt = datetime.now()
            logger.info(
                f"🔌 Starting WebSocket connection with {len(active_keys)} instruments"
            )

            # Clear connection ready event
            self.connection_ready.clear()

            # Start streaming
            await self.ws_client.connect_and_stream()

        except Exception as e:
            logger.error(f"❌ Failed to start WebSocket client: {e}")
            raise

    async def _handle_market_data(self, data: dict):
        """Handle incoming market data with enhanced format handling"""
        try:
            start_time = time.time()
            self._last_raw_data = data.copy() if isinstance(data, dict) else data
            self.last_data_received = datetime.now()
            self.performance_metrics["messages_received"] += 1

            # Signal connection is working
            if not self.connection_ready.is_set():
                self.connection_ready.set()
                logger.info("✅ WebSocket connection is receiving data")
                await self._broadcast_connection_status(
                    {
                        "status": "connected",
                        "message": "WebSocket connection established",
                    }
                )

            # Determine message type
            msg_type = data.get("type")
            has_feeds = "feeds" in data

            # Handle market_info messages
            if msg_type == "market_info" or "marketInfo" in data:
                await self._handle_market_info(data)

            # Handle feeds format (main data format)
            elif has_feeds:
                await self._handle_feeds_data(data)

            # Handle live_feed messages (older format)
            elif msg_type == "live_feed":
                await self._handle_live_feed_data(data)

            elif msg_type == "heartbeat":
                logger.debug("💓 Received heartbeat")

            elif msg_type == "error":
                logger.error(f"❌ Market data error: {data}")
                await self._execute_callbacks("error", data)
                await self._broadcast_error(data)

            else:
                # Handle direct instrument data format
                if any(key for key in data if "|" in key):
                    await self._handle_direct_instrument_data(data)
                else:
                    logger.warning(f"⚠️ Unknown message format: {str(data)[:200]}...")

            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            self.performance_metrics["last_latency_ms"] = processing_time

            # Update average latency
            if self.performance_metrics["avg_latency_ms"] == 0:
                self.performance_metrics["avg_latency_ms"] = processing_time
            else:
                self.performance_metrics["avg_latency_ms"] = (
                    0.95 * self.performance_metrics["avg_latency_ms"]
                    + 0.05 * processing_time
                )

            try:
                # This is a separate method to avoid circular imports
                await self._update_instrument_registry(data)
            except Exception as e:
                logger.debug(f"⚠️ Registry update error: {e}")

        except Exception as e:
            logger.error(f"❌ Error handling market data: {e}")
            logger.error(traceback.format_exc())

    async def _handle_market_info(self, data: dict):
        """Handle market info/status messages"""
        segment_status = data.get("status", {})
        if not segment_status and "marketInfo" in data:
            segment_status = data.get("marketInfo", {}).get("segmentStatus", {})

        # Process market status
        phases = {}
        active_segments = data.get("active_segments", [])
        all_markets_closed = data.get("all_markets_closed", True)

        # Extract phases and active segments
        if not active_segments:
            for segment, status in segment_status.items():
                exchange = segment.split("_")[0] if "_" in segment else segment
                is_open = "OPEN" in status
                phases[exchange] = "open" if is_open else "closed"
                if is_open and exchange not in active_segments:
                    active_segments.append(exchange)
            all_markets_closed = len(active_segments) == 0

        # Update market status
        prev_status = self.market_status
        self.market_status = phases.get("NSE", "unknown").lower()
        self.market_segment_status = segment_status
        self.market_phases = phases
        self.active_segments = active_segments
        self.all_markets_closed = all_markets_closed

        if prev_status != self.market_status:
            logger.info(
                f"📈 Market status updated: {self.market_status} (active segments: {active_segments})"
            )
            await self._broadcast_market_status()

            await self._execute_callbacks(
                "market_status",
                {
                    "status": self.market_status,
                    "segment_status": segment_status,
                    "phases": phases,
                    "active_segments": active_segments,
                    "all_markets_closed": all_markets_closed,
                    "previous_status": prev_status,
                    "timestamp": data.get("currentTs", datetime.now().isoformat()),
                },
            )

            # Check if markets closed and schedule shutdown
            if all_markets_closed and self.data_count > 0:
                logger.info("🔔 Market closed - initiating cleanup process")
                await self._store_market_snapshot()
                self._schedule_market_close_shutdown()

    async def _handle_feeds_data(self, data: dict):
        """🚀 Handle feeds format data with ultra-fast hub integration + ZERO-DELAY streaming"""
        feeds = data.get("feeds", {})
        update_count = len(feeds)
        is_snapshot = self.update_count == 0

        if update_count > 0:
            self.data_count += update_count
            self.update_count += 1

            # 🚀 CRITICAL: ZERO-DELAY real-time streaming to UI FIRST (before any processing)
            try:
                from services.realtime_data_streamer import realtime_streamer
                # This bypasses ALL processing and sends raw data directly to UI
                await realtime_streamer.stream_raw_market_data(data)
            except ImportError:
                logger.debug("Real-time streamer not available - using legacy path")
            except Exception as e:
                logger.debug(f"Real-time streaming error: {e}")

            # 🚨 CRITICAL: ZERO-DELAY breakout detection (parallel with UI streaming)
            try:
                from services.realtime_breakout_detector import realtime_breakout_detector
                # Process breakouts in parallel (non-blocking)
                asyncio.create_task(realtime_breakout_detector.process_realtime_data(data))
            except ImportError:
                logger.debug("Real-time breakout detector not available")
            except Exception as e:
                logger.debug(f"Real-time breakout detection error: {e}")

            # Log data reception
            if is_snapshot:
                logger.info(
                    f"📸 Received initial snapshot with {update_count} instruments (ZERO-DELAY streaming active)"
                )
            elif self.update_count % 50 == 0:  # Less frequent logging for performance
                logger.info(
                    f"📊 Received update #{self.update_count} with {update_count} instruments (total: {self.data_count})"
                )

            # 🚀 BACKGROUND: All data processing happens in parallel (non-blocking)
            # This includes enrichment, analytics, caching - UI already got raw data above
            asyncio.create_task(self._background_data_processing(feeds, is_snapshot, data))
                
            logger.debug(f"✅ ZERO-DELAY streaming + background processing initiated for {len(feeds)} instruments")

    async def _background_data_processing(self, feeds: dict, is_snapshot: bool, data: dict):
        """Background processing that doesn't block the main data flow"""
        try:
            # Legacy cache and registry updates (background only)
            await asyncio.gather(
                self._update_cache(feeds),
                self._legacy_registry_update(feeds),
                self._broadcast_live_data(feeds, is_snapshot),
                return_exceptions=True
            )

            # Execute callbacks (background)
            await self._execute_callbacks(
                "price_update",
                {
                    "data": feeds,
                    "is_snapshot": is_snapshot,
                    "update_count": self.update_count,
                    "timestamp": data.get("currentTs", datetime.now().isoformat()),
                    "source": "centralized_background"
                },
            )
        except Exception as e:
            logger.debug(f"Background processing error: {e}")

    async def _legacy_data_processing(self, feeds: dict, is_snapshot: bool, data: dict):
        """Legacy fallback processing"""
        await asyncio.gather(
            self._update_cache(feeds),
            self._update_instrument_registry(feeds),
            self._broadcast_live_data(feeds, is_snapshot),
            return_exceptions=True
        )

        await self._execute_callbacks(
            "price_update",
            {
                "data": feeds,
                "is_snapshot": is_snapshot,
                "update_count": self.update_count,
                "timestamp": data.get("currentTs", datetime.now().isoformat()),
                "source": "centralized_legacy"
            },
        )

    async def _legacy_registry_update(self, feeds: dict):
        """Legacy registry update (background only)"""
        try:
            from services.instrument_registry import instrument_registry
            normalized_data = self._normalize_market_data(feeds)
            if normalized_data:
                instrument_registry.update_live_prices(normalized_data)
        except Exception as e:
            logger.debug(f"Legacy registry update error: {e}")

    async def _handle_live_feed_data(self, data: dict):
        """Handle live_feed format data with ZERO-DELAY streaming"""
        feeds = data.get("data", {})
        update_count = len(feeds)
        is_snapshot = data.get("is_snapshot", False)

        if update_count > 0:
            self.data_count += update_count
            self.update_count += 1

            # 🚀 CRITICAL: ZERO-DELAY streaming FIRST
            try:
                from services.realtime_data_streamer import realtime_streamer
                await realtime_streamer.stream_raw_market_data(data)
            except Exception as e:
                logger.debug(f"Real-time streaming error: {e}")

            if is_snapshot or self.update_count == 1:
                logger.info(
                    f"📸 Received initial snapshot with {update_count} instruments (ZERO-DELAY)"
                )
            elif self.update_count % 10 == 0:
                logger.info(
                    f"📊 Received update #{self.update_count} with {update_count} instruments (total: {self.data_count})"
                )

            # ⚡ PERFORMANCE FIX: Run cache updates and broadcasting in parallel for faster response
            await asyncio.gather(
                self._update_cache(feeds),
                self._update_instrument_registry(feeds),
                self._broadcast_live_data(feeds, is_snapshot),
                return_exceptions=True  # Don't let one failure block others
            )

            await self._execute_callbacks(
                "price_update",
                {
                    "data": feeds,
                    "is_snapshot": is_snapshot,
                    "update_count": self.update_count,
                    "timestamp": data.get("timestamp", datetime.now().isoformat()),
                },
            )

    async def _handle_direct_instrument_data(self, data: dict):
        """Handle direct instrument data format with ZERO-DELAY streaming"""
        is_snapshot = self.update_count == 0
        update_count = len(data)
        self.data_count += update_count
        self.update_count += 1

        # 🚀 CRITICAL: ZERO-DELAY streaming FIRST
        try:
            from services.realtime_data_streamer import realtime_streamer
            await realtime_streamer.stream_raw_market_data(data)
        except Exception as e:
            logger.debug(f"Real-time streaming error: {e}")

        logger.info(
            f"📊 Received direct instrument data format with {update_count} instruments (ZERO-DELAY)"
        )

        await self._update_cache(data)
        await self._update_instrument_registry(data)
        await self._broadcast_live_data(data, is_snapshot)

        await self._execute_callbacks(
            "price_update",
            {
                "data": data,
                "is_snapshot": is_snapshot,
                "update_count": self.update_count,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def _update_instrument_registry(self, feed_data: dict):
        """✅ SIMPLE FIX: Send data directly to React frontend via unified manager"""
        try:
            if not feed_data:
                return

            # 🚀 REMOVED: Redundant unified manager calls
            # These are now handled by instrument_registry.update_live_prices() callbacks
            # which provide ZERO DELAY for strategies and optimized UI batching
            logger.debug(f"⚡ OPTIMIZED: Data will be broadcast via instrument registry callbacks")
                
        except Exception as e:
            logger.error(f"❌ Error in optimized broadcast: {e}")
                
            # Original registry update (background)
            try:
                from services.instrument_registry import instrument_registry
                normalized_data = self._normalize_market_data(feed_data)
                if normalized_data:
                    instrument_registry.update_live_prices(normalized_data)
            except Exception as e:
                logger.warning(f"⚠️ Registry update error: {e}")
                
        except Exception as e:
            logger.error(f"❌ Error in _update_instrument_registry: {e}")


    def _normalize_market_data(self, feed_data: dict) -> dict:
        """COMPLETE: Handle all Upstox formats with full error handling"""
        normalized = {}
        stats = {"success": 0, "errors": 0, "empty": 0, "invalid_format": 0}

        for instrument_key, raw_data in feed_data.items():
            try:
                # Validate input
                if not self._validate_raw_input(instrument_key, raw_data):
                    stats["invalid_format"] += 1
                    continue

                # Extract based on format
                extracted = self._extract_by_format(raw_data)
                if not extracted:
                    stats["empty"] += 1
                    continue

                # Enrich with metadata
                enriched = self._enrich_with_metadata(instrument_key, extracted)
                if enriched:
                    normalized[instrument_key] = enriched
                    stats["success"] += 1
                else:
                    stats["errors"] += 1

            except Exception as e:
                stats["errors"] += 1
                logger.debug(f"Error processing {instrument_key}: {e}")

        if stats["success"] > 0:
            logger.debug(
                f"📊 Processed: {stats['success']} success, {stats['errors']} errors, {stats['empty']} empty"
            )

        return normalized

    def _validate_raw_input(self, instrument_key: str, raw_data: Any) -> bool:
        """Validate raw input data"""
        if not instrument_key or "|" not in instrument_key:
            return False
        if not isinstance(raw_data, dict):
            return False
        if "fullFeed" not in raw_data:
            return False
        return True

    def _extract_by_format(self, raw_data: dict) -> Optional[dict]:
        """Extract data based on Upstox format type"""
        full_feed = raw_data.get("fullFeed", {})

        # Format 1: Market Data (NSE_EQ, NSE_FO, MCX_FO)
        if "marketFF" in full_feed:
            return self._extract_market_format(full_feed["marketFF"])

        # Format 2: Index Data (NSE_INDEX, BSE_INDEX)
        elif "indexFF" in full_feed:
            return self._extract_index_format(full_feed["indexFF"])

        return None

    def _extract_market_format(self, market_ff: dict) -> dict:
        """Extract from marketFF format"""
        data = {}

        # Core price data
        if "ltpc" in market_ff and market_ff["ltpc"]:
            ltpc = market_ff["ltpc"]
            data.update(
                {
                    "ltp": self._safe_float(ltpc.get("ltp")),
                    "cp": self._safe_float(ltpc.get("cp")),
                    "ltq": self._safe_int(ltpc.get("ltq")),
                    "ltt": self._safe_string(ltpc.get("ltt")),
                }
            )

        # Volume data
        if "vtt" in market_ff:
            data["volume"] = self._safe_int(market_ff.get("vtt"))

        # OHLC data
        if "marketOHLC" in market_ff:
            ohlc_data = market_ff["marketOHLC"].get("ohlc", [])
            daily_data = self._extract_daily_ohlc(ohlc_data)
            if daily_data:
                data.update(daily_data)

        # Options data (if present)
        if "optionGreeks" in market_ff and market_ff["optionGreeks"]:
            greeks = market_ff["optionGreeks"]
            data["option_greeks"] = {
                "delta": self._safe_float(greeks.get("delta")),
                "theta": self._safe_float(greeks.get("theta")),
                "gamma": self._safe_float(greeks.get("gamma")),
                "vega": self._safe_float(greeks.get("vega")),
                "rho": self._safe_float(greeks.get("rho")),
            }

        # Open Interest (for derivatives)
        if "oi" in market_ff:
            data["open_interest"] = self._safe_float(market_ff.get("oi"))

        # Average Trade Price
        if "atp" in market_ff:
            data["avg_trade_price"] = self._safe_float(market_ff.get("atp"))

        # Bid/Ask data
        if "marketLevel" in market_ff and "bidAskQuote" in market_ff["marketLevel"]:
            bid_ask = market_ff["marketLevel"]["bidAskQuote"]
            if bid_ask and len(bid_ask) > 0 and bid_ask[0]:
                first_level = bid_ask[0]
                data.update(
                    {
                        "bid_price": self._safe_float(first_level.get("bidP")),
                        "bid_qty": self._safe_int(first_level.get("bidQ")),
                        "ask_price": self._safe_float(first_level.get("askP")),
                        "ask_qty": self._safe_int(first_level.get("askQ")),
                    }
                )

        return data

    def _extract_index_format(self, index_ff: dict) -> dict:
        """Extract from indexFF format"""
        data = {}

        # Index LTPC
        if "ltpc" in index_ff and index_ff["ltpc"]:
            ltpc = index_ff["ltpc"]
            data.update(
                {
                    "ltp": self._safe_float(ltpc.get("ltp")),
                    "cp": self._safe_float(ltpc.get("cp")),
                    "ltt": self._safe_string(ltpc.get("ltt")),
                }
            )

        # Index OHLC
        if "marketOHLC" in index_ff:
            ohlc_data = index_ff["marketOHLC"].get("ohlc", [])
            daily_data = self._extract_daily_ohlc(ohlc_data)
            if daily_data:
                data.update(daily_data)

        return data

    def _extract_daily_ohlc(self, ohlc_list: list) -> Optional[dict]:
        """Extract daily OHLC from list"""
        if not isinstance(ohlc_list, list):
            return None

        # Find daily interval
        for ohlc in ohlc_list:
            if isinstance(ohlc, dict) and ohlc.get("interval") == "1d":
                return {
                    "open": self._safe_float(ohlc.get("open")),
                    "high": self._safe_float(ohlc.get("high")),
                    "low": self._safe_float(ohlc.get("low")),
                    "close": self._safe_float(ohlc.get("close")),
                    "daily_volume": self._safe_int(ohlc.get("vol")),
                }

        return None

    def _enrich_with_metadata(
        self, instrument_key: str, extracted_data: dict
    ) -> Optional[dict]:
        """Enrich data with symbol metadata"""
        try:
            # Resolve symbol
            symbol_info = self._resolve_instrument_symbol(instrument_key)
            if not symbol_info:
                return None

            # Calculate derived metrics
            self._calculate_price_metrics(extracted_data)

            # Create enriched structure with frontend-compatible field names
            enriched = {
                # Identifiers
                "instrument_key": instrument_key,
                "symbol": symbol_info["symbol"],
                "name": symbol_info["name"],
                "exchange": symbol_info["exchange"],
                "sector": symbol_info["sector"],
                "instrument_type": symbol_info["type"],
                # Price data with frontend-compatible field names
                **extracted_data,
                # CRITICAL FIX: Add frontend-compatible field mapping
                "last_price": extracted_data.get("ltp", 0),  # Map ltp → last_price for frontend
                # Metadata
                "timestamp": datetime.now().isoformat(),
                "data_source": "upstox_live",
                "processing_time": datetime.now().isoformat(),
            }

            return enriched

        except Exception as e:
            logger.debug(f"Error enriching {instrument_key}: {e}")
            return None

    def _resolve_instrument_symbol(self, instrument_key: str) -> Optional[dict]:
        """Resolve instrument key to symbol and metadata"""
        try:
            parts = instrument_key.split("|")
            if len(parts) != 2:
                return None

            exchange_segment, identifier = parts

            # NSE Equity with ISIN
            if "NSE_EQ" in exchange_segment:
                return self._resolve_nse_equity(identifier, instrument_key)

            # NSE Index
            elif "NSE_INDEX" in exchange_segment:
                return self._resolve_nse_index(identifier)

            # BSE Index
            elif "BSE_INDEX" in exchange_segment:
                return self._resolve_bse_index(identifier)

            # NSE F&O
            elif "NSE_FO" in exchange_segment:
                return self._resolve_nse_fo(instrument_key, identifier)

            # MCX F&O
            elif "MCX_FO" in exchange_segment:
                return self._resolve_mcx_fo(instrument_key, identifier)

            return None

        except Exception as e:
            logger.debug(f"Error resolving {instrument_key}: {e}")
            return None

    def _resolve_nse_equity(self, isin: str, instrument_key: str) -> Optional[dict]:
        """Resolve NSE equity ISIN to symbol"""
        # Comprehensive ISIN mapping
        isin_mapping = {
            "INE002A01018": {
                "symbol": "RELIANCE",
                "name": "Reliance Industries Limited",
            },
            "INE467B01029": {
                "symbol": "TCS",
                "name": "Tata Consultancy Services Limited",
            },
            "INE040A01034": {"symbol": "HDFCBANK", "name": "HDFC Bank Limited"},
            "INE090A01013": {"symbol": "ICICIBANK", "name": "ICICI Bank Limited"},
            "INE090A01021": {"symbol": "INFY", "name": "Infosys Limited"},
            "INE216A01030": {"symbol": "AXISBANK", "name": "Axis Bank Limited"},
            "INE238A01034": {"symbol": "SBIN", "name": "State Bank of India"},
            "INE397D01024": {"symbol": "BHARTIARTL", "name": "Bharti Airtel Limited"},
            "INE726G01019": {"symbol": "WIPRO", "name": "Wipro Limited"},
            "INE213A01029": {"symbol": "HCLTECH", "name": "HCL Technologies Limited"},
            "INE001A01036": {"symbol": "EICHERMOT", "name": "Eicher Motors Limited"},
            "INE545U01014": {"symbol": "TECHM", "name": "Tech Mahindra Limited"},
            # Add from your sample data
            "INE498L01015": {"symbol": "INDIGO", "name": "InterGlobe Aviation Limited"},
            "INE176B01034": {
                "symbol": "BPCL",
                "name": "Bharat Petroleum Corporation Limited",
            },
            "INE053F01010": {"symbol": "ANILINDIA", "name": "Anil Chemicals Limited"},
            "INE121J01017": {"symbol": "PAGEIND", "name": "Page Industries Limited"},
            "INE200M01039": {"symbol": "RELAXO", "name": "Relaxo Footwears Limited"},
            "INE288B01029": {"symbol": "NESTLEIND", "name": "Nestle India Limited"},
            "INE935A01035": {
                "symbol": "ADANIGREEN",
                "name": "Adani Green Energy Limited",
            },
            "INE918I01026": {"symbol": "ZOMATO", "name": "Zomato Limited"},
        }

        instrument_service = get_instrument_service()

        if instrument_service and hasattr(instrument_service, "_instrument_by_key"):
            instrument_data = instrument_service._instrument_by_key.get(instrument_key)

            symbol = getattr(instrument_data, "trading_symbol", None)
            if not symbol:
                symbol = getattr(instrument_data, "symbol", "unknown")

            name = getattr(instrument_data, "name", isin)

            # stock_info = isin_mapping.get(isin)
            sector = self._get_sector_for_symbol(symbol)
            return {
                "symbol": symbol,
                "name": name,
                "exchange": "NSE",
                "sector": sector,
                "type": "EQ",
            }
        else:
            logger.debug(
                f"Instrument data not found in service for key: {instrument_key} (ISIN: {isin})"
            )

        return None

    def _resolve_nse_index(self, identifier: str) -> Optional[dict]:
        """FIXED: Resolve NSE index with better matching"""
        index_mapping = {
            "Nifty 50": {"symbol": "NIFTY", "name": "Nifty 50"},
            "NIFTY": {"symbol": "NIFTY", "name": "Nifty 50"},
            "Nifty Bank": {"symbol": "BANKNIFTY", "name": "Nifty Bank"},
            "BANKNIFTY": {"symbol": "BANKNIFTY", "name": "Nifty Bank"},
            "Nifty Fin Service": {
                "symbol": "FINNIFTY",
                "name": "Nifty Financial Services",
            },
            "Nifty Financial Services": {
                "symbol": "FINNIFTY",
                "name": "Nifty Financial Services",
            },
            "FINNIFTY": {"symbol": "FINNIFTY", "name": "Nifty Financial Services"},
            "Nifty Midcap 50": {"symbol": "MIDCPNIFTY", "name": "Nifty Midcap 50"},
            "NIFTY MID SELECT": {"symbol": "MIDCPNIFTY", "name": "Nifty Midcap 50"},
            "MIDCPNIFTY": {"symbol": "MIDCPNIFTY", "name": "Nifty Midcap 50"},
        }

        # Try exact match first
        index_info = index_mapping.get(identifier)
        if index_info:
            logger.debug(f"✅ Index resolved: {identifier} → {index_info['symbol']}")
            return {
                "symbol": index_info["symbol"],
                "name": index_info["name"],
                "exchange": "NSE",
                "sector": "INDEX",
                "type": "INDEX",
            }

        # Try partial matching
        for key, info in index_mapping.items():
            if identifier in key or key in identifier:
                logger.debug(
                    f"✅ Index resolved (partial): {identifier} → {info['symbol']}"
                )
                return {
                    "symbol": info["symbol"],
                    "name": info["name"],
                    "exchange": "NSE",
                    "sector": "INDEX",
                    "type": "INDEX",
                }

        logger.warning(f"⚠️ Unknown NSE index: {identifier}")
        return None

    def _resolve_bse_index(self, identifier: str) -> Optional[dict]:
        """FIXED: Resolve BSE index with better matching"""
        if "SENSEX" in identifier or identifier == "SENSEX":
            logger.debug(f"✅ BSE Index resolved: {identifier} → SENSEX")
            return {
                "symbol": "SENSEX",
                "name": "S&P BSE Sensex",
                "exchange": "BSE",
                "sector": "INDEX",
                "type": "INDEX",
            }

        logger.warning(f"⚠️ Unknown BSE index: {identifier}")
        return None

    def _resolve_nse_fo(self, instrument_key: str, identifier: str) -> Optional[dict]:
        """Resolve NSE F&O instruments"""
        try:
            # Try to get from instrument registry
            from services.instrument_registry import instrument_registry

            if hasattr(instrument_registry, "_instrument_by_key"):
                instr = instrument_registry._instrument_by_key.get(instrument_key)
                if instr:
                    symbol = getattr(instr, "symbol", None) or getattr(
                        instr, "underlying_symbol", None
                    )
                    if symbol:
                        sector = self._get_sector_for_symbol(symbol)
                        return {
                            "symbol": symbol,
                            "name": getattr(instr, "name", symbol),
                            "exchange": "NSE",
                            "sector": sector,
                            "type": getattr(instr, "instrument_type", "FO"),
                        }

            return None

        except Exception:
            return None

    def _resolve_mcx_fo(self, instrument_key: str, identifier: str) -> Optional[dict]:
        """Resolve MCX F&O instruments"""
        try:
            # Try to get from instrument registry
            from services.instrument_registry import instrument_registry

            if hasattr(instrument_registry, "_instrument_by_key"):
                instr = instrument_registry._instrument_by_key.get(instrument_key)
                if instr:
                    symbol = getattr(instr, "symbol", None) or getattr(
                        instr, "underlying_symbol", None
                    )
                    if symbol:
                        return {
                            "symbol": symbol,
                            "name": getattr(instr, "name", symbol),
                            "exchange": "MCX",
                            "sector": "COMMODITY",
                            "type": getattr(instr, "instrument_type", "FO"),
                        }

            return None

        except Exception:
            return None

    def _get_sector_for_symbol(self, symbol: str) -> str:
        """FIXED: Get sector for symbol with better error handling"""
        try:
            from services.sector_mapping import SYMBOL_TO_SECTOR

            sector = SYMBOL_TO_SECTOR.get(symbol.upper(), "OTHER")
            logger.debug(f"📊 Sector mapping: {symbol} → {sector}")
            return sector

        except ImportError:
            logger.warning("⚠️ Sector mapping not available")
            return "OTHER"
        except Exception as e:
            logger.warning(f"⚠️ Error getting sector for {symbol}: {e}")
            return "OTHER"

    def _calculate_price_metrics(self, data: dict):
        """Calculate derived price metrics"""
        ltp = data.get("ltp")
        cp = data.get("cp")

        if ltp and cp and cp > 0:
            change = ltp - cp
            change_percent = (change / cp) * 100

            data.update(
                {"change": round(change, 2), "change_percent": round(change_percent, 2)}
            )

            # Price trend
            if change_percent > 2:
                data["trend"] = "strong_bullish"
            elif change_percent > 0:
                data["trend"] = "bullish"
            elif change_percent < -2:
                data["trend"] = "strong_bearish"
            elif change_percent < 0:
                data["trend"] = "bearish"
            else:
                data["trend"] = "neutral"

        # Volatility calculation
        high = data.get("high")
        low = data.get("low")
        if high and low and ltp:
            range_percent = ((high - low) / ltp) * 100
            if range_percent > 5:
                data["volatility"] = "high"
            elif range_percent > 2:
                data["volatility"] = "medium"
            else:
                data["volatility"] = "low"

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safe float conversion"""
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    def _safe_int(self, value: Any) -> Optional[int]:
        """Safe int conversion"""
        try:
            return int(float(value)) if value is not None else None
        except (ValueError, TypeError):
            return None

    def _safe_string(self, value: Any) -> Optional[str]:
        """Safe string conversion"""
        try:
            return str(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    async def _store_market_snapshot(self):
        """Store the current market data snapshot to Redis"""
        try:
            if not redis_manager:
                logger.warning(
                    "⚠️ Cannot store market snapshot: Redis manager not available"
                )
                return False

            snapshot_data = {
                "market_data": self.market_data_cache,
                "market_status": self.market_status,
                "market_segment_status": self.market_segment_status,
                "market_phases": self.market_phases,
                "active_segments": self.active_segments,
                "last_update_time": datetime.now().isoformat(),
                "update_count": self.update_count,
                "data_count": self.data_count,
                "snapshot_time": datetime.now().isoformat(),
            }

            # Store with 24-hour TTL
            success = redis_manager.set(
                "market_data_snapshot", snapshot_data, ttl=86400
            )

            if success:
                logger.info(
                    f"💾 Stored market data snapshot with {len(self.market_data_cache)} instruments to Redis"
                )

                # Store individual instruments for faster access
                for instrument_key, data in self.market_data_cache.items():
                    redis_key = f"market_data:{instrument_key}"
                    redis_manager.set(redis_key, data, ttl=86400)

                return True
            else:
                logger.warning("⚠️ Failed to store market data snapshot to Redis")
                return False

        except Exception as e:
            logger.error(f"❌ Error storing market snapshot: {e}")
            logger.error(traceback.format_exc())
            return False

    def _schedule_market_close_shutdown(self):
        """Schedule a delayed shutdown after market close"""
        if self._shutdown_scheduled:
            return

        self._shutdown_scheduled = True

        async def delayed_shutdown():
            logger.info(
                "⏳ Scheduled shutdown after market close - waiting 2 minutes for final data"
            )
            await asyncio.sleep(120)

            await self._store_market_snapshot()
            await self._broadcast_connection_status(
                {
                    "status": "market_closed",
                    "message": "Market is closed - WebSocket connection will be stopped until market reopens",
                }
            )

            if self.ws_client:
                self.ws_client.stop()
                self.ws_client = None

            logger.info("🛑 WebSocket connection stopped due to market close")

            await self._execute_callbacks(
                "connection_status",
                {
                    "status": "market_closed_shutdown",
                    "message": "WebSocket connection stopped due to market close",
                    "timestamp": datetime.now().isoformat(),
                },
            )

            self._schedule_market_open_check()

        task = asyncio.create_task(delayed_shutdown())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    async def _load_market_snapshot(self):
        """Load the latest market data snapshot from Redis"""
        try:
            if not redis_manager:
                logger.warning(
                    "⚠️ Cannot load market snapshot: Redis manager not available"
                )
                return False

            snapshot_data = redis_manager.get("market_data_snapshot")
            if not snapshot_data:
                logger.info("ℹ️ No market data snapshot found in Redis")
                return False

            # Restore data from snapshot
            self.market_data_cache = snapshot_data.get("market_data", {})
            self.market_status = snapshot_data.get("market_status", "unknown")
            self.market_segment_status = snapshot_data.get("market_segment_status", {})
            self.market_phases = snapshot_data.get("market_phases", {})
            self.active_segments = snapshot_data.get("active_segments", [])
            self.update_count = snapshot_data.get("update_count", 0)
            self.data_count = snapshot_data.get("data_count", 0)

            snapshot_time = snapshot_data.get("snapshot_time")
            logger.info(
                f"📂 Restored market data snapshot with {len(self.market_data_cache)} instruments from {snapshot_time}"
            )

            # Broadcast restored snapshot to clients
            if self.market_data_cache:
                for client_id, ws in list(self.dashboard_clients.items()):
                    try:
                        await self._send_to_client(
                            ws,
                            {
                                "type": "restored_snapshot",
                                "data": self.market_data_cache,
                                "market_open": False,
                                "data_source": "REDIS_SNAPSHOT",
                                "snapshot_time": snapshot_time,
                                "timestamp": datetime.now().isoformat(),
                            },
                        )
                    except Exception as e:
                        logger.warning(
                            f"⚠️ Failed to send snapshot to client {client_id}: {e}"
                        )

            await self._broadcast_market_status()
            return True

        except Exception as e:
            logger.error(f"❌ Error loading market snapshot: {e}")
            logger.error(traceback.format_exc())
            return False

    def _schedule_market_open_check(self):
        """Schedule periodic checks for market open"""

        async def check_market_open():
            while self.is_running:
                try:
                    current_time = datetime.now().time()
                    current_day = datetime.now().weekday()

                    market_should_be_open = (
                        current_day < 5
                        and current_time
                        >= datetime.strptime("09:15:00", "%H:%M:%S").time()
                        and current_time
                        <= datetime.strptime("15:30:00", "%H:%M:%S").time()
                    )

                    if market_should_be_open and not self.connection_ready.is_set():
                        logger.info(
                            "🔔 Market opening time detected - starting WebSocket connection"
                        )
                        self._shutdown_scheduled = False

                        task = asyncio.create_task(self._maintain_connection())
                        self.background_tasks.add(task)
                        task.add_done_callback(self.background_tasks.discard)

                        await asyncio.sleep(60)

                    sleep_time = 300 if not market_should_be_open else 1800
                    await asyncio.sleep(sleep_time)

                except Exception as e:
                    logger.error(f"❌ Error in market open check: {e}")
                    await asyncio.sleep(300)

        task = asyncio.create_task(check_market_open())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    async def _update_cache(self, feed_data: dict):
        """Update market data cache with proper data extraction and field mapping"""
        if not feed_data:
            return

        processed_count = 0
        indices_count = 0
        stocks_count = 0

        # Process each instrument
        for instrument_key, raw_data in feed_data.items():
            try:
                # Extract data based on Upstox feed structure
                extracted_data = self._extract_market_data(instrument_key, raw_data)
                
                if extracted_data and extracted_data.get("ltp", 0) > 0:
                    # CRITICAL FIX: Add frontend-compatible field mapping
                    processed_data = {
                        **extracted_data,
                        "last_price": extracted_data.get("ltp", 0),  # Map ltp → last_price for frontend
                        "symbol": self._extract_symbol_from_key(instrument_key),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Update cache with processed data
                    self.market_data_cache[instrument_key] = processed_data
                    processed_count += 1
                    
                    # Count by type
                    if "INDEX|" in instrument_key:
                        indices_count += 1
                    else:
                        stocks_count += 1
                else:
                    # Still store raw data for debugging but mark as incomplete
                    incomplete_data = {
                        "raw_data": raw_data,
                        "symbol": self._extract_symbol_from_key(instrument_key),
                        "ltp": 0,
                        "last_price": 0,
                        "status": "incomplete",
                        "timestamp": datetime.now().isoformat()
                    }
                    self.market_data_cache[instrument_key] = incomplete_data

            except Exception as e:
                logger.warning(f"⚠️ Error processing {instrument_key}: {e}")

        # Log processing stats
        if processed_count > 0:
            logger.info(f"📊 Processed {processed_count} instruments ({indices_count} indices, {stocks_count} stocks)")

        # Store in Redis if available
        if redis_manager and processed_count > 0:
            try:
                essential_data = {}
                for key, data in self.market_data_cache.items():
                    if isinstance(data, dict) and data.get("ltp", 0) > 0:
                        essential_data[key] = {
                            "ltp": data.get("ltp", 0),
                            "last_price": data.get("last_price", 0),  # Include frontend field
                            "ltq": data.get("ltq"),
                            "cp": data.get("cp"),
                            "symbol": data.get("symbol"),
                            "timestamp": data.get("timestamp", datetime.now().isoformat()),
                        }

                redis_manager.set("market_data_cache", essential_data, ttl=3600)
            except Exception as e:
                logger.warning(f"⚠️ Failed to store market data in Redis: {e}")

    def _extract_market_data(self, instrument_key: str, raw_data: dict) -> dict:
        """Extract market data from Upstox feed structure"""
        try:
            extracted = {}
            
            # Handle different Upstox data structures
            if isinstance(raw_data, dict):
                full_feed = raw_data.get("fullFeed", {})
                
                # For indices: indexFF -> ltpc
                if "indexFF" in full_feed:
                    ltpc_data = full_feed["indexFF"].get("ltpc", {})
                    if ltpc_data and ltpc_data.get("ltp"):
                        extracted = {
                            "ltp": ltpc_data.get("ltp", 0),
                            "ltt": ltpc_data.get("ltt"),
                            "cp": ltpc_data.get("cp", 0),
                            "change": ltpc_data.get("ltp", 0) - ltpc_data.get("cp", 0),
                            "type": "index"
                        }
                        # Calculate change percentage
                        if ltpc_data.get("cp", 0) > 0:
                            extracted["change_percent"] = round(
                                ((ltpc_data.get("ltp", 0) - ltpc_data.get("cp", 0)) / ltpc_data.get("cp", 0)) * 100, 2
                            )
                
                # For stocks: marketFF -> ltpc
                elif "marketFF" in full_feed:
                    ltpc_data = full_feed["marketFF"].get("ltpc", {})
                    market_level = full_feed["marketFF"].get("marketLevel", {})
                    
                    # Sometimes stock data is in ltpc
                    if ltpc_data and ltpc_data.get("ltp"):
                        extracted = {
                            "ltp": ltpc_data.get("ltp", 0),
                            "ltt": ltpc_data.get("ltt"),
                            "cp": ltpc_data.get("cp", 0),
                            "ltq": ltpc_data.get("ltq", 0),
                            "change": ltpc_data.get("ltp", 0) - ltpc_data.get("cp", 0),
                            "type": "stock"
                        }
                        # Calculate change percentage
                        if ltpc_data.get("cp", 0) > 0:
                            extracted["change_percent"] = round(
                                ((ltpc_data.get("ltp", 0) - ltpc_data.get("cp", 0)) / ltpc_data.get("cp", 0)) * 100, 2
                            )
                    
                    # Sometimes data is in marketLevel
                    elif market_level:
                        bid_ask = market_level.get("bidAsk", {})
                        if bid_ask:
                            # Use bid/ask as fallback
                            bid_price = bid_ask.get("bid", [{}])[0].get("price", 0) if bid_ask.get("bid") else 0
                            ask_price = bid_ask.get("ask", [{}])[0].get("price", 0) if bid_ask.get("ask") else 0
                            
                            if bid_price > 0 or ask_price > 0:
                                ltp = (bid_price + ask_price) / 2 if bid_price > 0 and ask_price > 0 else (bid_price or ask_price)
                                extracted = {
                                    "ltp": ltp,
                                    "bid": bid_price,
                                    "ask": ask_price,
                                    "type": "stock",
                                    "source": "bid_ask"
                                }
                
                # Direct data format (fallback)
                elif raw_data.get("ltp"):
                    extracted = {
                        "ltp": raw_data.get("ltp", 0),
                        "ltt": raw_data.get("ltt"),
                        "cp": raw_data.get("cp", 0),
                        "ltq": raw_data.get("ltq", 0),
                        "type": "direct"
                    }
                    
            return extracted
            
        except Exception as e:
            logger.warning(f"⚠️ Error extracting data for {instrument_key}: {e}")
            return {}

    def _extract_symbol_from_key(self, instrument_key: str) -> str:
        """Extract symbol from instrument key"""
        try:
            # Format: "NSE_EQ|RELIANCE" or "NSE_INDEX|Nifty 50"
            if "|" in instrument_key:
                return instrument_key.split("|", 1)[1]
            return instrument_key
        except:
            return instrument_key

    async def _broadcast_market_status(self):
        """Broadcast market status to all clients"""
        status_data = {
            "type": "market_info",
            "marketStatus": self.market_status,
            "segmentStatus": self.market_segment_status,
            "phases": self.market_phases,
            "activeSegments": self.active_segments,
            "source": "centralized",
            "timestamp": datetime.now().isoformat(),
        }

        await self._send_to_all_clients(status_data)
        logger.info(
            f"📡 Broadcasted market status: {self.market_status} (active: {self.active_segments})"
        )

    async def _broadcast_live_data(self, feed_data: dict, is_snapshot: bool = False):
        """Broadcast live data to clients"""
        if not feed_data:
            return

        self.performance_metrics["updates_processed"] += 1
        total_clients = len(self.dashboard_clients) + len(self.trading_clients)

        if total_clients == 0:
            return

        timestamp = datetime.now().isoformat()
        clients_updated = 0

        # Send to dashboard clients (all data)
        dashboard_payload = {
            "type": "dashboard_update",
            "data": feed_data,
            "market_open": self.market_status == "open",
            "data_source": "CENTRALIZED_WS",
            "timestamp": timestamp,
            "update_count": self.update_count,
            "is_snapshot": is_snapshot,
        }

        clients_updated += await self._send_to_client_group(
            self.dashboard_clients, dashboard_payload
        )

        # Send to trading clients (filtered by subscription)
        for client_id, ws in self.trading_clients.items():
            subscribed_keys = self.client_subscriptions.get(client_id, set())
            if not subscribed_keys:
                continue

            relevant_data = {
                key: value for key, value in feed_data.items() if key in subscribed_keys
            }
            if relevant_data:
                trading_payload = {
                    "type": "trading_update",
                    "data": relevant_data,
                    "market_open": self.market_status == "open",
                    "timestamp": timestamp,
                    "update_count": self.update_count,
                    "is_snapshot": is_snapshot,
                }

                if await self._send_to_client(ws, trading_payload):
                    clients_updated += 1

        self.performance_metrics["clients_updated"] = clients_updated

        # Log broadcast stats
        if is_snapshot:
            logger.info(
                f"📡 Broadcast initial snapshot to {clients_updated}/{total_clients} clients"
            )
        elif self.update_count % 20 == 0:
            logger.info(
                f"📡 Broadcast update #{self.update_count} to {clients_updated}/{total_clients} clients"
            )

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

        if total_sent > 0:
            logger.debug(f"📤 Sent to {total_sent} clients")

    async def _send_to_client_group(self, client_group: dict, data: dict) -> int:
        """Send data to a group of clients"""
        if not client_group:
            return 0

        disconnected_ids = []
        sent_count = 0

        for client_id, ws in client_group.items():
            success = await self._send_to_client(ws, data)
            if success:
                sent_count += 1
            else:
                disconnected_ids.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_ids:
            await self.remove_client(client_id)

        return sent_count

    async def _send_to_client(self, ws: WebSocket, data: dict) -> bool:
        """Send data to a single client"""
        try:
            if ws.client_state != WebSocketState.CONNECTED:
                return False

            await ws.send_json(data)
            return True

        except Exception as e:
            logger.debug(f"⚠️ Failed to send to client: {str(e)[:100]}")
            return False

    async def _handle_connection_stop(self):
        """Handle WebSocket connection stop"""
        logger.warning("🛑 WebSocket connection stopped")
        self.ws_client = None
        self.connection_ready.clear()

        await self._broadcast_connection_status(
            {"status": "disconnected", "message": "WebSocket connection lost"}
        )

        await self._execute_callbacks(
            "connection_status",
            {
                "status": "disconnected",
                "message": "WebSocket connection lost",
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def _handle_auth_error(self):
        """Handle authentication errors"""
        logger.error("🔐 Admin token authentication failed")
        self.connection_ready.clear()

        # First try to trigger automated token refresh
        logger.info("🔄 Attempting automated token refresh...")
        refresh_success = await self._try_automated_refresh()
        
        if refresh_success:
            logger.info("✅ Automated token refresh successful, reloading token...")
            token_refreshed = await self._load_admin_token()
            if token_refreshed:
                logger.info("✅ New token loaded, triggering reconnection...")
                # Reset reconnect attempts to allow retry with new token
                self.reconnect_attempts = 0
                # Clear any connection ready flag to force reconnect
                self.connection_ready.clear()
                return
        
        # Fallback: Try to reload token from database (in case it was manually refreshed)
        token_refreshed = await self._load_admin_token()

        if not token_refreshed:
            # Send error notification with enhanced troubleshooting
            subject = "🚨 Critical: Trading Bot Admin Token Expired"
            message = f"""
            The admin token for the centralized WebSocket manager has expired.
            Automated refresh failed - manual intervention required.
            
            Immediate action required:
            1. Log in to the admin dashboard
            2. Refresh the Upstox broker connection manually
            3. Verify the new token is valid
            
            If running on Windows and automation fails:
            1. Browser automation may not work due to subprocess limitations
            2. Consider running from WSL for automated token refresh
            3. Use manual token refresh via Upstox website as workaround
            
            System Impact:
            - Real-time market data will not be available
            - Trading signals may be delayed
            - Dashboard updates will stop
            
            Time: {datetime.now()}
            Reconnect attempts: {self.reconnect_attempts}/{self.max_reconnect_attempts}
            """

            try:
                email_sent = email_service.send_notification(
                    recipient_email=ADMIN_EMAIL, subject=subject, message=message
                )
                if email_sent:
                    logger.info("📧 Sent admin token expiration alert")
            except Exception as e:
                logger.error(f"❌ Error sending token expiration email: {e}")

            await self._broadcast_error(
                {
                    "reason": "admin_token_expired",
                    "message": "Admin authentication failed. Please contact administrator.",
                }
            )

            await self._execute_callbacks(
                "error",
                {
                    "reason": "admin_token_expired",
                    "message": "Admin authentication failed",
                    "timestamp": datetime.now().isoformat(),
                },
            )

            self.is_running = False

    async def _execute_callbacks(self, event_type: str, data: dict):
        """Execute registered callbacks for an event type"""
        if event_type not in self.callbacks:
            return

        callbacks = self.callbacks[event_type]
        if not callbacks:
            return

        if "timestamp" not in data:
            data["timestamp"] = datetime.now().isoformat()

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)

                self.performance_metrics["callbacks_executed"] += 1

            except Exception as e:
                logger.error(f"❌ Error in {event_type} callback: {e}")

    async def _send_reconnection_warning_email(self):
        """Send warning email when approaching max reconnection attempts"""
        subject = "⚠️ Warning: WebSocket Reconnection Issues"
        message = f"""
        The centralized WebSocket manager is having trouble maintaining connection.
        
        Warning Details:
        - Current Attempt: {self.reconnect_attempts} of {self.max_reconnect_attempts}
        - Last Connection Attempt: {self.last_connection_attempt.isoformat() if self.last_connection_attempt else 'Never'}
        
        System Status:
        - Market Data: {'Connected' if self.connection_ready.is_set() else 'Disconnected'}
        - Active Instruments: {len(self.active_instrument_keys)}
        - Connected Clients: {len(self.dashboard_clients) + len(self.trading_clients)}
        
        The system will automatically attempt to reconnect.
        """

        try:
            email_sent = email_service.send_notification(
                recipient_email=ADMIN_EMAIL, subject=subject, message=message
            )
            if email_sent:
                logger.info("📧 Sent WebSocket reconnection warning")
        except Exception as e:
            logger.error(f"❌ Error sending reconnection warning email: {e}")

    async def _send_max_reconnections_email(self):
        """Send critical email when max reconnection attempts reached"""
        subject = "🚨 CRITICAL: WebSocket Connection Failed"
        message = f"""
        The centralized WebSocket manager has failed after maximum reconnection attempts.
        
        Critical Details:
        - Max Attempts Reached: {self.max_reconnect_attempts}
        - Last Successful Connection: {self.last_data_received.isoformat() if self.last_data_received else 'Never'}
        
        System Impact:
        - Real-time market data has stopped
        - Trading signals will be delayed
        - Dashboard updates are frozen
        
        Immediate Action Required:
        1. Check Upstox API status
        2. Verify admin token validity
        3. Restart the WebSocket manager service
        """

        try:
            email_sent = email_service.send_notification(
                recipient_email=ADMIN_EMAIL, subject=subject, message=message
            )
            if email_sent:
                logger.info("📧 Sent max reconnections alert")
        except Exception as e:
            logger.error(f"❌ Error sending max reconnections email: {e}")

    # ===== PUBLIC API METHODS =====

    def register_callback(self, event_type: str, callback: CallbackFunction):
        """Register a callback function for specific events"""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []

        self.callbacks[event_type].append(callback)
        logger.info(f"✅ Registered callback for {event_type}")
        return True

    def unregister_callback(self, event_type: str, callback: CallbackFunction):
        """Unregister a previously registered callback"""
        if event_type in self.callbacks and callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)
            logger.info(f"✅ Unregistered callback for {event_type}")
            return True
        return False

    async def add_client(
        self,
        client_id: str,
        websocket: WebSocket,
        client_type: str = "dashboard",
        instrument_keys: List[str] = None,
    ):
        """Add a client websocket connection"""
        if client_type == "dashboard":
            self.dashboard_clients[client_id] = websocket
            logger.info(f"📊 Dashboard client connected: {client_id}")
        else:
            self.trading_clients[client_id] = websocket
            logger.info(f"🎯 Trading client connected: {client_id}")

            if instrument_keys:
                self.client_subscriptions[client_id] = set(instrument_keys)
                logger.info(
                    f"🔔 Client {client_id} subscribed to {len(instrument_keys)} instruments"
                )

        await self._send_initial_data(client_id, websocket, client_type)
        return True

    async def _send_initial_data(
        self, client_id: str, websocket: WebSocket, client_type: str
    ):
        """Send initial data to a newly connected client"""
        try:
            # Send market status
            await self._send_to_client(
                websocket,
                {
                    "type": "market_info",
                    "marketStatus": self.market_status,
                    "source": "centralized",
                    "timestamp": datetime.now().isoformat(),
                },
            )

            # Send cached data based on client type
            if client_type == "dashboard":
                if self.market_data_cache:
                    logger.info(
                        f"📤 Sending {len(self.market_data_cache)} cached items to dashboard client {client_id}"
                    )
                    await self._send_to_client(
                        websocket,
                        {
                            "type": "dashboard_update",
                            "data": self.market_data_cache,
                            "market_open": self.market_status == "open",
                            "data_source": "CENTRALIZED_WS_CACHE",
                            "timestamp": datetime.now().isoformat(),
                            "is_cached": True,
                            "update_count": self.update_count,
                        },
                    )

            elif client_type == "trading" and client_id in self.client_subscriptions:
                subscribed_keys = self.client_subscriptions[client_id]
                relevant_data = {
                    key: value
                    for key, value in self.market_data_cache.items()
                    if key in subscribed_keys
                }

                if relevant_data:
                    logger.info(
                        f"📤 Sending {len(relevant_data)} relevant cached items to trading client {client_id}"
                    )
                    await self._send_to_client(
                        websocket,
                        {
                            "type": "trading_update",
                            "data": relevant_data,
                            "market_open": self.market_status == "open",
                            "data_source": "CENTRALIZED_WS_CACHE",
                            "timestamp": datetime.now().isoformat(),
                            "is_cached": True,
                            "update_count": self.update_count,
                        },
                    )

            # Send connection status
            await self._send_to_client(
                websocket,
                {
                    "type": "connection_status",
                    "status": (
                        "connected" if self.connection_ready.is_set() else "connecting"
                    ),
                    "source": "centralized",
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except Exception as e:
            logger.error(f"❌ Error sending initial data to client {client_id}: {e}")

    async def remove_client(self, client_id: str):
        """Remove a client connection"""
        removed = False

        if client_id in self.dashboard_clients:
            del self.dashboard_clients[client_id]
            removed = True
            logger.info(f"🧹 Removed dashboard client: {client_id}")

        if client_id in self.trading_clients:
            del self.trading_clients[client_id]
            removed = True
            logger.info(f"🧹 Removed trading client: {client_id}")

        if client_id in self.client_subscriptions:
            del self.client_subscriptions[client_id]
            logger.info(f"🧹 Removed subscriptions for client: {client_id}")

        return removed

    async def update_client_subscriptions(
        self, client_id: str, instrument_keys: List[str]
    ):
        """Update instrument subscriptions for a client"""
        if client_id not in self.trading_clients:
            logger.warning(
                f"⚠️ Cannot update subscriptions: Client {client_id} not found"
            )
            return False

        self.client_subscriptions[client_id] = set(instrument_keys)
        logger.info(
            f"🔄 Updated subscriptions for client {client_id}: {len(instrument_keys)} instruments"
        )

        # Send initial data for new subscriptions
        if client_id in self.trading_clients:
            relevant_data = {
                key: value
                for key, value in self.market_data_cache.items()
                if key in instrument_keys
            }

            if relevant_data:
                await self._send_to_client(
                    self.trading_clients[client_id],
                    {
                        "type": "subscription_update",
                        "data": relevant_data,
                        "market_open": self.market_status == "open",
                        "timestamp": datetime.now().isoformat(),
                        "message": "Subscription updated",
                        "subscribed_instruments": len(instrument_keys),
                    },
                )

        return True

    async def stop(self):
        """Stop the centralized manager"""
        logger.info("🛑 Stopping centralized WebSocket manager")
        self.is_running = False

        if self.ws_client:
            self.ws_client.stop()
            self.ws_client = None

        self.connection_ready.clear()

        await self._send_to_all_clients(
            {
                "type": "service_shutdown",
                "message": "Centralized WebSocket service is shutting down",
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Clear connections
        self.dashboard_clients.clear()
        self.trading_clients.clear()
        self.client_subscriptions.clear()

        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()

        return True

    # ===== DATA ACCESS METHODS =====

    def get_latest_data(self, instrument_key: str) -> Optional[dict]:
        """Get latest data for a specific instrument"""
        return self.market_data_cache.get(instrument_key)

    def get_latest_price(self, instrument_key: str) -> Optional[float]:
        """Get latest price for a specific instrument"""
        data = self.market_data_cache.get(instrument_key)
        if not data or not isinstance(data, dict):
            return None

        # Try different formats
        if "ltp" in data:
            return data["ltp"]
        elif "fullFeed" in data:
            feed = data.get("fullFeed", {}).get("marketFF", {})
            ltpc = feed.get("ltpc", {})
            return ltpc.get("ltp")

        return None

    def get_market_status(self) -> str:
        """Get current market status"""
        return self.market_status

    def get_last_update_time(self, instrument_key: str = None) -> Optional[str]:
        """Get timestamp of last update"""
        if instrument_key:
            data = self.market_data_cache.get(instrument_key)
            return data.get("timestamp") if data else None

        return self.last_data_received.isoformat() if self.last_data_received else None

    def get_all_prices(self) -> Dict[str, float]:
        """Get all latest prices as a dictionary"""
        result = {}
        for key, data in self.market_data_cache.items():
            price = self.get_latest_price(key)
            if price is not None:
                result[key] = price
        return result

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get formatted data for dashboard"""
        # Calculate active instruments (those with recent valid data)
        active_instruments = 0
        for data in self.market_data_cache.values():
            if isinstance(data, dict) and data.get('last_price'):
                active_instruments += 1
        
        return {
            "market_status": self.market_status,
            "last_updated": (
                self.last_data_received.isoformat() if self.last_data_received else None
            ),
            "data": self.market_data_cache,
            "update_count": self.update_count,
            "total_instruments": len(self.market_data_cache),
            "active_instruments": active_instruments,
        }

    def get_top_performers(
        self, limit: int = 5, sort: str = "gainers"
    ) -> List[Dict[str, Any]]:
        """Get top gainers or losers"""
        price_changes = []

        for key, data in self.market_data_cache.items():
            try:
                if not isinstance(data, dict):
                    continue

                ltp = None
                prev_close = None
                symbol = key

                # Extract price data
                if "ltp" in data:
                    ltp = data.get("ltp")
                    prev_close = data.get("cp")
                    symbol = data.get("symbol", key)
                elif "fullFeed" in data:
                    feed = data.get("fullFeed", {}).get("marketFF", {})
                    ltpc = feed.get("ltpc", {})
                    ltp = ltpc.get("ltp")
                    prev_close = ltpc.get("cp")

                if ltp is not None and prev_close is not None and prev_close > 0:
                    change_pct = (ltp - prev_close) / prev_close * 100
                    price_changes.append(
                        {
                            "instrument_key": key,
                            "symbol": symbol,
                            "ltp": ltp,
                            "prev_close": prev_close,
                            "change_pct": change_pct,
                        }
                    )

            except Exception:
                continue

        # Sort by percentage change
        reverse_sort = sort == "gainers"
        price_changes.sort(key=lambda x: x.get("change_pct", 0), reverse=reverse_sort)

        return price_changes[:limit]

    # ===== STATUS METHODS =====

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the manager"""
        return {
            "is_running": self.is_running,
            "admin_user_id": self.admin_user_id,
            "ws_connected": self.connection_ready.is_set(),
            "market_status": self.market_status,
            "market_phases": self.market_phases,
            "active_segments": self.active_segments,
            "total_instruments": len(self.all_instrument_keys),
            "active_instruments": len(self.active_instrument_keys),
            "clients": {
                "dashboard": len(self.dashboard_clients),
                "trading": len(self.trading_clients),
                "total": len(self.dashboard_clients) + len(self.trading_clients),
            },
            "data_stats": {
                "cached_instruments": len(self.market_data_cache),
                "update_count": self.update_count,
                "data_count": self.data_count,
            },
            "reconnect_attempts": self.reconnect_attempts,
            "last_data_received": (
                self.last_data_received.isoformat() if self.last_data_received else None
            ),
            "timestamp": datetime.now().isoformat(),
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        status = self.get_status()

        # Calculate health score
        health_score = 100
        issues = []

        if not self.is_running:
            health_score -= 50
            issues.append("Service not running")

        if not status["ws_connected"]:
            health_score -= 30
            issues.append("WebSocket not connected")

        if self.reconnect_attempts > 0:
            health_score -= min(5 * self.reconnect_attempts, 25)
            issues.append(f"Recent reconnection attempts: {self.reconnect_attempts}")

        if not self.market_data_cache:
            health_score -= 10
            issues.append("No cached market data")

        # Check data freshness
        if self.last_data_received:
            time_since_data = (datetime.now() - self.last_data_received).total_seconds()
            if time_since_data > 300:  # 5 minutes
                health_score -= 15
                issues.append(f"No data received for {int(time_since_data/60)} minutes")

        # Performance metrics
        performance = {
            "messages_received": self.performance_metrics["messages_received"],
            "updates_processed": self.performance_metrics["updates_processed"],
            "callbacks_executed": self.performance_metrics["callbacks_executed"],
            "clients_updated": self.performance_metrics["clients_updated"],
            "reconnection_count": self.performance_metrics["reconnection_count"],
            "last_latency_ms": round(self.performance_metrics["last_latency_ms"], 2),
            "avg_latency_ms": round(self.performance_metrics["avg_latency_ms"], 2),
        }

        status.update(
            {
                "health_score": max(0, health_score),
                "status": (
                    "healthy"
                    if health_score > 70
                    else "degraded" if health_score > 30 else "unhealthy"
                ),
                "issues": issues,
                "performance_metrics": performance,
            }
        )

        return status

    # ===== DEBUG METHODS =====

    async def force_test_broadcast(self, test_data: Dict[str, Any] = None):
        """Force a test broadcast for debugging"""
        if test_data is None:
            test_data = {
                "NSE_EQ|INE002A01018": {  # RELIANCE
                    "ltp": 2500.0,
                    "ltq": 100,
                    "cp": 2475.0,
                    "timestamp": datetime.now().isoformat(),
                    "test": True,
                }
            }

        logger.info("🧪 Force broadcasting test data")
        await self._broadcast_live_data(test_data)
        return True

    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information"""
        return {
            "last_raw_data": getattr(self, "_last_raw_data", None),
            "connection_attempts": self.reconnect_attempts,
            "background_tasks": len(self.background_tasks),
            "callback_counts": {
                event: len(callbacks) for event, callbacks in self.callbacks.items()
            },
            "cache_size": len(self.market_data_cache),
            "subscription_counts": {
                client_id: len(subs)
                for client_id, subs in self.client_subscriptions.items()
            },
        }

    async def _enrich_price_data(self, feeds: dict) -> dict:
        """🚀 FAST: Enrich price data with metadata (sector, symbol, etc.) in <3ms"""
        try:
            from services.instrument_registry import instrument_registry
            
            # Update and get enriched data in one operation (fast)
            enriched_data = instrument_registry.update_and_enrich_prices(feeds)
            return enriched_data if enriched_data else feeds
            
        except Exception as e:
            logger.debug(f"Price enrichment error: {e}")
            # Return original feeds if enrichment fails
            return feeds
    
    async def _broadcast_realtime_prices(self, enriched_feeds: dict):
        """🚀 REMOVED: Redundant price broadcasting - now handled by instrument registry callbacks"""
        # This method is now redundant as price broadcasting is handled by:
        # instrument_registry.update_live_prices() -> _execute_real_time_callbacks() -> UI callbacks
        logger.debug(f"⚡ OPTIMIZED: Price broadcasting handled by instrument registry ({len(enriched_feeds)} feeds)")
        return  # Early return - no processing needed
    
    async def _process_analytics_background(self, feeds: dict, enriched_feeds: dict, is_snapshot: bool, data: dict):
        """Background processing for analytics (non-blocking, can have slight delay)"""
        try:
            from services.unified_websocket_manager import unified_manager
            
            # Update market data hub (background)
            try:
                from services.market_data_hub import market_data_hub
                market_data_hub.update_market_data_batch(feeds)
                logger.debug(f"📊 Hub updated with {len(feeds)} instruments (background)")
            except Exception as e:
                logger.debug(f"Hub update error: {e}")
            
            # Update cache (background)
            await self._update_cache(feeds)
            
            # Update registry (background) 
            await self._legacy_registry_update(feeds)
            
            # Queue analytics dashboard update (can have delay)
            dashboard_data = {
                "data": enriched_feeds,
                "market_open": self.market_status == "open",
                "timestamp": data.get("currentTs", datetime.now().isoformat()),
                "update_count": self.update_count,
                "is_snapshot": is_snapshot
            }
            
            logger.debug(f"📊 BACKGROUND: Analytics processing started for {len(enriched_feeds)} instruments")
            
            # 🚀 REMOVED: Redundant unified manager call
            # Dashboard updates now handled by instrument registry UI callbacks
            
            # Execute other callbacks
            await self._execute_callbacks("price_update", {
                "data": enriched_feeds,
                "is_snapshot": is_snapshot,
                "timestamp": datetime.now().isoformat(),
                "source": "background_analytics"
            })
            
        except Exception as e:
            logger.debug(f"Background analytics processing error: {e}")

    async def _update_instrument_registry_legacy(self, feeds: Dict[str, Any]):
        """✅ LEGACY: Update instrument registry with live price data (fallback method)"""
        try:
            # Import instrument registry
            from services.instrument_registry import instrument_registry
            
            # Update registry with live feeds
            if feeds and isinstance(feeds, dict):
                stats = instrument_registry.update_live_prices(feeds)
                logger.debug(f"📊 Updated instrument registry: {stats}")
                
        except ImportError:
            logger.warning("⚠️ Instrument registry not available - data not stored")
        except Exception as e:
            logger.error(f"❌ Error updating instrument registry: {e}")


# Create singleton instance
centralized_manager = CentralizedWebSocketManager()


# ===== CONVENIENCE FUNCTIONS FOR EASY IMPORT =====


def get_centralized_manager() -> CentralizedWebSocketManager:
    """Get the singleton centralized manager instance"""
    return centralized_manager


async def initialize_centralized_websocket() -> bool:
    """Initialize the centralized WebSocket manager"""
    return await centralized_manager.initialize()


async def start_centralized_websocket() -> bool:
    """Start the centralized WebSocket connection"""
    return await centralized_manager.start_connection()


def register_market_data_callback(callback: CallbackFunction) -> bool:
    """Register a callback for market data updates"""
    return centralized_manager.register_callback("price_update", callback)


def register_market_status_callback(callback: CallbackFunction) -> bool:
    """Register a callback for market status updates"""
    return centralized_manager.register_callback("market_status", callback)


def get_latest_market_price(instrument_key: str) -> Optional[float]:
    """Get the latest price for an instrument"""
    return centralized_manager.get_latest_price(instrument_key)


def get_market_status() -> str:
    """Get current market status"""
    return centralized_manager.get_market_status()


async def add_websocket_client(
    client_id: str,
    websocket: WebSocket,
    client_type: str = "dashboard",
    instrument_keys: List[str] = None,
) -> bool:
    """Add a WebSocket client to the centralized manager"""
    return await centralized_manager.add_client(
        client_id, websocket, client_type, instrument_keys
    )


async def remove_websocket_client(client_id: str) -> bool:
    """Remove a WebSocket client from the centralized manager"""
    return await centralized_manager.remove_client(client_id)


def get_all_market_prices() -> Dict[str, float]:
    """Get all current market prices"""
    return centralized_manager.get_all_prices()


def get_centralized_websocket_status() -> Dict[str, Any]:
    """Get status of the centralized WebSocket manager"""
    return centralized_manager.get_status()


async def stop_centralized_websocket() -> bool:
    """Stop the centralized WebSocket manager"""
    return await centralized_manager.stop()


# For any existing imports that might be looking for these
websocket_manager = centralized_manager  # Alias for backwards compatibility
manager = centralized_manager  # Short alias
