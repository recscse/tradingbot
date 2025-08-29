"""
NIFTY 09:40 EMA + Candle Strength Strategy

Pure strategy logic with no I/O dependencies.
Implements the specific trading rules for NIFTY 50 at 9:40 AM.

Strategy Rules:
1. Calculate 20-period EMA on 5-minute data at 9:40 AM
2. Measure candle strength using OHLCV patterns
3. Generate BUY signal if: price > EMA AND candle_strength > 0.7 AND volume > avg_volume
4. Set stop loss at -2% and target at +4% (1:2 risk-reward)
5. Exit on EMA crossover or EOD
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
from datetime import datetime, time
import logging

logger = logging.getLogger(__name__)

def decide_trade(df_5m: pd.DataFrame, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Core NIFTY 09:40 strategy decision function with EMA crossover and trailing stops.
    
    Args:
        df_5m: 5-minute OHLCV DataFrame with columns [timestamp, open, high, low, close, volume]
        params: Strategy parameters dict with keys:
                - ema_period: EMA period (default: 20)
                - strength_threshold: Minimum candle strength (default: 0.7)
                - volume_multiplier: Volume threshold multiplier (default: 1.5)
                - stop_loss_pct: Stop loss percentage (default: 2.0)
                - target_pct: Target percentage (default: 4.0)
                - use_candle_low_sl: Use last candle low as stop loss (default: True)
                - ema_crossover_exit: Exit on EMA crossover (default: True)
                
    Returns:
        Trade signal dict or None if no signal:
        {
            "signal": "BUY" | "SELL" | "HOLD",
            "confidence": float,
            "entry_price": float,
            "stop_loss": float,
            "target": float,
            "reason": str,
            "timestamp": str,
            "ema_value": float,
            "candle_strength": float,
            "volume_ratio": float,
            "trailing_stop_logic": dict,
            "ema_crossover_detected": bool,
            "candle_low_sl": float
        }
    """
    # Set default parameters
    if params is None:
        params = {}
    
    ema_period = params.get('ema_period', 20)
    strength_threshold = params.get('strength_threshold', 0.7)
    volume_multiplier = params.get('volume_multiplier', 1.5)
    stop_loss_pct = params.get('stop_loss_pct', 2.0)
    target_pct = params.get('target_pct', 4.0)
    use_candle_low_sl = params.get('use_candle_low_sl', True)
    ema_crossover_exit = params.get('ema_crossover_exit', True)
    
    # Validate inputs
    if df_5m.empty or len(df_5m) < ema_period + 5:
        logger.debug("❌ Insufficient data for strategy calculation")
        return None
    
    required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    if not all(col in df_5m.columns for col in required_columns):
        logger.error(f"❌ Missing required columns. Expected: {required_columns}, Got: {list(df_5m.columns)}")
        return None
    
    try:
        # Ensure DataFrame is sorted by timestamp
        df = df_5m.copy().sort_values('timestamp').reset_index(drop=True)
        
        # Check if we're at the right time (9:40 AM or after)
        current_time = datetime.now().time()
        strategy_start_time = time(9, 40)  # 9:40 AM
        
        # For backtesting, check the last timestamp
        last_timestamp = pd.to_datetime(df['timestamp'].iloc[-1])
        if hasattr(last_timestamp, 'time'):
            last_time = last_timestamp.time()
            if last_time < strategy_start_time:
                logger.debug("⏰ Strategy not active before 9:40 AM")
                return {
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "entry_price": df['close'].iloc[-1],
                    "stop_loss": 0.0,
                    "target": 0.0,
                    "reason": "Before strategy start time (9:40 AM)",
                    "timestamp": df['timestamp'].iloc[-1],
                    "ema_value": 0.0,
                    "candle_strength": 0.0,
                    "volume_ratio": 0.0
                }
        
        # Calculate EMA using pandas
        df['ema'] = df['close'].ewm(span=ema_period, adjust=False).mean()
        
        # Calculate candle strength using the imported indicator
        from services.indicators import candle_strength
        df['strength'] = candle_strength(df, period=5)
        
        # Calculate volume ratio (current vs average)
        volume_avg_period = min(20, len(df) - 1)  # Use 20 periods or available data
        df['volume_avg'] = df['volume'].rolling(window=volume_avg_period).mean()
        df['volume_ratio'] = df['volume'] / df['volume_avg'].replace(0, 1)
        
        # Get current (latest) values
        current_idx = len(df) - 1
        current_price = df['close'].iloc[current_idx]
        current_ema = df['ema'].iloc[current_idx]
        current_strength = df['strength'].iloc[current_idx]
        current_volume_ratio = df['volume_ratio'].iloc[current_idx]
        
        # Get previous values for crossover detection
        prev_idx = current_idx - 1 if current_idx > 0 else current_idx
        prev_price = df['close'].iloc[prev_idx] if prev_idx >= 0 else current_price
        prev_ema = df['ema'].iloc[prev_idx] if prev_idx >= 0 else current_ema
        
        # Detect EMA crossover
        ema_crossover_detected = False
        crossover_direction = "none"
        
        if ema_crossover_exit and prev_idx != current_idx:
            # Bullish crossover: price crosses above EMA
            if prev_price <= prev_ema and current_price > current_ema:
                ema_crossover_detected = True
                crossover_direction = "bullish"
            # Bearish crossover: price crosses below EMA  
            elif prev_price >= prev_ema and current_price < current_ema:
                ema_crossover_detected = True
                crossover_direction = "bearish"
        
        # Calculate candle low stop loss
        candle_low_sl = 0.0
        if use_candle_low_sl:
            # Use the low of the current or previous candle as stop loss
            recent_lows = df['low'].tail(3)  # Last 3 candles
            candle_low_sl = recent_lows.min()
            
        # Calculate dynamic trailing stop logic
        trailing_stop_logic = {
            "ema_based_trail": current_ema * 0.995,  # EMA - 0.5%
            "candle_low_trail": candle_low_sl,
            "percentage_trail": current_price * (1 - stop_loss_pct / 100),
            "recommended_trail": "candle_low" if use_candle_low_sl else "percentage"
        }
        
        # Strategy logic
        price_above_ema = current_price > current_ema
        strength_sufficient = current_strength > strength_threshold
        volume_sufficient = current_volume_ratio > volume_multiplier
        
        # Calculate confidence based on how well conditions are met
        ema_confidence = min((current_price - current_ema) / current_ema * 100, 1.0) if current_ema > 0 else 0.0
        strength_confidence = current_strength
        volume_confidence = min(current_volume_ratio / volume_multiplier, 1.0)
        
        # Overall confidence (weighted average)
        overall_confidence = (0.4 * ema_confidence + 0.35 * strength_confidence + 0.25 * volume_confidence)
        overall_confidence = np.clip(overall_confidence, 0.0, 1.0)
        
        # Generate signal
        if price_above_ema and strength_sufficient and volume_sufficient:
            signal = "BUY"
            entry_price = current_price
            
            # Dynamic stop loss calculation
            if use_candle_low_sl and candle_low_sl > 0:
                # Use candle low as stop loss if it's reasonable (within 3% of entry)
                candle_low_distance = abs(entry_price - candle_low_sl) / entry_price * 100
                if candle_low_distance <= 3.0:  # Max 3% distance
                    stop_loss = candle_low_sl
                else:
                    stop_loss = entry_price * (1 - stop_loss_pct / 100)
            else:
                stop_loss = entry_price * (1 - stop_loss_pct / 100)
            
            target = entry_price * (1 + target_pct / 100)
            
            reason_parts = []
            if price_above_ema:
                reason_parts.append(f"Price {current_price:.2f} > EMA {current_ema:.2f}")
            if strength_sufficient:
                reason_parts.append(f"Candle strength {current_strength:.2f} > {strength_threshold}")
            if volume_sufficient:
                reason_parts.append(f"Volume ratio {current_volume_ratio:.2f} > {volume_multiplier}")
            
            reason = "BUY: " + ", ".join(reason_parts)
            
        else:
            # Check for sell conditions (price below EMA with weak strength)
            if current_price < current_ema and current_strength < 0.3:
                signal = "SELL"
                entry_price = current_price
                stop_loss = entry_price * (1 + stop_loss_pct / 100)  # Stop loss above for short
                target = entry_price * (1 - target_pct / 100)  # Target below for short
                
                reason = f"SELL: Price {current_price:.2f} < EMA {current_ema:.2f}, weak strength {current_strength:.2f}"
            else:
                signal = "HOLD"
                entry_price = current_price
                stop_loss = 0.0
                target = 0.0
                
                missing_conditions = []
                if not price_above_ema:
                    missing_conditions.append(f"Price {current_price:.2f} <= EMA {current_ema:.2f}")
                if not strength_sufficient:
                    missing_conditions.append(f"Candle strength {current_strength:.2f} <= {strength_threshold}")
                if not volume_sufficient:
                    missing_conditions.append(f"Volume ratio {current_volume_ratio:.2f} <= {volume_multiplier}")
                
                reason = "HOLD: " + ", ".join(missing_conditions) if missing_conditions else "HOLD: No clear signal"
        
        # Create result dictionary
        result = {
            "signal": signal,
            "confidence": round(overall_confidence, 3),
            "entry_price": round(entry_price, 2),
            "stop_loss": round(stop_loss, 2),
            "target": round(target, 2),
            "reason": reason,
            "timestamp": df['timestamp'].iloc[-1],
            "ema_value": round(current_ema, 2),
            "candle_strength": round(current_strength, 3),
            "volume_ratio": round(current_volume_ratio, 2),
            "trailing_stop_logic": {
                "ema_based_trail": round(trailing_stop_logic["ema_based_trail"], 2),
                "candle_low_trail": round(trailing_stop_logic["candle_low_trail"], 2),
                "percentage_trail": round(trailing_stop_logic["percentage_trail"], 2),
                "recommended_trail": trailing_stop_logic["recommended_trail"]
            },
            "ema_crossover_detected": ema_crossover_detected,
            "crossover_direction": crossover_direction,
            "candle_low_sl": round(candle_low_sl, 2),
            "use_candle_low_sl": use_candle_low_sl,
            "ema_crossover_exit": ema_crossover_exit
        }
        
        if signal != "HOLD":
            logger.info(f"🎯 NIFTY 09:40 Strategy: {signal} at {entry_price} (confidence: {overall_confidence:.1%})")
            logger.info(f"📊 EMA: {current_ema:.2f}, Strength: {current_strength:.2f}, Volume: {current_volume_ratio:.2f}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in NIFTY 09:40 strategy calculation: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def get_strategy_info() -> Dict[str, Any]:
    """
    Get strategy information and default parameters.
    
    Returns:
        Strategy metadata dict
    """
    return {
        "name": "NIFTY 09:40 EMA + Candle Strength",
        "description": "Trend-following strategy using EMA crossover and candle strength analysis",
        "version": "1.0.0",
        "author": "Trading System",
        "timeframe": "5m",
        "instruments": ["NSE_INDEX|Nifty 50", "NSE_INDEX|NIFTY 50"],
        "start_time": "09:40",
        "end_time": "15:15",
        "default_params": {
            "ema_period": 20,
            "strength_threshold": 0.7,
            "volume_multiplier": 1.5,
            "stop_loss_pct": 2.0,
            "target_pct": 4.0
        },
        "required_data": {
            "min_bars": 25,  # EMA period + buffer
            "timeframe": "5m",
            "columns": ["timestamp", "open", "high", "low", "close", "volume"]
        },
        "risk_parameters": {
            "max_risk_per_trade": 2.0,  # 2% max risk per trade
            "max_daily_trades": 3,      # Maximum 3 trades per day
            "max_position_size": 10000, # Maximum position size
            "required_margin": 50000    # Minimum margin required
        }
    }

def validate_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize strategy parameters.
    
    Args:
        params: Raw parameters dict
        
    Returns:
        Validated parameters dict
    """
    defaults = get_strategy_info()["default_params"]
    validated = {}
    
    # Validate each parameter with bounds checking
    validated['ema_period'] = max(5, min(50, params.get('ema_period', defaults['ema_period'])))
    validated['strength_threshold'] = max(0.1, min(1.0, params.get('strength_threshold', defaults['strength_threshold'])))
    validated['volume_multiplier'] = max(0.5, min(5.0, params.get('volume_multiplier', defaults['volume_multiplier'])))
    validated['stop_loss_pct'] = max(0.5, min(10.0, params.get('stop_loss_pct', defaults['stop_loss_pct'])))
    validated['target_pct'] = max(1.0, min(20.0, params.get('target_pct', defaults['target_pct'])))
    
    return validated

def backtest_summary_stats(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate summary statistics for a list of completed trades.
    
    Args:
        trades: List of trade result dictionaries
        
    Returns:
        Summary statistics dict
    """
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "avg_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "profit_factor": 0.0
        }
    
    # Extract returns
    returns = []
    for trade in trades:
        if trade.get('pnl') is not None:
            returns.append(trade['pnl'])
    
    if not returns:
        return {"total_trades": len(trades), "error": "No PnL data available"}
    
    returns_array = np.array(returns)
    
    # Basic statistics
    total_trades = len(returns)
    winning_trades = len([r for r in returns if r > 0])
    win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
    
    avg_return = np.mean(returns_array)
    total_return = np.sum(returns_array)
    
    # Risk metrics
    std_return = np.std(returns_array) if len(returns) > 1 else 0.0
    sharpe_ratio = avg_return / std_return if std_return > 0 else 0.0
    
    # Drawdown calculation
    cumulative_returns = np.cumsum(returns_array)
    running_max = np.maximum.accumulate(cumulative_returns)
    drawdowns = running_max - cumulative_returns
    max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0.0
    
    # Profit factor
    gross_profits = sum([r for r in returns if r > 0])
    gross_losses = sum([abs(r) for r in returns if r < 0])
    profit_factor = gross_profits / gross_losses if gross_losses > 0 else float('inf') if gross_profits > 0 else 0.0
    
    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": total_trades - winning_trades,
        "win_rate": round(win_rate * 100, 2),
        "avg_return": round(avg_return, 2),
        "total_return": round(total_return, 2),
        "std_return": round(std_return, 2),
        "sharpe_ratio": round(sharpe_ratio, 3),
        "max_drawdown": round(max_drawdown, 2),
        "profit_factor": round(profit_factor, 3),
        "best_trade": round(np.max(returns_array), 2),
        "worst_trade": round(np.min(returns_array), 2)
    }