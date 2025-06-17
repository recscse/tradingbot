import asyncio
import logging
import os
from datetime import datetime, time
from contextlib import asynccontextmanager
import threading
import uvicorn
import socketio
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Import your existing Redis safety manager
from typing import Optional, Any
import redis
from redis.exceptions import ConnectionError, RedisError
import json

# Import your existing database and models
from core.middleware import TokenRefreshMiddleware
from database.connection import SessionLocal, get_db
from database.init_db import init_db
from database.models import BrokerConfig, TradePerformance, TradeSignal, User

# Load environment variables FIRST
load_dotenv()

# Configure logging EARLY
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# NEW: Add centralized WebSocket system imports
try:
    from services.centralized_ws_manager import centralized_manager

    CENTRALIZED_WS_AVAILABLE = True
    logger.info("✅ NEW: Centralized WebSocket manager imported successfully")
except ImportError as e:
    CENTRALIZED_WS_AVAILABLE = False
    logger.error(f"❌ NEW: Centralized WebSocket manager not available: {e}")

    # Fallback dummy manager
    class DummyCentralizedManager:
        def __init__(self):
            self.is_running = False

        async def initialize(self):
            return False

        async def start_connection(self):
            pass

        async def stop(self):
            pass

        def get_status(self):
            return {"status": "not_available"}

        async def health_check(self):
            return {"status": "not_available"}

    centralized_manager = DummyCentralizedManager()

# Import your existing routers
from router import analytics_router, order_router
from router.user_router import router as user_router
from router.auth_router import auth_router
from router.broker_router import broker_router
from router.stock_list_router import stock_list_router
from router.dhan_router import dhan_router
from router.upstox_router import upstox_router
from router.fyers_router import fyers_router
from router.market_data_router import market_data_router
from services import stop_loss_router
from ws_router.upstox_ltp_ws import ws_upstox_router
from router.backtest_router import backtesting_router
from router.stock_router import router as stock_router
from router.profile_router import router as profile_router
from router.paper_trading_router import router as paper_trading_router
from router.notification_router import router as notification_router

# NEW: Import centralized WebSocket routes
try:
    from router.market_ws import (
        router as centralized_market_ws_router,
    )  # FIXED: routes not router

    CENTRALIZED_ROUTES_AVAILABLE = True
    logger.info("✅ NEW: Centralized WebSocket routes imported successfully")
except ImportError as e:
    CENTRALIZED_ROUTES_AVAILABLE = False
    logger.error(f"❌ NEW: Centralized WebSocket routes not available: {e}")
    from fastapi import APIRouter

    centralized_market_ws_router = APIRouter()

# LEGACY: Import existing market WebSocket router for backward compatibility
try:
    from router.market_ws import router as legacy_market_ws_router

    LEGACY_MARKET_WS_AVAILABLE = True
    logger.info(
        "✅ Legacy market WebSocket routes available for backward compatibility"
    )
except ImportError:
    LEGACY_MARKET_WS_AVAILABLE = False
    logger.warning("⚠️ Legacy market WebSocket routes not available")

# KEEP: Your existing trading engine and services
from services.trading_services.trading_engine import TradingEngine
from router.dashboard_router import router as dashboard_router

# FIXED: Import optimized instrument service correctly
try:
    from services.optimized_instrument_service import (
        get_instrument_service,
        get_fast_retrieval,
        initialize_instrument_system,
        is_initialized as instrument_is_initialized,
        health_check as instrument_health_check,
    )

    OPTIMIZED_INSTRUMENTS_AVAILABLE = True
    logger.info("✅ Optimized instrument service functions imported successfully")
except ImportError as e:
    OPTIMIZED_INSTRUMENTS_AVAILABLE = False
    logger.warning(f"⚠️ Optimized instrument service not available: {e}")

    # Create fallback functions
    def get_instrument_service():
        return None

    def get_fast_retrieval():
        return None

    async def initialize_instrument_system():
        return type(
            "Result",
            (),
            {
                "status": "not_available",
                "mapped_stocks": 0,
                "websocket_instruments": 0,
                "message": "Optimized instrument service not available",
            },
        )()

    async def instrument_health_check():
        return {"status": "not_available"}

    def instrument_is_initialized():
        return False


