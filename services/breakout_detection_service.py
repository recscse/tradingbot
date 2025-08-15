#!/usr/bin/env python3
"""
Breakout/Breakdown Detection Service - Real-Time Analysis

This service detects real-time breakouts and breakdowns using proper
support/resistance levels, volume confirmation, and time-based validation.

Key Features:
- Dynamic support/resistance calculation using 20/50 period highs/lows
- Volume confirmation with dynamic average calculation
- Time-based breakout validation (during trading hours)
- Breakout strength measurement
- Ultra-fast processing using NumPy vectorization
- Real-time alerts for breakout opportunities

CORRECTED LOGIC:
- Previous logic used placeholder avg_volume (FIXED)
- Added proper support/resistance level calculation
- Added breakdown detection (was missing)
- Added breakout strength and confidence scoring
- Added time-based validation for breakouts
"""

import numpy as np
import pandas as pd
from datetime import datetime, time, timedelta
from typing import Dict, List, Any, Optional, Tuple, Deque
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
class BreakoutSignal:
    symbol: str
    instrument_key: str
    breakout_type: str  # "breakout" or "breakdown"
    current_price: float
    resistance_level: float  # For breakouts
    support_level: float     # For breakdowns
    breakout_strength: float  # How far above resistance/below support
    volume: int
    avg_volume_20d: float
    volume_ratio: float
    price_momentum: float    # Recent price momentum
    breakout_quality: str    # "weak", "moderate", "strong", "very_strong"
    time_since_level: int    # Minutes since price was at this level
    sector: str
    market_cap: str
    timestamp: datetime  # Exact moment breakout was detected
    breakout_time: str   # Human-readable time format
    breakout_date: str   # Human-readable date format
    confidence_score: float  # 0.0 to 1.0
    metadata: Dict[str, Any]

