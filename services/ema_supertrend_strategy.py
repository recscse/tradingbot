"""
EMA + SuperTrend Strategy Service
Accurate implementation for options trading with live market data integration
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from decimal import Decimal
import asyncio
import time

from services.indicators import ema, atr

logger = logging.getLogger(__name__)


@dataclass
class TradingSignal:
    """EMA + SuperTrend trading signal with risk management"""
    signal_type: str  # 'BUY_CE', 'BUY_PE', 'HOLD', 'EXIT'
    strength: float  # 0-100 signal strength
    entry_price: Decimal
    stop_loss: Decimal
    target_1: Decimal
    target_2: Decimal
    risk_reward_ratio: float

    # Technical analysis details
    ema_value: Decimal
    supertrend_value: Decimal
    supertrend_direction: str  # 'UP' or 'DOWN'
    trailing_sl_value: Decimal

    # Signal metadata
    timestamp: datetime
    processing_time_ms: float
    underlying_symbol: str
    current_trend: str  # 'BULLISH', 'BEARISH', 'SIDEWAYS'

    # Position management
    position_size_multiplier: float = 1.0
    confidence_level: float = 0.0  # 0-1 confidence in signal
    market_conditions: str = "NORMAL"  # NORMAL, VOLATILE, TRENDING

    # Options specific
    suggested_strike: Optional[Decimal] = None
    suggested_expiry: Optional[str] = None
    option_type: str = "CE"  # CE or PE


@dataclass
class OHLCData:
    """OHLC data structure for strategy calculations"""
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for pandas operations"""
        return {
            'timestamp': self.timestamp,
            'open': float(self.open),
            'high': float(self.high),
            'low': float(self.low),
            'close': float(self.close),
            'volume': self.volume
        }


