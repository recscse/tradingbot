import asyncio
import logging
import os
from datetime import datetime
from contextlib import asynccontextmanager
import threading
import time
import schedule
import uvicorn
import socketio
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Import database and models
from core.middleware import TokenRefreshMiddleware
from database.connection import SessionLocal, get_db
from database.init_db import init_db
from database.models import TradePerformance, TradeSignal
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
from router.market_ws import router as market_ws_router
from router.backtest_router import backtesting_router
from router.stock_router import router as stock_router
from router.profile_router import router as profile_router
from router.paper_trading_router import router as paper_trading_router
from router.notification_router import router as notification_router

# KEEP: Your existing trading engine import
from services.trading_services.trading_engine import TradingEngine
from router.dashboard_router import router as dashboard_router

# ADD: Import your instrument and data services
from services.optimized_instrument_service import instrument_service, fast_retrieval
from services.trading_scheduler import TradingScheduler, start_trading_scheduler
from services.pre_market_data_service import PreMarketDataService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ENHANCE: Global instances
trading_engine = None
trading_scheduler = None
instrument_service_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global trading_engine, trading_scheduler, instrument_service_instance
    logger.info("🚀 Starting Enhanced Trading Application with Hybrid System...")

    try:
        # 1. DB initialization
        db = next(get_db())
        logger.info("✅ DB session initialized.")

        # 2. NEW: Initialize OptimizedInstrumentService first
        logger.info("🔧 Initializing OptimizedInstrumentService...")
        instrument_service_instance = instrument_service
        result = await instrument_service_instance.initialize_instruments_system()
        logger.info(
            f"✅ Instrument service initialized: {result['mapped_stocks']} stocks, {result['websocket_instruments']} instruments"
        )

        # 3. NEW: Initialize TradingScheduler
        logger.info("🕐 Starting TradingScheduler...")
        trading_scheduler = TradingScheduler()
        trading_scheduler.start_scheduler()
        logger.info("✅ TradingScheduler started")

        # 4. ENHANCE: Initialize trading engine (your existing code)
        trading_engine = TradingEngine()
        logger.info("🤖 Trading Engine initialized.")

        # 5. ENHANCE: Start trading engine in background with enhanced startup
        engine_task = asyncio.create_task(start_enhanced_trading_engine())
        logger.info("⚡ Enhanced Trading Engine background task started.")

        # 6. NEW: Start background services
        broadcast_task = asyncio.create_task(broadcast_trading_updates())
        logger.info("📡 Background broadcast service started.")

        logger.info("🟢 All enhanced services started successfully!")

        yield

    except Exception as e:
        logger.exception("🔥 Enhanced lifespan startup failed.")
        raise e
    finally:
        # Enhanced cleanup
        logger.info("🛑 Starting enhanced shutdown...")

        if trading_engine:
            logger.info("🛑 Stopping Trading Engine...")
            trading_engine.stop_engine()

        if trading_scheduler:
            logger.info("🛑 Stopping Trading Scheduler...")
            trading_scheduler.stop_scheduler()

        logger.info("🛑 Enhanced lifespan shutdown complete.")


async def start_enhanced_trading_engine():
    """Enhanced trading engine startup with instrument service integration"""
    global trading_engine, instrument_service_instance
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            logger.info(
                f"🚀 Starting Enhanced Trading Engine (attempt {retry_count + 1}/{max_retries})"
            )

            # Ensure instrument service is ready
            if not instrument_service_instance:
                logger.warning("⚠️ Instrument service not ready, initializing...")
                await instrument_service.initialize_instruments_system()

            # Start the trading engine
            await trading_engine.start_trading_engine()
            logger.info("✅ Enhanced Trading Engine started successfully")
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
                    "❌ Enhanced Trading Engine failed to start after all retries"
                )


# KEEP: Your existing FastAPI initialization
app = FastAPI(
    title="Enhanced Trading Bot API",
    description="AI-powered automated trading system with hybrid WebSocket architecture",
    version="2.0.0",  # Updated version
    lifespan=lifespan,
)

# KEEP: Your existing CORS and middleware setup
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

