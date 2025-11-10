"""
Enhanced Market WebSocket Router with Centralized WebSocket Manager

This module provides WebSocket endpoints for real-time market data
using the centralized WebSocket manager.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Set

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    HTTPException,
    Query,
)
from fastapi.websockets import WebSocketState
from fastapi.responses import JSONResponse

# JWT authentication
from jwt.exceptions import ExpiredSignatureError, DecodeError
from services.auth_service import get_current_user

# Database
from database.connection import get_db
from database.models import BrokerConfig, User

# Import the centralized WebSocket manager
from services.centralized_ws_manager import centralized_manager

# Import instrument service for symbol resolution
try:
    from services.optimized_instrument_service import (
        get_instrument_service,
        get_stock_instruments,
        get_dashboard_realtime_keys,
        get_stock_trading_data_keys,
    )
except ImportError:
    # Fallback functions if service not available
    def get_instrument_service():
        return None

    def get_stock_instruments(symbol: str):
        return None

    def get_dashboard_realtime_keys():
        return {"instrument_keys": []}

    def get_stock_trading_data_keys(symbol: str):
        return {"instrument_keys": []}


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Track active connections for monitoring
active_connections: Dict[str, Dict[str, Any]] = {}


# Helper functions
def generate_client_id(user_id: int, connection_type: str) -> str:
    """Generate a unique client ID for WebSocket connections"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_id = str(uuid.uuid4())[:8]
    return f"{connection_type}_{user_id}_{timestamp}_{random_id}"


async def resolve_instrument_keys(symbols: List[str]) -> List[str]:
    """Resolve instrument keys from symbol names"""
    instrument_keys = []
    instrument_service = get_instrument_service()

    if not instrument_service:
        return []

    for symbol in symbols:
        stock_info = get_stock_instruments(symbol)
        if stock_info and "primary_instrument_key" in stock_info:
            instrument_keys.append(stock_info["primary_instrument_key"])

    return instrument_keys


async def get_default_instrument_keys() -> List[str]:
    """Get default instrument keys for dashboard"""
    try:
        dashboard_keys = get_dashboard_realtime_keys()
        if dashboard_keys and "instrument_keys" in dashboard_keys:
            return dashboard_keys["instrument_keys"]
    except Exception as e:
        logger.error(f"Error getting default keys: {e}")

    # Fallback minimal set
    return [
        "NSE_INDEX|Nifty 50",
        "NSE_INDEX|Nifty Bank",
        "NSE_EQ|INE002A01018",  # RELIANCE
    ]


