"""
Trade Preparation Module
Validates and prepares trades for execution with complete risk management
"""

import logging
from decimal import Decimal
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from services.trading_execution.capital_manager import (
    capital_manager,
    TradingMode,
    CapitalAllocation
)
from services.trading_execution.strategy_engine import (
    strategy_engine,
    TradingSignal,
    SignalType,
    TrailingStopType
)

logger = logging.getLogger(__name__)


class TradeStatus(Enum):
    """Trade preparation status"""
    READY = "ready"
    PENDING_SIGNAL = "pending_signal"
    INSUFFICIENT_CAPITAL = "insufficient_capital"
    NO_ACTIVE_BROKER = "no_active_broker"
    INVALID_PARAMS = "invalid_params"
    ERROR = "error"


@dataclass
class PreparedTrade:
    """
    Complete trade preparation with all execution details

    Attributes:
        status: Trade preparation status
        stock_symbol: Stock symbol
        option_instrument_key: Option contract instrument key
        option_type: CE or PE
        strike_price: Option strike price
        expiry_date: Option expiry date
        current_premium: Current option premium
        lot_size: Lot size for the option
        signal: Trading signal from strategy
        capital_allocation: Capital allocation details
        risk_reward_ratio: Risk to reward ratio
        entry_price: Entry price for trade
        stop_loss: Stop loss price
        target_price: Target price
        trailing_stop_config: Trailing stop loss configuration
        position_size_lots: Number of lots to trade
        total_investment: Total capital required
        max_loss_amount: Maximum loss for this trade
        trading_mode: Paper or Live trading
        broker_name: Broker to use for execution
        user_id: User identifier
        prepared_at: Preparation timestamp
        valid_until: Trade validity end time
        metadata: Additional metadata
    """
    status: TradeStatus
    stock_symbol: str
    option_instrument_key: str
    option_type: str
    strike_price: Decimal
    expiry_date: str
    current_premium: Decimal
    lot_size: int
    signal: Optional[Dict[str, Any]]
    capital_allocation: Optional[Dict[str, Any]]
    risk_reward_ratio: Decimal
    entry_price: Decimal
    stop_loss: Decimal
    target_price: Decimal
    trailing_stop_config: Dict[str, Any]
    position_size_lots: int
    total_investment: Decimal
    max_loss_amount: Decimal
    trading_mode: str
    broker_name: Optional[str]
    user_id: int
    prepared_at: str
    valid_until: str
    metadata: Dict[str, Any]


