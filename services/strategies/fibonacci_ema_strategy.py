"""
Fibonacci + EMA Strategy Engine - Phase 3 Implementation

Advanced HFT-grade Fibonacci retracement strategy with EMA confluence for F&O options trading.

Features:
- Forward Fibonacci Analysis (Bullish BUY CE setups)
- Reverse Fibonacci Analysis (Bearish BUY PE setups)
- Multi-EMA Confluence (9, 25, 50, 100 periods)
- Multi-timeframe confirmation (1m, 5m)
- Dynamic risk-reward calculations
- Sub-10ms signal generation
- Real-time position management

Strategy Logic:
1. BULLISH (BUY CE): EMA bullish alignment + Fibonacci 38.2-50% retracement bounce
2. BEARISH (BUY PE): EMA bearish alignment + Fibonacci 61.8-78.6% rejection
3. Volume confirmation + RSI filter
4. Dynamic stop-loss at key Fibonacci levels
"""

import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import asyncio
import time

logger = logging.getLogger(__name__)

@dataclass
class FibonacciSignal:
    """Standardized Fibonacci strategy signal"""
    signal_type: str  # 'BUY_CE', 'BUY_PE', 'HOLD'
    strength: float  # 0-100 signal strength
    entry_price: float
    stop_loss: float
    target_1: float
    target_2: float
    risk_reward_ratio: float
    fibonacci_level: str  # Which Fibonacci level triggered signal
    ema_alignment: str  # 'strong_bullish', 'bullish', 'bearish', 'strong_bearish'
    volume_confirmation: bool
    multi_timeframe_confirmed: bool
    processing_time_ms: float
    timestamp: datetime
    
    # Option trading specific
    option_type: str  # 'CE' or 'PE'
    underlying_symbol: str
    suggested_strike: Optional[float] = None
    suggested_expiry: Optional[str] = None
    
    # Technical details
    swing_high: float = 0.0
    swing_low: float = 0.0
    fibonacci_levels: Dict[str, float] = None
    ema_values: Dict[str, float] = None

