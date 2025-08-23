# services/realtime_data_streamer.py
"""
🚀 ZERO-DELAY Real-time Data Streamer
Direct path from Upstox WebSocket to UI bypassing ALL processing layers
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Set, Any, Optional
from collections import defaultdict
import weakref

logger = logging.getLogger(__name__)


class RealtimeDataStreamer:
    """
    🚀 ULTRA-FAST: Direct WebSocket to UI streaming without ANY processing delays
    
    This service provides ZERO-DELAY data streaming by:
    1. Receiving raw data from centralized_ws_manager
    2. Immediately broadcasting to UI without enrichment
    3. Background processing for analytics happens separately
    """

    def __init__(self):
        # UI WebSocket connections (using WeakSet for automatic cleanup)
        self._ui_connections = set()
        self._connection_subscriptions = defaultdict(set)  # client_id -> {instrument_keys}
        
        # Performance tracking
        self._total_broadcasts = 0
        self._last_broadcast_time = 0
        self._broadcast_latency = []
        
        # Real-time streaming controls
        self._streaming_active = False
        self._max_broadcast_latency_ms = 5  # Maximum allowed latency before warning
        
        # Data validation (minimal - just prevent crashes)
        self._required_fields = ['lp', 'instrument_token']  # lp = last_price, minimal validation
        
        logger.info("🚀 ZERO-DELAY Real-time Data Streamer initialized")

    async def register_ui_connection(self, websocket, client_id: str, subscriptions: Set[str] = None):
        """Register a UI WebSocket connection for real-time streaming"""
        try:
            self._ui_connections.add(websocket)
            if subscriptions:
                self._connection_subscriptions[client_id] = subscriptions
            
            logger.info(f"🔗 UI connection registered: {client_id} ({len(subscriptions) if subscriptions else 0} subscriptions)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to register UI connection {client_id}: {e}")
            return False

    async def unregister_ui_connection(self, websocket, client_id: str):
        """Unregister UI WebSocket connection"""
        try:
            self._ui_connections.discard(websocket)
            self._connection_subscriptions.pop(client_id, None)
            
            logger.info(f"🔗 UI connection unregistered: {client_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to unregister UI connection {client_id}: {e}")

    async def stream_raw_market_data(self, raw_data: Dict[str, Any]):
        """
        🚀 CRITICAL: Stream raw market data INSTANTLY to UI
        
        This method receives raw data from centralized_ws_manager and immediately
        broadcasts it to UI without ANY processing delays.
        """
        start_time = time.time()
        
        try:
            if not self._streaming_active:
                return
                
            # Minimal validation - only check if data exists
            if not raw_data or not isinstance(raw_data, dict):
                return

            # Extract feeds data (the actual market data)
            feeds = raw_data.get('feeds', {})
            if not feeds:
                # Try alternative formats
                if 'data' in raw_data:
                    feeds = raw_data['data']
                else:
                    # Raw instrument data format
                    feeds = {k: v for k, v in raw_data.items() if '|' in k or 'NSE_EQ' in k or 'NSE_FO' in k}
            
            if not feeds:
                return

            # 🚀 ZERO-DELAY: Broadcast immediately
            broadcast_count = await self._instant_ui_broadcast(feeds, raw_data.get('timestamp'))
            
            # Performance tracking
            processing_time = (time.time() - start_time) * 1000
            self._broadcast_latency.append(processing_time)
            self._total_broadcasts += 1
            self._last_broadcast_time = time.time()
            
            # Keep only last 100 latency measurements for rolling average
            if len(self._broadcast_latency) > 100:
                self._broadcast_latency = self._broadcast_latency[-100:]
            
            # Log performance warnings if latency is high
            if processing_time > self._max_broadcast_latency_ms:
                avg_latency = sum(self._broadcast_latency) / len(self._broadcast_latency)
                logger.warning(
                    f"⚡ High broadcast latency: {processing_time:.2f}ms "
                    f"(avg: {avg_latency:.2f}ms, broadcasts: {broadcast_count})"
                )
                
            logger.debug(f"⚡ Streamed {len(feeds)} instruments in {processing_time:.2f}ms to {broadcast_count} connections")
            
        except Exception as e:
            logger.error(f"❌ Error in real-time streaming: {e}")

    async def _instant_ui_broadcast(self, feeds: Dict[str, Any], timestamp: str = None) -> int:
        """
        🚀 INSTANT: Broadcast data to UI connections immediately
        """
        if not self._ui_connections:
            return 0
            
        # Prepare broadcast message
        ui_message = {
            "type": "live_price_update",
            "data": feeds,
            "timestamp": timestamp or datetime.now().isoformat(),
            "source": "realtime_streamer",
            "latency_optimized": True
        }
        
        message_json = json.dumps(ui_message)
        broadcast_count = 0
        dead_connections = set()
        
        # Broadcast to all active UI connections
        for websocket in self._ui_connections.copy():  # Copy to avoid modification during iteration
            try:
                if hasattr(websocket, 'application_state') and websocket.application_state.CONNECTED:
                    await websocket.send_text(message_json)
                    broadcast_count += 1
                else:
                    dead_connections.add(websocket)
                    
            except Exception as e:
                logger.debug(f"❌ Failed to send to WebSocket: {e}")
                dead_connections.add(websocket)
        
        # Clean up dead connections
        for dead_ws in dead_connections:
            self._ui_connections.discard(dead_ws)
        
        return broadcast_count

    def start_streaming(self):
        """Start real-time streaming"""
        self._streaming_active = True
        logger.info("🚀 Real-time data streaming STARTED (ZERO-DELAY mode)")

    def stop_streaming(self):
        """Stop real-time streaming"""
        self._streaming_active = False
        logger.info("⏹️ Real-time data streaming STOPPED")

    def get_streaming_stats(self) -> Dict[str, Any]:
        """Get real-time streaming performance statistics"""
        avg_latency = sum(self._broadcast_latency) / len(self._broadcast_latency) if self._broadcast_latency else 0
        
        return {
            "streaming_active": self._streaming_active,
            "total_broadcasts": self._total_broadcasts,
            "active_connections": len(self._ui_connections),
            "total_subscriptions": sum(len(subs) for subs in self._connection_subscriptions.values()),
            "average_latency_ms": round(avg_latency, 2),
            "last_broadcast": self._last_broadcast_time,
            "performance_samples": len(self._broadcast_latency),
            "max_allowed_latency_ms": self._max_broadcast_latency_ms
        }

    async def health_check(self) -> Dict[str, Any]:
        """Health check for the streaming service"""
        stats = self.get_streaming_stats()
        
        is_healthy = (
            self._streaming_active and 
            stats["average_latency_ms"] < self._max_broadcast_latency_ms * 2
        )
        
        return {
            "status": "healthy" if is_healthy else "degraded",
            "streaming_active": self._streaming_active,
            "active_connections": len(self._ui_connections),
            "performance": {
                "avg_latency_ms": stats["average_latency_ms"],
                "total_broadcasts": self._total_broadcasts
            },
            "timestamp": datetime.now().isoformat()
        }


# Create singleton instance
realtime_streamer = RealtimeDataStreamer()