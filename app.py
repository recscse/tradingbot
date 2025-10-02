# app.py

import asyncio
import logging
import os
from datetime import datetime, time
from contextlib import asynccontextmanager
import uvicorn
import socketio
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Load environment variables FIRST
load_dotenv()

# Configure logging EARLY
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ⚠️ DEPRECATED: Legacy enhanced analytics service - DISABLED
# Replaced by: services/realtime_market_engine.py + router/realtime_analytics_router.py
try:
    # Keep import for backward compatibility but don't use
    from services.enhanced_market_analytics import enhanced_analytics

    enhanced_analytics = None  # Disabled
    ANALYTICS_SERVICE_AVAILABLE = False
    logger.warning(
        "⚠️ DEPRECATED: Enhanced analytics service disabled - using Real-Time Analytics Engine"
    )
except ImportError as e:
    enhanced_analytics = None
    ANALYTICS_SERVICE_AVAILABLE = False
    logger.info(
        "✅ Enhanced analytics service not loaded (replaced by Real-Time Analytics Engine)"
    )

try:
    from services.centralized_ws_manager import centralized_manager
    from router.market_ws import (
        router as centralized_market_ws_router,
        initialize_websocket_system,
    )

    CENTRALIZED_WS_AVAILABLE = True
    CENTRALIZED_ROUTES_AVAILABLE = True
    logger.info("✅ NEW: Centralized WebSocket manager imported successfully")
    logger.info("✅ NEW: Centralized WebSocket routes imported successfully")
except ImportError as e:
    CENTRALIZED_WS_AVAILABLE = False
    CENTRALIZED_ROUTES_AVAILABLE = False
    logger.error(f"❌ NEW: Centralized WebSocket manager not available: {e}")
    logger.error(f"❌ NEW: Centralized WebSocket routes not available: {e}")
    centralized_manager = None
    from fastapi import APIRouter

    centralized_market_ws_router = APIRouter()  # Dummy router

# LEGACY: Use the same router for backward compatibility
if CENTRALIZED_WS_AVAILABLE:
    legacy_market_ws_router = centralized_market_ws_router
    LEGACY_MARKET_WS_AVAILABLE = True
    logger.info(
        "✅ Legacy market WebSocket routes available for backward compatibility"
    )
else:
    legacy_market_ws_router = centralized_market_ws_router  # Same dummy router
    LEGACY_MARKET_WS_AVAILABLE = False
    logger.warning("⚠️ Legacy market WebSocket routes not available")

# Import other services
from typing import Optional, Any
import redis
from redis.exceptions import ConnectionError, RedisError
import json

# Import your existing database and models
from core.middleware import TokenRefreshMiddleware
from database.connection import SessionLocal, get_db
from database.init_db import init_db
from database.models import BrokerConfig, TradePerformance, TradeSignal, User

# SAFE: Import analytics router without circular dependencies
try:
    from router.market_analytics_router import router as market_analytics_router

    MARKET_ANALYTICS_ROUTER_AVAILABLE = True
    logger.info("✅ Market analytics router imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ Market analytics router not available: {e}")
    from fastapi import APIRouter

    market_analytics_router = APIRouter()  # Dummy router
    MARKET_ANALYTICS_ROUTER_AVAILABLE = False

# Import other services
# Removed auto_stock_selection_service - using intelligent_stock_selection_service instead

# Import your existing routers
from router import analytics_router, order_router
from router.user_router import router as user_router
from router.auth_router import auth_router
from router.broker_router import broker_router
from router.stock_list_router import stock_list_router
from router.dhan_router import dhan_router

# from router.trading_config_router import router as trading_config_router
from router.config_router import router as config_router
from router.upstox_router import upstox_router
from router.fyers_router import fyers_router
from router.broker_profile_router import broker_profile_router
from router.margin_aware_trading_router import margin_trading_router

from ws_router.upstox_ltp_ws import ws_upstox_router
from router.backtest_router import backtesting_router
from router.stock_router import router as stock_router
from router.profile_router import router as profile_router
from router.paper_trading_router import router as paper_trading_router
from router.notification_router import router as notification_router

# from router.instrument_routes import router as instrument_router
# from services.instrument_registry import instrument_registry
from router.websocket_routes import router as websocket_router
from router.debug_routes import router as debug_router
from router.heatmap_router import router as heatmap_router

# from router.unified_websocket_routes import router as unified_ws_router
from router.paper_trading_routes import router as paper_trading_router
from router.option_routes import option_router

# from services.unified_websocket_manager import unified_manager, start_unified_websocket

try:
    from router.auto_trading_routes import router as auto_trading_router

    AUTO_TRADING_AVAILABLE = True
    logger.info("✅ Auto Trading routes imported successfully")
except ImportError as e:
    from fastapi import APIRouter

    auto_trading_router = APIRouter()  # Dummy router
    AUTO_TRADING_AVAILABLE = False
    logger.warning(f"⚠️ Auto Trading services not available: {e}")


# Import from market_analytics_router safely
try:
    from router.market_analytics_router import INSTRUMENT_REGISTRY_AVAILABLE
except ImportError:
    INSTRUMENT_REGISTRY_AVAILABLE = False

# Import your existing trading engine and services

# FIXED: Import trading scheduler correctly
try:
    from services.trading_scheduler import TradingScheduler

    TRADING_SCHEDULER_AVAILABLE = True
    logger.info("✅ Trading scheduler imported successfully")
except ImportError as e:
    TRADING_SCHEDULER_AVAILABLE = False
    logger.warning(f"⚠️ Trading scheduler not available: {e}")

    class TradingScheduler:
        def __init__(self):
            self.is_running = False

        def start_scheduler(self):
            self.is_running = True
            logger.info("✅ Fallback TradingScheduler started")

        def stop_scheduler(self):
            self.is_running = False


# Import pre-market service
try:
    from services.pre_market_data_service import (
        PreMarketDataService,
        get_cached_trading_stocks,
    )
except ImportError:

    def get_cached_trading_stocks():
        return []

    logger.warning("⚠️ Pre-market data service not available")