# FIXED: Import trading scheduler correctly
try:
    from services.trading_scheduler import TradingScheduler

    # Note: start_trading_scheduler might not exist or be used differently
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


# KEEP: Your existing pre-market service import
try:
    from services.pre_market_data_service import (
        PreMarketDataService,
        get_cached_trading_stocks,
    )
except ImportError:

    def get_cached_trading_stocks():
        return []

    logger.warning("⚠️ Pre-market data service not available")


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
instrument_service_instance = None
fast_retrieval_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Enhanced lifespan with NEW centralized WebSocket system integration"""
    global trading_engine, trading_scheduler, instrument_service_instance, fast_retrieval_instance

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

        # 3. NEW: Initialize Centralized WebSocket System FIRST
        if CENTRALIZED_WS_AVAILABLE:
            logger.info("🔌 Initializing NEW Centralized WebSocket System...")
            try:
                if await centralized_manager.initialize():
                    await centralized_manager.start_connection()

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

        # 4. FIXED: Initialize OptimizedInstrumentService correctly
        logger.info("🔧 Initializing OptimizedInstrumentService...")
        if OPTIMIZED_INSTRUMENTS_AVAILABLE:
            try:
                # Get singleton instances using factory functions
                instrument_service_instance = get_instrument_service()
                fast_retrieval_instance = get_fast_retrieval()

                # Initialize the system
                result = await initialize_instrument_system()

                if result.status == "success":
                    logger.info(
                        f"✅ Optimized instrument service initialized: {result.mapped_stocks} stocks, {result.websocket_instruments} instruments"
                    )
                else:
                    logger.warning(
                        f"⚠️ Instrument initialization had issues: {result.error if hasattr(result, 'error') else 'Unknown error'}"
                    )

            except Exception as e:
                logger.warning(
                    f"⚠️ Instrument service initialization failed: {e} - continuing with limited functionality"
                )
                instrument_service_instance = None
                fast_retrieval_instance = None
        else:
            logger.warning("⚠️ Optimized instrument service not available")

        # 5. FIXED: Initialize TradingScheduler correctly
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

        # 6. Initialize trading engine
        try:
            trading_engine = TradingEngine()
            logger.info("🤖 Trading Engine initialized.")
        except Exception as e:
            logger.error(f"❌ Trading Engine initialization failed: {e}")

        # 7. Start background tasks
        if trading_engine:
            engine_task = asyncio.create_task(start_enhanced_trading_engine())
            logger.info("⚡ Enhanced Trading Engine background task started.")

        broadcast_task = asyncio.create_task(broadcast_trading_updates())
        logger.info("📡 Background broadcast service started.")

        logger.info(
            "🟢 All services started successfully with NEW Centralized WebSocket + Optimized Architecture!"
        )

        yield

    except Exception as e:
        logger.exception("🔥 Enhanced lifespan startup failed - but app will continue")
        yield
    finally:
        # Enhanced cleanup
        logger.info("🛑 Starting enhanced shutdown...")

        # NEW: Stop centralized WebSocket system
        if CENTRALIZED_WS_AVAILABLE:
            try:
                await centralized_manager.stop()
                logger.info("✅ NEW: Centralized WebSocket system stopped")
            except Exception as e:
                logger.error(f"Error stopping centralized WebSocket: {e}")

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

        logger.info("🛑 Enhanced lifespan shutdown complete.")


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

            # Check if instrument service is ready using the correct method
            if not instrument_service_instance:
                logger.warning(
                    "⚠️ Instrument service not ready, attempting initialization..."
                )
                if OPTIMIZED_INSTRUMENTS_AVAILABLE:
                    try:
                        instrument_service_instance = get_instrument_service()
                        await initialize_instrument_system()
                    except Exception as e:
                        logger.warning(f"Instrument service still unavailable: {e}")
            elif OPTIMIZED_INSTRUMENTS_AVAILABLE:
                # Use the correct function to check if initialized
                if not instrument_is_initialized():
                    logger.warning(
                        "⚠️ Instrument service not initialized, attempting initialization..."
                    )
                    try:
                        await initialize_instrument_system()
                    except Exception as e:
                        logger.warning(f"Instrument service initialization failed: {e}")

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
app.include_router(stock_list_router, prefix="/api/stocks", tags=["Stock Data"])
app.include_router(upstox_router, prefix="/api/broker/upstox", tags=["Upstox API"])
app.include_router(fyers_router, prefix="/api/broker/fyers", tags=["Fyers API"])
app.include_router(dhan_router, prefix="/api/dhan", tags=["Dhan API"])
app.include_router(market_data_router, tags=["Market Data"])
app.include_router(analytics_router.router, tags=["Analytics"])
app.include_router(order_router.router, tags=["Orders"])
app.include_router(stop_loss_router.router, tags=["Stop Loss"])
app.include_router(ws_upstox_router, tags=["Legacy WebSocket"])
app.include_router(backtesting_router, prefix="/api/backtesting", tags=["Backtesting"])
app.include_router(stock_router, tags=["Stocks"])
app.include_router(profile_router, tags=["Profile"])
app.include_router(paper_trading_router, tags=["Paper Trading"])
app.include_router(notification_router, tags=["Notifications"])
app.include_router(dashboard_router, tags=["Dashboard & Trading Engine"])

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


# SocketIO setup
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=ALLOWED_ORIGINS)
sio_app = socketio.ASGIApp(sio, other_asgi_app=app)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with NEW centralized WebSocket system status"""
    redis_status = trading_redis.health_check()

    # Get centralized system status
    try:
        centralized_status = (
            await centralized_manager.health_check()
            if CENTRALIZED_WS_AVAILABLE
            else {"status": "not_available"}
        )
    except Exception:
        centralized_status = {"status": "error"}

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
    }


