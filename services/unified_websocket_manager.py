# # services/unified_websocket_manager.py - WORKING VERSION
# """
# 🚀 Unified Event-Driven WebSocket Manager

# This service provides:
# - Real-time price updates with percentage calculations
# - Market analytics and dashboard updates
# - Optimized event broadcasting
# - Enhanced error handling and reconnection

# Key features:
# - Ultra-fast price update processing
# - Automatic percentage change calculations
# - Event prioritization and queuing
# - Connection lifecycle management
# """
# import asyncio
# import json
# import logging
# from datetime import datetime, timezone
# from typing import Dict, List, Set, Any, Callable, Optional
# from fastapi import WebSocket
# from fastapi.websockets import WebSocketState
# from collections import defaultdict
# import uuid


# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
# )

# logger = logging.getLogger(__name__)


# def safe_float(value, default=0.0):
#     """Safely convert a value to float"""
#     try:
#         if value is None or value == "":
#             return default
#         if isinstance(value, bool):
#             return float(value)
#         return float(value)
#     except (ValueError, TypeError):
#         logger.debug(f"Invalid float value: {value}, using default {default}")
#         return default


# def safe_int(value, default=0):
#     """Safely convert a value to int"""
#     try:
#         if value is None or value == "":
#             return default
#         if isinstance(value, bool):
#             return int(value)
#         return int(value)
#     except (ValueError, TypeError):
#         logger.debug(f"Invalid int value: {value}, using default {default}")
#         return default


# class UnifiedWebSocketManager:
#     """
#     FIXED: Single WebSocket manager for ALL features using event-driven architecture
#     """

#     def __init__(self):
#         # Connection management
#         self.connections: Dict[str, WebSocket] = {}
#         self.client_subscriptions: Dict[str, Set[str]] = {}
#         self.client_types: Dict[str, str] = {}
#         self.is_active: bool = True  # Manager status

#         # Event system
#         self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
#         self.event_queue = asyncio.Queue(
#             maxsize=50000
#         )  # 🚀 CRITICAL FIX: Much larger queue for high-frequency Real-Time Analytics

#         # 🚀 CRITICAL FIX: Faster rate limiting for Real-Time Analytics Engine
#         self.last_event_time = {}
#         self.event_rate_limits = {
#             "price_update": 0.001,  # 1000 updates/sec for Real-Time Analytics
#             "dashboard_update": 0.002,  # 500 updates/sec for dashboard efficiency
#             "live_prices_enriched": 0.001,  # 1000 updates/sec for enriched data
#             "index_update": 0.01,  # 100 updates/sec for indices
#             "top_movers_update": 0.5,  # 2 updates/sec for analytics
#             "intraday_stocks_update": 0.5,  # 2 updates/sec for stock screening
#             "market_sentiment_update": 1.0,  # 1 update/sec for sentiment
#             "indices_data_update": 0.5,  # 2 updates/sec for index data
#             "volume_analysis_update": 1.0,  # 1 update/sec for volume analysis
#             "analytics_update": 2.0,  # 1 update every 2 seconds for complex analytics
#             "gap_signals_update": 0.1,  # 10 updates/sec for gap signals
#             "breakout_signals_update": 0.1,  # 10 updates/sec for breakout signals
#         }

#         # SAFETY: Trading mode configuration
#         self.trading_mode = True  # Enable stricter limits for trading
#         self.emergency_mode = False  # Bypass rate limiting in extreme volatility
#         self.pending_events = {}  # For deduplication

#         # Feature-specific data caches
#         self.live_prices = {}
#         self.analytics_cache = {}
#         self.heatmap_cache = {}
#         self.movers_cache = {}

#         # Background tasks
#         self.background_tasks = set()
#         self.is_running = False

#         # Initialize optimized service for real-time price processing only
#         # Analytics are handled by routes on-demand
#         self.optimized_service = None
#         self._init_optimized_service()

#     def _init_optimized_service(self):
#         """Initialize optimized service for real-time price processing only"""
#         try:
#             from services.optimized_market_data_service import optimized_market_service

#             self.optimized_service = optimized_market_service
#             logger.info(
#                 "✅ Optimized service initialized for real-time price processing"
#             )
#         except ImportError as e:
#             logger.warning(
#                 f"⚠️ Optimized service not available for price processing: {e}"
#             )
#             self.optimized_service = None

#     # CRITICAL FIX: Add register_handler method INSIDE the class
#     def register_handler(self, event_type: str, handler_func):
#         """Register a handler function for a specific event type"""
#         if not hasattr(self, "_event_handlers"):
#             self._event_handlers = defaultdict(list)

#         self._event_handlers[event_type].append(handler_func)
#         logger.info(f"✅ Registered handler for {event_type} events")
#         return True

#     async def start(self):
#         """Start the unified WebSocket system"""
#         if self.is_running:
#             return

#         self.is_running = True
#         self.is_active = True  # Set active state when starting

#         # Start event processor
#         processor_task = asyncio.create_task(self._process_events())
#         self.background_tasks.add(processor_task)
#         processor_task.add_done_callback(lambda t: self.background_tasks.discard(t))

#         # No analytics processing in manager - handled by routes on-demand

#         # Start pending event processor
#         pending_task = asyncio.create_task(self._process_pending_events())
#         self.background_tasks.add(pending_task)
#         pending_task.add_done_callback(lambda t: self.background_tasks.discard(t))
#         logger.info("🚀 Unified WebSocket Manager started")

#     async def stop(self):
#         """Stop the unified WebSocket system"""
#         self.is_running = False
#         self.is_active = False  # Set inactive state when stopping

#         # Cancel all background tasks
#         for task in self.background_tasks:
#             if not task.done():
#                 task.cancel()

#         # Wait for tasks to complete
#         if self.background_tasks:
#             await asyncio.gather(*self.background_tasks, return_exceptions=True)

#         # Close all connections
#         for client_id, ws in list(self.connections.items()):
#             try:
#                 if ws.client_state == WebSocketState.CONNECTED:
#                     await ws.close()
#             except Exception as e:
#                 logger.debug(f"Error closing connection {client_id}: {e}")

#         self.connections.clear()
#         logger.info("🛑 Unified WebSocket Manager stopped")

#     # ===== CONNECTION MANAGEMENT =====
#     async def add_client(
#         self, websocket: WebSocket, client_type: str = "dashboard"
#     ) -> str:
#         """Add a new WebSocket client"""
#         try:
#             # FIXED: Accept the WebSocket connection FIRST
#             await websocket.accept()
#             logger.info("🔌 WebSocket connection accepted")

#             client_id = f"{client_type}_{uuid.uuid4().hex[:8]}"

#             self.connections[client_id] = websocket
#             self.client_types[client_id] = client_type
#             self.client_subscriptions[client_id] = set()

#             # Ensure event processor is running when first client connects
#             if len(self.connections) == 1 and self.is_running:
#                 try:
#                     # Start event processor if not already running
#                     if not any(
#                         task for task in self.background_tasks if not task.done()
#                     ):
#                         task = asyncio.create_task(self._process_events())
#                         self.background_tasks.add(task)
#                         logger.info(
#                             "🔄 Started event processor for new client connection"
#                         )
#                 except Exception as e:
#                     logger.error(f"❌ Error starting event processor: {e}")

