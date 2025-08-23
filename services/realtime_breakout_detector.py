# services/realtime_breakout_detector.py
"""
🚀 ZERO-DELAY Real-time Breakout Detection Service

This service processes raw market data instantly to detect breakouts,
gaps, and momentum changes in real-time without any processing delays.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict, deque
import json

logger = logging.getLogger(__name__)


class RealtimeBreakoutDetector:
    """
    🚀 Ultra-fast breakout detection that processes raw market data
    instantly without waiting for enrichment or heavy analytics
    """

    def __init__(self):
        # Price history for breakout detection (keep lightweight)
        self._price_history = defaultdict(lambda: deque(maxlen=50))  # Last 50 price points per instrument
        self._volume_history = defaultdict(lambda: deque(maxlen=20))  # Last 20 volume points
        self._breakout_cache = {}  # Cache recent breakouts to avoid duplicates
        
        # Real-time breakout signals
        self._active_breakouts = {}  # instrument_key -> breakout_data
        self._breakout_callbacks = []  # Callbacks for breakout events
        
        # Performance tracking
        self._detections_count = 0
        self._processing_times = deque(maxlen=100)
        self._last_detection_time = None
        
        # Breakout detection parameters (lightweight)
        self._min_breakout_percent = 2.0  # Minimum 2% price move for breakout
        self._min_volume_multiplier = 1.5  # Volume should be 1.5x average
        self._breakout_timeout = 300  # 5 minutes timeout for breakout signals
        
        # Active instruments to monitor (avoid processing noise)
        self._monitored_instruments = set()
        self._hot_instruments = set()  # High-activity instruments
        
        logger.info("🚀 Real-time Breakout Detector initialized (ZERO-DELAY)")

    def add_monitored_instruments(self, instrument_keys: List[str]):
        """Add instruments to monitor for breakouts"""
        self._monitored_instruments.update(instrument_keys)
        logger.info(f"📊 Monitoring {len(self._monitored_instruments)} instruments for breakouts")

    def register_breakout_callback(self, callback):
        """Register callback for breakout events"""
        self._breakout_callbacks.append(callback)
        logger.info(f"📞 Registered breakout callback ({len(self._breakout_callbacks)} total)")

    async def process_realtime_data(self, raw_data: Dict[str, Any]):
        """
        🚀 CRITICAL: Process raw market data instantly for breakout detection
        
        This method is called directly from the ZERO-DELAY streamer
        and must complete processing in under 5ms to avoid delays.
        """
        start_time = time.time()
        
        try:
            # Extract feeds data
            feeds = raw_data.get('feeds', {})
            if not feeds:
                feeds = raw_data.get('data', {})
                if not feeds:
                    # Direct instrument data format
                    feeds = {k: v for k, v in raw_data.items() if '|' in k}
            
            if not feeds:
                return
            
            breakouts_detected = []
            
            # Process only monitored instruments for performance
            for instrument_key, price_data in feeds.items():
                if instrument_key not in self._monitored_instruments:
                    continue
                    
                # Quick breakout check (must be ultra-fast)
                breakout = await self._quick_breakout_check(instrument_key, price_data)
                if breakout:
                    breakouts_detected.append(breakout)
            
            # Broadcast breakouts if any detected
            if breakouts_detected:
                await self._broadcast_breakouts(breakouts_detected)
                
            # Performance tracking
            processing_time = (time.time() - start_time) * 1000
            self._processing_times.append(processing_time)
            self._last_detection_time = time.time()
            
            # Log performance warnings if too slow
            if processing_time > 5.0:  # Over 5ms is too slow
                avg_time = sum(self._processing_times) / len(self._processing_times)
                logger.warning(
                    f"⚡ Breakout detection slow: {processing_time:.2f}ms "
                    f"(avg: {avg_time:.2f}ms, detected: {len(breakouts_detected)})"
                )
                
        except Exception as e:
            logger.error(f"❌ Error in real-time breakout detection: {e}")

    async def _quick_breakout_check(self, instrument_key: str, price_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        🚀 Ultra-fast breakout detection (must complete in <1ms per instrument)
        """
        try:
            # Extract essential data quickly
            current_price = float(price_data.get('lp', price_data.get('last_price', 0)))
            volume = int(price_data.get('v', price_data.get('volume', 0)))
            open_price = float(price_data.get('op', price_data.get('open', current_price)))
            
            if current_price <= 0:
                return None
            
            # Update price history
            price_history = self._price_history[instrument_key]
            volume_history = self._volume_history[instrument_key]
            
            price_history.append(current_price)
            if volume > 0:
                volume_history.append(volume)
            
            # Need at least 10 data points for detection
            if len(price_history) < 10:
                return None
            
            # Quick breakout detection logic
            # 1. Price movement check
            price_change_percent = ((current_price - open_price) / open_price) * 100
            if abs(price_change_percent) < self._min_breakout_percent:
                return None
            
            # 2. Volume confirmation (if available)
            volume_confirmed = True
            if len(volume_history) >= 5 and volume > 0:
                avg_volume = sum(list(volume_history)[-5:]) / 5
                volume_confirmed = volume >= (avg_volume * self._min_volume_multiplier)
            
            # 3. Price momentum check
            recent_prices = list(price_history)[-5:]  # Last 5 prices
            price_trend = recent_prices[-1] - recent_prices[0]
            momentum_confirmed = (price_trend > 0 and price_change_percent > 0) or (price_trend < 0 and price_change_percent < 0)
            
            # 4. Check if already detected recently (avoid spam)
            cache_key = f"{instrument_key}_{int(time.time() / 60)}"  # 1-minute cache
            if cache_key in self._breakout_cache:
                return None
            
            # Breakout confirmed if price and momentum conditions are met
            if momentum_confirmed and (volume_confirmed or abs(price_change_percent) > self._min_breakout_percent * 2):
                breakout_data = {
                    'instrument_key': instrument_key,
                    'symbol': instrument_key.split('|')[-1] if '|' in instrument_key else instrument_key,
                    'breakout_type': 'bullish' if price_change_percent > 0 else 'bearish',
                    'current_price': current_price,
                    'open_price': open_price,
                    'price_change': current_price - open_price,
                    'price_change_percent': price_change_percent,
                    'volume': volume,
                    'volume_confirmed': volume_confirmed,
                    'momentum_strength': abs(price_trend),
                    'detection_time': datetime.now().isoformat(),
                    'source': 'realtime_breakout_detector'
                }
                
                # Cache this detection
                self._breakout_cache[cache_key] = breakout_data
                self._detections_count += 1
                
                return breakout_data
            
            return None
            
        except Exception as e:
            logger.debug(f"Error in quick breakout check for {instrument_key}: {e}")
            return None

    async def _broadcast_breakouts(self, breakouts: List[Dict[str, Any]]):
        """Broadcast breakout signals to all registered callbacks"""
        try:
            if not self._breakout_callbacks:
                return
            
            broadcast_data = {
                'type': 'breakout_signals',
                'signals': breakouts,
                'detection_count': len(breakouts),
                'timestamp': datetime.now().isoformat(),
                'source': 'realtime_breakout_detector'
            }
            
            # Execute callbacks
            for callback in self._breakout_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(broadcast_data)
                    else:
                        callback(broadcast_data)
                except Exception as e:
                    logger.error(f"❌ Error in breakout callback: {e}")
                    
            logger.info(f"🚨 Broadcast {len(breakouts)} real-time breakout signals")
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting breakouts: {e}")

    def get_active_breakouts(self) -> List[Dict[str, Any]]:
        """Get currently active breakout signals"""
        current_time = time.time()
        active = []
        
        for breakout_data in self._active_breakouts.values():
            detection_time = datetime.fromisoformat(breakout_data['detection_time'])
            if (current_time - detection_time.timestamp()) < self._breakout_timeout:
                active.append(breakout_data)
        
        return active

    def get_detector_stats(self) -> Dict[str, Any]:
        """Get performance statistics for the breakout detector"""
        avg_processing_time = sum(self._processing_times) / len(self._processing_times) if self._processing_times else 0
        
        return {
            'detections_count': self._detections_count,
            'monitored_instruments': len(self._monitored_instruments),
            'active_breakouts': len(self.get_active_breakouts()),
            'avg_processing_time_ms': round(avg_processing_time, 2),
            'last_detection': self._last_detection_time,
            'cache_size': len(self._breakout_cache),
            'callbacks_registered': len(self._breakout_callbacks),
            'performance_samples': len(self._processing_times)
        }

    async def cleanup_old_data(self):
        """Clean up old data to prevent memory bloat"""
        current_time = time.time()
        
        # Clean old breakout cache
        old_cache_keys = [
            key for key, data in self._breakout_cache.items() 
            if (current_time - datetime.fromisoformat(data['detection_time']).timestamp()) > self._breakout_timeout
        ]
        
        for key in old_cache_keys:
            self._breakout_cache.pop(key, None)
        
        if old_cache_keys:
            logger.debug(f"🧹 Cleaned {len(old_cache_keys)} old breakout cache entries")

    async def health_check(self) -> Dict[str, Any]:
        """Health check for the breakout detector"""
        stats = self.get_detector_stats()
        
        is_healthy = (
            stats['avg_processing_time_ms'] < 10.0 and  # Processing under 10ms
            len(self._monitored_instruments) > 0 and  # Has instruments to monitor
            len(self._breakout_callbacks) > 0  # Has callbacks registered
        )
        
        return {
            'status': 'healthy' if is_healthy else 'degraded',
            'monitoring_active': len(self._monitored_instruments) > 0,
            'callbacks_registered': len(self._breakout_callbacks) > 0,
            'performance': {
                'avg_processing_time_ms': stats['avg_processing_time_ms'],
                'detections_count': stats['detections_count']
            },
            'timestamp': datetime.now().isoformat()
        }


# Create singleton instance
realtime_breakout_detector = RealtimeBreakoutDetector()