# Import gap detection service (formerly premarket candle builder)
try:
    from services.gapdetection_service import (
        get_gap_detection_service,
        start_gap_detection_scheduler,
    )

    GAP_DETECTION_AVAILABLE = True
    logger.info("✅ Gap detection service imported successfully")
except ImportError as e:
    GAP_DETECTION_AVAILABLE = False
    logger.warning(f"⚠️ Gap detection service not available: {e}")

    # Dummy functions for fallback
    def get_gap_detection_service():
        return None

    async def start_gap_detection_scheduler():
        pass


# KEEP: Your existing Redis manager (it's already well-designed)
class TradingSafeRedisManager:
    """Redis manager specifically designed for trading applications with graceful fallbacks"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.is_connected = False
        self.fallback_cache = {}
        self._initialize_redis()

    def _initialize_redis(self):
        """Initialize Redis connection with comprehensive error handling"""
        redis_enabled = os.getenv("REDIS_ENABLED", "true").lower() == "true"

        if not redis_enabled:
            logger.info("🔧 Redis disabled via REDIS_ENABLED environment variable")
            return

        try:
            self.redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                db=int(os.getenv("REDIS_DB", 0)),
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=False,
                health_check_interval=30,
            )

            # Test connection
            self.redis_client.ping()
            self.is_connected = True
            logger.info("✅ Redis connected successfully for trading system")

        except ConnectionError:
            logger.warning(
                "⚠️ Redis connection failed - trading system will use fallback cache"
            )
            self.redis_client = None
            self.is_connected = False
        except Exception as e:
            logger.error(f"❌ Redis initialization error: {e} - using fallback cache")
            self.redis_client = None
            self.is_connected = False

    def get(self, key: str, default: Any = None) -> Any:
        """Get value with fallback to in-memory cache for critical trading data"""
        if self.is_connected and self.redis_client:
            try:
                result = self.redis_client.get(key)
                if result is None:
                    return self.fallback_cache.get(key, default)

                try:
                    parsed_result = json.loads(result)
                    if any(
                        critical in key
                        for critical in [
                            "live_price",
                            "selected_stocks",
                            "trading_data",
                        ]
                    ):
                        self.fallback_cache[key] = parsed_result
                    return parsed_result
                except (json.JSONDecodeError, TypeError):
                    if any(
                        critical in key
                        for critical in [
                            "live_price",
                            "selected_stocks",
                            "trading_data",
                        ]
                    ):
                        self.fallback_cache[key] = result
                    return result

            except RedisError as e:
                logger.warning(f"Redis GET error for key '{key}': {e} - using fallback")
                return self.fallback_cache.get(key, default)

        return self.fallback_cache.get(key, default)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value with fallback storage for critical data"""
        success = False

        if self.is_connected and self.redis_client:
            try:
                if isinstance(value, (dict, list)):
                    serialized_value = json.dumps(value)
                else:
                    serialized_value = value

                result = self.redis_client.set(key, serialized_value, ex=ttl)
                success = bool(result)

            except RedisError as e:
                logger.warning(f"Redis SET error for key '{key}': {e}")
                success = False

        # Always update fallback cache for critical trading data
        if any(
            critical in key
            for critical in [
                "live_price",
                "selected_stocks",
                "trading_data",
                "market_status",
            ]
        ):
            self.fallback_cache[key] = value
            if not success:
                logger.debug(f"Stored '{key}' in fallback cache")

        return success

    def delete(self, *keys: str) -> int:
        """Delete keys with fallback cache cleanup"""
        deleted_count = 0

        if self.is_connected and self.redis_client:
            try:
                deleted_count = self.redis_client.delete(*keys)
            except RedisError as e:
                logger.warning(f"Redis DELETE error: {e}")

        for key in keys:
            if key in self.fallback_cache:
                del self.fallback_cache[key]
                deleted_count += 1

        return deleted_count

    def exists(self, key: str) -> bool:
        """Check existence in Redis or fallback cache"""
        if self.is_connected and self.redis_client:
            try:
                return bool(self.redis_client.exists(key))
            except RedisError:
                pass

        return key in self.fallback_cache

    def keys(self, pattern: str = "*") -> list:
        """Get keys with fallback support"""
        redis_keys = []

        if self.is_connected and self.redis_client:
            try:
                redis_keys = self.redis_client.keys(pattern)
            except RedisError as e:
                logger.warning(f"Redis KEYS error: {e}")

        import fnmatch

        fallback_keys = [
            key for key in self.fallback_cache.keys() if fnmatch.fnmatch(key, pattern)
        ]

        all_keys = list(set(redis_keys + fallback_keys))
        return all_keys

    def health_check(self) -> dict:
        """Comprehensive health check for trading system"""
        if not self.redis_client:
            return {
                "status": "fallback_mode",
                "message": "Redis disabled - using in-memory fallback cache",
                "fallback_cache_size": len(self.fallback_cache),
            }

        try:
            self.redis_client.ping()
            self.is_connected = True
            return {
                "status": "healthy",
                "message": "Redis connection is working",
                "fallback_cache_size": len(self.fallback_cache),
            }
        except Exception as e:
            self.is_connected = False
            return {
                "status": "degraded",
                "message": f"Redis connection failed: {str(e)} - using fallback",
                "fallback_cache_size": len(self.fallback_cache),
            }

    def get_trading_cache_stats(self) -> dict:
        """Get statistics specific to trading data caching"""
        stats = {
            "redis_connected": self.is_connected,
            "fallback_cache_size": len(self.fallback_cache),
            "critical_data_cached": 0,
            "cache_mode": "redis" if self.is_connected else "fallback",
        }

        critical_keys = [
            "live_price",
            "selected_stocks",
            "trading_data",
            "market_status",
        ]
        stats["critical_data_cached"] = len(
            [
                key
                for key in self.fallback_cache.keys()
                if any(critical in key for critical in critical_keys)
            ]
        )

        return stats


# Initialize global Redis manager
trading_redis = TradingSafeRedisManager()