#             # Send welcome message directly via WebSocket
#             try:
#                 await websocket.send_json(
#                     {
#                         "type": "connection_established",
#                         "client_id": client_id,
#                         "client_type": client_type,
#                         "available_events": self.get_available_events(),
#                         "timestamp": datetime.now().isoformat(),
#                     }
#                 )
#             except Exception as e:
#                 logger.error(f"❌ Error sending welcome message: {e}")
#                 # Continue anyway - connection is established

#             # Send initial data
#             await self._send_initial_data(client_id, client_type)

#             logger.info(f"🔌 Client connected: {client_id} ({client_type})")
#             return client_id

#         except Exception as e:
#             logger.error(f"❌ Error adding client: {e}")
#             # Try to close WebSocket if there was an error
#             try:
#                 await websocket.close(code=1011, reason=f"Error during setup: {str(e)}")
#             except Exception:
#                 pass
#             raise

#     async def remove_client(self, client_id: str):
#         """Remove a WebSocket client"""
#         if client_id in self.connections:
#             try:
#                 ws = self.connections[client_id]
#                 if ws.client_state == WebSocketState.CONNECTED:
#                     await ws.close()
#             except Exception as e:
#                 logger.debug(f"Error closing WebSocket for {client_id}: {e}")

#             # Clean up
#             self.connections.pop(client_id, None)
#             self.client_types.pop(client_id, None)
#             self.client_subscriptions.pop(client_id, None)

#             logger.info(f"🔌 Client disconnected: {client_id}")

#     # ===== EVENT SYSTEM =====
#     def subscribe_to_events(self, client_id: str, events: List[str]):
#         """Subscribe client to specific events with deduplication"""
#         if client_id in self.client_subscriptions:
#             # Check if already subscribed to prevent spam
#             existing_events = self.client_subscriptions[client_id]
#             new_events = set(events) - existing_events

#             if new_events:
#                 existing_events.update(new_events)
#                 logger.info(
#                     f"📡 Client {client_id} subscribed to {len(new_events)} new events (total: {len(existing_events)})"
#                 )
#             else:
#                 logger.debug(
#                     f"📡 Client {client_id} already subscribed to all requested events"
#                 )
#         else:
#             # First time subscription
#             self.client_subscriptions[client_id] = set(events)
#             logger.info(
#                 f"📡 Client {client_id} subscribed to {len(events)} events (first time)"
#             )

#     async def emit_realtime_price(self, enriched_tick: Dict[str, Any]):
#         """
#         🚀 ULTRA-FAST: Direct real-time price broadcast bypassing queue
#         For maximum speed price updates (<1ms latency)
#         """
#         if not enriched_tick or not self.connections:
#             return

#         try:
#             # Create optimized price update message
#             price_message = {
#                 "type": "price_update",
#                 "data": enriched_tick,
#                 "timestamp": datetime.now().isoformat(),
#                 "realtime": True,
#             }

#             # Broadcast directly to all connected clients (bypass queue)
#             message_str = json.dumps(price_message, default=str)

#             # Send to all clients concurrently for maximum speed
#             tasks = []
#             for client_id, websocket in list(self.connections.items()):
#                 if websocket.client_state == WebSocketState.CONNECTED:
#                     tasks.append(
#                         self._send_direct_message(client_id, websocket, message_str)
#                     )

#             if tasks:
#                 # Execute all sends concurrently for minimum latency
#                 await asyncio.gather(*tasks, return_exceptions=True)

#         except Exception as e:
#             logger.error(f"❌ Real-time price broadcast error: {e}")

#     async def emit_direct_price_batch(self, price_batch: Dict[str, Dict[str, Any]]):
#         """
#         🚀 ULTRA-FAST: Direct batch price broadcast to ALL UI sections
#         Bypasses all queues and analytics processing for maximum speed
#         Ensures proper population across Dashboard, Trading, Analytics sections
#         """
#         if not price_batch or not self.connections:
#             return

#         try:
#             timestamp = datetime.now().isoformat()

#             # 🚀 SECTION 1: Individual price updates for Zustand store (ultra-fast component updates)
#             individual_price_messages = []
#             for instrument_key, price_data in price_batch.items():
#                 if price_data and price_data.get("ltp"):
#                     individual_message = {
#                         "type": "price_update",
#                         "data": price_data,  # Single price for Zustand
#                         "timestamp": timestamp,
#                         "realtime": True,
#                         "direct_feed": True,
#                     }
#                     individual_price_messages.append(individual_message)

#             # 🚀 SECTION 2: Batch update for legacy components (Dashboard overview)
#             batch_price_message = {
#                 "type": "price_update",
#                 "data": price_batch,  # Full batch for legacy hook
#                 "timestamp": timestamp,
#                 "count": len(price_batch),
#                 "direct_feed": True,
#                 "realtime": True,
#                 "batch_update": True,
#             }

#             # 🚀 SECTION 3: Dashboard update for analytics sections
#             dashboard_message = {
#                 "type": "dashboard_update",
#                 "data": price_batch,
#                 "timestamp": timestamp,
#                 "count": len(price_batch),
#                 "source": "direct_feed",
#                 "market_open": True,
#                 "update_sections": ["overview", "movers", "sectors", "analytics"],
#             }

#             # 🚀 SECTION 4: Enhanced format for Trading components
#             trading_message = {
#                 "type": "live_prices_enriched",
#                 "data": price_batch,
#                 "timestamp": timestamp,
#                 "count": len(price_batch),
#                 "enriched": True,
#                 "direct_feed": True,
#                 "trading_ready": True,
#             }

#             # 🚀 SECTION 5: Indices extraction for index tracking
#             indices_data = {}
#             stocks_data = {}

#             for instrument_key, price_data in price_batch.items():
#                 if any(
#                     idx in instrument_key.upper()
#                     for idx in [
#                         "NIFTY",
#                         "SENSEX",
#                         "BANKEX",
#                         "INDEX",
#                         "FINNIFTY",
#                         "MIDCPNIFTY",
#                     ]
#                 ):
#                     indices_data[instrument_key] = price_data
#                 else:
#                     stocks_data[instrument_key] = price_data

#             # Send indices update if we have index data
#             indices_message = None
#             if indices_data:
#                 indices_message = {
#                     "type": "index_update",
#                     "data": indices_data,
#                     "timestamp": timestamp,
#                     "count": len(indices_data),
#                     "direct_feed": True,
#                 }

#             # Convert all messages to JSON for efficiency
#             messages_to_send = []

#             # Add batch message (most important - processed by useUnifiedMarketData)
#             messages_to_send.append(json.dumps(batch_price_message, default=str))

#             # Add dashboard message (for analytics sections)
#             messages_to_send.append(json.dumps(dashboard_message, default=str))

#             # Add trading message (for trading components)
#             messages_to_send.append(json.dumps(trading_message, default=str))

#             # Add indices message if available
#             if indices_message:
#                 messages_to_send.append(json.dumps(indices_message, default=str))

#             # 🚀 ULTRA-FAST BROADCAST: Send all message types to all clients
#             tasks = []
#             for client_id, websocket in list(self.connections.items()):
#                 if websocket.client_state == WebSocketState.CONNECTED:
#                     # Send all critical messages concurrently
#                     for message_str in messages_to_send:
#                         tasks.append(
#                             self._send_direct_message(client_id, websocket, message_str)
#                         )

