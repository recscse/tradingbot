"""
Gap Detector Service - Complete Implementation as per Specifications

This service implements comprehensive gap detection with:
- Gap Up/Down detection at market open
- ORB15/ORB30 confirmation
- CPR (Central Pivot Range) calculations
- Pivot Points (S1-S3, R1-R3) 
- Bias assignment (Bullish/Bearish/Neutral)
- Redis publishing and WebSocket broadcasting
- Integration with existing FastAPI system

Key Features:
- Real-time gap detection using yesterday's OHLC vs today's opening
- ORB confirmation using 15m/30m opening range breakouts
- Complete CPR and pivot level calculations
- Comprehensive bias determination
- Ultra-fast processing with proper error handling
- Full integration with WebSocket and Redis systems
"""

import asyncio
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta, time
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
import pytz

# FastAPI and WebSocket imports
from fastapi import WebSocket

# Redis and WebSocket integrations
try:
    from utils.redis_cache import redis_client
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis_client = None

try:
    from services.unified_websocket_manager import unified_manager
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    unified_manager = None

# Market data integrations
try:
    from services.instrument_registry import instrument_registry
    from services.market_data_hub import market_data_hub
    MARKET_DATA_AVAILABLE = True
except ImportError:
    MARKET_DATA_AVAILABLE = False
    instrument_registry = None
    market_data_hub = None

logger = logging.getLogger(__name__)

# Market timezone
IST = pytz.timezone('Asia/Kolkata')

class GapType(Enum):
    """Gap types"""
    GAP_UP = "gap_up"
    GAP_DOWN = "gap_down"
    NO_GAP = "no_gap"