# Health check endpoint
@app.get("/health")
async def enhanced_health_check():
    """Enhanced health check with NEW centralized WebSocket system"""
    global trading_engine, trading_scheduler, instrument_service_instance

    redis_status = trading_redis.health_check()
    cache_stats = trading_redis.get_trading_cache_stats()

    # Get centralized system health
    try:
        centralized_health = (
            await centralized_manager.health_check()
            if CENTRALIZED_WS_AVAILABLE
            else {"status": "not_available"}
        )
    except Exception as e:
        centralized_health = {"status": "error", "error": str(e)}

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
            "instrument_service": "unknown",
            "redis": redis_status["status"],
        },
        "new_centralized_websocket_details": centralized_health,
        "redis_details": redis_status,
        "cache_stats": cache_stats,
    }

    # Check trading engine
    if trading_engine:
        try:
            health_status["services"]["trading_engine"] = (
                "running" if trading_engine.is_running else "stopped"
            )
            health_status["trading_engine_details"] = {
                "selected_stocks_count": len(trading_engine.selected_stocks),
                "active_users_count": len(trading_engine.active_users),
            }
        except Exception as e:
            health_status["services"]["trading_engine"] = "error"
            health_status["trading_engine_error"] = str(e)

    # Check trading scheduler
    if trading_scheduler:
        try:
            health_status["services"]["trading_scheduler"] = (
                "running" if trading_scheduler.is_running else "stopped"
            )
        except Exception:
            health_status["services"]["trading_scheduler"] = "error"

    # Check instrument service
    if instrument_service_instance and OPTIMIZED_INSTRUMENTS_AVAILABLE:
        try:
            health_status["services"]["instrument_service"] = "running"
            health_status["instrument_service_details"] = {
                "service_type": "optimized_redis_with_fallback",
                "initialized": instrument_is_initialized(),
            }
        except Exception:
            health_status["services"]["instrument_service"] = "error"

    return health_status


# NEW: Centralized WebSocket system management endpoints
if CENTRALIZED_WS_AVAILABLE:

    @app.get("/api/v1/system/centralized-status")
    async def get_centralized_system_status():
        """Get detailed NEW centralized WebSocket system status"""
        try:
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