#             if tasks:
#                 # Execute all sends concurrently for minimum latency
#                 results = await asyncio.gather(*tasks, return_exceptions=True)
#                 successful = sum(1 for r in results if r is True)
#                 total_messages = len(messages_to_send) * len(self.connections)

#                 logger.debug(
#                     f"⚡ COMPREHENSIVE BROADCAST: {len(price_batch)} prices → {len(self.connections)} clients"
#                 )
#                 logger.debug(
#                     f"⚡ Messages sent: {len(messages_to_send)} types × {len(self.connections)} clients = {total_messages} total"
#                 )
#                 logger.debug(f"⚡ Success rate: {successful}/{len(tasks)} sends OK")

#                 # Log section coverage
#                 sections_covered = [
#                     "Zustand_Store",
#                     "Dashboard",
#                     "Trading",
#                     "Analytics",
#                 ]
#                 if indices_data:
#                     sections_covered.append("Indices")

#                 logger.info(
#                     f"🎯 REAL-TIME COVERAGE: {', '.join(sections_covered)} sections updated with {len(price_batch)} instruments"
#                 )

#         except Exception as e:
#             logger.error(f"❌ Direct batch price broadcast error: {e}")

#     async def _send_direct_message(
#         self, client_id: str, websocket: WebSocket, message: str
#     ):
#         """Send message directly to WebSocket client with proper state checking"""
#         try:
#             # Check WebSocket state before sending
#             if hasattr(websocket, "client_state"):
#                 if websocket.client_state in [
#                     WebSocketState.DISCONNECTED,
#                     WebSocketState.CLOSED,
#                 ]:
#                     logger.debug(f"🔌 Skipping send to disconnected client {client_id}")
#                     await self.remove_client(client_id)
#                     return False

#             # Check connection state using application_state
#             if hasattr(websocket, "application_state"):
#                 if websocket.application_state in [
#                     WebSocketState.DISCONNECTED,
#                     WebSocketState.CLOSED,
#                 ]:
#                     logger.debug(f"🔌 Skipping send to closed client {client_id}")
#                     await self.remove_client(client_id)
#                     return False

#             await websocket.send_text(message)
#             return True

#         except RuntimeError as e:
#             if "close message has been sent" in str(e) or "Connection is closed" in str(
#                 e
#             ):
#                 logger.debug(f"🔌 Client {client_id} connection already closed")
#             else:
#                 logger.error(f"❌ Runtime error sending to {client_id}: {e}")
#             await self.remove_client(client_id)
#         except Exception as e:
#             logger.error(f"❌ Failed to send to client {client_id}: {e}")
#             await self.remove_client(client_id)

#         return False

#     async def emit_to_all(self, event: str, data: Dict[str, Any]):
#         """Enhanced emit with circuit breaker integration"""
#         if not self.connections:
#             # Update circuit breaker about lack of connections
#             try:
#                 from services.circuit_breaker import circuit_breaker

#                 await circuit_breaker.update_system_health(
#                     {"websocket_connected": False, "api_failure": True}
#                 )
#             except ImportError:
#                 pass
#             return

#         try:
#             message = {
#                 "type": event,
#                 "data": data,
#                 "timestamp": datetime.now().isoformat(),
#                 "sequence_number": getattr(self, "_seq_num", 0),
#             }

#             # Increment sequence number for message ordering
#             self._seq_num = getattr(self, "_seq_num", 0) + 1

#             disconnected_clients = []
#             successful_sends = 0

#             # Create a copy of connections to avoid modification during iteration
#             connections_copy = list(self.connections.items())

#             for client_id, websocket in connections_copy:
#                 try:
#                     # Check WebSocket state before sending
#                     is_connected = True

#                     if hasattr(websocket, "client_state"):
#                         if websocket.client_state in [
#                             WebSocketState.DISCONNECTED,
#                             WebSocketState.CLOSED,
#                         ]:
#                             is_connected = False

#                     if hasattr(websocket, "application_state") and is_connected:
#                         if websocket.application_state in [
#                             WebSocketState.DISCONNECTED,
#                             WebSocketState.CLOSED,
#                         ]:
#                             is_connected = False

#                     if not is_connected:
#                         logger.debug(
#                             f"🔌 Skipping broadcast to disconnected client {client_id}"
#                         )
#                         disconnected_clients.append(client_id)
#                         continue

#                     await websocket.send_text(json.dumps(message))
#                     successful_sends += 1

#                 except RuntimeError as e:
#                     if "close message has been sent" in str(
#                         e
#                     ) or "Connection is closed" in str(e):
#                         logger.debug(
#                             f"🔌 Client {client_id} connection already closed during broadcast"
#                         )
#                     else:
#                         logger.warning(f"Failed to send to client {client_id}: {e}")
#                     disconnected_clients.append(client_id)
#                 except Exception as e:
#                     logger.warning(f"Failed to send to client {client_id}: {e}")
#                     disconnected_clients.append(client_id)

#             # Clean up disconnected clients
#             for client_id in disconnected_clients:
#                 self.connections.pop(client_id, None)

#             # Update circuit breaker with connection health
#             connection_health = successful_sends > 0
#             try:
#                 from services.circuit_breaker import circuit_breaker

#                 await circuit_breaker.update_system_health(
#                     {
#                         "websocket_connected": connection_health,
#                         "last_price_update": (
#                             datetime.now(timezone.utc)
#                             if event == "price_update"
#                             else None
#                         ),
#                         "api_success": True,
#                     }
#                 )
#             except ImportError:
#                 pass

#         except Exception as e:
#             logger.error(f"❌ Error emitting to all clients: {e}")
#             # Notify circuit breaker of system failure
#             try:
#                 from services.circuit_breaker import circuit_breaker

#                 await circuit_breaker.update_system_health(
#                     {"websocket_connected": False, "api_failure": True}
#                 )
#             except ImportError:
#                 pass

#     def emit_event(self, event_type: str, data: Dict[str, Any], priority: int = 5):
#         """Emit an event to the queue with optimized rate limiting for stability (1=highest, 10=lowest)"""

#         now = datetime.now()

#         # 🚨 CRITICAL: NEVER rate limit live market data events - must be sent immediately
#         if event_type in ["live_price_update", "market_data_update"]:
#             priority = -1  # Ultimate priority for live market data
#             logger.debug(f"⚡ INSTANT {event_type} bypass rate limits")
#         # Check rate limiting for other events unless in emergency mode
#         elif not self.emergency_mode and event_type in self.event_rate_limits:
#             rate_limit = self.event_rate_limits[event_type]

#             if rate_limit > 0 and event_type in self.last_event_time:
#                 time_since_last = (
#                     now - self.last_event_time[event_type]
#                 ).total_seconds()
#                 if time_since_last < rate_limit:
#                     # Rate limited - add to pending instead of dropping
#                     self.pending_events[event_type] = {
#                         "data": data,
#                         "priority": priority,
#                         "timestamp": now,
#                     }
#                     logger.debug(
#                         f"⏱️ Rate limited {event_type}, adding to pending (last: {time_since_last:.3f}s, limit: {rate_limit}s)"
#                     )
#                     return

#         logger.debug(f"✅ Processing {event_type} (priority: {priority})")
#         self.last_event_time[event_type] = now

