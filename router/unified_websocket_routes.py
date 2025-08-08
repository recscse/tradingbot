# router/unified_websocket_routes.py - ENHANCED VERSION
"""
Enhanced Unified WebSocket Routes with better error handling
"""

from typing import Any, Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
import json
from datetime import datetime
import logging
import asyncio
import uuid
import traceback

from services.unified_websocket_manager import unified_manager


logger = logging.getLogger(__name__)


router = APIRouter()


@router.websocket("/ws/unified")
async def unified_websocket_endpoint(websocket: WebSocket):
    """
    ENHANCED: Single WebSocket endpoint for ALL features with better error handling
    """
    client_id = None

    try:
        # FIXED: Accept the WebSocket connection directly in the route handler
        await websocket.accept()
        logger.info("✅ WebSocket connection accepted")

        # Generate client ID
        client_id = f"dashboard_{uuid.uuid4().hex[:8]}"

        # Register with the unified manager
        unified_manager.connections[client_id] = websocket
        unified_manager.client_types[client_id] = "dashboard"
        unified_manager.client_subscriptions[client_id] = set()

        # Send welcome message directly
        await websocket.send_json(
            {
                "type": "connection_established",
                "client_id": client_id,
                "client_type": "dashboard",
                "available_events": unified_manager.get_available_events(),
                "timestamp": datetime.now().isoformat(),
            }
        )

        logger.info(f"🔌 New client connected: {client_id}")

        # Send initial data with better error handling
        try:
            from services.enhanced_market_analytics import enhanced_analytics
            from services.instrument_registry import instrument_registry

            # Force analytics calculation to ensure fresh data
            try:
                if unified_manager.is_running and unified_manager.analytics_service:
                    await unified_manager._calculate_all_analytics()
            except Exception as analytics_error:
                logger.warning(f"⚠️ Could not force analytics update: {analytics_error}")

            # Send analytics data
            initial_data = enhanced_analytics.get_complete_analytics()
            if isinstance(initial_data, dict) and initial_data:
                await websocket.send_json(
                    {
                        "type": "initial_data",
                        "data": initial_data,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                logger.info(f"📊 Sent initial analytics data to {client_id}")
            else:
                # Send minimal data if analytics not available
                await websocket.send_json(
                    {
                        "type": "initial_data",
                        "data": {"message": "Analytics initializing, please wait for updates"},
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                logger.info(f"📊 Sent minimal initial data to {client_id}")

            # Send enriched live prices
            enriched_prices = instrument_registry.get_enriched_prices()
            if enriched_prices:
                await websocket.send_json(
                    {
                        "type": "live_prices_enriched",
                        "data": enriched_prices,
                        "total_instruments": len(enriched_prices),
                        "data_format": "enriched",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                logger.info(f"💰 Sent initial enriched prices to {client_id}: {len(enriched_prices)} instruments")
            else:
                logger.info(f"💰 No enriched prices available for {client_id}")

        except Exception as e:
            logger.error(f"❌ Error sending initial data: {e}")
            # Send error notification to client
            try:
                await websocket.send_json(
                    {
                        "type": "error", 
                        "message": "Initial data loading error, real-time updates will continue",
                        "timestamp": datetime.now().isoformat()
                    }
                )
            except Exception as send_error:
                logger.error(f"❌ Could not send error notification: {send_error}")

        # Message handling loop
        while True:
            try:
                # Receive message from client with timeout
                data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=300.0
                )  # 5 min timeout

                try:
                    message = json.loads(data)
                except json.JSONDecodeError as e:
                    logger.warning(f"❌ Invalid JSON from {client_id}: {e}")
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Invalid JSON format",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                    continue

                # Handle the message
                await handle_unified_message(client_id, websocket, message)

            except asyncio.TimeoutError:
                # Send ping to check if client is still alive
                try:
                    await websocket.send_json(
                        {"type": "ping", "timestamp": datetime.now().isoformat()}
                    )
                except:
                    logger.info(f"❌ Ping failed for {client_id}, closing connection")
                    break  # Client is dead

            except WebSocketDisconnect:
                logger.info(f"🔌 Client {client_id} disconnected normally")
                break

            except Exception as e:
                logger.error(f"❌ Message handling error for {client_id}: {e}")
                try:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Message processing error: {str(e)}",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                except:
                    logger.info(
                        f"❌ Cannot send error message to {client_id}, closing connection"
                    )
                    break  # Can't send error, connection is probably dead

    except WebSocketDisconnect:
        logger.info(f"🔌 Client disconnected during setup")
    except Exception as e:
        logger.error(f"❌ WebSocket connection error: {e}")
        logger.error(traceback.format_exc())

    finally:
        # Clean up
        if client_id:
            if client_id in unified_manager.connections:
                del unified_manager.connections[client_id]
            if client_id in unified_manager.client_types:
                del unified_manager.client_types[client_id]
            if client_id in unified_manager.client_subscriptions:
                del unified_manager.client_subscriptions[client_id]
            logger.info(f"🧹 Cleaned up client: {client_id}")


async def handle_unified_message(
    client_id: str, websocket: WebSocket, message: Dict[str, Any]
):
    """Handle messages from clients with improved error handling"""
    try:
        message_type = message.get("type")

        if not message_type:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "Missing message type",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return

        if message_type == "subscribe":
            # Subscribe to specific events
            events = message.get("events", [])
            real_time_mode = message.get("real_time", False)  # NEW: Real-time mode flag
            
            if not isinstance(events, list):
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Events must be a list",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                return

            unified_manager.subscribe_to_events(client_id, events)
            
            # If real-time mode requested, trigger immediate updates
            if real_time_mode:
                try:
                    # Force immediate analytics calculation and broadcast
                    from services.enhanced_market_analytics import enhanced_analytics
                    priority_analytics = enhanced_analytics.get_priority_analytics()
                    
                    for feature, data in priority_analytics.items():
                        if feature not in ["generated_at", "processing_time_ms", "is_priority_update"]:
                            unified_manager.emit_event(f"{feature}_update", data, priority=1)
                    
                    logger.info(f"✅ Real-time mode activated for client {client_id}")
                except Exception as e:
                    logger.error(f"❌ Error activating real-time mode: {e}")

            await websocket.send_json(
                {
                    "type": "subscription_confirmed",
                    "events": events,
                    "real_time_mode": real_time_mode,
                    "available_events": unified_manager.get_available_events(),
                    "timestamp": datetime.now().isoformat(),
                }
            )

        elif message_type == "get_dashboard_data":
            # FIXED: Enhanced dashboard data with proper error handling
            from services.enhanced_market_analytics import enhanced_analytics

            try:
                # Get complete analytics
                complete_dashboard_data = enhanced_analytics.get_complete_analytics()

                if not isinstance(complete_dashboard_data, dict):
                    logger.error(
                        f"get_complete_analytics expected dict, got {type(complete_dashboard_data)}"
                    )
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Invalid analytics data format",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                    return

                # CRITICAL FIX: Log what we're sending
                logger.info(
                    f"📊 Dashboard data features: {list(complete_dashboard_data.keys())}"
                )

                # Verify each feature has data
                for feature, data in complete_dashboard_data.items():
                    if feature in [
                        "top_movers",
                        "sector_heatmap",
                        "gap_analysis",
                        "volume_analysis",
                    ]:
                        if isinstance(data, dict):
                            logger.info(
                                f"✅ {feature}: {len(data)} keys - sample: {list(data.keys())[:3]}"
                            )
                        else:
                            logger.warning(f"⚠️ {feature}: unexpected type {type(data)}")

                # FIXED: Ensure all required fields are present with defaults
                dashboard_data = {
                    "type": "dashboard_data",
                    "timestamp": datetime.now().isoformat(),
                    # Core analytics
                    "top_movers": complete_dashboard_data.get(
                        "top_movers", {"gainers": [], "losers": []}
                    ),
                    "sector_heatmap": complete_dashboard_data.get(
                        "sector_heatmap", {"sectors": []}
                    ),
                    "gap_analysis": complete_dashboard_data.get(
                        "gap_analysis", {"gap_up": [], "gap_down": []}
                    ),
                    "breakout_analysis": complete_dashboard_data.get(
                        "breakout_analysis", {"breakouts": [], "breakdowns": []}
                    ),
                    "market_sentiment": complete_dashboard_data.get(
                        "market_sentiment", {"sentiment": "neutral"}
                    ),
                    "volume_analysis": complete_dashboard_data.get(
                        "volume_analysis", {"volume_leaders": []}
                    ),
                    "intraday_highlights": complete_dashboard_data.get(
                        "intraday_highlights", {"all_candidates": []}
                    ),
                    "intraday_stocks": complete_dashboard_data.get(
                        "intraday_stocks", {"all_candidates": []}
                    ),
                    "record_movers": complete_dashboard_data.get(
                        "record_movers", {"new_highs": [], "new_lows": []}
                    ),
                    "indices_data": complete_dashboard_data.get(  # NEW: Added indices data
                        "indices_data",
                        {"indices": [], "major_indices": [], "sector_indices": []},
                    ),
                    # Metadata
                    "generated_at": complete_dashboard_data.get("generated_at"),
                    "processing_time_ms": complete_dashboard_data.get(
                        "processing_time_ms"
                    ),
                    "cache_status": complete_dashboard_data.get("cache_status", {}),
                }

                await websocket.send_json(dashboard_data)
                logger.info(f"✅ Sent enhanced dashboard data to {client_id}")

            except Exception as e:
                logger.error(f"❌ Error getting dashboard data: {e}")
                import traceback

                logger.error(f"Full traceback: {traceback.format_exc()}")

                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Error getting dashboard data: {str(e)}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        elif message_type == "get_live_prices":
            try:
                from services.instrument_registry import instrument_registry

                symbols = message.get("symbols", [])

                if symbols and isinstance(symbols, list):
                    # Get specific enriched data for requested symbols
                    enriched_prices = {}
                    enriched_data = instrument_registry.get_enriched_prices()

                    for symbol in symbols:
                        symbol_upper = symbol.upper()
                        for instrument_key, data in enriched_data.items():
                            if data.get("symbol") == symbol_upper:
                                enriched_prices[instrument_key] = data
                                break
                else:
                    # Get all enriched data
                    enriched_prices = instrument_registry.get_enriched_prices()

                await websocket.send_json(
                    {
                        "type": "live_prices_enriched",  # Changed type to indicate enriched data
                        "data": enriched_prices,  # ✅ NOW HAS SYMBOL, NAME, SECTOR
                        "total_instruments": len(enriched_prices),
                        "data_format": "enriched",  # Indicator for frontend
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            except Exception as e:
                logger.error(f"Error getting enriched live prices: {e}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Error getting live prices: {str(e)}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        elif message_type == "get_options_chain":
            # Get options chain for symbol
            symbol = message.get("symbol")
            expiry = message.get("expiry")

            if not symbol:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Symbol is required for options chain",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                return

            try:
                from services.instrument_registry import instrument_registry

                options_data = instrument_registry.get_options_chain(
                    symbol.upper(), expiry
                )

                await websocket.send_json(
                    {
                        "type": "options_chain",
                        "symbol": symbol.upper(),
                        "expiry": expiry,
                        "data": options_data,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            except Exception as e:
                logger.error(f"❌ Error getting options chain for {symbol}: {e}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Error getting options chain: {str(e)}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        elif message_type == "get_stock_data":
            # Get specific stock data
            symbol = message.get("symbol")

            if not symbol:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Symbol is required",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                return

            try:
                from services.instrument_registry import instrument_registry

                stock_data = instrument_registry.get_spot_price(symbol.upper())

                await websocket.send_json(
                    {
                        "type": "stock_data",
                        "symbol": symbol.upper(),
                        "data": stock_data,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            except Exception as e:
                logger.error(f"❌ Error getting stock data for {symbol}: {e}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Error getting stock data: {str(e)}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        elif message_type == "get_indices_data":
            try:
                from services.enhanced_market_analytics import enhanced_analytics

                indices_data = enhanced_analytics.get_indices_data()

                await websocket.send_json(
                    {
                        "type": "indices_data",
                        "data": indices_data,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

                logger.info(
                    f"📈 Sent indices data to {client_id}: {indices_data.get('summary', {}).get('total_indices', 0)} indices"
                )

            except Exception as e:
                logger.error(f"❌ Error getting indices data: {e}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Error getting indices data: {str(e)}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        elif message_type == "get_sector_data":
            try:
                from services.instrument_registry import instrument_registry

                # Group enriched data by sector
                enriched_data = instrument_registry.get_enriched_prices()
                sector_groups = {}

                for instrument_key, data in enriched_data.items():
                    sector = data.get("sector", "OTHER")
                    if sector not in sector_groups:
                        sector_groups[sector] = []
                    sector_groups[sector].append(data)

                await websocket.send_json(
                    {
                        "type": "sector_data",
                        "data": sector_groups,
                        "total_sectors": len(sector_groups),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            except Exception as e:
                logger.error(f"Error getting sector data: {e}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Error getting sector data: {str(e)}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        elif message_type == "search_stocks":
            try:
                from services.instrument_registry import instrument_registry

                query = message.get("query", "").upper()
                if not query:
                    return

                # Search in enriched data
                enriched_data = instrument_registry.get_enriched_prices()
                search_results = []

                for instrument_key, data in enriched_data.items():
                    symbol = data.get("symbol", "")
                    name = data.get("name", "")

                    if query in symbol or query in name.upper():
                        search_results.append(data)

                        if len(search_results) >= 10:  # Limit results
                            break

                await websocket.send_json(
                    {
                        "type": "search_results",
                        "data": search_results,
                        "query": query,
                        "total_results": len(search_results),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            except Exception as e:
                logger.error(f"Error searching stocks: {e}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Error searching stocks: {str(e)}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        elif message_type == "ping":
            # Respond to ping
            await websocket.send_json(
                {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat(),
                    "server_time": datetime.now().isoformat(),
                }
            )

        elif message_type == "get_system_status":
            # Get system status
            try:
                status = unified_manager.get_status()

                await websocket.send_json(
                    {
                        "type": "system_status",
                        "data": status,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            except Exception as e:
                logger.error(f"❌ Error getting system status: {e}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Error getting system status: {str(e)}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        else:
            # Unknown message type
            await websocket.send_json(
                {
                    "type": "unknown_message",
                    "received_type": message_type,
                    "available_types": [
                        "subscribe",
                        "get_dashboard_data",
                        "get_live_prices",
                        "get_options_chain",
                        "get_stock_data",
                        "get_indices_data",
                        "get_system_status",
                        "ping",
                    ],
                    "timestamp": datetime.now().isoformat(),
                }
            )

    except Exception as e:
        logger.error(f"❌ Error handling message from {client_id}: {e}")
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": f"Internal error processing message: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        except Exception:
            logger.error(f"Failed to send error message to {client_id}")


# REST API endpoints for unified system
@router.get("/api/unified/status")
async def get_unified_status():
    """Get status of unified WebSocket system"""
    try:
        status = unified_manager.get_status()
        return {
            "success": True,
            "status": status,
            "available_events": unified_manager.get_available_events(),
            "websocket_url": "/ws/unified",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Error getting unified status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


@router.post("/api/unified/emit-event")
async def emit_test_event(event_data: Dict[str, Any]):
    """Emit a test event (for debugging)"""
    try:
        event_type = event_data.get("type")
        data = event_data.get("data", {})

        if not event_type:
            raise HTTPException(status_code=400, detail="Event type is required")

        unified_manager.emit_event(event_type, data)

        return {
            "success": True,
            "message": f"Event {event_type} emitted",
            "event_type": event_type,
            "data_size": len(str(data)),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Error emitting test event: {e}")
        raise HTTPException(status_code=500, detail=f"Error emitting event: {str(e)}")


@router.get("/api/unified/indices")
async def get_indices_data():
    """Get current indices data"""
    try:
        from services.enhanced_market_analytics import enhanced_analytics

        indices_data = enhanced_analytics.get_indices_data()

        return {
            "success": True,
            "data": indices_data,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Error getting indices data: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error getting indices data: {str(e)}"
        )


@router.get("/api/unified/indices/{symbol}")
async def get_specific_index_data(symbol: str):
    """Get specific index data by symbol"""
    try:
        from services.instrument_registry import instrument_registry

        index_data = instrument_registry.get_spot_price(symbol.upper())

        if not index_data:
            raise HTTPException(status_code=404, detail=f"Index {symbol} not found")

        return {
            "success": True,
            "symbol": symbol.upper(),
            "data": index_data,
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting index data for {symbol}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error getting index data: {str(e)}"
        )


@router.post("/api/unified/trigger-indices-refresh")
async def trigger_indices_refresh():
    """Manually trigger indices data refresh"""
    try:
        from services.enhanced_market_analytics import enhanced_analytics

        # Clear indices cache
        if "indices_data" in enhanced_analytics.cache:
            del enhanced_analytics.cache["indices_data"]
        if "indices_data" in enhanced_analytics.last_calculated:
            del enhanced_analytics.last_calculated["indices_data"]

        # Get fresh indices data
        indices_data = enhanced_analytics.get_indices_data()

        # Emit the update event
        unified_manager.emit_event("indices_data_update", indices_data)

        return {
            "success": True,
            "message": "Indices data refreshed successfully",
            "total_indices": indices_data.get("summary", {}).get("total_indices", 0),
            "major_indices": len(indices_data.get("major_indices", [])),
            "sector_indices": len(indices_data.get("sector_indices", [])),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Error refreshing indices data: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error refreshing indices data: {str(e)}"
        )


@router.get("/api/unified/market-summary")
async def get_market_summary_with_indices():
    """Get comprehensive market summary including indices"""
    try:
        from services.enhanced_market_analytics import enhanced_analytics
        from services.instrument_registry import instrument_registry

        # Get analytics data
        analytics = enhanced_analytics.get_complete_analytics()

        # Get registry market summary
        try:
            registry_summary = instrument_registry.get_market_summary()
        except AttributeError:
            registry_summary = {}

        # Combine data
        market_summary = {
            "indices": analytics.get("indices_data", {}),
            "market_sentiment": analytics.get("market_sentiment", {}),
            "market_breadth": registry_summary,
            "top_movers": analytics.get("top_movers", {}),
            "sector_performance": analytics.get("sector_heatmap", {}),
            "volume_analysis": analytics.get("volume_analysis", {}),
            "timestamp": datetime.now().isoformat(),
        }

        return {
            "success": True,
            "data": market_summary,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Error getting market summary: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error getting market summary: {str(e)}"
        )


@router.get("/api/unified/analytics")
async def get_current_analytics():
    """Get current analytics data"""
    try:
        return {
            "success": True,
            "data": unified_manager.analytics_cache,
            "live_prices_count": len(unified_manager.live_prices),
            "cache_keys": list(unified_manager.analytics_cache.keys()),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Error getting analytics: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error getting analytics: {str(e)}"
        )


@router.get("/api/unified/connections")
async def get_connection_info():
    """Get information about active connections"""
    try:
        status = unified_manager.get_status()

        return {
            "success": True,
            "connections": {
                "total": status["total_connections"],
                "by_type": status["client_types"],
                "active_subscriptions": len(unified_manager.client_subscriptions),
            },
            "system": {
                "event_queue_size": status["event_queue_size"],
                "background_tasks": status["background_tasks"],
                "is_running": status["is_running"],
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Error getting connection info: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error getting connection info: {str(e)}"
        )


@router.post("/api/unified/restart")
async def restart_unified_system():
    """Restart the unified WebSocket system (admin only)"""
    try:
        logger.info("🔄 Restarting unified WebSocket system...")

        # Stop current system
        await unified_manager.stop()

        # Wait a moment
        await asyncio.sleep(2)

        # Start again
        await unified_manager.start()

        return {
            "success": True,
            "message": "Unified WebSocket system restarted successfully",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Error restarting unified system: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error restarting system: {str(e)}"
        )


@router.get("/api/unified/health")
async def health_check():
    """Health check endpoint"""
    try:
        status = unified_manager.get_status()

        health_score = 100
        issues = []

        if not status["is_running"]:
            health_score -= 50
            issues.append("System not running")

        if status["total_connections"] == 0:
            health_score -= 10
            issues.append("No active connections")

        if status["event_queue_size"] > 900:  # Near queue limit
            health_score -= 20
            issues.append("Event queue nearly full")

        if len(status["cached_analytics"]) == 0:
            health_score -= 15
            issues.append("No cached analytics")

        health_status = (
            "healthy"
            if health_score >= 80
            else "degraded" if health_score >= 50 else "unhealthy"
        )

        return {
            "success": True,
            "health": {
                "status": health_status,
                "score": max(0, health_score),
                "issues": issues,
            },
            "system": status,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Error in health check: {e}")
        return {
            "success": False,
            "health": {
                "status": "error",
                "score": 0,
                "issues": [f"Health check failed: {str(e)}"],
            },
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/api/unified/trigger-analytics")
async def trigger_analytics_refresh():
    """Manually trigger analytics refresh"""
    try:
        try:
            from services.enhanced_market_analytics import enhanced_analytics

            analytics_data = enhanced_analytics.get_complete_analytics()

            # Store in unified manager cache
            unified_manager.analytics_cache = analytics_data

            # Emit events for each feature
            for feature, data in analytics_data.items():
                if feature not in [
                    "generated_at",
                    "processing_time_ms",
                    "cache_status",
                ]:
                    unified_manager.emit_event(f"{feature}_update", data)

            return {
                "success": True,
                "message": "Analytics refreshed successfully",
                "features": list(analytics_data.keys()),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"❌ Error refreshing analytics: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error refreshing analytics: {str(e)}"
            )
    except Exception as e:
        logger.error(f"❌ Unhandled error in trigger_analytics_refresh: {e}")
        raise HTTPException(status_code=500, detail=f"Unhandled error: {str(e)}")