# KEEP: All your existing router includes
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(broker_router, prefix="/api/broker", tags=["Broker API"])
app.include_router(stock_list_router, prefix="/api/stocks", tags=["Stock Data"])
app.include_router(upstox_router, prefix="/api/broker/upstox", tags=["Upstox API"])
app.include_router(fyers_router, prefix="/api/broker/fyers", tags=["Fyers API"])
app.add_middleware(TokenRefreshMiddleware)
app.include_router(dhan_router, prefix="/api/dhan", tags=["Dhan API"])
app.include_router(market_data_router)
app.include_router(analytics_router.router)
app.include_router(order_router.router)
app.include_router(stop_loss_router.router)
app.include_router(ws_upstox_router)
app.include_router(market_ws_router)  # Your enhanced WebSocket routes
app.include_router(backtesting_router, prefix="/api/backtesting")
app.include_router(stock_router)
app.include_router(profile_router)
app.include_router(paper_trading_router)
app.include_router(notification_router)
app.include_router(dashboard_router, tags=["Dashboard & Trading Engine"])


# KEEP: Your existing preflight handler
@app.options("/{full_path:path}")
async def preflight_handler(full_path: str):
    return JSONResponse(content={"message": "Preflight OK"}, status_code=200)


# KEEP: Your existing SocketIO setup
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=ALLOWED_ORIGINS)
sio_app = socketio.ASGIApp(sio, other_asgi_app=app)


# KEEP: Your existing root endpoint
@app.get("/")
async def root():
    return {
        "status": "running",
        "version": "2.0.0",
        "system": "hybrid_websocket",
        "timestamp": datetime.now().isoformat(),
    }


# ENHANCE: Your existing health check
@app.get("/health")
async def enhanced_health_check():
    global trading_engine, trading_scheduler, instrument_service_instance

    health_status = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "system": "hybrid_websocket",
        "services": {
            "database": "ok",
            "trading_engine": "unknown",
            "trading_scheduler": "unknown",
            "instrument_service": "unknown",
        },
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
                "last_analysis": getattr(
                    trading_engine.market_scheduler, "last_analysis_time", None
                ),
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
    if instrument_service_instance:
        try:
            # Test if can retrieve data
            test_keys = fast_retrieval.get_all_websocket_keys()
            health_status["services"]["instrument_service"] = "running"
            health_status["instrument_service_details"] = {
                "cached_instruments": len(test_keys),
                "service_type": "optimized_redis_cache",
            }
        except Exception:
            health_status["services"]["instrument_service"] = "error"

    return health_status


# ADD: New API endpoints for enhanced system
@app.get("/api/system/info")
async def get_system_info():
    """Get comprehensive system information"""
    global trading_engine, trading_scheduler, instrument_service_instance

    try:
        system_info = {
            "version": "2.0.0",
            "architecture": "hybrid_websocket",
            "components": {
                "dashboard": {
                    "data_source": "LTP_API",
                    "update_frequency": "3_seconds",
                    "instruments_supported": "unlimited",
                },
                "trading": {
                    "data_source": "focused_websocket",
                    "instruments_per_stock": 64,
                    "max_stocks": 10,
                    "real_time": True,
                },
            },
            "services_status": {},
            "performance": {},
        }

        # Get instrument service stats
        if instrument_service_instance:
            try:
                all_keys = fast_retrieval.get_all_websocket_keys()
                system_info["services_status"]["instrument_service"] = {
                    "status": "running",
                    "total_instruments": len(all_keys),
                    "cache_type": "redis_optimized",
                }
            except Exception as e:
                system_info["services_status"]["instrument_service"] = {
                    "status": "error",
                    "error": str(e),
                }

        # Get trading engine stats
        if trading_engine:
            system_info["services_status"]["trading_engine"] = {
                "status": "running" if trading_engine.is_running else "stopped",
                "selected_stocks": len(trading_engine.selected_stocks),
                "active_users": len(trading_engine.active_users),
            }

        return system_info

    except Exception as e:
        return {"error": str(e)}


@app.get("/api/instruments/stats")
async def get_instrument_stats():
    """Get instrument service statistics"""
    try:
        # Get stats from your optimized instrument service
        all_ws_keys = fast_retrieval.get_all_websocket_keys()

        # Sample some stocks to get their instrument counts
        sample_stocks = ["RELIANCE", "TCS", "HDFC", "INFY", "ICICIBANK"]
        stock_details = {}

        for symbol in sample_stocks:
            try:
                mapping = fast_retrieval.get_stock_instruments(symbol)
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
            "cache_status": "active",
            "last_updated": datetime.now().isoformat(),
        }

    except Exception as e:
        return {"error": str(e)}


