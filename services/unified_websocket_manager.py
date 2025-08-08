# services/unified_websocket_manager.py - FIXED VERSION
"""
Fixed Unified Event-Driven WebSocket Manager
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Set, Any, Callable, Optional
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from collections import defaultdict
import uuid

logger = logging.getLogger(__name__)


def safe_float(value, default=0.0):
    """Safely convert a value to float"""
    try:
        if value is None or value == "":
            return default
        if isinstance(value, bool):
            return float(value)
        return float(value)
    except (ValueError, TypeError):
        logger.debug(f"Invalid float value: {value}, using default {default}")
        return default


def safe_int(value, default=0):
    """Safely convert a value to int"""
    try:
        if value is None or value == "":
            return default
        if isinstance(value, bool):
            return int(value)
        return int(value)
    except (ValueError, TypeError):
        logger.debug(f"Invalid int value: {value}, using default {default}")
        return default


class UnifiedWebSocketManager:
    """
    FIXED: Single WebSocket manager for ALL features using event-driven architecture
    """

    def __init__(self):
        # Connection management
        self.connections: Dict[str, WebSocket] = {}
        self.client_subscriptions: Dict[str, Set[str]] = {}
        self.client_types: Dict[str, str] = {}

        # Event system
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self.event_queue = asyncio.Queue(maxsize=200)  # TRADING SAFETY: Increased for volatile periods
        
        # PERFORMANCE: Rate limiting and deduplication - ADJUSTED FOR TRADING SAFETY
        self.last_event_time = {}
        self.event_rate_limits = {
            "price_update": 0.1,  # CRITICAL: Reduced to 100ms for trading accuracy
            "dashboard_update": 0.2,  # Reduced to 200ms for UI responsiveness
            "top_movers_update": 1.0,  # Reduced to 1 second for momentum detection
            "intraday_stocks_update": 1.0,  # Reduced to 1 second for breakouts  
            "market_sentiment_update": 3.0,  # Reduced to 3 seconds
            "indices_data_update": 0.5,  # Reduced to 500ms for index tracking
            "volume_analysis_update": 2.0,  # Reduced to 2 seconds
            "analytics_update": 5.0,  # Reduced to 5 seconds
        }
        
        # SAFETY: Trading mode configuration
        self.trading_mode = True  # Enable stricter limits for trading
        self.emergency_mode = False  # Bypass rate limiting in extreme volatility
        self.pending_events = {}  # For deduplication

        # Feature-specific data caches
        self.live_prices = {}
        self.analytics_cache = {}
        self.heatmap_cache = {}
        self.movers_cache = {}

        # Background tasks
        self.background_tasks = set()
        self.is_running = False

        # FIXED: Add analytics service
        self.analytics_service = None
        self._init_analytics_service()

    # CRITICAL FIX: Add register_handler method INSIDE the class
    def register_handler(self, event_type: str, handler_func):
        """Register a handler function for a specific event type"""
        if not hasattr(self, "_event_handlers"):
            self._event_handlers = defaultdict(list)

        self._event_handlers[event_type].append(handler_func)
        logger.info(f"✅ Registered handler for {event_type} events")
        return True

    def _init_analytics_service(self):
        """Initialize analytics service"""
        try:
            from services.enhanced_market_analytics import enhanced_analytics

            self.analytics_service = enhanced_analytics
            logger.info("✅ Analytics service initialized")
        except ImportError as e:
            logger.warning(f"⚠️ Analytics service not available: {e}")

    async def start(self):
        """Start the unified WebSocket system"""
        if self.is_running:
            return

        self.is_running = True

        # Start event processor
        processor_task = asyncio.create_task(self._process_events())
        self.background_tasks.add(processor_task)
        processor_task.add_done_callback(lambda t: self.background_tasks.discard(t))

        # Start analytics updater
        analytics_task = asyncio.create_task(self._update_analytics())
        self.background_tasks.add(analytics_task)
        analytics_task.add_done_callback(lambda t: self.background_tasks.discard(t))
        
        # Start pending event processor
        pending_task = asyncio.create_task(self._process_pending_events())
        self.background_tasks.add(pending_task)
        pending_task.add_done_callback(lambda t: self.background_tasks.discard(t))
        
        # PERFORMANCE: Removed real-time heartbeat to prevent excessive analytics computation

        logger.info("🚀 Unified WebSocket Manager started")

    async def stop(self):
        """Stop the unified WebSocket system"""
        self.is_running = False

        # Cancel all background tasks
        for task in self.background_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)

        # Close all connections
        for client_id, ws in list(self.connections.items()):
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.close()
            except Exception as e:
                logger.debug(f"Error closing connection {client_id}: {e}")

        self.connections.clear()
        logger.info("🛑 Unified WebSocket Manager stopped")

    # ===== CONNECTION MANAGEMENT =====
    async def add_client(
        self, websocket: WebSocket, client_type: str = "dashboard"
    ) -> str:
        """Add a new WebSocket client"""
        try:
            # FIXED: Accept the WebSocket connection FIRST
            await websocket.accept()
            logger.info("🔌 WebSocket connection accepted")

            client_id = f"{client_type}_{uuid.uuid4().hex[:8]}"

            self.connections[client_id] = websocket
            self.client_types[client_id] = client_type
            self.client_subscriptions[client_id] = set()
            
            # Ensure event processor is running when first client connects
            if len(self.connections) == 1 and self.is_running:
                try:
                    # Start event processor if not already running
                    if not any(task for task in self.background_tasks if not task.done()):
                        task = asyncio.create_task(self._process_events())
                        self.background_tasks.add(task)
                        logger.info("🔄 Started event processor for new client connection")
                except Exception as e:
                    logger.error(f"❌ Error starting event processor: {e}")

            # Send welcome message directly via WebSocket
            try:
                await websocket.send_json(
                    {
                        "type": "connection_established",
                        "client_id": client_id,
                        "client_type": client_type,
                        "available_events": self.get_available_events(),
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            except Exception as e:
                logger.error(f"❌ Error sending welcome message: {e}")
                # Continue anyway - connection is established

            # Send initial data
            await self._send_initial_data(client_id, client_type)

            logger.info(f"🔌 Client connected: {client_id} ({client_type})")
            return client_id

        except Exception as e:
            logger.error(f"❌ Error adding client: {e}")
            # Try to close WebSocket if there was an error
            try:
                await websocket.close(code=1011, reason=f"Error during setup: {str(e)}")
            except Exception:
                pass
            raise

    async def remove_client(self, client_id: str):
        """Remove a WebSocket client"""
        if client_id in self.connections:
            try:
                ws = self.connections[client_id]
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.close()
            except Exception as e:
                logger.debug(f"Error closing WebSocket for {client_id}: {e}")

            # Clean up
            self.connections.pop(client_id, None)
            self.client_types.pop(client_id, None)
            self.client_subscriptions.pop(client_id, None)

            logger.info(f"🔌 Client disconnected: {client_id}")

    # ===== EVENT SYSTEM =====
    def subscribe_to_events(self, client_id: str, events: List[str]):
        """Subscribe client to specific events"""
        if client_id in self.client_subscriptions:
            self.client_subscriptions[client_id].update(events)
            logger.info(f"📡 Client {client_id} subscribed to {len(events)} events")

    def emit_event(self, event_type: str, data: Dict[str, Any], priority: int = 5):
        """Emit an event to the queue with priority support and rate limiting (1=highest, 10=lowest)"""
        
        # TRADING SAFETY: Emergency mode bypasses rate limiting
        if self.emergency_mode:
            logger.warning(f"🚨 EMERGENCY MODE: Bypassing rate limit for {event_type}")
        else:
            # PERFORMANCE: Rate limiting check
            now = datetime.now()
            rate_limit = self.event_rate_limits.get(event_type, 1.0)
            
            if event_type in self.last_event_time:
                time_since_last = (now - self.last_event_time[event_type]).total_seconds()
                if time_since_last < rate_limit:
                    # TRADING SAFETY: Allow high-priority events to bypass rate limiting
                    if priority <= 2 and event_type in ["price_update", "dashboard_update"]:
                        # Critical trading data bypasses rate limiting
                        logger.debug(f"⚡ Bypassing rate limit for critical {event_type} (priority: {priority})")
                        pass  
                    else:
                        # Rate limited - store as pending for later processing
                        self.pending_events[event_type] = {
                            "data": data,
                            "priority": priority,
                            "timestamp": now
                        }
                        logger.debug(f"🚦 Rate limited {event_type}, stored as pending")
                        return
        
        self.last_event_time[event_type] = now
        
        # Process any pending event of this type
        if event_type in self.pending_events:
            # Use the latest pending data
            pending = self.pending_events.pop(event_type)
            data = pending["data"]
            priority = pending["priority"]
        
        # Determine priority based on event type and data content
        if not isinstance(priority, int):
            priority = self._determine_event_priority(event_type, data)
        
        # PERFORMANCE: Normalize event type to prevent typos
        normalized_event_type = self._normalize_event_type(event_type)
        
        event = {
            "type": normalized_event_type,
            "data": data,
            "timestamp": now.isoformat(),
            "priority": priority,
        }

        try:
            self.event_queue.put_nowait(event)
            logger.debug(f"✅ Queued {normalized_event_type} (priority: {priority})")
        except asyncio.QueueFull:
            # For full queue, drop lower priority events first
            if priority <= 3:  # High priority events
                logger.warning(f"⚠️ Queue full but keeping high priority event: {normalized_event_type}")
                # Try to make room by processing one event immediately if possible
                try:
                    oldest_event = self.event_queue.get_nowait()
                    if oldest_event.get("priority", 5) > priority:
                        # Replace with higher priority event
                        self.event_queue.put_nowait(event)
                        logger.debug(f"🔄 Replaced lower priority event with {normalized_event_type}")
                    else:
                        # Put the old event back and drop current
                        self.event_queue.put_nowait(oldest_event) 
                        logger.warning(f"⚠️ Dropping high priority event due to queue pressure: {normalized_event_type}")
                except asyncio.QueueEmpty:
                    pass
            else:
                logger.warning(f"⚠️ Event queue full, dropping event: {normalized_event_type}")

    def _normalize_event_type(self, event_type: str) -> str:
        """Normalize event types to prevent duplicates from typos"""
        # Fix common typos seen in logs
        fixes = {
            "price_upddate": "price_update",
            "pprice_update": "price_update", 
            "dashboardd_update": "dashboard_update",
            "ddashboard_update": "dashboard_update",
            "top_moverrs_update": "top_movers_update",
            "ttop_movers_update": "top_movers_update",
            "intraday__stocks_update": "intraday_stocks_update", 
            "iintraday_stocks_update": "intraday_stocks_update",
            "market_seentiment_update": "market_sentiment_update",
            "mmarket_sentiment_update": "market_sentiment_update",
            "indices_ddata_update": "indices_data_update",
            "iindices_data_update": "indices_data_update",
        }
        
        return fixes.get(event_type, event_type)

    def _determine_event_priority(self, event_type: str, data: Dict[str, Any]) -> int:
        """Determine event priority based on type and content (1=highest, 10=lowest)"""
        
        # Indices data - highest priority
        if "indices" in event_type.lower() or event_type in ["market_status_update"]:
            return 1
            
        # FNO stocks data - high priority  
        if ("fno" in event_type.lower() or 
            (isinstance(data, dict) and data.get("fno_candidates")) or
            self._contains_fno_symbols(data)):
            return 2
            
        # Price updates and dashboard data - high priority
        if event_type in ["price_update", "dashboard_update", "live_prices_update"]:
            return 2
            
        # Top movers and volume analysis - medium-high priority
        if event_type in ["top_movers_update", "intraday_stocks_update"]:
            return 3
            
        # Market sentiment - medium priority  
        if "sentiment" in event_type.lower():
            return 4
            
        # Analytics and other updates - lower priority
        if "analytics" in event_type.lower():
            return 6
            
        # Default priority
        return 5
        
    def _contains_fno_symbols(self, data: Dict[str, Any]) -> bool:
        """Check if data contains FNO symbols"""
        try:
            fno_symbols = {"RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "SBIN", 
                          "WIPRO", "MARUTI", "HINDUNILVR", "ITC", "BAJFINANCE"}
            
            if isinstance(data, dict):
                # Check various data structures for FNO symbols
                for value in data.values():
                    if isinstance(value, str) and value.upper() in fno_symbols:
                        return True
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict) and item.get("symbol", "").upper() in fno_symbols:
                                return True  
                            elif isinstance(item, str) and item.upper() in fno_symbols:
                                return True
                                
            return False
        except:
            return False

    async def _process_events(self):
        """Process events from the queue with improved error handling"""
        logger.info("🔄 Event processor started")
        processed_count = 0
        
        while self.is_running:
            try:
                # Check if we're still supposed to be running
                if not self.is_running:
                    logger.info("🛑 Event processor stopping - is_running=False")
                    break
                    
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)  # OPTIMIZED: Longer timeout for batch processing
                processed_count += 1
                
                if processed_count % 50 == 0:  # OPTIMIZED: More frequent logging for monitoring
                    logger.info(f"🔄 Processed {processed_count} events, queue size: {self.event_queue.qsize()}")

                # FIXED: Special handling for analytics triggers
                if event.get("type") == "trigger_analytics":
                    try:
                        from services.enhanced_market_analytics import (
                            enhanced_analytics,
                        )

                        analytics_data = enhanced_analytics.get_complete_analytics()

                        # Emit individual feature events with proper priority
                        for feature, data in analytics_data.items():
                            if feature not in [
                                "generated_at",
                                "processing_time_ms",
                                "cache_status",
                            ]:
                                # Use priority for analytics events  
                                self.emit_event(f"{feature}_update", data, priority=6)

                        logger.info(
                            f"✅ Analytics refreshed and broadcast: {list(analytics_data.keys())}"
                        )
                    except Exception as e:
                        logger.error(f"❌ Error refreshing analytics: {e}")

                # Process regular event - REMOVED immediate analytics to prevent feedback loops
                event_type = event.get("type", "")
                
                # PERFORMANCE: Removed immediate analytics trigger to prevent excessive computation
                # Analytics are now handled by separate scheduled updates with proper caching
                
                await self._handle_event(event)
                
                # Mark task as done for the queue
                self.event_queue.task_done()
                
            except asyncio.TimeoutError:
                # Timeout is normal when no events are available - reduced timeout for faster processing
                if processed_count % 100 == 0 and processed_count > 0:  # OPTIMIZED: Less frequent status updates
                    logger.debug(f"🔄 Event processor alive, processed {processed_count} events")
                continue
            except asyncio.CancelledError:
                logger.info("🛑 Event processor cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Event processing error: {e}")
                # Continue processing despite errors
                await asyncio.sleep(0.1)
                
        logger.info(f"🛑 Event processor stopped after processing {processed_count} events")

    async def _handle_event(self, event: Dict[str, Any]):
        """Handle a single event with registered handlers"""
        try:
            event_type = event["type"]

            # FIXED: Call registered handlers first
            if hasattr(self, "_event_handlers") and event_type in self._event_handlers:
                for handler in self._event_handlers[event_type]:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event["data"])
                        else:
                            handler(event["data"])
                    except Exception as e:
                        logger.error(
                            f"❌ Error in registered handler for {event_type}: {e}"
                        )

            # Update relevant caches
            await self._update_cache_for_event(event)

            # Broadcast to subscribed clients
            await self._broadcast_event(event)

        except Exception as e:
            logger.error(f"❌ Error handling event {event.get('type')}: {e}")

    # ===== FEATURE-SPECIFIC METHODS =====
    async def _update_analytics(self):
        """Update analytics data periodically with optimized cycles"""
        cycle_count = 0
        while self.is_running:
            try:
                if self.analytics_service:
                    cycle_count += 1
                    # Only do full analytics every 6th cycle (30 seconds)
                    if cycle_count % 6 == 0:  
                        await self._calculate_all_analytics()
                        logger.info("🔄 Full analytics update cycle")
                    else:  
                        # Priority analytics every 5 seconds
                        await self._calculate_priority_analytics()
                        logger.debug("⚡ Priority analytics update cycle")
                else:
                    await self._calculate_basic_analytics()

                await asyncio.sleep(5)  # OPTIMIZED: 5 seconds for less frequent updates

            except Exception as e:
                logger.error(f"❌ Analytics update error: {e}")
                await asyncio.sleep(60)  # Longer error recovery time

    async def _calculate_all_analytics(self):
        """Calculate all analytics using enhanced service"""
        try:
            # Get complete analytics
            complete_analytics = self.analytics_service.get_complete_analytics()

            # Store in cache
            self.analytics_cache = complete_analytics

            # Emit individual events with proper data validation
            for feature, data in complete_analytics.items():
                if feature in ["generated_at", "cache_status", "processing_time_ms"]:
                    continue

                event_type = f"{feature}_update"
                
                # Ensure FNO data is properly included
                if feature == "intraday_stocks" and isinstance(data, dict):
                    if "fno_candidates" in data:
                        logger.info(f"📊 Broadcasting {len(data.get('fno_candidates', []))} FNO candidates")
                    if "all_candidates" in data:
                        logger.info(f"📊 Broadcasting {len(data.get('all_candidates', []))} total candidates")
                
                self.emit_event(event_type, data)

            logger.debug("📊 All analytics calculated and emitted")

        except Exception as e:
            logger.error(f"❌ Error calculating analytics: {e}")
            
    async def _calculate_priority_analytics(self):
        """Calculate priority analytics using enhanced service - faster updates"""
        try:
            # Get priority analytics for real-time critical updates
            priority_analytics = self.analytics_service.get_priority_analytics()

            # Store in cache
            self.analytics_cache.update(priority_analytics)

            # Emit individual events with high priority
            for feature, data in priority_analytics.items():
                if feature in ["generated_at", "cache_status", "processing_time_ms", "is_priority_update"]:
                    continue

                event_type = f"{feature}_update"
                
                # Mark as priority update and emit with high priority
                self.emit_event(event_type, data, priority=1 if feature in ['top_movers', 'intraday_stocks'] else 2)

            logger.debug("📊 Priority analytics calculated and emitted")

        except Exception as e:
            logger.error(f"❌ Error calculating priority analytics: {e}")
            
    async def _process_pending_events(self):
        """Process rate-limited pending events periodically"""
        logger.info("⏰ Pending event processor started")
        
        while self.is_running:
            try:
                now = datetime.now()
                events_to_process = []
                
                # Check which pending events can now be processed
                for event_type, pending in list(self.pending_events.items()):
                    rate_limit = self.event_rate_limits.get(event_type, 1.0)
                    
                    if event_type in self.last_event_time:
                        time_since_last = (now - self.last_event_time[event_type]).total_seconds()
                        if time_since_last >= rate_limit:
                            events_to_process.append(event_type)
                    else:
                        events_to_process.append(event_type)
                
                # Process pending events
                for event_type in events_to_process:
                    if event_type in self.pending_events:
                        pending = self.pending_events.pop(event_type)
                        self.emit_event(event_type, pending["data"], pending["priority"])
                        logger.debug(f"⏰ Processed pending event: {event_type}")
                
                await asyncio.sleep(1.0)  # Check pending events every second
                
            except Exception as e:
                logger.error(f"❌ Pending event processor error: {e}")
                await asyncio.sleep(5)

    # PERFORMANCE: Real-time heartbeat removed to prevent excessive analytics computation
    # async def _real_time_heartbeat(self):
    #     """DISABLED: Continuous real-time updates heartbeat was causing performance issues"""
    #     pass

    async def _calculate_basic_analytics(self):
        """Fallback basic analytics if enhanced service unavailable"""
        try:
            from services.instrument_registry import instrument_registry

            # Get all live data
            all_stocks = []
            excluded_symbols = {
                "NIFTY",
                "BANKNIFTY",
                "FINNIFTY",
                "SENSEX",
                "MIDCPNIFTY",
            }

            for symbol in instrument_registry._symbols_map:
                if symbol in excluded_symbols:
                    continue

                try:
                    price = instrument_registry.get_spot_price(symbol)
                    if price and price.get("last_price"):
                        processed_price = {
                            "symbol": symbol,
                            "last_price": safe_float(price.get("last_price")),
                            "change_percent": safe_float(price.get("change_percent")),
                            "volume": safe_float(price.get("volume")),
                            "high": safe_float(price.get("high")),
                            "low": safe_float(price.get("low")),
                            "open": safe_float(price.get("open")),
                            "close": safe_float(price.get("close")),
                        }

                        if processed_price["last_price"] > 0:
                            all_stocks.append(processed_price)

                except Exception as e:
                    logger.debug(f"Error processing {symbol}: {e}")
                    continue

            if not all_stocks:
                return

            # Calculate basic analytics
            gainers = sorted(
                [s for s in all_stocks if s.get("change_percent", 0) > 0],
                key=lambda x: x.get("change_percent", 0),
                reverse=True,
            )[:20]

            losers = sorted(
                [s for s in all_stocks if s.get("change_percent", 0) < 0],
                key=lambda x: x.get("change_percent", 0),
            )[:20]

            volume_leaders = sorted(
                all_stocks,
                key=lambda x: x.get("volume", 0),
                reverse=True,
            )[:20]

            # Calculate market sentiment
            total_stocks = len(all_stocks)
            advancing = len([s for s in all_stocks if s.get("change_percent", 0) > 0])
            declining = len([s for s in all_stocks if s.get("change_percent", 0) < 0])

            sentiment_score = (
                (advancing - declining) / total_stocks if total_stocks > 0 else 0
            )
            sentiment = (
                "bullish"
                if sentiment_score > 0.1
                else "bearish" if sentiment_score < -0.1 else "neutral"
            )

            # Emit events
            self.emit_event(
                "top_movers_update", {"gainers": gainers[:10], "losers": losers[:10]}
            )
            self.emit_event(
                "volume_analysis_update", {"volume_leaders": volume_leaders[:10]}
            )
            self.emit_event(
                "market_sentiment_update",
                {
                    "sentiment": sentiment,
                    "sentiment_score": sentiment_score,
                    "advancing": advancing,
                    "declining": declining,
                    "total": total_stocks,
                },
            )

        except Exception as e:
            logger.error(f"❌ Basic analytics calculation error: {e}")

    # ===== CACHE MANAGEMENT =====
    async def _update_cache_for_event(self, event: Dict[str, Any]):
        """Update relevant caches based on event type"""
        try:
            event_type = event["type"]
            data = event["data"]

            if event_type == "price_update":
                if isinstance(data, dict):
                    self.live_prices.update(data)
            elif event_type.endswith("_update"):
                feature_name = event_type.replace("_update", "")
                self.analytics_cache[feature_name] = data

        except Exception as e:
            logger.error(f"❌ Cache update error: {e}")

    # ===== BROADCASTING =====
    async def _broadcast_event(self, event: Dict[str, Any]):
        """Broadcast event to subscribed clients"""
        event_type = event["type"]
        clients_to_notify = []

        for client_id, subscriptions in self.client_subscriptions.items():
            if event_type in subscriptions or "all" in subscriptions:
                clients_to_notify.append(client_id)

        # Send to all subscribed clients
        if clients_to_notify:
            await asyncio.gather(
                *[
                    self.send_to_client(client_id, event)
                    for client_id in clients_to_notify
                ],
                return_exceptions=True,
            )

    async def send_to_client(self, client_id: str, data: Dict[str, Any]) -> bool:
        """Send data to a specific client with improved error handling"""
        if client_id not in self.connections:
            logger.warning(f"⚠️ Client {client_id} not found in connections")
            return False

        websocket = self.connections[client_id]

        try:
            # FIXED: Explicitly check the WebSocket state before sending
            if websocket.client_state != WebSocketState.CONNECTED:
                logger.warning(
                    f"⚠️ WebSocket for {client_id} is not connected (state: {websocket.client_state})"
                )
                return False

            # FIXED: Send message with error handling
            await websocket.send_json(data)
            return True
        except RuntimeError as e:
            if "not connected" in str(e).lower():
                logger.warning(f"⚠️ WebSocket for {client_id} is not connected: {e}")
            else:
                logger.error(f"❌ Runtime error sending to {client_id}: {e}")
            await self.remove_client(client_id)
        except Exception as e:
            logger.error(f"❌ Failed to send to client {client_id}: {e}")
            await self.remove_client(client_id)

        return False

    async def _send_initial_data(self, client_id: str, client_type: str):
        """Send initial data based on client type with improved error handling"""
        if client_id not in self.connections:
            logger.warning(f"⚠️ Cannot send initial data: Client {client_id} not found")
            return

        websocket = self.connections[client_id]

        try:
            # Check WebSocket state before attempting to send
            if websocket.client_state != WebSocketState.CONNECTED:
                logger.warning(
                    f"⚠️ Cannot send initial data to {client_id}: WebSocket not connected"
                )
                return

            # First, try to get analytics data from the enhanced service
            try:
                from services.enhanced_market_analytics import enhanced_analytics

                analytics_data = enhanced_analytics.get_complete_analytics()

                # Send directly to WebSocket
                if isinstance(analytics_data, dict) and analytics_data:
                    await websocket.send_json(
                        {
                            "type": "initial_data",
                            "data": analytics_data,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                    logger.info(f"📊 Sent initial analytics to {client_id}")
            except Exception as e:
                logger.error(f"❌ Error getting initial analytics: {e}")

                # Fall back to cached analytics
                if self.analytics_cache:
                    try:
                        await websocket.send_json(
                            {
                                "type": "analytics_data",
                                "data": self.analytics_cache,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                        logger.info(f"📊 Sent cached analytics to {client_id}")
                    except Exception as e:
                        logger.error(f"❌ Error sending cached analytics: {e}")

            # Send live prices if available
            if self.live_prices:
                try:
                    await websocket.send_json(
                        {
                            "type": "live_prices",
                            "data": self.live_prices,
                            "count": len(self.live_prices),
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                    logger.info(
                        f"📊 Sent live prices to {client_id} ({len(self.live_prices)} instruments)"
                    )
                except Exception as e:
                    logger.error(f"❌ Error sending live prices: {e}")
        except Exception as e:
            logger.error(f"❌ Error in _send_initial_data for {client_id}: {e}")

    # ===== PUBLIC API =====
    def get_available_events(self) -> List[str]:
        """Get list of available event types"""
        return [
            "price_update",
            "dashboard_update",
            "index_update", 
            "top_movers_update",
            "volume_analysis_update",
            "gap_analysis_update",
            "breakout_analysis_update",
            "market_sentiment_update",
            "heatmap_update",
            "intraday_stocks_update",
            "record_movers_update",
            "options_chain_update",
            "market_status_update",
            "live_prices_enriched",
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get system status with trading safety metrics"""
        queue_size = self.event_queue.qsize()
        queue_percentage = (queue_size / self.event_queue.maxsize) * 100
        
        return {
            "is_running": self.is_running,
            "total_connections": len(self.connections),
            "client_types": dict(
                defaultdict(
                    int,
                    {
                        ct: sum(1 for t in self.client_types.values() if t == ct)
                        for ct in set(self.client_types.values())
                    },
                )
            ),
            "cached_analytics": list(self.analytics_cache.keys()),
            "live_prices_count": len(self.live_prices),
            "event_queue_size": queue_size,
            "event_queue_percentage": round(queue_percentage, 1),
            "queue_status": "CRITICAL" if queue_percentage > 80 else "WARNING" if queue_percentage > 60 else "OK",
            "background_tasks": len(self.background_tasks),
            "analytics_service_available": self.analytics_service is not None,
            # TRADING SAFETY METRICS
            "trading_mode": self.trading_mode,
            "emergency_mode": self.emergency_mode,
            "pending_events_count": len(self.pending_events),
            "rate_limits": self.event_rate_limits,
        }
    
    def enable_emergency_mode(self):
        """Enable emergency mode to bypass rate limiting during high volatility"""
        self.emergency_mode = True
        logger.warning("🚨 EMERGENCY MODE ENABLED - Rate limiting bypassed for all events")
        
    def disable_emergency_mode(self):
        """Disable emergency mode to restore normal rate limiting"""
        self.emergency_mode = False  
        logger.info("✅ EMERGENCY MODE DISABLED - Normal rate limiting restored")
        
    def adjust_rate_limits(self, new_limits: Dict[str, float]):
        """Dynamically adjust rate limits for different market conditions"""
        self.event_rate_limits.update(new_limits)
        logger.info(f"⚙️ Rate limits adjusted: {new_limits}")


