"""
Pure pandas/numpy technical indicators for trading strategies.

All functions are unit-testable and side-effect free.
Designed for vectorized operations on OHLCV DataFrames.
"""

import pandas as pd
import numpy as np
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)

def ema(data: Union[pd.Series, np.ndarray], period: int) -> Union[pd.Series, np.ndarray]:
    """
    Exponential Moving Average calculation using pandas/numpy.
    
    Args:
        data: Price series (typically close prices)
        period: EMA period (e.g., 20 for 20-period EMA)
        
    Returns:
        EMA values as same type as input
    """
    if isinstance(data, pd.Series):
        return data.ewm(span=period, adjust=False).mean()
    elif isinstance(data, np.ndarray):
        # Pure numpy implementation
        alpha = 2 / (period + 1)
        ema_values = np.empty_like(data, dtype=float)
        ema_values[0] = data[0]
        
        for i in range(1, len(data)):
            ema_values[i] = alpha * data[i] + (1 - alpha) * ema_values[i - 1]
        
        return ema_values
    else:
        raise TypeError("Data must be pandas Series or numpy array")

def candle_strength(df: pd.DataFrame, period: int = 5) -> pd.Series:
    """
    Calculate candle strength indicator based on OHLC patterns.
    
    Measures:
    - Body size relative to total range
    - Wick symmetry
    - Volume confirmation
    - Recent price momentum
    
    Args:
        df: OHLCV DataFrame with columns [open, high, low, close, volume]
        period: Lookback period for strength calculation
        
    Returns:
        Series with strength values (0.0 to 1.0, higher = stronger)
    """
    if len(df) < period:
        return pd.Series(index=df.index, dtype=float).fillna(0.0)
    
    try:
        # Calculate basic candle metrics
        body_size = abs(df['close'] - df['open'])
        total_range = df['high'] - df['low']
        upper_wick = df['high'] - np.maximum(df['open'], df['close'])
        lower_wick = np.minimum(df['open'], df['close']) - df['low']
        
        # Avoid division by zero
        total_range = total_range.replace(0, np.nan)
        
        # 1. Body dominance (larger body = stronger candle)
        body_ratio = (body_size / total_range).fillna(0)
        
        # 2. Wick balance (balanced wicks = stronger)
        total_wicks = upper_wick + lower_wick
        wick_imbalance = np.where(
            total_wicks > 0,
            abs(upper_wick - lower_wick) / total_wicks,
            0
        )
        wick_balance = 1 - wick_imbalance
        
        # 3. Volume confirmation (rolling volume comparison)
        vol_ma = df['volume'].rolling(window=period).mean()
        vol_strength = np.minimum(df['volume'] / vol_ma.replace(0, 1), 2.0).fillna(1.0)
        
        # 4. Momentum component (price movement consistency)
        price_momentum = df['close'].pct_change(period).fillna(0)
        momentum_strength = np.minimum(abs(price_momentum) * 10, 1.0)
        
        # Combine all components with weights
        strength = (
            0.4 * body_ratio +           # 40% - body dominance  
            0.2 * wick_balance +         # 20% - wick balance
            0.2 * vol_strength +         # 20% - volume confirmation
            0.2 * momentum_strength      # 20% - momentum
        )
        
        # Normalize to 0-1 range and apply smoothing
        strength = np.clip(strength, 0, 1)
        strength = pd.Series(strength, index=df.index)
        
        # Apply 3-period smoothing to reduce noise
        strength_smoothed = strength.rolling(window=3, center=True).mean().fillna(strength)
        
        return strength_smoothed
        
    except Exception as e:
        logger.error(f"❌ Error calculating candle strength: {e}")
        return pd.Series(index=df.index, dtype=float).fillna(0.0)

def rsi(data: Union[pd.Series, np.ndarray], period: int = 14) -> Union[pd.Series, np.ndarray]:
    """
    Relative Strength Index calculation.
    
    Args:
        data: Price series (typically close prices)
        period: RSI period (typically 14)
        
    Returns:
        RSI values (0-100)
    """
    if isinstance(data, pd.Series):
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)
    
    elif isinstance(data, np.ndarray):
        delta = np.diff(data, prepend=data[0])
        gains = np.where(delta > 0, delta, 0)
        losses = np.where(delta < 0, -delta, 0)
        
        # Simple moving averages
        avg_gain = np.convolve(gains, np.ones(period)/period, mode='same')
        avg_loss = np.convolve(losses, np.ones(period)/period, mode='same')
        
        # Avoid division by zero
        avg_loss = np.where(avg_loss == 0, 1e-10, avg_loss)
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    else:
        raise TypeError("Data must be pandas Series or numpy array")

def bollinger_bands(data: Union[pd.Series, np.ndarray], period: int = 20, std_dev: float = 2.0) -> dict:
    """
    Bollinger Bands calculation.
    
    Args:
        data: Price series
        period: Moving average period
        std_dev: Standard deviation multiplier
        
    Returns:
        Dict with 'upper', 'middle', 'lower' bands
    """
    if isinstance(data, pd.Series):
        sma = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        
        return {
            'upper': sma + (std * std_dev),
            'middle': sma,
            'lower': sma - (std * std_dev)
        }
    
    elif isinstance(data, np.ndarray):
        # Rolling window computation using convolution
        sma = np.convolve(data, np.ones(period)/period, mode='same')
        
        # Calculate rolling standard deviation
        rolling_std = np.empty_like(data)
        for i in range(len(data)):
            start = max(0, i - period + 1)
            end = i + 1
            rolling_std[i] = np.std(data[start:end])
        
        return {
            'upper': sma + (rolling_std * std_dev),
            'middle': sma, 
            'lower': sma - (rolling_std * std_dev)
        }
    else:
        raise TypeError("Data must be pandas Series or numpy array")

def macd(data: Union[pd.Series, np.ndarray], fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """
    MACD (Moving Average Convergence Divergence) calculation.
    
    Args:
        data: Price series
        fast: Fast EMA period
        slow: Slow EMA period  
        signal: Signal line EMA period
        
    Returns:
        Dict with 'macd', 'signal', 'histogram'
    """
    fast_ema = ema(data, fast)
    slow_ema = ema(data, slow)
    
    if isinstance(data, pd.Series):
        macd_line = fast_ema - slow_ema
        signal_line = ema(macd_line, signal)
        histogram = macd_line - signal_line
    else:
        macd_line = fast_ema - slow_ema
        signal_line = ema(macd_line, signal)
        histogram = macd_line - signal_line
    
    return {
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    }

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Average True Range calculation.
    
    Args:
        df: OHLC DataFrame
        period: ATR period
        
    Returns:
        ATR values
    """
    high = df['high']
    low = df['low']
    close = df['close']
    prev_close = close.shift(1)
    
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    
    return atr

def support_resistance_levels(df: pd.DataFrame, window: int = 20) -> dict:
    """
    Calculate dynamic support and resistance levels.
    
    Args:
        df: OHLC DataFrame
        window: Lookback window for level calculation
        
    Returns:
        Dict with 'support' and 'resistance' levels
    """
    try:
        highs = df['high'].rolling(window=window).max()
        lows = df['low'].rolling(window=window).min()
        
        # Calculate levels based on recent price action
        resistance = highs.rolling(window=3).mean()
        support = lows.rolling(window=3).mean()
        
        return {
            'support': support,
            'resistance': resistance
        }
        
    except Exception as e:
        logger.error(f"❌ Error calculating support/resistance: {e}")
        return {
            'support': pd.Series(index=df.index).fillna(0),
            'resistance': pd.Series(index=df.index).fillna(0)
        }