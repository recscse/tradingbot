# In api/websocket_routes.py
from datetime import datetime
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
from typing import Any, Dict, Set, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Keep track of active connections
active_connections: Dict[str, WebSocket] = {}
client_subscriptions: Dict[str, Set[str]] = {}


@router.websocket("/ws/market-data")
async def websocket_market_data(websocket: WebSocket):
    """Improved WebSocket endpoint for market data streaming"""
    await websocket.accept()

    # Generate unique client ID
    client_id = f"client_{id(websocket)}"
    active_connections[client_id] = websocket
    client_subscriptions[client_id] = set()

    try:
        logger.info(f"🔌 WebSocket client connected: {client_id}")

        # Send welcome message
        await websocket.send_json(
            {
                "type": "connection_status",
                "status": "connected",
                "client_id": client_id,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Process messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle subscription request
            if message.get("type") == "subscribe":
                keys = message.get("keys", [])
                if keys:
                    # Register subscriptions
                    client_subscriptions[client_id] = set(keys)

                    # Confirm subscription
                    await websocket.send_json(
                        {
                            "type": "subscription_status",
                            "status": "subscribed",
                            "subscribed_keys": len(keys),
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

                    logger.info(
                        f"📊 Client {client_id} subscribed to {len(keys)} instruments"
                    )

                    # Send initial data if available
                    try:
                        from services.instrument_registry import instrument_registry

                        # Get registry stats for debugging
                        registry_stats = instrument_registry.get_stats()
                        logger.info(
                            f"📊 Registry status: {registry_stats['live_prices']} live prices available"
                        )

                        # Prepare initial data
                        initial_data = {}

                        # Try to get data for each key
                        for key in keys:
                            # Extract symbol from instrument key for better lookup
                            try:
                                key_parts = key.split("|")
                                if len(key_parts) == 2:
                                    exchange_segment = key_parts[0]
                                    symbol_or_token = key_parts[1]

                                    # Different handling based on segment
                                    if "INDEX" in exchange_segment:
                                        # For indices
                                        symbol = symbol_or_token
                                        price_data = instrument_registry.get_spot_price(
                                            symbol
                                        )
                                        if price_data:
                                            initial_data[key] = price_data
                                    elif "EQ" in exchange_segment:
                                        # For equities
                                        symbol = symbol_or_token
                                        # Try to get price data directly from registry
                                        if (
                                            hasattr(instrument_registry, "_live_prices")
                                            and key in instrument_registry._live_prices
                                        ):
                                            initial_data[key] = (
                                                instrument_registry._live_prices[key]
                                            )
                                        else:
                                            # Fall back to get_spot_price method
                                            price_data = (
                                                instrument_registry.get_spot_price(
                                                    symbol
                                                )
                                            )
                                            if price_data:
                                                initial_data[key] = price_data
                            except Exception as e:
                                logger.warning(
                                    f"⚠️ Error getting initial data for {key}: {e}"
                                )
                                continue

                        # Send initial data or empty response
                        await websocket.send_json(
                            {
                                "type": "market_data",
                                "data": initial_data,
                                "is_snapshot": True,
                                "keys_found": len(initial_data),
                                "keys_requested": len(keys),
                                "message": f"Found {len(initial_data)} of {len(keys)} requested instruments",
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

                        logger.info(
                            f"📊 Sent initial data with {len(initial_data)}/{len(keys)} instruments to {client_id}"
                        )

                    except ImportError as e:
                        logger.warning(f"⚠️ Could not import instrument_registry: {e}")
                        # Send empty initial data
                        await websocket.send_json(
                            {
                                "type": "market_data",
                                "data": {},
                                "is_snapshot": True,
                                "message": "Registry not available, will receive live data when available",
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                    except Exception as e:
                        logger.error(f"❌ Error getting initial data: {e}")
                        # Send empty initial data with error
                        await websocket.send_json(
                            {
                                "type": "market_data",
                                "data": {},
                                "is_snapshot": True,
                                "error": str(e),
                                "message": "Error getting initial data, will receive updates when available",
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

            # Handle unsubscribe request
            elif message.get("type") == "unsubscribe":
                client_subscriptions[client_id] = set()
                await websocket.send_json(
                    {
                        "type": "subscription_status",
                        "status": "unsubscribed",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                logger.info(f"📊 Client {client_id} unsubscribed from all instruments")

            # Handle debug request
            elif message.get("type") == "debug":
                try:
                    from services.instrument_registry import instrument_registry

                    registry_stats = instrument_registry.get_stats()
                    debug_prices = instrument_registry.debug_live_prices(10)

                    await websocket.send_json(
                        {
                            "type": "debug_info",
                            "registry_stats": registry_stats,
                            "live_prices_sample": debug_prices,
                            "subscriptions": list(client_subscriptions[client_id]),
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                except Exception as e:
                    await websocket.send_json(
                        {
                            "type": "debug_info",
                            "error": str(e),
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"❌ WebSocket error for {client_id}: {e}")
        import traceback

        logger.error(f"❌ Traceback: {traceback.format_exc()}")
    finally:
        # Clean up
        active_connections.pop(client_id, None)
        client_subscriptions.pop(client_id, None)


# Function to broadcast market data updates to subscribed clients
async def broadcast_market_data(data: Dict[str, Any]):
    """Broadcast market data to subscribed clients with enhanced error handling"""
    if not active_connections:
        return

    # Track broadcast stats
    start_time = time.time()
    updates_sent = 0
    clients_updated = 0

    try:
        # Group clients by their subscriptions for efficient broadcasting
        clients_by_key = {}
        for client_id, subscriptions in client_subscriptions.items():
            for key in subscriptions:
                if key not in clients_by_key:
                    clients_by_key[key] = []
                clients_by_key[key].append(client_id)

        # For each updated instrument, send data to subscribed clients
        updates_by_client = {}
        for instrument_key, price_data in data.items():
            if instrument_key in clients_by_key:
                for client_id in clients_by_key[instrument_key]:
                    if client_id not in updates_by_client:
                        updates_by_client[client_id] = {}
                    updates_by_client[client_id][instrument_key] = price_data
                    updates_sent += 1

        # Send updates to each client
        disconnected_clients = []
        for client_id, updates in updates_by_client.items():
            if client_id in active_connections:
                try:
                    await active_connections[client_id].send_json(
                        {
                            "type": "market_data",
                            "data": updates,
                            "is_snapshot": False,
                            "update_count": len(updates),
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                    clients_updated += 1
                except Exception as e:
                    logger.error(f"❌ Error sending to client {client_id}: {e}")
                    disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            active_connections.pop(client_id, None)
            client_subscriptions.pop(client_id, None)
            logger.info(f"🧹 Cleaned up disconnected client: {client_id}")

        # Log broadcast stats periodically
        elapsed_time = (time.time() - start_time) * 1000  # ms
        if updates_sent > 0 and clients_updated > 0 and updates_sent % 500 == 0:
            logger.info(
                f"📡 Broadcast: {updates_sent} updates to {clients_updated} clients in {elapsed_time:.1f}ms"
            )

    except Exception as e:
        logger.error(f"❌ Broadcast error: {e}")


# INTEGRATION WITH CENTRALIZED MANAGER
# Add this function to integrate with your centralized WebSocket manager
async def integrate_with_centralized_manager():
    """
    Integrate this WebSocket route with the centralized manager
    This should be called during application startup
    """
    try:
        # Import the centralized manager
        from services.centralized_ws_manager import centralized_manager

        # Register this broadcast function as a callback
        def price_update_callback(data):
            """Callback to broadcast price updates to WebSocket clients"""
            import asyncio

            # Extract the market data from the callback
            market_data = data.get("data", {})
            if market_data:
                # Create a task to broadcast the data
                asyncio.create_task(broadcast_market_data(market_data))

        # Register the callback with the centralized manager
        centralized_manager.register_callback("price_update", price_update_callback)

        logger.info("✅ Integrated WebSocket routes with centralized manager")
        return True

    except ImportError as e:
        logger.warning(f"⚠️ Could not integrate with centralized manager: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error integrating with centralized manager: {e}")
        return False


# Helper function to get connection stats
def get_websocket_stats():
    """Get current WebSocket connection statistics"""
    total_clients = len(active_connections)
    total_subscriptions = sum(len(subs) for subs in client_subscriptions.values())

    return {
        "total_clients": total_clients,
        "total_subscriptions": total_subscriptions,
        "clients": list(active_connections.keys()),
        "subscription_summary": {
            client_id: len(subs) for client_id, subs in client_subscriptions.items()
        },
    }

    # Add this code to the END of your existing api/websocket_routes.py file


# Place it AFTER your existing broadcast_market_data function


# ===== ROOT WebSocket Route (Fixes 403 errors) =====
@router.websocket("/")
async def websocket_root(websocket: WebSocket):
    """Root WebSocket endpoint - handles current component connections"""
    await websocket.accept()
    client_id = f"root_{id(websocket)}"
    active_connections[client_id] = websocket

    try:
        logger.info(f"🔌 Root WebSocket client connected: {client_id}")

        # Send welcome message
        await websocket.send_json(
            {
                "type": "connection",
                "status": "connected",
                "client_id": client_id,
                "message": "Connected to trading system",
                "available_endpoints": [
                    "/ws/market-data",
                    "/ws/dashboard",
                    "/ws/scanner",
                    "/ws/signals",
                ],
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Message handling loop
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                await handle_root_message(websocket, client_id, message)

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "message": "Invalid JSON format"}
                )
            except Exception as e:
                logger.error(f"❌ Root message error: {e}")

    except Exception as e:
        logger.error(f"❌ Root WebSocket error: {e}")
    finally:
        active_connections.pop(client_id, None)
        logger.info(f"🧹 Root client disconnected: {client_id}")


# ===== DASHBOARD WebSocket Route =====
@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """Dashboard WebSocket endpoint"""
    await websocket.accept()
    client_id = f"dashboard_{id(websocket)}"
    active_connections[client_id] = websocket
    client_subscriptions[client_id] = set()

    try:
        logger.info(f"📊 Dashboard WebSocket connected: {client_id}")

        await websocket.send_json(
            {
                "type": "dashboard_connected",
                "client_id": client_id,
                "message": "Connected to dashboard updates",
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Try to register with centralized manager
        try:
            from services.centralized_ws_manager import get_centralized_manager

            manager = get_centralized_manager()
            await manager.add_client(client_id, websocket, "dashboard")
            logger.info(f"✅ Dashboard client registered with centralized manager")
        except ImportError:
            logger.warning("⚠️ Centralized manager not available")
        except Exception as e:
            logger.warning(f"⚠️ Could not register with centralized manager: {e}")

        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                await handle_dashboard_message(websocket, client_id, message)

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "message": "Invalid JSON format"}
                )
            except Exception as e:
                logger.error(f"❌ Dashboard message error: {e}")

    except Exception as e:
        logger.error(f"❌ Dashboard WebSocket error: {e}")
    finally:
        active_connections.pop(client_id, None)
        client_subscriptions.pop(client_id, None)
        # Remove from centralized manager
        try:
            from services.centralized_ws_manager import get_centralized_manager

            manager = get_centralized_manager()
            await manager.remove_client(client_id)
        except:
            pass
        logger.info(f"🧹 Dashboard client disconnected: {client_id}")


# ===== SCANNER WebSocket Route =====
# @router.websocket("/ws/scanner")
# async def websocket_scanner(websocket: WebSocket):
#     """Scanner WebSocket endpoint"""
#     await websocket.accept()
#     client_id = f"scanner_{id(websocket)}"
#     active_connections[client_id] = websocket

#     try:
#         logger.info(f"🔍 Scanner WebSocket connected: {client_id}")

#         await websocket.send_json(
#             {
#                 "type": "scanner_connected",
#                 "client_id": client_id,
#                 "message": "Connected to scanner updates",
#                 "timestamp": datetime.now().isoformat(),
#             }
#         )

#         while True:
#             try:
#                 data = await websocket.receive_text()
#                 message = json.loads(data)
#                 await handle_scanner_message(websocket, client_id, message)

#             except WebSocketDisconnect:
#                 break
#             except json.JSONDecodeError:
#                 await websocket.send_json(
#                     {"type": "error", "message": "Invalid JSON format"}
#                 )
#             except Exception as e:
#                 logger.error(f"❌ Scanner message error: {e}")

#     except Exception as e:
#         logger.error(f"❌ Scanner WebSocket error: {e}")
#     finally:
#         active_connections.pop(client_id, None)
#         logger.info(f"🧹 Scanner client disconnected: {client_id}")


# ===== SIGNALS WebSocket Route =====
# @router.websocket("/ws/signals")
# async def websocket_signals(websocket: WebSocket):
#     """Trading Signals WebSocket endpoint"""
#     await websocket.accept()
#     client_id = f"signals_{id(websocket)}"
#     active_connections[client_id] = websocket

#     try:
#         logger.info(f"🎯 Signals WebSocket connected: {client_id}")

#         await websocket.send_json(
#             {
#                 "type": "signals_connected",
#                 "client_id": client_id,
#                 "message": "Connected to trading signals",
#                 "timestamp": datetime.now().isoformat(),
#             }
#         )

#         while True:
#             try:
#                 data = await websocket.receive_text()
#                 message = json.loads(data)
#                 await handle_signals_message(websocket, client_id, message)

#             except WebSocketDisconnect:
#                 break
#             except json.JSONDecodeError:
#                 await websocket.send_json(
#                     {"type": "error", "message": "Invalid JSON format"}
#                 )
#             except Exception as e:
#                 logger.error(f"❌ Signals message error: {e}")

#     except Exception as e:
#         logger.error(f"❌ Signals WebSocket error: {e}")
#     finally:
#         active_connections.pop(client_id, None)
#         logger.info(f"🧹 Signals client disconnected: {client_id}")


# ===== MESSAGE HANDLERS =====


async def handle_root_message(websocket: WebSocket, client_id: str, message: dict):
    """Handle root WebSocket messages - delegates to appropriate handlers"""
    message_type = message.get("type")

    try:
        # Ping/Pong
        if message_type == "ping":
            await websocket.send_json(
                {"type": "pong", "timestamp": datetime.now().isoformat()}
            )

        # Dashboard related messages
        elif message_type in ["subscribe_to_dashboard_updates"]:
            await handle_dashboard_message(websocket, client_id, message)

        # Default response
        else:
            await websocket.send_json(
                {
                    "type": "echo",
                    "received": message,
                    "suggestion": "Use specific endpoints for better performance",
                    "timestamp": datetime.now().isoformat(),
                }
            )

    except Exception as e:
        logger.error(f"❌ Error handling root message: {e}")
        await websocket.send_json(
            {"type": "error", "message": "Error processing message"}
        )


async def handle_dashboard_message(websocket: WebSocket, client_id: str, message: dict):
    """Handle dashboard-specific messages"""
    message_type = message.get("type")

    try:
        if message_type == "subscribe_to_scanner_updates":
            await websocket.send_json(
                {
                    "type": "subscription_status",
                    "channel": "scanner_updates",
                    "status": "subscribed",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        elif message_type == "subscribe_to_signal_updates":
            await websocket.send_json(
                {
                    "type": "subscription_status",
                    "channel": "signal_updates",
                    "status": "subscribed",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Get dashboard data
        elif message_type == "get_dashboard_data":
            try:
                dashboard_data = await get_dashboard_data()
                await websocket.send_json(
                    {
                        "type": "dashboard_data",
                        "data": dashboard_data,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            except Exception as e:
                await websocket.send_json(
                    {"type": "error", "message": f"Error getting dashboard data: {e}"}
                )

        else:
            await websocket.send_json(
                {
                    "type": "unknown_message",
                    "received": message,
                    "timestamp": datetime.now().isoformat(),
                }
            )

    except Exception as e:
        logger.error(f"❌ Error handling dashboard message: {e}")


# async def handle_scanner_message(websocket: WebSocket, client_id: str, message: dict):
#     """Handle scanner-specific messages"""
#     message_type = message.get("type")

#     try:
#         if message_type == "subscribe_to_scanner_updates":
#             await websocket.send_json(
#                 {
#                     "type": "subscription_status",
#                     "channel": "scanner_updates",
#                     "status": "subscribed",
#                     "timestamp": datetime.now().isoformat(),
#                 }
#             )

#         elif message_type == "get_scanner_results":
#             try:
#                 # Get scanner results from your scanner engine
#                 from router.scanner_signal_router import scanner_engine

#                 if scanner_engine:
#                     # Get the latest scanner results
#                     # You may need to adjust this based on your scanner engine implementation
#                     scanner_results = {}

#                     # Try to get scanner status and results
#                     try:
#                         status = scanner_engine.get_scanner_status()
#                         scanner_results = {
#                             "status": status,
#                             "results": {},  # Add actual results here
#                         }
#                     except Exception as scanner_error:
#                         logger.warning(f"⚠️ Scanner engine error: {scanner_error}")
#                         scanner_results = {"error": str(scanner_error)}

#                     await websocket.send_json(
#                         {
#                             "type": "scanner_results",
#                             "data": scanner_results,
#                             "timestamp": datetime.now().isoformat(),
#                         }
#                     )
#                 else:
#                     await websocket.send_json(
#                         {"type": "error", "message": "Scanner engine not available"}
#                     )
#             except ImportError:
#                 await websocket.send_json(
#                     {"type": "error", "message": "Scanner engine not imported"}
#                 )
#             except Exception as e:
#                 await websocket.send_json(
#                     {"type": "error", "message": f"Scanner error: {e}"}
#                 )

#         else:
#             await websocket.send_json(
#                 {
#                     "type": "unknown_message",
#                     "received": message,
#                     "timestamp": datetime.now().isoformat(),
#                 }
#             )

#     except Exception as e:
#         logger.error(f"❌ Error handling scanner message: {e}")


# async def handle_signals_message(websocket: WebSocket, client_id: str, message: dict):
#     """Handle signals-specific messages"""
#     message_type = message.get("type")

#     try:
#         if message_type == "subscribe_to_signal_updates":
#             await websocket.send_json(
#                 {
#                     "type": "subscription_status",
#                     "channel": "signal_updates",
#                     "status": "subscribed",
#                     "timestamp": datetime.now().isoformat(),
#                 }
#             )

#         elif message_type == "get_trading_signals":
#             try:
#                 # Get signals from your signal engine
#                 from router.scanner_signal_router import signal_engine

#                 if signal_engine:
#                     signals = signal_engine.get_active_signals()
#                     await websocket.send_json(
#                         {
#                             "type": "trading_signals",
#                             "signals": signals,
#                             "timestamp": datetime.now().isoformat(),
#                         }
#                     )
#                 else:
#                     await websocket.send_json(
#                         {"type": "error", "message": "Signal engine not available"}
#                     )
#             except ImportError:
#                 await websocket.send_json(
#                     {"type": "error", "message": "Signal engine not imported"}
#                 )
#             except Exception as e:
#                 await websocket.send_json(
#                     {"type": "error", "message": f"Signal error: {e}"}
#                 )

#         else:
#             await websocket.send_json(
#                 {
#                     "type": "unknown_message",
#                     "received": message,
#                     "timestamp": datetime.now().isoformat(),
#                 }
#             )

#     except Exception as e:
#         logger.error(f"❌ Error handling signals message: {e}")


# ===== UTILITY FUNCTIONS =====


async def get_dashboard_data():
    """Get combined dashboard data"""
    try:
        dashboard_data = {
            "scanner": {"status": None, "results": {}},
            "signals": {"status": None, "active_signals": []},
            "timestamp": datetime.now().isoformat(),
        }

        return dashboard_data

    except Exception as e:
        logger.error(f"❌ Error getting dashboard data: {e}")
        return {"error": str(e), "timestamp": datetime.now().isoformat()}


@router.websocket("/ws/options-chain/{symbol}")
async def websocket_options_chain(websocket: WebSocket, symbol: str):
    """Options Chain WebSocket endpoint"""
    await websocket.accept()
    client_id = f"options_{id(websocket)}_{symbol}"
    active_connections[client_id] = websocket

    # Track which options chain this client is subscribed to
    if not hasattr(websocket_routes, "options_chain_subscriptions"):
        websocket_routes.options_chain_subscriptions = {}

    # Add this client to the subscriptions for this symbol
    if symbol not in websocket_routes.options_chain_subscriptions:
        websocket_routes.options_chain_subscriptions[symbol] = set()

    websocket_routes.options_chain_subscriptions[symbol].add(client_id)

    try:
        logger.info(f"📊 Options Chain WebSocket connected: {client_id}")

        # Send initial options chain data
        try:
            from services.instrument_registry import instrument_registry

            # Get initial options chain data
            options_chain = instrument_registry.get_options_chain(symbol.upper())

            # Get spot price for ATM identification
            spot_data = instrument_registry.get_spot_price(symbol.upper())
            spot_price = spot_data.get("last_price") if spot_data else None

            # Add ATM strike identification
            if spot_price and "strikes" in options_chain:
                options_chain["atm_strike"] = min(
                    options_chain["strikes"], key=lambda x: abs(x - spot_price)
                )

            # Send initial data
            await websocket.send_json(
                {
                    "type": "options_chain",
                    "symbol": symbol.upper(),
                    "spot_price": spot_price,
                    "data": options_chain,
                    "is_snapshot": True,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # Register instrument keys with centralized manager
            # This ensures price updates for these instruments come to this client
            if "call_data" in options_chain and "put_data" in options_chain:
                instrument_keys = []

                # Get the spot price key
                if spot_data and "instrument_key" in spot_data:
                    instrument_keys.append(spot_data["instrument_key"])

                # Get keys for all options
                for call in options_chain.get("call_data", []):
                    if "instrument_key" in call:
                        instrument_keys.append(call["instrument_key"])

                for put in options_chain.get("put_data", []):
                    if "instrument_key" in put:
                        instrument_keys.append(put["instrument_key"])

                # Register with centralized manager
                try:
                    from services.centralized_ws_manager import get_centralized_manager

                    manager = get_centralized_manager()
                    await manager.update_client_subscriptions(
                        client_id, instrument_keys
                    )
                    logger.info(
                        f"✅ Registered {len(instrument_keys)} keys with centralized manager"
                    )
                except Exception as e:
                    logger.warning(
                        f"⚠️ Could not register with centralized manager: {e}"
                    )

        except Exception as e:
            logger.error(f"❌ Error sending initial options chain data: {e}")
            await websocket.send_json(
                {
                    "type": "error",
                    "message": f"Error getting options chain data: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Message handling loop
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle options chain messages
                message_type = message.get("type")

                if message_type == "change_expiry":
                    # Change the selected expiry
                    expiry = message.get("expiry")

                    try:
                        options_chain = instrument_registry.get_options_chain(
                            symbol.upper(), expiry
                        )

                        # Send updated options chain
                        await websocket.send_json(
                            {
                                "type": "options_chain",
                                "symbol": symbol.upper(),
                                "data": options_chain,
                                "is_snapshot": True,
                                "expiry_changed": True,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                    except Exception as e:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": f"Error changing expiry: {str(e)}",
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

                elif message_type == "refresh":
                    # Manual refresh request
                    try:
                        options_chain = instrument_registry.get_options_chain(
                            symbol.upper()
                        )

                        # Send refreshed options chain
                        await websocket.send_json(
                            {
                                "type": "options_chain",
                                "symbol": symbol.upper(),
                                "data": options_chain,
                                "is_snapshot": True,
                                "refreshed": True,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                    except Exception as e:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": f"Error refreshing options chain: {str(e)}",
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "message": "Invalid JSON format"}
                )
            except Exception as e:
                logger.error(f"❌ Options chain message error: {e}")

    except Exception as e:
        logger.error(f"❌ Options Chain WebSocket error: {e}")
    finally:
        # Cleanup
        active_connections.pop(client_id, None)

        # Remove from options chain subscriptions
        if (
            hasattr(websocket_routes, "options_chain_subscriptions")
            and symbol in websocket_routes.options_chain_subscriptions
        ):
            websocket_routes.options_chain_subscriptions[symbol].discard(client_id)

            # Remove empty sets
            if not websocket_routes.options_chain_subscriptions[symbol]:
                del websocket_routes.options_chain_subscriptions[symbol]

        # Remove from centralized manager
        try:
            from services.centralized_ws_manager import get_centralized_manager

            manager = get_centralized_manager()
            await manager.remove_client(client_id)
        except:
            pass

        logger.info(f"🧹 Options Chain client disconnected: {client_id}")


# ===== UPDATE EXISTING FUNCTION =====


# Replace your existing get_websocket_stats function with this updated version:
def get_websocket_stats():
    """Get current WebSocket connection statistics - UPDATED"""
    total_clients = len(active_connections)
    total_subscriptions = sum(len(subs) for subs in client_subscriptions.values())

    # Group clients by type
    client_types = {
        "root": [cid for cid in active_connections.keys() if cid.startswith("root_")],
        "dashboard": [
            cid for cid in active_connections.keys() if cid.startswith("dashboard_")
        ],
        "scanner": [
            cid for cid in active_connections.keys() if cid.startswith("scanner_")
        ],
        "signals": [
            cid for cid in active_connections.keys() if cid.startswith("signals_")
        ],
        "market_data": [
            cid for cid in active_connections.keys() if cid.startswith("client_")
        ],
    }

    return {
        "total_clients": total_clients,
        "total_subscriptions": total_subscriptions,
        "client_types": {k: len(v) for k, v in client_types.items()},
        "clients_by_type": client_types,
        "active_endpoints": [
            "/",
            "/ws/dashboard",
            "/ws/scanner",
            "/ws/signals",
            "/ws/market-data",
        ],
        "subscription_summary": {
            client_id: len(subs) for client_id, subs in client_subscriptions.items()
        },
    }