class TradePrepService:
    """
    Trade Preparation Service

    Orchestrates the complete trade preparation process:
    1. Validates user's active broker and capital
    2. Fetches live market data for the option
    3. Runs strategy to generate trading signal
    4. Calculates position size and risk management
    5. Prepares complete trade execution details
    """

    def __init__(self):
        """Initialize trade preparation service"""
        self.signal_validity_minutes = 15  # Signals valid for 15 minutes
        logger.info("Trade Preparation Service initialized")

    async def prepare_trade(
        self,
        user_id: int,
        stock_symbol: str,
        option_instrument_key: str,
        option_type: str,
        strike_price: Decimal,
        expiry_date: str,
        lot_size: int,
        db: Session,
        trading_mode: TradingMode = TradingMode.PAPER,
        use_spot_strategy: bool = True,
        broker_name: Optional[str] = None
    ) -> PreparedTrade:
        """
        Prepare trade with complete validation and risk management

        Args:
            user_id: User identifier
            stock_symbol: Underlying stock symbol
            option_instrument_key: Option contract instrument key
            option_type: "CE" for calls, "PE" for puts
            strike_price: Option strike price
            expiry_date: Option expiry date
            lot_size: Lot size for the option
            db: Database session
            trading_mode: Paper or Live trading mode

        Returns:
            PreparedTrade with complete execution details

        Raises:
            ValueError: If parameters are invalid
        """
        if not user_id or user_id <= 0:
            raise ValueError("Invalid user_id provided")
        if not option_instrument_key:
            raise ValueError("Option instrument key is required")
        if option_type not in ["CE", "PE"]:
            raise ValueError("Option type must be 'CE' or 'PE'")

        try:
            logger.info(f"Preparing trade for user {user_id}: {stock_symbol} {option_type} {strike_price}")

            # Step 1: Validate broker configuration
            broker_config = capital_manager.get_active_broker_config(user_id, db)

            if not broker_config and trading_mode == TradingMode.LIVE:
                logger.warning(f"No active broker for user {user_id}")
                return self._create_error_trade(
                    TradeStatus.NO_ACTIVE_BROKER,
                    user_id, stock_symbol, option_instrument_key,
                    option_type, strike_price, expiry_date, lot_size,
                    trading_mode, "No active broker configuration found"
                )

            broker_name = broker_config.broker_name if broker_config else "Paper Trading"

            # Step 2: Get available capital
            available_capital = capital_manager.get_available_capital(user_id, db, trading_mode)

            if available_capital <= 0:
                logger.warning(f"No available capital for user {user_id}")
                return self._create_error_trade(
                    TradeStatus.INSUFFICIENT_CAPITAL,
                    user_id, stock_symbol, option_instrument_key,
                    option_type, strike_price, expiry_date, lot_size,
                    trading_mode, "Insufficient capital available"
                )

            # Step 3: Fetch current option premium (live market data)
            current_premium = self._get_current_option_premium(
                option_instrument_key, broker_config, trading_mode
            )

            if current_premium <= 0:
                logger.warning(f"Could not fetch premium for {option_instrument_key}")
                current_premium = Decimal('50.0')  # Fallback premium for testing

            # Step 4: Calculate position size based on capital
            capital_allocation = capital_manager.calculate_position_size(
                available_capital,
                current_premium,
                lot_size
            )

            # Step 5: Validate sufficient capital
            capital_validation = capital_manager.validate_capital_availability(
                user_id,
                capital_allocation.allocated_capital,
                db,
                trading_mode
            )

            if not capital_validation.get("valid"):
                logger.warning(f"Insufficient capital: need {capital_allocation.allocated_capital}")
                return self._create_error_trade(
                    TradeStatus.INSUFFICIENT_CAPITAL,
                    user_id, stock_symbol, option_instrument_key,
                    option_type, strike_price, expiry_date, lot_size,
                    trading_mode,
                    f"Insufficient capital. Need: {capital_allocation.allocated_capital}, Available: {available_capital}"
                )

            # Step 6 & 7: Generate trading signal (spot-based or option-based)
            signal = None

            if use_spot_strategy:
                # Use SPOT-based strategy (more accurate signals)
                try:
                    from services.trading_execution.spot_strategy_executor import spot_strategy_executor
                    from services.trading_execution.spot_instrument_mapper import spot_instrument_mapper

                    # Get spot instrument key for this stock
                    spot_instrument_key = spot_instrument_mapper.get_spot_instrument_for_option(
                        option_instrument_key, db
                    )

                    if spot_instrument_key:
                        logger.info(f"Using SPOT strategy for {stock_symbol} (spot key: {spot_instrument_key})")

                        # Generate signal based on SPOT price analysis
                        signal = await spot_strategy_executor.generate_spot_based_signal(
                            spot_instrument_key=spot_instrument_key,
                            access_token=broker_config.access_token,
                            option_type=option_type,
                            interval="1minute"
                        )

                        logger.info(f"SPOT signal: {signal.signal_type.value}, Confidence: {signal.confidence}")
                    else:
                        logger.warning(f"No spot instrument found for {stock_symbol}, falling back to option-based strategy")
                        use_spot_strategy = False  # Fallback

                except Exception as e:
                    logger.error(f"Error in spot strategy: {e}, falling back to option-based strategy")
                    use_spot_strategy = False  # Fallback

            if not use_spot_strategy or signal is None:
                # Fallback: Use option premium-based strategy
                logger.info(f"Using OPTION premium strategy for {stock_symbol}")

                # Fetch historical data for option
                historical_data = self._get_historical_data(
                    stock_symbol, option_instrument_key, broker_config, trading_mode
                )

                # Generate signal from option premium
                signal = strategy_engine.generate_signal(
                    current_premium,
                    historical_data,
                    option_type
                )

            # Check signal validity
            if signal.signal_type == SignalType.HOLD:
                logger.info(f"No clear trading signal for {stock_symbol}")
                return self._create_pending_trade(
                    user_id, stock_symbol, option_instrument_key,
                    option_type, strike_price, expiry_date, lot_size,
                    current_premium, capital_allocation, signal, trading_mode, broker_name
                )

            # Step 8: Calculate risk-reward ratio
            risk = abs(signal.entry_price - signal.stop_loss)
            reward = abs(signal.target_price - signal.entry_price)
            risk_reward_ratio = reward / risk if risk > 0 else Decimal('0')

            # Step 9: Create prepared trade
            prepared_trade = PreparedTrade(
                status=TradeStatus.READY,
                stock_symbol=stock_symbol,
                option_instrument_key=option_instrument_key,
                option_type=option_type,
                strike_price=strike_price,
                expiry_date=expiry_date,
                current_premium=current_premium,
                lot_size=lot_size,
                signal=asdict(signal) if signal else None,
                capital_allocation=asdict(capital_allocation),
                risk_reward_ratio=risk_reward_ratio,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                target_price=signal.target_price,
                trailing_stop_config=signal.trailing_stop_config,
                position_size_lots=capital_allocation.position_size_lots,
                total_investment=capital_allocation.allocated_capital,
                max_loss_amount=capital_allocation.max_loss,
                trading_mode=trading_mode.value,
                broker_name=broker_name,
                user_id=user_id,
                prepared_at=datetime.now().isoformat(),
                valid_until=(datetime.now() + timedelta(minutes=self.signal_validity_minutes)).isoformat(),
                metadata={
                    "signal_confidence": float(signal.confidence),
                    "signal_reason": signal.reason,
                    "capital_utilization_percent": float(capital_allocation.capital_utilization_percent),
                    "risk_per_trade_percent": float(capital_allocation.risk_per_trade_percent)
                }
            )

            logger.info(f"Trade prepared successfully: {stock_symbol} {option_type}")
            logger.info(f"  Entry: {signal.entry_price}, SL: {signal.stop_loss}, Target: {signal.target_price}")
            logger.info(f"  Position: {capital_allocation.position_size_lots} lots, Investment: Rs.{capital_allocation.allocated_capital:,.2f}")

            return prepared_trade

        except Exception as e:
            logger.error(f"Error preparing trade: {e}")
            return self._create_error_trade(
                TradeStatus.ERROR,
                user_id, stock_symbol, option_instrument_key,
                option_type, strike_price, expiry_date, lot_size,
                trading_mode, str(e)
            )

    def _get_current_option_premium(
        self,
        option_instrument_key: str,
        broker_config: Any,
        trading_mode: TradingMode
    ) -> Decimal:
        """
        Fetch current option premium from live market data

        Args:
            option_instrument_key: Option instrument key
            broker_config: Broker configuration
            trading_mode: Trading mode

        Returns:
            Current option premium
        """
        try:
            if trading_mode == TradingMode.PAPER:
                # For paper trading, use mock data or last known price
                logger.info("Paper trading mode: using mock premium")
                return Decimal('50.0')

            # Fetch live premium from market data
            from services.realtime_market_engine import get_market_engine
            engine = get_market_engine()

            if option_instrument_key in engine.instruments:
                instrument = engine.instruments[option_instrument_key]
                premium = Decimal(str(instrument.current_price))
                logger.info(f"Live premium for {option_instrument_key}: Rs.{premium}")
                return premium
            else:
                logger.warning(f"Instrument not found in market engine: {option_instrument_key}")
                return Decimal('50.0')

        except Exception as e:
            logger.error(f"Error fetching option premium: {e}")
            return Decimal('50.0')

    def _get_historical_data(
        self,
        stock_symbol: str,
        option_instrument_key: str,
        broker_config: Any,
        trading_mode: TradingMode
    ) -> Dict[str, List[float]]:
        """
        Fetch historical candle data for strategy calculation

        Args:
            stock_symbol: Stock symbol
            option_instrument_key: Option instrument key
            broker_config: Broker configuration
            trading_mode: Trading mode

        Returns:
            Dict with OHLC data lists
        """
        try:
            # Fetch historical data (mock for now)
            # In production, this should fetch real historical data from broker API

            # Generate mock data for testing
            import numpy as np
            num_candles = 100
            base_price = 50.0

            np.random.seed(42)
            closes = []
            highs = []
            lows = []
            opens = []

            for i in range(num_candles):
                open_price = base_price + np.random.randn() * 2
                high_price = open_price + abs(np.random.randn() * 3)
                low_price = open_price - abs(np.random.randn() * 3)
                close_price = open_price + np.random.randn() * 2

                opens.append(open_price)
                highs.append(high_price)
                lows.append(low_price)
                closes.append(close_price)

                base_price = close_price

            return {
                'open': opens,
                'high': highs,
                'low': lows,
                'close': closes,
                'volume': [100000] * num_candles
            }

        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return {'close': [50.0] * 100}

    def _create_pending_trade(
        self,
        user_id: int,
        stock_symbol: str,
        option_instrument_key: str,
        option_type: str,
        strike_price: Decimal,
        expiry_date: str,
        lot_size: int,
        current_premium: Decimal,
        capital_allocation: CapitalAllocation,
        signal: TradingSignal,
        trading_mode: TradingMode,
        broker_name: str
    ) -> PreparedTrade:
        """Create pending trade when no clear signal"""
        return PreparedTrade(
            status=TradeStatus.PENDING_SIGNAL,
            stock_symbol=stock_symbol,
            option_instrument_key=option_instrument_key,
            option_type=option_type,
            strike_price=strike_price,
            expiry_date=expiry_date,
            current_premium=current_premium,
            lot_size=lot_size,
            signal=asdict(signal),
            capital_allocation=asdict(capital_allocation),
            risk_reward_ratio=Decimal('0'),
            entry_price=current_premium,
            stop_loss=Decimal('0'),
            target_price=Decimal('0'),
            trailing_stop_config={},
            position_size_lots=capital_allocation.position_size_lots,
            total_investment=capital_allocation.allocated_capital,
            max_loss_amount=capital_allocation.max_loss,
            trading_mode=trading_mode.value,
            broker_name=broker_name,
            user_id=user_id,
            prepared_at=datetime.now().isoformat(),
            valid_until=(datetime.now() + timedelta(minutes=self.signal_validity_minutes)).isoformat(),
            metadata={"reason": signal.reason}
        )

    def _create_error_trade(
        self,
        status: TradeStatus,
        user_id: int,
        stock_symbol: str,
        option_instrument_key: str,
        option_type: str,
        strike_price: Decimal,
        expiry_date: str,
        lot_size: int,
        trading_mode: TradingMode,
        error_message: str
    ) -> PreparedTrade:
        """Create error trade response"""
        return PreparedTrade(
            status=status,
            stock_symbol=stock_symbol,
            option_instrument_key=option_instrument_key,
            option_type=option_type,
            strike_price=strike_price,
            expiry_date=expiry_date,
            current_premium=Decimal('0'),
            lot_size=lot_size,
            signal=None,
            capital_allocation=None,
            risk_reward_ratio=Decimal('0'),
            entry_price=Decimal('0'),
            stop_loss=Decimal('0'),
            target_price=Decimal('0'),
            trailing_stop_config={},
            position_size_lots=0,
            total_investment=Decimal('0'),
            max_loss_amount=Decimal('0'),
            trading_mode=trading_mode.value,
            broker_name=None,
            user_id=user_id,
            prepared_at=datetime.now().isoformat(),
            valid_until=datetime.now().isoformat(),
            metadata={"error": error_message}
        )


# Create singleton instance
trade_prep_service = TradePrepService()