class EMASuperTrendStrategy:
    """
    EMA + SuperTrend Strategy Implementation

    Strategy Logic:
    - BUY CE: Price above EMA AND SuperTrend direction changes to UP
    - BUY PE: Price below EMA AND SuperTrend direction changes to DOWN
    - EXIT: Price hits SuperTrend trailing stop (multiplier 1.0)

    Technical Parameters:
    - EMA Period: 20 (configurable)
    - SuperTrend Period: 10 (configurable)
    - SuperTrend Multiplier 1: 2.0 (for trend detection)
    - SuperTrend Multiplier 2: 1.0 (for trailing stop loss)
    """

    def __init__(self,
                 ema_period: int = 20,
                 supertrend_period: int = 10,
                 trend_multiplier: float = 2.0,
                 trailing_multiplier: float = 1.0):

        self.ema_period = ema_period
        self.supertrend_period = supertrend_period
        self.trend_multiplier = trend_multiplier  # For signal generation
        self.trailing_multiplier = trailing_multiplier  # For stop loss

        # Data storage for calculations
        self.ohlc_data: Dict[str, List[OHLCData]] = {}
        self.indicators_cache: Dict[str, Dict] = {}

        # Strategy configuration
        self.config = {
            'min_data_points': max(ema_period, supertrend_period) + 5,
            'max_data_points': 200,  # Keep last 200 candles
            'signal_strength_threshold': 70,
            'risk_reward_min': 1.5,
            'risk_reward_target': 2.0,
            'confidence_threshold': 0.6,
        }

        logger.info(f"EMA + SuperTrend Strategy initialized - "
                   f"EMA: {ema_period}, SuperTrend: {supertrend_period}, "
                   f"Multipliers: {trend_multiplier}x (trend), {trailing_multiplier}x (SL)")

    def add_market_data(self, symbol: str, market_data: Dict[str, Any]) -> None:
        """
        Add live market data for strategy calculation

        Args:
            symbol: Trading symbol
            market_data: Normalized market data from live feed
        """
        try:
            # Extract OHLC data from normalized feed
            ohlc = self._extract_ohlc_from_feed(market_data)
            if not ohlc:
                return

            # Initialize symbol data if not exists
            if symbol not in self.ohlc_data:
                self.ohlc_data[symbol] = []
                self.indicators_cache[symbol] = {}

            # Add new data point
            self.ohlc_data[symbol].append(ohlc)

            # Maintain data size limit
            if len(self.ohlc_data[symbol]) > self.config['max_data_points']:
                self.ohlc_data[symbol] = self.ohlc_data[symbol][-self.config['max_data_points']:]

            # Update indicators cache
            if len(self.ohlc_data[symbol]) >= self.config['min_data_points']:
                self._calculate_indicators(symbol)

        except Exception as e:
            logger.error(f"Error adding market data for {symbol}: {e}")

    def _extract_ohlc_from_feed(self, market_data: Dict[str, Any]) -> Optional[OHLCData]:
        """Extract OHLC data from live feed format"""
        try:
            # Handle different data formats from live feed
            if 'ltp' in market_data:
                # Use LTP as current close price
                close_price = Decimal(str(market_data['ltp']))

                # Extract OHLC if available, otherwise use LTP
                ohlc = OHLCData(
                    timestamp=datetime.now(),
                    open=Decimal(str(market_data.get('open', close_price))),
                    high=Decimal(str(market_data.get('high', close_price))),
                    low=Decimal(str(market_data.get('low', close_price))),
                    close=close_price,
                    volume=int(market_data.get('volume', 0))
                )
                return ohlc

            elif 'close' in market_data:
                # Standard OHLC format
                return OHLCData(
                    timestamp=datetime.now(),
                    open=Decimal(str(market_data['open'])),
                    high=Decimal(str(market_data['high'])),
                    low=Decimal(str(market_data['low'])),
                    close=Decimal(str(market_data['close'])),
                    volume=int(market_data.get('volume', 0))
                )

            return None

        except Exception as e:
            logger.error(f"Error extracting OHLC from feed: {e}")
            return None

    def _calculate_indicators(self, symbol: str) -> None:
        """Calculate EMA and SuperTrend indicators"""
        try:
            if symbol not in self.ohlc_data or not self.ohlc_data[symbol]:
                return

            # Convert to pandas DataFrame for calculation
            data_list = [ohlc.to_dict() for ohlc in self.ohlc_data[symbol]]
            df = pd.DataFrame(data_list)

            if len(df) < self.config['min_data_points']:
                return

            # Calculate EMA
            df['ema'] = ema(df['close'], self.ema_period)

            # Calculate SuperTrend for trend detection (multiplier 2.0)
            supertrend_trend = self._calculate_supertrend(
                df, self.supertrend_period, self.trend_multiplier
            )
            df['supertrend_trend'] = supertrend_trend['values']
            df['supertrend_direction'] = supertrend_trend['direction']

            # Calculate SuperTrend for trailing stop loss (multiplier 1.0)
            supertrend_sl = self._calculate_supertrend(
                df, self.supertrend_period, self.trailing_multiplier
            )
            df['supertrend_sl'] = supertrend_sl['values']
            df['supertrend_sl_direction'] = supertrend_sl['direction']

            # Update cache
            self.indicators_cache[symbol] = {
                'dataframe': df,
                'last_update': datetime.now(),
                'data_points': len(df)
            }

            logger.debug(f"Updated indicators for {symbol} - {len(df)} data points")

        except Exception as e:
            logger.error(f"Error calculating indicators for {symbol}: {e}")

    def _calculate_supertrend(self, df: pd.DataFrame, period: int, multiplier: float) -> Dict:
        """
        Calculate SuperTrend indicator with proper implementation

        Args:
            df: OHLC DataFrame
            period: ATR period
            multiplier: SuperTrend multiplier

        Returns:
            Dict with 'values' and 'direction' lists
        """
        try:
            if len(df) < period:
                return {
                    'values': [None] * len(df),
                    'direction': [None] * len(df)
                }

            # Calculate ATR using the indicators module
            df_copy = df.copy()
            atr_values = []

            # Manual ATR calculation for SuperTrend
            for i in range(len(df)):
                if i == 0:
                    atr_values.append(df.iloc[i]['high'] - df.iloc[i]['low'])
                else:
                    tr1 = df.iloc[i]['high'] - df.iloc[i]['low']
                    tr2 = abs(df.iloc[i]['high'] - df.iloc[i-1]['close'])
                    tr3 = abs(df.iloc[i]['low'] - df.iloc[i-1]['close'])
                    true_range = max(tr1, tr2, tr3)

                    if i < period:
                        atr_values.append(sum(atr_values) / len(atr_values))
                    else:
                        # Exponential moving average of true range
                        alpha = 2.0 / (period + 1)
                        atr_values.append(alpha * true_range + (1 - alpha) * atr_values[-1])

            # Calculate SuperTrend
            supertrend_values = []
            directions = []

            for i in range(len(df)):
                if i < period:
                    supertrend_values.append(None)
                    directions.append(None)
                    continue

                # Basic bands
                hl2 = (df.iloc[i]['high'] + df.iloc[i]['low']) / 2
                upper_band = hl2 + multiplier * atr_values[i]
                lower_band = hl2 - multiplier * atr_values[i]

                if i == period:
                    # Initialize first SuperTrend value
                    if df.iloc[i]['close'] <= upper_band:
                        supertrend_values.append(upper_band)
                        directions.append('DOWN')
                    else:
                        supertrend_values.append(lower_band)
                        directions.append('UP')
                else:
                    # Calculate subsequent values
                    prev_supertrend = supertrend_values[-1]
                    prev_direction = directions[-1]

                    if prev_direction == 'UP':
                        current_supertrend = max(lower_band, prev_supertrend)
                        if df.iloc[i]['close'] > current_supertrend:
                            current_direction = 'UP'
                        else:
                            current_direction = 'DOWN'
                            current_supertrend = upper_band
                    else:  # DOWN
                        current_supertrend = min(upper_band, prev_supertrend)
                        if df.iloc[i]['close'] < current_supertrend:
                            current_direction = 'DOWN'
                        else:
                            current_direction = 'UP'
                            current_supertrend = lower_band

                    supertrend_values.append(current_supertrend)
                    directions.append(current_direction)

            return {
                'values': supertrend_values,
                'direction': directions
            }

        except Exception as e:
            logger.error(f"SuperTrend calculation error: {e}")
            return {
                'values': [None] * len(df),
                'direction': [None] * len(df)
            }

    def generate_signal(self, symbol: str) -> Optional[TradingSignal]:
        """
        Generate trading signal based on EMA + SuperTrend strategy

        Args:
            symbol: Trading symbol to analyze

        Returns:
            TradingSignal or None if no valid signal
        """
        start_time = time.time()

        try:
            # Check if we have sufficient data
            if symbol not in self.indicators_cache:
                return None

            cache = self.indicators_cache[symbol]
            df = cache['dataframe']

            if len(df) < self.config['min_data_points']:
                return None

            # Get current and previous values
            current_idx = len(df) - 1
            prev_idx = current_idx - 1

            if prev_idx < 0:
                return None

            # Extract current values
            current_price = Decimal(str(df.iloc[current_idx]['close']))
            current_ema = Decimal(str(df.iloc[current_idx]['ema']))
            current_supertrend = Decimal(str(df.iloc[current_idx]['supertrend_trend']))
            current_direction = df.iloc[current_idx]['supertrend_direction']
            trailing_sl = Decimal(str(df.iloc[current_idx]['supertrend_sl']))

            # Extract previous values for trend change detection
            prev_direction = df.iloc[prev_idx]['supertrend_direction']

            # Check for valid values
            if (pd.isna(current_ema) or pd.isna(current_supertrend) or
                current_direction is None or prev_direction is None):
                return None

            # Signal generation logic
            signal_type = "HOLD"
            signal_strength = 0

            # BUY CE Condition: Price above EMA AND SuperTrend turns UP
            if (current_price > current_ema and
                current_direction == 'UP' and
                prev_direction == 'DOWN'):

                signal_type = "BUY_CE"
                signal_strength = self._calculate_signal_strength(
                    df, current_idx, 'BULLISH'
                )

            # BUY PE Condition: Price below EMA AND SuperTrend turns DOWN
            elif (current_price < current_ema and
                  current_direction == 'DOWN' and
                  prev_direction == 'UP'):

                signal_type = "BUY_PE"
                signal_strength = self._calculate_signal_strength(
                    df, current_idx, 'BEARISH'
                )

            # Only generate signal if strength is above threshold
            if signal_strength < self.config['signal_strength_threshold']:
                return None

            # Calculate risk-reward metrics
            risk_reward_data = self._calculate_risk_reward(
                signal_type, current_price, current_supertrend, trailing_sl, df
            )

            # Create trading signal
            processing_time = (time.time() - start_time) * 1000

            signal = TradingSignal(
                signal_type=signal_type,
                strength=signal_strength,
                entry_price=current_price,
                stop_loss=risk_reward_data['stop_loss'],
                target_1=risk_reward_data['target_1'],
                target_2=risk_reward_data['target_2'],
                risk_reward_ratio=risk_reward_data['risk_reward'],
                ema_value=current_ema,
                supertrend_value=current_supertrend,
                supertrend_direction=current_direction,
                trailing_sl_value=trailing_sl,
                timestamp=datetime.now(),
                processing_time_ms=processing_time,
                underlying_symbol=symbol,
                current_trend=self._determine_trend(df, current_idx),
                confidence_level=signal_strength / 100.0,
                option_type='CE' if signal_type == 'BUY_CE' else 'PE'
            )

            logger.info(f"Generated {signal_type} signal for {symbol} "
                       f"(Strength: {signal_strength:.1f}, R:R: {risk_reward_data['risk_reward']:.2f})")

            return signal

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"Signal generation failed for {symbol}: {e} (took {processing_time:.2f}ms)")
            return None

    def _calculate_signal_strength(self, df: pd.DataFrame, current_idx: int, trend_type: str) -> float:
        """Calculate signal strength based on multiple factors"""
        try:
            strength = 0.0

            # Factor 1: EMA alignment (30 points)
            current_price = df.iloc[current_idx]['close']
            current_ema = df.iloc[current_idx]['ema']

            if trend_type == 'BULLISH' and current_price > current_ema:
                ema_distance = (current_price - current_ema) / current_ema
                strength += min(30, ema_distance * 1000)  # Scale factor
            elif trend_type == 'BEARISH' and current_price < current_ema:
                ema_distance = (current_ema - current_price) / current_ema
                strength += min(30, ema_distance * 1000)

            # Factor 2: SuperTrend confirmation (40 points)
            current_direction = df.iloc[current_idx]['supertrend_direction']
            if ((trend_type == 'BULLISH' and current_direction == 'UP') or
                (trend_type == 'BEARISH' and current_direction == 'DOWN')):
                strength += 40

            # Factor 3: Volume confirmation (20 points)
            if current_idx >= 5:
                current_volume = df.iloc[current_idx]['volume']
                avg_volume = df.iloc[current_idx-5:current_idx]['volume'].mean()
                if current_volume > avg_volume * 1.2:
                    strength += 20

            # Factor 4: Price momentum (10 points)
            if current_idx >= 3:
                price_change = ((current_price - df.iloc[current_idx-3]['close']) /
                              df.iloc[current_idx-3]['close'])
                if ((trend_type == 'BULLISH' and price_change > 0) or
                    (trend_type == 'BEARISH' and price_change < 0)):
                    strength += min(10, abs(price_change) * 500)

            return min(100.0, strength)

        except Exception as e:
            logger.error(f"Error calculating signal strength: {e}")
            return 0.0

    def _calculate_risk_reward(self, signal_type: str, entry_price: Decimal,
                              supertrend: Decimal, trailing_sl: Decimal,
                              df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate stop loss and targets with risk-reward ratio"""
        try:
            if signal_type == "BUY_CE":
                # Bullish trade - use trailing SuperTrend as stop loss
                stop_loss = trailing_sl

                # Calculate targets based on recent volatility
                price_range = self._calculate_recent_range(df, 20)
                target_1 = entry_price + (price_range * Decimal('0.618'))
                target_2 = entry_price + (price_range * Decimal('1.0'))

            else:  # BUY_PE
                # Bearish trade
                stop_loss = trailing_sl

                price_range = self._calculate_recent_range(df, 20)
                target_1 = entry_price - (price_range * Decimal('0.618'))
                target_2 = entry_price - (price_range * Decimal('1.0'))

            # Calculate risk-reward ratio
            risk = abs(entry_price - stop_loss)
            reward = abs(target_1 - entry_price)

            risk_reward_ratio = float(reward / risk) if risk > 0 else 0.0

            # Ensure minimum risk-reward ratio
            if risk_reward_ratio < self.config['risk_reward_min']:
                adjustment_factor = Decimal(str(self.config['risk_reward_min']))
                if signal_type == "BUY_CE":
                    target_1 = entry_price + (risk * adjustment_factor)
                    target_2 = entry_price + (risk * Decimal(str(self.config['risk_reward_target'])))
                else:
                    target_1 = entry_price - (risk * adjustment_factor)
                    target_2 = entry_price - (risk * Decimal(str(self.config['risk_reward_target'])))

                risk_reward_ratio = self.config['risk_reward_min']

            return {
                'stop_loss': stop_loss,
                'target_1': target_1,
                'target_2': target_2,
                'risk_reward': risk_reward_ratio,
                'risk_amount': risk,
                'reward_amount': abs(target_1 - entry_price)
            }

        except Exception as e:
            logger.error(f"Risk-reward calculation error: {e}")
            # Fallback to percentage-based calculation
            risk_pct = Decimal('0.02')  # 2%
            reward_pct = Decimal('0.04')  # 4%

            if signal_type == "BUY_CE":
                return {
                    'stop_loss': entry_price * (Decimal('1') - risk_pct),
                    'target_1': entry_price * (Decimal('1') + reward_pct),
                    'target_2': entry_price * (Decimal('1') + reward_pct * Decimal('1.5')),
                    'risk_reward': 2.0,
                    'risk_amount': entry_price * risk_pct,
                    'reward_amount': entry_price * reward_pct
                }
            else:
                return {
                    'stop_loss': entry_price * (Decimal('1') + risk_pct),
                    'target_1': entry_price * (Decimal('1') - reward_pct),
                    'target_2': entry_price * (Decimal('1') - reward_pct * Decimal('1.5')),
                    'risk_reward': 2.0,
                    'risk_amount': entry_price * risk_pct,
                    'reward_amount': entry_price * reward_pct
                }

    def _calculate_recent_range(self, df: pd.DataFrame, periods: int) -> Decimal:
        """Calculate recent price range for target setting"""
        try:
            end_idx = len(df) - 1
            start_idx = max(0, end_idx - periods)

            recent_data = df.iloc[start_idx:end_idx + 1]
            high = recent_data['high'].max()
            low = recent_data['low'].min()

            return Decimal(str(high - low))

        except Exception as e:
            logger.error(f"Error calculating recent range: {e}")
            return Decimal('50.0')  # Fallback value

    def _determine_trend(self, df: pd.DataFrame, current_idx: int) -> str:
        """Determine overall market trend"""
        try:
            if current_idx < 10:
                return "SIDEWAYS"

            # Look at last 10 periods for trend determination
            recent_closes = df.iloc[current_idx-10:current_idx+1]['close'].values
            recent_ema = df.iloc[current_idx-10:current_idx+1]['ema'].values

            # Count bullish vs bearish periods
            bullish_count = sum(1 for i in range(len(recent_closes))
                               if recent_closes[i] > recent_ema[i])

            if bullish_count >= 7:
                return "BULLISH"
            elif bullish_count <= 3:
                return "BEARISH"
            else:
                return "SIDEWAYS"

        except Exception as e:
            logger.error(f"Error determining trend: {e}")
            return "SIDEWAYS"

    def check_exit_conditions(self, symbol: str, position_type: str,
                             entry_price: Decimal) -> Optional[TradingSignal]:
        """
        Check if exit conditions are met for existing position

        Args:
            symbol: Trading symbol
            position_type: 'BUY_CE' or 'BUY_PE'
            entry_price: Entry price of position

        Returns:
            EXIT signal if conditions met, None otherwise
        """
        try:
            if symbol not in self.indicators_cache:
                return None

            cache = self.indicators_cache[symbol]
            df = cache['dataframe']

            if len(df) == 0:
                return None

            current_idx = len(df) - 1
            current_price = Decimal(str(df.iloc[current_idx]['close']))
            trailing_sl = Decimal(str(df.iloc[current_idx]['supertrend_sl']))

            should_exit = False

            if position_type == 'BUY_CE':
                # Exit CE if price falls below trailing SuperTrend
                should_exit = current_price <= trailing_sl

            elif position_type == 'BUY_PE':
                # Exit PE if price rises above trailing SuperTrend
                should_exit = current_price >= trailing_sl

            if should_exit:
                return TradingSignal(
                    signal_type='EXIT',
                    strength=100.0,  # Exit signals are always strong
                    entry_price=entry_price,
                    stop_loss=trailing_sl,
                    target_1=current_price,
                    target_2=current_price,
                    risk_reward_ratio=0.0,
                    ema_value=Decimal(str(df.iloc[current_idx]['ema'])),
                    supertrend_value=Decimal(str(df.iloc[current_idx]['supertrend_trend'])),
                    supertrend_direction=df.iloc[current_idx]['supertrend_direction'],
                    trailing_sl_value=trailing_sl,
                    timestamp=datetime.now(),
                    processing_time_ms=0.0,
                    underlying_symbol=symbol,
                    current_trend=self._determine_trend(df, current_idx),
                    option_type='CE' if position_type == 'BUY_CE' else 'PE'
                )

            return None

        except Exception as e:
            logger.error(f"Error checking exit conditions for {symbol}: {e}")
            return None

    def get_current_indicators(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current indicator values for a symbol"""
        try:
            if symbol not in self.indicators_cache:
                return None

            cache = self.indicators_cache[symbol]
            df = cache['dataframe']

            if len(df) == 0:
                return None

            current_idx = len(df) - 1

            return {
                'price': float(df.iloc[current_idx]['close']),
                'ema': float(df.iloc[current_idx]['ema']),
                'supertrend_trend': float(df.iloc[current_idx]['supertrend_trend']),
                'supertrend_direction': df.iloc[current_idx]['supertrend_direction'],
                'supertrend_sl': float(df.iloc[current_idx]['supertrend_sl']),
                'supertrend_sl_direction': df.iloc[current_idx]['supertrend_sl_direction'],
                'volume': int(df.iloc[current_idx]['volume']),
                'data_points': len(df),
                'last_update': cache['last_update'].isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting indicators for {symbol}: {e}")
            return None


# Global strategy instance
ema_supertrend_strategy = EMASuperTrendStrategy()