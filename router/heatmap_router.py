# router/heatmap_router.py
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Set
from fastapi import APIRouter, Query, HTTPException, WebSocket, WebSocketDisconnect

from services.heatmap_service import heatmap_service

logger = logging.getLogger(__name__)

# Create heatmap router
router = APIRouter()


class HeatmapWebSocketManager:
    """WebSocket manager for real-time heatmap updates"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.client_preferences: Dict[str, Dict[str, Any]] = {}
        self.broadcast_task = None
        self._connection_lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect a new WebSocket client"""
        async with self._connection_lock:
            await websocket.accept()
            self.active_connections[client_id] = websocket
            self.client_preferences[client_id] = {
                "width": 1200,
                "height": 800,
                "refresh_interval": 30,
                "filters": {},
            }
            logger.info(f"🔥 Heatmap WebSocket client connected: {client_id}")

            # Start broadcast task if not already running
            if not self.broadcast_task:
                self.broadcast_task = asyncio.create_task(self._broadcast_updates())

        # Send initial heatmap data
        await self.send_initial_heatmap(client_id)

    async def disconnect(self, client_id: str):
        """Disconnect a WebSocket client"""
        async with self._connection_lock:
            if client_id in self.active_connections:
                try:
                    websocket = self.active_connections[client_id]
                    if not websocket.client_state.DISCONNECTED:
                        await websocket.close()
                except Exception as e:
                    logger.debug(f"Error closing websocket for {client_id}: {e}")

                del self.active_connections[client_id]

            if client_id in self.client_preferences:
                del self.client_preferences[client_id]

            logger.info(f"🔥 Heatmap WebSocket client disconnected: {client_id}")

            # Stop broadcast task if no clients
            if not self.active_connections and self.broadcast_task:
                self.broadcast_task.cancel()
                self.broadcast_task = None

    async def is_connected(self, client_id: str) -> bool:
        """Check if a client is still connected"""
        if client_id not in self.active_connections:
            return False
        websocket = self.active_connections[client_id]
        return websocket.client_state != websocket.client_state.DISCONNECTED

    async def send_personal_message(self, message: dict, client_id: str) -> bool:
        """Send message to specific client"""
        if not await self.is_connected(client_id):
            await self.disconnect(client_id)
            return False

        try:
            websocket = self.active_connections[client_id]
            await websocket.send_text(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Error sending message to {client_id}: {e}")
            await self.disconnect(client_id)
            return False

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return

        disconnected_clients = []
        connections_copy = dict(self.active_connections)

        for client_id, connection in connections_copy.items():
            try:
                if await self.is_connected(client_id):
                    await connection.send_text(json.dumps(message))
                else:
                    disconnected_clients.append(client_id)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.disconnect(client_id)

    async def send_initial_heatmap(self, client_id: str):
        """Send initial heatmap data to newly connected client"""
        try:
            if not await self.is_connected(client_id):
                return

            preferences = self.client_preferences.get(client_id, {})
            width = preferences.get("width", 1200)
            height = preferences.get("height", 800)

            # Get initial heatmap data
            heatmap_data = heatmap_service.get_bloomberg_heatmap(width, height)
            sector_summary = heatmap_service.get_sector_summary()

            initial_message = {
                "type": "initial_heatmap",
                "data": {
                    "heatmap": heatmap_data,
                    "sector_summary": sector_summary,
                    "preferences": preferences,
                },
                "timestamp": datetime.now().isoformat(),
                "client_id": client_id,
            }

            success = await self.send_personal_message(initial_message, client_id)
            if success:
                logger.info(f"🔥 Sent initial heatmap data to client {client_id}")

        except Exception as e:
            logger.error(f"Error sending initial heatmap to {client_id}: {e}")
            await self.send_personal_message(
                {
                    "type": "error",
                    "message": f"Failed to send initial heatmap: {str(e)}",
                },
                client_id,
            )

    async def _broadcast_updates(self):
        """Background task to broadcast periodic heatmap updates"""
        while True:
            try:
                if not self.active_connections:
                    await asyncio.sleep(30)
                    continue

                # Get fresh heatmap data for broadcast
                heatmap_data = heatmap_service.get_bloomberg_heatmap(1200, 800)
                sector_summary = heatmap_service.get_sector_summary()

                update_message = {
                    "type": "heatmap_update",
                    "data": {
                        "heatmap": heatmap_data,
                        "sector_summary": sector_summary,
                        "stats": heatmap_data.get("data", {}).get("stats", {}),
                    },
                    "timestamp": datetime.now().isoformat(),
                    "clients_count": len(self.active_connections),
                }

                await self.broadcast(update_message)
                logger.info(
                    f"🔥 Broadcast heatmap update to {len(self.active_connections)} clients"
                )

                await asyncio.sleep(30)  # Update every 30 seconds

            except asyncio.CancelledError:
                logger.info("🔥 Heatmap broadcast task cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in heatmap broadcast: {e}")
                await asyncio.sleep(60)

    async def update_client_preferences(
        self, client_id: str, preferences: Dict[str, Any]
    ):
        """Update client preferences"""
        if client_id in self.client_preferences:
            self.client_preferences[client_id].update(preferences)

            # Send updated heatmap with new preferences
            width = preferences.get("width", 1200)
            height = preferences.get("height", 800)

            heatmap_data = heatmap_service.get_bloomberg_heatmap(width, height)

            update_message = {
                "type": "preferences_updated",
                "data": {
                    "heatmap": heatmap_data,
                    "preferences": self.client_preferences[client_id],
                },
                "timestamp": datetime.now().isoformat(),
            }

            await self.send_personal_message(update_message, client_id)


# Create WebSocket manager instance
heatmap_ws_manager = HeatmapWebSocketManager()


# REST API Endpoints
@router.get("/api/heatmap/bloomberg-style")
async def get_bloomberg_heatmap(
    width: int = Query(1200, ge=800, le=2000, description="Heatmap width"),
    height: int = Query(800, ge=600, le=1200, description="Heatmap height"),
):
    """Get Bloomberg-style treemap heatmap data"""
    try:
        heatmap_data = heatmap_service.get_bloomberg_heatmap(width, height)
        return heatmap_data
    except Exception as e:
        logger.error(f"Error generating Bloomberg heatmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/heatmap/treemap-data")
async def get_treemap_data():
    """Get raw treemap data for custom implementations"""
    try:
        treemap_data = heatmap_service.generate_treemap_data()
        return {
            "success": True,
            "data": treemap_data,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting treemap data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/heatmap/sector-summary")
async def get_sector_summary():
    """Get sector-wise performance summary"""
    try:
        summary_data = heatmap_service.get_sector_summary()
        return {
            "success": True,
            "data": summary_data,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting sector summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/heatmap/enhanced")
async def get_enhanced_heatmap(
    width: int = Query(1200, ge=800, le=2000),
    height: int = Query(800, ge=600, le=1200),
    color_metric: str = Query("change_percent", description="Metric for cell colors"),
    size_metric: str = Query("market_cap", description="Metric for cell sizes"),
    min_change: float = Query(None, description="Minimum change percentage filter"),
    min_volume: int = Query(None, description="Minimum volume filter"),
    sectors: str = Query(
        None, description="Comma-separated list of sectors to include"
    ),
):
    """Get enhanced heatmap with filtering and customization options"""
    try:
        # Get base heatmap data
        heatmap_data = heatmap_service.get_bloomberg_heatmap(width, height)

        if not heatmap_data.get("success", True):
            return heatmap_data

        cells = heatmap_data.get("data", {}).get("cells", [])

        # Apply filters
        filtered_cells = cells

        if min_change is not None:
            filtered_cells = [
                cell
                for cell in filtered_cells
                if abs(cell.get("change_percent", 0)) >= min_change
            ]

        if min_volume is not None:
            filtered_cells = [
                cell for cell in filtered_cells if cell.get("volume", 0) >= min_volume
            ]

        if sectors:
            sector_list = [s.strip().upper() for s in sectors.split(",")]
            filtered_cells = [
                cell
                for cell in filtered_cells
                if cell.get("sector_key", "").upper() in sector_list
            ]

        # Update stats for filtered data
        stats = {
            "total_stocks": len(filtered_cells),
            "gainers": len(
                [c for c in filtered_cells if c.get("change_percent", 0) > 0.1]
            ),
            "losers": len(
                [c for c in filtered_cells if c.get("change_percent", 0) < -0.1]
            ),
            "unchanged": len(
                [c for c in filtered_cells if -0.1 <= c.get("change_percent", 0) <= 0.1]
            ),
        }

        # Update heatmap data
        heatmap_data["data"]["cells"] = filtered_cells
        heatmap_data["data"]["stats"] = stats
        heatmap_data["data"]["filters"] = {
            "color_metric": color_metric,
            "size_metric": size_metric,
            "min_change": min_change,
            "min_volume": min_volume,
            "sectors": sectors,
        }

        return heatmap_data

    except Exception as e:
        logger.error(f"Error getting enhanced heatmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket Endpoint
@router.websocket("/ws/heatmap")
async def websocket_heatmap(websocket: WebSocket):
    """WebSocket endpoint for real-time heatmap updates"""
    client_id = f"heatmap_{datetime.now().timestamp()}"

    try:
        # Connect the client
        await heatmap_ws_manager.connect(websocket, client_id)

        # Handle incoming messages
        while True:
            try:
                if not await heatmap_ws_manager.is_connected(client_id):
                    break

                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                message = json.loads(data)
                message_type = message.get("type", "unknown")
                logger.info(
                    f"🔥 Received heatmap message from {client_id}: {message_type}"
                )

                if not await heatmap_ws_manager.is_connected(client_id):
                    break

                # Handle different message types
                if message_type == "get_heatmap":
                    width = message.get("width", 1200)
                    height = message.get("height", 800)

                    heatmap_data = heatmap_service.get_bloomberg_heatmap(width, height)

                    await heatmap_ws_manager.send_personal_message(
                        {
                            "type": "heatmap_data",
                            "data": heatmap_data,
                            "timestamp": datetime.now().isoformat(),
                        },
                        client_id,
                    )

                elif message_type == "get_sector_summary":
                    sector_data = heatmap_service.get_sector_summary()

                    await heatmap_ws_manager.send_personal_message(
                        {
                            "type": "sector_summary",
                            "data": sector_data,
                            "timestamp": datetime.now().isoformat(),
                        },
                        client_id,
                    )

                elif message_type == "update_preferences":
                    preferences = message.get("preferences", {})
                    await heatmap_ws_manager.update_client_preferences(
                        client_id, preferences
                    )

                elif message_type == "get_treemap_data":
                    treemap_data = heatmap_service.generate_treemap_data()

                    await heatmap_ws_manager.send_personal_message(
                        {
                            "type": "treemap_data",
                            "data": treemap_data,
                            "timestamp": datetime.now().isoformat(),
                        },
                        client_id,
                    )

                elif message_type == "ping":
                    await heatmap_ws_manager.send_personal_message(
                        {"type": "pong", "timestamp": datetime.now().isoformat()},
                        client_id,
                    )

                else:
                    await heatmap_ws_manager.send_personal_message(
                        {
                            "type": "error",
                            "message": f"Unknown message type: {message_type}",
                            "timestamp": datetime.now().isoformat(),
                        },
                        client_id,
                    )

            except WebSocketDisconnect:
                logger.info(
                    f"🔥 Heatmap WebSocket client {client_id} disconnected normally"
                )
                break
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON from heatmap client {client_id}: {e}")
                await heatmap_ws_manager.send_personal_message(
                    {
                        "type": "error",
                        "message": "Invalid JSON format",
                        "timestamp": datetime.now().isoformat(),
                    },
                    client_id,
                )
            except Exception as e:
                logger.error(f"❌ Error handling heatmap message from {client_id}: {e}")
                if await heatmap_ws_manager.is_connected(client_id):
                    await heatmap_ws_manager.send_personal_message(
                        {
                            "type": "error",
                            "message": str(e),
                            "timestamp": datetime.now().isoformat(),
                        },
                        client_id,
                    )
                else:
                    break

    except Exception as e:
        logger.error(f"❌ Heatmap WebSocket error for client {client_id}: {e}")

    finally:
        await heatmap_ws_manager.disconnect(client_id)