#         # ⚡ ULTRA-FAST: Skip all pending event processing for maximum speed
#         # Process any pending event of this type - DISABLED for zero delay
#         # if event_type in self.pending_events:
#         #     pending = self.pending_events.pop(event_type)
#         #     data = pending["data"]
#         #     priority = pending["priority"]

#         # 🚨 ULTIMATE PRIORITY: live market data events must be sent first
#         if event_type in ["live_price_update", "market_data_update"]:
#             priority = -1  # Ultimate priority - bypasses everything
#         # ⚡ ULTRA-FAST: Use priority 1 for other critical trading events
#         elif event_type in [
#             "price_update",
#             "dashboard_update",
#             "live_prices_enriched",
#             "index_update",
#             "top_movers_update",
#             "intraday_stocks_update",
#             "indices_data_update",
#         ]:
#             priority = 1  # Highest priority for all market data

#         # Determine priority based on event type and data content
#         if not isinstance(priority, int):
#             priority = self._determine_event_priority(event_type, data)

#         # PERFORMANCE: Normalize event type to prevent typos
#         normalized_event_type = self._normalize_event_type(event_type)

#         event = {
#             "type": normalized_event_type,
#             "data": data,
#             "timestamp": now.isoformat(),
#             "priority": priority,
#         }

#         # 🚨 CRITICAL: BYPASS QUEUE for live market data events - send immediately
#         if normalized_event_type in ["live_price_update", "market_data_update"]:
#             logger.info(
#                 f"⚡⚡⚡ BYPASSING QUEUE for {normalized_event_type} - INSTANT BROADCAST"
#             )
#             # Send immediately without queuing
#             asyncio.create_task(self._broadcast_event(event))
#             return

#         try:
#             self.event_queue.put_nowait(event)

#             # 🚀 QUEUE MONITORING: Check queue health periodically
#             if self.event_queue.qsize() % 1000 == 0:  # Check every 1000 events
#                 self.monitor_queue_health()

#             # 🚀 ENHANCED LOGGING: Track critical events with zero delay confirmation
#             if normalized_event_type in [
#                 "price_update",
#                 "dashboard_update",
#                 "live_prices_enriched",
#                 "index_update",
#                 # NOTE: live market data events bypass queue entirely, so not logged here
#             ]:
#                 data_size = 0
#                 if isinstance(data, dict):
#                     data_size = len(data)
#                 elif isinstance(data, list):
#                     data_size = len(data)
#                 logger.info(
#                     f"⚡ ZERO-DELAY queued {normalized_event_type} (priority: {priority}, data: {data_size} items, queue: {self.event_queue.qsize()})"
#                 )
#             else:
#                 logger.debug(
#                     f"✅ Queued {normalized_event_type} (priority: {priority})"
#                 )
#         except asyncio.QueueFull:
#             # ✅ IMPROVED: Enhanced queue management with priority-based dropping
#             current_queue_size = self.event_queue.qsize()
#             logger.warning(
#                 f"🚨 Queue full ({current_queue_size}/{self.event_queue.maxsize}) for event: {normalized_event_type}"
#             )

#             if priority <= 1:  # Critical trading data (live prices, urgent updates)
#                 logger.warning(
#                     f"🚨 FORCE-QUEUING critical trading event: {normalized_event_type}"
#                 )
#                 try:
#                     # 🚀 CRITICAL FIX: More aggressive queue clearing for Real-Time Analytics
#                     cleared_events = 0
#                     attempts = 0
#                     max_attempts = 50  # More attempts for critical trading data

#                     while attempts < max_attempts and cleared_events < 100:
#                         try:
#                             dropped_event = self.event_queue.get_nowait()
#                             dropped_priority = dropped_event.get("priority", 5)
#                             dropped_type = dropped_event.get("type", "unknown")

#                             # More aggressive: drop any event with priority >= 2 for critical events
#                             if dropped_priority >= 2 or dropped_type in [
#                                 "real_time_analytics_update",
#                                 "market_sentiment_update",
#                             ]:
#                                 cleared_events += 1
#                                 logger.debug(
#                                     f"🗑️ Cleared {dropped_type} (priority {dropped_priority}) for critical {normalized_event_type}"
#                                 )
#                                 # Don't put it back - just drop it
#                             else:
#                                 # Only keep highest priority events (priority 1)
#                                 self.event_queue.put_nowait(dropped_event)
#                                 attempts += 1
#                         except asyncio.QueueEmpty:
#                             # Successfully cleared space
#                             break
#                         except asyncio.QueueFull:
#                             attempts += 1

#                     # Try to add our critical event
#                     try:
#                         self.event_queue.put_nowait(event)
#                         logger.info(
#                             f"✅ Successfully queued critical {normalized_event_type} after clearing {cleared_events} events"
#                         )
#                     except asyncio.QueueFull:
#                         logger.error(
#                             f"❌ Failed to queue critical event {normalized_event_type} after clearing {cleared_events} events"
#                         )

#                 except Exception as e:
#                     logger.error(
#                         f"❌ Error managing queue for critical event {normalized_event_type}: {e}"
#                     )
#             else:
#                 # Non-critical event - just drop it
#                 logger.debug(
#                     f"⚠️ Dropping non-critical event {normalized_event_type} (priority {priority}) due to full queue"
#                 )

#     def _normalize_event_type(self, event_type: str) -> str:
#         """Normalize event types to prevent duplicates from typos"""
#         # Fix common typos seen in logs
#         fixes = {
#             "price_upddate": "price_update",
#             "pprice_update": "price_update",
#             "dashboardd_update": "dashboard_update",
#             "ddashboard_update": "dashboard_update",
#             "top_moverrs_update": "top_movers_update",
#             "ttop_movers_update": "top_movers_update",
#             "intraday__stocks_update": "intraday_stocks_update",
#             "iintraday_stocks_update": "intraday_stocks_update",
#             "market_seentiment_update": "market_sentiment_update",
#             "mmarket_sentiment_update": "market_sentiment_update",
#             "indices_ddata_update": "indices_data_update",
#             "iindices_data_update": "indices_data_update",
#         }

#         return fixes.get(event_type, event_type)

#     def _determine_event_priority(self, event_type: str, data: Dict[str, Any]) -> int:
#         """Determine event priority based on type and content (1=highest, 10=lowest)"""

#         # Indices data - highest priority
#         if "indices" in event_type.lower() or event_type in ["market_status_update"]:
#             return 1

#         # FNO stocks data - high priority
#         if (
#             "fno" in event_type.lower()
#             or (isinstance(data, dict) and data.get("fno_candidates"))
#             or self._contains_fno_symbols(data)
#         ):
#             return 2

#         # Price updates and dashboard data - high priority
#         if event_type in ["price_update", "dashboard_update", "live_prices_update"]:
#             return 2

#         # Top movers and volume analysis - medium-high priority
#         if event_type in ["top_movers_update", "intraday_stocks_update"]:
#             return 3

#         # Market sentiment - medium priority
#         if "sentiment" in event_type.lower():
#             return 4

#         # Analytics and other updates - lower priority
#         if "analytics" in event_type.lower():
#             return 6

#         # Default priority
#         return 5