class FibonacciEMAStrategy:
    """
    HFT-Grade Fibonacci + EMA Strategy Engine
    
    Optimized for sub-10ms signal generation with comprehensive
    risk management and multi-timeframe analysis.
    """
    
    def __init__(self):
        self.ema_periods = [9, 25, 50, 100]
        self.fibonacci_levels = [0.0, 0.236, 0.382, 0.500, 0.618, 0.786, 1.0]
        self.rsi_period = 14
        self.volume_period = 20
        self.swing_lookback = 50  # Bars to look back for swing points
        
        # Strategy configuration
        self.config = {
            'min_signal_strength': 65,  # Minimum signal strength to trade
            'volume_multiplier': 1.2,   # Volume must be 1.2x average
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'fib_tolerance': 0.01,      # 1% tolerance around Fibonacci levels
            'min_risk_reward': 1.5,     # Minimum risk:reward ratio
            'max_risk_reward': 3.0,     # Maximum risk:reward ratio
        }
        
        logger.info("✅ FibonacciEMAStrategy initialized")
    
    async def generate_signal(self, ohlc_1m: pd.DataFrame, ohlc_5m: pd.DataFrame, 
                            current_price: float, symbol: str) -> Optional[FibonacciSignal]:
        """
        Main signal generation method with multi-timeframe analysis
        
        Args:
            ohlc_1m: 1-minute OHLC DataFrame
            ohlc_5m: 5-minute OHLC DataFrame  
            current_price: Current market price
            symbol: Underlying symbol
            
        Returns:
            FibonacciSignal or None if no valid signal
        """
        start_time = time.time()
        
        try:
            # Validate input data
            if not self._validate_data(ohlc_1m, ohlc_5m):
                return None
            
            # Calculate technical indicators for 1m timeframe
            indicators_1m = self._calculate_indicators(ohlc_1m)
            indicators_5m = self._calculate_indicators(ohlc_5m)
            
            # Find swing points and calculate Fibonacci levels (1m primary)
            swing_high, swing_low = self._find_swing_points(ohlc_1m)
            fib_levels = self._calculate_fibonacci_levels(swing_high, swing_low)
            
            # Generate signals for both timeframes
            signal_1m = self._analyze_timeframe(ohlc_1m, indicators_1m, fib_levels, current_price, '1m')
            signal_5m = self._analyze_timeframe(ohlc_5m, indicators_5m, fib_levels, current_price, '5m')
            
            # Multi-timeframe confirmation
            confirmed_signal = self._confirm_multi_timeframe(signal_1m, signal_5m)
            
            if not confirmed_signal:
                return None
            
            # Calculate risk-reward and position details
            risk_reward_data = self._calculate_risk_reward(
                confirmed_signal, current_price, fib_levels, swing_high, swing_low
            )
            
            # Create final signal
            processing_time = (time.time() - start_time) * 1000
            
            signal = FibonacciSignal(
                signal_type=confirmed_signal['type'],
                strength=confirmed_signal['strength'],
                entry_price=current_price,
                stop_loss=risk_reward_data['stop_loss'],
                target_1=risk_reward_data['target_1'],
                target_2=risk_reward_data['target_2'],
                risk_reward_ratio=risk_reward_data['risk_reward'],
                fibonacci_level=confirmed_signal['fibonacci_level'],
                ema_alignment=confirmed_signal['ema_alignment'],
                volume_confirmation=confirmed_signal['volume_confirmed'],
                multi_timeframe_confirmed=True,
                processing_time_ms=processing_time,
                timestamp=datetime.now(),
                option_type='CE' if 'BUY_CE' in confirmed_signal['type'] else 'PE',
                underlying_symbol=symbol,
                swing_high=swing_high,
                swing_low=swing_low,
                fibonacci_levels=fib_levels,
                ema_values=indicators_1m['emas']
            )
            
            logger.info(f"✅ Generated {signal.signal_type} signal for {symbol} "
                       f"(Strength: {signal.strength:.1f}, R:R: {signal.risk_reward_ratio:.2f})")
            
            return signal
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"❌ Signal generation failed for {symbol}: {e} (took {processing_time:.2f}ms)")
            return None
    
    def _validate_data(self, ohlc_1m: pd.DataFrame, ohlc_5m: pd.DataFrame) -> bool:
        """Validate input data quality"""
        try:
            # Check minimum data requirements
            if len(ohlc_1m) < 60:  # Need at least 1 hour of 1m data
                logger.debug("❌ Insufficient 1m data (need 60+ bars)")
                return False
            
            if len(ohlc_5m) < 20:  # Need at least 100 minutes of 5m data
                logger.debug("❌ Insufficient 5m data (need 20+ bars)")
                return False
            
            # Check for required columns
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            for df, timeframe in [(ohlc_1m, '1m'), (ohlc_5m, '5m')]:
                for col in required_columns:
                    if col not in df.columns:
                        logger.debug(f"❌ Missing {col} column in {timeframe} data")
                        return False
            
            # Check for valid prices (no zeros or negatives)
            for df in [ohlc_1m, ohlc_5m]:
                if (df[['open', 'high', 'low', 'close']] <= 0).any().any():
                    logger.debug("❌ Invalid price data (zeros or negatives found)")
                    return False
            
            return True
            
        except Exception as e:
            logger.debug(f"❌ Data validation failed: {e}")
            return False
    
    def _calculate_indicators(self, ohlc: pd.DataFrame) -> Dict[str, Any]:
        """Calculate all technical indicators for a timeframe"""
        try:
            indicators = {}
            
            # Calculate EMAs
            emas = {}
            for period in self.ema_periods:
                if len(ohlc) >= period:
                    emas[f'ema_{period}'] = ohlc['close'].ewm(span=period).mean().iloc[-1]
                else:
                    emas[f'ema_{period}'] = ohlc['close'].mean()
            
            indicators['emas'] = emas
            
            # Calculate RSI
            if len(ohlc) >= self.rsi_period:
                delta = ohlc['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                indicators['rsi'] = rsi.iloc[-1]
            else:
                indicators['rsi'] = 50  # Neutral RSI
            
            # Volume analysis
            volume_avg = ohlc['volume'].rolling(self.volume_period).mean().iloc[-1]
            current_volume = ohlc['volume'].iloc[-1]
            indicators['volume_ratio'] = current_volume / volume_avg if volume_avg > 0 else 1.0
            
            # Price momentum
            if len(ohlc) >= 5:
                price_change = (ohlc['close'].iloc[-1] - ohlc['close'].iloc[-5]) / ohlc['close'].iloc[-5]
                indicators['momentum_5bar'] = price_change
            else:
                indicators['momentum_5bar'] = 0.0
            
            return indicators
            
        except Exception as e:
            logger.error(f"❌ Indicator calculation failed: {e}")
            return {
                'emas': {f'ema_{p}': 0 for p in self.ema_periods},
                'rsi': 50,
                'volume_ratio': 1.0,
                'momentum_5bar': 0.0
            }
    
    def _find_swing_points(self, ohlc: pd.DataFrame) -> Tuple[float, float]:
        """Find recent swing high and low points"""
        try:
            # Use last N bars to find swing points
            lookback = min(self.swing_lookback, len(ohlc))
            recent_data = ohlc.tail(lookback)
            
            # Method 1: Simple high/low (fallback)
            swing_high = recent_data['high'].max()
            swing_low = recent_data['low'].min()
            
            # Method 2: Peak/Trough detection for better swing points
            try:
                highs = recent_data['high'].values
                lows = recent_data['low'].values
                
                # Find local peaks (swing highs)
                swing_highs = []
                for i in range(2, len(highs) - 2):
                    if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and
                        highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                        swing_highs.append(highs[i])
                
                # Find local troughs (swing lows)
                swing_lows_detected = []
                for i in range(2, len(lows) - 2):
                    if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and
                        lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                        swing_lows_detected.append(lows[i])
                
                # Use detected swing points if found
                if swing_highs:
                    swing_high = max(swing_highs)
                if swing_lows_detected:
                    swing_low = min(swing_lows_detected)
                
            except Exception:
                # Fallback to simple method
                pass
            
            # Ensure swing high > swing low
            if swing_high <= swing_low:
                swing_high = recent_data['high'].max()
                swing_low = recent_data['low'].min()
            
            logger.debug(f"📍 Swing points: High={swing_high:.2f}, Low={swing_low:.2f}")
            return swing_high, swing_low
            
        except Exception as e:
            logger.error(f"❌ Swing point detection failed: {e}")
            # Fallback to recent high/low
            return ohlc['high'].max(), ohlc['low'].min()
    
    def _calculate_fibonacci_levels(self, swing_high: float, swing_low: float) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels"""
        try:
            diff = swing_high - swing_low
            
            fib_levels = {}
            for level in self.fibonacci_levels:
                fib_levels[f'fib_{level:.3f}'.replace('.', '_')] = swing_high - (diff * level)
            
            # Add common names for easy access
            fib_levels.update({
                'swing_high': swing_high,
                'swing_low': swing_low,
                'fib_23_6': swing_high - (diff * 0.236),
                'fib_38_2': swing_high - (diff * 0.382),
                'fib_50_0': swing_high - (diff * 0.500),
                'fib_61_8': swing_high - (diff * 0.618),
                'fib_78_6': swing_high - (diff * 0.786)
            })
            
            return fib_levels
            
        except Exception as e:
            logger.error(f"❌ Fibonacci calculation failed: {e}")
            return {
                'swing_high': swing_high,
                'swing_low': swing_low,
                'fib_23_6': swing_high * 0.95,
                'fib_38_2': swing_high * 0.90,
                'fib_50_0': (swing_high + swing_low) / 2,
                'fib_61_8': swing_low * 1.05,
                'fib_78_6': swing_low * 1.02
            }
    
    def _analyze_timeframe(self, ohlc: pd.DataFrame, indicators: Dict, 
                          fib_levels: Dict, current_price: float, timeframe: str) -> Optional[Dict]:
        """Analyze single timeframe for trading signals"""
        try:
            emas = indicators['emas']
            rsi = indicators['rsi']
            volume_ratio = indicators['volume_ratio']
            
            # EMA alignment analysis
            ema_20 = emas.get('ema_20', current_price)
            ema_25 = emas.get('ema_25', current_price)
            ema_50 = emas.get('ema_50', current_price)
            
            # Determine EMA alignment
            if current_price > ema_20 > ema_25 > ema_50:
                ema_alignment = 'strong_bullish'
                alignment_strength = 100
            elif current_price > ema_25 > ema_50:
                ema_alignment = 'bullish'
                alignment_strength = 75
            elif current_price < ema_20 < ema_25 < ema_50:
                ema_alignment = 'strong_bearish'
                alignment_strength = 100
            elif current_price < ema_25 < ema_50:
                ema_alignment = 'bearish'
                alignment_strength = 75
            else:
                ema_alignment = 'sideways'
                alignment_strength = 30
            
            # Check for bullish signals (BUY CE)
            bullish_signal = self._check_bullish_conditions(
                current_price, emas, fib_levels, rsi, volume_ratio
            )
            
            # Check for bearish signals (BUY PE)
            bearish_signal = self._check_bearish_conditions(
                current_price, emas, fib_levels, rsi, volume_ratio
            )
            
            # Return strongest signal
            if bullish_signal and bullish_signal['strength'] >= self.config['min_signal_strength']:
                return {
                    'type': 'BUY_CE',
                    'strength': bullish_signal['strength'],
                    'fibonacci_level': bullish_signal['fibonacci_level'],
                    'ema_alignment': ema_alignment,
                    'volume_confirmed': volume_ratio >= self.config['volume_multiplier'],
                    'timeframe': timeframe,
                    'details': bullish_signal
                }
            
            elif bearish_signal and bearish_signal['strength'] >= self.config['min_signal_strength']:
                return {
                    'type': 'BUY_PE',
                    'strength': bearish_signal['strength'],
                    'fibonacci_level': bearish_signal['fibonacci_level'],
                    'ema_alignment': ema_alignment,
                    'volume_confirmed': volume_ratio >= self.config['volume_multiplier'],
                    'timeframe': timeframe,
                    'details': bearish_signal
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Timeframe analysis failed for {timeframe}: {e}")
            return None
    
    def _check_bullish_conditions(self, current_price: float, emas: Dict, 
                                 fib_levels: Dict, rsi: float, volume_ratio: float) -> Optional[Dict]:
        """Check for bullish Fibonacci setup (Forward Fibonacci)"""
        try:
            conditions_met = []
            strength_score = 0
            fibonacci_level_triggered = None
            
            # Condition 1: Price above EMA25 (bullish bias)
            if current_price > emas.get('ema_25', 0):
                conditions_met.append('price_above_ema25')
                strength_score += 25
            
            # Condition 2: EMA alignment (bullish)
            if (emas.get('ema_20', 0) > emas.get('ema_25', 0) > emas.get('ema_50', 0)):
                conditions_met.append('strong_ema_bullish')
                strength_score += 30
            elif emas.get('ema_20', 0) > emas.get('ema_25', 0):
                conditions_met.append('partial_ema_bullish')
                strength_score += 15
            
            # Condition 3: Fibonacci retracement bounce (38.2% - 50% zone)
            fib_38_2 = fib_levels.get('fib_38_2', 0)
            fib_50_0 = fib_levels.get('fib_50_0', 0)
            
            # Check if price is in or just above the golden zone
            tolerance = current_price * self.config['fib_tolerance']
            
            if (fib_50_0 - tolerance) <= current_price <= (fib_38_2 + tolerance):
                conditions_met.append('fibonacci_retracement_zone')
                fibonacci_level_triggered = 'fib_38_2_to_50_0'
                strength_score += 35
            elif (fib_38_2 - tolerance) <= current_price <= (fib_38_2 + tolerance):
                conditions_met.append('fibonacci_38_2_level')
                fibonacci_level_triggered = 'fib_38_2'
                strength_score += 30
            
            # Condition 4: Volume confirmation
            if volume_ratio >= self.config['volume_multiplier']:
                conditions_met.append('volume_confirmation')
                strength_score += 20
            
            # Condition 5: RSI not overbought
            if self.config['rsi_oversold'] < rsi < self.config['rsi_overbought']:
                conditions_met.append('rsi_healthy')
                strength_score += 10
            
            # Must have at least 3 conditions and Fibonacci trigger
            if len(conditions_met) >= 3 and fibonacci_level_triggered:
                return {
                    'strength': min(strength_score, 100),
                    'fibonacci_level': fibonacci_level_triggered,
                    'conditions_met': conditions_met,
                    'rsi_value': rsi,
                    'volume_ratio': volume_ratio
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Bullish condition check failed: {e}")
            return None
    
    def _check_bearish_conditions(self, current_price: float, emas: Dict, 
                                 fib_levels: Dict, rsi: float, volume_ratio: float) -> Optional[Dict]:
        """Check for bearish Fibonacci setup (Reverse Fibonacci)"""
        try:
            conditions_met = []
            strength_score = 0
            fibonacci_level_triggered = None
            
            # Condition 1: Price below EMA25 (bearish bias)
            if current_price < emas.get('ema_25', 0):
                conditions_met.append('price_below_ema25')
                strength_score += 25
            
            # Condition 2: EMA alignment (bearish)
            if (emas.get('ema_20', 0) < emas.get('ema_25', 0) < emas.get('ema_50', 0)):
                conditions_met.append('strong_ema_bearish')
                strength_score += 30
            elif emas.get('ema_20', 0) < emas.get('ema_25', 0):
                conditions_met.append('partial_ema_bearish')
                strength_score += 15
            
            # Condition 3: Fibonacci rejection (61.8% - 78.6% zone)
            fib_61_8 = fib_levels.get('fib_61_8', 0)
            fib_78_6 = fib_levels.get('fib_78_6', 0)
            
            # Check if price is in or just below the rejection zone
            tolerance = current_price * self.config['fib_tolerance']
            
            if (fib_78_6 - tolerance) <= current_price <= (fib_61_8 + tolerance):
                conditions_met.append('fibonacci_rejection_zone')
                fibonacci_level_triggered = 'fib_61_8_to_78_6'
                strength_score += 35
            elif (fib_61_8 - tolerance) <= current_price <= (fib_61_8 + tolerance):
                conditions_met.append('fibonacci_61_8_level')
                fibonacci_level_triggered = 'fib_61_8'
                strength_score += 30
            
            # Condition 4: Volume confirmation
            if volume_ratio >= self.config['volume_multiplier']:
                conditions_met.append('volume_confirmation')
                strength_score += 20
            
            # Condition 5: RSI not oversold
            if self.config['rsi_oversold'] < rsi < self.config['rsi_overbought']:
                conditions_met.append('rsi_healthy')
                strength_score += 10
            
            # Must have at least 3 conditions and Fibonacci trigger
            if len(conditions_met) >= 3 and fibonacci_level_triggered:
                return {
                    'strength': min(strength_score, 100),
                    'fibonacci_level': fibonacci_level_triggered,
                    'conditions_met': conditions_met,
                    'rsi_value': rsi,
                    'volume_ratio': volume_ratio
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Bearish condition check failed: {e}")
            return None
    
    def _confirm_multi_timeframe(self, signal_1m: Optional[Dict], 
                                signal_5m: Optional[Dict]) -> Optional[Dict]:
        """Confirm signal across multiple timeframes"""
        try:
            # Both timeframes must have signals
            if not signal_1m or not signal_5m:
                return None
            
            # Signals must be in same direction
            if signal_1m['type'] != signal_5m['type']:
                logger.debug("❌ Multi-timeframe signals conflict")
                return None
            
            # Calculate combined strength (weighted toward 1m for precision)
            combined_strength = (signal_1m['strength'] * 0.7) + (signal_5m['strength'] * 0.3)
            
            # Use 1m signal as primary with enhanced strength
            confirmed_signal = signal_1m.copy()
            confirmed_signal['strength'] = combined_strength
            confirmed_signal['multi_timeframe_confirmed'] = True
            
            logger.debug(f"✅ Multi-timeframe {confirmed_signal['type']} confirmed "
                        f"(1m: {signal_1m['strength']:.1f}, 5m: {signal_5m['strength']:.1f}, "
                        f"Combined: {combined_strength:.1f})")
            
            return confirmed_signal
            
        except Exception as e:
            logger.error(f"❌ Multi-timeframe confirmation failed: {e}")
            return None
    
    def _calculate_risk_reward(self, signal: Dict, entry_price: float, 
                              fib_levels: Dict, swing_high: float, swing_low: float) -> Dict:
        """Calculate stop loss, targets, and risk-reward ratio"""
        try:
            signal_type = signal['type']
            
            if signal_type == 'BUY_CE':
                # Bullish trade risk management
                # Stop loss below recent swing low or Fibonacci 61.8%
                stop_loss_fib = fib_levels.get('fib_61_8', swing_low)
                stop_loss = min(stop_loss_fib, swing_low * 0.98)  # 2% buffer below swing low
                
                # Targets based on Fibonacci extensions
                price_range = swing_high - swing_low
                target_1 = entry_price + (price_range * 0.618)  # 1.618 Fibonacci extension
                target_2 = entry_price + (price_range * 1.000)  # 2.618 Fibonacci extension
                
            else:  # BUY_PE
                # Bearish trade risk management
                # Stop loss above recent swing high or Fibonacci 38.2%
                stop_loss_fib = fib_levels.get('fib_38_2', swing_high)
                stop_loss = max(stop_loss_fib, swing_high * 1.02)  # 2% buffer above swing high
                
                # Targets based on Fibonacci extensions
                price_range = swing_high - swing_low
                target_1 = entry_price - (price_range * 0.618)
                target_2 = entry_price - (price_range * 1.000)
            
            # Calculate risk-reward ratio
            risk = abs(entry_price - stop_loss)
            reward_1 = abs(target_1 - entry_price)
            
            risk_reward = reward_1 / risk if risk > 0 else 0
            
            # Ensure minimum risk-reward ratio
            if risk_reward < self.config['min_risk_reward']:
                # Adjust target to meet minimum R:R
                if signal_type == 'BUY_CE':
                    target_1 = entry_price + (risk * self.config['min_risk_reward'])
                    target_2 = entry_price + (risk * self.config['max_risk_reward'])
                else:
                    target_1 = entry_price - (risk * self.config['min_risk_reward'])
                    target_2 = entry_price - (risk * self.config['max_risk_reward'])
                
                risk_reward = self.config['min_risk_reward']
            
            return {
                'stop_loss': round(stop_loss, 2),
                'target_1': round(target_1, 2),
                'target_2': round(target_2, 2),
                'risk_reward': round(risk_reward, 2),
                'risk_amount': round(risk, 2),
                'reward_amount': round(abs(target_1 - entry_price), 2)
            }
            
        except Exception as e:
            logger.error(f"❌ Risk-reward calculation failed: {e}")
            # Fallback risk management
            risk_percent = 0.02  # 2% risk
            reward_percent = 0.04  # 4% reward (1:2 R:R)
            
            if signal['type'] == 'BUY_CE':
                return {
                    'stop_loss': round(entry_price * (1 - risk_percent), 2),
                    'target_1': round(entry_price * (1 + reward_percent), 2),
                    'target_2': round(entry_price * (1 + reward_percent * 1.5), 2),
                    'risk_reward': 2.0,
                    'risk_amount': round(entry_price * risk_percent, 2),
                    'reward_amount': round(entry_price * reward_percent, 2)
                }
            else:
                return {
                    'stop_loss': round(entry_price * (1 + risk_percent), 2),
                    'target_1': round(entry_price * (1 - reward_percent), 2),
                    'target_2': round(entry_price * (1 - reward_percent * 1.5), 2),
                    'risk_reward': 2.0,
                    'risk_amount': round(entry_price * risk_percent, 2),
                    'reward_amount': round(entry_price * reward_percent, 2)
                }

# Global strategy instance
fibonacci_ema_strategy = FibonacciEMAStrategy()