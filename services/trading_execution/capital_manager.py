"""
Trading Capital Manager
Manages capital allocation, validates available funds, and calculates position sizes
"""

import logging
from decimal import Decimal
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
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
        self.paper_trading_capital = Decimal('100000')  # 1 Lakh for paper trading
        self.max_capital_per_trade_percent = Decimal('0.60')  # 60% max per trade
        self.max_risk_per_trade_percent = Decimal('0.02')  # 2% max risk per trade
        self.min_capital_buffer = Decimal('0.10')  # Keep 10% buffer
        self.last_error = None
        self.function_health = {
            "fetch_funds": {"status": "unknown", "last_run": None, "error": None},
            "position_sizing": {"status": "unknown", "last_run": None, "error": None}
        }

        logger.info("Trading Capital Manager initialized")

    def get_status(self) -> Dict[str, Any]:
        """Get status for system health monitoring"""
        status = "healthy"
        if self.last_error:
            status = "warning"
            
        return {
            "status": status,
            "last_error": self.last_error,
            "function_health": self.function_health,
            "timestamp": datetime.now().isoformat()
        }

    def _update_function_health(self, func_name: str, status: str, error: str = None):
        """Update internal function health"""
        self.function_health[func_name] = {
            "status": status,
            "last_run": datetime.now().isoformat(),
            "error": error
        }
        if error:
            self.last_error = f"[{func_name}] {error}"

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
        Get available capital for trading (total capital minus already allocated capital)

        CRITICAL: This method now accounts for capital already allocated to active positions
        to prevent over-allocation when multiple positions are open concurrently.

        Args:
            user_id: User identifier
            db: Database session
            trading_mode: Paper or Live trading mode

        Returns:
            Available capital amount (after deducting allocated capital)

        Raises:
            ValueError: If user_id is invalid
        """
        if not user_id or user_id <= 0:
            raise ValueError("Invalid user_id provided")

        try:
            # Get total capital (from broker or paper trading)
            if trading_mode == TradingMode.PAPER:
                # Dynamic paper trading capital
                # Note: This is a synchronous method, but we need to access async paper service
                # Using a safe way to run async code synchronously or better yet, accessing via database if possible
                # For now, let's try to get the account from the service if initialized, or fall back to static
                
                from services.paper_trading_account import paper_trading_service
                
                # Try to access the in-memory account synchronously if possible
                # Since paper_trading_service.accounts is a simple dict, we can access it directly
                account = paper_trading_service.accounts.get(user_id)
                
                if account:
                    # Logic from paper_trading_account.close_position:
                    # available_margin += exit_value
                    # used_margin -= invested
                    # So current_balance (cash) + used_margin = Total Equity
                    # Or available_margin + used_margin = Total Equity
                    
                    # paper_trading_service.py: 
                    # account.available_margin = initial - used + pnl
                    # account.used_margin = used
                    # Total = available + used
                    
                    total_capital = Decimal(str(account.available_margin)) + Decimal(str(account.used_margin))
                else:
                    total_capital = self.paper_trading_capital
            else:
                # Live trading - fetch from broker
                broker_config = self.get_active_broker_config(user_id, db)

                if not broker_config:
                    logger.error(f"No active broker for user {user_id}")
                    return Decimal('0')

                # Get funds from broker API
                total_capital = self._fetch_funds_from_broker(broker_config)

                if total_capital <= 0:
                    logger.warning(f"No available funds for user {user_id}")
                    return Decimal('0')

            # Calculate capital already allocated to active positions
            allocated_capital = self._get_allocated_capital_for_active_positions(user_id, db)

            # Available capital = Total capital - Allocated capital
            available_capital = total_capital - allocated_capital

            logger.info(
                f"User {user_id} capital: Total={total_capital:,.2f}, "
                f"Allocated={allocated_capital:,.2f}, Available={available_capital:,.2f}"
            )

            return max(Decimal('0'), available_capital)

        except Exception as e:
            logger.error(f"Error getting available capital: {e}")
            return Decimal('0')

    def get_available_capital_for_new_position(
        self,
        user_id: int,
        db: Session,
        trading_mode: TradingMode = TradingMode.PAPER
    ) -> Decimal:
        """
        Get capital available for opening a NEW position based on position limits

        IMPROVED LOGIC: Instead of deducting from total capital pool, this method:
        1. Checks if max concurrent positions limit is reached
        2. Returns per-trade max allocation if limit not reached
        3. Returns 0 if max positions already open

        This prevents capital exhaustion issues where multiple positions block new trades.

        Args:
            user_id: User identifier
            db: Database session
            trading_mode: Paper or Live trading mode

        Returns:
            Per-trade capital allocation if positions available, else 0

        Raises:
            ValueError: If user_id is invalid
        """
        if not user_id or user_id <= 0:
            raise ValueError("Invalid user_id provided")

        try:
            # Get total capital
            if trading_mode == TradingMode.PAPER:
                from services.paper_trading_account import paper_trading_service
                account = paper_trading_service.accounts.get(user_id)
                if account:
                    total_capital = Decimal(str(account.available_margin)) + Decimal(str(account.used_margin))
                else:
                    total_capital = self.paper_trading_capital
            else:
                broker_config = self.get_active_broker_config(user_id, db)
                if not broker_config:
                    logger.error(f"No active broker for user {user_id}")
                    return Decimal('0')
                total_capital = self._fetch_funds_from_broker(broker_config)
                if total_capital <= 0:
                    return Decimal('0')

            # Calculate per-trade max allocation (60% of total capital)
            max_per_trade = total_capital * self.max_capital_per_trade_percent

            # Check concurrent position limit
            from database.models import ActivePosition

            active_positions_count = db.query(ActivePosition).filter(
                ActivePosition.user_id == user_id,
                ActivePosition.is_active == True
            ).count()

            MAX_CONCURRENT_POSITIONS = 5

            if active_positions_count >= MAX_CONCURRENT_POSITIONS:
                logger.warning(
                    f"User {user_id} reached max concurrent positions "
                    f"({active_positions_count}/{MAX_CONCURRENT_POSITIONS})"
                )
                return Decimal('0')

            logger.info(
                f"User {user_id} - Capital available for new position: "
                f"Rs.{max_per_trade:,.2f} "
                f"({active_positions_count}/{MAX_CONCURRENT_POSITIONS} positions active)"
            )

            return max_per_trade

        except Exception as e:
            logger.error(f"Error getting capital for new position: {e}")
            return Decimal('0')

    def _get_allocated_capital_for_active_positions(
        self,
        user_id: int,
        db: Session
    ) -> Decimal:
        """
        Calculate total capital allocated to user's active positions

        Args:
            user_id: User identifier
            db: Database session

        Returns:
            Total allocated capital amount
        """
        try:
            from database.models import AutoTradeExecution

            # Get all active trades for this user
            active_trades = db.query(AutoTradeExecution).filter(
                AutoTradeExecution.user_id == user_id,
                AutoTradeExecution.status == "ACTIVE"
            ).all()

            total_allocated = Decimal('0')

            for trade in active_trades:
                if trade.allocated_capital:
                    total_allocated += Decimal(str(trade.allocated_capital))
                else:
                    # Fallback: calculate from entry_price * quantity
                    entry_value = Decimal(str(trade.entry_price)) * Decimal(str(trade.quantity))
                    total_allocated += entry_value

            logger.debug(f"User {user_id} has {len(active_trades)} active positions with total allocated capital: Rs.{total_allocated:,.2f}")

            return total_allocated

        except Exception as e:
            logger.error(f"Error calculating allocated capital: {e}")
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
        max_loss_percent: Optional[Decimal] = None,
        max_lots: Optional[int] = None
    ) -> CapitalAllocation:
        """
        Calculate optimal position size based on capital and risk management

        Args:
            available_capital: Total available capital
            option_premium: Current option premium price
            lot_size: Lot size for the option contract
            max_loss_percent: Maximum loss as percentage of capital (optional)
            max_lots: Maximum number of lots to trade (optional)

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

            # Calculate maximum capital to allocate (60% of total)
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
            
            # Apply external max_lots constraint if provided
            if max_lots is not None and max_lots > 0:
                recommended_lots = min(recommended_lots, max_lots)
                
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

    def get_capital_utilization_summary(
        self,
        user_id: int,
        db: Session,
        trading_mode: TradingMode = TradingMode.PAPER
    ) -> Dict[str, Any]:
        """
        Get comprehensive capital utilization summary for a user

        Args:
            user_id: User identifier
            db: Database session
            trading_mode: Paper or Live trading mode

        Returns:
            Dict with capital utilization details

        Raises:
            ValueError: If user_id is invalid
        """
        if not user_id or user_id <= 0:
            raise ValueError("Invalid user_id provided")

        try:
            from database.models import AutoTradeExecution, ActivePosition

            # Get total capital
            if trading_mode == TradingMode.PAPER:
                from services.paper_trading_account import paper_trading_service
                account = paper_trading_service.accounts.get(user_id)
                if account:
                    total_capital = Decimal(str(account.available_margin)) + Decimal(str(account.used_margin))
                else:
                    total_capital = self.paper_trading_capital
            else:
                broker_config = self.get_active_broker_config(user_id, db)
                if broker_config:
                    total_capital = self._fetch_funds_from_broker(broker_config)
                else:
                    total_capital = Decimal('0')

            # Get allocated capital
            allocated_capital = self._get_allocated_capital_for_active_positions(user_id, db)

            # Get available capital
            available_capital = total_capital - allocated_capital

            # Get active positions count
            active_positions_count = db.query(ActivePosition).filter(
                ActivePosition.user_id == user_id,
                ActivePosition.is_active == True
            ).count()

            # Get active trades count
            active_trades_count = db.query(AutoTradeExecution).filter(
                AutoTradeExecution.user_id == user_id,
                AutoTradeExecution.status == "ACTIVE"
            ).count()

            # Calculate utilization percentage
            utilization_percent = (allocated_capital / total_capital * Decimal('100')) if total_capital > 0 else Decimal('0')

            # Get current PnL from active positions
            active_positions = db.query(ActivePosition).filter(
                ActivePosition.user_id == user_id,
                ActivePosition.is_active == True
            ).all()

            total_unrealized_pnl = sum(
                Decimal(str(pos.current_pnl)) for pos in active_positions
            )

            return {
                "user_id": user_id,
                "trading_mode": trading_mode.value,
                "total_capital": float(total_capital),
                "allocated_capital": float(allocated_capital),
                "available_capital": float(available_capital),
                "utilization_percent": float(utilization_percent),
                "active_positions_count": active_positions_count,
                "active_trades_count": active_trades_count,
                "total_unrealized_pnl": float(total_unrealized_pnl),
                "max_capital_per_trade": float(total_capital * self.max_capital_per_trade_percent),
                "max_risk_per_trade": float(total_capital * self.max_risk_per_trade_percent),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting capital utilization summary: {e}")
            return {
                "user_id": user_id,
                "error": str(e)
            }


# Create singleton instance
capital_manager = TradingCapitalManager()