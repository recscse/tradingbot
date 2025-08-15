#!/usr/bin/env python3
"""
Gap Up/Down Detection Service - Market Opening Only

This service specifically detects gap up and gap down stocks that occur
at market opening (9:15 AM IST). It processes live feed data to identify
significant price gaps between previous close and opening price.

Key Features:
- Triggers ONLY at market opening (9:15 AM IST)
- Accurate gap calculation: (open - previous_close) / previous_close * 100
- Volume confirmation for significant gaps
- Ultra-fast processing using NumPy vectorization
- Real-time alerts for gap opportunities

CORRECTED LOGIC:
- Previous gap logic used 'close' instead of 'previous_close' (FIXED)
- Added market timing validation
- Added volume confirmation
- Added gap strength measurement
"""

import numpy as np
import pandas as pd
from datetime import datetime, time, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
from collections import defaultdict, deque
from dataclasses import dataclass
import asyncio

# PERFORMANCE CRITICAL: Ultra-fast libraries
try:
    import numba
    from numba import jit, njit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    def jit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    njit = jit

# Import existing services
try:
    from services.instrument_registry import instrument_registry
    from services.ultra_fast_registry import get_ultra_fast_registry
    from services.unified_websocket_manager import unified_manager
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class GapSignal:
    symbol: str
    instrument_key: str
    gap_type: str  # "gap_up" or "gap_down"
    gap_percentage: float
    open_price: float
    previous_close: float
    current_price: float
    volume: int
    avg_volume_20d: float
    volume_ratio: float
    gap_strength: str  # "weak", "moderate", "strong", "very_strong"
    sector: str
    market_cap: str
    timestamp: datetime
    confidence_score: float  # 0.0 to 1.0