class BreakoutDetectionService:
    """Real-time breakout and breakdown detection service"""
    
    def __init__(self):
        # Market timing
        self.market_open_time = time(9, 15)   # 9:15 AM IST
        self.market_close_time = time(15, 30) # 3:30 PM IST
        
        # Price history for support/resistance calculation
        self.price_history = defaultdict(lambda: deque(maxlen=100))      # Recent 100 ticks
        self.ohlc_history = defaultdict(lambda: deque(maxlen=50))        # Daily OHLC for 50 days
        self.volume_history = defaultdict(lambda: deque(maxlen=20))       # 20-day volume history
        
        # Breakout detection parameters
        self.lookback_periods = {
            "short": 20,    # 20-period high/low for immediate levels
            "medium": 50,   # 50-period high/low for intermediate levels
            "long": 100     # 100-period high/low for major levels
        }
        
        # Breakout thresholds
        self.breakout_thresholds = {
            "minimum_breach": 0.2,    # 0.2% minimum breach above resistance
            "weak": 0.5,              # 0.5% breach
            "moderate": 1.0,          # 1.0% breach  
            "strong": 2.0,            # 2.0% breach
            "very_strong": 3.0        # 3.0% breach
        }
        
        # Volume confirmation thresholds
        self.volume_thresholds = {
            "minimum": 1.3,      # 1.3x average volume
            "moderate": 2.0,     # 2x average volume
            "strong": 3.0,       # 3x average volume
            "exceptional": 5.0   # 5x average volume
        }
        
        # Data storage
        self.active_breakouts = []          # Current breakout signals
        self.todays_breakouts = []          # All breakouts today
        self.support_resistance_levels = {} # symbol -> {"support": [levels], "resistance": [levels]}
        
        # Performance tracking
        self.breakouts_detected_today = 0
        self.processing_times = deque(maxlen=1000)
        self.symbols_monitored = set()
        
        # State management
        self.is_market_hours = False
        self.detection_active = True
        
        # Integration with ultra-fast components
        self.ultra_fast_registry = None
        if DEPENDENCIES_AVAILABLE:
            try:
                self.ultra_fast_registry = get_ultra_fast_registry()
                logger.info("✅ Breakout detection service initialized with ultra-fast registry")
            except Exception as e:
                logger.warning(f"⚠️ Ultra-fast registry not available: {e}")
                
        logger.info("📈 Breakout Detection Service initialized")

    def is_trading_hours(self) -> bool:
        """Check if current time is during trading hours"""
        now = datetime.now()
        current_time = now.time()
        current_date = now.date()
        
        # Monday to Friday only
        if current_date.weekday() >= 5:
            return False
            
        return self.market_open_time <= current_time <= self.market_close_time

    def update_price_data(self, symbol: str, price: float, volume: int, 
                         ohlc_data: Optional[Dict[str, float]] = None):
        """Update price and volume data for a symbol"""
        try:
            # Update price history
            self.price_history[symbol].append({
                'price': price,
                'volume': volume,
                'timestamp': datetime.now()
            })
            
            # Update volume history
            self.volume_history[symbol].append(volume)
            
            # Update OHLC if provided
            if ohlc_data:
                self.ohlc_history[symbol].append({
                    'open': ohlc_data.get('open', price),
                    'high': ohlc_data.get('high', price),
                    'low': ohlc_data.get('low', price),
                    'close': price,
                    'volume': volume,
                    'timestamp': datetime.now()
                })
            
            self.symbols_monitored.add(symbol)
            
        except Exception as e:
            logger.error(f"❌ Error updating price data for {symbol}: {e}")

    @jit(nopython=True if NUMBA_AVAILABLE else False)
    def _calculate_support_resistance_vectorized(self, prices: np.ndarray, periods: np.ndarray) -> tuple:
        """Ultra-fast vectorized support/resistance calculation"""
        resistance_levels = np.zeros(len(periods))
        support_levels = np.zeros(len(periods))
        
        for i, period in enumerate(periods):
            if len(prices) >= period:
                recent_prices = prices[-period:]
                resistance_levels[i] = np.max(recent_prices)
                support_levels[i] = np.min(recent_prices)
        
        return resistance_levels, support_levels

    @jit(nopython=True if NUMBA_AVAILABLE else False) 
    def _calculate_breakout_strength_vectorized(self, current_prices: np.ndarray, 
                                               resistance_levels: np.ndarray) -> np.ndarray:
        """Ultra-fast vectorized breakout strength calculation"""
        return ((current_prices - resistance_levels) / resistance_levels) * 100.0

    def calculate_support_resistance_levels(self, symbol: str) -> Dict[str, List[float]]:
        """Calculate dynamic support and resistance levels using ultra-fast vectorization"""
        try:
            if symbol not in self.price_history or len(self.price_history[symbol]) < 20:
                return {"support": [], "resistance": []}
            
            # Get recent price data
            price_data = list(self.price_history[symbol])
            prices = np.array([p['price'] for p in price_data], dtype=np.float64)
            
            # Ultra-fast vectorized calculation
            periods = np.array(list(self.lookback_periods.values()), dtype=np.int32)
            resistance_levels, support_levels = self._calculate_support_resistance_vectorized(prices, periods)
            
            # Remove zeros and duplicates, then sort
            resistance_list = sorted(list(set(resistance_levels[resistance_levels > 0])), reverse=True)
            support_list = sorted(list(set(support_levels[support_levels > 0])))
            
            # Store calculated levels
            self.support_resistance_levels[symbol] = {
                "support": support_list,
                "resistance": resistance_list,
                "calculated_at": datetime.now()
            }
            
            return {"support": support_list, "resistance": resistance_list}
            
        except Exception as e:
            logger.error(f"❌ Error calculating support/resistance for {symbol}: {e}")
            return {"support": [], "resistance": []}

    def detect_breakout_breakdown(self, symbol: str, current_price: float, 
                                 volume: int) -> Optional[BreakoutSignal]:
        """Detect breakout or breakdown for a symbol"""
        try:
            # Only detect during trading hours AND when detection is active
            if not self.is_trading_hours() or not self.detection_active:
                return None
                
            # Need minimum price history
            if symbol not in self.price_history or len(self.price_history[symbol]) < 20:
                return None
            
            # Calculate support/resistance levels
            levels = self.calculate_support_resistance_levels(symbol)
            if not levels["support"] and not levels["resistance"]:
                return None
            
            # Get average volume
            avg_volume = self._get_average_volume(symbol)
            volume_ratio = volume / avg_volume if avg_volume > 0 else 0
            
            # Check volume confirmation
            if volume_ratio < self.volume_thresholds["minimum"]:
                return None
            
            # Check for breakout (price above resistance)
            breakout_detected = False
            breakdown_detected = False
            relevant_level = 0
            breakout_type = ""
            
            # Check resistance breakout
            for resistance in levels["resistance"]:
                if current_price > resistance:
                    breach_percentage = ((current_price - resistance) / resistance) * 100
                    if breach_percentage >= self.breakout_thresholds["minimum_breach"]:
                        breakout_detected = True
                        relevant_level = resistance
                        breakout_type = "breakout"
                        break
            
            # Check support breakdown
            if not breakout_detected:
                for support in levels["support"]:
                    if current_price < support:
                        breach_percentage = ((support - current_price) / support) * 100
                        if breach_percentage >= self.breakout_thresholds["minimum_breach"]:
                            breakdown_detected = True
                            relevant_level = support
                            breakout_type = "breakdown"
                            break
            
            # If no breakout/breakdown detected
            if not (breakout_detected or breakdown_detected):
                return None
            
            # Calculate breakout strength
            if breakout_detected:
                strength_pct = ((current_price - relevant_level) / relevant_level) * 100
            else:
                strength_pct = ((relevant_level - current_price) / relevant_level) * 100
            
            # Determine breakout quality
            quality = self._determine_breakout_quality(strength_pct, volume_ratio)
            
            # Calculate price momentum
            momentum = self._calculate_price_momentum(symbol)
            
            # Calculate time since price was at this level
            time_since_level = self._calculate_time_since_level(symbol, relevant_level)
            
            # Get additional metadata
            sector = self._get_stock_sector(symbol)
            market_cap = self._get_market_cap_category(current_price)
            
            # Calculate confidence score
            confidence = self._calculate_confidence_score(
                strength_pct, volume_ratio, momentum, time_since_level
            )
            
            # Create breakout signal with precise timestamp
            breakout_timestamp = datetime.now()
            breakout_signal = BreakoutSignal(
                symbol=symbol,
                instrument_key=f"NSE_EQ|{symbol}",  # Default format
                breakout_type=breakout_type,
                current_price=current_price,
                resistance_level=levels["resistance"][0] if levels["resistance"] else 0,
                support_level=levels["support"][-1] if levels["support"] else 0,
                breakout_strength=strength_pct,
                volume=volume,
                avg_volume_20d=avg_volume,
                volume_ratio=volume_ratio,
                price_momentum=momentum,
                breakout_quality=quality,
                time_since_level=time_since_level,
                sector=sector,
                market_cap=market_cap,
                timestamp=breakout_timestamp,
                breakout_time=breakout_timestamp.strftime("%H:%M:%S"),  # HH:MM:SS format
                breakout_date=breakout_timestamp.strftime("%Y-%m-%d"),  # YYYY-MM-DD format
                confidence_score=confidence,
                metadata={
                    "all_resistance_levels": levels["resistance"][:3],  # Top 3
                    "all_support_levels": levels["support"][-3:],       # Bottom 3
                    "breach_percentage": strength_pct,
                    "detection_milliseconds": breakout_timestamp.microsecond // 1000,  # For precision
                    "market_session": "regular" if self.is_trading_hours() else "pre_post",
                    "exact_detection_time": breakout_timestamp.isoformat(),  # Full ISO timestamp
                    "detection_during_market_hours": self.is_trading_hours(),
                    "market_open_time": self.market_open_time.strftime("%H:%M:%S"),
                    "market_close_time": self.market_close_time.strftime("%H:%M:%S")
                }
            )
            
            # Add to collections
            self.active_breakouts.append(breakout_signal)
            self.todays_breakouts.append(breakout_signal)
            self.breakouts_detected_today += 1
            
            # Log significant breakouts
            if strength_pct >= self.breakout_thresholds["moderate"]:
                logger.info(
                    f"🚨 {breakout_type.upper()}: {symbol} @ ₹{current_price:.2f} "
                    f"({strength_pct:.2f}% {breakout_type}, Vol: {volume_ratio:.1f}x)"
                )
            
            return breakout_signal
            
        except Exception as e:
            logger.error(f"❌ Error detecting breakout for {symbol}: {e}")
            return None

    def process_live_feed_batch(self, feed_data: Dict[str, Any]) -> List[BreakoutSignal]:
        """Process batch of live feed data for breakout detection"""
        if not self.is_trading_hours() or not self.detection_active:
            return []
        
        start_time = datetime.now()
        new_breakouts = []
        
        try:
            for symbol, data in feed_data.items():
                # Extract data
                current_price = data.get('ltp', 0)
                volume = data.get('volume', 0)
                
                if not current_price or not volume:
                    continue
                
                # Update price data
                ohlc_data = {
                    'open': data.get('open', current_price),
                    'high': data.get('high', current_price),
                    'low': data.get('low', current_price)
                }
                self.update_price_data(symbol, current_price, volume, ohlc_data)
                
                # Detect breakout/breakdown
                breakout = self.detect_breakout_breakdown(symbol, current_price, volume)
                if breakout:
                    new_breakouts.append(breakout)
            
            # Track performance
            processing_time = (datetime.now() - start_time).total_seconds() * 1000000
            self.processing_times.append(processing_time)
            
            if new_breakouts:
                logger.info(
                    f"📊 Processed {len(feed_data)} symbols, found {len(new_breakouts)} breakouts "
                    f"in {processing_time:.1f}μs"
                )
                
                # Broadcast breakout signals
                self._broadcast_breakout_signals(new_breakouts)
            
            return new_breakouts
            
        except Exception as e:
            logger.error(f"❌ Error processing breakout detection batch: {e}")
            return []

    def _get_average_volume(self, symbol: str) -> float:
        """Get 20-day average volume for a symbol"""
        if symbol not in self.volume_history or len(self.volume_history[symbol]) == 0:
            return 100000  # Default volume
        
        return np.mean(list(self.volume_history[symbol]))

    def _determine_breakout_quality(self, strength_pct: float, volume_ratio: float) -> str:
        """Determine breakout quality based on strength and volume"""
        # Base quality from strength
        if strength_pct >= self.breakout_thresholds["very_strong"]:
            base_quality = "very_strong"
        elif strength_pct >= self.breakout_thresholds["strong"]:
            base_quality = "strong"
        elif strength_pct >= self.breakout_thresholds["moderate"]:
            base_quality = "moderate"
        else:
            base_quality = "weak"
        
        # Upgrade quality based on volume
        if volume_ratio >= self.volume_thresholds["exceptional"] and base_quality != "very_strong":
            # Upgrade by one level
            quality_levels = ["weak", "moderate", "strong", "very_strong"]
            current_index = quality_levels.index(base_quality)
            if current_index < len(quality_levels) - 1:
                base_quality = quality_levels[current_index + 1]
        
        return base_quality

    def _calculate_price_momentum(self, symbol: str) -> float:
        """Calculate recent price momentum (% change over last 10 ticks)"""
        try:
            if symbol not in self.price_history or len(self.price_history[symbol]) < 10:
                return 0.0
            
            price_data = list(self.price_history[symbol])
            recent_prices = [p['price'] for p in price_data[-10:]]
            
            if len(recent_prices) >= 2:
                start_price = recent_prices[0]
                end_price = recent_prices[-1]
                momentum = ((end_price - start_price) / start_price) * 100
                return momentum
            
            return 0.0
            
        except Exception:
            return 0.0

    def _calculate_time_since_level(self, symbol: str, level: float) -> int:
        """Calculate minutes since price was near this level"""
        try:
            if symbol not in self.price_history:
                return 0
            
            price_data = list(self.price_history[symbol])
            now = datetime.now()
            
            # Look for when price was within 1% of this level
            tolerance = level * 0.01
            
            for i in range(len(price_data) - 1, -1, -1):
                price_point = price_data[i]
                if abs(price_point['price'] - level) <= tolerance:
                    time_diff = now - price_point['timestamp']
                    return int(time_diff.total_seconds() / 60)
            
            return 999  # More than available history
            
        except Exception:
            return 0

    def _calculate_confidence_score(self, strength_pct: float, volume_ratio: float,
                                  momentum: float, time_since_level: int) -> float:
        """Calculate confidence score for breakout (0.0 to 1.0)"""
        try:
            # Strength score (0.3 max)
            strength_score = min(strength_pct / 5.0, 0.3)
            
            # Volume score (0.3 max)
            volume_score = min(volume_ratio / 5.0, 0.3)
            
            # Momentum score (0.2 max)
            momentum_score = min(abs(momentum) / 5.0, 0.2)
            
            # Time factor score (0.2 max) - longer time since level = higher confidence
            time_score = min(time_since_level / 120.0, 0.2)  # Max at 2 hours
            
            total_score = strength_score + volume_score + momentum_score + time_score
            return min(total_score, 1.0)
            
        except Exception:
            return 0.5

    def _get_stock_sector(self, symbol: str) -> str:
        """Get sector information for symbol"""
        try:
            if DEPENDENCIES_AVAILABLE:
                enriched_data = instrument_registry.get_enriched_prices()
                for key, data in enriched_data.items():
                    if data.get('symbol') == symbol:
                        return data.get('sector', 'UNKNOWN')
            return 'UNKNOWN'
        except Exception:
            return 'UNKNOWN'

    def _get_market_cap_category(self, price: float) -> str:
        """Estimate market cap category based on price"""
        if price > 1000:
            return "LARGE_CAP"
        elif price > 200:
            return "MID_CAP"
        else:
            return "SMALL_CAP"

    def _broadcast_breakout_signals(self, breakout_signals: List[BreakoutSignal]):
        """Broadcast breakout signals to connected clients"""
        try:
            if not DEPENDENCIES_AVAILABLE or not breakout_signals:
                return
            
            # Convert to serializable format with enhanced timestamps
            signals_data = []
            for signal in breakout_signals:
                signals_data.append({
                    "symbol": signal.symbol,
                    "breakout_type": signal.breakout_type,
                    "current_price": signal.current_price,
                    "resistance_level": signal.resistance_level,
                    "support_level": signal.support_level,
                    "breakout_strength": round(signal.breakout_strength, 2),
                    "volume_ratio": round(signal.volume_ratio, 1),
                    "breakout_quality": signal.breakout_quality,
                    "confidence_score": round(signal.confidence_score, 2),
                    "price_momentum": round(signal.price_momentum, 2),
                    "time_since_level": signal.time_since_level,
                    "sector": signal.sector,
                    "timestamp": signal.timestamp.isoformat(),
                    "breakout_time": signal.breakout_time,  # HH:MM:SS
                    "breakout_date": signal.breakout_date,  # YYYY-MM-DD
                    "volume": signal.volume,
                    "avg_volume_20d": signal.avg_volume_20d,
                    "market_cap": signal.market_cap,
                    "metadata": signal.metadata
                })
            
            # Broadcast via unified WebSocket manager
            unified_manager.emit_event("breakout_signals_update", {
                "signals": signals_data,
                "count": len(signals_data),
                "market_hours": self.is_trading_hours(),
                "timestamp": datetime.now().isoformat()
            }, priority=1)  # High priority for breakout signals
            
            logger.info(f"📡 Broadcast {len(breakout_signals)} breakout signals to clients")
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting breakout signals: {e}")

    def get_active_breakouts(self, breakout_type: str = None, 
                           min_quality: str = None) -> List[Dict[str, Any]]:
        """Get currently active breakout signals"""
        filtered_breakouts = self.active_breakouts.copy()
        
        # Filter by breakout type
        if breakout_type:
            filtered_breakouts = [b for b in filtered_breakouts if b.breakout_type == breakout_type]
        
        # Filter by minimum quality
        if min_quality:
            quality_order = ["weak", "moderate", "strong", "very_strong"]
            min_index = quality_order.index(min_quality)
            filtered_breakouts = [b for b in filtered_breakouts 
                                if quality_order.index(b.breakout_quality) >= min_index]
        
        # Sort by confidence score
        filtered_breakouts.sort(key=lambda x: x.confidence_score, reverse=True)
        
        # Convert to dict format with enhanced timestamp info
        return [{
            "symbol": b.symbol,
            "breakout_type": b.breakout_type,
            "current_price": b.current_price,
            "resistance_level": b.resistance_level,
            "support_level": b.support_level,
            "breakout_strength": round(b.breakout_strength, 2),
            "breakout_quality": b.breakout_quality,
            "volume_ratio": round(b.volume_ratio, 1),
            "confidence_score": round(b.confidence_score, 2),
            "timestamp": b.timestamp.isoformat(),
            "breakout_time": b.breakout_time,  # HH:MM:SS
            "breakout_date": b.breakout_date,  # YYYY-MM-DD
            "time_ago_minutes": int((datetime.now() - b.timestamp).total_seconds() / 60),
            "volume": b.volume,
            "avg_volume_20d": b.avg_volume_20d,
            "price_momentum": round(b.price_momentum, 2),
            "sector": b.sector,
            "market_cap": b.market_cap,
            "time_since_level": b.time_since_level
        } for b in filtered_breakouts]

    async def process_market_data(self, feeds_data: Dict[str, Any]) -> List[BreakoutSignal]:
        """
        Async wrapper for processing market data - Required for ultra-fast integration
        """
        try:
            # Convert feeds data to the expected format
            if not feeds_data:
                return []
            
            # Process the data synchronously (breakout detection is already optimized)
            breakouts = self.process_live_feed_batch(feeds_data)
            
            # Return as list of BreakoutSignal objects
            return breakouts
            
        except Exception as e:
            logger.error(f"❌ Error in async breakout processing: {e}")
            return []

    async def shutdown(self):
        """Cleanup method for graceful shutdown"""
        try:
            logger.info("🛑 Breakout detection service shutting down...")
            # Clear active breakouts
            self.active_breakouts.clear()
            logger.info("✅ Breakout detection service shut down cleanly")
        except Exception as e:
            logger.error(f"❌ Error during breakout detection service shutdown: {e}")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get breakout detection performance metrics"""
        return {
            "breakouts_detected_today": self.breakouts_detected_today,
            "active_breakouts_count": len(self.active_breakouts),
            "symbols_monitored": len(self.symbols_monitored),
            "detection_active": self.detection_active,
            "is_trading_hours": self.is_trading_hours(),
            "avg_processing_time_us": np.mean(self.processing_times) if self.processing_times else 0,
            "support_resistance_calculated": len(self.support_resistance_levels),
            "breakout_thresholds": self.breakout_thresholds,
            "volume_thresholds": self.volume_thresholds,
            "current_time": datetime.now().time().isoformat(),
            "market_open_time": self.market_open_time.isoformat(),
            "market_close_time": self.market_close_time.isoformat()
        }

    def clear_old_breakouts(self, minutes_old: int = 60):
        """Clear breakout signals older than specified minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes_old)
        
        # Remove old active breakouts
        self.active_breakouts = [b for b in self.active_breakouts 
                               if b.timestamp > cutoff_time]
        
        logger.info(f"🧹 Cleared breakouts older than {minutes_old} minutes")

    async def run_breakout_monitor(self):
        """Background task to monitor breakouts and cleanup"""
        logger.info("🔍 Starting breakout detection monitor...")
        previous_market_state = None
        
        while True:
            try:
                # Update market hours status
                current_market_state = self.is_trading_hours()
                self.is_market_hours = current_market_state
                
                # Handle market session transitions
                if previous_market_state is not None and previous_market_state != current_market_state:
                    if current_market_state:
                        logger.info("🔔 Market OPENED - Breakout detection ACTIVE")
                        self.detection_active = True
                    else:
                        logger.info("🔔 Market CLOSED - Breakout detection INACTIVE")
                        self.detection_active = False
                        # Clear active breakouts from previous session to avoid stale data
                        self.clear_old_breakouts(0)  # Clear all breakouts immediately when market closes
                        logger.info("🧹 Cleared all active breakouts due to market close")
                
                previous_market_state = current_market_state
                
                # During trading hours: Clear old breakouts every 30 minutes
                if current_market_state and datetime.now().minute % 30 == 0:
                    self.clear_old_breakouts(60)  # Clear breakouts older than 1 hour
                    logger.info("🧹 Cleared old breakouts (1+ hours old)")
                
                # Outside trading hours: Clear all breakouts every 6 hours to prevent stale data
                elif not current_market_state and datetime.now().hour % 6 == 0 and datetime.now().minute == 0:
                    self.clear_old_breakouts(0)  # Clear all breakouts
                    logger.info("🧹 Cleared all breakouts (market closed)")
                
                await asyncio.sleep(60)  # Run every minute
                
            except Exception as e:
                logger.error(f"❌ Breakout monitor error: {e}")
                await asyncio.sleep(60)

# Singleton instance
breakout_detection_service = BreakoutDetectionService()

def get_breakout_detection_service() -> BreakoutDetectionService:
    """Get the singleton breakout detection service"""
    return breakout_detection_service

# Convenience functions for integration
def process_breakout_data(feed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process live feed data for breakout detection"""
    breakouts = breakout_detection_service.process_live_feed_batch(feed_data)
    return [b.__dict__ for b in breakouts]

def get_current_breakouts(quality: str = "moderate") -> List[Dict[str, Any]]:
    """Get current breakout signals above minimum quality"""
    return breakout_detection_service.get_active_breakouts(min_quality=quality)

def get_current_breakdowns(quality: str = "moderate") -> List[Dict[str, Any]]:
    """Get current breakdown signals above minimum quality"""
    return breakout_detection_service.get_active_breakouts("breakdown", quality)

def is_breakout_detection_active() -> bool:
    """Check if breakout detection is currently active"""
    return breakout_detection_service.detection_active

async def start_breakout_monitor():
    """Start the breakout detection background monitor"""
    await breakout_detection_service.run_breakout_monitor()