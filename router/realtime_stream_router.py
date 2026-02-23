# router/realtime_stream_router.py
"""
🚀 ZERO-DELAY Real-time Streaming WebSocket Router
Direct WebSocket connections for ultra-fast market data streaming
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/realtime", tags=["Real-time Streaming"])


@router.websocket("/stream")
async def realtime_market_data_stream(websocket: WebSocket):
    """
    🚀 ZERO-DELAY WebSocket endpoint for real-time market data streaming
    
    This endpoint provides ultra-fast market data updates by bypassing
    all processing layers and streaming raw data directly from Upstox.
    """
    await websocket.accept()
    client_id = f"realtime_client_{id(websocket)}"
    
    logger.info(f"🚀 ZERO-DELAY client connected: {client_id}")
    
    try:
        # Initialize real-time streamer
        from services.realtime_data_streamer import realtime_streamer
        
        # Start streaming if not already active
        realtime_streamer.start_streaming()
        
        # Register this WebSocket connection
        await realtime_streamer.register_ui_connection(websocket, client_id)
        
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "client_id": client_id,
            "message": "🚀 ZERO-DELAY streaming active",
            "streaming_stats": realtime_streamer.get_streaming_stats(),
            "timestamp": datetime.now().isoformat()
        }))
        
        # Keep connection alive and handle any incoming messages
        while True:
            try:
                # Check application state before receiving
                if websocket.application_state != WebSocketState.CONNECTED:
                    break
                    
                # Wait for any client messages (heartbeat, subscription changes, etc.)
                # Reduced timeout to be more responsive to state changes
                message = await asyncio.wait_for(websocket.receive_text(), timeout=20.0)
                
                try:
                    data = json.loads(message)
                    message_type = data.get("type")
                    
                    if message_type == "ping":
                        # Respond to ping with pong
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        }))
                        
                    elif message_type == "get_stats":
                        # Send streaming statistics
                        stats = realtime_streamer.get_streaming_stats()
                        await websocket.send_text(json.dumps({
                            "type": "streaming_stats",
                            "data": stats,
                            "timestamp": datetime.now().isoformat()
                        }))
                        
                    elif message_type == "subscribe":
                        # Handle subscription to specific instruments
                        instruments = data.get("instruments", [])
                        if instruments:
                            # For now, we stream all data - selective subscription can be added later
                            logger.info(f"📊 Client {client_id} subscribed to {len(instruments)} instruments")
                            await websocket.send_text(json.dumps({
                                "type": "subscription_confirmed",
                                "instruments_count": len(instruments),
                                "message": "Streaming all market data (selective streaming coming soon)",
                                "timestamp": datetime.now().isoformat()
                            }))
                        
                    else:
                        logger.debug(f"Unknown message type from {client_id}: {message_type}")
                        
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from client {client_id}: {message}")
                    
            except asyncio.TimeoutError:
                # Send periodic heartbeat to keep connection alive
                if websocket.application_state == WebSocketState.CONNECTED:
                    try:
                        await websocket.send_text(json.dumps({
                            "type": "heartbeat",
                            "active_connections": len(realtime_streamer._ui_connections),
                            "streaming_active": realtime_streamer._streaming_active,
                            "timestamp": datetime.now().isoformat()
                        }))
                    except Exception:
                        break
                else:
                    break
            
            except WebSocketDisconnect:
                # Normal disconnection handled by outer try-except
                raise
                
            except Exception as e:
                # 🛠️ IMPROVED: Handle abnormal closures (1006) without noisy error logs
                error_str = str(e)
                if "1006" in error_str or "ABNORMAL_CLOSURE" in error_str:
                    logger.debug(f"🔗 Client {client_id} connection closed abnormally (1006)")
                elif "1005" in error_str:
                    logger.debug(f"🔗 Client {client_id} connection closed (1005)")
                else:
                    # Log other unexpected errors
                    logger.error(f"Error handling message from {client_id}: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"🔗 Client {client_id} disconnected")
        
    except Exception as e:
        # Handle abnormal closures (1006) without noisy error logs at top level
        error_str = str(e)
        if "1006" in error_str or "ABNORMAL_CLOSURE" in error_str:
            logger.debug(f"🔗 Client {client_id} connection closed abnormally (1006)")
        elif "1005" in error_str:
            logger.debug(f"🔗 Client {client_id} connection closed (1005)")
        else:
            logger.error(f"❌ Error in real-time streaming for {client_id}: {e}")
        
    finally:
        # Clean up connection
        try:
            from services.realtime_data_streamer import realtime_streamer
            await realtime_streamer.unregister_ui_connection(websocket, client_id)
            logger.info(f"🔗 Cleaned up connection for {client_id}")
        except Exception as e:
            logger.error(f"❌ Error cleaning up connection {client_id}: {e}")


@router.get("/health")
async def realtime_streaming_health():
    """Health check for real-time streaming service"""
    try:
        from services.realtime_data_streamer import realtime_streamer
        
        health = await realtime_streamer.health_check()
        stats = realtime_streamer.get_streaming_stats()
        
        return {
            "status": "ok",
            "service": "realtime_data_streamer",
            "health": health,
            "stats": stats,
            "endpoints": {
                "stream": "/api/v1/realtime/stream",
                "health": "/api/v1/realtime/health",
                "stats": "/api/v1/realtime/stats"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except ImportError:
        return {
            "status": "error",
            "error": "Real-time data streamer service not available",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/stats")
async def realtime_streaming_stats():
    """Get detailed streaming statistics"""
    try:
        from services.realtime_data_streamer import realtime_streamer
        
        stats = realtime_streamer.get_streaming_stats()
        health = await realtime_streamer.health_check()
        
        return {
            "success": True,
            "stats": stats,
            "health": health,
            "performance_analysis": {
                "zero_delay_active": stats["streaming_active"],
                "latency_optimal": stats["average_latency_ms"] < 10,
                "connection_health": health["status"] == "healthy",
                "throughput": {
                    "total_broadcasts": stats["total_broadcasts"],
                    "active_connections": stats["active_connections"],
                    "broadcasts_per_connection": (
                        stats["total_broadcasts"] / max(1, stats["active_connections"])
                    )
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except ImportError:
        return {
            "success": False,
            "error": "Real-time data streamer service not available",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }