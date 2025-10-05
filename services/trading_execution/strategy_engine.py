"""
Strategy Engine - SuperTrend + EMA
Generates entry/exit signals based on technical indicators with live market data
"""

import logging
import numpy as np
import pandas as pd
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Trading signal types"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    EXIT_LONG = "exit_long"
    EXIT_SHORT = "exit_short"


class TrailingStopType(Enum):
    """Trailing stop loss types"""
    SUPERTREND_1X = "supertrend_1x"  # 1x multiplier SuperTrend
    SUPERTREND_2X = "supertrend_2x"  # 2x multiplier SuperTrend
    PERCENTAGE = "percentage"         # Fixed percentage


@dataclass
class TradingSignal:
    """
    Trading signal with entry/exit details

    Attributes:
        signal_type: Type of signal (BUY/SELL/HOLD/EXIT)
        price: Price at which signal generated
        confidence: Signal confidence (0-1)
        reason: Reason for signal generation
        indicators: Indicator values at signal time
        entry_price: Recommended entry price
        stop_loss: Stop loss price
        target_price: Target price
        trailing_stop_config: Trailing stop loss configuration
        timestamp: Signal generation timestamp
    """
    signal_type: SignalType
    price: Decimal
    confidence: Decimal
    reason: str
    indicators: Dict[str, Any]
    entry_price: Decimal
    stop_loss: Decimal
    target_price: Decimal
    trailing_stop_config: Dict[str, Any]
    timestamp: str


