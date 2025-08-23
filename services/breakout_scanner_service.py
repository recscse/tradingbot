#!/usr/bin/env python3
"""
Breakout Scanner Service - Real-time breakout detection using Market Data Hub

Features:
- Real-time breakout detection from live market data
- Multiple breakout strategies (volume, price, momentum)
- Daily reset for new trading sessions
- High/low tracking with timestamps
- Integration with unified WebSocket for UI updates
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta, time as datetime_time
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
import threading
from enum import Enum

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class BreakoutType(Enum):
    """Types of breakouts detected"""
    VOLUME_BREAKOUT = "volume_breakout"
    PRICE_BREAKOUT = "price_breakout"
    MOMENTUM_BREAKOUT = "momentum_breakout"
    RESISTANCE_BREAKOUT = "resistance_breakout"
    SUPPORT_BREAKDOWN = "support_breakdown"

@dataclass
class BreakoutSignal:
    """Breakout signal data structure"""
    instrument_key: str
    symbol: str
    breakout_type: BreakoutType
    current_price: float
    breakout_price: float
    volume: int
    percentage_move: float
    strength: float  # 1-10 scale
    timestamp: datetime
    market_cap_category: str = "unknown"
    sector: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "instrument_key": self.instrument_key,
            "symbol": self.symbol,
            "breakout_type": self.breakout_type.value,
            "current_price": self.current_price,
            "breakout_price": self.breakout_price,
            "volume": self.volume,
            "percentage_move": self.percentage_move,
            "strength": self.strength,
            "timestamp": self.timestamp.isoformat(),
            "timestamp_formatted": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "date": self.timestamp.strftime("%Y-%m-%d"),
            "time": self.timestamp.strftime("%H:%M:%S"),
            "time_12h": self.timestamp.strftime("%I:%M:%S %p"),
            "market_cap_category": self.market_cap_category,
            "sector": self.sector,
            "time_ago": self._calculate_time_ago(),
            "epoch_timestamp": int(self.timestamp.timestamp())
        }
    
    def _calculate_time_ago(self) -> str:
        """Calculate human readable time ago"""
        now = datetime.now()
        diff = now - self.timestamp
        total_seconds = diff.total_seconds()
        
        if total_seconds < 0:
            return "just now"
        elif total_seconds < 10:
            return "just now"
        elif total_seconds < 60:
            return f"{int(total_seconds)}s ago"
        elif total_seconds < 3600:
            minutes = int(total_seconds / 60)
            return f"{minutes}m ago"
        elif total_seconds < 86400:  # 24 hours
            hours = int(total_seconds / 3600)
            minutes = int((total_seconds % 3600) / 60)
            if minutes > 0:
                return f"{hours}h {minutes}m ago"
            else:
                return f"{hours}h ago"
        else:
            days = int(total_seconds / 86400)
            return f"{days}d ago"

@dataclass
class InstrumentTracker:
    """Track instrument data for breakout detection"""
    instrument_key: str
    symbol: str
    
    # Price tracking
    current_price: float = 0.0
    day_high: float = 0.0
    day_low: float = float('inf')
    open_price: float = 0.0
    prev_close: float = 0.0
    
    # Volume tracking
    current_volume: int = 0
    avg_volume_20d: int = 0
    volume_spike_threshold: float = 2.0  # 2x average volume
    
    # Price history for breakout detection
    price_history: deque = field(default_factory=lambda: deque(maxlen=100))
    volume_history: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Breakout levels
    resistance_level: float = 0.0
    support_level: float = 0.0
    
    # Timestamps
    last_updated: datetime = field(default_factory=datetime.now)
    session_start: datetime = field(default_factory=datetime.now)
    
    # Breakout tracking
    breakouts_today: List[BreakoutSignal] = field(default_factory=list)
    last_breakout_time: Optional[datetime] = None

class BreakoutScannerService:
    """Real-time breakout scanner using Market Data Hub"""
    
    def __init__(self):
        # Core data structures
        self.instruments: Dict[str, InstrumentTracker] = {}
        self.active_breakouts: Dict[str, List[BreakoutSignal]] = defaultdict(list)
        self.daily_breakouts: List[BreakoutSignal] = []
        
        # IMPROVED Configuration
        self.min_price = 20.0   # Increased to avoid penny stocks
        self.max_price = 10000.0  # Increased range
        self.min_volume = 5000  # Increased minimum volume
        self.breakout_threshold = 1.8  # Reduced to 1.8% (more sensitive)
        self.volume_multiplier = 2.0  # Increased to 2.0x (more selective)
        self.resistance_lookback = 20  # Days to look back for resistance
        self.gap_threshold = 1.5  # Gap detection threshold
        self.volume_z_threshold = 2.0  # Z-score threshold for volume spikes
        
        # Service state
        self.is_running = False
        self.is_market_open = False
        self.current_trading_day = datetime.now().date()
        self.market_data_hub = None
        self.unified_manager = None
        self.centralized_manager = None
        
        # Performance tracking
        self.scan_count = 0
        self.breakouts_detected = 0
        self.last_scan_time = None
        
        # Threading
        self.data_lock = threading.RLock()
        self.background_tasks = set()
        
        # Initialize connections
        self._init_market_data_hub()
        self._init_centralized_manager()
        
    def _init_market_data_hub(self):
        """Initialize connection to Market Data Hub"""
        try:
            from services.market_data_hub import market_data_hub
            self.market_data_hub = market_data_hub
            logger.info("✅ Breakout Scanner connected to Market Data Hub")
        except ImportError as e:
            logger.error(f"❌ Could not connect to Market Data Hub: {e}")
            self.market_data_hub = None
    
    def _init_unified_manager(self):
        """Initialize connection to Unified WebSocket Manager"""
        try:
            from services.unified_websocket_manager import unified_manager
            self.unified_manager = unified_manager
            logger.info("✅ Breakout Scanner connected to Unified WebSocket Manager")
        except ImportError as e:
            logger.error(f"❌ Could not connect to Unified Manager: {e}")
            self.unified_manager = None
    
    def _init_centralized_manager(self):
        """Initialize connection to Centralized WebSocket Manager"""
        try:
            from services.centralized_ws_manager import centralized_manager, register_market_data_callback
            self.centralized_manager = centralized_manager
            
            # Register callback for real-time data
            success = register_market_data_callback(self._process_centralized_data)
            if success:
                logger.info("✅ Breakout Scanner registered with Centralized WebSocket Manager")
            else:
                logger.warning("⚠️ Failed to register with Centralized WebSocket Manager")
        except ImportError as e:
            logger.error(f"❌ Could not connect to Centralized Manager: {e}")
            self.centralized_manager = None
    
    async def start(self):
        """Start the breakout scanner service"""
        if self.is_running:
            logger.info("🔍 Breakout Scanner already running")
            return
            
        self.is_running = True
        logger.info("🚀 Starting Breakout Scanner Service...")
        
        # Initialize unified manager connection
        self._init_unified_manager()
        
        # Initialize centralized manager connection
        self._init_centralized_manager()
        
        # Register with Market Data Hub for real-time data
        if self.market_data_hub:
            try:
                success = self.market_data_hub.register_consumer(
                    consumer_name="breakout_scanner",
                    callback=self._process_market_data,
                    topics=["prices"],
                    priority=2,  # Medium priority (after UI, before analytics)
                    max_queue_size=1000
                )
                
                if success:
                    logger.info("🔍 Registered with Market Data Hub for real-time breakout scanning")
                else:
                    logger.warning("⚠️ Failed to register with Market Data Hub")
                    
            except Exception as e:
                logger.error(f"❌ Error registering with Market Data Hub: {e}")
        
        # Start background tasks
        scan_task = asyncio.create_task(self._scan_loop())
        cleanup_task = asyncio.create_task(self._cleanup_loop())
        market_status_task = asyncio.create_task(self._market_status_loop())
        
        self.background_tasks.update([scan_task, cleanup_task, market_status_task])
        
        logger.info("✅ Breakout Scanner Service started successfully")
    
    async def stop(self):
        """Stop the breakout scanner service"""
        if not self.is_running:
            return
            
        self.is_running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
        self.background_tasks.clear()
        
        logger.info("🛑 Breakout Scanner Service stopped")
    
    def _process_market_data(self, data: Dict[str, Any]):
        """Process real-time market data from Market Data Hub - FIXED FORMAT"""
        try:
            # FIXED: Handle different data formats from Market Data Hub
            prices = None
            
            # Format 1: Direct prices data (from Hub)
            if isinstance(data, dict) and any(key.startswith(('NSE_', 'BSE_')) for key in data.keys()):
                prices = data
                logger.debug(f"Processing direct prices format: {len(prices)} instruments")
                
            # Format 2: Wrapped in data structure
            elif data.get("type") == "price_update":
                market_data = data.get("data", {})
                prices = market_data.get("prices", {})
                logger.debug(f"Processing wrapped format: {len(prices)} instruments")
                
            # Format 3: Hub callback format
            elif "data" in data and isinstance(data["data"], dict):
                if "prices" in data["data"]:
                    prices = data["data"]["prices"]
                else:
                    prices = data["data"]  # Direct price data
                logger.debug(f"Processing hub callback format: {len(prices)} instruments")
            
            if not prices:
                logger.debug("No price data found in callback")
                return
            
            # Process each instrument update
            instruments_processed = 0
            new_breakouts = []
            
            with self.data_lock:
                for instrument_key, price_data in prices.items():
                    try:
                        # FIXED: Add debug logging
                        logger.debug(f"Processing instrument: {instrument_key}")
                        
                        # Update instrument tracker
                        breakout = self._update_instrument(instrument_key, price_data)
                        if breakout:
                            new_breakouts.append(breakout)
                            logger.info(f"🚨 BREAKOUT DETECTED: {breakout.symbol}")
                            
                        instruments_processed += 1
                        
                    except Exception as e:
                        logger.debug(f"Error processing {instrument_key}: {e}")
                        
        except Exception as e:
            logger.error(f"Error processing market data: {e}")
            
    async def _process_centralized_data(self, data: Dict[str, Any]):
        """Process real-time market data from Centralized WebSocket Manager"""
        try:
            # Handle centralized manager feed format
            feeds = None
            
            if isinstance(data, dict) and "feeds" in data:
                feeds = data["feeds"]
                logger.debug(f"Breakout Scanner: Processing centralized feed with {len(feeds)} updates")
            elif isinstance(data, list):
                feeds = data
                logger.debug(f"Breakout Scanner: Processing direct feed list with {len(feeds)} updates")
            
            if not feeds:
                logger.debug(f"Breakout Scanner: No feeds found in centralized data")
                return
            
            # Convert feeds to price format for breakout analysis
            prices = {}
            for feed in feeds:
                instrument_key = feed.get('instrument_key')
                if instrument_key:
                    # Convert to standard price format
                    prices[instrument_key] = {
                        'instrument_key': instrument_key,
                        'ltp': feed.get('last_price', 0),
                        'last_price': feed.get('last_price', 0),
                        'volume': feed.get('volume', 0),
                        'open': feed.get('open', 0),
                        'high': feed.get('high', 0),
                        'low': feed.get('low', 0),
                        'prev_close': feed.get('prev_close', 0),
                        'timestamp': feed.get('timestamp'),
                        'symbol': feed.get('symbol', 'Unknown')
                    }
            
            if prices:
                # Process the converted data using existing breakout analysis logic
                new_breakouts = []
                processed_count = 0
                
                with self.data_lock:
                    for instrument_key, price_data in prices.items():
                        try:
                            # Ensure instrument exists in our tracking
                            if instrument_key not in self.instruments:
                                self._add_instrument_for_tracking(instrument_key, price_data)
                            
                            breakout = self._update_instrument(instrument_key, price_data)
                            if breakout:
                                new_breakouts.append(breakout)
                                logger.info(f"🚨 BREAKOUT DETECTED: {breakout.symbol} - {breakout.breakout_type.value}")
                                
                            processed_count += 1
                            
                        except Exception as e:
                            logger.debug(f"Error processing centralized breakout for {instrument_key}: {e}")
                
                # Update processing stats
                self.last_scan_time = datetime.now()
                
                # Add new breakouts to daily collection
                if new_breakouts:
                    self.daily_breakouts.extend(new_breakouts)
                    self.breakouts_detected += len(new_breakouts)
                    logger.info(f"🚀 Breakout Scanner: Detected {len(new_breakouts)} new breakouts from centralized feed")
                
        except Exception as e:
            logger.error(f"❌ Error processing centralized data in breakout scanner: {e}")
    
    def _add_instrument_for_tracking(self, instrument_key: str, price_data: Dict[str, Any]):
        """Add instrument to breakout tracking system"""
        try:
            symbol = price_data.get('symbol', instrument_key.split('|')[-1] if '|' in instrument_key else instrument_key)
            
            tracker = InstrumentTracker(
                instrument_key=instrument_key,
                symbol=symbol,
                current_price=price_data.get('last_price', 0),
                open_price=price_data.get('open', 0),
                prev_close=price_data.get('prev_close', 0),
                current_volume=price_data.get('volume', 0)
            )
            
            self.instruments[instrument_key] = tracker
            logger.debug(f"Added {symbol} to breakout tracking")
            
        except Exception as e:
            logger.error(f"Error adding instrument {instrument_key} for breakout tracking: {e}")
    
    def _update_instrument(self, instrument_key: str, price_data: Dict[str, Any]) -> Optional[BreakoutSignal]:
        """Update instrument data and check for breakouts - FIXED WITH DEBUG"""
        try:
            # FIXED: Add debug logging for troubleshooting
            logger.debug(f"Updating instrument {instrument_key}: {price_data}")
            
            # Get or create instrument tracker
            if instrument_key not in self.instruments:
                self.instruments[instrument_key] = InstrumentTracker(
                    instrument_key=instrument_key,
                    symbol=price_data.get("symbol", instrument_key.split("|")[-1])
                )
                logger.debug(f"Created new tracker for {instrument_key}")
            
            tracker = self.instruments[instrument_key]
            
            # Extract price data with fallbacks
            current_price = float(price_data.get("ltp", price_data.get("last_price", 0)))
            volume = int(price_data.get("volume", 0))
            change_percent = float(price_data.get("change_percent", price_data.get("chp", 0)))
            
            logger.debug(f"Extracted: price={current_price}, volume={volume}, change={change_percent}%")
            
            # FIXED: More lenient validation for testing
            if current_price <= 0:
                logger.debug(f"Skipping {instrument_key}: invalid price {current_price}")
                return None
                
            if current_price < self.min_price:
                logger.debug(f"Skipping {instrument_key}: price {current_price} < min {self.min_price}")
                return None
                
            if current_price > self.max_price:
                logger.debug(f"Skipping {instrument_key}: price {current_price} > max {self.max_price}")
                return None
            
            if volume < self.min_volume:
                logger.debug(f"Skipping {instrument_key}: volume {volume} < min {self.min_volume}")
                return None
            
            logger.debug(f"Instrument {instrument_key} passed validation checks")
            
            # Update tracker
            prev_price = tracker.current_price
            tracker.current_price = current_price
            tracker.current_volume = volume
            tracker.last_updated = datetime.now()
            
            # Update daily high/low
            if current_price > tracker.day_high:
                tracker.day_high = current_price
            if current_price < tracker.day_low:
                tracker.day_low = current_price
            
            # Add to price history
            tracker.price_history.append((datetime.now(), current_price, volume))
            tracker.volume_history.append(volume)
            
            # Calculate support/resistance if we have enough data
            if len(tracker.price_history) >= 20:
                self._calculate_support_resistance(tracker)
            
            # Check for breakouts
            return self._check_breakouts(tracker, price_data)
            
        except Exception as e:
            logger.debug(f"Error updating instrument {instrument_key}: {e}")
            return None
    
    def _calculate_support_resistance(self, tracker: InstrumentTracker):
        """Calculate support and resistance levels"""
        try:
            if len(tracker.price_history) < 20:
                return
            
            # Get recent price data
            recent_prices = [price for _, price, _ in list(tracker.price_history)[-20:]]
            
            # Calculate resistance (recent high)
            tracker.resistance_level = max(recent_prices)
            
            # Calculate support (recent low)  
            tracker.support_level = min(recent_prices)
            
        except Exception as e:
            logger.debug(f"Error calculating support/resistance: {e}")
    
    def _check_breakouts(self, tracker: InstrumentTracker, price_data: Dict[str, Any]) -> Optional[BreakoutSignal]:
        """IMPROVED breakout detection with better accuracy"""
        try:
            current_price = tracker.current_price
            volume = tracker.current_volume
            
            # Skip if we just had a breakout (avoid duplicates)
            if (tracker.last_breakout_time and 
                (datetime.now() - tracker.last_breakout_time).total_seconds() < 300):  # 5 minutes
                return None
            
            detected_breakouts = []
            
            # 1. IMPROVED Volume Breakout Detection
            volume_breakout = self._check_volume_breakout_improved(tracker, price_data)
            if volume_breakout:
                detected_breakouts.append(volume_breakout)
            
            # 2. IMPROVED Momentum Breakout Detection  
            momentum_breakout = self._check_momentum_breakout_improved(tracker, price_data)
            if momentum_breakout:
                detected_breakouts.append(momentum_breakout)
            
            # 3. IMPROVED Resistance/Support Breakout Detection
            resistance_breakout = self._check_resistance_breakout_improved(tracker, price_data)
            if resistance_breakout:
                detected_breakouts.append(resistance_breakout)
            
            # 4. NEW: Gap Breakout Detection
            gap_breakout = self._check_gap_breakout(tracker, price_data)
            if gap_breakout:
                detected_breakouts.append(gap_breakout)
            
            # Return the strongest breakout signal
            if detected_breakouts:
                strongest_breakout = max(detected_breakouts, key=lambda x: x['strength'])
                
                # Convert to BreakoutSignal object
                breakout_type_map = {
                    'volume_breakout': BreakoutType.VOLUME_BREAKOUT,
                    'momentum_breakout': BreakoutType.MOMENTUM_BREAKOUT,
                    'resistance_breakout': BreakoutType.RESISTANCE_BREAKOUT,
                    'support_breakdown': BreakoutType.SUPPORT_BREAKDOWN,
                    'gap_up_breakout': BreakoutType.MOMENTUM_BREAKOUT,  # Map to momentum
                    'gap_down_breakout': BreakoutType.SUPPORT_BREAKDOWN,  # Map to support breakdown
                }
                
                breakout_type = breakout_type_map.get(strongest_breakout['type'], BreakoutType.MOMENTUM_BREAKOUT)
                
                return self._create_breakout_signal(
                    tracker, breakout_type,
                    current_price, strongest_breakout['move'], strongest_breakout['strength']
                )
            
            return None
            
        except Exception as e:
            logger.debug(f"Error checking breakouts for {tracker.symbol}: {e}")
            return None
    
    def _create_breakout_signal(self, tracker: InstrumentTracker, breakout_type: BreakoutType,
                              breakout_price: float, percentage_move: float, strength: float) -> BreakoutSignal:
        """Create a breakout signal"""
        signal = BreakoutSignal(
            instrument_key=tracker.instrument_key,
            symbol=tracker.symbol,
            breakout_type=breakout_type,
            current_price=tracker.current_price,
            breakout_price=breakout_price,
            volume=tracker.current_volume,
            percentage_move=percentage_move,
            strength=strength,
            timestamp=datetime.now()
        )
        
        # Add to tracking
        tracker.breakouts_today.append(signal)
        tracker.last_breakout_time = signal.timestamp
        self.daily_breakouts.append(signal)
        self.breakouts_detected += 1
        
        # Add to active breakouts (keep last 50 per type)
        breakout_key = breakout_type.value
        self.active_breakouts[breakout_key].append(signal)
        if len(self.active_breakouts[breakout_key]) > 50:
            self.active_breakouts[breakout_key] = self.active_breakouts[breakout_key][-50:]
        
        logger.info(f"🚨 {breakout_type.value.upper()}: {signal.symbol} @ {signal.current_price:.2f} ({percentage_move:+.2f}%)")
        
        return signal
    
    def _check_volume_breakout_improved(self, tracker: InstrumentTracker, price_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Improved volume breakout detection"""
        try:
            current_volume = tracker.current_volume
            change_percent = abs(float(price_data.get("change_percent", 0)))
            
            # Need at least 10 data points for volume analysis
            if len(tracker.volume_history) < 10:
                return None
            
            # Calculate volume statistics
            recent_volumes = list(tracker.volume_history)[-10:]
            avg_volume = np.mean(recent_volumes)
            volume_std = np.std(recent_volumes)
            
            if avg_volume <= 0:
                return None
            
            # Volume breakout criteria (IMPROVED):
            volume_ratio = current_volume / avg_volume
            volume_z_score = (current_volume - avg_volume) / max(volume_std, avg_volume * 0.1)
            
            # Breakout conditions (ANY of these):
            conditions = [
                volume_ratio >= self.volume_multiplier * 1.5,  # 3x average volume
                volume_z_score >= self.volume_z_threshold,     # 2 standard deviations
                (volume_ratio >= self.volume_multiplier and change_percent >= 1.5),  # 2x volume + 1.5% move
            ]
            
            if any(conditions) and change_percent >= 0.8:  # At least 0.8% price move
                strength = min(10, max(3, volume_ratio * 2))  # Minimum strength 3
                
                return {
                    'type': 'volume_breakout',
                    'strength': strength,
                    'move': change_percent,
                    'volume_ratio': volume_ratio
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Volume breakout check error: {e}")
            return None
    
    def _check_momentum_breakout_improved(self, tracker: InstrumentTracker, price_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Improved momentum breakout detection"""
        try:
            change_percent = float(price_data.get("change_percent", 0))
            current_price = tracker.current_price
            
            # Dynamic threshold based on stock price
            if current_price >= 2000:
                momentum_threshold = self.breakout_threshold * 0.75  # 1.35% for expensive stocks
            elif current_price >= 1000:
                momentum_threshold = self.breakout_threshold  # 1.8% for mid-price stocks
            else:
                momentum_threshold = self.breakout_threshold * 1.25  # 2.25% for cheaper stocks
            
            abs_change = abs(change_percent)
            
            if abs_change >= momentum_threshold:
                # Calculate strength with better scaling
                strength = min(10, max(2, abs_change * 2))
                
                breakout_type = 'momentum_breakout' if change_percent > 0 else 'support_breakdown'
                
                return {
                    'type': breakout_type,
                    'strength': strength,
                    'move': change_percent,
                    'threshold_used': momentum_threshold
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Momentum breakout check error: {e}")
            return None
    
    def _check_resistance_breakout_improved(self, tracker: InstrumentTracker, price_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Improved resistance/support breakout detection"""
        try:
            current_price = tracker.current_price
            
            # Need sufficient price history
            if len(tracker.price_history) < 15:
                return None
            
            # IMPROVED resistance/support calculation using percentile method
            recent_prices = [price for _, price, _ in list(tracker.price_history)[-20:]]
            
            # Calculate resistance and support using percentile method (more robust)
            resistance_level = np.percentile(recent_prices, 90)  # 90th percentile as resistance
            support_level = np.percentile(recent_prices, 10)   # 10th percentile as support
            
            # Alternative: Use recent highs/lows
            recent_high = max(recent_prices[-10:])  # Last 10 periods high
            recent_low = min(recent_prices[-10:])   # Last 10 periods low
            
            # Use the more conservative estimate
            resistance_level = max(resistance_level, recent_high)
            support_level = min(support_level, recent_low)
            
            breakout_buffer = 0.005  # 0.5% buffer for breakout confirmation
            
            # Resistance breakout
            if current_price > resistance_level * (1 + breakout_buffer):
                percentage_move = ((current_price - resistance_level) / resistance_level) * 100
                
                if percentage_move >= 0.3:  # At least 0.3% above resistance
                    strength = min(10, max(4, percentage_move * 3))
                    
                    return {
                        'type': 'resistance_breakout',
                        'strength': strength,
                        'move': percentage_move,
                        'resistance_level': resistance_level
                    }
            
            # Support breakdown
            elif current_price < support_level * (1 - breakout_buffer):
                percentage_move = ((support_level - current_price) / support_level) * 100
                
                if percentage_move >= 0.3:  # At least 0.3% below support
                    strength = min(10, max(4, percentage_move * 3))
                    
                    return {
                        'type': 'support_breakdown',
                        'strength': strength,
                        'move': -percentage_move,  # Negative for breakdown
                        'support_level': support_level
                    }
            
            return None
            
        except Exception as e:
            logger.debug(f"Resistance/support breakout check error: {e}")
            return None
    
    def _check_gap_breakout(self, tracker: InstrumentTracker, price_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """NEW: Gap breakout detection (opening gaps)"""
        try:
            current_price = tracker.current_price
            open_price = float(price_data.get("open", 0))
            prev_close = tracker.prev_close
            
            if open_price <= 0 or prev_close <= 0:
                return None
            
            # Calculate gap percentage
            gap_percent = ((open_price - prev_close) / prev_close) * 100
            
            if abs(gap_percent) >= self.gap_threshold:
                # Check if gap is being sustained
                price_from_open = ((current_price - open_price) / open_price) * 100
                
                # Gap up breakout
                if gap_percent > 0 and price_from_open >= -0.5:  # Not fading significantly
                    strength = min(10, max(3, abs(gap_percent) * 2))
                    
                    return {
                        'type': 'gap_up_breakout',
                        'strength': strength,
                        'move': gap_percent,
                        'open_price': open_price,
                        'prev_close': prev_close
                    }
                
                # Gap down breakout
                elif gap_percent < 0 and price_from_open <= 0.5:  # Not recovering significantly
                    strength = min(10, max(3, abs(gap_percent) * 2))
                    
                    return {
                        'type': 'gap_down_breakout',
                        'strength': strength,
                        'move': gap_percent,
                        'open_price': open_price,
                        'prev_close': prev_close
                    }
            
            return None
            
        except Exception as e:
            logger.debug(f"Gap breakout check error: {e}")
            return None

    async def _broadcast_breakouts(self, breakouts: List[BreakoutSignal]):
        """Broadcast breakout signals to UI via unified manager"""
        try:
            if not self.unified_manager or not breakouts:
                return
            
            # Group breakouts by type
            breakouts_by_type = defaultdict(list)
            for breakout in breakouts:
                breakouts_by_type[breakout.breakout_type.value].append(breakout.to_dict())
            
            # Broadcast to UI
            broadcast_data = {
                "type": "breakout_update",
                "data": {
                    "new_breakouts": [b.to_dict() for b in breakouts],
                    "breakouts_by_type": dict(breakouts_by_type),
                    "total_today": len(self.daily_breakouts),
                    "timestamp": datetime.now().isoformat(),
                    "market_status": "open" if self.is_market_open else "closed"
                }
            }
            
            self.unified_manager.emit_event("breakout_update", broadcast_data, priority=2)
            
            logger.info(f"📡 Broadcasted {len(breakouts)} breakout signals to UI")
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting breakouts: {e}")
    
    async def _scan_loop(self):
        """Background scanning loop"""
        while self.is_running:
            try:
                await asyncio.sleep(10)  # Scan every 10 seconds
                
                # Check if we need to reset for new trading day
                if self._is_new_trading_day():
                    await self._reset_for_new_day()
                
            except Exception as e:
                logger.error(f"❌ Error in scan loop: {e}")
                await asyncio.sleep(5)
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                
                with self.data_lock:
                    # Remove old breakouts (older than 6 hours)
                    cutoff_time = datetime.now() - timedelta(hours=6)
                    
                    for breakout_type in self.active_breakouts:
                        self.active_breakouts[breakout_type] = [
                            b for b in self.active_breakouts[breakout_type]
                            if datetime.fromisoformat(b.timestamp.replace('Z', '+00:00') if isinstance(b.timestamp, str) else b.timestamp.isoformat()) > cutoff_time
                        ]
                
                logger.debug("🧹 Cleaned up old breakout data")
                
            except Exception as e:
                logger.error(f"❌ Error in cleanup loop: {e}")
                await asyncio.sleep(60)
    
    async def _market_status_loop(self):
        """Track market status"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Simple market hours check (9:15 AM to 3:30 PM IST)
                now = datetime.now()
                market_start = now.replace(hour=9, minute=15, second=0, microsecond=0)
                market_end = now.replace(hour=15, minute=30, second=0, microsecond=0)
                
                was_open = self.is_market_open
                self.is_market_open = market_start <= now <= market_end
                
                if was_open != self.is_market_open:
                    status = "opened" if self.is_market_open else "closed"
                    logger.info(f"📈 Market {status} - Breakout scanner adjusted")
                
            except Exception as e:
                logger.error(f"❌ Error checking market status: {e}")
                await asyncio.sleep(60)
    
    def _is_new_trading_day(self) -> bool:
        """Check if it's a new trading day"""
        today = datetime.now().date()
        return today > self.current_trading_day
    
    async def _reset_for_new_day(self):
        """Reset data for new trading day"""
        with self.data_lock:
            # Update current trading day
            self.current_trading_day = datetime.now().date()
            
            # Reset daily breakouts
            self.daily_breakouts = []
            
            # Reset instrument trackers for new day
            for tracker in self.instruments.values():
                tracker.day_high = tracker.current_price
                tracker.day_low = tracker.current_price
                tracker.breakouts_today = []
                tracker.session_start = datetime.now()
            
            # Reset counters
            self.breakouts_detected = 0
            
            logger.info(f"🌅 Reset breakout scanner for new trading day: {self.current_trading_day}")
    
    def get_breakouts_summary(self) -> Dict[str, Any]:
        """Get summary of today's breakouts"""
        with self.data_lock:
            current_time = datetime.now()
            summary = {
                "total_breakouts_today": len(self.daily_breakouts),
                "breakouts_by_type": {},
                "top_breakouts": [],
                "recent_breakouts": [],
                "scanner_stats": {
                    "instruments_tracked": len(self.instruments),
                    "scans_completed": self.scan_count,
                    "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
                    "last_scan_formatted": self.last_scan_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_scan_time else None,
                    "market_status": "open" if self.is_market_open else "closed",
                    "trading_day": self.current_trading_day.isoformat(),
                    "trading_day_formatted": self.current_trading_day.strftime("%Y-%m-%d"),
                    "session_start": datetime.now().replace(hour=9, minute=15).strftime("%Y-%m-%d %H:%M:%S"),
                    "session_end": datetime.now().replace(hour=15, minute=30).strftime("%Y-%m-%d %H:%M:%S")
                },
                "timestamp": current_time.isoformat(),
                "timestamp_formatted": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                "generated_at": current_time.strftime("%I:%M:%S %p"),
                "epoch_timestamp": int(current_time.timestamp())
            }
            
            # Group by breakout type
            for breakout in self.daily_breakouts:
                breakout_type = breakout.breakout_type.value
                if breakout_type not in summary["breakouts_by_type"]:
                    summary["breakouts_by_type"][breakout_type] = []
                summary["breakouts_by_type"][breakout_type].append(breakout.to_dict())
            
            # Top breakouts (by strength)
            top_breakouts = sorted(
                self.daily_breakouts, 
                key=lambda x: x.strength, 
                reverse=True
            )[:20]
            summary["top_breakouts"] = [b.to_dict() for b in top_breakouts]
            
            # Recent breakouts (last 10)
            recent_breakouts = sorted(
                self.daily_breakouts,
                key=lambda x: x.timestamp,
                reverse=True
            )[:10]
            summary["recent_breakouts"] = [b.to_dict() for b in recent_breakouts]
            
            return summary

# Global instance
breakout_scanner = BreakoutScannerService()

async def start_breakout_scanner():
    """Start the breakout scanner service"""
    await breakout_scanner.start()

async def stop_breakout_scanner():
    """Stop the breakout scanner service"""
    await breakout_scanner.stop()

def get_breakouts_data() -> Dict[str, Any]:
    """Get current breakouts data for API"""
    return breakout_scanner.get_breakouts_summary()

# Health check function
def health_check() -> Dict[str, Any]:
    """Health check for the service"""
    return {
        "service": "breakout_scanner",
        "status": "running" if breakout_scanner.is_running else "stopped",
        "market_open": breakout_scanner.is_market_open,
        "instruments_tracked": len(breakout_scanner.instruments),
        "breakouts_today": len(breakout_scanner.daily_breakouts),
        "last_scan": breakout_scanner.last_scan_time.isoformat() if breakout_scanner.last_scan_time else None,
        "timestamp": datetime.now().isoformat()
    }