# Essential API endpoints
@app.get("/api/selected-stocks/today")
async def get_todays_selected_stocks():
    """Get today's selected stocks for trading"""
    try:
        cached_stocks = trading_redis.get("selected_stocks_today", [])

        if cached_stocks:
            return {
                "success": True,
                "selectedStocks": cached_stocks,
                "count": len(cached_stocks),
                "timestamp": datetime.now().isoformat(),
                "data_source": "redis_cache",
            }

        selected_stocks = get_cached_trading_stocks()

        if selected_stocks:
            trading_redis.set("selected_stocks_today", selected_stocks, ttl=3600)

        return {
            "success": True,
            "selectedStocks": selected_stocks or [],
            "count": len(selected_stocks) if selected_stocks else 0,
            "timestamp": datetime.now().isoformat(),
            "data_source": "pre_market_analysis",
        }
    except Exception as e:
        logger.error(f"Error getting selected stocks: {e}")
        return {"success": False, "selectedStocks": [], "count": 0, "error": str(e)}


@app.post("/api/trigger-stock-selection")
async def trigger_stock_selection():
    """Manually trigger stock selection process"""
    try:
        logger.info("🎯 Manual stock selection triggered")

        trading_redis.set(
            "manual_stock_selection_triggered",
            {"timestamp": datetime.now().isoformat(), "triggered_by": "api_endpoint"},
            ttl=3600,
        )

        return {
            "success": True,
            "message": "Stock selection process triggered",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error triggering selection: {e}")
        return {"success": False, "error": str(e)}


# FIXED: Instrument stats endpoint
@app.get("/api/instruments/stats")
async def get_instrument_stats():
    """Get instrument service statistics (fixed to work with singleton pattern)"""
    try:
        redis_status = trading_redis.health_check()

        # Use the correct way to get WebSocket keys
        try:
            if fast_retrieval_instance and OPTIMIZED_INSTRUMENTS_AVAILABLE:
                all_ws_keys = await fast_retrieval_instance.get_all_websocket_keys()
            else:
                all_ws_keys = []
        except Exception as e:
            logger.warning(f"Error getting websocket keys: {e}")
            all_ws_keys = []

        sample_stocks = ["RELIANCE", "TCS", "HDFC", "INFY", "ICICIBANK"]
        stock_details = {}

        for symbol in sample_stocks:
            try:
                if fast_retrieval_instance:
                    mapping = await fast_retrieval_instance.get_stock_instruments_async(
                        symbol
                    )
                    if mapping:
                        stock_details[symbol] = {
                            "total_instruments": mapping.get("instrument_count", 0),
                            "websocket_keys": len(mapping.get("websocket_keys", [])),
                            "primary_key": mapping.get("primary_instrument_key"),
                        }
            except Exception:
                continue

        return {
            "total_websocket_instruments": len(all_ws_keys),
            "sample_stocks": stock_details,
            "cache_status": "active_with_fallback",
            "redis_status": redis_status["status"],
            "centralized_ws_compatible": CENTRALIZED_WS_AVAILABLE,
            "service_available": OPTIMIZED_INSTRUMENTS_AVAILABLE,
            "service_initialized": (
                instrument_is_initialized()
                if OPTIMIZED_INSTRUMENTS_AVAILABLE
                else False
            ),
            "last_updated": datetime.now().isoformat(),
        }

    except Exception as e:
        return {"error": str(e)}


# Engine status endpoint
@app.get("/api/engine/status")
async def get_enhanced_engine_status():
    """Get comprehensive trading engine status"""
    global trading_engine, trading_scheduler, instrument_service_instance

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
                centralized_manager.get_status() if CENTRALIZED_WS_AVAILABLE else {}
            )
            centralized_health = (
                await centralized_manager.health_check()
                if CENTRALIZED_WS_AVAILABLE
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
                "is_running": (
                    trading_scheduler.is_running if trading_scheduler else False
                ),
            },
            "new_centralized_websocket_system": {
                "available": CENTRALIZED_WS_AVAILABLE,
                "health_score": centralized_health.get("health_score", 0),
                "ws_connected": centralized_status.get("ws_connected", False),
                "total_instruments": centralized_status.get("total_instruments", 0),
                "admin_token_strategy": True,
            },
            "instrument_service": {
                "is_initialized": instrument_service_instance is not None,
                "service_available": OPTIMIZED_INSTRUMENTS_AVAILABLE,
                "initialized": (
                    instrument_is_initialized()
                    if OPTIMIZED_INSTRUMENTS_AVAILABLE
                    else False
                ),
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


# Enhanced broadcast function
async def broadcast_trading_updates():
    """Enhanced broadcast with NEW centralized WebSocket system awareness"""
    global trading_engine, trading_scheduler, instrument_service_instance

    while True:
        try:
            if trading_engine and hasattr(sio, "emit"):
                redis_status = trading_redis.health_check()

                # Get centralized system status
                try:
                    centralized_status = (
                        centralized_manager.get_status()
                        if CENTRALIZED_WS_AVAILABLE
                        else {}
                    )
                    centralized_health = (
                        await centralized_manager.health_check()
                        if CENTRALIZED_WS_AVAILABLE
                        else {}
                    )
                except Exception:
                    centralized_status = {}
                    centralized_health = {}

                status_update = {
                    "type": "enhanced_engine_status_with_NEW_centralized_ws",
                    "data": {
                        "engine": {
                            "is_running": trading_engine.is_running,
                            "selected_stocks_count": len(
                                trading_engine.selected_stocks
                            ),
                        },
                        "scheduler": {
                            "is_running": (
                                trading_scheduler.is_running
                                if trading_scheduler
                                else False
                            )
                        },
                        "instrument_service": {
                            "status": (
                                "active" if instrument_service_instance else "inactive"
                            )
                        },
                        "new_centralized_websocket_system": {
                            "available": CENTRALIZED_WS_AVAILABLE,
                            "health_score": centralized_health.get("health_score", 0),
                            "ws_connected": centralized_status.get(
                                "ws_connected", False
                            ),
                            "admin_token_strategy": True,
                        },
                        "redis": {
                            "status": redis_status["status"],
                        },
                        "architecture": "hybrid_optimized_with_NEW_centralized_websocket",
                        "timestamp": datetime.now().isoformat(),
                    },
                }

                await sio.emit("trading_update", status_update, room="trading_updates")

            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"❌ Enhanced broadcast error: {e}")
            await asyncio.sleep(60)