# Singleton instance
unified_manager = UnifiedWebSocketManager()


# Integration with existing systems
def integrate_with_centralized_manager():
    """Integrate with existing centralized manager"""
    try:
        from services.centralized_ws_manager import centralized_manager

        # Register callback to forward price updates with immediate analytics
        def price_update_callback(data):
            try:
                price_data = data.get("data", {})
                if price_data:
                    # Emit price update with highest priority
                    unified_manager.emit_event("price_update", price_data, priority=1)
                    
                    # Also forward as dashboard_update for broader compatibility
                    unified_manager.emit_event("dashboard_update", {
                        "type": "dashboard_update",
                        "data": price_data,
                        "market_open": data.get("market_open", True),
                        "timestamp": data.get("timestamp", datetime.now().isoformat())
                    }, priority=1)
                    
                    # PERFORMANCE: Removed immediate analytics to prevent feedback loops
                    # Analytics will be updated by the scheduled task with proper caching
                    
            except Exception as e:
                logger.error(f"❌ Error in real-time price update callback: {e}")

        centralized_manager.register_callback("price_update", price_update_callback)
        logger.info("✅ Integrated with centralized manager")

    except ImportError:
        logger.warning("⚠️ Centralized manager not available")
    except Exception as e:
        logger.error(f"❌ Integration error: {e}")


# Convenience functions
async def start_unified_websocket():
    """Start the unified WebSocket system"""
    try:
        await unified_manager.start()
        integrate_with_centralized_manager()
        logger.info("✅ Unified WebSocket system started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to start unified WebSocket: {e}")


async def stop_unified_websocket():
    """Stop the unified WebSocket system"""
    try:
        await unified_manager.stop()
        logger.info("✅ Unified WebSocket system stopped")
    except Exception as e:
        logger.error(f"❌ Error stopping unified WebSocket: {e}")


def emit_market_event(event_type: str, data: Dict[str, Any]):
    """Emit a market event"""
    try:
        unified_manager.emit_event(event_type, data)
    except Exception as e:
        logger.error(f"❌ Error emitting event {event_type}: {e}")


# Add this method to the UnifiedWebSocketManager class in unified_websocket_manager.py
