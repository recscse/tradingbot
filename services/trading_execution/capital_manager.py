"""
Trading Capital Manager
Manages capital allocation, validates available funds, and calculates position sizes
"""

import logging
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
# FIX 6: Cleaned imports, removed unused User import
from sqlalchemy.orm import Session
from database.models import BrokerConfig, ActivePosition, AutoTradeExecution
from utils.timezone_utils import get_ist_now_naive

logger = logging.getLogger(__name__)


class TradingMode(Enum):
    """Trading mode configuration"""
    PAPER = "paper"
    LIVE = "live"


@dataclass
class CapitalAllocation:
    """
    Capital allocation details for a trading position
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
    """

    def __init__(self):
        """Initialize capital manager with configuration"""
        self.paper_trading_capital = Decimal('100000')  # 1 Lakh default for paper trading
        self.max_capital_per_trade_percent = Decimal('0.60')  # 60% max per trade
        self.max_risk_per_trade_percent = Decimal('0.02')  # 2% max risk per trade
        self.min_capital_buffer = Decimal('0.10')  # Keep 10% buffer
        self.last_error = None
        self.function_health = {
            "fetch_funds": {"status": "unknown", "last_run": None, "error": None},
            "position_sizing": {"status": "unknown", "last_run": None, "error": None},
            "available_capital": {"status": "unknown", "last_run": None, "error": None}
        }

        logger.info("Trading Capital Manager initialized")

    def get_status(self) -> Dict[str, Any]:
        """Get status for system health monitoring"""
        # FIX 1: Timezone consistency
        status = "healthy"
        if self.last_error:
            status = "warning"
            
        return {
            "status": status,
            "last_error": self.last_error,
            "function_health": self.function_health,
            "timestamp": get_ist_now_naive().isoformat()
        }

    def _update_function_health(self, func_name: str, status: str, error: str = None):
        """Update internal function health"""
        # FIX 1: Timezone consistency
        self.function_health[func_name] = {
            "status": status,
            "last_run": get_ist_now_naive().isoformat(),
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
                return None

            # FIX 1: Timezone consistency for token expiry check
            now_ist = get_ist_now_naive()
            if broker_config.access_token_expiry and broker_config.access_token_expiry < now_ist:
                logger.warning(f"Broker token expired for user {user_id}")
                return None

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
        """
        if not user_id or user_id <= 0:
            raise ValueError("Invalid user_id provided")

        try:
            if trading_mode == TradingMode.PAPER:
                # FIX 3: Paper Trading Capital Source handled safely
                from services.paper_trading_account import paper_trading_service, PaperAccount
                account = paper_trading_service.accounts.get(user_id)
                
                if not account:
                    # Sync with DB synchronously
                    from database.models import PaperTradingAccount
                    db_account = db.query(PaperTradingAccount).filter(PaperTradingAccount.user_id == user_id).first()
                    if db_account:
                        account = PaperAccount(
                            user_id=db_account.user_id,
                            initial_capital=float(db_account.initial_capital),
                            current_balance=float(db_account.current_balance),
                            used_margin=float(db_account.used_margin),
                            available_margin=float(db_account.available_margin),
                            total_pnl=float(db_account.total_pnl),
                            daily_pnl=float(db_account.daily_pnl),
                            positions_count=db_account.positions_count
                        )
                        paper_trading_service.accounts[user_id] = account

                if account:
                    total_capital = Decimal(str(account.available_margin)) + Decimal(str(account.used_margin))
                else:
                    logger.warning(f"Paper account not found for user {user_id}. Falling back to default capital.")
                    total_capital = self.paper_trading_capital
            else:
                broker_config = self.get_active_broker_config(user_id, db)
                if not broker_config:
                    self._update_function_health("available_capital", "error", "No active broker config")
                    return Decimal('0')

                available_margin, used_margin = self._fetch_funds_from_broker(broker_config)
                # For Live trading, available_margin already accounts for used margin
                # We return it directly as the 'available' cash
                return max(Decimal('0'), available_margin)

            # For Paper Trading only: JOIN check to ensure only truly active positions consume capital
            allocated_capital = self._get_allocated_capital_for_active_positions(user_id, db)
            available_capital = total_capital - allocated_capital

            # FIX 5: Health tracking
            self._update_function_health("available_capital", "success")
            return max(Decimal('0'), available_capital)

        except Exception as e:
            self._update_function_health("available_capital", "error", str(e))
            logger.error(f"Error getting available capital: {e}")
            return Decimal('0')

    def get_available_capital_for_new_position(
        self,
        user_id: int,
        db: Session,
        trading_mode: TradingMode = TradingMode.PAPER
    ) -> Decimal:
        """
        Get capital available for opening a NEW position
        """
        if not user_id or user_id <= 0:
            raise ValueError("Invalid user_id provided")

        try:
            if trading_mode == TradingMode.PAPER:
                # FIX 3: Paper Trading Capital Source handled safely
                from services.paper_trading_account import paper_trading_service, PaperAccount
                account = paper_trading_service.accounts.get(user_id)
                
                if not account:
                    # Sync with DB synchronously
                    from database.models import PaperTradingAccount
                    db_account = db.query(PaperTradingAccount).filter(PaperTradingAccount.user_id == user_id).first()
                    if db_account:
                        account = PaperAccount(
                            user_id=db_account.user_id,
                            initial_capital=float(db_account.initial_capital),
                            current_balance=float(db_account.current_balance),
                            used_margin=float(db_account.used_margin),
                            available_margin=float(db_account.available_margin),
                            total_pnl=float(db_account.total_pnl),
                            daily_pnl=float(db_account.daily_pnl),
                            positions_count=db_account.positions_count
                        )
                        paper_trading_service.accounts[user_id] = account

                if account:
                    total_capital = Decimal(str(account.available_margin)) + Decimal(str(account.used_margin))
                else:
                    logger.warning(f"Paper account not found for user {user_id}. Falling back to default capital.")
                    total_capital = self.paper_trading_capital
            else:
                broker_config = self.get_active_broker_config(user_id, db)
                if not broker_config:
                    return Decimal('0')
                available_margin, used_margin = self._fetch_funds_from_broker(broker_config)
                # For Live, the broker API gives us free cash directly as available_margin
                total_capital = available_margin

            # Check concurrent position limit
            active_positions_count = db.query(ActivePosition).filter(
                ActivePosition.user_id == user_id,
                ActivePosition.is_active == True
            ).count()

            if active_positions_count >= 5: # MAX_CONCURRENT_POSITIONS
                return Decimal('0')

            # FIX 5: Health tracking
            self._update_function_health("available_capital", "success")
            # Return available margin (free cash)
            return total_capital

        except Exception as e:
            self._update_function_health("available_capital", "error", str(e))
            return Decimal('0')

    def get_total_account_size(
        self,
        user_id: int,
        db: Session,
        trading_mode: TradingMode = TradingMode.PAPER
    ) -> Decimal:
        """
        Get the total base capital of the account (Available + Used)
        Used for risk-per-trade percentage calculations
        """
        try:
            if trading_mode == TradingMode.PAPER:
                from services.paper_trading_account import paper_trading_service
                account = paper_trading_service.accounts.get(user_id)
                if account:
                    return Decimal(str(account.available_margin)) + Decimal(str(account.used_margin))
                return self.paper_trading_capital
            else:
                broker_config = self.get_active_broker_config(user_id, db)
                if not broker_config:
                    return Decimal('0')
                available, used = self._fetch_funds_from_broker(broker_config)
                return available + used
        except Exception:
            return Decimal('0')

    def _get_allocated_capital_for_active_positions(
        self,
        user_id: int,
        db: Session
    ) -> Decimal:
        """
        Calculate total capital allocated to user's active positions
        """
        try:
            # FIX 2: Joined query to ensure we only count positions where ActivePosition is true
            active_trades = db.query(AutoTradeExecution).join(
                ActivePosition, AutoTradeExecution.id == ActivePosition.trade_execution_id
            ).filter(
                ActivePosition.user_id == user_id,
                ActivePosition.is_active == True
            ).all()

            total_allocated = Decimal('0')
            for trade in active_trades:
                if trade.allocated_capital:
                    total_allocated += Decimal(str(trade.allocated_capital))
                else:
                    # Fallback: calculate from entry_price * quantity
                    total_allocated += Decimal(str(trade.entry_price)) * Decimal(str(trade.quantity))

            return total_allocated

        except Exception as e:
            logger.error(f"Error calculating allocated capital: {e}")
            return Decimal('0')

    def _fetch_funds_from_broker(self, broker_config: BrokerConfig) -> Tuple[Decimal, Decimal]:
        """
        Fetch available funds from broker API
        Returns: (available_margin, used_margin)
        """
        try:
            broker_name = broker_config.broker_name.lower()
            available = Decimal('0')
            used = Decimal('0')

            if 'upstox' in broker_name:
                from brokers.upstox_broker import UpstoxBroker
                broker = UpstoxBroker(broker_config)
                funds_data = broker.get_funds()
                if funds_data and 'equity' in funds_data:
                    equity = funds_data['equity']
                    available = Decimal(str(equity.get('available_margin', 0)))
                    used = Decimal(str(equity.get('used_margin', 0)))

            elif 'angel' in broker_name:
                from brokers.angel_one_broker import AngelOneBroker
                broker = AngelOneBroker(broker_config)
                funds_data = broker.get_funds()
                if funds_data and 'availablecash' in funds_data:
                    available = Decimal(str(funds_data['availablecash']))
                    # Angel doesn't easily expose 'used' in this simple call, 
                    # but we can assume total = available if used not found
                    used = Decimal('0')

            elif 'dhan' in broker_name:
                from brokers.dhan_broker import DhanBroker
                broker = DhanBroker(broker_config)
                funds_data = broker.get_funds()
                if funds_data and 'availableBalance' in funds_data:
                    available = Decimal(str(funds_data['availableBalance']))
                    used = Decimal('0')

            # FIX 5: Health tracking
            self._update_function_health("fetch_funds", "success")
            return available, used

        except Exception as e:
            # FIX 5: Health tracking
            self._update_function_health("fetch_funds", "error", str(e))
            logger.error(f"Error fetching funds from broker: {e}")
            return Decimal('0'), Decimal('0')

    def calculate_position_size(
        self,
        available_capital: Decimal,
        option_premium: Decimal,
        lot_size: int,
        max_loss_percent: Optional[Decimal] = None,
        max_lots: Optional[int] = None,
        risk_per_unit: Optional[Decimal] = None,
        total_account_size: Optional[Decimal] = None
    ) -> CapitalAllocation:
        """
        Calculate optimal position size based on capital and risk management
        """
        if available_capital <= 0:
            raise ValueError("Available capital must be positive")
        if option_premium <= 0:
            raise ValueError("Option premium must be positive")
        if lot_size <= 0:
            raise ValueError("Lot size must be positive")

        try:
            if not max_loss_percent:
                max_loss_percent = self.max_risk_per_trade_percent

            # IMPORTANT: Use total_account_size for the risk amount calculation if provided
            # Risk is 2% of the TOTAL account, not just what's left.
            risk_base = total_account_size if total_account_size is not None else available_capital
            
            max_allocable_capital = available_capital * self.max_capital_per_trade_percent
            max_loss_amount = risk_base * max_loss_percent
            position_value_per_lot = option_premium * Decimal(str(lot_size))

            # Use provided risk per unit (e.g., entry - SL) or default to 100% of premium
            effective_risk_per_unit = risk_per_unit if (risk_per_unit and risk_per_unit > 0) else option_premium
            
            # SAFEGUARD: Cap effective risk at 40% of premium for small accounts
            # If risk is 100%, it's almost impossible to trade on small accounts.
            max_risk_allowed = option_premium * Decimal('0.40')
            if effective_risk_per_unit > max_risk_allowed:
                logger.info(f"Capping risk per unit from {effective_risk_per_unit:.2f} to {max_risk_allowed:.2f} (40% of premium)")
                effective_risk_per_unit = max_risk_allowed

            risk_per_lot = effective_risk_per_unit * Decimal(str(lot_size))

            max_lots_by_capital = int(max_allocable_capital / position_value_per_lot)
            max_lots_by_risk = int(max_loss_amount / risk_per_lot)

            recommended_lots = min(max_lots_by_capital, max_lots_by_risk)
            
            # FIX: Prevent 0-lot rejections for valid signals if risk is acceptable
            # If recommended is 0 but we have capital, check if 1 lot is within HARD risk limit (2.5%)
            if recommended_lots <= 0 and max_lots_by_capital >= 1:
                hard_risk_percent = Decimal('0.025')  # 2.5% hard limit
                hard_max_loss_amount = risk_base * hard_risk_percent
                
                if risk_per_lot <= hard_max_loss_amount:
                    logger.info(f"Using 1 lot as fallback: risk ₹{risk_per_lot:.2f} is within 2.5% hard limit (₹{hard_max_loss_amount:.2f})")
                    recommended_lots = 1
                else:
                    logger.warning(f"Rejecting trade: 1 lot risk ₹{risk_per_lot:.2f} exceeds 2.5% hard limit (₹{hard_max_loss_amount:.2f})")

            if max_lots is not None and max_lots > 0:
                recommended_lots = min(recommended_lots, max_lots)
                
            # FIX 4: Critical Risk Fix - Raise error instead of forcing 1 lot
            if recommended_lots <= 0:
                raise ValueError(f"Position size calculation resulted in 0 lots for premium {option_premium} (risk per unit: {effective_risk_per_unit:.4f}). Trade rejected to prevent risk violation. Max allocable: ₹{max_allocable_capital:.2f}, Risk limit: ₹{max_loss_amount:.2f}")

            allocated_capital = position_value_per_lot * Decimal(str(recommended_lots))
            capital_utilization = (allocated_capital / available_capital) * Decimal('100')
            risk_per_trade = (risk_per_lot * Decimal(str(recommended_lots)) / available_capital) * Decimal('100')

            allocation = CapitalAllocation(
                total_capital=available_capital,
                allocated_capital=allocated_capital,
                position_size_lots=recommended_lots,
                position_value=allocated_capital,
                max_loss=risk_per_lot * Decimal(str(recommended_lots)),
                margin_required=allocated_capital,
                capital_utilization_percent=capital_utilization,
                risk_per_trade_percent=risk_per_trade
            )

            # FIX 5: Health tracking
            self._update_function_health("position_sizing", "success")
            return allocation

        except Exception as e:
            # FIX 5: Health tracking
            self._update_function_health("position_sizing", "error", str(e))
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
        """
        if not user_id or user_id <= 0:
            raise ValueError("Invalid user_id provided")
        if required_capital <= 0:
            raise ValueError("Required capital must be positive")

        try:
            available_capital = self.get_available_capital(user_id, db, trading_mode)
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
            return {"valid": False, "error": str(e)}

    def get_capital_utilization_summary(
        self,
        user_id: int,
        db: Session,
        trading_mode: TradingMode = TradingMode.PAPER
    ) -> Dict[str, Any]:
        """
        Get comprehensive capital utilization summary for a user
        """
        if not user_id or user_id <= 0:
            raise ValueError("Invalid user_id provided")

        try:
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
                    available, used = self._fetch_funds_from_broker(broker_config)
                    total_capital = available + used
                else:
                    total_capital = Decimal('0')

            allocated_capital = self._get_allocated_capital_for_active_positions(user_id, db)
            available_capital = total_capital - allocated_capital

            active_positions_count = db.query(ActivePosition).filter(
                ActivePosition.user_id == user_id,
                ActivePosition.is_active == True
            ).count()

            utilization_percent = (allocated_capital / total_capital * Decimal('100')) if total_capital > 0 else Decimal('0')

            return {
                "user_id": user_id,
                "trading_mode": trading_mode.value,
                "total_capital": float(total_capital),
                "allocated_capital": float(allocated_capital),
                "available_capital": float(available_capital),
                "utilization_percent": float(utilization_percent),
                "active_positions_count": active_positions_count,
                # FIX 1: Timezone consistency
                "timestamp": get_ist_now_naive().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting capital summary: {e}")
            return {"user_id": user_id, "error": str(e)}


# Create singleton instance
capital_manager = TradingCapitalManager()