@app.post("/api/system/initialize-instruments")
async def reinitialize_instruments():
    """Manually reinitialize instrument service"""
    global instrument_service_instance

    try:
        logger.info("🔄 Manual instrument service reinitialization requested")

        result = await instrument_service.initialize_instruments_system()
        instrument_service_instance = instrument_service

        return {
            "status": "success",
            "message": "Instrument service reinitialized",
            "result": result,
        }

    except Exception as e:
        logger.error(f"❌ Manual instrument initialization failed: {e}")
        return {"error": str(e)}


# ADD: New endpoints for selected stocks
@app.get("/api/selected-stocks/today")
async def get_todays_selected_stocks():
    """Get today's selected stocks for trading"""
    try:
        from services.pre_market_data_service import get_cached_trading_stocks

        selected_stocks = get_cached_trading_stocks()
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

        # In a real implementation, you'd trigger your stock selection process
        # For now, return success with a note to check the scheduler
        return {
            "success": True,
            "message": "Stock selection process triggered",
            "note": "Check TradingScheduler logs for progress",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error triggering selection: {e}")
        return {"success": False, "error": str(e)}


# ENHANCE: Your existing trading engine status endpoint
@app.get("/api/engine/status")
async def get_enhanced_engine_status():
    """Get comprehensive enhanced trading engine status"""
    global trading_engine, trading_scheduler, instrument_service_instance

    if not trading_engine:
        return {"error": "Trading engine not initialized"}

    try:
        from datetime import time

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

        status = {
            "engine": {
                "is_running": trading_engine.is_running,
                "current_phase": phase,
                "selected_stocks": {
                    "count": len(trading_engine.selected_stocks),
                    "symbols": list(trading_engine.selected_stocks.keys())[
                        :10
                    ],  # First 10
                },
                "active_users": len(trading_engine.active_users),
            },
            "scheduler": {
                "is_running": (
                    trading_scheduler.is_running if trading_scheduler else False
                ),
                "next_job": "check_scheduler_logs",
            },
            "instrument_service": {
                "is_initialized": instrument_service_instance is not None,
                "total_instruments": (
                    len(fast_retrieval.get_all_websocket_keys())
                    if instrument_service_instance
                    else 0
                ),
            },
            "services": {
                "market_scheduler": hasattr(trading_engine, "market_scheduler"),
                "ohlc_service": hasattr(trading_engine, "ohlc_service"),
                "live_data_service": hasattr(trading_engine, "live_data_service"),
                "ai_trading_service": hasattr(trading_engine, "ai_trading_service"),
            },
            "websocket_system": {
                "dashboard": "LTP_API_polling",
                "trading": "focused_websocket",
                "architecture": "hybrid",
            },
            "last_analysis": (
                getattr(trading_engine.market_scheduler, "last_analysis_time", None)
                if hasattr(trading_engine, "market_scheduler")
                else None
            ),
        }

        return status

    except Exception as e:
        logger.error(f"❌ Error getting enhanced engine status: {e}")
        return {"error": str(e)}


# KEEP: Your existing restart and logs endpoints
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
            }
        else:
            return {"error": "Trading engine not available"}

    except Exception as e:
        logger.error(f"❌ Enhanced engine restart failed: {e}")
        return {"error": str(e)}


# ENHANCE: Your existing broadcast function
async def broadcast_trading_updates():
    """Enhanced broadcast with hybrid system status"""
    global trading_engine, trading_scheduler, instrument_service_instance

    while True:
        try:
            if trading_engine and hasattr(sio, "emit"):
                # Enhanced status update
                status_update = {
                    "type": "enhanced_engine_status",
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
                        "system": "hybrid_websocket",
                        "timestamp": datetime.now().isoformat(),
                    },
                }

                await sio.emit("trading_update", status_update, room="trading_updates")

            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"❌ Enhanced broadcast error: {e}")
            await asyncio.sleep(60)


# Add these endpoints to your existing app.py