#     def _contains_fno_symbols(self, data: Dict[str, Any]) -> bool:
#         """Check if data contains FNO symbols"""
#         try:
#             fno_symbols = {
#                 "RELIANCE",
#                 "TCS",
#                 "HDFCBANK",
#                 "ICICIBANK",
#                 "INFY",
#                 "SBIN",
#                 "WIPRO",
#                 "MARUTI",
#                 "HINDUNILVR",
#                 "ITC",
#                 "BAJFINANCE",
#             }

#             if isinstance(data, dict):
#                 # Check various data structures for FNO symbols
#                 for value in data.values():
#                     if isinstance(value, str) and value.upper() in fno_symbols:
#                         return True
#                     elif isinstance(value, list):
#                         for item in value:
#                             if (
#                                 isinstance(item, dict)
#                                 and item.get("symbol", "").upper() in fno_symbols
#                             ):
#                                 return True
#                             elif isinstance(item, str) and item.upper() in fno_symbols:
#                                 return True

#             return False
#         except:
#             return False

#     async def _process_events(self):
#         """Process events from the queue with improved error handling"""
#         logger.info("🔄 Event processor started")
#         processed_count = 0

#         while self.is_running:
#             try:
#                 # Check if we're still supposed to be running
#                 if not self.is_running:
#                     logger.info("🛑 Event processor stopping - is_running=False")
#                     break

#                 event = await asyncio.wait_for(
#                     self.event_queue.get(), timeout=0.1
#                 )  # ✅ IMPROVED: Balanced timeout to prevent CPU spinning while maintaining responsiveness
#                 processed_count += 1

#                 if (
#                     processed_count % 50 == 0
#                 ):  # OPTIMIZED: More frequent logging for monitoring
#                     logger.info(
#                         f"🔄 Processed {processed_count} events, queue size: {self.event_queue.qsize()}"
#                     )

#                 # No analytics processing in manager - analytics handled by routes

#                 # Process regular event - REMOVED immediate analytics to prevent feedback loops
#                 event_type = event.get("type", "")

#                 # PERFORMANCE: Removed immediate analytics trigger to prevent excessive computation
#                 # Analytics are now handled by separate scheduled updates with proper caching

#                 await self._handle_event(event)

#                 # Mark task as done for the queue
#                 self.event_queue.task_done()

#             except asyncio.TimeoutError:
#                 # Timeout is normal when no events are available - reduced timeout for faster processing
#                 if (
#                     processed_count % 100 == 0 and processed_count > 0
#                 ):  # OPTIMIZED: Less frequent status updates
#                     logger.debug(
#                         f"🔄 Event processor alive, processed {processed_count} events"
#                     )
#                 continue
#             except asyncio.CancelledError:
#                 logger.info("🛑 Event processor cancelled")
#                 break
#             except Exception as e:
#                 logger.error(f"❌ Event processing error: {e}")
#                 # Continue processing despite errors
#                 await asyncio.sleep(0.1)

#         logger.info(
#             f"🛑 Event processor stopped after processing {processed_count} events"
#         )

#     async def _handle_event(self, event: Dict[str, Any]):
#         """Handle a single event with registered handlers"""
#         try:
#             event_type = event["type"]

#             # FIXED: Call registered handlers first
#             if hasattr(self, "_event_handlers") and event_type in self._event_handlers:
#                 for handler in self._event_handlers[event_type]:
#                     try:
#                         if asyncio.iscoroutinefunction(handler):
#                             await handler(event["data"])
#                         else:
#                             handler(event["data"])
#                     except Exception as e:
#                         logger.error(
#                             f"❌ Error in registered handler for {event_type}: {e}"
#                         )

#             # Update relevant caches
#             await self._update_cache_for_event(event)

#             # Broadcast to subscribed clients
#             await self._broadcast_event(event)

#         except Exception as e:
#             logger.error(f"❌ Error handling event {event.get('type')}: {e}")

#     # ===== CORE WEBSOCKET METHODS =====
#     # Analytics are handled by routes on-demand - no periodic processing needed

#     # ===== ANALYTICS REMOVED =====
#     # All analytics processing has been moved to unified_websocket_routes.py
#     # The routes handle analytics on-demand when clients request data
#     # This eliminates redundant processing and improves performance

#     async def _process_pending_events(self):
#         """Process rate-limited pending events periodically"""
#         logger.info("⏰ Pending event processor started")

#         while self.is_running:
#             try:
#                 now = datetime.now()
#                 events_to_process = []

#                 # Check which pending events can now be processed
#                 for event_type, pending in list(self.pending_events.items()):
#                     rate_limit = self.event_rate_limits.get(event_type, 1.0)

#                     if event_type in self.last_event_time:
#                         time_since_last = (
#                             now - self.last_event_time[event_type]
#                         ).total_seconds()
#                         if time_since_last >= rate_limit:
#                             events_to_process.append(event_type)
#                     else:
#                         events_to_process.append(event_type)

#                 # Process pending events
#                 for event_type in events_to_process:
#                     if event_type in self.pending_events:
#                         pending = self.pending_events.pop(event_type)
#                         self.emit_event(
#                             event_type, pending["data"], pending["priority"]
#                         )
#                         logger.debug(f"⏰ Processed pending event: {event_type}")

#                 await asyncio.sleep(1.0)  # Check pending events every second

#             except Exception as e:
#                 logger.error(f"❌ Pending event processor error: {e}")
#                 await asyncio.sleep(5)

#     # ===== CACHE MANAGEMENT =====
#     async def _update_cache_for_event(self, event: Dict[str, Any]):
#         """Update relevant caches based on event type"""
#         try:
#             event_type = event["type"]
#             data = event["data"]

#             if event_type == "price_update":
#                 if isinstance(data, dict):
#                     self.live_prices.update(data)
#             elif event_type.endswith("_update"):
#                 feature_name = event_type.replace("_update", "")
#                 self.analytics_cache[feature_name] = data

#         except Exception as e:
#             logger.error(f"❌ Cache update error: {e}")

#     # ===== BROADCASTING =====
#     async def _broadcast_event(self, event: Dict[str, Any]):
#         """Broadcast event to subscribed clients and SSE connections"""
#         event_type = event["type"]
#         clients_to_notify = []

#         for client_id, subscriptions in self.client_subscriptions.items():
#             if event_type in subscriptions or "all" in subscriptions:
#                 clients_to_notify.append(client_id)

#         # 🚀 ENHANCED LOGGING: Track broadcasting including live_price_update
#         if event_type in [
#             "price_update",
#             "dashboard_update",
#             "live_prices_enriched",
#             "live_price_update",
#         ]:
#             data_size = 0
#             if isinstance(event.get("data"), dict):
#                 data_size = len(event["data"])
#             elif isinstance(event.get("data"), list):
#                 data_size = len(event["data"])

#             # 🚨 CRITICAL: Always log live_price_update for monitoring
#             if event_type == "live_price_update":
#                 logger.info(
#                     f"⚡⚡⚡ INSTANT BROADCAST {event_type} to {len(clients_to_notify)} clients (data: {data_size} items)"
#                 )
#             else:
#                 logger.info(
#                     f"⚡ Broadcasting {event_type} to {len(clients_to_notify)} clients (data: {data_size} items)"
#                 )

#         # Send to all subscribed clients
#         if clients_to_notify:
#             results = await asyncio.gather(
#                 *[
#                     self.send_to_client(client_id, event)
#                     for client_id in clients_to_notify
#                 ],
#                 return_exceptions=True,
#             )