# Global instances
trading_engine = None
trading_scheduler = None
market_scheduler = None
instrument_service_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Enhanced lifespan with NEW centralized WebSocket system integration"""
    global trading_engine, trading_scheduler, market_scheduler, instrument_service_instance

    logger.info(
        "🚀 Starting Enhanced Trading Application with NEW Centralized WebSocket System..."
    )

    try:
        # 1. DB initialization
        db = next(get_db())
        logger.info("✅ DB session initialized.")
        db.close()

        # 2. Redis health check
        redis_status = trading_redis.health_check()
        logger.info(f"🔧 Redis status: {redis_status['message']}")

        # 3. Initialize instrument service FIRST
        logger.info("🔧 Initializing Instrument Service...")
        from services.instrument_refresh_service import get_trading_service

        instrument_service = get_trading_service()
        initialization_result = await instrument_service.initialize_service()

        if initialization_result.status == "success":
            logger.info(
                f"✅ Instrument service initialized with {initialization_result.mapped_stocks} stocks"
            )
            instrument_service_instance = instrument_service
        else:
            logger.error(
                f"❌ Instrument service initialization failed: {initialization_result.error}"
            )

        # 4. Initialize optimized market data service FIRST
        try:
            logger.info("🚀 Initializing Optimized Market Data Service...")
            from services.optimized_market_data_service import optimized_market_service

            await optimized_market_service.initialize_instruments()
            stats = optimized_market_service.get_stats()
            logger.info(
                f"✅ Optimized Market Service initialized with {stats['total_instruments']} instruments, {stats['active_instruments']} active"
            )
        except Exception as e:
            logger.error(f"❌ Optimized market service initialization failed: {e}")

        # 4.5. 🚀 NEW: Initialize Real-Time Market Analytics Engine
        try:
            logger.info("📊 Initializing Real-Time Market Analytics Engine...")
            from services.realtime_market_engine import initialize_market_engine
            from services.instrument_refresh_service import get_analytics_metadata

            # Get analytics metadata from instrument service
            analytics_metadata = get_analytics_metadata()

            if analytics_metadata:
                # Initialize analytics engine with metadata
                initialize_market_engine(analytics_metadata)

                from services.realtime_market_engine import get_market_engine

                engine = get_market_engine()
                stats = engine.get_stats()

                logger.info(
                    f"✅ Real-Time Analytics Engine initialized with {stats['total_instruments']} instruments "
                    f"across {stats['sectors']} sectors"
                )
                logger.info(
                    f"📈 Analytics latency: {stats['analytics_latency_ms']:.2f}ms"
                )
            else:
                logger.warning(
                    "⚠️ No analytics metadata available - analytics engine not initialized"
                )

        except Exception as e:
            logger.error(f"❌ Real-Time Analytics Engine initialization failed: {e}")
            import traceback

            logger.error(f"❌ Traceback: {traceback.format_exc()}")

        # 5. Initialize instrument registry SECOND (for backward compatibility)
        try:
            logger.info("🔧 Initializing Instrument Registry...")
            from services.instrument_registry import instrument_registry

            registry_initialized = await instrument_registry.initialize_registry()

            if registry_initialized:
                stats = instrument_registry.get_stats()
                logger.info(
                    f"✅ Instrument Registry initialized with {stats['spot_instruments']} spot instruments, {stats['fno_instruments']} F&O instruments"
                )
            else:
                logger.error("❌ Instrument registry initialization failed")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Instrument Registry: {e}")
            import traceback

            logger.error(f"❌ Traceback: {traceback.format_exc()}")

        # 6. Start Unified WebSocket System (🚀 ENHANCED with Real-Time Analytics Engine)
        # logger.info(
        #     "🔌 Starting Enhanced Unified WebSocket System with Real-Time Analytics..."
        # )
        # await start_unified_websocket()

        # 7. 🚀 Start Enhanced Breakout Engine (consolidated breakout detection)
        logger.info("🚀 Starting Enhanced Breakout Engine...")
        try:
            from services.enhanced_breakout_engine import start_enhanced_breakout_engine

            await start_enhanced_breakout_engine()
            logger.info("✅ Enhanced Breakout Engine started successfully")
        except Exception as e:
            logger.error(f"❌ Failed to start Enhanced Breakout Engine: {e}")

        # Gap Detection Service analyzes market gaps at 9:08 AM daily

        # 7c. Start Gap Detection Service
        if GAP_DETECTION_AVAILABLE:
            logger.info("Starting Gap Detection Service...")
            try:
                # Start as background task to avoid blocking startup
                asyncio.create_task(start_gap_detection_scheduler())
                logger.info(
                    "Gap Detection Service started - scheduled for 9:08 AM IST daily"
                )
            except Exception as e:
                logger.error(
                    f"Failed to start Gap Detection Service: {e}"
                )

        # 8. NEW: Initialize Centralized WebSocket System
        if CENTRALIZED_WS_AVAILABLE:
            logger.info("🔌 Initializing NEW Centralized WebSocket System...")
            try:
                if await centralized_manager.initialize():
                    await centralized_manager.start_connection()

                    # 🚀 NEW: Initialize optimized real-time trading system (ZERO DELAY)
                    try:
                        from services.startup_integration import (
                            initialize_realtime_trading_system,
                        )

                        success = await initialize_realtime_trading_system()
                        if success:
                            logger.info(
                                "✅ Real-time trading system initialized (ZERO DELAY ARCHITECTURE)"
                            )
                        else:
                            logger.warning(
                                "⚠️ Real-time trading system initialization incomplete"
                            )
                    except ImportError:
                        logger.debug("Startup integration not available")

                    # 🚀 CRITICAL: Initialize ZERO-DELAY real-time streaming
                    try:
                        from services.realtime_data_streamer import realtime_streamer

                        realtime_streamer.start_streaming()
                        logger.info("🚀 ZERO-DELAY real-time streaming ACTIVATED")
                    except ImportError as e:
                        logger.warning(f"⚠️ ZERO-DELAY streaming not available: {e}")

                    except Exception as e:
                        logger.error(
                            f"❌ Error initializing real-time trading system: {e}"
                        )

                    status = await centralized_manager.health_check()
                    logger.info(
                        f"✅ NEW: Centralized WebSocket system started successfully"
                    )
                    logger.info(f"📊 Health Score: {status.get('health_score', 0)}/100")
                    logger.info(
                        f"🔗 WebSocket Connected: {status.get('ws_connected', False)}"
                    )
                    logger.info(
                        f"📈 Total Instruments: {status.get('total_instruments', 0)}"
                    )
                    logger.info(f"👑 Admin Token Strategy: Active")

                    # 🚀 ENHANCED: Connect centralized manager to unified WebSocket manager with Real-Time Analytics
                    logger.info(
                        "🔗 Connecting centralized WebSocket manager to enhanced unified system..."
                    )
                    try:
                        from services.unified_websocket_manager import (
                            integrate_with_centralized_manager,
                        )

                        integrate_with_centralized_manager()
                        logger.info(
                            "✅ ENHANCED: WebSocket managers connected with Real-Time Analytics integration"
                        )
                    except Exception as e:
                        logger.error(
                            f"❌ Failed to connect enhanced WebSocket managers: {e}"
                        )

                else:
                    logger.error(
                        "❌ NEW: Failed to initialize centralized WebSocket system"
                    )
            except Exception as e:
                logger.error(f"❌ NEW: Centralized WebSocket system error: {e}")
        else:
            logger.warning(
                "⚠️ NEW: Centralized WebSocket system not available - using legacy only"
            )

        # 7. FIXED: Initialize TradingScheduler correctly
        logger.info("🕐 Starting TradingScheduler...")
        if TRADING_SCHEDULER_AVAILABLE:
            try:
                trading_scheduler = TradingScheduler()
                trading_scheduler.start_scheduler()
                logger.info("✅ TradingScheduler started")
            except Exception as e:
                logger.warning(
                    f"⚠️ TradingScheduler failed to start: {e} - continuing without scheduler"
                )
        else:
            logger.warning("⚠️ TradingScheduler not available")

        # 7.1. Initialize Upstox Token Automation
        logger.info("🔄 Starting Upstox Token Automation (2GB RAM)...")
        try:
            from services.upstox_automation_service import start_upstox_automation

            upstox_automation = start_upstox_automation()
            if upstox_automation:
                logger.info(
                    "✅ Upstox token automation started - will refresh tokens daily at 4:00 AM"
                )
            else:
                logger.warning("⚠️ Upstox token automation failed to start")
        except Exception as e:
            logger.warning(
                f"⚠️ Upstox automation error: {e} - continuing without automation"
            )
            logger.warning(
                "💡 Configure UPSTOX_MOBILE, UPSTOX_PIN, and UPSTOX_TOTP_KEY to enable automation"
            )

        # 7.2. Initialize MarketScheduleService - CRITICAL for FNO and Instrument automation
        logger.info("📅 Starting MarketScheduleService...")
        try:
            from services.market_schedule_service import MarketScheduleService

            market_scheduler = MarketScheduleService()
            # Start as background task to avoid blocking startup
            market_scheduler_task = asyncio.create_task(
                market_scheduler.start_daily_scheduler()
            )
            logger.info(
                "✅ MarketScheduleService started - will handle daily FNO refresh, instrument updates, and market timing coordination"
            )
        except Exception as e:
            logger.warning(
                f"⚠️ MarketScheduleService failed to start: {e} - continuing without market scheduling"
            )
            logger.warning(
                "💡 This means FNO stocks and instruments will not auto-refresh. Manual refresh required."
            )

        # 7.3. Initialize Notification Scheduler - NEW comprehensive notification system
        logger.info("📨 Starting Notification Scheduler...")
        try:
            from services.notification_scheduler import notification_scheduler

            notification_scheduler.start_scheduler()
            logger.info(
                "✅ Notification Scheduler started - handling token expiry, daily summaries, and system alerts"
            )
        except Exception as e:
            logger.warning(
                f"⚠️ Notification Scheduler failed to start: {e} - continuing without notification scheduling"
            )
            logger.warning(
                "💡 This means automated token expiry alerts and daily summaries will not work"
            )

        # Note: Old gap and breakout detection services removed
        # Now using enhanced services started earlier in the startup process
        logger.info(
            "🎯 Using enhanced gap and breakout detection services (numpy/pandas optimized)"
        )

        # 13. ✅ NEW: Start Auto Trading WebSocket Service
        if AUTO_TRADING_AVAILABLE:
            logger.info("🔴 Starting Auto Trading WebSocket Service...")
            try:
                from services.websocket.auto_trading_websocket import (
                    start_auto_trading_websocket,
                )

                await start_auto_trading_websocket()
                logger.info("✅ Auto Trading WebSocket Service started")
            except Exception as e:
                logger.error(f"❌ Auto Trading WebSocket Service failed to start: {e}")

        # 14. ✅ Intelligent Stock Selection Service available via router
        # No startup needed - service is initialized when router is accessed
        logger.info(
            "✅ Intelligent Stock Selection Service available via /api/v1/intelligent-stock-selection"
        )

        # 15. ✅ NEW: Initialize Auto Trade Execution Service
        if AUTO_TRADING_AVAILABLE:
            logger.info("⚡ Initializing Auto Trade Execution Service...")
            try:
                from services.execution.auto_trade_execution_service import (
                    start_auto_trade_execution,
                )

                await start_auto_trade_execution()
                logger.info("✅ Auto Trade Execution Service initialized")
            except Exception as e:
                logger.error(
                    f"❌ Auto Trade Execution Service failed to initialize: {e}"
                )

        # 16. 🚀 NEW: Initialize Intelligent Stock Selection Service
        logger.info("🧠 Initializing Intelligent Stock Selection Service...")
        try:
            from services.intelligent_stock_selection_service import (
                intelligent_stock_selector,
            )

            await intelligent_stock_selector.initialize_services()
            logger.info(
                "✅ Intelligent Stock Selection Service initialized successfully"
            )
        except ImportError as e:
            logger.warning(f"⚠️ Intelligent Stock Selection Service not available: {e}")
        except Exception as e:
            logger.error(
                f"❌ Intelligent Stock Selection Service failed to initialize: {e}"
            )

        # 17. 🚀 NEW: Initialize MCX WebSocket Service
        logger.info("📊 Initializing MCX WebSocket Service...")
        try:
            from services.websocket.mcx.integration import initialize_mcx_service

            mcx_success = await initialize_mcx_service()
            if mcx_success:
                logger.info("✅ MCX WebSocket Service initialized successfully")
            else:
                logger.warning("⚠️ MCX WebSocket Service initialization failed")
        except ImportError as e:
            logger.warning(f"⚠️ MCX WebSocket Service not available: {e}")
        except Exception as e:
            logger.error(f"❌ MCX WebSocket Service failed to initialize: {e}")

        logger.info(
            "🟢 All services started successfully with NEW Centralized WebSocket + MCX + Optimized Architecture!"
        )

        # Signal that startup is complete and token refresh can now proceed
        if CENTRALIZED_WS_AVAILABLE and centralized_manager:
            try:
                centralized_manager.mark_startup_complete()
                logger.info("✅ Marked startup complete - token refresh enabled")
            except Exception as e:
                logger.warning(f"⚠️ Error marking startup complete: {e}")

        # Start simple unified WebSocket broadcast task
        try:
            logger.info("🚀 Starting Simple Unified WebSocket System...")
            from router.unified_websocket_routes import start_broadcast_task

            await start_broadcast_task()
            logger.info("✅ Simple Unified WebSocket broadcast started")
        except Exception as e:
            logger.error(f"❌ Failed to start Unified WebSocket broadcast: {e}")

        yield

    except Exception as e:
        logger.exception("🔥 Enhanced lifespan startup failed - but app will continue")
        yield
    finally:
        # Enhanced cleanup
        logger.info("🛑 Starting enhanced shutdown...")

        # Stop simple unified WebSocket broadcast
        try:
            from router.unified_websocket_routes import stop_broadcast_task

            await stop_broadcast_task()
            logger.info("✅ Simple Unified WebSocket broadcast stopped")
        except Exception as e:
            logger.error(f"Error stopping Unified WebSocket broadcast: {e}")

        # NEW: Stop centralized WebSocket system
        if CENTRALIZED_WS_AVAILABLE and centralized_manager:
            try:
                await centralized_manager.stop()
                logger.info("✅ NEW: Centralized WebSocket system stopped")
            except Exception as e:
                logger.error(f"Error stopping centralized WebSocket: {e}")

        # NEW: Stop MCX WebSocket service
        try:
            from services.websocket.mcx.integration import stop_mcx_service

            await stop_mcx_service()
            logger.info("✅ MCX WebSocket service stopped")
        except ImportError:
            pass  # MCX service not available
        except Exception as e:
            logger.error(f"❌ Error stopping MCX WebSocket service: {e}")

        # Premarket Candle Builder Service stops automatically when premarket window closes

        # Stop trading engine
        if trading_engine:
            try:
                logger.info("🛑 Stopping Trading Engine...")
                trading_engine.stop_engine()
            except Exception as e:
                logger.error(f"Error stopping trading engine: {e}")

        if trading_scheduler:
            try:
                logger.info("🛑 Stopping Trading Scheduler...")
                trading_scheduler.stop_scheduler()
            except Exception as e:
                logger.error(f"Error stopping trading scheduler: {e}")

        # Stop MarketScheduleService
        if market_scheduler:
            try:
                logger.info("🛑 Stopping Market Scheduler...")
                market_scheduler.stop_scheduler()
            except Exception as e:
                logger.error(f"Error stopping market scheduler: {e}")

        # Stop Notification Scheduler - NEW
        try:
            logger.info("🛑 Stopping Notification Scheduler...")
            from services.notification_scheduler import notification_scheduler

            notification_scheduler.stop_scheduler()
            logger.info("✅ Notification Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping notification scheduler: {e}")

        logger.info(
            "🎯 Enhanced gap and breakout detection services shutdown completed"
        )

        # Stop Upstox automation
        try:
            from services.upstox_automation_service import stop_upstox_automation

            stop_upstox_automation()
            logger.info("✅ Upstox token automation stopped")
        except Exception as e:
            logger.error(f"Error stopping Upstox automation: {e}")

        # logger.info("🛑 Enhanced lifespan shutdown complete.")
        # await unified_manager.stop()


# FIXED: Enhanced trading engine startup function
async def start_enhanced_trading_engine():
    """Enhanced trading engine startup with proper instrument service checking"""
    global trading_engine, instrument_service_instance
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            logger.info(
                f"🚀 Starting Enhanced Trading Engine (attempt {retry_count + 1}/{max_retries})"
            )

            # Start the trading engine
            if trading_engine:
                await trading_engine.start_trading_engine()
                logger.info("✅ Enhanced Trading Engine started successfully")
                break
            else:
                logger.error("Trading engine not initialized")
                break

        except Exception as e:
            retry_count += 1
            logger.error(
                f"❌ Enhanced Trading Engine failed (attempt {retry_count}): {e}"
            )

            if retry_count < max_retries:
                wait_time = 60 * retry_count
                logger.info(f"⏳ Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    "❌ Enhanced Trading Engine failed to start after all retries - continuing without engine"
                )


# FastAPI app initialization
app = FastAPI(
    title="Enhanced Trading Bot API with NEW Centralized WebSocket",
    description="AI-powered trading system with NEW single admin WebSocket + optimized architecture",
    version="3.0.0",
    lifespan=lifespan,
)

# CORS setup
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://resplendent-shortbread-e830d3.netlify.app",
    "https://growthquantix.com",
    "https://www.growthquantix.com",
    "https://api.growthquantix.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Refresh-Token",
        "X-CSRFToken",
    ],
    expose_headers=["Content-Disposition", "Authorization"],
)

app.add_middleware(TokenRefreshMiddleware)

# Include all routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(broker_router, prefix="/api/broker", tags=["Broker API"])
app.include_router(config_router, tags=["Configuration"])
app.include_router(stock_list_router, prefix="/api/stocks", tags=["Stock Data"])
app.include_router(upstox_router, prefix="/api/broker/upstox", tags=["Upstox API"])
app.include_router(fyers_router, prefix="/api/broker/fyers", tags=["Fyers API"])
app.include_router(broker_profile_router, tags=["Broker Profile & Funds"])
app.include_router(margin_trading_router, tags=["Margin-Aware Trading"])
app.include_router(dhan_router, prefix="/api/dhan", tags=["Dhan API"])
app.include_router(analytics_router.router, tags=["Analytics"])
app.include_router(order_router.router, tags=["Orders"])
app.include_router(ws_upstox_router, tags=["🗑️ Legacy WebSocket (REDUNDANT)"])
app.include_router(backtesting_router, prefix="/api/backtesting", tags=["Backtesting"])
app.include_router(stock_router, tags=["Stocks"])
app.include_router(profile_router, tags=["Profile"])
app.include_router(
    paper_trading_router, tags=["Paper Trading"]
)  # app.include_router(trading_config_router, prefix="/api", tags=["Trading Configuration"])
app.include_router(notification_router, tags=["Notifications"])
# app.include_router(dashboard_router, tags=["Dashboard & Trading Engine"])
# app.include_router(instrument_router, tags=["Instruments"])
app.include_router(websocket_router, tags=["🗑️ WebSocket Management (REDUNDANT)"])
app.include_router(debug_router, tags=["Debug"])
app.include_router(market_analytics_router, tags=["Market Analytics"])
app.include_router(heatmap_router, tags=["Heatmap & Sector Analysis"])
# 🚀 NEW: Simple Unified WebSocket System for Real-Time Market Data
try:
    from router.unified_websocket_routes import router as unified_websocket_router

    app.include_router(unified_websocket_router, tags=["🚀 Unified WebSocket - Real-Time"])
    logger.info("✅ Simple Unified WebSocket routes registered")
except ImportError as e:
    logger.warning(f"⚠️ Unified WebSocket routes not available: {e}")

app.include_router(paper_trading_router, tags=["Paper Trading"])
app.include_router(option_router, tags=["Options & Futures"])
app.include_router(auto_trading_router, tags=["Auto Trading & Stock Selection"])

# NIFTY 09:40 Strategy Router
try:
    from router.nifty_strategy_router import nifty_strategy_router

    app.include_router(nifty_strategy_router, tags=["NIFTY 09:40 Strategy"])
    logger.info("✅ NIFTY 09:40 Strategy routes registered")
except ImportError as e:
    logger.warning(f"⚠️ NIFTY strategy routes not available: {e}")


# 🚀 NEW: Add ZERO-DELAY real-time streaming routes
try:
    from router.realtime_stream_router import router as realtime_stream_router

    app.include_router(
        realtime_stream_router, tags=["🚀 ZERO-DELAY Real-time Streaming"]
    )
    logger.info("✅ 🚀 ZERO-DELAY real-time streaming routes registered")
except ImportError as e:
    logger.warning(f"⚠️ Real-time streaming routes not available: {e}")
    # Breakout router removed - using enhanced_breakout_engine instead
    logger.info("✅ Using enhanced_breakout_engine for breakout functionality")

# NEW: Add centralized WebSocket routes
if CENTRALIZED_ROUTES_AVAILABLE:
    app.include_router(
        centralized_market_ws_router,
        prefix="/api/v1",
        tags=["NEW: Centralized WebSocket"],
    )
    logger.info("✅ NEW: Centralized WebSocket routes registered")
else:
    logger.error("❌ NEW: Centralized WebSocket routes not available")

# Legacy market WebSocket for backward compatibility
if LEGACY_MARKET_WS_AVAILABLE:
    app.include_router(legacy_market_ws_router, tags=["Legacy Market WebSocket"])
    logger.info(
        "✅ Legacy market WebSocket routes available for backward compatibility"
    )


# Preflight handler
@app.options("/{full_path:path}")
async def preflight_handler(full_path: str):
    return JSONResponse(content={"message": "Preflight OK"}, status_code=200)


# ============================================================================
# SOCKET.IO SETUP - Simplified Integration for Stability
# ============================================================================
# Temporarily use basic Socket.IO setup to avoid ASGI compatibility issues
logger.info("🔧 Initializing Socket.IO with basic setup for stability")
sio = socketio.AsyncServer(
    async_mode="asgi", cors_allowed_origins=ALLOWED_ORIGINS, engineio_logger=False
)
sio_app = socketio.ASGIApp(sio, other_asgi_app=app)
SOCKET_IO_AVAILABLE = True


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with NEW centralized WebSocket system status"""
    redis_status = trading_redis.health_check()

    # Get centralized system status
    try:
        centralized_status = (
            await centralized_manager.health_check()
            if CENTRALIZED_WS_AVAILABLE and centralized_manager
            else {"status": "not_available"}
        )
    except Exception:
        centralized_status = {"status": "error"}

    # NEW: Get instrument registry status
    try:
        from services.instrument_registry import instrument_registry

        registry_stats = instrument_registry.get_stats()
    except Exception:
        registry_stats = {"status": "error"}

    return {
        "status": "running",
        "version": "3.0.0",
        "architecture": "hybrid_optimized_with_NEW_centralized_websocket",
        "new_centralized_websocket_system": {
            "available": CENTRALIZED_WS_AVAILABLE,
            "health_score": centralized_status.get("health_score", 0),
            "status": centralized_status.get("status", "unknown"),
            "ws_connected": centralized_status.get("ws_connected", False),
            "total_instruments": centralized_status.get("total_instruments", 0),
            "admin_token_strategy": True,
        },
        "instrument_registry": {
            "status": "active",
            "spot_instruments": registry_stats.get("spot_instruments", 0),
            "fno_instruments": registry_stats.get("fno_instruments", 0),
            "symbols": registry_stats.get("symbols", 0),
            "live_prices": registry_stats.get("live_prices", 0),
        },
        "existing_systems": {
            "optimized_instrument_service": instrument_service_instance is not None,
            "trading_engine": trading_engine.is_running if trading_engine else False,
            "redis_safety": redis_status["status"],
            "legacy_websocket": LEGACY_MARKET_WS_AVAILABLE,
        },
        "websocket_endpoints": {
            "new_centralized_dashboard": (
                "/api/v1/ws/dashboard"
                if CENTRALIZED_ROUTES_AVAILABLE
                else "not_available"
            ),
            "new_centralized_trading": (
                "/api/v1/ws/trading"
                if CENTRALIZED_ROUTES_AVAILABLE
                else "not_available"
            ),
            "legacy_market": (
                "/ws/market" if LEGACY_MARKET_WS_AVAILABLE else "not_available"
            ),
        },
        "redis_status": redis_status["status"],
        "timestamp": datetime.now().isoformat(),
        "market_analytics_system": {
            "available": ANALYTICS_SERVICE_AVAILABLE,
            "websocket_endpoint": "/ws/market-analytics",
            "active_connections": 0,  # Will be updated dynamically
            "features": [
                "real_time_market_data",
                "top_movers",
                "volume_analysis",
                "market_sentiment",
            ],
            "rest_endpoints": [
                "/api/analytics/top-movers",
                "/api/analytics/volume-analysis",
                "/api/analytics/market-sentiment",
                "/api/analytics/status",
                "/api/analytics/quick-data",
            ],
        },
    }


