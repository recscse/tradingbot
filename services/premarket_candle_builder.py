#!/usr/bin/env python3
"""
Premarket Candle Builder Service - 9:00 AM to 9:08 AM IST

This service builds OHLC candles from live WebSocket tick data during the premarket 
window (9:00 AM to 9:08 AM IST) and performs gap detection analysis.

Key Features:
- Real-time candle building from tick-by-tick data
- Precise 8-minute premarket window handling
- Gap detection with volume confirmation
- Database persistence with automatic cleanup
- High-performance tick processing with minimal latency

Architecture:
- Subscribes to WebSocket feeds during premarket hours only
- Builds candles incrementally from each tick
- Calculates gaps against previous day's close
- Generates alerts for significant gaps (>1%)
- Auto-cleanup of data older than 2 days
"""

import asyncio
import logging
from datetime import datetime, date, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

# Database imports
from database.connection import get_db
from database.models import PremarketCandle, GapDetectionAlert

# Service imports
try:
    from services.instrument_registry import instrument_registry
    from services.unified_websocket_manager import unified_manager
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    logging.warning(f"Dependencies not available: {e}")

logger = logging.getLogger(__name__)

# Premarket trading hours (IST)
PREMARKET_START_TIME = time(9, 0)   # 9:00 AM
PREMARKET_END_TIME = time(9, 8)     # 9:08 AM  
MARKET_OPEN_TIME = time(9, 15)      # 9:15 AM

@dataclass
class TickData:
    """Single tick data point"""
    timestamp: datetime
    price: Decimal
    volume: int
    instrument_key: str
    symbol: str

@dataclass  
class CandleBuilder:
    """Real-time candle builder for a single instrument"""
    symbol: str
    instrument_key: str
    start_time: datetime
    end_time: datetime
    
    # OHLC data
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    close_price: Optional[Decimal] = None
    
    # Volume and trade data
    total_volume: int = 0
    total_trades: int = 0
    tick_count: int = 0
    
    # Previous close for gap calculation
    previous_close: Optional[Decimal] = None
    
    # Price accumulation for average
    price_sum: Decimal = field(default_factory=lambda: Decimal('0'))
    
    # Quality tracking
    first_tick_time: Optional[datetime] = None
    last_tick_time: Optional[datetime] = None
    
    def add_tick(self, tick: TickData) -> None:
        """Add a single tick to the candle"""
        if not self._is_valid_tick(tick):
            return
            
        price = tick.price
        volume = tick.volume
        
        # Set open price (first tick)
        if self.open_price is None:
            self.open_price = price
            self.first_tick_time = tick.timestamp
            
        # Update high/low
        if self.high_price is None or price > self.high_price:
            self.high_price = price
            
        if self.low_price is None or price < self.low_price:
            self.low_price = price
            
        # Always update close (last price)
        self.close_price = price
        self.last_tick_time = tick.timestamp
        
        # Accumulate volume and trades
        self.total_volume += volume
        self.total_trades += 1
        self.tick_count += 1
        
        # Accumulate weighted price for average
        self.price_sum += price * volume
        
    def _is_valid_tick(self, tick: TickData) -> bool:
        """Validate tick data"""
        return (
            tick.price > 0 and
            tick.volume > 0 and
            self.start_time <= tick.timestamp <= self.end_time and
            tick.instrument_key == self.instrument_key
        )
        
    def is_complete(self) -> bool:
        """Check if candle has minimum required data"""
        return (
            self.open_price is not None and
            self.close_price is not None and
            self.tick_count > 0
        )
        
    def get_avg_price(self) -> Decimal:
        """Calculate volume-weighted average price"""
        if self.total_volume > 0:
            return (self.price_sum / self.total_volume).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        elif self.close_price:
            return self.close_price
        else:
            return Decimal('0')
            
    def calculate_gap_percentage(self) -> Optional[Decimal]:
        """Calculate gap percentage against previous close"""
        if not self.previous_close or not self.open_price or self.previous_close <= 0:
            return None
            
        gap_pct = ((self.open_price - self.previous_close) / self.previous_close * 100)
        return gap_pct.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        
    def get_gap_type(self) -> str:
        """Determine gap type"""
        gap_pct = self.calculate_gap_percentage()
        if gap_pct is None:
            return "NO_GAP"
        elif gap_pct > Decimal('0.5'):
            return "GAP_UP"
        elif gap_pct < Decimal('-0.5'):
            return "GAP_DOWN"
        else:
            return "NO_GAP"
            
    def get_gap_strength(self) -> str:
        """Calculate gap strength based on percentage"""
        gap_pct = self.calculate_gap_percentage()
        if gap_pct is None:
            return "WEAK"
            
        abs_gap = abs(gap_pct)
        if abs_gap >= Decimal('8.0'):
            return "VERY_STRONG"
        elif abs_gap >= Decimal('5.0'):
            return "STRONG"
        elif abs_gap >= Decimal('2.5'):
            return "MODERATE"
        else:
            return "WEAK"
            
    def get_data_quality_score(self) -> Decimal:
        """Calculate data quality score (0-1)"""
        if self.tick_count == 0:
            return Decimal('0')
            
        # Base score from tick count (more ticks = better quality)
        tick_score = min(Decimal(self.tick_count) / Decimal('100'), Decimal('0.5'))
        
        # Time coverage score (how much of the 8-minute window we have data for)
        if self.first_tick_time and self.last_tick_time:
            coverage_duration = (self.last_tick_time - self.first_tick_time).total_seconds()
            expected_duration = 8 * 60  # 8 minutes in seconds
            coverage_score = min(Decimal(coverage_duration) / Decimal(expected_duration), Decimal('0.4'))
        else:
            coverage_score = Decimal('0')
            
        # Completeness score (have all OHLC)
        completeness_score = Decimal('0.1') if self.is_complete() else Decimal('0')
        
        total_score = tick_score + coverage_score + completeness_score
        return total_score.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)


