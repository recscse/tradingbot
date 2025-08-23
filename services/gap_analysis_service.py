#!/usr/bin/env python3
"""
Gap Analysis Service - Comprehensive Gap Up/Gap Down Detection

Captures gap up and gap down stocks from Market Data Hub with:
- Real-time gap detection during market open
- Multiple gap categories (small, medium, large gaps)
- Gap sustainability tracking
- Volume analysis for gap confirmation
- Sector-wise gap analysis
- Integration with UI for live updates
"""

import asyncio
import logging
import threading
from datetime import datetime, timedelta, time as datetime_time
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import json

import numpy as np

logger = logging.getLogger(__name__)

class GapType(Enum):
    """Types of gaps detected"""
    GAP_UP_SMALL = "gap_up_small"        # 1-2.5% gap up
    GAP_UP_MEDIUM = "gap_up_medium"      # 2.5-5% gap up
    GAP_UP_LARGE = "gap_up_large"        # >5% gap up
    GAP_DOWN_SMALL = "gap_down_small"    # 1-2.5% gap down
    GAP_DOWN_MEDIUM = "gap_down_medium"  # 2.5-5% gap down
    GAP_DOWN_LARGE = "gap_down_large"    # >5% gap down

class GapSustainability(Enum):
    """Gap sustainability status"""
    SUSTAINING = "sustaining"      # Gap is holding
    FADING = "fading"              # Gap is closing
    FILLED = "filled"              # Gap completely closed
    EXPANDING = "expanding"        # Gap is increasing

@dataclass
class GapSignal:
    """Gap signal data structure"""
    instrument_key: str
    symbol: str
    gap_type: GapType
    gap_percent: float
    gap_points: float
    prev_close: float
    open_price: float
    current_price: float
    volume: int
    sustainability: GapSustainability
    strength_score: float  # 1-10 scale
    timestamp: datetime
    sector: str = "unknown"
    market_cap_category: str = "unknown"
    
    # Gap tracking
    initial_gap_percent: float = 0.0
    max_gap_percent: float = 0.0
    gap_fill_percent: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "instrument_key": self.instrument_key,
            "symbol": self.symbol,
            "gap_type": self.gap_type.value,
            "gap_percent": round(self.gap_percent, 2),
            "gap_points": round(self.gap_points, 2),
            "prev_close": self.prev_close,
            "open_price": self.open_price,
            "current_price": self.current_price,
            "volume": self.volume,
            "sustainability": self.sustainability.value,
            "strength_score": round(self.strength_score, 1),
            "timestamp": self.timestamp.isoformat(),
            "timestamp_formatted": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "date": self.timestamp.strftime("%Y-%m-%d"),
            "time": self.timestamp.strftime("%H:%M:%S"),
            "time_12h": self.timestamp.strftime("%I:%M:%S %p"),
            "sector": self.sector,
            "market_cap_category": self.market_cap_category,
            "time_ago": self._calculate_time_ago(),
            "epoch_timestamp": int(self.timestamp.timestamp()),
            # Gap tracking
            "initial_gap_percent": round(self.initial_gap_percent, 2),
            "max_gap_percent": round(self.max_gap_percent, 2),
            "gap_fill_percent": round(self.gap_fill_percent, 2),
            "gap_direction": "up" if self.gap_percent > 0 else "down",
            "gap_size": self._categorize_gap_size(),
            "confirmation": self._get_confirmation_message()
        }
    
    def _calculate_time_ago(self) -> str:
        """Calculate human readable time ago"""
        now = datetime.now()
        diff = now - self.timestamp
        total_seconds = diff.total_seconds()
        
        if total_seconds < 0:
            return "just now"
        elif total_seconds < 60:
            return f"{int(total_seconds)}s ago"
        elif total_seconds < 3600:
            minutes = int(total_seconds / 60)
            return f"{minutes}m ago"
        elif total_seconds < 86400:
            hours = int(total_seconds / 3600)
            minutes = int((total_seconds % 3600) / 60)
            return f"{hours}h {minutes}m ago" if minutes > 0 else f"{hours}h ago"
        else:
            days = int(total_seconds / 86400)
            return f"{days}d ago"
    
    def _categorize_gap_size(self) -> str:
        """Categorize gap by size"""
        abs_gap = abs(self.gap_percent)
        if abs_gap >= 5:
            return "large"
        elif abs_gap >= 2.5:
            return "medium"
        else:
            return "small"
    
    def _get_confirmation_message(self) -> str:
        """Get confirmation message for the gap"""
        direction = "up" if self.gap_percent > 0 else "down"
        size = self._categorize_gap_size()
        
        if self.sustainability == GapSustainability.SUSTAINING:
            return f"{size.title()} gap {direction} holding strong"
        elif self.sustainability == GapSustainability.FADING:
            return f"{size.title()} gap {direction} showing weakness"
        elif self.sustainability == GapSustainability.FILLED:
            return f"{size.title()} gap {direction} completely filled"
        else:  # EXPANDING
            return f"{size.title()} gap {direction} expanding further"