@app.get("/api/v1/trading/{symbol}")
async def get_trading_data(symbol: str):
    """Get comprehensive trading data for a symbol"""
    try:
        from services.instrument_registry import instrument_registry

        # Get spot price
        # spot_data = instrument_registry.get_spot_price(symbol.upper())
        # if not spot_data:
        #     return {
        #         "success": False,
        #         "error": f"Symbol {symbol} not found",
        #     }

        # Get options chain

        return {
            "success": True,
            # "spot": spot_data,
            # "options_chain": options_chain,
            "updated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Error getting trading data for {symbol}: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/v1/system/refresh-instruments")
async def refresh_instruments():
    """Admin endpoint to refresh instrument data"""
    try:
        logger.info("🔄 Manual instrument refresh requested")

        # Get trading service instance
        from services.instrument_refresh_service import get_trading_service

        instrument_service = get_trading_service()

        # Re-initialize the service
        result = await instrument_service.initialize_service()

        # Refresh centralized WebSocket manager
        if CENTRALIZED_WS_AVAILABLE and centralized_manager:
            await centralized_manager.initialize()

        # NEW: Refresh instrument registry
        # await instrument_registry.initialize_registry()

        return {
            "success": True,
            "message": "Instrument refresh completed successfully",
            "refresh_result": {
                "status": result.status,
                "websocket_keys": result.websocket_instruments,
                "dashboard_keys": result.dashboard_instruments,
                "filtered_instruments": result.filtered_instruments,
                "processing_time": result.processing_time,
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Error refreshing instruments: {e}")
        return {"success": False, "error": str(e)}


# FIXED: Health check endpoint
@app.get("/health")
async def enhanced_health_check():
    """Enhanced health check with NEW centralized WebSocket system"""
    global trading_engine, trading_scheduler, market_scheduler, instrument_service_instance

    redis_status = trading_redis.health_check()
    cache_stats = trading_redis.get_trading_cache_stats()

    # Get centralized system health
    try:
        centralized_health = (
            await centralized_manager.health_check()
            if CENTRALIZED_WS_AVAILABLE and centralized_manager
            else {"status": "not_available"}
        )
    except Exception as e:
        centralized_health = {"status": "error", "error": str(e)}

    # FIXED: Initialize health_status FIRST
    health_status = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0.0",
        "architecture": "hybrid_optimized_with_NEW_centralized_websocket",
        "services": {
            "database": "ok",
            "new_centralized_websocket": centralized_health.get("status", "unknown"),
            "trading_engine": "unknown",
            "trading_scheduler": "unknown",
            "market_scheduler": "unknown",
            "instrument_service": "unknown",
            "redis": redis_status["status"],
        },
        "new_centralized_websocket_details": centralized_health,
        "redis_details": redis_status,
        "cache_stats": cache_stats,
        "market_analytics": ("ok" if ANALYTICS_SERVICE_AVAILABLE else "not_available"),
    }

    # Check trading engine

    # Check trading scheduler
    if trading_scheduler:
        try:
            health_status["services"]["trading_scheduler"] = (
                "running" if trading_scheduler.is_running else "stopped"
            )
        except Exception:
            health_status["services"]["trading_scheduler"] = "error"

    # Check market scheduler
    if market_scheduler:
        try:
            health_status["services"]["market_scheduler"] = (
                "running" if market_scheduler.is_running else "stopped"
            )
        except Exception:
            health_status["services"]["market_scheduler"] = "error"

    # FIXED: Return the health_status
    return health_status


# FIXED: Centralized WebSocket system management endpoints (always available)
@app.get("/api/v1/system/centralized-status")
async def get_centralized_system_status():
    """Get detailed NEW centralized WebSocket system status"""
    try:
        if not CENTRALIZED_WS_AVAILABLE or not centralized_manager:
            return {
                "success": False,
                "error": "Centralized WebSocket system not available",
                "timestamp": datetime.now().isoformat(),
            }

        status = centralized_manager.get_status()
        health = await centralized_manager.health_check()

        return {
            "success": True,
            "system": "centralized_single_admin_websocket",
            "status": status,
            "health": health,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/v1/admin/restart-centralized-ws")
async def restart_centralized_websocket():
    """Admin endpoint to restart NEW centralized WebSocket system"""
    try:
        if not CENTRALIZED_WS_AVAILABLE or not centralized_manager:
            return {
                "success": False,
                "error": "Centralized WebSocket system not available",
                "timestamp": datetime.now().isoformat(),
            }

        logger.info("🔄 Admin requested NEW centralized WebSocket restart")

        await centralized_manager.stop()
        await asyncio.sleep(2)

        if await centralized_manager.initialize():
            await centralized_manager.start_connection()
            health = await centralized_manager.health_check()
            return {
                "success": True,
                "message": "NEW centralized WebSocket system restarted successfully",
                "health": health,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "message": "Failed to restart NEW centralized WebSocket system",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"❌ Error restarting NEW centralized WebSocket: {e}")
        return {"success": False, "error": str(e)}


# Engine status endpoint
@app.get("/api/engine/status")
async def get_enhanced_engine_status():
    """Get comprehensive trading engine status"""
    global trading_engine, trading_scheduler, market_scheduler, instrument_service_instance

    if not trading_engine:
        return {"error": "Trading engine not initialized"}

    try:
        current_time = datetime.now().time()

        # Determine current market phase
        if time(9, 0) <= current_time < time(9, 15):
            phase = "pre_market_analysis"
        elif time(9, 15) <= current_time < time(9, 30):
            phase = "market_preparation"
        elif time(9, 30) <= current_time < time(15, 30):
            phase = "active_trading"
        else:
            phase = "post_market"

        redis_status = trading_redis.health_check()

        # Get centralized system status
        try:
            centralized_status = (
                centralized_manager.get_status()
                if CENTRALIZED_WS_AVAILABLE and centralized_manager
                else {}
            )
            centralized_health = (
                await centralized_manager.health_check()
                if CENTRALIZED_WS_AVAILABLE and centralized_manager
                else {}
            )
        except Exception:
            centralized_status = {}
            centralized_health = {}

        status = {
            "engine": {
                "is_running": trading_engine.is_running,
                "current_phase": phase,
                "selected_stocks": {
                    "count": len(trading_engine.selected_stocks),
                    "symbols": list(trading_engine.selected_stocks.keys())[:10],
                },
                "active_users": len(trading_engine.active_users),
            },
            "scheduler": {
                "trading_scheduler_running": (
                    trading_scheduler.is_running if trading_scheduler else False
                ),
                "market_scheduler_running": (
                    market_scheduler.is_running if market_scheduler else False
                ),
            },
            "new_centralized_websocket_system": {
                "available": CENTRALIZED_WS_AVAILABLE,
                "health_score": centralized_health.get("health_score", 0),
                "ws_connected": centralized_status.get("ws_connected", False),
                "total_instruments": centralized_status.get("total_instruments", 0),
                "admin_token_strategy": True,
            },
            "redis_system": {
                "status": redis_status["status"],
                "is_connected": trading_redis.is_connected,
            },
            "timestamp": datetime.now().isoformat(),
        }

        return status

    except Exception as e:
        logger.error(f"❌ Error getting enhanced engine status: {e}")
        return {"error": str(e)}


@app.post("/api/engine/restart")
async def restart_trading_engine():
    """Restart the trading engine"""
    global trading_engine

    try:
        if trading_engine and trading_engine.is_running:
            logger.info("🔄 Restarting Enhanced Trading Engine...")
            trading_engine.stop_engine()
            await asyncio.sleep(5)

        if trading_engine:
            asyncio.create_task(start_enhanced_trading_engine())
            return {
                "message": "Enhanced trading engine restart initiated",
                "status": "restarting",
                "centralized_ws_compatible": CENTRALIZED_WS_AVAILABLE,
            }
        else:
            return {"error": "Trading engine not available"}

    except Exception as e:
        logger.error(f"❌ Enhanced engine restart failed: {e}")
        return {"error": str(e)}


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error on {request.url}: {str(exc)}")

    # Don't expose Redis connection errors
    if "redis" in str(exc).lower() or "connection" in str(exc).lower():
        logger.warning("Redis-related error handled gracefully")
        return JSONResponse(
            status_code=200,
            content={
                "message": "Service running in safe mode",
                "note": "Some caching features may be limited",
                "timestamp": datetime.now().isoformat(),
            },
        )

    if os.getenv("ENVIRONMENT") == "production":
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An error occurred. Please try again later.",
                "timestamp": datetime.now().isoformat(),
            },
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": str(exc),
                "message": "An internal server error occurred. Please check the logs.",
                "timestamp": datetime.now().isoformat(),
                "path": str(request.url),
            },
        )