#             # Count successful sends for debugging
#             successful_sends = sum(1 for result in results if result is True)
#             if successful_sends == 0 and len(clients_to_notify) > 0:
#                 logger.warning(
#                     f"⚠️ No clients received {event_type} (attempted {len(clients_to_notify)})"
#                 )
#         elif event_type in ["price_update", "dashboard_update", "live_prices_enriched"]:
#             logger.warning(
#                 f"⚠️ No clients subscribed to {event_type}! Available clients: {len(self.client_subscriptions)}"
#             )
#             if len(self.client_subscriptions) > 0:
#                 logger.info(
#                     f"📋 Client subscriptions: {dict(self.client_subscriptions)}"
#                 )

#     async def send_to_client(self, client_id: str, data: Dict[str, Any]) -> bool:
#         """⚡ ZERO-DELAY: Send data to client with ultra-fast error handling"""
#         if client_id not in self.connections:
#             # Silently skip - client was cleaned up, this is normal
#             return False

#         websocket = self.connections[client_id]

#         try:
#             # ⚡ ULTRA-FAST: Skip state check for maximum speed (WebSocket will handle errors)
#             # if websocket.client_state != WebSocketState.CONNECTED:
#             #     return False

#             # ⚡ ZERO TIMEOUT: Remove timeout to prevent blocking real-time data
#             await websocket.send_json(data)
#             return True
#         except asyncio.TimeoutError:
#             # Should not happen with no timeout, but handle anyway
#             logger.warning(f"⚠️ Unexpected timeout for client {client_id}")
#             await self.remove_client(client_id)
#         except RuntimeError as e:
#             if "not connected" in str(e).lower():
#                 logger.debug(f"🔌 Client {client_id} disconnected")
#             else:
#                 logger.error(f"❌ Runtime error sending to {client_id}: {e}")
#             await self.remove_client(client_id)
#         except Exception as e:
#             logger.error(f"❌ Failed to send to client {client_id}: {e}")
#             await self.remove_client(client_id)

#         return False

#     async def _send_initial_data(self, client_id: str, client_type: str):
#         """Send initial data based on client type with improved error handling"""
#         if client_id not in self.connections:
#             logger.warning(f"⚠️ Cannot send initial data: Client {client_id} not found")
#             return

#         websocket = self.connections[client_id]

#         try:
#             # Check WebSocket state before attempting to send
#             if websocket.client_state != WebSocketState.CONNECTED:
#                 logger.warning(
#                     f"⚠️ Cannot send initial data to {client_id}: WebSocket not connected"
#                 )
#                 return

#             # No initial analytics data sent from manager
#             # Clients should request data via routes: get_dashboard_data, get_live_prices, etc.
#             logger.info(
#                 f"📊 Client {client_id} connected - data available via route requests"
#             )

#             # Send live prices if available
#             if self.live_prices:
#                 try:
#                     await websocket.send_json(
#                         {
#                             "type": "live_prices",
#                             "data": self.live_prices,
#                             "count": len(self.live_prices),
#                             "timestamp": datetime.now().isoformat(),
#                         }
#                     )
#                     logger.info(
#                         f"📊 Sent live prices to {client_id} ({len(self.live_prices)} instruments)"
#                     )
#                 except Exception as e:
#                     logger.error(f"❌ Error sending live prices: {e}")
#         except Exception as e:
#             logger.error(f"❌ Error in _send_initial_data for {client_id}: {e}")

#     # ===== PUBLIC API =====
#     def get_available_events(self) -> List[str]:
#         """Get list of available event types"""
#         return [
#             "market_data_update",  # 🚀 NEW: Single comprehensive market event
#             "price_update",  # Legacy support
#             "dashboard_update",  # Legacy support
#             "index_update",
#             "top_movers_update",
#             "volume_analysis_update",
#             "gap_analysis_update",
#             "breakout_analysis_update",
#             "market_sentiment_update",
#             "heatmap_update",
#             "intraday_stocks_update",
#             "record_movers_update",
#             "options_chain_update",
#             "market_status_update",
#             "live_prices_enriched",
#             # Auto-trading events
#             "auto_trading_update",
#             "fibonacci_signal",
#             "position_update",
#             "performance_update",
#             "system_status",
#             "emergency_alert",
#             "session_update",
#             "fno_selection_update",
#         ]

#     def get_status(self) -> Dict[str, Any]:
#         """Get system status with trading safety metrics"""
#         queue_size = self.event_queue.qsize()
#         queue_percentage = (queue_size / self.event_queue.maxsize) * 100

#         return {
#             "is_running": self.is_running,
#             "total_connections": len(self.connections),
#             "client_types": dict(
#                 defaultdict(
#                     int,
#                     {
#                         ct: sum(1 for t in self.client_types.values() if t == ct)
#                         for ct in set(self.client_types.values())
#                     },
#                 )
#             ),
#             "cached_analytics": list(self.analytics_cache.keys()),
#             "live_prices_count": len(self.live_prices),
#             "event_queue_size": queue_size,
#             "event_queue_percentage": round(queue_percentage, 1),
#             "queue_status": (
#                 "CRITICAL"
#                 if queue_percentage > 80
#                 else "WARNING" if queue_percentage > 60 else "OK"
#             ),
#             "background_tasks": len(self.background_tasks),
#             "analytics_service_available": self.analytics_service is not None,
#             # TRADING SAFETY METRICS
#             "trading_mode": self.trading_mode,
#             "emergency_mode": self.emergency_mode,
#             "pending_events_count": len(self.pending_events),
#             "rate_limits": self.event_rate_limits,
#         }

#     def enable_emergency_mode(self):
#         """Enable emergency mode to bypass rate limiting during high volatility"""
#         self.emergency_mode = True
#         logger.warning(
#             "🚨 EMERGENCY MODE ENABLED - Rate limiting bypassed for all events"
#         )

#     def disable_emergency_mode(self):
#         """Disable emergency mode to restore normal rate limiting"""
#         self.emergency_mode = False
#         logger.info("✅ EMERGENCY MODE DISABLED - Normal rate limiting restored")

#     def get_queue_health(self) -> Dict[str, Any]:
#         """Get queue health metrics for monitoring"""
#         queue_size = self.event_queue.qsize()
#         queue_capacity = self.event_queue.maxsize
#         queue_usage_percent = (
#             (queue_size / queue_capacity) * 100 if queue_capacity > 0 else 0
#         )

#         return {
#             "queue_size": queue_size,
#             "queue_capacity": queue_capacity,
#             "queue_usage_percent": round(queue_usage_percent, 2),
#             "queue_health": (
#                 "critical"
#                 if queue_usage_percent > 90
#                 else "warning" if queue_usage_percent > 70 else "healthy"
#             ),
#             "emergency_mode": self.emergency_mode,
#             "pending_events": len(self.pending_events),
#         }

#     def monitor_queue_health(self):
#         """Monitor queue health and auto-enable emergency mode if needed"""
#         health = self.get_queue_health()

