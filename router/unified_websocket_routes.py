import asyncio
import logging
from datetime import datetime
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

logger = logging.getLogger(__name__)
router = APIRouter()

# Active connections and subscriptions
active_connections: Dict[str, WebSocket] = {}
client_subscriptions: Dict[str, Set[str]] = {}

_event_listeners_registered = False


async def broadcast_to_clients(event_type: str, data: dict):
    """Send event data to all subscribed clients."""
    if not active_connections:
        return

    message = {
        "type": event_type,
        "data": data,
        "timestamp": datetime.now().isoformat(),
    }

    # Log analytics broadcasts
    if event_type == "analytics_update":
        gainers_in_msg = message.get("data", {}).get("top_movers", {}).get("gainers", [])
        logger.debug(f"Message contains {len(gainers_in_msg)} gainers")

    disconnected = []
    sent_count = 0
    for client_id, ws in list(active_connections.items()):
        try:
            if event_type in client_subscriptions.get(client_id, set()):
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json(message)
                    sent_count += 1
        except Exception as e:
            logger.debug(f"Error sending to {client_id}: {e}")
            disconnected.append(client_id)

    if event_type == "analytics_update" and sent_count > 0:
        logger.info(f"Sent analytics_update to {sent_count} client(s)")

    for client_id in disconnected:
        active_connections.pop(client_id, None)
        client_subscriptions.pop(client_id, None)


def register_engine_listeners():
    """Register listeners on RealtimeMarketEngine events and centralized manager."""
    global _event_listeners_registered
    if _event_listeners_registered:
        return

    from services.realtime_market_engine import get_market_engine
    from services.centralized_ws_manager import get_centralized_manager

    engine = get_market_engine()
    centralized_manager = get_centralized_manager()

    # Price updates from realtime engine
    def on_price_update(data):
        if active_connections:
            asyncio.create_task(broadcast_to_clients("price_update", data))

    # Full analytics (top movers, sentiment, sector heatmap, volume analysis)
    def on_analytics_update(data):
        if active_connections:
            gainers = data.get("top_movers", {}).get("gainers", [])
            losers = data.get("top_movers", {}).get("losers", [])
            logger.info(
                f"Broadcasting analytics to {len(active_connections)} clients: "
                f"{len(gainers)} gainers, {len(losers)} losers"
            )
            asyncio.create_task(broadcast_to_clients("analytics_update", data))

    # Breakout signals from enhanced breakout engine
    def on_breakout_signal(data):
        if active_connections:
            logger.info(f"Broadcasting breakout signal to {len(active_connections)} clients: {data.get('instrument', 'unknown')}")
            asyncio.create_task(broadcast_to_clients("breakout_signal", data))

    # Register engine events
    engine.event_emitter.on("price_update", on_price_update)
    engine.event_emitter.on("analytics_update", on_analytics_update)
    engine.event_emitter.on("breakout_signal", on_breakout_signal)

    # Also register with centralized manager for real-time price updates
    def on_centralized_price_update(updates: dict):
        """Handle price updates from centralized WebSocket manager"""
        if not active_connections or not updates:
            return

        if not isinstance(updates, dict):
            logger.error(f"Invalid updates type: {type(updates).__name__}")
            return

        try:
            # Extract the actual feed data from the updates dict
            # The data structure is: {"data": {instrument_key: {price_data}}, ...}
            feed_data = updates.get("data", {})

            if not feed_data:
                logger.debug("No feed data in updates")
                return

            # Forward to realtime engine for processing
            from services.realtime_market_engine import update_market_data
            update_market_data(feed_data)

            # Note: We don't broadcast here because the engine.event_emitter.emit("price_update")
            # will trigger on_price_update() callback above, which broadcasts complete data

        except Exception as e:
            logger.error(f"Error in on_centralized_price_update: {e}", exc_info=True)

    try:
        centralized_manager.register_callback("price_update", on_centralized_price_update)
        logger.info("✅ Registered callback with centralized WebSocket manager")
    except Exception as e:
        logger.warning(f"⚠️ Could not register with centralized manager: {e}")

    _event_listeners_registered = True
    logger.info("✅ WebSocket listeners registered on market engine and centralized manager")


@router.websocket("/ws/unified")
async def unified_websocket_endpoint(websocket: WebSocket):
    """Unified WebSocket endpoint for real-time market data."""
    client_id = None
    try:
        await websocket.accept()

        import uuid

        client_id = f"client_{uuid.uuid4().hex[:8]}"
        active_connections[client_id] = websocket
        client_subscriptions[client_id] = set()

        logger.info(f"✅ Client connected: {client_id}")

        # Welcome message
        await websocket.send_json(
            {
                "type": "connection_established",
                "client_id": client_id,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Register engine listeners (once)
        register_engine_listeners()

        # Handle client messages
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "subscribe":
                events = data.get("events", [])
                if "all" in events:
                    client_subscriptions[client_id] = {
                        "price_update",
                        "analytics_update",
                        "breakout_signal",
                    }
                else:
                    client_subscriptions[client_id].update(events)

                await websocket.send_json(
                    {
                        "type": "subscription_confirmed",
                        "events": list(client_subscriptions[client_id]),
                    }
                )
                logger.info(
                    f"📡 Client {client_id} subscribed to {len(client_subscriptions[client_id])} events"
                )

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "get_dashboard_data":
                from services.realtime_market_engine import get_live_analytics, get_market_engine

                engine = get_market_engine()

                # Get all live prices from engine
                live_prices = engine.get_live_prices()

                # Get analytics
                analytics = get_live_analytics()

                # Combine into dashboard data
                dashboard_data = {
                    "market_data": live_prices,
                    "live_prices": live_prices,
                }

                if analytics:
                    dashboard_data.update(analytics)

                await websocket.send_json(
                    {"type": "dashboard_data", "data": dashboard_data}
                )

            elif msg_type == "get_live_prices":
                from services.realtime_market_engine import get_market_engine

                engine = get_market_engine()
                live_prices = engine.get_live_prices()

                await websocket.send_json(
                    {"type": "dashboard_update", "data": live_prices}
                )

    except WebSocketDisconnect:
        logger.info(f"🔌 Client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
    finally:
        if client_id:
            active_connections.pop(client_id, None)
            client_subscriptions.pop(client_id, None)
            logger.info(f"🧹 Cleaned up client: {client_id}")