# WebSocket routes
@router.websocket("/api/v1/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """
    Real-time dashboard WebSocket endpoint

    This WebSocket provides a continuous stream of market data for the dashboard.
    Data comes from the centralized WebSocket manager, which maintains a single
    connection to Upstox.
    """
    # Extract token from query params
    token = websocket.query_params.get("token")
    if not token:
        await websocket.accept()
        await websocket.send_json({"type": "error", "reason": "missing_token"})
        await websocket.close()
        return

    client_id = None
    user = None

    try:
        # Accept the connection first
        await websocket.accept()

        # Authenticate user
        db = next(get_db())
        try:
            user = get_current_user(token=token, db=db)
        except (ExpiredSignatureError, DecodeError):
            await websocket.send_json({"type": "error", "reason": "token_expired"})
            await websocket.close()
            return

        # Generate client ID
        client_id = generate_client_id(user.id, "dashboard")

        # Log connection
        logger.info(f"📊 Dashboard WebSocket connected: {client_id}")

        # Store connection info
        active_connections[client_id] = {
            "user_id": user.id,
            "connection_type": "dashboard",
            "connected_at": datetime.now().isoformat(),
        }

        # Add client to centralized manager
        await centralized_manager.add_client(
            client_id=client_id, websocket=websocket, client_type="dashboard"
        )

        # Wait for WebSocket to disconnect
        try:
            while websocket.client_state == WebSocketState.CONNECTED:
                # Handle client messages
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                    if data:
                        try:
                            message = json.loads(data)
                            await handle_dashboard_message(client_id, message)
                        except json.JSONDecodeError:
                            pass
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_json(
                            {"type": "ping", "timestamp": datetime.now().isoformat()}
                        )
        except WebSocketDisconnect:
            pass

    except Exception as e:
        logger.error(f"❌ Error in dashboard WebSocket: {e}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(
                {"type": "error", "message": "Internal server error"}
            )

    finally:
        # Clean up
        if client_id and client_id in active_connections:
            del active_connections[client_id]

        # Remove from centralized manager
        if client_id:
            await centralized_manager.remove_client(client_id)

        logger.info(f"Dashboard WebSocket disconnected: {client_id}")


@router.websocket("/api/v1/ws/trading")
async def trading_websocket(
    websocket: WebSocket,
    symbols: Optional[str] = Query(None),
):
    """
    Real-time trading WebSocket endpoint

    This WebSocket provides a filtered stream of market data for specific instruments.
    Data comes from the centralized WebSocket manager, filtered to the requested symbols.
    """
    # Extract token from query params
    token = websocket.query_params.get("token")
    if not token:
        await websocket.accept()
        await websocket.send_json({"type": "error", "reason": "missing_token"})
        await websocket.close()
        return

    client_id = None
    user = None

    try:
        # Accept the connection first
        await websocket.accept()

        # Authenticate user
        db = next(get_db())
        try:
            user = get_current_user(token=token, db=db)
        except (ExpiredSignatureError, DecodeError):
            await websocket.send_json({"type": "error", "reason": "token_expired"})
            await websocket.close()
            return

        # Generate client ID
        client_id = generate_client_id(user.id, "trading")

        # Parse symbols if provided
        symbol_list = []
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]

        # Get instrument keys for the symbols
        instrument_keys = []
        if symbol_list:
            # For each symbol, get all related instrument keys (spot, futures, options)
            for symbol in symbol_list:
                trading_keys = get_stock_trading_data_keys(symbol)
                if trading_keys and "instrument_keys" in trading_keys:
                    instrument_keys.extend(trading_keys["instrument_keys"])

        # If no valid instruments found, use default dashboard instruments
        if not instrument_keys:
            instrument_keys = await get_default_instrument_keys()

        # Log connection
        logger.info(
            f"🎯 Trading WebSocket connected: {client_id} for {len(instrument_keys)} instruments"
        )

        # Store connection info
        active_connections[client_id] = {
            "user_id": user.id,
            "connection_type": "trading",
            "symbols": symbol_list,
            "instrument_count": len(instrument_keys),
            "connected_at": datetime.now().isoformat(),
        }

        # Add client to centralized manager with subscriptions
        await centralized_manager.add_client(
            client_id=client_id,
            websocket=websocket,
            client_type="trading",
            instrument_keys=instrument_keys,
        )

        # Wait for WebSocket to disconnect
        try:
            while websocket.client_state == WebSocketState.CONNECTED:
                # Handle client messages
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                    if data:
                        try:
                            message = json.loads(data)
                            await handle_trading_message(client_id, message)
                        except json.JSONDecodeError:
                            pass
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_json(
                            {"type": "ping", "timestamp": datetime.now().isoformat()}
                        )
        except WebSocketDisconnect:
            pass

    except Exception as e:
        logger.error(f"❌ Error in trading WebSocket: {e}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(
                {"type": "error", "message": "Internal server error"}
            )

    finally:
        # Clean up
        if client_id and client_id in active_connections:
            del active_connections[client_id]

        # Remove from centralized manager
        if client_id:
            await centralized_manager.remove_client(client_id)

        logger.info(f"Trading WebSocket disconnected: {client_id}")


# Legacy WebSocket for backward compatibility - DEPRECATED
@router.websocket("/ws/market")
async def legacy_market_websocket(websocket: WebSocket):
    """
    Legacy WebSocket endpoint for backward compatibility

    DEPRECATED: This endpoint is maintained for backward compatibility only.
    New clients should use /ws/unified instead.

    Note: This endpoint does NOT use centralized_manager to avoid method conflicts.
    It simply redirects clients to use the unified endpoint.
    """
    token = websocket.query_params.get("token")

    try:
        await websocket.accept()

        # Send deprecation warning and redirect message
        await websocket.send_json({
            "type": "deprecated_endpoint",
            "message": "This endpoint is deprecated. Please use /ws/unified for real-time data.",
            "redirect_to": "/ws/unified",
            "timestamp": datetime.now().isoformat()
        })

        logger.warning("⚠️ Legacy WebSocket endpoint /ws/market accessed - client should migrate to /ws/unified")

        # Close connection gracefully
        await websocket.close(code=1000, reason="Endpoint deprecated, use /ws/unified")

    except Exception as e:
        logger.error(f"❌ Error in legacy WebSocket: {e}")
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.close(code=1011, reason="Internal server error")
            except:
                pass


# Message handlers
async def handle_dashboard_message(client_id: str, message: Dict[str, Any]):
    """Handle messages from dashboard WebSocket clients"""
    message_type = message.get("type")

    if message_type == "ping":
        # Handle ping message (for keepalive)
        return

    elif message_type == "get_status":
        # Handle status request
        status = centralized_manager.get_status()

        # Format for client response
        client_status = {
            "type": "status_response",
            "data": {
                "connected": status["ws_connected"],
                "market_status": status["market_status"],
                "cached_instruments": status["data_stats"]["cached_instruments"],
                "connection_uptime": (
                    (
                        datetime.now()
                        - datetime.fromisoformat(status["last_data_received"])
                    ).total_seconds()
                    if status["last_data_received"]
                    else 0
                ),
                "timestamp": datetime.now().isoformat(),
            },
        }

        # Send directly to requesting client
        if client_id in active_connections:
            # This would be a direct WebSocket send, but we don't have the WebSocket object here
            # Instead, we use a callback mechanism or an alternative approach
            pass


async def handle_trading_message(client_id: str, message: Dict[str, Any]):
    """Handle messages from trading WebSocket clients"""
    message_type = message.get("type")

    if message_type == "ping":
        # Handle ping message (for keepalive)
        return

    elif message_type == "subscribe":
        # Handle subscription update
        symbols = message.get("symbols", [])
        if not symbols:
            return

        # Resolve instrument keys
        instrument_keys = []
        for symbol in symbols:
            trading_keys = get_stock_trading_data_keys(symbol)
            if trading_keys and "instrument_keys" in trading_keys:
                instrument_keys.extend(trading_keys["instrument_keys"])

        # Update subscriptions
        if instrument_keys:
            await centralized_manager.update_client_subscriptions(
                client_id, instrument_keys
            )

            # Update active connections record
            if client_id in active_connections:
                active_connections[client_id]["symbols"] = symbols
                active_connections[client_id]["instrument_count"] = len(instrument_keys)


# REST API endpoints for WebSocket management


@router.get("/api/v1/ws/status")
async def get_websocket_status():
    """Get WebSocket service status"""
    try:
        # Get status from centralized manager
        status = await centralized_manager.health_check()

        # Add active connection info
        connection_stats = {
            "dashboard_connections": len(
                [
                    c
                    for c in active_connections.values()
                    if c.get("connection_type") == "dashboard"
                ]
            ),
            "trading_connections": len(
                [
                    c
                    for c in active_connections.values()
                    if c.get("connection_type") == "trading"
                ]
            ),
            "legacy_connections": len(
                [
                    c
                    for c in active_connections.values()
                    if c.get("connection_type") == "legacy"
                ]
            ),
            "total_connections": len(active_connections),
            "active_users": len(
                set(c.get("user_id") for c in active_connections.values())
            ),
        }

        return {
            "centralized_websocket": {
                "status": status["status"],
                "health_score": status["health_score"],
                "is_running": status["is_running"],
                "ws_connected": status["ws_connected"],
                "market_status": status["market_status"],
                "last_data_received": status["last_data_received"],
                "issues": status["issues"] if "issues" in status else [],
            },
            "connections": connection_stats,
            "performance": status.get("performance_metrics", {}),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting WebSocket status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get WebSocket status")


@router.post("/api/v1/ws/start")
async def start_websocket_service():
    """Start the centralized WebSocket service"""
    try:
        # Check if already running
        status = centralized_manager.get_status()
        if status["is_running"] and status["ws_connected"]:
            return {
                "message": "WebSocket service is already running",
                "status": "already_running",
            }

        # Start the service
        result = await centralized_manager.start_connection()

        if result:
            return {
                "message": "WebSocket service started successfully",
                "status": "starting",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "message": "Failed to start WebSocket service",
                "status": "error",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"Error starting WebSocket service: {e}")
        raise HTTPException(status_code=500, detail="Failed to start WebSocket service")


@router.post("/api/v1/ws/stop")
async def stop_websocket_service():
    """Stop the centralized WebSocket service"""
    try:
        # Stop the service
        result = await centralized_manager.stop()

        if result:
            return {
                "message": "WebSocket service stopped successfully",
                "status": "stopped",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "message": "Failed to stop WebSocket service",
                "status": "error",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"Error stopping WebSocket service: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop WebSocket service")


@router.get("/api/v1/market-data/latest/{symbol}")
async def get_latest_price(symbol: str):
    """Get latest price data for a symbol"""
    try:
        # Resolve symbol to instrument key
        instrument_service = get_instrument_service()
        if not instrument_service:
            raise HTTPException(
                status_code=500, detail="Instrument service not available"
            )

        stock_info = get_stock_instruments(symbol)
        if not stock_info or "primary_instrument_key" not in stock_info:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

        instrument_key = stock_info["primary_instrument_key"]

        # Get latest price data
        price_data = centralized_manager.get_latest_data(instrument_key)

        if not price_data:
            return {
                "symbol": symbol,
                "instrument_key": instrument_key,
                "message": "No price data available",
                "market_status": centralized_manager.get_market_status(),
                "timestamp": datetime.now().isoformat(),
            }

        # Format response
        return {
            "symbol": symbol,
            "instrument_key": instrument_key,
            "price_data": price_data,
            "market_status": centralized_manager.get_market_status(),
            "last_updated": centralized_manager.get_last_update_time(instrument_key),
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest price: {e}")
        raise HTTPException(status_code=500, detail="Failed to get latest price data")


@router.get("/api/v1/market-data/top-movers")
async def get_top_movers(
    limit: int = Query(5, ge=1, le=20), type: str = Query("gainers")
):
    """Get top gainers or losers"""
    try:
        # Validate type parameter
        if type not in ["gainers", "losers"]:
            raise HTTPException(
                status_code=400, detail="Type must be 'gainers' or 'losers'"
            )

        # Get top movers
        movers = centralized_manager.get_top_performers(limit=limit, sort=type)

        return {
            "type": type,
            "count": len(movers),
            "market_status": centralized_manager.get_market_status(),
            "movers": movers,
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting top movers: {e}")
        raise HTTPException(status_code=500, detail="Failed to get top movers")


@router.post("/api/v1/ws/test-broadcast")
async def test_broadcast():
    """Force a test broadcast for debugging"""
    try:
        # Create test data
        test_data = {
            "NSE_INDEX|Nifty 50": {
                "ltp": 22500.0,
                "ltq": 100,
                "cp": 22400.0,
                "timestamp": datetime.now().isoformat(),
                "test": True,
            },
            "NSE_EQ|INE002A01018": {  # RELIANCE
                "ltp": 2700.0,
                "ltq": 100,
                "cp": 2650.0,
                "timestamp": datetime.now().isoformat(),
                "test": True,
            },
        }

        # Broadcast test data
        result = await centralized_manager.force_test_broadcast(test_data)

        return {
            "message": "Test broadcast sent successfully",
            "status": "success" if result else "error",
            "data_items": len(test_data),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error sending test broadcast: {e}")
        raise HTTPException(status_code=500, detail="Failed to send test broadcast")


# Initialization function
async def initialize_websocket_system():
    """Initialize the WebSocket system at application startup"""
    try:
        # Initialize the centralized manager
        initialized = await centralized_manager.initialize()

        if initialized:
            # Start the connection
            await centralized_manager.start_connection()
            logger.info("✅ WebSocket system initialized and started")
        else:
            logger.error("❌ Failed to initialize WebSocket system")

        return initialized
    except Exception as e:
        logger.error(f"❌ Error initializing WebSocket system: {e}")
        return False