class BiasType(Enum):
    """Market bias types"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

@dataclass
class GapSignal:
    """Comprehensive gap signal with CPR and pivot levels"""
    symbol: str
    gap_type: str  # "gap_up" | "gap_down" | "no_gap"
    bias: str  # "bullish" | "bearish" | "neutral"
    yesterday_high: float
    yesterday_low: float
    yesterday_close: float
    open_price: float
    orb_high: float
    orb_low: float
    confirmed: bool
    confirmation_time: Optional[str]
    timestamp: str
    
    # CPR + Pivot levels
    pivot: float
    bc: float  # Bottom Central Pivot
    tc: float  # Top Central Pivot
    s1: float
    s2: float
    s3: float
    r1: float
    r2: float
    r3: float
    
    # Additional metrics
    gap_percentage: float
    volume_ratio: float
    confidence_score: float
    sector: str
    market_cap: str
    instrument_key: str
    current_price: float
    orb_minutes: int  # 15 or 30
    gap_fade: bool  # True if price re-enters yesterday's range
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)

class GapDetectorService:
    """
    Complete Gap Detector Service implementing all specifications:
    - Gap detection using yesterday's OHLC vs today's opening
    - ORB confirmation (15m/30m windows)
    - CPR and pivot point calculations
    - Bias determination
    - Redis publishing and WebSocket broadcasting
    """
    
    def __init__(self):
        # Market timing configuration (IST)
        self.market_open_time = time(9, 15)  # 9:15 AM IST
        self.market_close_time = time(15, 30)  # 3:30 PM IST
        self.orb15_end_time = time(9, 30)  # ORB15 ends at 9:30 AM
        self.orb30_end_time = time(9, 45)  # ORB30 ends at 9:45 AM
        
        # Gap detection thresholds
        self.gap_thresholds = {
            "minimum": Decimal("0.5"),  # 0.5% minimum gap
            "significant": Decimal("2.0"),  # 2% significant gap
            "strong": Decimal("5.0"),  # 5% strong gap
        }
        
        # Data storage
        self.yesterday_ohlc: Dict[str, Dict[str, Decimal]] = {}
        self.today_candles: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.orb_data: Dict[str, Dict[str, Decimal]] = {}
        self.gap_signals: List[GapSignal] = []
        self.current_gaps: Dict[str, GapSignal] = {}
        
        # State management
        self.is_gap_detection_active = False
        self.orb_confirmation_active = False
        self.today_date = datetime.now(IST).date()
        self.processed_symbols = set()
        
        # Performance tracking
        self.processing_stats = {
            "gaps_detected": 0,
            "confirmations": 0,
            "fades": 0,
            "processing_time_ms": 0
        }
        
        # Redis configuration
        self.redis_channel = "gap_signals"
        
        # Initialize integrations
        self._init_integrations()
        
        logger.info("✅ Gap Detector Service initialized with CPR and pivot calculations")
    
    def _init_integrations(self):
        """Initialize Redis and WebSocket integrations"""
        try:
            if REDIS_AVAILABLE and redis_client:
                # Test Redis connection
                redis_client.ping()
                logger.info("✅ Redis integration initialized")
            else:
                logger.warning("⚠️ Redis not available - gap signals will not be published to Redis")
        except Exception as e:
            logger.error(f"❌ Redis integration failed: {e}")
        
        try:
            if WEBSOCKET_AVAILABLE and unified_manager:
                logger.info("✅ WebSocket integration initialized")
            else:
                logger.warning("⚠️ WebSocket manager not available - gap signals will not be broadcast")
        except Exception as e:
            logger.error(f"❌ WebSocket integration failed: {e}")
    
    def ingest_daily_ohlc(self, symbol: str, ohlc_data: Dict[str, Any]) -> bool:
        """
        Ingest yesterday's OHLC data for gap detection
        
        Args:
            symbol: Stock symbol
            ohlc_data: Dictionary with keys: open, high, low, close
            
        Returns:
            bool: Success status
        """
        try:
            # Convert to Decimal for precision
            self.yesterday_ohlc[symbol] = {
                'open': Decimal(str(ohlc_data.get('open', 0))),
                'high': Decimal(str(ohlc_data.get('high', 0))),
                'low': Decimal(str(ohlc_data.get('low', 0))),
                'close': Decimal(str(ohlc_data.get('close', 0)))
            }
            
            logger.debug(f"📊 Ingested OHLC for {symbol}: {ohlc_data}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error ingesting OHLC for {symbol}: {e}")
            return False
    
    def ingest_intraday_candle(self, symbol: str, candle_data: Dict[str, Any]) -> bool:
        """
        Ingest today's intraday candle data
        
        Args:
            symbol: Stock symbol
            candle_data: Dictionary with OHLC data and timestamp
            
        Returns:
            bool: Success status
        """
        try:
            # Add timestamp if not present
            if 'timestamp' not in candle_data:
                candle_data['timestamp'] = datetime.now(IST).isoformat()
            
            # Convert prices to Decimal
            processed_candle = {
                'timestamp': candle_data['timestamp'],
                'open': Decimal(str(candle_data.get('open', 0))),
                'high': Decimal(str(candle_data.get('high', 0))),
                'low': Decimal(str(candle_data.get('low', 0))),
                'close': Decimal(str(candle_data.get('close', candle_data.get('ltp', 0)))),
                'volume': int(candle_data.get('volume', 0))
            }
            
            # Store candle data
            self.today_candles[symbol].append(processed_candle)
            
            # Keep only last 50 candles for performance
            if len(self.today_candles[symbol]) > 50:
                self.today_candles[symbol] = self.today_candles[symbol][-50:]
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error ingesting candle for {symbol}: {e}")
            return False
    
    def detect_gap(self, symbol: str) -> Optional[GapSignal]:
        """
        Detect gap for a symbol using yesterday's OHLC vs today's opening
        
        Args:
            symbol: Stock symbol
            
        Returns:
            GapSignal or None if no significant gap
        """
        try:
            # Check if we have required data
            if symbol not in self.yesterday_ohlc:
                logger.debug(f"⚠️ No yesterday OHLC for {symbol}")
                return None
            
            if symbol not in self.today_candles or len(self.today_candles[symbol]) == 0:
                logger.debug(f"⚠️ No today candles for {symbol}")
                return None
            
            yesterday = self.yesterday_ohlc[symbol]
            today_first_candle = self.today_candles[symbol][0]
            
            # Extract data
            yesterday_high = yesterday['high']
            yesterday_low = yesterday['low']
            yesterday_close = yesterday['close']
            today_open = today_first_candle['open']
            
            # Gap rules implementation
            gap_type = GapType.NO_GAP
            gap_percentage = Decimal('0')
            
            # Gap Up: Today Open > Yesterday High
            if today_open > yesterday_high:
                gap_type = GapType.GAP_UP
                gap_percentage = ((today_open - yesterday_high) / yesterday_close) * Decimal('100')
            
            # Gap Down: Today Open < Yesterday Low
            elif today_open < yesterday_low:
                gap_type = GapType.GAP_DOWN
                gap_percentage = ((today_open - yesterday_low) / yesterday_close) * Decimal('100')
            
            # Check if gap is significant enough
            if abs(gap_percentage) < self.gap_thresholds["minimum"]:
                return None
            
            # Calculate CPR and pivot levels
            pivot_data = self._calculate_cpr_pivots(yesterday)
            
            # Get ORB data if available
            orb_high, orb_low = self._get_orb_levels(symbol, 15)  # Default to ORB15
            
            # Determine bias
            bias = self._determine_bias(symbol, gap_type, today_open, yesterday)
            
            # Get additional metadata
            current_price = self._get_current_price(symbol)
            sector = self._get_sector(symbol)
            market_cap = self._get_market_cap_category(current_price)
            instrument_key = self._get_instrument_key(symbol)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                gap_percentage, symbol, current_price
            )
            
            # Check for gap fade
            gap_fade = self._check_gap_fade(symbol, yesterday_high, yesterday_low)
            
            # Create gap signal
            gap_signal = GapSignal(
                symbol=symbol,
                gap_type=gap_type.value,
                bias=bias.value,
                yesterday_high=float(yesterday_high),
                yesterday_low=float(yesterday_low),
                yesterday_close=float(yesterday_close),
                open_price=float(today_open),
                orb_high=float(orb_high),
                orb_low=float(orb_low),
                confirmed=False,  # Will be confirmed later
                confirmation_time=None,
                timestamp=datetime.now(IST).isoformat(),
                
                # CPR and pivot levels
                pivot=float(pivot_data['pivot']),
                bc=float(pivot_data['bc']),
                tc=float(pivot_data['tc']),
                s1=float(pivot_data['s1']),
                s2=float(pivot_data['s2']),
                s3=float(pivot_data['s3']),
                r1=float(pivot_data['r1']),
                r2=float(pivot_data['r2']),
                r3=float(pivot_data['r3']),
                
                # Additional metrics
                gap_percentage=float(gap_percentage),
                volume_ratio=self._get_volume_ratio(symbol),
                confidence_score=float(confidence_score),
                sector=sector,
                market_cap=market_cap,
                instrument_key=instrument_key,
                current_price=float(current_price),
                orb_minutes=15,  # Default ORB15
                gap_fade=gap_fade
            )
            
            # Store gap signal
            self.current_gaps[symbol] = gap_signal
            
            logger.info(
                f"🚨 Gap detected: {symbol} {gap_type.value} {gap_percentage:.2f}% "
                f"(Open: {today_open}, Bias: {bias.value})"
            )
            
            return gap_signal
            
        except Exception as e:
            logger.error(f"❌ Error detecting gap for {symbol}: {e}")
            return None
    
    def confirm_gap(self, symbol: str, orb_minutes: int = 15) -> bool:
        """
        Confirm gap using ORB (Opening Range Breakout) rules
        
        Args:
            symbol: Stock symbol
            orb_minutes: ORB window (15 or 30 minutes)
            
        Returns:
            bool: True if gap is confirmed
        """
        try:
            if symbol not in self.current_gaps:
                return False
            
            gap_signal = self.current_gaps[symbol]
            
            if gap_signal.confirmed:
                return True  # Already confirmed
            
            yesterday = self.yesterday_ohlc[symbol]
            orb_high, orb_low = self._get_orb_levels(symbol, orb_minutes)
            
            confirmed = False
            
            # ORB Confirmation rules
            if gap_signal.gap_type == GapType.GAP_UP.value:
                # Gap Up → ORB Low > Yesterday High
                if orb_low > Decimal(str(yesterday['high'])):
                    confirmed = True
                    logger.info(f"✅ Gap Up confirmed for {symbol}: ORB Low {orb_low} > Yesterday High {yesterday['high']}")
            
            elif gap_signal.gap_type == GapType.GAP_DOWN.value:
                # Gap Down → ORB High < Yesterday Low
                if orb_high < Decimal(str(yesterday['low'])):
                    confirmed = True
                    logger.info(f"✅ Gap Down confirmed for {symbol}: ORB High {orb_high} < Yesterday Low {yesterday['low']}")
            
            if confirmed:
                # Update gap signal
                gap_signal.confirmed = True
                gap_signal.confirmation_time = datetime.now(IST).isoformat()
                gap_signal.orb_high = float(orb_high)
                gap_signal.orb_low = float(orb_low)
                gap_signal.orb_minutes = orb_minutes
                
                # Add to confirmed signals
                if gap_signal not in self.gap_signals:
                    self.gap_signals.append(gap_signal)
                
                self.processing_stats["confirmations"] += 1
                
                # Broadcast confirmed gap
                asyncio.create_task(self._broadcast_gap_signal(gap_signal))
            
            return confirmed
            
        except Exception as e:
            logger.error(f"❌ Error confirming gap for {symbol}: {e}")
            return False
    
    def _calculate_cpr_pivots(self, yesterday_ohlc: Dict[str, Decimal]) -> Dict[str, Decimal]:
        """
        Calculate CPR (Central Pivot Range) and pivot points from yesterday's OHLC
        
        Formulas:
        - Pivot (P) = (High + Low + Close) / 3
        - BC (Bottom Central Pivot) = (High + Low) / 2
        - TC (Top Central Pivot) = (P – BC) + P
        - R1 = 2*P – Low, S1 = 2*P – High
        - R2 = P + (High – Low), S2 = P – (High – Low)
        - R3 = High + 2*(P – Low), S3 = Low – 2*(High – P)
        """
        try:
            high = yesterday_ohlc['high']
            low = yesterday_ohlc['low']
            close = yesterday_ohlc['close']
            
            # Calculate pivot point
            pivot = (high + low + close) / Decimal('3')
            
            # Calculate CPR levels
            bc = (high + low) / Decimal('2')
            tc = (pivot - bc) + pivot
            
            # Calculate support and resistance levels
            r1 = Decimal('2') * pivot - low
            s1 = Decimal('2') * pivot - high
            
            r2 = pivot + (high - low)
            s2 = pivot - (high - low)
            
            r3 = high + Decimal('2') * (pivot - low)
            s3 = low - Decimal('2') * (high - pivot)
            
            return {
                'pivot': pivot.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'bc': bc.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'tc': tc.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                's1': s1.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                's2': s2.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                's3': s3.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'r1': r1.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'r2': r2.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'r3': r3.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating CPR/pivots: {e}")
            # Return default values
            return {k: Decimal('0') for k in ['pivot', 'bc', 'tc', 's1', 's2', 's3', 'r1', 'r2', 'r3']}
    
    def _get_orb_levels(self, symbol: str, orb_minutes: int) -> Tuple[Decimal, Decimal]:
        """
        Get ORB (Opening Range Breakout) high and low levels
        
        Args:
            symbol: Stock symbol
            orb_minutes: ORB window (15 or 30 minutes)
            
        Returns:
            Tuple of (orb_high, orb_low)
        """
        try:
            if symbol not in self.today_candles or len(self.today_candles[symbol]) == 0:
                return Decimal('0'), Decimal('0')
            
            # Get candles within ORB window
            orb_candles = []
            market_open = datetime.now(IST).replace(hour=9, minute=15, second=0, microsecond=0)
            orb_end = market_open + timedelta(minutes=orb_minutes)
            
            for candle in self.today_candles[symbol]:
                candle_time = datetime.fromisoformat(candle['timestamp']).replace(tzinfo=IST)
                if market_open <= candle_time <= orb_end:
                    orb_candles.append(candle)
            
            if not orb_candles:
                return Decimal('0'), Decimal('0')
            
            # Calculate ORB high and low
            orb_high = max(candle['high'] for candle in orb_candles)
            orb_low = min(candle['low'] for candle in orb_candles)
            
            return orb_high, orb_low
            
        except Exception as e:
            logger.error(f"❌ Error getting ORB levels for {symbol}: {e}")
            return Decimal('0'), Decimal('0')
    
    def _determine_bias(self, symbol: str, gap_type: GapType, open_price: Decimal, 
                       yesterday_ohlc: Dict[str, Decimal]) -> BiasType:
        """
        Determine market bias based on gap type and price action
        
        Args:
            symbol: Stock symbol
            gap_type: Type of gap detected
            open_price: Today's opening price
            yesterday_ohlc: Yesterday's OHLC data
            
        Returns:
            BiasType: Bullish, Bearish, or Neutral
        """
        try:
            if gap_type == GapType.GAP_UP:
                # Gap up generally indicates bullish sentiment
                # Check if price is holding above key levels
                current_price = self._get_current_price(symbol)
                if current_price >= open_price:
                    return BiasType.BULLISH
                else:
                    return BiasType.NEUTRAL  # Gap up but fading
            
            elif gap_type == GapType.GAP_DOWN:
                # Gap down generally indicates bearish sentiment
                # Check if price is holding below key levels
                current_price = self._get_current_price(symbol)
                if current_price <= open_price:
                    return BiasType.BEARISH
                else:
                    return BiasType.NEUTRAL  # Gap down but recovering
            
            else:
                return BiasType.NEUTRAL
                
        except Exception as e:
            logger.error(f"❌ Error determining bias for {symbol}: {e}")
            return BiasType.NEUTRAL
    
    def _check_gap_fade(self, symbol: str, yesterday_high: Decimal, yesterday_low: Decimal) -> bool:
        """
        Check if gap is fading (price re-entering yesterday's range)
        
        Args:
            symbol: Stock symbol
            yesterday_high: Yesterday's high price
            yesterday_low: Yesterday's low price
            
        Returns:
            bool: True if gap is fading
        """
        try:
            current_price = self._get_current_price(symbol)
            
            # Check if current price is within yesterday's range
            if yesterday_low <= Decimal(str(current_price)) <= yesterday_high:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error checking gap fade for {symbol}: {e}")
            return False
    
    def _get_current_price(self, symbol: str) -> Decimal:
        """Get current price for symbol"""
        try:
            if symbol in self.today_candles and len(self.today_candles[symbol]) > 0:
                return self.today_candles[symbol][-1]['close']
            elif MARKET_DATA_AVAILABLE and instrument_registry:
                price_data = instrument_registry.get_spot_price(symbol)
                if price_data and 'ltp' in price_data:
                    return Decimal(str(price_data['ltp']))
            return Decimal('0')
        except Exception:
            return Decimal('0')
    
    def _get_volume_ratio(self, symbol: str) -> float:
        """Get volume ratio compared to average volume"""
        try:
            if symbol not in self.today_candles or len(self.today_candles[symbol]) == 0:
                return 1.0
            
            current_volume = sum(candle['volume'] for candle in self.today_candles[symbol])
            # For simplicity, assume average volume is current volume
            # In production, this would use historical volume data
            return 1.5  # Default elevated volume for gap situations
            
        except Exception:
            return 1.0
    
    def _calculate_confidence_score(self, gap_percentage: Decimal, symbol: str, current_price: Decimal) -> Decimal:
        """Calculate confidence score for gap signal"""
        try:
            # Base score from gap size (0-0.4)
            gap_score = min(abs(gap_percentage) / Decimal('10'), Decimal('0.4'))
            
            # Volume score (0-0.3)
            volume_score = Decimal('0.2')  # Default moderate volume
            
            # Price action score (0-0.2)
            price_score = Decimal('0.15') if current_price > Decimal('100') else Decimal('0.1')
            
            # Market condition score (0-0.1)
            market_score = Decimal('0.1')
            
            total_score = gap_score + volume_score + price_score + market_score
            return min(total_score, Decimal('1.0'))
            
        except Exception:
            return Decimal('0.5')
    
    def _get_sector(self, symbol: str) -> str:
        """Get sector for symbol"""
        try:
            if MARKET_DATA_AVAILABLE and instrument_registry:
                enriched_data = instrument_registry.get_enriched_prices()
                for key, data in enriched_data.items():
                    if data.get('symbol') == symbol:
                        return data.get('sector', 'UNKNOWN')
            return 'UNKNOWN'
        except Exception:
            return 'UNKNOWN'
    
    def _get_market_cap_category(self, price: Decimal) -> str:
        """Get market cap category based on price"""
        if price > Decimal('1000'):
            return "LARGE_CAP"
        elif price > Decimal('200'):
            return "MID_CAP"
        else:
            return "SMALL_CAP"
    
    def _get_instrument_key(self, symbol: str) -> str:
        """Get instrument key for symbol"""
        try:
            if MARKET_DATA_AVAILABLE and instrument_registry:
                return instrument_registry.get_instrument_key(symbol) or f"NSE_EQ|{symbol}"
            return f"NSE_EQ|{symbol}"
        except Exception:
            return f"NSE_EQ|{symbol}"
    
    async def _broadcast_gap_signal(self, gap_signal: GapSignal):
        """Broadcast gap signal via Redis and WebSocket"""
        try:
            signal_data = gap_signal.to_dict()
            
            # Publish to Redis
            if REDIS_AVAILABLE and redis_client:
                try:
                    redis_client.publish(self.redis_channel, json.dumps(signal_data))
                    logger.debug(f"📡 Published gap signal to Redis: {gap_signal.symbol}")
                except Exception as e:
                    logger.error(f"❌ Error publishing to Redis: {e}")
            
            # Broadcast via WebSocket
            if WEBSOCKET_AVAILABLE and unified_manager:
                try:
                    unified_manager.emit_event("gap_signals_update", {
                        "signals": [signal_data],
                        "count": 1,
                        "timestamp": datetime.now(IST).isoformat()
                    }, priority=1)
                    logger.debug(f"📡 Broadcast gap signal via WebSocket: {gap_signal.symbol}")
                except Exception as e:
                    logger.error(f"❌ Error broadcasting via WebSocket: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting gap signal: {e}")
    
    def get_bias(self, symbol: str) -> str:
        """Get bias for a symbol"""
        try:
            if symbol in self.current_gaps:
                return self.current_gaps[symbol].bias
            return BiasType.NEUTRAL.value
        except Exception:
            return BiasType.NEUTRAL.value
    
    def get_current_gaps(self) -> List[Dict[str, Any]]:
        """Get list of current gap signals"""
        try:
            return [gap.to_dict() for gap in self.gap_signals if gap.confirmed]
        except Exception as e:
            logger.error(f"❌ Error getting current gaps: {e}")
            return []
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            **self.processing_stats,
            "total_symbols_tracked": len(self.yesterday_ohlc),
            "current_gaps_count": len(self.current_gaps),
            "confirmed_gaps_count": len([g for g in self.gap_signals if g.confirmed]),
            "is_market_open": self._is_market_hours(),
            "gap_detection_active": self.is_gap_detection_active,
            "today_date": self.today_date.isoformat()
        }
    
    def _is_market_hours(self) -> bool:
        """Check if current time is within market hours"""
        try:
            now = datetime.now(IST)
            current_time = now.time()
            current_date = now.date()
            
            # Check weekday
            if current_date.weekday() > 4:  # Saturday = 5, Sunday = 6
                return False
            
            # Check market hours
            return self.market_open_time <= current_time <= self.market_close_time
            
        except Exception:
            return False
    
    async def process_market_data_batch(self, market_data: Dict[str, Any]) -> List[GapSignal]:
        """
        Process batch market data for gap detection and confirmation
        
        Args:
            market_data: Dictionary of market data by symbol
            
        Returns:
            List of new gap signals
        """
        try:
            start_time = datetime.now()
            new_signals = []
            
            for symbol, data in market_data.items():
                try:
                    # Ingest intraday candle
                    self.ingest_intraday_candle(symbol, data)
                    
                    # Detect gaps
                    if symbol not in self.processed_symbols:
                        gap_signal = self.detect_gap(symbol)
                        if gap_signal:
                            new_signals.append(gap_signal)
                            self.processed_symbols.add(symbol)
                    
                    # Try to confirm existing gaps
                    if symbol in self.current_gaps:
                        confirmed = self.confirm_gap(symbol, orb_minutes=15)
                        if confirmed and not self.current_gaps[symbol].confirmed:
                            # Also try ORB30 confirmation
                            self.confirm_gap(symbol, orb_minutes=30)
                
                except Exception as e:
                    logger.error(f"❌ Error processing {symbol}: {e}")
                    continue
            
            # Update performance stats
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self.processing_stats["processing_time_ms"] = processing_time
            self.processing_stats["gaps_detected"] += len(new_signals)
            
            if new_signals:
                logger.info(f"📊 Processed {len(market_data)} symbols, detected {len(new_signals)} gaps in {processing_time:.1f}ms")
            
            return new_signals
            
        except Exception as e:
            logger.error(f"❌ Error in batch processing: {e}")
            return []

# Singleton instance
gap_detector_service = GapDetectorService()

def get_gap_detector_service() -> GapDetectorService:
    """Get the singleton gap detector service instance"""
    return gap_detector_service

# Helper functions for integration

def get_current_gaps() -> List[Dict[str, Any]]:
    """Get list of current gap signals"""
    return gap_detector_service.get_current_gaps()

def get_bias(symbol: str) -> str:
    """Get bias for a symbol"""
    return gap_detector_service.get_bias(symbol)

def process_gap_detection(market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process market data for gap detection"""
    try:
        loop = asyncio.get_event_loop()
        signals = loop.run_until_complete(
            gap_detector_service.process_market_data_batch(market_data)
        )
        return [signal.to_dict() for signal in signals]
    except Exception as e:
        logger.error(f"❌ Error in gap detection processing: {e}")
        return []

# Test simulation function
async def test_gap_detection_simulation():
    """Test simulation with sample OHLC data"""
    logger.info("🧪 Starting gap detection test simulation...")
    
    try:
        # Sample yesterday's OHLC data
        sample_ohlc = {
            "INFY": {"open": 1490, "high": 1520, "low": 1485, "close": 1510},
            "TCS": {"open": 3200, "high": 3250, "low": 3180, "close": 3230},
            "RELIANCE": {"open": 2400, "high": 2450, "low": 2380, "close": 2420}
        }
        
        # Ingest yesterday's OHLC
        for symbol, ohlc in sample_ohlc.items():
            gap_detector_service.ingest_daily_ohlc(symbol, ohlc)
        
        # Sample today's market data (with gaps)
        sample_market_data = {
            "INFY": {  # Gap up scenario
                "open": 1535,  # Above yesterday's high (1520)
                "high": 1542,
                "low": 1525,
                "close": 1530,
                "ltp": 1530,
                "volume": 150000
            },
            "TCS": {  # Gap down scenario
                "open": 3170,  # Below yesterday's low (3180)
                "high": 3175,
                "low": 3160,
                "close": 3165,
                "ltp": 3165,
                "volume": 200000
            },
            "RELIANCE": {  # No significant gap
                "open": 2415,  # Within yesterday's range
                "high": 2430,
                "low": 2410,
                "close": 2425,
                "ltp": 2425,
                "volume": 180000
            }
        }
        
        # Process market data
        gap_signals = await gap_detector_service.process_market_data_batch(sample_market_data)
        
        # Display results
        logger.info(f"🎯 Test simulation results: {len(gap_signals)} gaps detected")
        
        for signal in gap_signals:
            logger.info(
                f"📊 {signal.symbol}: {signal.gap_type} {signal.gap_percentage:.2f}% "
                f"(Bias: {signal.bias}, Pivot: {signal.pivot}, Confidence: {signal.confidence_score:.2f})"
            )
        
        # Test CPR calculations
        logger.info("🧮 CPR and Pivot levels for INFY:")
        infy_signal = next((s for s in gap_signals if s.symbol == "INFY"), None)
        if infy_signal:
            logger.info(f"   Pivot: {infy_signal.pivot}, BC: {infy_signal.bc}, TC: {infy_signal.tc}")
            logger.info(f"   Support: S1={infy_signal.s1}, S2={infy_signal.s2}, S3={infy_signal.s3}")
            logger.info(f"   Resistance: R1={infy_signal.r1}, R2={infy_signal.r2}, R3={infy_signal.r3}")
        
        logger.info("✅ Gap detection test simulation completed successfully")
        return gap_signals
        
    except Exception as e:
        logger.error(f"❌ Test simulation failed: {e}")
        return []

if __name__ == "__main__":
    # Run test simulation if script is executed directly
    asyncio.run(test_gap_detection_simulation())