class StrategyEngine:
    """
    SuperTrend + EMA Strategy Engine

    Strategy Rules:
    - Entry: Price crosses above SuperTrend AND price > EMA (for longs)
    - Entry: Price crosses below SuperTrend AND price < EMA (for shorts)
    - Exit: SuperTrend reversal OR price crosses EMA (opposite direction)
    - Trailing Stop: Uses SuperTrend levels with 1x or 2x multiplier options
    """

    def __init__(self):
        """Initialize strategy engine with default parameters"""
        # EMA Configuration
        self.ema_period = 20  # 20-period EMA

        # SuperTrend Configuration
        self.supertrend_period = 10  # ATR period
        self.supertrend_multiplier_1x = 3.0  # Standard multiplier
        self.supertrend_multiplier_2x = 6.0  # Conservative multiplier

        # Risk Management
        self.default_risk_reward_ratio = Decimal('2.0')  # 1:2 risk-reward
        self.min_confidence_threshold = Decimal('0.60')  # Minimum 60% confidence

        logger.info("Strategy Engine initialized with SuperTrend + EMA")
        logger.info(f"  EMA Period: {self.ema_period}")
        logger.info(f"  SuperTrend Period: {self.supertrend_period}")
        logger.info(f"  SuperTrend Multipliers: 1x={self.supertrend_multiplier_1x}, 2x={self.supertrend_multiplier_2x}")

    def calculate_ema(self, prices: List[float], period: int) -> np.ndarray:
        """
        Calculate Exponential Moving Average

        Args:
            prices: List of price values
            period: EMA period

        Returns:
            NumPy array of EMA values

        Raises:
            ValueError: If prices list is too short
        """
        if len(prices) < period:
            raise ValueError(f"Insufficient data: need at least {period} prices")

        try:
            prices_series = pd.Series(prices)
            ema = prices_series.ewm(span=period, adjust=False).mean()
            return ema.values

        except Exception as e:
            logger.error(f"Error calculating EMA: {e}")
            raise

    def calculate_atr(
        self,
        high_prices: List[float],
        low_prices: List[float],
        close_prices: List[float],
        period: int
    ) -> np.ndarray:
        """
        Calculate Average True Range (ATR)

        Args:
            high_prices: List of high prices
            low_prices: List of low prices
            close_prices: List of close prices
            period: ATR period

        Returns:
            NumPy array of ATR values

        Raises:
            ValueError: If price lists have different lengths
        """
        if not (len(high_prices) == len(low_prices) == len(close_prices)):
            raise ValueError("Price lists must have same length")

        try:
            df = pd.DataFrame({
                'high': high_prices,
                'low': low_prices,
                'close': close_prices
            })

            # True Range calculation
            df['tr1'] = df['high'] - df['low']
            df['tr2'] = abs(df['high'] - df['close'].shift())
            df['tr3'] = abs(df['low'] - df['close'].shift())
            df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)

            # ATR = Moving average of TR
            atr = df['tr'].rolling(window=period).mean()

            return atr.values

        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            raise

    def calculate_supertrend(
        self,
        high_prices: List[float],
        low_prices: List[float],
        close_prices: List[float],
        period: int = 10,
        multiplier: float = 3.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate SuperTrend indicator

        Args:
            high_prices: List of high prices
            low_prices: List of low prices
            close_prices: List of close prices
            period: ATR period
            multiplier: ATR multiplier

        Returns:
            Tuple of (supertrend_values, trend_direction)
            trend_direction: 1 = uptrend, -1 = downtrend

        Raises:
            ValueError: If parameters are invalid
        """
        if period <= 0 or multiplier <= 0:
            raise ValueError("Period and multiplier must be positive")

        try:
            df = pd.DataFrame({
                'high': high_prices,
                'low': low_prices,
                'close': close_prices
            })

            # Calculate ATR
            atr = self.calculate_atr(high_prices, low_prices, close_prices, period)
            df['atr'] = atr

            # Basic Bands
            df['hl_avg'] = (df['high'] + df['low']) / 2
            df['basic_ub'] = df['hl_avg'] + (multiplier * df['atr'])
            df['basic_lb'] = df['hl_avg'] - (multiplier * df['atr'])

            # Final Bands
            df['final_ub'] = 0.0
            df['final_lb'] = 0.0
            df['supertrend'] = 0.0
            df['trend'] = 1

            for i in range(period, len(df)):
                # Upper Band
                if df['basic_ub'].iloc[i] < df['final_ub'].iloc[i-1] or df['close'].iloc[i-1] > df['final_ub'].iloc[i-1]:
                    df.loc[df.index[i], 'final_ub'] = df['basic_ub'].iloc[i]
                else:
                    df.loc[df.index[i], 'final_ub'] = df['final_ub'].iloc[i-1]

                # Lower Band
                if df['basic_lb'].iloc[i] > df['final_lb'].iloc[i-1] or df['close'].iloc[i-1] < df['final_lb'].iloc[i-1]:
                    df.loc[df.index[i], 'final_lb'] = df['basic_lb'].iloc[i]
                else:
                    df.loc[df.index[i], 'final_lb'] = df['final_lb'].iloc[i-1]

                # SuperTrend
                if df['close'].iloc[i] <= df['final_ub'].iloc[i]:
                    df.loc[df.index[i], 'supertrend'] = df['final_ub'].iloc[i]
                    df.loc[df.index[i], 'trend'] = -1
                else:
                    df.loc[df.index[i], 'supertrend'] = df['final_lb'].iloc[i]
                    df.loc[df.index[i], 'trend'] = 1

            return df['supertrend'].values, df['trend'].values

        except Exception as e:
            logger.error(f"Error calculating SuperTrend: {e}")
            raise

    def generate_signal(
        self,
        current_price: Decimal,
        historical_data: Dict[str, List[float]],
        option_type: str = "CE"
    ) -> TradingSignal:
        """
        Generate trading signal based on SuperTrend + EMA strategy

        Args:
            current_price: Current market price
            historical_data: Dict with 'open', 'high', 'low', 'close', 'volume' lists
            option_type: "CE" for calls, "PE" for puts

        Returns:
            TradingSignal with entry/exit details

        Raises:
            ValueError: If historical_data is insufficient
        """
        if not historical_data or 'close' not in historical_data:
            raise ValueError("Historical data must contain 'close' prices")

        try:
            close_prices = historical_data['close']
            high_prices = historical_data.get('high', close_prices)
            low_prices = historical_data.get('low', close_prices)

            if len(close_prices) < max(self.ema_period, self.supertrend_period) + 10:
                raise ValueError(f"Need at least {max(self.ema_period, self.supertrend_period) + 10} candles")

            # Calculate indicators
            ema = self.calculate_ema(close_prices, self.ema_period)
            supertrend_1x, trend_1x = self.calculate_supertrend(
                high_prices, low_prices, close_prices,
                self.supertrend_period, self.supertrend_multiplier_1x
            )
            supertrend_2x, trend_2x = self.calculate_supertrend(
                high_prices, low_prices, close_prices,
                self.supertrend_period, self.supertrend_multiplier_2x
            )

            # Current values (latest)
            current_ema = Decimal(str(ema[-1]))
            current_supertrend_1x = Decimal(str(supertrend_1x[-1]))
            current_supertrend_2x = Decimal(str(supertrend_2x[-1]))
            current_trend_1x = int(trend_1x[-1])
            current_trend_2x = int(trend_2x[-1])

            # Previous values
            prev_trend_1x = int(trend_1x[-2]) if len(trend_1x) > 1 else current_trend_1x

            # Determine signal type
            signal_type = SignalType.HOLD
            confidence = Decimal('0.5')
            reason = "No clear signal"

            # LONG ENTRY LOGIC (for CE options)
            if option_type == "CE":
                # Uptrend conditions
                price_above_ema = current_price > current_ema
                price_above_supertrend = current_price > current_supertrend_1x
                trend_bullish = current_trend_1x == 1
                trend_reversal_up = prev_trend_1x == -1 and current_trend_1x == 1

                if trend_reversal_up and price_above_ema:
                    signal_type = SignalType.BUY
                    confidence = Decimal('0.85')
                    reason = "SuperTrend reversal to uptrend + Price above EMA"
                elif price_above_supertrend and price_above_ema and trend_bullish:
                    signal_type = SignalType.BUY
                    confidence = Decimal('0.75')
                    reason = "Strong uptrend: Price above SuperTrend and EMA"
                elif not price_above_supertrend or not price_above_ema:
                    signal_type = SignalType.EXIT_LONG
                    confidence = Decimal('0.80')
                    reason = "Exit: Price below SuperTrend or EMA"

            # SHORT ENTRY LOGIC (for PE options)
            else:
                # Downtrend conditions
                price_below_ema = current_price < current_ema
                price_below_supertrend = current_price < current_supertrend_1x
                trend_bearish = current_trend_1x == -1
                trend_reversal_down = prev_trend_1x == 1 and current_trend_1x == -1

                if trend_reversal_down and price_below_ema:
                    signal_type = SignalType.SELL
                    confidence = Decimal('0.85')
                    reason = "SuperTrend reversal to downtrend + Price below EMA"
                elif price_below_supertrend and price_below_ema and trend_bearish:
                    signal_type = SignalType.SELL
                    confidence = Decimal('0.75')
                    reason = "Strong downtrend: Price below SuperTrend and EMA"
                elif not price_below_supertrend or not price_below_ema:
                    signal_type = SignalType.EXIT_SHORT
                    confidence = Decimal('0.80')
                    reason = "Exit: Price above SuperTrend or EMA"

            # Calculate entry, stop loss, and target
            entry_price = current_price

            if option_type == "CE":
                # For calls: SL at SuperTrend 1x, Target based on R:R
                stop_loss = current_supertrend_1x
                risk = abs(entry_price - stop_loss)
                target_price = entry_price + (risk * self.default_risk_reward_ratio)
            else:
                # For puts: SL at SuperTrend 1x, Target based on R:R
                stop_loss = current_supertrend_1x
                risk = abs(entry_price - stop_loss)
                target_price = entry_price - (risk * self.default_risk_reward_ratio)

            # Trailing stop configuration
            trailing_stop_config = {
                "type": TrailingStopType.SUPERTREND_1X.value,
                "supertrend_1x_value": float(current_supertrend_1x),
                "supertrend_2x_value": float(current_supertrend_2x),
                "multiplier_1x": self.supertrend_multiplier_1x,
                "multiplier_2x": self.supertrend_multiplier_2x,
                "trailing_distance_percent": 2.0  # 2% trailing for percentage-based
            }

            # Indicator values
            indicators = {
                "ema": float(current_ema),
                "supertrend_1x": float(current_supertrend_1x),
                "supertrend_2x": float(current_supertrend_2x),
                "trend_1x": current_trend_1x,
                "trend_2x": current_trend_2x,
                "atr": float(supertrend_1x[-1] - supertrend_1x[-2]) if len(supertrend_1x) > 1 else 0.0
            }

            signal = TradingSignal(
                signal_type=signal_type,
                price=current_price,
                confidence=confidence,
                reason=reason,
                indicators=indicators,
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_price=target_price,
                trailing_stop_config=trailing_stop_config,
                timestamp=datetime.now().isoformat()
            )

            logger.info(f"Signal generated: {signal_type.value} at {current_price}")
            logger.info(f"  Confidence: {confidence:.2f}")
            logger.info(f"  Entry: {entry_price}, SL: {stop_loss}, Target: {target_price}")

            return signal

        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            raise

    def update_trailing_stop(
        self,
        current_price: Decimal,
        entry_price: Decimal,
        current_stop_loss: Decimal,
        trailing_type: TrailingStopType,
        supertrend_value: Optional[Decimal] = None,
        position_type: str = "LONG"
    ) -> Decimal:
        """
        Update trailing stop loss based on current price and strategy

        Args:
            current_price: Current market price
            entry_price: Entry price of position
            current_stop_loss: Current stop loss level
            trailing_type: Type of trailing stop
            supertrend_value: Current SuperTrend value (for SuperTrend-based trailing)
            position_type: "LONG" or "SHORT"

        Returns:
            Updated stop loss price

        Raises:
            ValueError: If parameters are invalid
        """
        if current_price <= 0 or entry_price <= 0:
            raise ValueError("Prices must be positive")

        try:
            new_stop_loss = current_stop_loss

            if trailing_type == TrailingStopType.SUPERTREND_1X or trailing_type == TrailingStopType.SUPERTREND_2X:
                # Use SuperTrend as trailing stop
                if supertrend_value:
                    if position_type == "LONG":
                        # Move SL up only (never down)
                        new_stop_loss = max(current_stop_loss, supertrend_value)
                    else:
                        # Move SL down only (never up)
                        new_stop_loss = min(current_stop_loss, supertrend_value)

            elif trailing_type == TrailingStopType.PERCENTAGE:
                # Percentage-based trailing
                trailing_percent = Decimal('0.02')  # 2% trailing

                if position_type == "LONG":
                    # Trail below current price by 2%
                    potential_stop = current_price * (Decimal('1') - trailing_percent)
                    new_stop_loss = max(current_stop_loss, potential_stop)
                else:
                    # Trail above current price by 2%
                    potential_stop = current_price * (Decimal('1') + trailing_percent)
                    new_stop_loss = min(current_stop_loss, potential_stop)

            logger.debug(f"Trailing SL updated: {current_stop_loss} -> {new_stop_loss}")
            return new_stop_loss

        except Exception as e:
            logger.error(f"Error updating trailing stop: {e}")
            return current_stop_loss


# Create singleton instance
strategy_engine = StrategyEngine()