@sio.event
async def disconnect(sid):
    logger.info(f"📡 Client disconnected: {sid}")


@sio.event
async def get_engine_status(sid, data):
    """Enhanced SocketIO endpoint with NEW centralized WebSocket system info"""
    global trading_engine, instrument_service_instance

    try:
        if trading_engine:
            redis_status = trading_redis.health_check()

            # Get centralized system status
            try:
                centralized_status = (
                    centralized_manager.get_status()
                    if CENTRALIZED_WS_AVAILABLE and centralized_manager
                    else {}
                )
            except Exception:
                centralized_status = {}

            status = {
                "is_running": trading_engine.is_running,
                "selected_stocks_count": len(trading_engine.selected_stocks),
                "active_users_count": len(trading_engine.active_users),
                "instrument_service_active": instrument_service_instance is not None,
                "redis_status": redis_status["status"],
                "new_centralized_websocket_system": {
                    "available": CENTRALIZED_WS_AVAILABLE,
                    "ws_connected": centralized_status.get("ws_connected", False),
                    "admin_token_strategy": True,
                },
                "architecture": "hybrid_optimized_with_NEW_centralized_websocket",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            status = {"error": "Trading engine not available"}

        await sio.emit("engine_status_update", status, to=sid)

    except Exception as e:
        await sio.emit("error", {"message": str(e)}, to=sid)


# Main runner
if __name__ == "__main__":
    logger.info(
        "🚀 Launching Enhanced Trading Platform with NEW Centralized WebSocket System..."
    )

    # Log system configuration
    logger.info(f"🔧 Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"🔧 Redis Enabled: {os.getenv('REDIS_ENABLED', 'true')}")
    logger.info(
        f"🔧 NEW Centralized WebSocket: {'Available' if CENTRALIZED_WS_AVAILABLE else 'Not Available'}"
    )
    logger.info(
        f"🔧 NEW Centralized Routes: {'Available' if CENTRALIZED_ROUTES_AVAILABLE else 'Not Available'}"
    )
    logger.info(
        f"🔧 Legacy WebSocket: {'Available' if LEGACY_MARKET_WS_AVAILABLE else 'Not Available'}"
    )
    logger.info(
        f"🔧 Trading Scheduler: {'Available' if TRADING_SCHEDULER_AVAILABLE else 'Not Available'}"
    )
    logger.info(
        f"🔧 Analytics Service: {'Available' if ANALYTICS_SERVICE_AVAILABLE else 'Not Available'}"
    )
    # logger.info(
    #     f"🔧 Analytics Processor: {'Available' if ANALYTICS_PROCESSOR_AVAILABLE else 'Not Available'}"
    # )

    uvicorn.run(
        "app:sio_app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        log_level="info",
        reload=os.getenv("DEBUG", "false").lower() == "true",
        workers=1,
    )
