# routes/market_ws.py (FIXED VERSION)
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from tempfile import gettempdir
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from jwt.exceptions import ExpiredSignatureError, DecodeError
from services.auth_service import get_current_user
from services.centralized_ws_manager import centralized_manager
from services.pre_market_data_service import get_cached_trading_stocks
from database.connection import get_db
from database.models import BrokerConfig

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
router = APIRouter()

# Store individual client connections for cleanup
active_connections = {}


@router.websocket("/ws/dashboard")
async def dashboard_data_websocket(websocket: WebSocket):
    """
    Dashboard endpoint using centralized WebSocket manager
    Shows all market data from the single admin connection
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.accept()
        await websocket.send_json({"type": "error", "reason": "missing_token"})
        await websocket.close()
        return

    logger.info(f"📊 Dashboard WebSocket request: {token}")

    try:
        # Validate user token
        db = next(get_db())
        try:
            user = get_current_user(token=token, db=db)
        except ExpiredSignatureError:
            await websocket.accept()
            await websocket.send_json({"type": "error", "reason": "token_expired"})
            await websocket.close()
            return
        except DecodeError:
            await websocket.accept()
            await websocket.send_json({"type": "error", "reason": "token_invalid"})
            await websocket.close()
            return

        await websocket.accept()

        # Ensure centralized manager is running
        if not centralized_manager.is_running:
            await centralized_manager.start_connection()

        # Add client to centralized manager
        await centralized_manager.add_dashboard_client(token, websocket)
        active_connections[token] = {
            "type": "dashboard",
            "websocket": websocket,
            "user_id": user.id,
            "connected_at": datetime.now(),
        }

        logger.info(f"✅ Dashboard WebSocket connected: {token} (User: {user.id})")

        # Send initial connection status
        await safe_send_json(
            websocket,
            {
                "type": "connection_status",
                "status": "connected",
                "message": "Connected to centralized market data",
                "data_source": "CENTRALIZED_WS",
                "timestamp": datetime.now().isoformat(),
                "manager_status": centralized_manager.get_status(),
            },
        )

        # Keep connection alive
        while token in active_connections and is_websocket_connected(websocket):
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30)

                # Handle client messages (ping/pong, status requests, etc.)
                if message:
                    try:
                        data = (
                            json.loads(message) if isinstance(message, str) else message
                        )
                        await handle_client_message(token, data, websocket)
                    except json.JSONDecodeError:
                        # Ignore malformed messages
                        pass

            except (WebSocketDisconnect, asyncio.TimeoutError):
                logger.info(f"❎ Dashboard WebSocket disconnect: {token}")
                break
            except RuntimeError as e:
                if "WebSocket is not connected" in str(e):
                    logger.info(f"📱 Dashboard WebSocket disconnected: {token}")
                    break
                logger.warning(f"⚠️ Dashboard WebSocket RuntimeError: {e}")
                break
            except Exception as e:
                logger.error(f"❌ Dashboard WebSocket unexpected error: {e}")
                break

    except Exception as e:
        logger.error(f"❌ Dashboard WebSocket error for {token}: {e}")
    finally:
        await cleanup_connection(token)


@router.websocket("/ws/trading")
async def trading_data_websocket(websocket: WebSocket):
    """
    Trading endpoint using centralized WebSocket manager
    Provides filtered data based on user's selected instruments
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.accept()
        await websocket.send_json({"type": "error", "reason": "missing_token"})
        await websocket.close()
        return

    logger.info(f"🎯 Trading WebSocket request: {token}")

    try:
        # Validate user token
        db = next(get_db())
        try:
            user = get_current_user(token=token, db=db)
        except ExpiredSignatureError:
            await websocket.accept()
            await websocket.send_json({"type": "error", "reason": "token_expired"})
            await websocket.close()
            return
        except DecodeError:
            await websocket.accept()
            await websocket.send_json({"type": "error", "reason": "token_invalid"})
            await websocket.close()
            return

        # Get user's trading instruments
        trading_instruments = await get_selected_trading_instruments(user.id)
        if not trading_instruments:
            await websocket.accept()
            await websocket.send_json(
                {"type": "error", "reason": "no_trading_instruments"}
            )
            await websocket.close()
            return

        await websocket.accept()

        # Ensure centralized manager is running
        if not centralized_manager.is_running:
            await centralized_manager.start_connection()

        # Add client to centralized manager with instrument filter
        await centralized_manager.add_trading_client(
            token, websocket, trading_instruments
        )
        active_connections[token] = {
            "type": "trading",
            "websocket": websocket,
            "user_id": user.id,
            "connected_at": datetime.now(),
            "instruments_count": len(trading_instruments),
        }

        logger.info(
            f"✅ Trading WebSocket connected: {token} (User: {user.id}, Instruments: {len(trading_instruments)})"
        )

        # Send initial connection status
        await safe_send_json(
            websocket,
            {
                "type": "connection_status",
                "status": "connected",
                "message": f"Connected to centralized trading data with {len(trading_instruments)} instruments",
                "data_source": "CENTRALIZED_WS_FILTERED",
                "instruments_count": len(trading_instruments),
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Keep connection alive
        while token in active_connections and is_websocket_connected(websocket):
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30)

                # Handle client messages
                if message:
                    try:
                        data = (
                            json.loads(message) if isinstance(message, str) else message
                        )
                        await handle_client_message(token, data, websocket)
                    except json.JSONDecodeError:
                        pass

            except (WebSocketDisconnect, asyncio.TimeoutError):
                logger.info(f"❎ Trading WebSocket disconnect: {token}")
                break
            except RuntimeError as e:
                if "WebSocket is not connected" in str(e):
                    logger.info(f"📱 Trading WebSocket disconnected: {token}")
                    break
                logger.warning(f"⚠️ Trading WebSocket RuntimeError: {e}")
                break
            except Exception as e:
                logger.error(f"❌ Trading WebSocket unexpected error: {e}")
                break

    except Exception as e:
        logger.error(f"❌ Trading WebSocket error for {token}: {e}")
    finally:
        await cleanup_connection(token)


@router.websocket("/ws/market")
async def legacy_market_data_websocket(websocket: WebSocket):
    """
    LEGACY: Backward compatibility endpoint
    Uses centralized manager but maintains old API format
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.accept()
        await websocket.send_json({"type": "error", "reason": "missing_token"})
        await websocket.close()
        return

    logger.info(f"🔄 Legacy WebSocket request: {token}")

    try:
        # Validate user token
        db = next(get_db())
        try:
            user = get_current_user(token=token, db=db)
        except ExpiredSignatureError:
            await websocket.accept()
            await websocket.send_json({"type": "error", "reason": "token_expired"})
            await websocket.close()
            return
        except DecodeError:
            await websocket.accept()
            await websocket.send_json({"type": "error", "reason": "token_invalid"})
            await websocket.close()
            return

        await websocket.accept()

        # Ensure centralized manager is running
        if not centralized_manager.is_running:
            await centralized_manager.start_connection()

        # Add client to centralized manager as legacy client
        await centralized_manager.add_legacy_client(token, websocket)
        active_connections[token] = {
            "type": "legacy",
            "websocket": websocket,
            "user_id": user.id,
            "connected_at": datetime.now(),
        }

        logger.info(f"✅ Legacy WebSocket connected: {token} (User: {user.id})")

        # Keep connection alive
        while token in active_connections and is_websocket_connected(websocket):
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30)

                if message:
                    try:
                        data = (
                            json.loads(message) if isinstance(message, str) else message
                        )
                        await handle_client_message(token, data, websocket)
                    except json.JSONDecodeError:
                        pass

            except (WebSocketDisconnect, asyncio.TimeoutError):
                logger.info(f"❎ Legacy WebSocket disconnect: {token}")
                break
            except RuntimeError as e:
                if "WebSocket is not connected" in str(e):
                    logger.info(f"📱 Legacy WebSocket disconnected: {token}")
                    break
                logger.warning(f"⚠️ Legacy WebSocket RuntimeError: {e}")
                break
            except Exception as e:
                logger.error(f"❌ Legacy WebSocket unexpected error: {e}")
                break

    except Exception as e:
        logger.error(f"❌ Legacy WebSocket error for {token}: {e}")
    finally:
        await cleanup_connection(token)


def is_websocket_connected(websocket: WebSocket) -> bool:
    """Check if WebSocket is still connected"""
    try:
        return websocket.client_state == WebSocketState.CONNECTED
    except:
        return False


async def safe_send_json(websocket: WebSocket, data: dict) -> bool:
    """Safely send JSON data to WebSocket"""
    try:
        if is_websocket_connected(websocket):
            await websocket.send_json(data)
            return True
    except Exception as e:
        logger.warning(f"⚠️ Failed to send WebSocket message: {e}")
    return False


async def handle_client_message(token: str, data: dict, websocket: WebSocket):
    """Handle messages from WebSocket clients - FIXED VERSION"""
    try:
        message_type = data.get("type")

        if message_type == "ping":
            # Respond with pong and status
            await safe_send_json(
                websocket,
                {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat(),
                    "manager_status": centralized_manager.get_status(),
                },
            )

        elif message_type == "get_status":
            # Send detailed status
            await safe_send_json(
                websocket,
                {
                    "type": "status_response",
                    "data": centralized_manager.get_status(),
                    "timestamp": datetime.now().isoformat(),
                },
            )

        elif message_type == "get_health":
            # Send health check
            health_data = await centralized_manager.health_check()
            await safe_send_json(
                websocket,
                {
                    "type": "health_response",
                    "data": health_data,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        elif message_type == "update_instruments" and data.get("instruments"):
            # Update trading instruments for this client
            new_instruments = data.get("instruments", [])
            if token in centralized_manager.trading_clients:
                centralized_manager.user_subscriptions[token] = set(new_instruments)
                logger.info(
                    f"🔄 Updated instruments for {token}: {len(new_instruments)} instruments"
                )

                # Confirm update
                await safe_send_json(
                    websocket,
                    {
                        "type": "instruments_updated",
                        "count": len(new_instruments),
                        "timestamp": datetime.now().isoformat(),
                    },
                )

    except Exception as e:
        logger.error(f"❌ Error handling client message from {token}: {e}")


async def get_selected_trading_instruments(user_id: int) -> list[str]:
    """
    Get instrument keys for selected trading stocks.
    Enhanced version that integrates with your existing services.
    """
    try:
        # Use your existing cached trading stocks
        selected_stocks = get_cached_trading_stocks()
        if not selected_stocks:
            logger.warning("No cached trading stocks available")
            return []

        all_instruments = []

        # Import your existing fast_retrieval service
        try:
            from services import fast_retrieval  # Adjust import path as needed
        except ImportError:
            logger.error("❌ fast_retrieval service not found")
            # Fallback: return basic instrument keys if fast_retrieval is not available
            return await get_fallback_trading_instruments()

        # Process selected stocks (limit to prevent overload)
        for stock_data in selected_stocks[
            :15
        ]:  # Limit to 15 stocks for focused trading
            symbol = stock_data.get("symbol")
            if not symbol:
                continue

            try:
                # Get instruments using your existing service
                stock_mapping = fast_retrieval.get_stock_instruments(symbol)
                if not stock_mapping:
                    continue

                # Add spot instrument
                primary_key = stock_mapping.get("primary_instrument_key")
                if primary_key:
                    all_instruments.append(primary_key)

                # Add futures and options from your existing mapping
                instruments = stock_mapping.get("instruments", {})

                # Add 2 futures (current month and next month)
                futures = instruments.get("FUT", [])[:2]
                for future in futures:
                    instrument_key = future.get("instrument_key")
                    if instrument_key:
                        all_instruments.append(instrument_key)

                # Add ATM ± 10 strike options (focused range for trading)
                current_price = stock_data.get("entry_price", 0) or stock_data.get(
                    "ltp", 0
                )
                if current_price > 0:
                    # Calculate ATM strike
                    if current_price < 100:
                        strike_interval = 5
                    elif current_price < 500:
                        strike_interval = 10
                    elif current_price < 1000:
                        strike_interval = 25
                    else:
                        strike_interval = 50

                    atm_strike = (
                        round(current_price / strike_interval) * strike_interval
                    )
                    min_strike = atm_strike - (5 * strike_interval)  # 5 strikes below
                    max_strike = atm_strike + (5 * strike_interval)  # 5 strikes above

                    # Add CE options (calls)
                    for option in instruments.get("CE", []):
                        strike = option.get("strike_price", 0)
                        if min_strike <= strike <= max_strike:
                            instrument_key = option.get("instrument_key")
                            if instrument_key:
                                all_instruments.append(instrument_key)

                    # Add PE options (puts)
                    for option in instruments.get("PE", []):
                        strike = option.get("strike_price", 0)
                        if min_strike <= strike <= max_strike:
                            instrument_key = option.get("instrument_key")
                            if instrument_key:
                                all_instruments.append(instrument_key)

            except Exception as e:
                logger.warning(f"⚠️ Error processing instruments for {symbol}: {e}")
                continue

        # Remove duplicates and filter valid instruments
        unique_instruments = list(set(filter(None, all_instruments)))

        # Limit to reasonable number for focused trading
        if len(unique_instruments) > 500:
            unique_instruments = unique_instruments[:500]
            logger.info(
                f"⚠️ Limited trading instruments to 500 (from {len(unique_instruments)})"
            )

        logger.info(
            f"🎯 Generated {len(unique_instruments)} trading instruments for user {user_id} from {len(selected_stocks)} stocks"
        )
        return unique_instruments

    except Exception as e:
        logger.error(f"❌ Error getting trading instruments for user {user_id}: {e}")
        return await get_fallback_trading_instruments()


async def get_fallback_trading_instruments() -> list[str]:
    """
    Fallback method to get trading instruments when fast_retrieval is not available
    """
    try:
        # Load from the same instrument keys file used by centralized manager
        file_path = Path(gettempdir()) / "today_instrument_keys.json"

        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                if isinstance(content, list):
                    # Return first 100 instruments as fallback
                    return content[:100]
                elif isinstance(content, dict):
                    if content.get("timestamp") == datetime.now().strftime("%Y-%m-%d"):
                        return content.get("keys", [])[:100]

        # If no file, return some common NSE instruments as absolute fallback
        logger.warning("⚠️ Using absolute fallback instruments")
        return [
            "NSE_EQ|INE002A01018",  # RELIANCE
            "NSE_EQ|INE467B01029",  # TCS
            "NSE_EQ|INE040A01034",  # HDFC
            "NSE_EQ|INE030A01027",  # ICICIBANK
            "NSE_EQ|INE009A01021",  # INFY
        ]

    except Exception as e:
        logger.error(f"❌ Error in fallback trading instruments: {e}")
        return []


async def cleanup_connection(token: str):
    """Cleanup individual WebSocket connection - IMPROVED VERSION"""
    logger.info(f"🧹 Cleaning up connection: {token}")

    # Remove from active connections
    connection = active_connections.pop(token, None)
    if connection:
        try:
            ws = connection["websocket"]
            if is_websocket_connected(ws):
                await ws.close()
        except Exception as e:
            logger.warning(f"⚠️ Error closing WebSocket for {token}: {e}")

    # Remove from centralized manager
    try:
        await centralized_manager.remove_client(token)
    except Exception as e:
        logger.warning(f"⚠️ Error removing client from centralized manager: {e}")


# Admin endpoints for monitoring and control
@router.get("/admin/ws-status")
async def get_websocket_status():
    """ADMIN: Get current WebSocket status"""
    try:
        return {
            "centralized_manager": await centralized_manager.health_check(),
            "active_connections": {
                "count": len(active_connections),
                "types": {
                    connection_type: len(
                        [
                            conn
                            for conn in active_connections.values()
                            if conn["type"] == connection_type
                        ]
                    )
                    for connection_type in ["dashboard", "trading", "legacy"]
                },
                "details": [
                    {
                        "token_preview": token[:8] + "...",
                        "type": conn["type"],
                        "user_id": conn.get("user_id"),
                        "connected_at": conn.get(
                            "connected_at", datetime.now()
                        ).isoformat(),
                        "instruments_count": conn.get("instruments_count", 0),
                        "websocket_state": (
                            "connected"
                            if is_websocket_connected(conn["websocket"])
                            else "disconnected"
                        ),
                    }
                    for token, conn in active_connections.items()
                ],
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Error getting WebSocket status: {e}")
        return {"error": str(e), "timestamp": datetime.now().isoformat()}


@router.post("/admin/ws-restart")
async def restart_websocket_service():
    """ADMIN: Restart the centralized WebSocket service"""
    try:
        logger.info("🔄 Admin requested WebSocket service restart")

        # Stop current service
        await centralized_manager.stop()
        await asyncio.sleep(2)

        # Restart service
        if await centralized_manager.initialize():
            await centralized_manager.start_connection()

            # Wait for connection to establish
            for i in range(10):
                await asyncio.sleep(1)
                status = centralized_manager.get_status()
                if status.get("ws_connected", False):
                    break

            return {
                "status": "success",
                "message": "WebSocket service restarted successfully",
                "health": await centralized_manager.health_check(),
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "status": "error",
                "message": "Failed to restart WebSocket service - initialization failed",
                "timestamp": datetime.now().isoformat(),
            }

    except Exception as e:
        logger.error(f"❌ Error restarting WebSocket service: {e}")
        return {
            "status": "error",
            "message": f"Error restarting service: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@router.post("/admin/ws-refresh-admin-token")
async def refresh_admin_token():
    """ADMIN: Force refresh of admin token"""
    try:
        success = await centralized_manager._refresh_admin_token()
        return {
            "status": "success" if success else "error",
            "message": (
                "Admin token refreshed successfully"
                if success
                else "Failed to refresh admin token"
            ),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Error refreshing admin token: {e}")
        return {
            "status": "error",
            "message": f"Error refreshing token: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/admin/ws-clients")
async def get_active_clients():
    """ADMIN: Get detailed information about active WebSocket clients"""
    try:
        client_details = []

        for token, connection in active_connections.items():
            client_info = {
                "token_preview": token[:8] + "...",
                "connection_type": connection["type"],
                "websocket_state": (
                    "connected"
                    if is_websocket_connected(connection["websocket"])
                    else "disconnected"
                ),
                "user_id": connection.get("user_id"),
                "connected_at": connection.get(
                    "connected_at", datetime.now()
                ).isoformat(),
                "in_centralized_manager": {
                    "dashboard": token in centralized_manager.dashboard_clients,
                    "trading": token in centralized_manager.trading_clients,
                    "legacy": token in centralized_manager.legacy_clients,
                },
            }

            # Add subscription info for trading clients
            if token in centralized_manager.user_subscriptions:
                client_info["subscribed_instruments"] = len(
                    centralized_manager.user_subscriptions[token]
                )

            client_details.append(client_info)

        return {
            "total_clients": len(active_connections),
            "centralized_manager_clients": {
                "dashboard": len(centralized_manager.dashboard_clients),
                "trading": len(centralized_manager.trading_clients),
                "legacy": len(centralized_manager.legacy_clients),
            },
            "client_details": client_details,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Error getting client details: {e}")
        return {"error": str(e), "timestamp": datetime.now().isoformat()}


@router.post("/admin/ws-disconnect-client/{token_preview}")
async def disconnect_client(token_preview: str):
    """ADMIN: Forcefully disconnect a specific client"""
    try:
        # Find client by token preview
        target_token = None
        for token in active_connections.keys():
            if token.startswith(token_preview):
                target_token = token
                break

        if not target_token:
            return {
                "status": "error",
                "message": f"No client found with token preview: {token_preview}",
                "timestamp": datetime.now().isoformat(),
            }

        # Disconnect the client
        await cleanup_connection(target_token)

        return {
            "status": "success",
            "message": f"Client {token_preview}... disconnected successfully",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Error disconnecting client: {e}")
        return {
            "status": "error",
            "message": f"Error disconnecting client: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint for the WebSocket service"""
    try:
        health_data = await centralized_manager.health_check()

        return {
            "service": "market_websocket",
            "status": health_data.get("status", "unknown"),
            "health_score": health_data.get("health_score", 0),
            "details": health_data,
            "active_connections": len(active_connections),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "service": "market_websocket",
            "status": "error",
            "health_score": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# Utility endpoint to test WebSocket without frontend
@router.get("/test-ws-connection")
async def test_websocket_connection():
    """UTILITY: Test WebSocket connection without frontend"""
    try:
        manager_status = centralized_manager.get_status()
        health_data = await centralized_manager.health_check()

        return {
            "test_info": {
                "message": "Use this info to test WebSocket connections",
                "websocket_endpoints": {
                    "dashboard": "/ws/dashboard?token=YOUR_USER_TOKEN",
                    "trading": "/ws/trading?token=YOUR_USER_TOKEN",
                    "legacy": "/ws/market?token=YOUR_USER_TOKEN",
                },
                "example_javascript": """
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/dashboard?token=YOUR_TOKEN');
ws.onmessage = (event) => console.log('Received:', JSON.parse(event.data));
ws.onopen = () => ws.send(JSON.stringify({type: 'ping'}));
                """.strip(),
            },
            "current_status": {
                "manager": manager_status,
                "health": health_data,
                "active_clients": len(active_connections),
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {"error": str(e), "timestamp": datetime.now().isoformat()}