# Helper function
def _get_current_market_phase():
    """Get current market phase"""
    current_time = datetime.now().time()

    if time(9, 0) <= current_time < time(9, 15):
        return "pre_market_analysis"
    elif time(9, 15) <= current_time < time(9, 30):
        return "market_preparation"
    elif time(9, 30) <= current_time < time(15, 30):
        return "active_trading"
    else:
        return "post_market"


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


# SocketIO events
@sio.event
async def connect(sid, environ):
    logger.info(f"📡 Client connected: {sid}")
    redis_status = trading_redis.health_check()

    # Get centralized system status
    try:
        centralized_status = (
            centralized_manager.get_status() if CENTRALIZED_WS_AVAILABLE else {}
        )
    except Exception:
        centralized_status = {}

    await sio.emit(
        "connection_status",
        {
            "status": "connected",
            "architecture": "hybrid_optimized_with_NEW_centralized_websocket",
            "redis_mode": redis_status["status"],
            "new_centralized_websocket": {
                "available": CENTRALIZED_WS_AVAILABLE,
                "ws_connected": centralized_status.get("ws_connected", False),
            },
        },
        to=sid,
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
                    centralized_manager.get_status() if CENTRALIZED_WS_AVAILABLE else {}
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


@sio.event
async def subscribe_to_updates(sid, data):
    """Subscribe to real-time trading updates"""
    try:
        await sio.enter_room(sid, "trading_updates")
        redis_status = trading_redis.health_check()

        await sio.emit(
            "subscription_status",
            {
                "status": "subscribed",
                "architecture": "hybrid_optimized_with_NEW_centralized_websocket",
                "redis_mode": redis_status["status"],
            },
            to=sid,
        )

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
        f"🔧 Optimized Instruments: {'Available' if OPTIMIZED_INSTRUMENTS_AVAILABLE else 'Not Available'}"
    )
    logger.info(
        f"🔧 Trading Scheduler: {'Available' if TRADING_SCHEDULER_AVAILABLE else 'Not Available'}"
    )

    uvicorn.run(
        "app:sio_app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        log_level="info",
        reload=os.getenv("DEBUG", "false").lower() == "true",
        workers=1,
    )