class PremarketCandleBuilderService:
    """Service for building premarket candles and detecting gaps"""
    
    def __init__(self):
        # Market timing
        self.premarket_start = PREMARKET_START_TIME
        self.premarket_end = PREMARKET_END_TIME
        self.market_open = MARKET_OPEN_TIME
        
        # Active candle builders (symbol -> CandleBuilder)
        self.active_builders: Dict[str, CandleBuilder] = {}
        
        # Previous close prices (symbol -> Decimal)
        self.previous_closes: Dict[str, Decimal] = {}
        
        # State management
        self.is_premarket_active = False
        self.current_session_date = date.today()
        self.processed_symbols: Set[str] = set()
        
        # Performance tracking
        self.ticks_processed_today = 0
        self.candles_built_today = 0
        self.gaps_detected_today = 0
        self.alerts_generated_today = 0
        
        # WebSocket integration
        self._register_websocket_callback()
        
        logger.info("✅ Premarket Candle Builder Service initialized")
        
    def _register_websocket_callback(self):
        """Register for WebSocket tick data during premarket hours"""
        try:
            if DEPENDENCIES_AVAILABLE and instrument_registry:
                # Get watchlist instruments for premarket gap detection
                watchlist = self._get_premarket_watchlist()
                
                if watchlist:
                    # Register callback for tick data
                    success = instrument_registry.register_strategy_callback(
                        strategy_name="premarket_candle_builder",
                        instruments=watchlist,
                        callback=self._process_tick_callback
                    )
                    
                    if success:
                        logger.info(f"✅ Registered for {len(watchlist)} instruments for premarket candle building")
                    else:
                        logger.error("❌ Failed to register premarket candle builder callback")
                        
        except Exception as e:
            logger.error(f"❌ Error registering WebSocket callback: {e}")
            
    def _get_premarket_watchlist(self) -> List[str]:
        """Get instrument keys for premarket monitoring"""
        # Major liquid stocks for gap detection
        watchlist_symbols = [
            "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "HDFC",
            "ITC", "LT", "SBIN", "BHARTIARTL", "KOTAKBANK", "ASIANPAINT",
            "MARUTI", "HINDUNILVR", "AXISBANK", "WIPRO", "ULTRACEMCO",
            "NESTLEIND", "TITAN", "POWERGRID", "NTPC", "ONGC", "COALINDIA",
            "BAJFINANCE", "M&M", "SUNPHARMA", "TECHM", "HCLTECH", "DRREDDY"
        ]
        
        instrument_keys = []
        if instrument_registry:
            for symbol in watchlist_symbols:
                symbol_data = instrument_registry._symbols_map.get(symbol)
                if symbol_data and symbol_data.get("spot"):
                    instrument_keys.extend(symbol_data["spot"])
                    
        return instrument_keys
        
    def is_premarket_hours(self) -> bool:
        """Check if current time is within premarket hours"""
        now = datetime.now()
        current_time = now.time()
        current_date = now.date()
        
        # Reset daily state if new day
        if current_date != self.current_session_date:
            self._reset_daily_state()
            self.current_session_date = current_date
            
        # Check if within premarket window and weekday
        return (
            self.premarket_start <= current_time <= self.premarket_end and
            current_date.weekday() < 5  # Monday to Friday only
        )
        
    def _reset_daily_state(self):
        """Reset state for new trading day"""
        self.active_builders.clear()
        self.processed_symbols.clear()
        self.ticks_processed_today = 0
        self.candles_built_today = 0
        self.gaps_detected_today = 0
        self.alerts_generated_today = 0
        self.is_premarket_active = False
        
        # Load previous closes for new day
        try:
            asyncio.create_task(self._load_previous_closes())
        except RuntimeError:
            # If no event loop is running, we'll load previous closes when needed
            pass
        
        logger.info("🌅 New trading day - premarket candle builder state reset")
        
    async def _load_previous_closes(self):
        """Load previous day's closing prices from database"""
        try:
            yesterday = self.current_session_date - timedelta(days=1)
            
            # Skip weekends
            while yesterday.weekday() > 4:  # Saturday=5, Sunday=6
                yesterday -= timedelta(days=1)
                
            db = next(get_db())
            
            # Query previous day's closing prices
            previous_candles = db.query(PremarketCandle).filter(
                PremarketCandle.candle_date == yesterday
            ).all()
            
            self.previous_closes.clear()
            for candle in previous_candles:
                self.previous_closes[candle.symbol] = candle.close_price
                
            logger.info(f"📊 Loaded {len(self.previous_closes)} previous closes from {yesterday}")
            
        except Exception as e:
            logger.error(f"❌ Error loading previous closes: {e}")
        finally:
            db.close()
            
    def _process_tick_callback(self, instrument_key: str, price_data: dict):
        """Process incoming tick data during premarket hours"""
        try:
            # Only process during premarket hours
            if not self.is_premarket_hours():
                return
                
            # Activate premarket session
            if not self.is_premarket_active:
                self.is_premarket_active = True
                logger.info("🚨 PREMARKET SESSION STARTED - Building candles from ticks")
                
            # ✅ FIXED: Extract data from NORMALIZED format (not raw WebSocket)
            # The data comes from instrument_registry.update_live_prices() in normalized format
            symbol = price_data.get('symbol') or self._get_symbol_from_instrument_key(instrument_key)
            if not symbol:
                return
                
            # Extract current price and previous close from normalized data
            current_price = price_data.get('ltp')
            previous_close = price_data.get('cp')
            open_price = price_data.get('open')
            volume = price_data.get('volume', 0)
            
            # Validate essential data
            if not all([current_price, previous_close, open_price]):
                return
                
            if current_price <= 0 or previous_close <= 0:
                return
                
            # Create tick data with current LTP
            tick = TickData(
                timestamp=datetime.now(),
                price=Decimal(str(current_price)),
                volume=int(volume) if volume else 1,
                instrument_key=instrument_key,
                symbol=symbol
            )
            
            # Get or create candle builder for this symbol
            builder = self._get_or_create_builder(symbol, instrument_key, Decimal(str(previous_close)))
            
            # Set the opening price from the feed if this is the first tick
            if builder.open_price is None:
                builder.open_price = Decimal(str(open_price))
            
            # Add tick to builder
            builder.add_tick(tick)
            self.ticks_processed_today += 1
            
            # Check if we should finalize the candle (end of premarket window)
            if datetime.now().time() >= self.premarket_end:
                # Schedule finalization as a background task instead of awaiting
                asyncio.create_task(self._finalize_candle(builder))
                
        except Exception as e:
            logger.error(f"❌ Error processing tick for premarket candle: {e}")
            
    def _get_symbol_from_instrument_key(self, instrument_key: str) -> Optional[str]:
        """Extract symbol from instrument key"""
        try:
            if instrument_registry:
                spot_data = instrument_registry._spot_instruments.get(instrument_key)
                if spot_data:
                    return spot_data.get('symbol')
        except Exception:
            pass
        return None
        
    def _get_or_create_builder(self, symbol: str, instrument_key: str, previous_close: Decimal = None) -> CandleBuilder:
        """Get existing builder or create new one"""
        if symbol not in self.active_builders:
            now = datetime.now()
            start_time = datetime.combine(now.date(), self.premarket_start)
            end_time = datetime.combine(now.date(), self.premarket_end)
            
            # Use the previous close from live feed if available, otherwise from cache
            prev_close = previous_close or self.previous_closes.get(symbol)
            
            builder = CandleBuilder(
                symbol=symbol,
                instrument_key=instrument_key,
                start_time=start_time,
                end_time=end_time,
                previous_close=prev_close
            )
            
            self.active_builders[symbol] = builder
            
        return self.active_builders[symbol]
        
    async def _finalize_candle(self, builder: CandleBuilder):
        """Finalize and save candle to database"""
        try:
            if not builder.is_complete():
                logger.warning(f"⚠️ Incomplete candle for {builder.symbol} - skipping")
                return
                
            # Check if already processed
            if builder.symbol in self.processed_symbols:
                return
                
            self.processed_symbols.add(builder.symbol)
            
            # Calculate gap analysis
            gap_percentage = builder.calculate_gap_percentage()
            gap_type = builder.get_gap_type()
            gap_strength = builder.get_gap_strength()
            
            # Determine if significant gap
            is_significant = gap_percentage and abs(gap_percentage) >= Decimal('1.0')
            
            # Create premarket candle record
            candle = PremarketCandle(
                symbol=builder.symbol,
                instrument_key=builder.instrument_key,
                candle_date=self.current_session_date,
                candle_start_time=builder.start_time,
                candle_end_time=builder.end_time,
                open_price=builder.open_price,
                high_price=builder.high_price,
                low_price=builder.low_price,
                close_price=builder.close_price,
                total_volume=builder.total_volume,
                total_trades=builder.total_trades,
                avg_price=builder.get_avg_price(),
                previous_close=builder.previous_close,
                gap_percentage=gap_percentage,
                gap_type=gap_type,
                gap_strength=gap_strength,
                volume_ratio=self._calculate_volume_ratio(builder),
                volume_confirmation=self._has_volume_confirmation(builder),
                ticks_received=builder.tick_count,
                data_quality_score=builder.get_data_quality_score(),
                sector=self._get_sector(builder.symbol),
                market_cap_category=self._get_market_cap_category(builder.close_price),
                is_significant_gap=is_significant or False
            )
            
            # Save to database
            db = next(get_db())
            try:
                db.add(candle)
                db.commit()
                db.refresh(candle)
                
                self.candles_built_today += 1
                
                # Generate alert for significant gaps
                if is_significant:
                    await self._generate_gap_alert(candle, db)
                    self.gaps_detected_today += 1
                    
                logger.info(
                    f"✅ Candle saved: {builder.symbol} "
                    f"Gap: {gap_percentage}% ({gap_strength}) "
                    f"Quality: {candle.data_quality_score}"
                )
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Error finalizing candle for {builder.symbol}: {e}")
            
    def _calculate_volume_ratio(self, builder: CandleBuilder) -> Optional[Decimal]:
        """Calculate volume ratio vs historical average"""
        # This would need historical volume data - simplified for now
        return Decimal('1.0')  # Placeholder
        
    def _has_volume_confirmation(self, builder: CandleBuilder) -> bool:
        """Check if volume confirms the price gap"""
        # Simplified - would need historical volume analysis
        return builder.total_volume > 1000  # Basic threshold
        
    def _get_sector(self, symbol: str) -> str:
        """Get sector for symbol"""
        # Simplified mapping - could be enhanced with real data
        sector_map = {
            "RELIANCE": "ENERGY", "TCS": "IT", "INFY": "IT", "WIPRO": "IT",
            "HDFCBANK": "BANKING", "ICICIBANK": "BANKING", "SBIN": "BANKING",
            "MARUTI": "AUTO", "M&M": "AUTO", "BAJFINANCE": "FINANCE"
        }
        return sector_map.get(symbol, "OTHER")
        
    def _get_market_cap_category(self, price: Decimal) -> str:
        """Estimate market cap category based on price"""
        if price > Decimal('1000'):
            return "LARGE_CAP"
        elif price > Decimal('200'):
            return "MID_CAP"
        else:
            return "SMALL_CAP"
            
    async def _generate_gap_alert(self, candle: PremarketCandle, db: Session):
        """Generate gap detection alert"""
        try:
            # Calculate alert priority
            gap_pct = abs(candle.gap_percentage or Decimal('0'))
            if gap_pct >= Decimal('8.0'):
                priority = "CRITICAL"
            elif gap_pct >= Decimal('5.0'):
                priority = "HIGH"
            elif gap_pct >= Decimal('2.5'):
                priority = "MEDIUM"
            else:
                priority = "LOW"
                
            # Calculate confidence score
            confidence = min(
                Decimal('0.3') + (gap_pct / Decimal('20')),  # Gap size component
                Decimal('1.0')
            )
            
            # Create alert
            alert = GapDetectionAlert(
                premarket_candle_id=candle.id,
                symbol=candle.symbol,
                gap_percentage=candle.gap_percentage,
                gap_type=candle.gap_type,
                gap_strength=candle.gap_strength,
                trigger_price=candle.close_price,
                previous_close=candle.previous_close,
                alert_priority=priority,
                confidence_score=confidence,
                volume_at_alert=candle.total_volume,
                volume_ratio=candle.volume_ratio,
                expires_at=datetime.combine(
                    candle.candle_date, 
                    self.market_open
                )
            )
            
            db.add(alert)
            db.commit()
            
            self.alerts_generated_today += 1
            
            # Broadcast alert
            await self._broadcast_gap_alert(alert)
            
            logger.info(
                f"🚨 GAP ALERT: {candle.symbol} {candle.gap_type} "
                f"{candle.gap_percentage}% (Priority: {priority})"
            )
            
        except Exception as e:
            logger.error(f"❌ Error generating gap alert: {e}")
            
    async def _broadcast_gap_alert(self, alert: GapDetectionAlert):
        """Broadcast gap alert via WebSocket"""
        try:
            if DEPENDENCIES_AVAILABLE and unified_manager:
                alert_data = {
                    "type": "gap_alert",
                    "symbol": alert.symbol,
                    "gap_type": alert.gap_type,
                    "gap_percentage": float(alert.gap_percentage),
                    "gap_strength": alert.gap_strength,
                    "priority": alert.alert_priority,
                    "confidence": float(alert.confidence_score),
                    "trigger_price": float(alert.trigger_price),
                    "previous_close": float(alert.previous_close),
                    "timestamp": alert.alert_time.isoformat()
                }
                
                unified_manager.emit_event(
                    "premarket_gap_alert", 
                    alert_data, 
                    priority=2  # High priority
                )
                
        except Exception as e:
            logger.error(f"❌ Error broadcasting gap alert: {e}")
            
    async def cleanup_old_data(self):
        """Remove data older than 2 days"""
        try:
            cutoff_date = date.today() - timedelta(days=2)
            
            db = next(get_db())
            try:
                # Delete old candles (cascades to alerts)
                deleted_candles = db.query(PremarketCandle).filter(
                    PremarketCandle.candle_date < cutoff_date
                ).delete()
                
                db.commit()
                
                if deleted_candles > 0:
                    logger.info(f"🧹 Cleaned up {deleted_candles} old premarket candles")
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
            
    async def finalize_session(self):
        """Finalize premarket session and cleanup"""
        try:
            if not self.is_premarket_active:
                return
                
            logger.info("⏰ PREMARKET SESSION ENDING - Finalizing all candles")
            
            # Finalize all remaining builders
            for builder in self.active_builders.values():
                if builder.symbol not in self.processed_symbols:
                    await self._finalize_candle(builder)
                    
            # Log session statistics
            logger.info(
                f"📊 Premarket Session Complete: "
                f"Ticks: {self.ticks_processed_today}, "
                f"Candles: {self.candles_built_today}, "
                f"Gaps: {self.gaps_detected_today}, "
                f"Alerts: {self.alerts_generated_today}"
            )
            
            # Cleanup old data
            await self.cleanup_old_data()
            
            # Clear builders
            self.active_builders.clear()
            self.is_premarket_active = False
            
        except Exception as e:
            logger.error(f"❌ Error finalizing premarket session: {e}")
            
    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics"""
        return {
            "is_premarket_active": self.is_premarket_active,
            "session_date": self.current_session_date.isoformat(),
            "ticks_processed": self.ticks_processed_today,
            "candles_built": self.candles_built_today,
            "gaps_detected": self.gaps_detected_today,
            "alerts_generated": self.alerts_generated_today,
            "active_builders": len(self.active_builders),
            "processed_symbols": len(self.processed_symbols),
            "previous_closes_loaded": len(self.previous_closes)
        }
        
    async def start_monitoring(self):
        """Start premarket monitoring background task"""
        logger.info("🔍 Starting premarket candle builder monitoring...")
        
        while True:
            try:
                current_time = datetime.now().time()
                
                # Check if we should be active
                if self.is_premarket_hours() and not self.is_premarket_active:
                    logger.info("🚨 Premarket hours detected - Ready for candle building")
                    
                # Check if session should end
                elif current_time >= self.premarket_end and self.is_premarket_active:
                    await self.finalize_session()
                    
                # Sleep until next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Premarket monitoring error: {e}")
                await asyncio.sleep(60)


# Singleton instance
premarket_candle_service = PremarketCandleBuilderService()

def get_premarket_candle_service() -> PremarketCandleBuilderService:
    """Get singleton premarket candle builder service"""
    return premarket_candle_service

async def start_premarket_monitoring():
    """Start premarket monitoring task"""
    await premarket_candle_service.start_monitoring()

# Utility functions for integration
async def get_todays_gaps(gap_type: str = None, min_strength: str = None) -> List[Dict[str, Any]]:
    """Get today's gap detection results"""
    try:
        db = next(get_db())
        
        query = db.query(PremarketCandle).filter(
            and_(
                PremarketCandle.candle_date == date.today(),
                PremarketCandle.is_significant_gap == True
            )
        )
        
        if gap_type:
            query = query.filter(PremarketCandle.gap_type == gap_type)
            
        if min_strength:
            strength_order = ["WEAK", "MODERATE", "STRONG", "VERY_STRONG"]
            min_index = strength_order.index(min_strength) if min_strength in strength_order else 0
            valid_strengths = strength_order[min_index:]
            query = query.filter(PremarketCandle.gap_strength.in_(valid_strengths))
            
        candles = query.order_by(desc(func.abs(PremarketCandle.gap_percentage))).all()
        
        results = []
        for candle in candles:
            results.append({
                "symbol": candle.symbol,
                "gap_type": candle.gap_type,
                "gap_percentage": float(candle.gap_percentage or 0),
                "gap_strength": candle.gap_strength,
                "open_price": float(candle.open_price),
                "close_price": float(candle.close_price),
                "previous_close": float(candle.previous_close or 0),
                "volume": candle.total_volume,
                "volume_ratio": float(candle.volume_ratio or 1),
                "data_quality": float(candle.data_quality_score or 0),
                "sector": candle.sector,
                "timestamp": candle.created_at.isoformat()
            })
            
        return results
        
    except Exception as e:
        logger.error(f"❌ Error getting today's gaps: {e}")
        return []
    finally:
        db.close()

async def get_active_alerts() -> List[Dict[str, Any]]:
    """Get active gap detection alerts"""
    try:
        db = next(get_db())
        
        alerts = db.query(GapDetectionAlert).filter(
            and_(
                GapDetectionAlert.alert_status == "ACTIVE",
                GapDetectionAlert.expires_at > datetime.now()
            )
        ).order_by(desc(GapDetectionAlert.confidence_score)).all()
        
        results = []
        for alert in alerts:
            results.append({
                "symbol": alert.symbol,
                "gap_type": alert.gap_type,
                "gap_percentage": float(alert.gap_percentage),
                "priority": alert.alert_priority,
                "confidence": float(alert.confidence_score),
                "trigger_price": float(alert.trigger_price),
                "expires_at": alert.expires_at.isoformat(),
                "timestamp": alert.alert_time.isoformat()
            })
            
        return results
        
    except Exception as e:
        logger.error(f"❌ Error getting active alerts: {e}")
        return []
    finally:
        db.close()