@dataclass
class InstrumentGapTracker:
    """Track gap data for individual instruments"""
    instrument_key: str
    symbol: str
    
    # Price data
    prev_close: float = 0.0
    open_price: float = 0.0
    current_price: float = 0.0
    day_high: float = 0.0
    day_low: float = 0.0
    
    # Volume data
    current_volume: int = 0
    avg_volume: int = 0
    
    # Gap tracking
    initial_gap_percent: float = 0.0
    current_gap_percent: float = 0.0
    max_gap_percent: float = 0.0
    gap_detected: bool = False
    gap_type: Optional[GapType] = None
    gap_sustainability: GapSustainability = GapSustainability.SUSTAINING
    
    # History
    price_updates: deque = field(default_factory=lambda: deque(maxlen=50))
    gap_signals_today: List[GapSignal] = field(default_factory=list)
    
    # Timestamps
    first_update_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None
    gap_detection_time: Optional[datetime] = None

class GapAnalysisService:
    """Comprehensive Gap Analysis Service using Market Data Hub"""
    
    def __init__(self):
        # Core data structures
        self.instruments: Dict[str, InstrumentGapTracker] = {}
        self.gap_signals: Dict[str, List[GapSignal]] = defaultdict(list)  # by gap type
        self.daily_gaps: List[GapSignal] = []
        
        # Configuration
        self.min_gap_threshold = 1.0        # Minimum 1% gap
        self.small_gap_threshold = 2.5      # Small gap up to 2.5%
        self.medium_gap_threshold = 5.0     # Medium gap up to 5%
        self.min_volume = 10000             # Minimum volume for consideration
        self.min_price = 10.0               # Minimum stock price
        self.max_price = 50000.0            # Maximum stock price
        self.gap_fill_threshold = 0.3       # 30% gap fill considered significant
        
        # Service state
        self.is_running = False
        self.is_market_open = False
        self.current_trading_day = datetime.now().date()
        self.market_open_detected = False
        
        # Market Data Hub connection
        self.market_data_hub = None
        self.unified_manager = None
        self.centralized_manager = None
        
        # Performance tracking
        self.gaps_detected_today = 0
        self.instruments_processed = 0
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
            logger.info("✅ Gap Analysis Service connected to Market Data Hub")
        except ImportError as e:
            logger.error(f"❌ Could not connect to Market Data Hub: {e}")
            self.market_data_hub = None
    
    def _init_unified_manager(self):
        """Initialize connection to Unified WebSocket Manager"""
        try:
            from services.unified_websocket_manager import unified_manager
            self.unified_manager = unified_manager
            logger.info("✅ Gap Analysis Service connected to Unified WebSocket Manager")
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
                logger.info("✅ Gap Analysis registered with Centralized WebSocket Manager")
            else:
                logger.warning("⚠️ Failed to register with Centralized WebSocket Manager")
        except ImportError as e:
            logger.error(f"❌ Could not connect to Centralized Manager: {e}")
            self.centralized_manager = None
    
    async def start(self):
        """Start the gap analysis service"""
        if self.is_running:
            logger.info("📊 Gap Analysis Service already running")
            return
            
        self.is_running = True
        logger.info("🚀 Starting Gap Analysis Service...")
        
        # Initialize unified manager connection
        self._init_unified_manager()
        
        # Initialize centralized manager connection  
        self._init_centralized_manager()
        
        # Register with Market Data Hub for real-time data
        if self.market_data_hub:
            try:
                success = self.market_data_hub.register_consumer(
                    consumer_name="gap_analysis",
                    callback=self._process_market_data,
                    topics=["prices"],
                    priority=2,  # Medium priority
                    max_queue_size=2000
                )
                
                if success:
                    logger.info("📊 Registered with Market Data Hub for gap analysis")
                else:
                    logger.warning("⚠️ Failed to register with Market Data Hub")
                    
            except Exception as e:
                logger.error(f"❌ Error registering with Market Data Hub: {e}")
        
        # Start background tasks
        monitor_task = asyncio.create_task(self._market_monitor_loop())
        cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        self.background_tasks.update([monitor_task, cleanup_task])
        
        logger.info("✅ Gap Analysis Service started successfully")
    
    async def stop(self):
        """Stop the gap analysis service"""
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
        
        logger.info("🛑 Gap Analysis Service stopped")
    
    def _process_market_data(self, data: Dict[str, Any]):
        """Process real-time market data from Market Data Hub"""
        try:
            # FIXED: Handle Market Data Hub format correctly
            prices = None
            
            # Format 1: Market Data Hub atomic broadcast format (most common)
            if isinstance(data, dict) and "prices" in data:
                prices = data["prices"]
                logger.debug(f"Gap Analysis: Processing atomic broadcast with {len(prices)} instruments")
                
            # Format 2: Direct prices data (fallback)
            elif isinstance(data, dict) and any(key.startswith(('NSE_', 'BSE_')) for key in data.keys()):
                prices = data
                logger.debug(f"Gap Analysis: Processing direct prices format with {len(prices)} instruments")
                
            # Format 3: Wrapped in data structure
            elif data.get("type") == "price_update":
                market_data = data.get("data", {})
                prices = market_data.get("prices", {})
                logger.debug(f"Gap Analysis: Processing wrapped format with {len(prices)} instruments")
                
            # Format 4: Hub callback format
            elif "data" in data and isinstance(data["data"], dict):
                if "prices" in data["data"]:
                    prices = data["data"]["prices"]
                else:
                    prices = data["data"]
                logger.debug(f"Gap Analysis: Processing hub callback format with {len(prices)} instruments")
            
            if not prices:
                logger.debug(f"Gap Analysis: No prices found in data: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                return
            
            # Process each instrument
            new_gaps = []
            processed_count = 0
            
            with self.data_lock:
                for instrument_key, price_data in prices.items():
                    try:
                        gap_signal = self._update_instrument_gap(instrument_key, price_data)
                        if gap_signal:
                            new_gaps.append(gap_signal)
                            
                        processed_count += 1
                        
                    except Exception as e:
                        logger.debug(f"Error processing gap for {instrument_key}: {e}")
                        
        except Exception as e:
            logger.error(f"Error processing market data: {e}")
            
    async def _process_centralized_data(self, data: Dict[str, Any]):
        """Process real-time market data from Centralized WebSocket Manager"""
        try:
            # Handle centralized manager feed format
            feeds = None
            
            if isinstance(data, dict) and "feeds" in data:
                feeds = data["feeds"]
                logger.debug(f"Gap Analysis: Processing centralized feed with {len(feeds)} updates")
            elif isinstance(data, list):
                feeds = data
                logger.debug(f"Gap Analysis: Processing direct feed list with {len(feeds)} updates")
            
            if not feeds:
                logger.debug(f"Gap Analysis: No feeds found in centralized data")
                return
            
            # Convert feeds to price format for gap analysis
            prices = {}
            for feed in feeds:
                instrument_key = feed.get('instrument_key')
                if instrument_key:
                    # Convert to standard price format
                    prices[instrument_key] = {
                        'instrument_key': instrument_key,
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
                # Process the converted data using existing gap analysis logic
                new_gaps = []
                processed_count = 0
                
                with self.data_lock:
                    for instrument_key, price_data in prices.items():
                        try:
                            # Ensure instrument exists in our tracking
                            if instrument_key not in self.instruments:
                                self._add_instrument_for_tracking(instrument_key, price_data)
                            
                            gap_signal = self._update_instrument_gap(instrument_key, price_data)
                            if gap_signal:
                                new_gaps.append(gap_signal)
                                
                            processed_count += 1
                            
                        except Exception as e:
                            logger.debug(f"Error processing centralized gap for {instrument_key}: {e}")
                
                # Update processing stats
                self.instruments_processed += processed_count
                self.last_scan_time = datetime.now()
                
                # Add new gaps to daily collection
                if new_gaps:
                    self.daily_gaps.extend(new_gaps)
                    self.gaps_detected_today += len(new_gaps)
                    logger.info(f"📈 Gap Analysis: Detected {len(new_gaps)} new gaps from centralized feed")
                
        except Exception as e:
            logger.error(f"❌ Error processing centralized data: {e}")
    
    def _add_instrument_for_tracking(self, instrument_key: str, price_data: Dict[str, Any]):
        """Add instrument to gap tracking system"""
        try:
            symbol = price_data.get('symbol', instrument_key.split('|')[-1] if '|' in instrument_key else instrument_key)
            
            tracker = InstrumentGapTracker(
                instrument_key=instrument_key,
                symbol=symbol,
                prev_close=price_data.get('prev_close', 0),
                current_price=price_data.get('last_price', 0),
                current_volume=price_data.get('volume', 0)
            )
            
            self.instruments[instrument_key] = tracker
            logger.debug(f"Added {symbol} to gap tracking")
            
        except Exception as e:
            logger.error(f"Error adding instrument {instrument_key} for tracking: {e}")
    
    def _update_instrument_gap(self, instrument_key: str, price_data: Dict[str, Any]) -> Optional[GapSignal]:
        """Update instrument gap data and detect gaps"""
        try:
            # Extract price data - handle Market Data Hub format
            current_price = float(price_data.get("ltp", price_data.get("last_price", 0)))
            open_price = float(price_data.get("open", 0))
            prev_close = float(price_data.get("cp", price_data.get("close", 0)))
            volume = int(price_data.get("volume", 0))
            
            logger.debug(f"Gap Analysis: {instrument_key} - LTP: {current_price}, Open: {open_price}, Close: {prev_close}, Volume: {volume}")
            
            # Validation
            if current_price <= 0 or open_price <= 0 or prev_close <= 0:
                return None
                
            if current_price < self.min_price or current_price > self.max_price:
                return None
                
            if volume < self.min_volume:
                return None
            
            # Get or create tracker
            if instrument_key not in self.instruments:
                symbol = price_data.get("symbol", instrument_key.split("|")[-1])
                self.instruments[instrument_key] = InstrumentGapTracker(
                    instrument_key=instrument_key,
                    symbol=symbol
                )
            
            tracker = self.instruments[instrument_key]
            
            # Update tracker data
            tracker.current_price = current_price
            tracker.current_volume = volume
            tracker.last_update_time = datetime.now()
            
            # Set initial data on first update
            if tracker.first_update_time is None:
                tracker.first_update_time = datetime.now()
                tracker.prev_close = prev_close
                tracker.open_price = open_price
                tracker.day_high = current_price
                tracker.day_low = current_price
                
                # Calculate initial gap
                if prev_close > 0 and open_price > 0:
                    tracker.initial_gap_percent = ((open_price - prev_close) / prev_close) * 100
                    tracker.current_gap_percent = tracker.initial_gap_percent
                    tracker.max_gap_percent = tracker.initial_gap_percent
                    
                    # Detect gap on first update
                    return self._detect_gap(tracker, price_data)
            else:
                # Update high/low
                if current_price > tracker.day_high:
                    tracker.day_high = current_price
                if current_price < tracker.day_low:
                    tracker.day_low = current_price
                    
                # Update current gap percentage
                if tracker.prev_close > 0:
                    tracker.current_gap_percent = ((current_price - tracker.prev_close) / tracker.prev_close) * 100
                    
                    # Update max gap
                    if abs(tracker.current_gap_percent) > abs(tracker.max_gap_percent):
                        tracker.max_gap_percent = tracker.current_gap_percent
                
                # Update existing gap sustainability
                if tracker.gap_detected:
                    self._update_gap_sustainability(tracker)
            
            # Add to price history
            tracker.price_updates.append({
                'timestamp': datetime.now(),
                'price': current_price,
                'volume': volume
            })
            
            return None
            
        except Exception as e:
            logger.debug(f"Error updating gap for {instrument_key}: {e}")
            return None
    
    def _detect_gap(self, tracker: InstrumentGapTracker, price_data: Dict[str, Any]) -> Optional[GapSignal]:
        """Detect gap in instrument"""
        try:
            gap_percent = tracker.initial_gap_percent
            
            # Check if gap meets threshold
            if abs(gap_percent) < self.min_gap_threshold:
                return None
            
            # Determine gap type
            gap_type = self._classify_gap_type(gap_percent)
            if gap_type is None:
                return None
            
            # Calculate strength score
            strength_score = self._calculate_gap_strength(tracker, price_data)
            
            # Determine initial sustainability
            sustainability = self._assess_initial_sustainability(tracker)
            
            # Create gap signal
            gap_signal = GapSignal(
                instrument_key=tracker.instrument_key,
                symbol=tracker.symbol,
                gap_type=gap_type,
                gap_percent=gap_percent,
                gap_points=tracker.open_price - tracker.prev_close,
                prev_close=tracker.prev_close,
                open_price=tracker.open_price,
                current_price=tracker.current_price,
                volume=tracker.current_volume,
                sustainability=sustainability,
                strength_score=strength_score,
                timestamp=datetime.now(),
                sector=price_data.get("sector", "unknown"),
                market_cap_category=self._categorize_by_price(tracker.current_price),
                initial_gap_percent=gap_percent,
                max_gap_percent=gap_percent
            )
            
            # Mark gap detected
            tracker.gap_detected = True
            tracker.gap_type = gap_type
            tracker.gap_detection_time = datetime.now()
            tracker.gap_sustainability = sustainability
            tracker.gap_signals_today.append(gap_signal)
            
            # Add to daily gaps
            self.daily_gaps.append(gap_signal)
            
            # Add to categorized gaps
            self.gap_signals[gap_type.value].append(gap_signal)
            
            # Keep only last 100 gaps per type
            if len(self.gap_signals[gap_type.value]) > 100:
                self.gap_signals[gap_type.value] = self.gap_signals[gap_type.value][-100:]
            
            self.gaps_detected_today += 1
            
            logger.info(f"🔍 GAP DETECTED: {tracker.symbol} - {gap_type.value} - {gap_percent:+.2f}%")
            
            return gap_signal
            
        except Exception as e:
            logger.debug(f"Error detecting gap for {tracker.symbol}: {e}")
            return None
    
    def _classify_gap_type(self, gap_percent: float) -> Optional[GapType]:
        """Classify gap type based on percentage"""
        abs_gap = abs(gap_percent)
        
        if abs_gap < self.min_gap_threshold:
            return None
        
        if gap_percent > 0:  # Gap up
            if abs_gap >= self.medium_gap_threshold:
                return GapType.GAP_UP_LARGE
            elif abs_gap >= self.small_gap_threshold:
                return GapType.GAP_UP_MEDIUM
            else:
                return GapType.GAP_UP_SMALL
        else:  # Gap down
            if abs_gap >= self.medium_gap_threshold:
                return GapType.GAP_DOWN_LARGE
            elif abs_gap >= self.small_gap_threshold:
                return GapType.GAP_DOWN_MEDIUM
            else:
                return GapType.GAP_DOWN_SMALL
    
    def _calculate_gap_strength(self, tracker: InstrumentGapTracker, price_data: Dict[str, Any]) -> float:
        """Calculate gap strength score (1-10)"""
        try:
            abs_gap = abs(tracker.initial_gap_percent)
            volume = tracker.current_volume
            
            # Base strength from gap size
            strength = min(8.0, abs_gap * 1.5)
            
            # Volume boost
            if volume > 100000:
                strength += 1.0
            elif volume > 500000:
                strength += 1.5
            elif volume > 1000000:
                strength += 2.0
            
            # Price level adjustment
            price = tracker.current_price
            if price >= 1000:
                strength *= 1.1  # High-priced stocks get slight boost
            elif price < 50:
                strength *= 0.9  # Low-priced stocks get slight penalty
            
            return max(1.0, min(10.0, strength))
            
        except Exception:
            return 5.0  # Default strength
    
    def _assess_initial_sustainability(self, tracker: InstrumentGapTracker) -> GapSustainability:
        """Assess initial gap sustainability"""
        try:
            # Check if price is moving away from or toward the gap
            gap_direction = 1 if tracker.initial_gap_percent > 0 else -1
            price_movement = ((tracker.current_price - tracker.open_price) / tracker.open_price) * 100
            
            # If price is moving in same direction as gap, it's sustaining
            if (gap_direction > 0 and price_movement > 0.2) or (gap_direction < 0 and price_movement < -0.2):
                return GapSustainability.EXPANDING
            elif (gap_direction > 0 and price_movement < -0.5) or (gap_direction < 0 and price_movement > 0.5):
                return GapSustainability.FADING
            else:
                return GapSustainability.SUSTAINING
                
        except Exception:
            return GapSustainability.SUSTAINING
    
    def _update_gap_sustainability(self, tracker: InstrumentGapTracker):
        """Update gap sustainability based on current price"""
        try:
            if not tracker.gap_detected or tracker.prev_close <= 0:
                return
            
            # Calculate how much of the gap is filled
            if tracker.initial_gap_percent > 0:  # Gap up
                if tracker.current_price <= tracker.prev_close:
                    tracker.gap_sustainability = GapSustainability.FILLED
                elif tracker.current_price < tracker.open_price * 0.7 + tracker.prev_close * 0.3:
                    tracker.gap_sustainability = GapSustainability.FADING
                elif tracker.current_price > tracker.open_price:
                    tracker.gap_sustainability = GapSustainability.EXPANDING
                else:
                    tracker.gap_sustainability = GapSustainability.SUSTAINING
            else:  # Gap down
                if tracker.current_price >= tracker.prev_close:
                    tracker.gap_sustainability = GapSustainability.FILLED
                elif tracker.current_price > tracker.open_price * 0.7 + tracker.prev_close * 0.3:
                    tracker.gap_sustainability = GapSustainability.FADING
                elif tracker.current_price < tracker.open_price:
                    tracker.gap_sustainability = GapSustainability.EXPANDING
                else:
                    tracker.gap_sustainability = GapSustainability.SUSTAINING
            
            # Calculate gap fill percentage
            if tracker.initial_gap_percent != 0:
                fill_amount = tracker.current_price - tracker.open_price
                gap_size = tracker.open_price - tracker.prev_close
                if gap_size != 0:
                    fill_percent = abs(fill_amount / gap_size) * 100
                    tracker.gap_fill_percent = min(100, fill_percent)
                    
        except Exception as e:
            logger.debug(f"Error updating gap sustainability: {e}")
    
    def _categorize_by_price(self, price: float) -> str:
        """Categorize stock by price range"""
        if price >= 2000:
            return "large_cap"
        elif price >= 500:
            return "mid_cap"
        else:
            return "small_cap"
    
    async def _broadcast_gaps(self, gap_signals: List[GapSignal]):
        """Broadcast gap signals to UI via unified manager"""
        try:
            if not self.unified_manager or not gap_signals:
                return
            
            # Group gaps by type
            gaps_by_type = defaultdict(list)
            for gap in gap_signals:
                gaps_by_type[gap.gap_type.value].append(gap.to_dict())
            
            # Separate gap up and gap down
            gap_up_signals = []
            gap_down_signals = []
            
            for gap in gap_signals:
                gap_dict = gap.to_dict()
                if gap.gap_percent > 0:
                    gap_up_signals.append(gap_dict)
                else:
                    gap_down_signals.append(gap_dict)
            
            # Broadcast to UI
            broadcast_data = {
                "type": "gap_analysis_update",
                "data": {
                    "new_gaps": [g.to_dict() for g in gap_signals],
                    "gap_up": gap_up_signals,
                    "gap_down": gap_down_signals,
                    "gaps_by_type": dict(gaps_by_type),
                    "total_gaps_today": len(self.daily_gaps),
                    "gaps_detected_today": self.gaps_detected_today,
                    "timestamp": datetime.now().isoformat(),
                    "market_status": "open" if self.is_market_open else "closed"
                }
            }
            
            self.unified_manager.emit_event("gap_analysis_update", broadcast_data, priority=2)
            
            logger.info(f"📡 Broadcasted {len(gap_signals)} gap signals to UI")
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting gaps: {e}")
    
    async def _market_monitor_loop(self):
        """Monitor market status and detect market open"""
        while self.is_running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Check if new trading day
                if self._is_new_trading_day():
                    await self._reset_for_new_day()
                
                # Update market status
                was_open = self.is_market_open
                self.is_market_open = self._is_market_hours()
                
                # Detect market open
                if not was_open and self.is_market_open:
                    self.market_open_detected = True
                    logger.info("📈 Market opened - Gap analysis active")
                elif was_open and not self.is_market_open:
                    logger.info("📈 Market closed - Gap analysis will continue monitoring")
                
            except Exception as e:
                logger.error(f"❌ Error in market monitor loop: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_loop(self):
        """Background cleanup of old data"""
        while self.is_running:
            try:
                await asyncio.sleep(600)  # Clean every 10 minutes
                
                with self.data_lock:
                    # Remove old gaps (older than 24 hours)
                    cutoff_time = datetime.now() - timedelta(hours=24)
                    
                    for gap_type in self.gap_signals:
                        self.gap_signals[gap_type] = [
                            gap for gap in self.gap_signals[gap_type]
                            if gap.timestamp > cutoff_time
                        ]
                    
                    # Clean up instrument trackers with no recent activity
                    inactive_instruments = []
                    for instrument_key, tracker in self.instruments.items():
                        if (tracker.last_update_time and 
                            (datetime.now() - tracker.last_update_time).total_seconds() > 7200):  # 2 hours
                            inactive_instruments.append(instrument_key)
                    
                    for instrument_key in inactive_instruments:
                        del self.instruments[instrument_key]
                    
                    if inactive_instruments:
                        logger.info(f"🧹 Cleaned up {len(inactive_instruments)} inactive instruments")
                
            except Exception as e:
                logger.error(f"❌ Error in cleanup loop: {e}")
                await asyncio.sleep(300)
    
    def _is_market_hours(self) -> bool:
        """Check if current time is within market hours"""
        now = datetime.now()
        market_start = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_end = now.replace(hour=15, minute=30, second=0, microsecond=0)
        return market_start <= now <= market_end
    
    def _is_new_trading_day(self) -> bool:
        """Check if it's a new trading day"""
        today = datetime.now().date()
        return today > self.current_trading_day
    
    async def _reset_for_new_day(self):
        """Reset data for new trading day"""
        with self.data_lock:
            # Update current trading day
            self.current_trading_day = datetime.now().date()
            
            # Reset daily data
            self.daily_gaps = []
            self.gaps_detected_today = 0
            self.market_open_detected = False
            
            # Clear gap signals but keep structure
            for gap_type in self.gap_signals:
                self.gap_signals[gap_type] = []
            
            # Reset instrument trackers
            instruments_to_reset = list(self.instruments.keys())
            for instrument_key in instruments_to_reset:
                tracker = self.instruments[instrument_key]
                tracker.gap_detected = False
                tracker.gap_type = None
                tracker.gap_sustainability = GapSustainability.SUSTAINING
                tracker.gap_signals_today = []
                tracker.first_update_time = None
                tracker.gap_detection_time = None
                tracker.initial_gap_percent = 0.0
                tracker.current_gap_percent = 0.0
                tracker.max_gap_percent = 0.0
                tracker.gap_fill_percent = 0.0
                tracker.price_updates.clear()
            
            logger.info(f"🌅 Reset gap analysis for new trading day: {self.current_trading_day}")
    
    def get_gap_summary(self) -> Dict[str, Any]:
        """Get comprehensive gap analysis summary"""
        with self.data_lock:
            current_time = datetime.now()
            
            # Categorize gaps
            gap_up_small = [g.to_dict() for g in self.daily_gaps if g.gap_type in [GapType.GAP_UP_SMALL]]
            gap_up_medium = [g.to_dict() for g in self.daily_gaps if g.gap_type in [GapType.GAP_UP_MEDIUM]]
            gap_up_large = [g.to_dict() for g in self.daily_gaps if g.gap_type in [GapType.GAP_UP_LARGE]]
            
            gap_down_small = [g.to_dict() for g in self.daily_gaps if g.gap_type in [GapType.GAP_DOWN_SMALL]]
            gap_down_medium = [g.to_dict() for g in self.daily_gaps if g.gap_type in [GapType.GAP_DOWN_MEDIUM]]
            gap_down_large = [g.to_dict() for g in self.daily_gaps if g.gap_type in [GapType.GAP_DOWN_LARGE]]
            
            # Combined categories
            all_gap_up = gap_up_small + gap_up_medium + gap_up_large
            all_gap_down = gap_down_small + gap_down_medium + gap_down_large
            
            # Sort by gap percentage
            all_gap_up.sort(key=lambda x: x['gap_percent'], reverse=True)
            all_gap_down.sort(key=lambda x: x['gap_percent'])
            
            # Recent gaps (last 2 hours)
            recent_cutoff = current_time - timedelta(hours=2)
            recent_gaps = [
                g.to_dict() for g in self.daily_gaps 
                if g.timestamp > recent_cutoff
            ]
            recent_gaps.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Sector analysis
            sector_gaps = defaultdict(lambda: {'gap_up': 0, 'gap_down': 0, 'total': 0})
            for gap in self.daily_gaps:
                sector = gap.sector
                if gap.gap_percent > 0:
                    sector_gaps[sector]['gap_up'] += 1
                else:
                    sector_gaps[sector]['gap_down'] += 1
                sector_gaps[sector]['total'] += 1
            
            # Sustainability analysis
            sustaining_gaps = len([g for g in self.daily_gaps if g.sustainability == GapSustainability.SUSTAINING])
            fading_gaps = len([g for g in self.daily_gaps if g.sustainability == GapSustainability.FADING])
            filled_gaps = len([g for g in self.daily_gaps if g.sustainability == GapSustainability.FILLED])
            expanding_gaps = len([g for g in self.daily_gaps if g.sustainability == GapSustainability.EXPANDING])
            
            summary = {
                # Main gap categories
                "gap_up": {
                    "all": all_gap_up[:50],  # Top 50
                    "small": gap_up_small,
                    "medium": gap_up_medium,
                    "large": gap_up_large,
                    "count": {
                        "total": len(all_gap_up),
                        "small": len(gap_up_small),
                        "medium": len(gap_up_medium),
                        "large": len(gap_up_large)
                    }
                },
                "gap_down": {
                    "all": all_gap_down[:50],  # Top 50
                    "small": gap_down_small,
                    "medium": gap_down_medium,
                    "large": gap_down_large,
                    "count": {
                        "total": len(all_gap_down),
                        "small": len(gap_down_small),
                        "medium": len(gap_down_medium),
                        "large": len(gap_down_large)
                    }
                },
                
                # Recent activity
                "recent_gaps": recent_gaps[:30],
                
                # Overall statistics
                "statistics": {
                    "total_gaps_today": len(self.daily_gaps),
                    "gap_up_total": len(all_gap_up),
                    "gap_down_total": len(all_gap_down),
                    "instruments_tracked": len(self.instruments),
                    "instruments_processed": self.instruments_processed,
                    "gaps_detected_today": self.gaps_detected_today,
                    "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
                    "market_status": "open" if self.is_market_open else "closed",
                    "trading_day": self.current_trading_day.isoformat(),
                },
                
                # Sustainability analysis
                "sustainability": {
                    "sustaining": sustaining_gaps,
                    "fading": fading_gaps,
                    "filled": filled_gaps,
                    "expanding": expanding_gaps,
                    "total": len(self.daily_gaps)
                },
                
                # Sector analysis
                "sector_analysis": dict(sector_gaps),
                
                # Top performers
                "top_gap_up": all_gap_up[:10],
                "top_gap_down": all_gap_down[:10],
                
                # Timestamps
                "timestamp": current_time.isoformat(),
                "timestamp_formatted": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                "generated_at": current_time.strftime("%I:%M:%S %p"),
                "epoch_timestamp": int(current_time.timestamp())
            }
            
            return summary

# Global instance
gap_analysis_service = GapAnalysisService()

async def start_gap_analysis():
    """Start the gap analysis service"""
    await gap_analysis_service.start()

async def stop_gap_analysis():
    """Stop the gap analysis service"""
    await gap_analysis_service.stop()

def get_gap_data() -> Dict[str, Any]:
    """Get current gap analysis data for API"""
    return gap_analysis_service.get_gap_summary()

# Health check function
def health_check() -> Dict[str, Any]:
    """Health check for the gap analysis service"""
    return {
        "service": "gap_analysis",
        "status": "running" if gap_analysis_service.is_running else "stopped",
        "market_open": gap_analysis_service.is_market_open,
        "instruments_tracked": len(gap_analysis_service.instruments),
        "gaps_detected_today": gap_analysis_service.gaps_detected_today,
        "last_scan": gap_analysis_service.last_scan_time.isoformat() if gap_analysis_service.last_scan_time else None,
        "timestamp": datetime.now().isoformat()
    }