#         if health["queue_usage_percent"] > 90 and not self.emergency_mode:
#             logger.warning(
#                 f"🚨 QUEUE CRITICAL: {health['queue_usage_percent']:.1f}% full - enabling emergency mode"
#             )
#             self.enable_emergency_mode()
#         elif health["queue_usage_percent"] < 50 and self.emergency_mode:
#             logger.info(
#                 f"✅ QUEUE RECOVERED: {health['queue_usage_percent']:.1f}% full - disabling emergency mode"
#             )
#             self.disable_emergency_mode()

#         return health

#     def adjust_rate_limits(self, new_limits: Dict[str, float]):
#         """Dynamically adjust rate limits for different market conditions"""
#         self.event_rate_limits.update(new_limits)
#         logger.info(f"⚙️ Rate limits adjusted: {new_limits}")


# # Singleton instance
# unified_manager = UnifiedWebSocketManager()


# # Integration with existing systems
# def integrate_with_centralized_manager():
#     try:
#         from services.centralized_ws_manager import centralized_manager

#         # Import gap and breakout detection services
#         gap_service = None
#         breakout_service = None
#         try:
#             from services.enhanced_breakout_engine import enhanced_breakout_engine

#             # Gap detection is now handled by premarket_candle_builder
#             # from services.premarket_candle_builder import get_todays_gaps

#             breakout_service = enhanced_breakout_engine
#             logger.info(
#                 "✅ Enhanced breakout engine loaded (gap detection via premarket_candle_builder)"
#             )
#         except ImportError as e:
#             logger.warning(f"⚠️ Detection services not available: {e}")

#         # Register callback to forward price updates (OPTIMIZED - NO BLOCKING)
#         def price_update_callback(data):
#             try:
#                 price_data = data.get("data", {})
#                 if price_data:
#                     # 🚀 ENHANCED: Ensure each instrument has symbol field for frontend compatibility
#                     enhanced_price_data = {}
#                     for instrument_key, instrument_data in price_data.items():
#                         if instrument_data and isinstance(instrument_data, dict):
#                             # Create enhanced data with symbol field
#                             enhanced_instrument = {
#                                 **instrument_data,
#                                 "instrument_key": instrument_key,
#                                 "timestamp": data.get(
#                                     "timestamp", datetime.now().isoformat()
#                                 ),
#                             }

#                             # Ensure symbol field exists with proper resolution
#                             if (
#                                 "symbol" not in enhanced_instrument
#                                 or not enhanced_instrument["symbol"]
#                             ):
#                                 # Extract symbol from instrument key with proper logic
#                                 if "|" in instrument_key:
#                                     parts = instrument_key.split("|")
#                                     if len(parts) >= 2:
#                                         exchange_segment, identifier = (
#                                             parts[0],
#                                             parts[1],
#                                         )

#                                         # For NSE_EQ with ISIN, try to resolve to trading symbol
#                                         if (
#                                             "NSE_EQ" in exchange_segment
#                                             and len(identifier) == 12
#                                             and identifier.startswith("INE")
#                                         ):
#                                             # This is an ISIN, try to get trading symbol from instrument_data
#                                             symbol = instrument_data.get(
#                                                 "trading_symbol"
#                                             ) or instrument_data.get("symbol")
#                                             enhanced_instrument["symbol"] = (
#                                                 symbol if symbol else identifier
#                                             )
#                                         else:
#                                             # For indices and other formats, use identifier directly
#                                             enhanced_instrument["symbol"] = identifier
#                                     else:
#                                         enhanced_instrument["symbol"] = instrument_key
#                                 else:
#                                     enhanced_instrument["symbol"] = instrument_key

#                             enhanced_price_data[instrument_key] = enhanced_instrument

#                     # 🚀 ULTIMATE STREAMLINED: Use ONLY Real-Time Market Analytics Engine
#                     try:
#                         from services.realtime_market_engine import (
#                             get_live_analytics,
#                             get_live_heatmap,
#                             get_market_engine,
#                         )

#                         # Get Real-Time Market Engine data (already updated by centralized_ws_manager)
#                         engine = get_market_engine()
#                         realtime_analytics = get_live_analytics()
#                         heatmap_data = get_live_heatmap(
#                             "sector", "market_cap", "performance"
#                         )

#                         # Get updated instruments from Real-Time Analytics Engine (no optimized_service needed)
#                         price_changes = {}
#                         for (
#                             instrument_key,
#                             instrument_data,
#                         ) in enhanced_price_data.items():
#                             if instrument_key in engine.instruments:
#                                 instrument = engine.instruments[instrument_key]
#                                 price_changes[instrument_key] = {
#                                     "symbol": instrument.symbol,
#                                     "name": instrument.name,
#                                     "ltp": instrument.ltp_paise
#                                     / 100,  # Convert back to rupees
#                                     "change_percent": instrument.change_ppm
#                                     / 10000,  # Convert back to percentage
#                                     "volume": instrument.volume,
#                                     "sector": instrument.sector,
#                                     "instrument_key": instrument_key,
#                                     "last_updated": datetime.now().isoformat(),
#                                 }

#                         # 🎯 SINGLE SOURCE COMPREHENSIVE EVENT - Everything from Real-Time Analytics Engine
#                         if price_changes or enhanced_price_data:
#                             unified_market_data = {
#                                 # Price data from Real-Time Analytics Engine (optimized format)
#                                 "price_changes": price_changes,  # Processed by analytics engine
#                                 "all_prices": enhanced_price_data,  # Raw price data for compatibility
#                                 # Complete analytics suite from Real-Time Analytics Engine
#                                 "analytics": realtime_analytics,
#                                 "heatmap": heatmap_data,
#                                 # Metadata
#                                 "market_status": {
#                                     "is_open": data.get("market_open", True),
#                                     "update_type": (
#                                         "incremental" if price_changes else "snapshot"
#                                     ),
#                                     "updated_count": (
#                                         len(price_changes) if price_changes else 0
#                                     ),
#                                     "total_instruments": len(enhanced_price_data),
#                                 },
#                                 "timestamp": datetime.now().isoformat(),
#                             }

#                             # 🚀 Send ONE event that bypasses queue for ultimate speed
#                             unified_manager.emit_event(
#                                 "market_data_update", unified_market_data, priority=-1
#                             )
#                             logger.debug(
#                                 f"⚡ SINGLE SOURCE broadcast: {len(price_changes)} changes, analytics from Real-Time Engine"
#                             )

#                         logger.debug(
#                             f"📊 Retrieved all data from Real-Time Analytics Engine for {len(enhanced_price_data)} instruments"
#                         )

#                     except ImportError:
#                         # Real-Time Analytics Engine not available - fallback to basic data
#                         logger.warning("⚠️ Real-Time Analytics Engine not available")
#                         unified_market_data = {
#                             "all_prices": enhanced_price_data,
#                             "analytics": {},
#                             "heatmap": {},
#                             "market_status": {"is_open": True},
#                             "timestamp": datetime.now().isoformat(),
#                         }
#                         unified_manager.emit_event(
#                             "market_data_update", unified_market_data, priority=-1
#                         )

#                     except Exception as e:
#                         logger.error(f"❌ Error in unified market data update: {e}")
#                         # CRITICAL FAILURE: If unified market data fails, log but don't send redundant events
#                         logger.error(
#                             "🚨 CRITICAL: Unified market data update failed - no fallback events to prevent redundancy"
#                         )

