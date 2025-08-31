# services/breakout_scanner_service.py
"""
Real-Time Breakout Detection Service for Intraday Trading

This service provides comprehensive real-time breakout detection from live tick feed data
with support for multiple timeframes, technical indicators, and confirmation filters.

Key Features:
- Live tick ingestion and OHLC candle aggregation
- Multiple support/resistance level calculations
- Volume, momentum, and EMA confirmation filters  
- Real-time signal broadcasting via WebSocket and Redis
- Scalable architecture supporting 225+ instruments
- Production-grade error handling and logging

Author: Claude Code
Created: 2025-08-31
"""

import asyncio
import logging
import json
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta, time
from typing import Dict, List, Any, Optional, Deque, Tuple
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd
import numpy as np
from pandas import DataFrame, Timestamp

# Indian timezone
from zoneinfo import ZoneInfo
IST = ZoneInfo("Asia/Kolkata")

logger = logging.getLogger(__name__)


@dataclass
class BreakoutSignal:
    """
    Structured breakout signal with complete trading information
    
    Attributes:
        symbol: Trading symbol (e.g., "RELIANCE")
        strategy: Breakout strategy type ("ORB15", "Donchian", "PivotBreakout", etc.)
        signal: Trading direction ("BUY" or "SELL")
        breakout_level: Price level that was broken
        entry_price: Recommended entry price
        stop_loss: Stop loss price
        target: Target price
        volume: Current volume at breakout
        timestamp: ISO 8601 timestamp string with timezone
    """
    symbol: str
    strategy: str
    signal: str  # "BUY" or "SELL"
    breakout_level: float
    entry_price: float
    stop_loss: float
    target: float
    volume: int
    timestamp: str  # ISO 8601 string
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str)