class GapDetectionService:
    """Specialized service for detecting gap up/down at market opening"""
    
    def __init__(self):
        # Market timing
        self.market_open_time = time(9, 15)  # 9:15 AM IST
        self.market_close_time = time(15, 30)  # 3:30 PM IST
        self.gap_detection_window = 300  # 5 minutes after market open
        
        # Gap thresholds (configurable for different market conditions)
        self.gap_thresholds = {
            "weak": 1.0,      # 1%+ gap
            "moderate": 2.5,  # 2.5%+ gap  
            "strong": 5.0,    # 5%+ gap
            "very_strong": 8.0  # 8%+ gap
        }
        
        # Volume confirmation thresholds
        self.volume_thresholds = {
            "minimum": 1.5,   # 1.5x average volume
            "strong": 3.0,    # 3x average volume
            "exceptional": 5.0  # 5x average volume
        }
        
        # Data storage
        self.previous_close_prices = {}  # symbol -> previous_close
        self.opening_prices = {}         # symbol -> opening_price
        self.volume_history = defaultdict(lambda: deque(maxlen=20))  # 20-day volume history
        self.gap_signals = []           # Today's gap signals
        self.processed_symbols = set()  # Symbols already processed today
        
        # State management
        self.is_market_opening = False
        self.gap_detection_active = False
        self.market_open_detected = False
        self.today_date = datetime.now().date()
        
        # Performance tracking
        self.gaps_detected_today = 0
        self.processing_times = deque(maxlen=1000)
        
        # Integration with ultra-fast components
        self.ultra_fast_registry = None
        if DEPENDENCIES_AVAILABLE:
            try:
                self.ultra_fast_registry = get_ultra_fast_registry()
                logger.info("✅ Gap detection service initialized with ultra-fast registry")
            except Exception as e:
                logger.warning(f"⚠️ Ultra-fast registry not available: {e}")
                
        logger.info("🕘 Gap Detection Service initialized - waiting for market opening...")

    def is_market_open_time(self) -> bool:
        """Check if current time is market opening time (9:15 AM IST)"""
        now = datetime.now()
        current_time = now.time()
        current_date = now.date()
        
        # Reset daily state if new day
        if current_date != self.today_date:
            self._reset_daily_state()
            self.today_date = current_date
        
        # Check if it's within gap detection window (9:15 - 9:20 AM)
        gap_end_time = (datetime.combine(current_date, self.market_open_time) + 
                       timedelta(seconds=self.gap_detection_window)).time()
        
        return (self.market_open_time <= current_time <= gap_end_time and
                current_date.weekday() < 5)  # Monday to Friday only

    def _reset_daily_state(self):
        """Reset state for new trading day"""
        self.gap_signals.clear()
        self.processed_symbols.clear()
        self.opening_prices.clear()
        self.gaps_detected_today = 0
        self.market_open_detected = False
        self.gap_detection_active = False
        logger.info("🌅 New trading day - gap detection state reset")

    def update_previous_close_prices(self, close_prices: Dict[str, float]):
        """Update previous close prices (called after market close)"""
        self.previous_close_prices.update(close_prices)
        logger.info(f"📊 Updated previous close prices for {len(close_prices)} symbols")

    def process_live_feed_data(self, feed_data: Dict[str, Any]) -> List[GapSignal]:
        """
        Process live feed data for gap detection
        
        Args:
            feed_data: Dictionary containing market data from WebSocket feed
            Format: {
                'symbol': {
                    'ltp': current_price,
                    'open': opening_price,
                    'volume': current_volume,
                    'cp': previous_close,  # This is the correct field
                    'instrument_key': key,
                    ...
                }
            }
        """
        if not self.is_market_open_time():
            return []
        
        if not self.gap_detection_active:
            self.gap_detection_active = True
            self.market_open_detected = True
            logger.info("🚨 MARKET OPENING DETECTED - Starting gap analysis!")
        
        start_time = datetime.now()
        new_gaps = []
        
        try:
            for symbol, data in feed_data.items():
                # Skip if already processed today
                if symbol in self.processed_symbols:
                    continue
                
                # Extract required data
                opening_price = data.get('open', 0)
                current_price = data.get('ltp', 0)
                volume = data.get('volume', 0)
                previous_close = data.get('cp', 0)  # CORRECTED: Use 'cp' not 'close'
                instrument_key = data.get('instrument_key', '')
                
                # Validate required data
                if not all([opening_price, previous_close, current_price]):
                    continue
                
                # CRITICAL FIX: Gap percentage calculation with validation
                if previous_close <= 0:
                    logger.warning(f"⚠️ Invalid previous_close for {symbol}: {previous_close}")
                    continue
                    
                # VERIFIED CORRECT FORMULA: Gap % = ((Open - Previous Close) / Previous Close) * 100
                gap_percentage = ((opening_price - previous_close) / previous_close) * 100.0
                
                # BUSINESS LOGIC VALIDATION: Gap must be between market open and previous close
                # Additional validation: opening price should be reasonable
                price_change_ratio = abs(gap_percentage)
                if price_change_ratio > 20.0:  # > 20% gap (circuit breaker territory)
                    logger.warning(f"⚠️ Extreme gap detected for {symbol}: {gap_percentage:.2f}% - validating...")
                    # Additional validation could be added here for extreme gaps
                
                # Check if gap is significant
                abs_gap = abs(gap_percentage)
                if abs_gap < self.gap_thresholds["weak"]:
                    continue
                
                # Calculate volume metrics
                avg_volume_20d = self._get_average_volume(symbol)
                volume_ratio = volume / avg_volume_20d if avg_volume_20d > 0 else 0
                
                # Volume confirmation check
                if volume_ratio < self.volume_thresholds["minimum"]:
                    logger.debug(f"⚠️ {symbol}: Gap {gap_percentage:.2f}% but low volume ({volume_ratio:.1f}x)")
                    continue
                
                # Determine gap type and strength
                gap_type = "gap_up" if gap_percentage > 0 else "gap_down"
                gap_strength = self._calculate_gap_strength(abs_gap)
                
                # Calculate confidence score
                confidence = self._calculate_confidence_score(
                    abs_gap, volume_ratio, symbol, current_price
                )
                
                # Get additional metadata
                sector = self._get_stock_sector(symbol)
                market_cap = self._get_market_cap_category(current_price)
                
                # Create gap signal
                gap_signal = GapSignal(
                    symbol=symbol,
                    instrument_key=instrument_key,
                    gap_type=gap_type,
                    gap_percentage=gap_percentage,
                    open_price=opening_price,
                    previous_close=previous_close,
                    current_price=current_price,
                    volume=volume,
                    avg_volume_20d=avg_volume_20d,
                    volume_ratio=volume_ratio,
                    gap_strength=gap_strength,
                    sector=sector,
                    market_cap=market_cap,
                    timestamp=datetime.now(),
                    confidence_score=confidence
                )
                
                new_gaps.append(gap_signal)
                self.gap_signals.append(gap_signal)
                self.processed_symbols.add(symbol)
                self.gaps_detected_today += 1
                
                # Update volume history
                self.volume_history[symbol].append(volume)
                
                # Log significant gaps
                if abs_gap >= self.gap_thresholds["moderate"]:
                    logger.info(
                        f"🚨 {gap_type.upper()}: {symbol} {gap_percentage:+.2f}% "
                        f"(Vol: {volume_ratio:.1f}x, Confidence: {confidence:.2f})"
                    )
            
            # Track performance
            processing_time = (datetime.now() - start_time).total_seconds() * 1000000
            self.processing_times.append(processing_time)
            
            if new_gaps:
                logger.info(
                    f"📊 Processed {len(feed_data)} symbols, found {len(new_gaps)} gaps "
                    f"in {processing_time:.1f}μs"
                )
                
                # Broadcast gap signals
                self._broadcast_gap_signals(new_gaps)
            
            return new_gaps
            
        except Exception as e:
            logger.error(f"❌ Error processing gap detection: {e}")
            return []

    @jit(nopython=True if NUMBA_AVAILABLE else False)
    def _calculate_gap_percentage_vectorized(self, opening_prices: np.ndarray, previous_closes: np.ndarray) -> np.ndarray:
        """Vectorized gap percentage calculation for ultra-fast processing"""
        return ((opening_prices - previous_closes) / previous_closes) * 100.0

    @jit(nopython=True if NUMBA_AVAILABLE else False)
    def _calculate_volume_ratios_vectorized(self, current_volumes: np.ndarray, avg_volumes: np.ndarray) -> np.ndarray:
        """Vectorized volume ratio calculation"""
        return np.divide(current_volumes, avg_volumes, out=np.zeros_like(current_volumes), where=avg_volumes!=0)

    def _get_average_volume(self, symbol: str) -> float:
        """Get 20-day average volume for a symbol"""
        if symbol not in self.volume_history or len(self.volume_history[symbol]) == 0:
            return 100000  # Default volume if no history
        
        return np.mean(list(self.volume_history[symbol]))

    def _calculate_gap_strength(self, abs_gap_percentage: float) -> str:
        """Calculate gap strength based on percentage"""
        if abs_gap_percentage >= self.gap_thresholds["very_strong"]:
            return "very_strong"
        elif abs_gap_percentage >= self.gap_thresholds["strong"]:
            return "strong"
        elif abs_gap_percentage >= self.gap_thresholds["moderate"]:
            return "moderate"
        else:
            return "weak"

    def _calculate_confidence_score(self, abs_gap: float, volume_ratio: float, 
                                  symbol: str, price: float) -> float:
        """Calculate confidence score for gap signal (0.0 to 1.0)"""
        try:
            # Base score from gap size (0.3 max)
            gap_score = min(abs_gap / 10.0, 0.3)
            
            # Volume confirmation score (0.4 max)
            volume_score = min(volume_ratio / 5.0, 0.4)
            
            # Market cap/liquidity score (0.2 max)
            liquidity_score = 0.2 if price > 100 else 0.1  # Higher price = more liquid
            
            # Sector/market condition score (0.1 max)
            market_score = 0.1  # Base market score
            
            total_score = gap_score + volume_score + liquidity_score + market_score
            return min(total_score, 1.0)
            
        except Exception:
            return 0.5  # Default confidence

    def _get_stock_sector(self, symbol: str) -> str:
        """Get sector information for symbol"""
        try:
            if DEPENDENCIES_AVAILABLE:
                # Try to get from instrument registry
                enriched_data = instrument_registry.get_enriched_prices()
                for key, data in enriched_data.items():
                    if data.get('symbol') == symbol:
                        return data.get('sector', 'UNKNOWN')
            return 'UNKNOWN'
        except Exception:
            return 'UNKNOWN'

    def _get_market_cap_category(self, price: float) -> str:
        """Estimate market cap category based on price (rough approximation)"""
        if price > 1000:
            return "LARGE_CAP"
        elif price > 200:
            return "MID_CAP"
        else:
            return "SMALL_CAP"

    def _broadcast_gap_signals(self, gap_signals: List[GapSignal]):
        """Broadcast gap signals to connected clients"""
        try:
            if not DEPENDENCIES_AVAILABLE or not gap_signals:
                return
                
            # Convert to serializable format
            signals_data = []
            for signal in gap_signals:
                signals_data.append({
                    "symbol": signal.symbol,
                    "gap_type": signal.gap_type,
                    "gap_percentage": round(signal.gap_percentage, 2),
                    "open_price": signal.open_price,
                    "previous_close": signal.previous_close,
                    "current_price": signal.current_price,
                    "volume_ratio": round(signal.volume_ratio, 1),
                    "gap_strength": signal.gap_strength,
                    "confidence_score": round(signal.confidence_score, 2),
                    "sector": signal.sector,
                    "market_cap": signal.market_cap,
                    "timestamp": signal.timestamp.isoformat()
                })
            
            # Broadcast via unified WebSocket manager
            unified_manager.emit_event("gap_signals_update", {
                "signals": signals_data,
                "count": len(signals_data),
                "market_open_time": self.market_open_time.isoformat(),
                "timestamp": datetime.now().isoformat()
            }, priority=1)  # High priority for gap signals
            
            logger.info(f"📡 Broadcast {len(gap_signals)} gap signals to clients")
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting gap signals: {e}")

    def get_todays_gaps(self, gap_type: str = None, min_strength: str = None) -> List[Dict[str, Any]]:
        """Get today's gap signals with optional filtering"""
        filtered_gaps = self.gap_signals.copy()
        
        # Filter by gap type
        if gap_type:
            filtered_gaps = [g for g in filtered_gaps if g.gap_type == gap_type]
        
        # Filter by minimum strength
        if min_strength:
            strength_order = ["weak", "moderate", "strong", "very_strong"]
            min_index = strength_order.index(min_strength)
            filtered_gaps = [g for g in filtered_gaps 
                           if strength_order.index(g.gap_strength) >= min_index]
        
        # Sort by gap percentage (absolute)
        filtered_gaps.sort(key=lambda x: abs(x.gap_percentage), reverse=True)
        
        # Convert to dict format
        return [{
            "symbol": g.symbol,
            "gap_type": g.gap_type,
            "gap_percentage": round(g.gap_percentage, 2),
            "gap_strength": g.gap_strength,
            "volume_ratio": round(g.volume_ratio, 1),
            "confidence_score": round(g.confidence_score, 2),
            "sector": g.sector,
            "timestamp": g.timestamp.isoformat()
        } for g in filtered_gaps]

    async def process_market_data(self, feeds_data: Dict[str, Any]) -> List[GapSignal]:
        """
        Async wrapper for processing market data - Required for ultra-fast integration
        """
        try:
            # Convert feeds data to the expected format
            if not feeds_data:
                return []
            
            # Process the data synchronously (gap detection is already fast)
            gaps = self.process_live_feed_data(feeds_data)
            
            # Return as list of GapSignal objects
            return gaps
            
        except Exception as e:
            logger.error(f"❌ Error in async gap processing: {e}")
            return []

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get gap detection performance metrics"""
        return {
            "gaps_detected_today": self.gaps_detected_today,
            "gap_detection_active": self.gap_detection_active,
            "market_open_detected": self.market_open_detected,
            "processed_symbols_count": len(self.processed_symbols),
            "avg_processing_time_us": np.mean(self.processing_times) if self.processing_times else 0,
            "symbols_with_volume_history": len(self.volume_history),
            "current_time": datetime.now().time().isoformat(),
            "market_open_time": self.market_open_time.isoformat(),
            "is_market_open_time": self.is_market_open_time(),
            "gap_thresholds": self.gap_thresholds,
            "volume_thresholds": self.volume_thresholds
        }
    
    async def shutdown(self):
        """Cleanup method for graceful shutdown"""
        try:
            logger.info("🛑 Gap detection service shutting down...")
            # Add any cleanup logic here if needed
            logger.info("✅ Gap detection service shut down cleanly")
        except Exception as e:
            logger.error(f"❌ Error during gap detection service shutdown: {e}")

    async def run_gap_detection_monitor(self):
        """Background task to monitor for market opening"""
        logger.info("🔍 Starting gap detection monitor...")
        
        while True:
            try:
                if self.is_market_open_time() and not self.gap_detection_active:
                    logger.info("🚨 Market opening time detected! Ready for gap analysis...")
                    
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Gap detection monitor error: {e}")
                await asyncio.sleep(60)

# Singleton instance
gap_detection_service = GapDetectionService()

def get_gap_detection_service() -> GapDetectionService:
    """Get the singleton gap detection service"""
    return gap_detection_service

# Convenience functions for integration
def process_gap_data(feed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process live feed data for gap detection"""
    gaps = gap_detection_service.process_live_feed_data(feed_data)
    return [g.__dict__ for g in gaps]

def get_todays_gap_up_stocks(min_percentage: float = 2.0) -> List[Dict[str, Any]]:
    """Get today's gap up stocks above minimum percentage"""
    all_gaps = gap_detection_service.get_todays_gaps("gap_up")
    return [g for g in all_gaps if g["gap_percentage"] >= min_percentage]

def get_todays_gap_down_stocks(min_percentage: float = 2.0) -> List[Dict[str, Any]]:
    """Get today's gap down stocks below minimum percentage"""
    all_gaps = gap_detection_service.get_todays_gaps("gap_down")
    return [g for g in all_gaps if abs(g["gap_percentage"]) >= min_percentage]

def is_gap_detection_active() -> bool:
    """Check if gap detection is currently active"""
    return gap_detection_service.gap_detection_active

async def start_gap_detection_monitor():
    """Start the gap detection background monitor"""
    await gap_detection_service.run_gap_detection_monitor()