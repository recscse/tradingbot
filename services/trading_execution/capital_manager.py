"""
Trading Capital Manager
Manages capital allocation, validates available funds, and calculates position sizes
"""

import logging
from decimal import Decimal
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session
from database.models import User, BrokerConfig

logger = logging.getLogger(__name__)


class TradingMode(Enum):
    """Trading mode configuration"""
    PAPER = "paper"
    LIVE = "live"


@dataclass
class CapitalAllocation:
    """
    Capital allocation details for a trading position

    Attributes:
        total_capital: Total capital available for trading
        allocated_capital: Capital allocated for this position
        position_size_lots: Number of lots to trade
        position_value: Total value of position (premium × lot_size × lots)
        max_loss: Maximum loss allowed for this position
        margin_required: Margin required (for futures/options)
        capital_utilization_percent: Percentage of total capital used
        risk_per_trade_percent: Risk as percentage of total capital
    """
    total_capital: Decimal
    allocated_capital: Decimal
    position_size_lots: int
    position_value: Decimal
    max_loss: Decimal
    margin_required: Decimal
    capital_utilization_percent: Decimal
    risk_per_trade_percent: Decimal


class TradingCapitalManager:
    """
    Manages trading capital and validates fund availability

    Features:
    - Validates demat account with active access token
    - Checks available capital from broker
    - Calculates position sizes based on risk management
    - Supports both paper trading (virtual capital) and live trading (real capital)
    - Prevents over-allocation of capital
    """

    def __init__(self):
        """Initialize capital manager with configuration"""
        self.paper_trading_capital = Decimal('1000000')  # 10 Lakhs for paper trading
        self.max_capital_per_trade_percent = Decimal('0.20')  # 20% max per trade
        self.max_risk_per_trade_percent = Decimal('0.02')  # 2% max risk per trade
        self.min_capital_buffer = Decimal('0.10')  # Keep 10% buffer

        logger.info("Trading Capital Manager initialized")

    def get_active_broker_config(
        self,
        user_id: int,
        db: Session,
        broker_name: Optional[str] = None
    ) -> Optional[BrokerConfig]:
        """
        Get active broker configuration with valid access token

        Args:
            user_id: User identifier
            db: Database session
            broker_name: Specific broker name (optional)

        Returns:
            Active BrokerConfig or None

        Raises:
            ValueError: If user_id is invalid
        """
        if not user_id or user_id <= 0:
            raise ValueError("Invalid user_id provided")

        try:
            query = db.query(BrokerConfig).filter(
                BrokerConfig.user_id == user_id,
                BrokerConfig.is_active == True,
                BrokerConfig.access_token.isnot(None)
            )

            if broker_name:
                query = query.filter(BrokerConfig.broker_name.ilike(broker_name))

            broker_config = query.first()

            if not broker_config:
                logger.warning(f"No active broker config found for user {user_id}")
                return None

            # Validate token expiry
            from datetime import datetime
            if broker_config.access_token_expiry and broker_config.access_token_expiry < datetime.now():
                logger.warning(f"Broker token expired for user {user_id}")
                return None

            logger.info(f"Active broker found: {broker_config.broker_name} for user {user_id}")
            return broker_config

        except Exception as e:
            logger.error(f"Error getting active broker config: {e}")
            return None

    def get_available_capital(
        self,
        user_id: int,
        db: Session,
        trading_mode: TradingMode = TradingMode.PAPER
    ) -> Decimal:
        """
        Get available capital for trading

        Args:
            user_id: User identifier
            db: Database session
            trading_mode: Paper or Live trading mode

        Returns:
            Available capital amount

        Raises:
            ValueError: If user_id is invalid
        """
        if not user_id or user_id <= 0:
            raise ValueError("Invalid user_id provided")

        try:
            if trading_mode == TradingMode.PAPER:
                # Paper trading uses virtual capital
                logger.info(f"Paper trading capital: Rs.{self.paper_trading_capital:,.2f}")
                return self.paper_trading_capital

            else:
                # Live trading - fetch from broker
                broker_config = self.get_active_broker_config(user_id, db)

                if not broker_config:
                    logger.error(f"No active broker for user {user_id}")
                    return Decimal('0')

                # Get funds from broker API
                available_funds = self._fetch_funds_from_broker(broker_config)

                if available_funds <= 0:
                    logger.warning(f"No available funds for user {user_id}")
                    return Decimal('0')

                logger.info(f"Live trading capital: Rs.{available_funds:,.2f}")
                return available_funds

        except Exception as e:
            logger.error(f"Error getting available capital: {e}")
            return Decimal('0')

    def _fetch_funds_from_broker(self, broker_config: BrokerConfig) -> Decimal:
        """
        Fetch available funds from broker API

        Args:
            broker_config: Broker configuration with access token

        Returns:
            Available funds amount
        """
        try:
            broker_name = broker_config.broker_name.lower()

            if 'upstox' in broker_name:
                from brokers.upstox_broker import UpstoxBroker
                broker = UpstoxBroker(broker_config)
                funds_data = broker.get_funds()

                if funds_data and 'equity' in funds_data:
                    available_margin = funds_data['equity'].get('available_margin', 0)
                    return Decimal(str(available_margin))

            elif 'angel' in broker_name:
                from brokers.angel_one_broker import AngelOneBroker
                broker = AngelOneBroker(broker_config)
                funds_data = broker.get_funds()

                if funds_data and 'availablecash' in funds_data:
                    return Decimal(str(funds_data['availablecash']))

            elif 'dhan' in broker_name:
                from brokers.dhan_broker import DhanBroker
                broker = DhanBroker(broker_config)
                funds_data = broker.get_funds()

                if funds_data and 'availableBalance' in funds_data:
                    return Decimal(str(funds_data['availableBalance']))

            logger.warning(f"Unsupported broker: {broker_name}")
            return Decimal('0')

        except Exception as e:
            logger.error(f"Error fetching funds from broker: {e}")
            return Decimal('0')

    def calculate_position_size(
        self,
        available_capital: Decimal,
        option_premium: Decimal,
        lot_size: int,
        max_loss_percent: Optional[Decimal] = None
    ) -> CapitalAllocation:
        """
        Calculate optimal position size based on capital and risk management

        Args:
            available_capital: Total available capital
            option_premium: Current option premium price
            lot_size: Lot size for the option contract
            max_loss_percent: Maximum loss as percentage of capital (optional)

        Returns:
            CapitalAllocation with position details

        Raises:
            ValueError: If parameters are invalid
        """
        if available_capital <= 0:
            raise ValueError("Available capital must be positive")
        if option_premium <= 0:
            raise ValueError("Option premium must be positive")
        if lot_size <= 0:
            raise ValueError("Lot size must be positive")

        try:
            # Use default max loss if not provided
            if not max_loss_percent:
                max_loss_percent = self.max_risk_per_trade_percent

            # Calculate maximum capital to allocate (20% of total)
            max_allocable_capital = available_capital * self.max_capital_per_trade_percent

            # Calculate maximum loss amount allowed
            max_loss_amount = available_capital * max_loss_percent

            # Position value per lot
            position_value_per_lot = option_premium * Decimal(str(lot_size))

            # Calculate lots based on capital constraint
            max_lots_by_capital = int(max_allocable_capital / position_value_per_lot)

            # Calculate lots based on risk constraint (assuming 100% premium loss as max loss)
            max_lots_by_risk = int(max_loss_amount / position_value_per_lot)

            # Take minimum of both constraints
            recommended_lots = min(max_lots_by_capital, max_lots_by_risk)
            recommended_lots = max(1, recommended_lots)  # At least 1 lot

            # Calculate actual values
            allocated_capital = position_value_per_lot * Decimal(str(recommended_lots))
            position_value = allocated_capital
            max_loss = position_value  # Maximum loss is 100% of premium paid
            margin_required = position_value  # For options, margin = premium paid

            # Calculate percentages
            capital_utilization = (allocated_capital / available_capital) * Decimal('100')
            risk_per_trade = (max_loss / available_capital) * Decimal('100')

            allocation = CapitalAllocation(
                total_capital=available_capital,
                allocated_capital=allocated_capital,
                position_size_lots=recommended_lots,
                position_value=position_value,
                max_loss=max_loss,
                margin_required=margin_required,
                capital_utilization_percent=capital_utilization,
                risk_per_trade_percent=risk_per_trade
            )

            logger.info(f"Position sizing calculated:")
            logger.info(f"  Lots: {recommended_lots}")
            logger.info(f"  Capital allocated: Rs.{allocated_capital:,.2f}")
            logger.info(f"  Capital utilization: {capital_utilization:.2f}%")
            logger.info(f"  Risk per trade: {risk_per_trade:.2f}%")

            return allocation

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            raise

    def validate_capital_availability(
        self,
        user_id: int,
        required_capital: Decimal,
        db: Session,
        trading_mode: TradingMode = TradingMode.PAPER
    ) -> Dict[str, Any]:
        """
        Validate if sufficient capital is available for trade

        Args:
            user_id: User identifier
            required_capital: Capital required for trade
            db: Database session
            trading_mode: Paper or Live trading mode

        Returns:
            Validation result with details

        Raises:
            ValueError: If parameters are invalid
        """
        if not user_id or user_id <= 0:
            raise ValueError("Invalid user_id provided")
        if required_capital <= 0:
            raise ValueError("Required capital must be positive")

        try:
            available_capital = self.get_available_capital(user_id, db, trading_mode)

            # Check if sufficient capital available
            capital_with_buffer = available_capital * (Decimal('1') - self.min_capital_buffer)
            sufficient = required_capital <= capital_with_buffer

            return {
                "valid": sufficient,
                "available_capital": float(available_capital),
                "required_capital": float(required_capital),
                "capital_with_buffer": float(capital_with_buffer),
                "shortfall": float(max(Decimal('0'), required_capital - capital_with_buffer)),
                "buffer_percent": float(self.min_capital_buffer * Decimal('100')),
                "trading_mode": trading_mode.value
            }

        except Exception as e:
            logger.error(f"Error validating capital: {e}")
            return {
                "valid": False,
                "error": str(e)
            }


# Create singleton instance
capital_manager = TradingCapitalManager()