"""
Enhanced Gap Detection Service
=============================

Optimized gap detection using numpy/pandas with morning-specific capture.
Captures all gap up/gap down stocks during market opening (9:15-9:45 AM).

Key Features:
- Ultra-fast numpy/pandas operations
- Morning-specific gap capture
- Real-time gap tracking
- Volume-based confirmation
- Integration with high-speed market data
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, time as dt_time, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import pytz
from collections import defaultdict
import json

# Import high-speed market data
from services.high_speed_market_data import high_speed_market_data

logger = logging.getLogger(__name__)
IST = pytz.timezone('Asia/Kolkata')

class GapType(Enum):
    """Gap classification"""
    SMALL_UP = "small_up"      # 1-3% gap up
    MEDIUM_UP = "medium_up"    # 3-5% gap up
    LARGE_UP = "large_up"      # >5% gap up
    SMALL_DOWN = "small_down"  # 1-3% gap down
    MEDIUM_DOWN = "medium_down" # 3-5% gap down
    LARGE_DOWN = "large_down"  # >5% gap down

@dataclass
class GapStock:
    """Gap stock data structure optimized for speed"""
    symbol: str
    instrument_key: str
    gap_percent: float
    gap_points: float
    prev_close: float
    open_price: float
    current_price: float
    volume: int
    gap_type: GapType
    strength_score: float  # 1-10
    detection_time: datetime
    volume_ratio: float = 0.0
    sector: str = "Unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "symbol": self.symbol,
            "instrument_key": self.instrument_key,
            "gap_percentage": round(self.gap_percent, 2),
            "gap_points": round(self.gap_points, 2),
            "prev_close": self.prev_close,
            "previous_close": self.prev_close,  # Alternative key for frontend compatibility
            "open_price": self.open_price,
            "current_price": self.current_price,
            "volume": self.volume,
            "gap_type": self.gap_type.value,
            "gap_strength": self._get_strength_label(),
            "strength_score": round(self.strength_score, 1),
            "confidence_score": min(1.0, self.strength_score / 10.0),
            "timestamp": self.detection_time.isoformat(),
            "time_detected": self.detection_time.strftime("%H:%M:%S"),
            "volume_ratio": round(self.volume_ratio, 1),
            "sector": self.sector,
            "gap_direction": "up" if self.gap_percent > 0 else "down",
            "gap_size": self._get_size_label(),
            "is_morning_gap": True  # All gaps detected are morning gaps
        }
    
    def _get_strength_label(self) -> str:
        """Get strength label based on score"""
        if self.strength_score >= 8:
            return "very_strong"
        elif self.strength_score >= 6:
            return "strong"
        elif self.strength_score >= 4:
            return "moderate"
        else:
            return "weak"
    
    def _get_size_label(self) -> str:
        """Get gap size label"""
        abs_gap = abs(self.gap_percent)
        if abs_gap >= 5:
            return "large"
        elif abs_gap >= 3:
            return "medium"
        else:
            return "small"

class EnhancedGapDetection:
    """
    Enhanced Gap Detection Service using numpy/pandas
    
    Optimized for morning gap capture with ultra-fast processing
    """
    
    def __init__(self):
        # Configuration
        self.min_gap_threshold = 1.0    # Minimum 1% gap
        self.small_gap_max = 3.0        # Small gap up to 3%
        self.medium_gap_max = 5.0       # Medium gap up to 5%
        self.min_volume = 10000         # Minimum volume
        self.min_price = 10.0          # Minimum price
        self.max_price = 100000.0      # Maximum price
        
        # Morning capture window
        self.morning_start = dt_time(9, 15)  # 9:15 AM
        self.morning_end = dt_time(9, 45)    # 9:45 AM
        
        # Data storage
        self.daily_gaps: List[GapStock] = []
        self.gap_up_stocks: List[GapStock] = []
        self.gap_down_stocks: List[GapStock] = []
        self.processed_instruments: set = set()
        
        # Numpy arrays for fast computation
        self.instruments_array = np.array([])
        self.prices_array = np.array([])
        self.volumes_array = np.array([])
        self.gap_percentages = np.array([])
        
        # Service state
        self.is_running = False
        self.is_morning_capture_active = False
        self.current_date = datetime.now(IST).date()
        self.last_update = None
        
        # Performance metrics
        self.stocks_processed = 0
        self.gaps_detected = 0
        
        logger.info("🚀 Enhanced Gap Detection initialized with numpy/pandas optimization")
    
    async def start(self):
        """Start the enhanced gap detection service"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("🎯 Starting Enhanced Gap Detection Service...")
        
        # Start background tasks
        asyncio.create_task(self._morning_capture_monitor())
        asyncio.create_task(self._data_processing_loop())
        
        logger.info("✅ Enhanced Gap Detection Service started")
    
    async def stop(self):
        """Stop the service"""
        self.is_running = False
        logger.info("🛑 Enhanced Gap Detection Service stopped")
    
    async def _morning_capture_monitor(self):
        """Monitor for morning capture window"""
        while self.is_running:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                current_time = datetime.now(IST)
                current_date = current_time.date()
                current_time_only = current_time.time()
                
                # Check if new trading day
                if current_date > self.current_date:
                    await self._reset_for_new_day()
                    self.current_date = current_date
                
                # Check if morning capture window
                was_active = self.is_morning_capture_active
                self.is_morning_capture_active = self.morning_start <= current_time_only <= self.morning_end
                
                if not was_active and self.is_morning_capture_active:
                    logger.info("🌅 Morning gap capture window OPENED - Starting intensive gap detection")
                    await self._start_intensive_capture()
                elif was_active and not self.is_morning_capture_active:
                    logger.info("🌇 Morning gap capture window CLOSED")
                    await self._finalize_morning_gaps()
                
            except Exception as e:
                logger.error(f"❌ Error in morning capture monitor: {e}")
                await asyncio.sleep(30)
    
    async def _start_intensive_capture(self):
        """Start intensive gap capture during morning window"""
        try:
            # Clear processed instruments for fresh capture
            self.processed_instruments.clear()
            
            # Get all available market data
            await self._capture_all_instruments()
            
            logger.info(f"🎯 Started intensive gap capture - monitoring all instruments")
            
        except Exception as e:
            logger.error(f"❌ Error starting intensive capture: {e}")
    
    async def _capture_all_instruments(self):
        """Capture gaps for all available instruments using vectorized operations"""
        try:
            # Get all instruments from high-speed market data
            performance_stats = high_speed_market_data.get_performance_stats()
            available_instruments = list(performance_stats.get('top_accessed', {}).keys())
            
            # If not many instruments available, try to get from other sources
            if len(available_instruments) < 100:
                try:
                    from services.instrument_registry import instrument_registry
                    if hasattr(instrument_registry, '_live_prices'):
                        additional_instruments = list(instrument_registry._live_prices.keys())
                        available_instruments.extend(additional_instruments)
                        available_instruments = list(set(available_instruments))  # Remove duplicates
                except Exception:
                    pass
            
            logger.info(f"📊 Processing {len(available_instruments)} instruments for gap detection")
            
            # Process in batches using numpy for speed
            batch_size = 100
            for i in range(0, len(available_instruments), batch_size):
                batch = available_instruments[i:i + batch_size]
                await self._process_instrument_batch(batch)
                
                # Small delay to prevent overwhelming the system
                if i % 500 == 0:
                    await asyncio.sleep(0.1)
            
            logger.info(f"✅ Completed gap detection for {len(available_instruments)} instruments")
            
        except Exception as e:
            logger.error(f"❌ Error capturing all instruments: {e}")
    
    async def _process_instrument_batch(self, instruments: List[str]):
        """Process a batch of instruments using vectorized operations"""
        try:
            # Prepare data arrays
            valid_data = []
            
            for instrument_key in instruments:
                if instrument_key in self.processed_instruments:
                    continue
                
                # Get price data
                price_data = high_speed_market_data.get_latest_price(instrument_key)
                if not price_data:
                    continue
                
                # Try to get more detailed data
                try:
                    from services.instrument_registry import instrument_registry
                    if hasattr(instrument_registry, '_live_prices'):
                        detailed_data = instrument_registry._live_prices.get(instrument_key, {})
                        if detailed_data:
                            price_data.update(detailed_data)
                except Exception:
                    pass
                
                # Extract required fields
                current_price = float(price_data.get('ltp', price_data.get('last_price', 0)))
                open_price = float(price_data.get('open', 0))
                prev_close = float(price_data.get('cp', price_data.get('prev_close', price_data.get('close', 0))))
                volume = int(price_data.get('volume', 0))
                
                # Validation
                if not self._is_valid_for_gap_detection(current_price, open_price, prev_close, volume):
                    continue
                
                # Calculate gap
                gap_percent = ((open_price - prev_close) / prev_close) * 100
                
                # Check if gap meets threshold
                if abs(gap_percent) >= self.min_gap_threshold:
                    valid_data.append({
                        'instrument_key': instrument_key,
                        'current_price': current_price,
                        'open_price': open_price,
                        'prev_close': prev_close,
                        'volume': volume,
                        'gap_percent': gap_percent,
                        'price_data': price_data
                    })
                
                self.processed_instruments.add(instrument_key)
            
            # Process valid gaps using numpy
            if valid_data:
                await self._process_gaps_vectorized(valid_data)
            
        except Exception as e:
            logger.error(f"❌ Error processing instrument batch: {e}")
    
    def _is_valid_for_gap_detection(self, current_price: float, open_price: float, 
                                   prev_close: float, volume: int) -> bool:
        """Validate if data is suitable for gap detection"""
        return (
            current_price > 0 and open_price > 0 and prev_close > 0 and
            self.min_price <= current_price <= self.max_price and
            volume >= self.min_volume
        )
    
    async def _process_gaps_vectorized(self, valid_data: List[Dict[str, Any]]):
        """Process gaps using vectorized numpy operations"""
        try:
            if not valid_data:
                return
            
            # Convert to numpy arrays for fast computation
            gap_percentages = np.array([data['gap_percent'] for data in valid_data])
            volumes = np.array([data['volume'] for data in valid_data])
            prices = np.array([data['current_price'] for data in valid_data])
            
            # Calculate strength scores vectorized
            strength_scores = self._calculate_strength_scores_vectorized(
                gap_percentages, volumes, prices
            )
            
            # Create gap stocks
            for i, data in enumerate(valid_data):
                gap_stock = await self._create_gap_stock(data, strength_scores[i])
                if gap_stock:
                    self._add_gap_stock(gap_stock)
            
            logger.info(f"📈 Processed {len(valid_data)} gap candidates using vectorized operations")
            
        except Exception as e:
            logger.error(f"❌ Error in vectorized gap processing: {e}")
    
    def _calculate_strength_scores_vectorized(self, gap_percentages: np.ndarray, 
                                            volumes: np.ndarray, prices: np.ndarray) -> np.ndarray:
        """Calculate strength scores using vectorized operations"""
        try:
            # Base strength from gap percentage
            abs_gaps = np.abs(gap_percentages)
            base_strength = np.minimum(8.0, abs_gaps * 1.5)
            
            # Volume boost (vectorized)
            volume_boost = np.zeros_like(volumes, dtype=float)
            volume_boost = np.where(volumes >= 1000000, 2.0, volume_boost)
            volume_boost = np.where((volumes >= 500000) & (volumes < 1000000), 1.5, volume_boost)
            volume_boost = np.where((volumes >= 100000) & (volumes < 500000), 1.0, volume_boost)
            volume_boost = np.where((volumes >= 50000) & (volumes < 100000), 0.5, volume_boost)
            
            # Price level adjustment (vectorized)
            price_multiplier = np.ones_like(prices)
            price_multiplier = np.where(prices >= 1000, 1.2, price_multiplier)
            price_multiplier = np.where(prices < 50, 0.8, price_multiplier)
            
            # Combined strength score
            final_scores = (base_strength + volume_boost) * price_multiplier
            
            # Clamp to valid range
            return np.clip(final_scores, 1.0, 10.0)
            
        except Exception as e:
            logger.error(f"❌ Error in vectorized strength calculation: {e}")
            return np.full(len(gap_percentages), 5.0)
    
    async def _create_gap_stock(self, data: Dict[str, Any], strength_score: float) -> Optional[GapStock]:
        """Create GapStock instance"""
        try:
            gap_percent = data['gap_percent']
            
            # Classify gap type
            gap_type = self._classify_gap_type(gap_percent)
            if not gap_type:
                return None
            
            # Extract symbol
            symbol = self._extract_symbol_from_instrument_key(data['instrument_key'])
            
            # Get sector if available
            sector = data['price_data'].get('sector', 'Unknown')
            
            # Calculate volume ratio (if historical data available)
            volume_ratio = self._calculate_volume_ratio(data['instrument_key'], data['volume'])
            
            gap_stock = GapStock(
                symbol=symbol,
                instrument_key=data['instrument_key'],
                gap_percent=gap_percent,
                gap_points=data['open_price'] - data['prev_close'],
                prev_close=data['prev_close'],
                open_price=data['open_price'],
                current_price=data['current_price'],
                volume=data['volume'],
                gap_type=gap_type,
                strength_score=strength_score,
                detection_time=datetime.now(IST),
                volume_ratio=volume_ratio,
                sector=sector
            )
            
            return gap_stock
            
        except Exception as e:
            logger.error(f"❌ Error creating gap stock: {e}")
            return None
    
    def _classify_gap_type(self, gap_percent: float) -> Optional[GapType]:
        """Classify gap type based on percentage"""
        abs_gap = abs(gap_percent)
        
        if abs_gap < self.min_gap_threshold:
            return None
        
        if gap_percent > 0:  # Gap up
            if abs_gap >= self.medium_gap_max:
                return GapType.LARGE_UP
            elif abs_gap >= self.small_gap_max:
                return GapType.MEDIUM_UP
            else:
                return GapType.SMALL_UP
        else:  # Gap down
            if abs_gap >= self.medium_gap_max:
                return GapType.LARGE_DOWN
            elif abs_gap >= self.small_gap_max:
                return GapType.MEDIUM_DOWN
            else:
                return GapType.SMALL_DOWN
    
    def _extract_symbol_from_instrument_key(self, instrument_key: str) -> str:
        """Extract symbol from instrument key"""
        try:
            if '|' in instrument_key:
                parts = instrument_key.split('|')
                if len(parts) > 1:
                    symbol_part = parts[1]
                    # Handle different formats
                    if '-' in symbol_part:
                        return symbol_part.split('-')[0]
                    return symbol_part
            return instrument_key
        except Exception:
            return instrument_key
    
    def _calculate_volume_ratio(self, instrument_key: str, current_volume: int) -> float:
        """Calculate volume ratio compared to average (simplified)"""
        try:
            # Get historical volume data if available
            volume_array = high_speed_market_data.get_volume_array(instrument_key, 20)
            
            if len(volume_array) > 1:
                avg_volume = np.mean(volume_array[:-1])  # Exclude current
                if avg_volume > 0:
                    return current_volume / avg_volume
            
            return 1.0  # Default ratio
            
        except Exception:
            return 1.0
    
    def _add_gap_stock(self, gap_stock: GapStock):
        """Add gap stock to appropriate collections"""
        self.daily_gaps.append(gap_stock)
        
        if gap_stock.gap_percent > 0:
            self.gap_up_stocks.append(gap_stock)
        else:
            self.gap_down_stocks.append(gap_stock)
        
        self.gaps_detected += 1
        
        logger.info(f"🎯 GAP DETECTED: {gap_stock.symbol} - {gap_stock.gap_type.value} - {gap_stock.gap_percent:+.2f}%")
    
    async def _finalize_morning_gaps(self):
        """Finalize morning gap detection and sort results"""
        try:
            # Sort gaps by percentage
            self.gap_up_stocks.sort(key=lambda x: x.gap_percent, reverse=True)
            self.gap_down_stocks.sort(key=lambda x: x.gap_percent)
            
            logger.info(f"🎯 Morning gap detection completed:")
            logger.info(f"   📈 Gap Up: {len(self.gap_up_stocks)} stocks")
            logger.info(f"   📉 Gap Down: {len(self.gap_down_stocks)} stocks")
            logger.info(f"   📊 Total Gaps: {len(self.daily_gaps)} stocks")
            
            # Broadcast to frontend
            await self._broadcast_gap_results()
            
        except Exception as e:
            logger.error(f"❌ Error finalizing morning gaps: {e}")
    
    async def _broadcast_gap_results(self):
        """Broadcast gap results to frontend"""
        try:
            from services.unified_websocket_manager import unified_manager
            
            if not unified_manager:
                return
            
            # Prepare data for broadcast
            gap_data = {
                "type": "gap_analysis_update",
                "data": {
                    "gap_up": [stock.to_dict() for stock in self.gap_up_stocks[:50]],  # Top 50
                    "gap_down": [stock.to_dict() for stock in self.gap_down_stocks[:50]],  # Top 50
                    "total_gap_up": len(self.gap_up_stocks),
                    "total_gap_down": len(self.gap_down_stocks),
                    "total_gaps": len(self.daily_gaps),
                    "timestamp": datetime.now(IST).isoformat(),
                    "capture_time": "morning",
                    "market_status": "open"
                }
            }
            
            # Broadcast to all connected clients
            unified_manager.emit_event("gap_analysis_update", gap_data, priority=1)
            
            logger.info(f"📡 Broadcasted gap analysis results to frontend")
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting gap results: {e}")
    
    async def _data_processing_loop(self):
        """Background data processing loop"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Process every minute
                
                # Update performance metrics
                self.stocks_processed = len(self.processed_instruments)
                self.last_update = datetime.now(IST)
                
                # Log performance
                if self.is_morning_capture_active:
                    logger.info(f"📊 Gap Detection Status: {self.gaps_detected} gaps from {self.stocks_processed} stocks")
                
            except Exception as e:
                logger.error(f"❌ Error in data processing loop: {e}")
                await asyncio.sleep(30)
    
    async def _reset_for_new_day(self):
        """Reset data for new trading day"""
        self.daily_gaps.clear()
        self.gap_up_stocks.clear()
        self.gap_down_stocks.clear()
        self.processed_instruments.clear()
        self.gaps_detected = 0
        self.stocks_processed = 0
        
        logger.info(f"🌅 Reset gap detection for new trading day: {self.current_date}")
    
    # API Methods
    
    def get_gap_analysis_data(self) -> Dict[str, Any]:
        """Get gap analysis data for API"""
        return {
            "gap_up": [stock.to_dict() for stock in self.gap_up_stocks],
            "gap_down": [stock.to_dict() for stock in self.gap_down_stocks],
            "statistics": {
                "total_gaps": len(self.daily_gaps),
                "gap_up_count": len(self.gap_up_stocks),
                "gap_down_count": len(self.gap_down_stocks),
                "stocks_processed": self.stocks_processed,
                "detection_active": self.is_morning_capture_active,
                "last_update": self.last_update.isoformat() if self.last_update else None,
                "trading_day": self.current_date.isoformat()
            },
            "summary": {
                "avg_gap_up": np.mean([s.gap_percent for s in self.gap_up_stocks]) if self.gap_up_stocks else 0,
                "avg_gap_down": np.mean([s.gap_percent for s in self.gap_down_stocks]) if self.gap_down_stocks else 0,
                "max_gap_up": max([s.gap_percent for s in self.gap_up_stocks]) if self.gap_up_stocks else 0,
                "max_gap_down": min([s.gap_percent for s in self.gap_down_stocks]) if self.gap_down_stocks else 0
            },
            "timestamp": datetime.now(IST).isoformat(),
            "market_status": "open" if self.is_morning_capture_active else "closed"
        }
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get service health status"""
        return {
            "service": "enhanced_gap_detection",
            "status": "running" if self.is_running else "stopped",
            "morning_capture_active": self.is_morning_capture_active,
            "gaps_detected_today": self.gaps_detected,
            "stocks_processed": self.stocks_processed,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "trading_day": self.current_date.isoformat(),
            "performance": {
                "gaps_per_minute": self.gaps_detected / max(1, (datetime.now(IST) - self.last_update).total_seconds() / 60) if self.last_update else 0,
                "processing_efficiency": self.gaps_detected / max(1, self.stocks_processed) * 100
            }
        }

# Global instance
enhanced_gap_detection = EnhancedGapDetection()

# API functions
async def start_enhanced_gap_detection():
    """Start the enhanced gap detection service"""
    await enhanced_gap_detection.start()

async def stop_enhanced_gap_detection():
    """Stop the enhanced gap detection service"""
    await enhanced_gap_detection.stop()

def get_gap_data() -> Dict[str, Any]:
    """Get current gap analysis data"""
    return enhanced_gap_detection.get_gap_analysis_data()

def health_check() -> Dict[str, Any]:
    """Health check for enhanced gap detection"""
    return enhanced_gap_detection.get_service_health()