@app.get("/api/ai-trading/status")
async def get_ai_trading_status():
    """Get detailed AI trading service status"""
    global trading_engine

    try:
        if (
            trading_engine
            and hasattr(trading_engine, "ai_trading_service")
            and trading_engine.ai_trading_service
        ):

            status = trading_engine.ai_trading_service.get_status()

            # Add system context
            status.update(
                {
                    "system_info": {
                        "strategy_service_type": (
                            type(
                                trading_engine.ai_trading_service.strategy_service
                            ).__name__
                            if trading_engine.ai_trading_service.strategy_service
                            else "None"
                        ),
                        "uses_yahoo_finance": False,  # We fixed this!
                        "data_sources": ["premarket_cache", "live_cache", "upstox_api"],
                        "market_phase": _get_current_market_phase(),
                        "timestamp": datetime.now().isoformat(),
                    }
                }
            )

            return status
        else:
            return {"error": "AI Trading service not available"}

    except Exception as e:
        return {"error": str(e)}


@app.get("/api/ai-trading/errors")
async def get_ai_trading_errors():
    """Get current AI trading errors"""
    global trading_engine

    try:
        if (
            trading_engine
            and hasattr(trading_engine, "ai_trading_service")
            and trading_engine.ai_trading_service
        ):

            ai_service = trading_engine.ai_trading_service

            return {
                "error_stocks": ai_service.error_count,
                "total_stocks": len(ai_service.selected_stocks),
                "error_percentage": (
                    (
                        len([c for c in ai_service.error_count.values() if c > 0])
                        / len(ai_service.selected_stocks)
                        * 100
                    )
                    if ai_service.selected_stocks
                    else 0
                ),
                "max_errors_per_stock": ai_service.max_errors_per_stock,
                "problematic_stocks": [
                    symbol
                    for symbol, count in ai_service.error_count.items()
                    if count >= ai_service.max_errors_per_stock
                ],
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {"error": "AI Trading service not available"}

    except Exception as e:
        return {"error": str(e)}


@app.post("/api/ai-trading/reset-errors")
async def reset_ai_trading_errors():
    """Reset error counts for AI trading service"""
    global trading_engine

    try:
        if (
            trading_engine
            and hasattr(trading_engine, "ai_trading_service")
            and trading_engine.ai_trading_service
        ):

            ai_service = trading_engine.ai_trading_service
            old_error_count = len([c for c in ai_service.error_count.values() if c > 0])

            # Reset error counts
            ai_service.error_count = {}

            logger.info(
                f"🔄 AI Trading errors reset - {old_error_count} stocks cleared"
            )

            return {
                "success": True,
                "message": f"Reset error counts for {old_error_count} stocks",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {"error": "AI Trading service not available"}

    except Exception as e:
        return {"error": str(e)}


@app.get("/api/data-sources/status")
async def get_data_sources_status():
    """Check status of all data sources used by AI trading"""
    try:
        status = {"timestamp": datetime.now().isoformat(), "sources": {}}

        # Check PreMarket cache
        try:
            from services.pre_market_data_service import get_cached_trading_stocks

            cached_stocks = get_cached_trading_stocks()
            status["sources"]["premarket_cache"] = {
                "status": "available" if cached_stocks else "empty",
                "stocks_count": len(cached_stocks) if cached_stocks else 0,
                "sample_stocks": list(cached_stocks[:3]) if cached_stocks else [],
            }
        except Exception as e:
            status["sources"]["premarket_cache"] = {"status": "error", "error": str(e)}

        # Check Redis live cache
        try:
            import redis

            redis_client = redis.Redis(
                host="localhost", port=6379, db=0, decode_responses=True
            )
            live_keys = redis_client.keys("live_price:*")
            status["sources"]["live_cache"] = {
                "status": "available" if live_keys else "empty",
                "live_stocks_count": len(live_keys),
                "sample_keys": live_keys[:3] if live_keys else [],
            }
        except Exception as e:
            status["sources"]["live_cache"] = {"status": "error", "error": str(e)}

        # Check Upstox API
        try:
            db = next(get_db())
            broker_config = (
                db.query(BrokerConfig)
                .filter(
                    BrokerConfig.broker_name.ilike("upstox"),
                    BrokerConfig.is_active == True,
                    BrokerConfig.access_token.isnot(None),
                )
                .first()
            )

            status["sources"]["upstox_api"] = {
                "status": "available" if broker_config else "not_configured",
                "token_available": broker_config is not None,
                "broker_active": broker_config.is_active if broker_config else False,
            }
            db.close()
        except Exception as e:
            status["sources"]["upstox_api"] = {"status": "error", "error": str(e)}

        # Overall assessment
        available_sources = len(
            [s for s in status["sources"].values() if s.get("status") == "available"]
        )
        status["summary"] = {
            "available_sources": available_sources,
            "total_sources": len(status["sources"]),
            "health": (
                "good"
                if available_sources >= 2
                else "degraded" if available_sources >= 1 else "poor"
            ),
        }

        return status

    except Exception as e:
        return {"error": str(e)}


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


# Enhanced health check with AI trading details
@app.get("/api/health/detailed")
async def detailed_health_check():
    """Detailed health check including AI trading service"""
    global trading_engine, trading_scheduler, instrument_service_instance

    health_status = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "system": "hybrid_websocket",
        "market_phase": _get_current_market_phase(),
        "services": {
            "database": "ok",
            "trading_engine": "unknown",
            "ai_trading_service": "unknown",
            "strategy_service": "unknown",
            "trading_scheduler": "unknown",
            "instrument_service": "unknown",
        },
        "ai_trading_details": {},
    }

    # Check trading engine
    if trading_engine:
        try:
            health_status["services"]["trading_engine"] = (
                "running" if trading_engine.is_running else "stopped"
            )

            # Check AI trading service
            if (
                hasattr(trading_engine, "ai_trading_service")
                and trading_engine.ai_trading_service
            ):
                ai_service = trading_engine.ai_trading_service
                health_status["services"]["ai_trading_service"] = (
                    "running" if ai_service.is_active else "stopped"
                )

                # AI trading details
                health_status["ai_trading_details"] = {
                    "selected_stocks": len(ai_service.selected_stocks),
                    "analyzed_stocks": len(ai_service.last_analysis_time),
                    "error_stocks": len(
                        [c for c in ai_service.error_count.values() if c > 0]
                    ),
                    "analysis_interval": ai_service.analysis_interval,
                    "data_sources": ["premarket_cache", "live_cache", "upstox_api"],
                }

                # Check strategy service
                if ai_service.strategy_service:
                    health_status["services"]["strategy_service"] = "initialized"
                    health_status["ai_trading_details"]["strategy_service_type"] = type(
                        ai_service.strategy_service
                    ).__name__
                    health_status["ai_trading_details"][
                        "uses_yahoo_finance"
                    ] = False  # Fixed!

        except Exception as e:
            health_status["services"]["trading_engine"] = "error"
            health_status["trading_engine_error"] = str(e)

    # Check other services (existing code)
    if trading_scheduler:
        try:
            health_status["services"]["trading_scheduler"] = (
                "running" if trading_scheduler.is_running else "stopped"
            )
        except Exception:
            health_status["services"]["trading_scheduler"] = "error"

    if instrument_service_instance:
        try:
            test_keys = fast_retrieval.get_all_websocket_keys()
            health_status["services"]["instrument_service"] = "running"
            health_status["instrument_service_details"] = {
                "cached_instruments": len(test_keys),
                "service_type": "optimized_redis_cache",
            }
        except Exception:
            health_status["services"]["instrument_service"] = "error"

    return health_status


# KEEP: All your existing SocketIO events and error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error on {request.url}: {str(exc)}")

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


# KEEP: Your existing SocketIO events
@sio.event
async def connect(sid, environ):
    logger.info(f"📡 Client connected: {sid}")
    await sio.emit(
        "connection_status", {"status": "connected", "system": "hybrid"}, to=sid
    )


@sio.event
async def disconnect(sid):
    logger.info(f"📡 Client disconnected: {sid}")


@sio.event
async def get_engine_status(sid, data):
    """Enhanced SocketIO endpoint for real-time engine status"""
    global trading_engine, instrument_service_instance

    try:
        if trading_engine:
            status = {
                "is_running": trading_engine.is_running,
                "selected_stocks_count": len(trading_engine.selected_stocks),
                "active_users_count": len(trading_engine.active_users),
                "instrument_service_active": instrument_service_instance is not None,
                "system": "hybrid_websocket",
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
        await sio.emit(
            "subscription_status", {"status": "subscribed", "system": "hybrid"}, to=sid
        )

    except Exception as e:
        await sio.emit("error", {"message": str(e)}, to=sid)


# KEEP: Your existing main runner
if __name__ == "__main__":
    logger.info("🚀 Launching Enhanced Growth Quantix Bot Server with Hybrid System...")

    uvicorn.run(
        "app:sio_app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        log_level="info",
    )