#                     # ✅ PERFORMANCE FIX: Move analytics to background (don't block price pipeline)
#                     if gap_service or breakout_service:
#                         # Queue analytics processing in background - DON'T BLOCK
#                         asyncio.create_task(
#                             process_analytics_background(
#                                 enhanced_price_data, gap_service, breakout_service
#                             )
#                         )

#             except Exception as e:
#                 logger.error(f"❌ Error in real-time price update callback: {e}")

#         # ✅ NEW: Background analytics processing (non-blocking)
#         async def process_analytics_background(
#             price_data, gap_service, breakout_service
#         ):
#             """Process analytics in background without blocking price pipeline"""
#             try:
#                 # Process gap detection in background
#                 if gap_service:
#                     try:
#                         new_gaps = gap_service.process_live_feed_data(price_data)
#                         if new_gaps:
#                             gap_signals_data = [
#                                 {
#                                     "symbol": gap.symbol,
#                                     "gap_type": gap.gap_type,
#                                     "gap_percentage": round(gap.gap_percentage, 2),
#                                     "open_price": gap.open_price,
#                                     "previous_close": gap.previous_close,
#                                     "current_price": gap.current_price,
#                                     "volume_ratio": round(gap.volume_ratio, 1),
#                                     "gap_strength": gap.gap_strength,
#                                     "confidence_score": round(gap.confidence_score, 2),
#                                     "sector": gap.sector,
#                                     "timestamp": gap.timestamp.isoformat(),
#                                 }
#                                 for gap in new_gaps
#                             ]

#                             # Broadcast gap signals (now from background)
#                             unified_manager.emit_event(
#                                 "gap_signals_update",
#                                 {
#                                     "signals": gap_signals_data,
#                                     "count": len(gap_signals_data),
#                                     "market_open_time": "09:15:00",
#                                     "timestamp": datetime.now().isoformat(),
#                                 },
#                                 priority=2,
#                             )  # Lower priority than price updates

#                             logger.info(
#                                 f"🚨 Background processed {len(new_gaps)} gap signals"
#                             )
#                     except Exception as e:
#                         logger.error(f"❌ Error in background gap detection: {e}")

#                 # ✅ MODERN BREAKOUT PROCESSING:
#                 # The new BreakoutScannerService already receives data via centralized WebSocket manager
#                 # and handles its own signal broadcasting via Redis/WebSocket. No batch processing needed.
#                 # Breakout signals are automatically processed through the callback system.

#                 # Legacy batch processing removed - modern event-driven architecture handles this

#                 # Background unified processing complete
#                 logger.debug("📊 Background market data processing completed")

#             except Exception as e:
#                 logger.error(f"❌ Error in background analytics processing: {e}")

#         # DISABLED: Single source architecture - realtime_market_engine handles UI broadcasting
#         # centralized_manager.register_callback("price_update", price_update_callback)
#         # centralized_manager.register_callback("market_status", market_status_callback)

#         logger.info("✅ Unified WebSocket Manager callback registration DISABLED for single source architecture")

#         logger.info("✅ Integration with centralized manager completed successfully")

#     except ImportError:
#         logger.warning("⚠️ Centralized manager not available")
#     except Exception as e:
#         logger.error(f"❌ Integration error: {e}")


# # Convenience functions
# async def start_unified_websocket():
#     """Start the unified WebSocket system"""
#     try:
#         await unified_manager.start()
#         # ✅ FIXED: Integration now handled in app.py after centralized manager is ready
#         logger.info("✅ Unified WebSocket system started successfully")
#     except Exception as e:
#         logger.error(f"❌ Failed to start unified WebSocket: {e}")


# async def stop_unified_websocket():
#     """Stop the unified WebSocket system"""
#     try:
#         await unified_manager.stop()
#         logger.info("✅ Unified WebSocket system stopped")
#     except Exception as e:
#         logger.error(f"❌ Error stopping unified WebSocket: {e}")


# def emit_market_event(event_type: str, data: Dict[str, Any]):
#     """Emit a market event"""
#     try:
#         unified_manager.emit_event(event_type, data)
#     except Exception as e:
#         logger.error(f"❌ Error emitting event {event_type}: {e}")


# def emit_intelligent_stock_selection_update(data: Dict[str, Any]):
#     """Emit intelligent stock selection update to all clients"""
#     try:
#         unified_manager.emit_event(
#             "intelligent_stock_selection_update", data, priority=5
#         )
#         logger.info("🧠 Broadcasted intelligent stock selection update")
#     except Exception as e:
#         logger.error(f"❌ Error emitting intelligent stock selection update: {e}")


# def emit_real_time_analytics_update(data: Dict[str, Any]):
#     """⚠️ DEPRECATED: Real-time analytics now sent via market_data_update event"""
#     try:
#         # ⚠️ DISABLED: This event is REDUNDANT with market_data_update
#         logger.debug(
#             "🚫 real_time_analytics_update disabled - using market_data_update instead"
#         )

#         # # DEPRECATED: Redundant with market_data_update event
#         # enhanced_data = _enhance_with_realtime_analytics(data)
#         # unified_manager.emit_event("real_time_analytics_update", enhanced_data, priority=2)
#         # list_count = len(enhanced_data.get("lists", {}))
#         # logger.debug(f"⚡ Broadcasted enhanced real-time analytics: {list_count} lists updated")

#     except Exception as e:
#         logger.error(f"❌ Error emitting real-time analytics update: {e}")


# def _enhance_with_realtime_analytics(data: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     🚀 NEW: Enhance existing analytics data with Real-Time Analytics Engine

#     This function integrates our new analytics engine with the existing data flow
#     """
#     try:
#         # Import real-time analytics engine
#         from services.realtime_market_engine import get_live_analytics, get_live_heatmap

#         # Get enhanced analytics from our new engine
#         realtime_analytics = get_live_analytics()

#         # Merge with existing data structure
#         enhanced_data = data.copy()

#         # Add real-time analytics while preserving existing structure
#         enhanced_data.update(
#             {
#                 # 🚀 NEW: Zero-latency analytics from our engine
#                 "realtime_engine": {
#                     "top_movers": realtime_analytics.get("top_movers", {}),
#                     "market_breadth": realtime_analytics.get("market_breadth", {}),
#                     "sector_analytics": realtime_analytics.get("sector_analytics", {}),
#                     "volume_analytics": realtime_analytics.get("volume_analytics", {}),
#                     "market_sentiment": realtime_analytics.get("market_sentiment", {}),
#                     "metadata": realtime_analytics.get("metadata", {}),
#                 },
#                 # 🚀 NEW: Professional heatmap data
#                 "heatmap_data": {
#                     "sector": get_live_heatmap("sector", "market_cap", "performance"),
#                     "individual": get_live_heatmap(
#                         "individual", "market_cap", "performance"
#                     ),
#                 },
#                 # Mark as enhanced
#                 "enhanced_by_realtime_engine": True,
#                 "enhancement_timestamp": datetime.now().isoformat(),
#             }
#         )

#         logger.debug("✅ Enhanced analytics data with Real-Time Engine")
#         return enhanced_data

#     except ImportError:
#         # Real-time engine not available, return original data
#         logger.debug("⚠️ Real-Time Analytics Engine not available, using original data")
#         return data
#     except Exception as e:
#         logger.error(f"❌ Error enhancing analytics data: {e}")
#         return data


# # Add this method to the UnifiedWebSocketManager class in unified_websocket_manager.py