class TickStore:
    """
    High-performance tick storage with rolling buffers
    
    Maintains recent tick history per instrument for candle building
    and technical analysis calculations.
    """
    
    def __init__(self, max_ticks: int = 5000):
        """
        Initialize tick storage
        
        Args:
            max_ticks: Maximum ticks to store per instrument
        """
        self._ticks: Dict[str, Deque[Dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=max_ticks)
        )
        self._last_prices: Dict[str, float] = {}
        self._last_update: Dict[str, datetime] = {}
        
        logger.info(f"✅ TickStore initialized with max_ticks={max_ticks}")
    
    def add_tick(self, instrument_key: str, ltp: float, ltt: int, ltq: int) -> None:
        """
        Add new tick data for an instrument
        
        Args:
            instrument_key: Unique instrument identifier
            ltp: Last traded price
            ltt: Last traded time (milliseconds timestamp)  
            ltq: Last traded quantity
            
        Raises:
            ValueError: If ltp is invalid or ltt is invalid timestamp
        """
        if not ltp or ltp <= 0:
            raise ValueError(f"Invalid LTP for {instrument_key}: {ltp}")
        
        try:
            # Convert milliseconds timestamp to datetime
            tick_time = datetime.fromtimestamp(ltt / 1000.0, tz=IST)
        except (ValueError, OSError) as e:
            raise ValueError(f"Invalid timestamp {ltt} for {instrument_key}: {e}") from e
        
        tick_data = {
            "price": Decimal(str(ltp)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            "quantity": ltq,
            "timestamp": tick_time,
            "unix_time": ltt
        }
        
        self._ticks[instrument_key].append(tick_data)
        self._last_prices[instrument_key] = float(tick_data["price"])
        self._last_update[instrument_key] = tick_time
    
    def get_recent_ticks(self, instrument_key: str, count: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent ticks for an instrument
        
        Args:
            instrument_key: Instrument identifier
            count: Number of recent ticks to return
            
        Returns:
            List of recent tick data dictionaries
        """
        if instrument_key not in self._ticks:
            return []
        
        ticks = list(self._ticks[instrument_key])
        return ticks[-count:] if count < len(ticks) else ticks
    
    def get_tick_count(self, instrument_key: str) -> int:
        """Get total tick count for instrument"""
        return len(self._ticks.get(instrument_key, []))
    
    def get_last_price(self, instrument_key: str) -> Optional[float]:
        """Get last traded price for instrument"""
        return self._last_prices.get(instrument_key)
    
    def get_price_range(self, instrument_key: str, minutes: int = 5) -> Tuple[float, float]:
        """
        Get price range (high, low) for specified minutes
        
        Args:
            instrument_key: Instrument identifier
            minutes: Time window in minutes
            
        Returns:
            Tuple of (high, low) prices
        """
        if instrument_key not in self._ticks:
            return (0.0, 0.0)
        
        cutoff_time = datetime.now(tz=IST) - timedelta(minutes=minutes)
        recent_ticks = [
            tick for tick in self._ticks[instrument_key] 
            if tick["timestamp"] >= cutoff_time
        ]
        
        if not recent_ticks:
            return (0.0, 0.0)
        
        prices = [float(tick["price"]) for tick in recent_ticks]
        return (max(prices), min(prices))


class CandleBuilder:
    """
    OHLC candle aggregation using Pandas resample functionality
    
    Builds 1-minute and 5-minute candles from tick data for
    technical analysis and breakout detection.
    """
    
    def __init__(self):
        """Initialize candle builder with DataFrame storage"""
        self._candles: Dict[str, Dict[str, DataFrame]] = defaultdict(
            lambda: {"1min": DataFrame(), "5min": DataFrame()}
        )
        self._last_candle_time: Dict[str, Dict[str, datetime]] = defaultdict(dict)
        
        logger.info("✅ CandleBuilder initialized with 1m and 5m timeframes")
    
    def build_candles(self, instrument_key: str, ticks: List[Dict[str, Any]]) -> Dict[str, DataFrame]:
        """
        Build OHLC candles from tick data using Pandas resample
        
        Args:
            instrument_key: Instrument identifier
            ticks: List of tick data with timestamp and price
            
        Returns:
            Dictionary with "1T" and "5T" DataFrame candles
            
        Raises:
            ValueError: If ticks data is invalid
        """
        if not ticks:
            return self._candles[instrument_key]
        
        try:
            # Convert ticks to DataFrame
            df_data = []
            for tick in ticks:
                df_data.append({
                    "timestamp": tick["timestamp"],
                    "price": float(tick["price"]),
                    "quantity": tick["quantity"]
                })
            
            if not df_data:
                return self._candles[instrument_key]
            
            df = DataFrame(df_data)
            df.set_index("timestamp", inplace=True)
            df.index = pd.to_datetime(df.index)
            
            # Build candles for both timeframes
            timeframes = {"1min": "1min", "5min": "5min"}
            
            for tf_key, tf_name in timeframes.items():
                try:
                    # Resample to OHLC
                    ohlc = df["price"].resample(tf_key).agg({
                        "open": "first",
                        "high": "max", 
                        "low": "min",
                        "close": "last"
                    }).dropna()
                    
                    # Add volume (sum of quantities)
                    volume = df["quantity"].resample(tf_key).sum()
                    
                    # Combine OHLC and volume
                    candles_df = pd.concat([ohlc, volume.rename("volume")], axis=1)
                    candles_df.dropna(inplace=True)
                    
                    if not candles_df.empty:
                        # Update stored candles (keep last 200 candles for memory efficiency)
                        self._candles[instrument_key][tf_key] = candles_df.tail(200).copy()
                        self._last_candle_time[instrument_key][tf_key] = candles_df.index[-1].to_pydatetime()
                        
                        logger.debug(f"📊 Built {len(candles_df)} {tf_name} candles for {instrument_key}")
                
                except Exception as e:
                    logger.error(f"❌ Error building {tf_name} candles for {instrument_key}: {e}")
                    continue
            
            return self._candles[instrument_key]
            
        except Exception as e:
            logger.error(f"❌ Error in build_candles for {instrument_key}: {e}")
            raise ValueError(f"Failed to build candles for {instrument_key}: {e}") from e
    
    def get_candles(self, instrument_key: str, timeframe: str = "1T") -> DataFrame:
        """
        Get recent candles for instrument and timeframe
        
        Args:
            instrument_key: Instrument identifier
            timeframe: "1T" for 1-minute, "5T" for 5-minute
            
        Returns:
            DataFrame with OHLC + volume candles
        """
        if timeframe not in ["1min", "5min"]:
            raise ValueError(f"Invalid timeframe: {timeframe}. Use '1min' or '5min'")
        
        return self._candles[instrument_key][timeframe].copy()
    
    def get_latest_candle(self, instrument_key: str, timeframe: str = "1min") -> Optional[Dict[str, Any]]:
        """
        Get the most recent completed candle
        
        Args:
            instrument_key: Instrument identifier  
            timeframe: Candle timeframe
            
        Returns:
            Dictionary with OHLC data or None if no candles
        """
        candles = self.get_candles(instrument_key, timeframe)
        
        if candles.empty:
            return None
        
        latest = candles.iloc[-1]
        return {
            "timestamp": latest.name,
            "open": latest["open"],
            "high": latest["high"], 
            "low": latest["low"],
            "close": latest["close"],
            "volume": latest["volume"]
        }


class LevelCalculator:
    """
    Support and resistance level calculation engine
    
    Calculates various technical levels including:
    - Yesterday's High & Low
    - Opening Range Breakout (ORB 15m & 30m)
    - Donchian Channel (20-period rolling)
    - Pivot Points (Classic R1/R2/S1/S2)
    - Central Pivot Range (CPR)
    """
    
    def __init__(self):
        """Initialize level calculator with cache storage"""
        self._daily_levels: Dict[str, Dict[str, float]] = {}
        self._orb_levels: Dict[str, Dict[str, float]] = {}
        self._donchian_levels: Dict[str, Dict[str, float]] = {}
        self._pivot_levels: Dict[str, Dict[str, float]] = {}
        self._cpr_levels: Dict[str, Dict[str, float]] = {}
        
        # Market session timings (IST)
        self.market_open = time(9, 15)
        self.orb_15_end = time(9, 30)
        self.orb_30_end = time(9, 45)
        
        logger.info("✅ LevelCalculator initialized with all level types")
    
    def calculate_yesterday_levels(
        self, 
        instrument_key: str, 
        yesterday_high: float, 
        yesterday_low: float
    ) -> Dict[str, float]:
        """
        Calculate yesterday's high and low levels
        
        Args:
            instrument_key: Instrument identifier
            yesterday_high: Previous day's high price
            yesterday_low: Previous day's low price
            
        Returns:
            Dictionary with yesterday's levels
            
        Raises:
            ValueError: If prices are invalid
        """
        if yesterday_high <= 0 or yesterday_low <= 0:
            raise ValueError(f"Invalid yesterday prices: high={yesterday_high}, low={yesterday_low}")
        
        if yesterday_high < yesterday_low:
            raise ValueError(f"Yesterday high ({yesterday_high}) cannot be less than low ({yesterday_low})")
        
        levels = {
            "yesterday_high": yesterday_high,
            "yesterday_low": yesterday_low,
            "yesterday_range": yesterday_high - yesterday_low
        }
        
        self._daily_levels[instrument_key] = levels
        logger.debug(f"📈 Calculated yesterday levels for {instrument_key}: H={yesterday_high:.2f} L={yesterday_low:.2f}")
        
        return levels
    
    def calculate_orb_levels(
        self, 
        instrument_key: str, 
        candles: DataFrame, 
        orb_minutes: int = 15
    ) -> Dict[str, float]:
        """
        Calculate Opening Range Breakout levels
        
        Args:
            instrument_key: Instrument identifier
            candles: 1-minute OHLC candles
            orb_minutes: ORB period in minutes (15 or 30)
            
        Returns:
            Dictionary with ORB high/low levels
            
        Raises:
            ValueError: If insufficient data or invalid orb_minutes
        """
        if orb_minutes not in [15, 30]:
            raise ValueError(f"ORB minutes must be 15 or 30, got: {orb_minutes}")
        
        if candles.empty:
            logger.warning(f"⚠️ No candles available for ORB calculation: {instrument_key}")
            return {}
        
        # Get today's candles starting from market open
        today = datetime.now(tz=IST).date()
        market_open_today = datetime.combine(today, self.market_open, tzinfo=IST)
        orb_end_time = market_open_today + timedelta(minutes=orb_minutes)
        
        # Filter candles for ORB period
        orb_candles = candles[
            (candles.index >= market_open_today) & 
            (candles.index < orb_end_time)
        ]
        
        if orb_candles.empty:
            logger.debug(f"📊 No ORB candles found for {instrument_key} (period: {orb_minutes}m)")
            return {}
        
        orb_high = orb_candles["high"].max()
        orb_low = orb_candles["low"].min()
        orb_range = orb_high - orb_low
        
        levels = {
            f"orb_{orb_minutes}_high": orb_high,
            f"orb_{orb_minutes}_low": orb_low,
            f"orb_{orb_minutes}_range": orb_range
        }
        
        self._orb_levels[instrument_key] = levels
        logger.debug(f"📈 Calculated ORB{orb_minutes} for {instrument_key}: H={orb_high:.2f} L={orb_low:.2f}")
        
        return levels
    
    def calculate_donchian_levels(
        self, 
        instrument_key: str, 
        candles: DataFrame, 
        period: int = 20
    ) -> Dict[str, float]:
        """
        Calculate Donchian Channel levels (rolling high/low)
        
        Args:
            instrument_key: Instrument identifier
            candles: OHLC candles DataFrame
            period: Rolling period for calculation
            
        Returns:
            Dictionary with Donchian channel levels
            
        Raises:
            ValueError: If insufficient data
        """
        if candles.empty or len(candles) < period:
            logger.warning(f"⚠️ Insufficient candles for Donchian({period}): {instrument_key}")
            return {}
        
        # Calculate rolling high and low
        donchian_high = candles["high"].rolling(window=period, min_periods=period//2).max().iloc[-1]
        donchian_low = candles["low"].rolling(window=period, min_periods=period//2).min().iloc[-1]
        
        if pd.isna(donchian_high) or pd.isna(donchian_low):
            logger.warning(f"⚠️ NaN values in Donchian calculation for {instrument_key}")
            return {}
        
        levels = {
            f"donchian_{period}_high": donchian_high,
            f"donchian_{period}_low": donchian_low,
            f"donchian_{period}_mid": (donchian_high + donchian_low) / 2
        }
        
        self._donchian_levels[instrument_key] = levels
        logger.debug(f"📈 Calculated Donchian({period}) for {instrument_key}: H={donchian_high:.2f} L={donchian_low:.2f}")
        
        return levels
    
    def calculate_pivot_levels(
        self, 
        instrument_key: str, 
        prev_high: float, 
        prev_low: float, 
        prev_close: float
    ) -> Dict[str, float]:
        """
        Calculate classic pivot point levels
        
        Args:
            instrument_key: Instrument identifier
            prev_high: Previous period high
            prev_low: Previous period low
            prev_close: Previous period close
            
        Returns:
            Dictionary with pivot levels (PP, R1, R2, S1, S2)
            
        Raises:
            ValueError: If prices are invalid
        """
        if any(p <= 0 for p in [prev_high, prev_low, prev_close]):
            raise ValueError(f"Invalid pivot prices: H={prev_high} L={prev_low} C={prev_close}")
        
        if prev_high < prev_low or prev_close < prev_low or prev_close > prev_high:
            raise ValueError(f"Inconsistent pivot prices: H={prev_high} L={prev_low} C={prev_close}")
        
        # Calculate pivot point
        pivot_point = (prev_high + prev_low + prev_close) / 3
        
        # Calculate resistance and support levels
        r1 = (2 * pivot_point) - prev_low
        r2 = pivot_point + (prev_high - prev_low)
        s1 = (2 * pivot_point) - prev_high
        s2 = pivot_point - (prev_high - prev_low)
        
        levels = {
            "pivot_point": pivot_point,
            "resistance_1": r1,
            "resistance_2": r2,
            "support_1": s1,
            "support_2": s2
        }
        
        self._pivot_levels[instrument_key] = levels
        logger.debug(f"📈 Calculated Pivots for {instrument_key}: PP={pivot_point:.2f} R1={r1:.2f} S1={s1:.2f}")
        
        return levels
    
    def calculate_cpr_levels(
        self, 
        instrument_key: str, 
        prev_high: float, 
        prev_low: float, 
        prev_close: float
    ) -> Dict[str, float]:
        """
        Calculate Central Pivot Range (CPR) levels
        
        Args:
            instrument_key: Instrument identifier
            prev_high: Previous period high
            prev_low: Previous period low  
            prev_close: Previous period close
            
        Returns:
            Dictionary with CPR levels (TC, PP, BC)
            
        Raises:
            ValueError: If prices are invalid
        """
        if any(p <= 0 for p in [prev_high, prev_low, prev_close]):
            raise ValueError(f"Invalid CPR prices: H={prev_high} L={prev_low} C={prev_close}")
        
        # Central Pivot Range calculation
        pivot_point = (prev_high + prev_low + prev_close) / 3
        top_central = (pivot_point - prev_low) + prev_close
        bottom_central = prev_close - (prev_high - pivot_point)
        
        levels = {
            "cpr_top": top_central,
            "cpr_pivot": pivot_point,
            "cpr_bottom": bottom_central,
            "cpr_width": top_central - bottom_central
        }
        
        self._cpr_levels[instrument_key] = levels
        logger.debug(f"📈 Calculated CPR for {instrument_key}: TC={top_central:.2f} BC={bottom_central:.2f}")
        
        return levels
    
    def get_all_levels(self, instrument_key: str) -> Dict[str, Any]:
        """
        Get all calculated levels for an instrument
        
        Args:
            instrument_key: Instrument identifier
            
        Returns:
            Dictionary containing all level types
        """
        return {
            "daily": self._daily_levels.get(instrument_key, {}),
            "orb": self._orb_levels.get(instrument_key, {}),
            "donchian": self._donchian_levels.get(instrument_key, {}),
            "pivot": self._pivot_levels.get(instrument_key, {}),
            "cpr": self._cpr_levels.get(instrument_key, {})
        }


class BreakoutStrategies:
    """
    Individual breakout detection strategy implementations
    
    Each strategy function analyzes candles and levels to detect
    specific breakout patterns with appropriate confirmation.
    """
    
    @staticmethod
    def yesterday_breakout(
        candles: DataFrame, 
        levels: Dict[str, float], 
        current_price: float
    ) -> Optional[Dict[str, Any]]:
        """
        Detect breakout above yesterday's high or below yesterday's low
        
        Args:
            candles: Recent OHLC candles
            levels: Yesterday's high/low levels
            current_price: Current market price
            
        Returns:
            Breakout signal dictionary or None
        """
        if candles.empty or not levels:
            return None
        
        yesterday_high = levels.get("yesterday_high")
        yesterday_low = levels.get("yesterday_low")
        
        if not yesterday_high or not yesterday_low:
            return None
        
        latest_candle = candles.iloc[-1]
        
        # Bullish breakout above yesterday's high
        if latest_candle["close"] > yesterday_high and current_price > yesterday_high:
            return {
                "type": "breakout",
                "direction": "BUY",
                "level": yesterday_high,
                "strength": (current_price - yesterday_high) / yesterday_high,
                "strategy": "YesterdayHigh"
            }
        
        # Bearish breakdown below yesterday's low
        elif latest_candle["close"] < yesterday_low and current_price < yesterday_low:
            return {
                "type": "breakdown", 
                "direction": "SELL",
                "level": yesterday_low,
                "strength": (yesterday_low - current_price) / yesterday_low,
                "strategy": "YesterdayLow"
            }
        
        return None
    
    @staticmethod
    def orb_breakout(
        candles: DataFrame, 
        levels: Dict[str, float], 
        current_price: float,
        orb_period: int = 15
    ) -> Optional[Dict[str, Any]]:
        """
        Detect Opening Range Breakout (ORB)
        
        Args:
            candles: Recent OHLC candles
            levels: ORB high/low levels
            current_price: Current market price
            orb_period: ORB period (15 or 30 minutes)
            
        Returns:
            ORB breakout signal or None
        """
        if candles.empty or not levels:
            return None
        
        orb_high = levels.get(f"orb_{orb_period}_high")
        orb_low = levels.get(f"orb_{orb_period}_low")
        
        if not orb_high or not orb_low:
            return None
        
        latest_candle = candles.iloc[-1]
        
        # Check if we're past ORB period (only trade after ORB is established)
        current_time = datetime.now(tz=IST).time()
        orb_end_time = time(9, 30) if orb_period == 15 else time(9, 45)
        
        if current_time < orb_end_time:
            return None
        
        # Bullish ORB breakout
        if latest_candle["close"] > orb_high and current_price > orb_high:
            return {
                "type": "breakout",
                "direction": "BUY", 
                "level": orb_high,
                "strength": (current_price - orb_high) / orb_high,
                "strategy": f"ORB{orb_period}"
            }
        
        # Bearish ORB breakdown
        elif latest_candle["close"] < orb_low and current_price < orb_low:
            return {
                "type": "breakdown",
                "direction": "SELL",
                "level": orb_low,
                "strength": (orb_low - current_price) / orb_low,
                "strategy": f"ORB{orb_period}"
            }
        
        return None
    
    @staticmethod 
    def donchian_breakout(
        candles: DataFrame,
        levels: Dict[str, float],
        current_price: float,
        period: int = 20
    ) -> Optional[Dict[str, Any]]:
        """
        Detect Donchian Channel breakout
        
        Args:
            candles: Recent OHLC candles
            levels: Donchian channel levels
            current_price: Current market price
            period: Donchian period
            
        Returns:
            Donchian breakout signal or None
        """
        if candles.empty or not levels:
            return None
        
        donchian_high = levels.get(f"donchian_{period}_high")
        donchian_low = levels.get(f"donchian_{period}_low")
        
        if not donchian_high or not donchian_low:
            return None
        
        latest_candle = candles.iloc[-1]
        
        # Bullish Donchian breakout
        if latest_candle["close"] > donchian_high and current_price > donchian_high:
            return {
                "type": "breakout",
                "direction": "BUY",
                "level": donchian_high,
                "strength": (current_price - donchian_high) / donchian_high,
                "strategy": f"Donchian{period}"
            }
        
        # Bearish Donchian breakdown  
        elif latest_candle["close"] < donchian_low and current_price < donchian_low:
            return {
                "type": "breakdown",
                "direction": "SELL",
                "level": donchian_low,
                "strength": (donchian_low - current_price) / donchian_low,
                "strategy": f"Donchian{period}"
            }
        
        return None
    
    @staticmethod
    def pivot_breakout(
        candles: DataFrame,
        levels: Dict[str, float], 
        current_price: float
    ) -> Optional[Dict[str, Any]]:
        """
        Detect pivot point breakout
        
        Args:
            candles: Recent OHLC candles
            levels: Pivot point levels
            current_price: Current market price
            
        Returns:
            Pivot breakout signal or None
        """
        if candles.empty or not levels:
            return None
        
        r1 = levels.get("resistance_1")
        r2 = levels.get("resistance_2")
        s1 = levels.get("support_1")
        s2 = levels.get("support_2")
        
        if not all([r1, r2, s1, s2]):
            return None
        
        latest_candle = candles.iloc[-1]
        
        # R2 breakout (strongest bullish signal)
        if latest_candle["close"] > r2 and current_price > r2:
            return {
                "type": "breakout",
                "direction": "BUY",
                "level": r2,
                "strength": (current_price - r2) / r2,
                "strategy": "PivotR2"
            }
        
        # R1 breakout
        elif latest_candle["close"] > r1 and current_price > r1:
            return {
                "type": "breakout", 
                "direction": "BUY",
                "level": r1,
                "strength": (current_price - r1) / r1,
                "strategy": "PivotR1"
            }
        
        # S1 breakdown
        elif latest_candle["close"] < s1 and current_price < s1:
            return {
                "type": "breakdown",
                "direction": "SELL",
                "level": s1,
                "strength": (s1 - current_price) / s1,
                "strategy": "PivotS1"
            }
        
        # S2 breakdown (strongest bearish signal)
        elif latest_candle["close"] < s2 and current_price < s2:
            return {
                "type": "breakdown",
                "direction": "SELL",
                "level": s2,
                "strength": (s2 - current_price) / s2,
                "strategy": "PivotS2"
            }
        
        return None
    
    @staticmethod
    def cpr_breakout(
        candles: DataFrame,
        levels: Dict[str, float],
        current_price: float
    ) -> Optional[Dict[str, Any]]:
        """
        Detect Central Pivot Range (CPR) breakout
        
        Args:
            candles: Recent OHLC candles
            levels: CPR levels
            current_price: Current market price
            
        Returns:
            CPR breakout signal or None
        """
        if candles.empty or not levels:
            return None
        
        cpr_top = levels.get("cpr_top")
        cpr_bottom = levels.get("cpr_bottom")
        
        if not cpr_top or not cpr_bottom:
            return None
        
        latest_candle = candles.iloc[-1]
        
        # CPR top breakout (bullish)
        if latest_candle["close"] > cpr_top and current_price > cpr_top:
            return {
                "type": "breakout",
                "direction": "BUY",
                "level": cpr_top,
                "strength": (current_price - cpr_top) / cpr_top,
                "strategy": "CPRBreakout"
            }
        
        # CPR bottom breakdown (bearish)
        elif latest_candle["close"] < cpr_bottom and current_price < cpr_bottom:
            return {
                "type": "breakdown",
                "direction": "SELL",
                "level": cpr_bottom,
                "strength": (cpr_bottom - current_price) / cpr_bottom,
                "strategy": "CPRBreakdown"
            }
        
        return None


class ConfirmationFilters:
    """
    Multi-layer confirmation filters for breakout validation
    
    Applies volume, momentum, and EMA filters to improve
    signal quality and reduce false breakouts.
    """
    
    @staticmethod
    def volume_filter(candles: DataFrame, volume_multiplier: float = 2.0) -> bool:
        """
        Check if current volume exceeds average volume threshold
        
        Args:
            candles: OHLC candles with volume data
            volume_multiplier: Multiplier for average volume threshold
            
        Returns:
            True if volume filter passes, False otherwise
        """
        if candles.empty or len(candles) < 20:
            return True  # Skip filter if insufficient data
        
        current_volume = candles.iloc[-1]["volume"]
        avg_volume_20 = candles["volume"].tail(20).mean()
        
        if pd.isna(avg_volume_20) or avg_volume_20 == 0:
            return True
        
        volume_ratio = current_volume / avg_volume_20
        return volume_ratio >= volume_multiplier
    
    @staticmethod
    def momentum_filter(candles: DataFrame, momentum_threshold: float = 0.015) -> bool:
        """
        Check if price momentum exceeds threshold (1.5% default)
        
        Args:
            candles: OHLC candles
            momentum_threshold: Minimum momentum percentage (0.015 = 1.5%)
            
        Returns:
            True if momentum filter passes, False otherwise
        """
        if candles.empty or len(candles) < 2:
            return True
        
        current_close = candles.iloc[-1]["close"]
        prev_close = candles.iloc[-2]["close"]
        
        if prev_close == 0:
            return True
        
        momentum = abs((current_close - prev_close) / prev_close)
        return momentum >= momentum_threshold
    
    @staticmethod
    def ema_filter(candles: DataFrame, fast_period: int = 20, slow_period: int = 50) -> Optional[str]:
        """
        Check EMA trend direction for trade bias
        
        Args:
            candles: OHLC candles
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            
        Returns:
            "bullish" if EMA20 > EMA50, "bearish" if EMA20 < EMA50, None if unclear
        """
        if candles.empty or len(candles) < slow_period:
            return None
        
        # Calculate EMAs
        ema_fast = candles["close"].ewm(span=fast_period).mean()
        ema_slow = candles["close"].ewm(span=slow_period).mean()
        
        if ema_fast.empty or ema_slow.empty:
            return None
        
        current_fast = ema_fast.iloc[-1]
        current_slow = ema_slow.iloc[-1]
        
        if pd.isna(current_fast) or pd.isna(current_slow):
            return None
        
        if current_fast > current_slow:
            return "bullish"
        elif current_fast < current_slow:
            return "bearish"
        else:
            return None
    
    @staticmethod
    def apply_all_filters(
        candles: DataFrame,
        signal_direction: str,
        volume_multiplier: float = 2.0,
        momentum_threshold: float = 0.015
    ) -> Dict[str, Any]:
        """
        Apply all confirmation filters to a breakout signal
        
        Args:
            candles: OHLC candles
            signal_direction: "BUY" or "SELL"
            volume_multiplier: Volume confirmation threshold
            momentum_threshold: Momentum confirmation threshold
            
        Returns:
            Dictionary with filter results and overall confirmation
        """
        results = {
            "volume_confirmed": ConfirmationFilters.volume_filter(candles, volume_multiplier),
            "momentum_confirmed": ConfirmationFilters.momentum_filter(candles, momentum_threshold),
            "ema_trend": ConfirmationFilters.ema_filter(candles),
            "trend_aligned": False,
            "overall_confirmed": False
        }
        
        # Check trend alignment
        if results["ema_trend"]:
            if signal_direction == "BUY" and results["ema_trend"] == "bullish":
                results["trend_aligned"] = True
            elif signal_direction == "SELL" and results["ema_trend"] == "bearish":
                results["trend_aligned"] = True
        
        # Overall confirmation logic
        confirmed_filters = sum([
            results["volume_confirmed"],
            results["momentum_confirmed"], 
            results["trend_aligned"] if results["ema_trend"] else True  # Skip trend if no data
        ])
        
        # Require at least 2 out of 3 filters to confirm
        total_filters = 3 if results["ema_trend"] else 2
        results["overall_confirmed"] = confirmed_filters >= max(2, total_filters - 1)
        
        return results


class BreakoutScannerService:
    """
    Main orchestrator for real-time breakout detection
    
    Coordinates tick ingestion, candle building, level calculation,
    breakout detection, and signal broadcasting.
    """
    
    def __init__(self, redis_client=None, websocket_manager=None):
        """
        Initialize breakout scanner service
        
        Args:
            redis_client: Redis client for pub/sub broadcasting
            websocket_manager: WebSocket manager for real-time updates
        """
        # Core components
        self.tick_store = TickStore(max_ticks=5000)
        self.candle_builder = CandleBuilder()
        self.level_calculator = LevelCalculator()
        
        # External integrations
        self.redis_client = redis_client
        self.websocket_manager = websocket_manager
        
        # Signal tracking
        self._recent_signals: Dict[str, List[BreakoutSignal]] = defaultdict(list)
        self._signal_cooldown: Dict[str, datetime] = {}
        self._processing_stats = {
            "ticks_processed": 0,
            "signals_generated": 0,
            "last_update": None
        }
        
        # Performance tracking
        self._performance_metrics = {
            "avg_processing_time": 0.0,
            "max_processing_time": 0.0,
            "error_count": 0,
            "success_count": 0
        }
        
        logger.info("🚀 BreakoutScannerService initialized successfully")
    
    async def ingest_tick(
        self, 
        instrument_key: str, 
        symbol: str,
        ltp: float, 
        ltt: int, 
        ltq: int
    ) -> None:
        """
        Ingest new tick data for processing
        
        Args:
            instrument_key: Unique instrument identifier
            symbol: Trading symbol (e.g., "RELIANCE")
            ltp: Last traded price
            ltt: Last traded time (milliseconds)
            ltq: Last traded quantity
            
        Raises:
            ValueError: If tick data is invalid
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate input data
            if not instrument_key or not symbol:
                raise ValueError("instrument_key and symbol cannot be empty")
            
            if ltp <= 0:
                raise ValueError(f"Invalid LTP: {ltp}")
            
            if ltt <= 0:
                raise ValueError(f"Invalid timestamp: {ltt}")
            
            # Store tick data
            self.tick_store.add_tick(instrument_key, ltp, ltt, ltq)
            self._processing_stats["ticks_processed"] += 1
            
            # Update performance metrics
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000  # ms
            self._update_performance_metrics(processing_time, success=True)
            
        except Exception as e:
            logger.error(f"❌ Error ingesting tick for {instrument_key}: {e}")
            self._update_performance_metrics(0, success=False)
            raise
    
    async def process_instrument(
        self,
        instrument_key: str,
        symbol: str,
        historical_data: Optional[Dict[str, Any]] = None
    ) -> List[BreakoutSignal]:
        """
        Process instrument for breakout detection
        
        Args:
            instrument_key: Instrument identifier
            symbol: Trading symbol
            historical_data: Optional historical OHLC data for level calculation
            
        Returns:
            List of detected breakout signals
            
        Raises:
            ValueError: If processing fails
        """
        start_time = asyncio.get_event_loop().time()
        signals = []
        
        try:
            # Check signal cooldown (prevent spam)
            if self._is_in_cooldown(instrument_key):
                return signals
            
            # Get recent ticks
            recent_ticks = self.tick_store.get_recent_ticks(instrument_key)
            if not recent_ticks:
                logger.debug(f"📊 No ticks available for {instrument_key}")
                return signals
            
            # Build candles
            candles = self.candle_builder.build_candles(instrument_key, recent_ticks)
            
            if candles["1min"].empty:
                logger.debug(f"📊 No 1m candles available for {instrument_key}")
                return signals
            
            # Calculate support/resistance levels
            await self._calculate_all_levels(instrument_key, candles, historical_data)
            
            # Get current price
            current_price = self.tick_store.get_last_price(instrument_key)
            if not current_price:
                return signals
            
            # Run breakout detection strategies
            strategies = [
                ("yesterday", self.level_calculator._daily_levels),
                ("orb_15", self.level_calculator._orb_levels),
                ("orb_30", self.level_calculator._orb_levels), 
                ("donchian", self.level_calculator._donchian_levels),
                ("pivot", self.level_calculator._pivot_levels),
                ("cpr", self.level_calculator._cpr_levels)
            ]
            
            for strategy_name, level_source in strategies:
                try:
                    signal = await self._detect_breakout(
                        strategy_name,
                        candles["1min"],
                        level_source.get(instrument_key, {}),
                        current_price,
                        symbol
                    )
                    
                    if signal:
                        signals.append(signal)
                        self._set_signal_cooldown(instrument_key)
                        logger.info(f"🚨 {strategy_name} breakout detected: {symbol} {signal.signal} @ {signal.entry_price}")
                
                except Exception as e:
                    logger.error(f"❌ Error in {strategy_name} strategy for {symbol}: {e}")
                    continue
            
            # Update stats
            self._processing_stats["signals_generated"] += len(signals)
            self._processing_stats["last_update"] = datetime.now(tz=IST)
            
            # Update performance metrics
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            self._update_performance_metrics(processing_time, success=True)
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Error processing instrument {instrument_key}: {e}")
            self._update_performance_metrics(0, success=False)
            raise ValueError(f"Failed to process instrument {instrument_key}: {e}") from e
    
    async def _calculate_all_levels(
        self,
        instrument_key: str,
        candles: Dict[str, DataFrame],
        historical_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Calculate all support/resistance levels for an instrument
        
        Args:
            instrument_key: Instrument identifier
            candles: Dictionary of candle DataFrames
            historical_data: Optional historical data for calculations
        """
        try:
            candles_1m = candles["1min"]
            
            # Yesterday levels (requires historical data)
            if historical_data:
                prev_high = historical_data.get("prev_high")
                prev_low = historical_data.get("prev_low") 
                prev_close = historical_data.get("prev_close")
                
                if all([prev_high, prev_low, prev_close]):
                    self.level_calculator.calculate_yesterday_levels(instrument_key, prev_high, prev_low)
                    self.level_calculator.calculate_pivot_levels(instrument_key, prev_high, prev_low, prev_close)
                    self.level_calculator.calculate_cpr_levels(instrument_key, prev_high, prev_low, prev_close)
            
            # ORB levels (15m and 30m)
            if not candles_1m.empty:
                self.level_calculator.calculate_orb_levels(instrument_key, candles_1m, orb_minutes=15)
                self.level_calculator.calculate_orb_levels(instrument_key, candles_1m, orb_minutes=30)
                
                # Donchian levels
                self.level_calculator.calculate_donchian_levels(instrument_key, candles_1m, period=20)
        
        except Exception as e:
            logger.error(f"❌ Error calculating levels for {instrument_key}: {e}")
    
    async def _detect_breakout(
        self,
        strategy_name: str,
        candles: DataFrame,
        levels: Dict[str, float],
        current_price: float,
        symbol: str
    ) -> Optional[BreakoutSignal]:
        """
        Detect breakout using specific strategy
        
        Args:
            strategy_name: Name of breakout strategy
            candles: OHLC candles
            levels: Support/resistance levels
            current_price: Current market price
            symbol: Trading symbol
            
        Returns:
            BreakoutSignal or None
        """
        try:
            # Strategy dispatch
            if strategy_name == "yesterday":
                breakout_data = BreakoutStrategies.yesterday_breakout(candles, levels, current_price)
            elif strategy_name == "orb_15":
                breakout_data = BreakoutStrategies.orb_breakout(candles, levels, current_price, orb_period=15)
            elif strategy_name == "orb_30":
                breakout_data = BreakoutStrategies.orb_breakout(candles, levels, current_price, orb_period=30)
            elif strategy_name == "donchian":
                breakout_data = BreakoutStrategies.donchian_breakout(candles, levels, current_price)
            elif strategy_name == "pivot":
                breakout_data = BreakoutStrategies.pivot_breakout(candles, levels, current_price)
            elif strategy_name == "cpr":
                breakout_data = BreakoutStrategies.cpr_breakout(candles, levels, current_price)
            else:
                logger.warning(f"⚠️ Unknown strategy: {strategy_name}")
                return None
            
            if not breakout_data:
                return None
            
            # Apply confirmation filters
            confirmation = ConfirmationFilters.apply_all_filters(
                candles,
                breakout_data["direction"],
                volume_multiplier=2.0,
                momentum_threshold=0.015
            )
            
            # Only proceed if breakout is confirmed
            if not confirmation["overall_confirmed"]:
                logger.debug(f"📊 Breakout not confirmed for {symbol} ({strategy_name})")
                return None
            
            # Calculate entry, stop loss, and target prices
            entry_price, stop_loss, target = self._calculate_trade_levels(
                breakout_data, current_price, candles
            )
            
            # Get current volume
            current_volume = int(candles.iloc[-1]["volume"]) if not candles.empty else 0
            
            # Create breakout signal
            signal = BreakoutSignal(
                symbol=symbol,
                strategy=breakout_data["strategy"],
                signal=breakout_data["direction"],
                breakout_level=breakout_data["level"],
                entry_price=entry_price,
                stop_loss=stop_loss,
                target=target,
                volume=current_volume,
                timestamp=datetime.now(tz=IST).isoformat()
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Error detecting breakout ({strategy_name}) for {symbol}: {e}")
            return None
    
    def _calculate_trade_levels(
        self,
        breakout_data: Dict[str, Any],
        current_price: float,
        candles: DataFrame
    ) -> Tuple[float, float, float]:
        """
        Calculate entry, stop loss, and target levels
        
        Args:
            breakout_data: Breakout detection results
            current_price: Current market price
            candles: OHLC candles for ATR calculation
            
        Returns:
            Tuple of (entry_price, stop_loss, target)
        """
        direction = breakout_data["direction"]
        breakout_level = breakout_data["level"]
        
        # Calculate ATR for dynamic stop loss
        atr = self._calculate_atr(candles, period=14)
        if not atr or atr == 0:
            atr = current_price * 0.02  # 2% fallback
        
        if direction == "BUY":
            # Entry slightly above breakout level
            entry_price = max(current_price, breakout_level * 1.002)  # 0.2% above
            
            # Stop loss below breakout level or using ATR
            stop_loss = min(breakout_level * 0.995, entry_price - (2 * atr))  # 0.5% below or 2x ATR
            
            # Target using 2:1 risk-reward ratio
            risk = entry_price - stop_loss
            target = entry_price + (2 * risk)
            
        else:  # SELL
            # Entry slightly below breakout level  
            entry_price = min(current_price, breakout_level * 0.998)  # 0.2% below
            
            # Stop loss above breakout level or using ATR
            stop_loss = max(breakout_level * 1.005, entry_price + (2 * atr))  # 0.5% above or 2x ATR
            
            # Target using 2:1 risk-reward ratio
            risk = stop_loss - entry_price
            target = entry_price - (2 * risk)
        
        return (
            round(entry_price, 2),
            round(stop_loss, 2),
            round(target, 2)
        )
    
    def _calculate_atr(self, candles: DataFrame, period: int = 14) -> Optional[float]:
        """
        Calculate Average True Range for stop loss calculation
        
        Args:
            candles: OHLC candles
            period: ATR calculation period
            
        Returns:
            ATR value or None if insufficient data
        """
        if candles.empty or len(candles) < period:
            return None
        
        try:
            # Calculate True Range
            candles = candles.copy()
            candles['prev_close'] = candles['close'].shift(1)
            
            candles['tr1'] = candles['high'] - candles['low']
            candles['tr2'] = abs(candles['high'] - candles['prev_close'])
            candles['tr3'] = abs(candles['low'] - candles['prev_close'])
            
            candles['true_range'] = candles[['tr1', 'tr2', 'tr3']].max(axis=1)
            
            # Calculate ATR using exponential moving average
            atr = candles['true_range'].ewm(span=period).mean().iloc[-1]
            
            return float(atr) if not pd.isna(atr) else None
            
        except Exception as e:
            logger.error(f"❌ Error calculating ATR: {e}")
            return None
    
    def _is_in_cooldown(self, instrument_key: str, cooldown_minutes: int = 5) -> bool:
        """Check if instrument is in signal cooldown period"""
        if instrument_key not in self._signal_cooldown:
            return False
        
        last_signal_time = self._signal_cooldown[instrument_key]
        cooldown_end = last_signal_time + timedelta(minutes=cooldown_minutes)
        
        return datetime.now(tz=IST) < cooldown_end
    
    def _set_signal_cooldown(self, instrument_key: str) -> None:
        """Set signal cooldown for instrument"""
        self._signal_cooldown[instrument_key] = datetime.now(tz=IST)
    
    def _update_performance_metrics(self, processing_time: float, success: bool) -> None:
        """Update internal performance metrics"""
        if success:
            self._performance_metrics["success_count"] += 1
            
            # Update average processing time
            current_avg = self._performance_metrics["avg_processing_time"]
            success_count = self._performance_metrics["success_count"]
            
            new_avg = ((current_avg * (success_count - 1)) + processing_time) / success_count
            self._performance_metrics["avg_processing_time"] = new_avg
            
            # Update max processing time
            if processing_time > self._performance_metrics["max_processing_time"]:
                self._performance_metrics["max_processing_time"] = processing_time
        else:
            self._performance_metrics["error_count"] += 1
    
    async def broadcast_signal(self, signal: BreakoutSignal) -> None:
        """
        Broadcast breakout signal to Redis and WebSocket
        
        Args:
            signal: BreakoutSignal to broadcast
        """
        try:
            signal_data = signal.to_dict()
            
            # Redis pub/sub broadcasting
            if self.redis_client:
                try:
                    await self.redis_client.publish("breakout_signals", signal.to_json())
                    logger.debug(f"📡 Signal broadcasted to Redis: {signal.symbol}")
                except Exception as e:
                    logger.error(f"❌ Redis broadcast error for {signal.symbol}: {e}")
            
            # WebSocket broadcasting
            if self.websocket_manager:
                try:
                    await self.websocket_manager.emit_event(
                        "breakout_signals",
                        {
                            "signal": signal_data,
                            "timestamp": signal.timestamp,
                            "source": "breakout_scanner"
                        },
                        priority=1  # High priority for trading signals
                    )
                    logger.debug(f"📡 Signal broadcasted to WebSocket: {signal.symbol}")
                except Exception as e:
                    logger.error(f"❌ WebSocket broadcast error for {signal.symbol}: {e}")
        
        except Exception as e:
            logger.error(f"❌ Error broadcasting signal for {signal.symbol}: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get service performance statistics
        
        Returns:
            Dictionary with processing statistics
        """
        return {
            "processing_stats": self._processing_stats.copy(),
            "performance_metrics": self._performance_metrics.copy(),
            "active_instruments": len(self.tick_store._ticks),
            "signals_in_cooldown": len(self._signal_cooldown),
            "recent_signals_count": sum(len(signals) for signals in self._recent_signals.values()),
            "service_status": "active"
        }


# Integration functions for FastAPI
async def create_breakout_scanner(redis_client=None, websocket_manager=None) -> BreakoutScannerService:
    """
    Create and initialize BreakoutScannerService instance
    
    Args:
        redis_client: Optional Redis client for pub/sub
        websocket_manager: Optional WebSocket manager for broadcasting
        
    Returns:
        Configured BreakoutScannerService instance
    """
    try:
        service = BreakoutScannerService(
            redis_client=redis_client,
            websocket_manager=websocket_manager
        )
        
        logger.info("🚀 BreakoutScannerService created successfully")
        return service
        
    except Exception as e:
        logger.error(f"❌ Failed to create BreakoutScannerService: {e}")
        raise


async def demo_breakout_detection(service: BreakoutScannerService) -> None:
    """
    Demonstration function with mock tick data
    
    Args:
        service: BreakoutScannerService instance
    """
    logger.info("🧪 Starting breakout detection demo...")
    
    try:
        # Mock historical data
        historical_data = {
            "prev_high": 2200.0,
            "prev_low": 2150.0, 
            "prev_close": 2180.0
        }
        
        # Mock tick data for RELIANCE
        instrument_key = "NSE_EQ|INE002A01018"
        symbol = "RELIANCE"
        base_price = 2190.0
        current_time = int(datetime.now().timestamp() * 1000)
        
        # Simulate ticks leading to breakout
        tick_prices = [
            2190.0, 2192.0, 2195.0, 2198.0, 2201.0, 2205.0  # Breakout above 2200
        ]
        
        for i, price in enumerate(tick_prices):
            await service.ingest_tick(
                instrument_key=instrument_key,
                symbol=symbol,
                ltp=price,
                ltt=current_time + (i * 60000),  # 1 minute intervals
                ltq=100
            )
            
            # Process for breakout detection
            signals = await service.process_instrument(
                instrument_key=instrument_key,
                symbol=symbol,
                historical_data=historical_data
            )
            
            # Broadcast any detected signals
            for signal in signals:
                await service.broadcast_signal(signal)
                logger.info(f"🚨 DEMO: {signal.strategy} signal - {signal.symbol} {signal.signal} @ {signal.entry_price}")
        
        # Print statistics
        stats = service.get_statistics()
        logger.info(f"📊 Demo completed. Stats: {stats}")
        
    except Exception as e:
        logger.error(f"❌ Demo error: {e}")


# Global service instance (will be created in app.py)
breakout_scanner_service: Optional[BreakoutScannerService] = None


def get_breakout_scanner_service() -> Optional[BreakoutScannerService]:
    """Get the global breakout scanner service instance"""
    return breakout_scanner_service


async def initialize_breakout_scanner_service(redis_client=None, websocket_manager=None) -> None:
    """
    Initialize the global breakout scanner service
    
    Args:
        redis_client: Redis client for broadcasting
        websocket_manager: WebSocket manager for real-time updates
    """
    global breakout_scanner_service
    
    try:
        breakout_scanner_service = await create_breakout_scanner(
            redis_client=redis_client,
            websocket_manager=websocket_manager
        )
        
        logger.info("🚀 Global BreakoutScannerService initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize global BreakoutScannerService: {e}")
        raise


if __name__ == "__main__":
    # Test the service with demo data
    async def test_service():
        service = await create_breakout_scanner()
        await demo_breakout_detection(service)
    
    asyncio.run(test_service())