"""
Multi-Demat Capital Service
Aggregates capital from all active demat accounts for a user
Provides unified view of available capital across brokers
"""

import logging
from decimal import Decimal
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.models import BrokerConfig, User, AutoTradeExecution, ActivePosition

logger = logging.getLogger(__name__)


class MultiDematCapitalService:
    """
    Aggregates and manages capital across multiple demat accounts

    Features:
    - Aggregates capital from all active demats
    - Calculates proportional allocation
    - Tracks capital utilization per demat
    - Validates token validity before including in capital pool
    """

    def __init__(self):
        """Initialize multi-demat capital service"""
        self.max_capital_utilization_percent = Decimal('0.80')  # Use max 80% of total capital
        self.max_per_trade_allocation_percent = Decimal('0.20')  # 20% max per trade
        logger.info("Multi-Demat Capital Service initialized")

    async def get_user_total_capital(
        self,
        user_id: int,
        db: Session,
        trading_mode: str = "live"
    ) -> Dict[str, Any]:
        """
        Get aggregated capital from all active demat accounts

        Args:
            user_id: User identifier
            db: Database session
            trading_mode: "paper" or "live"

        Returns:
            Dictionary with total capital and per-demat breakdown

        Raises:
            ValueError: If user_id is invalid
        """
        if not user_id or user_id <= 0:
            raise ValueError("Invalid user_id provided")

        try:
            # Paper trading mode - return virtual capital
            if trading_mode == "paper":
                return await self._get_paper_trading_capital(user_id, db)

            # Live trading mode - aggregate from all demats
            return self._get_live_trading_capital(user_id, db)

        except Exception as e:
            logger.error(f"Error getting user capital for user {user_id}: {e}")
            raise

    async def _get_paper_trading_capital(self, user_id: int, db: Session) -> Dict[str, Any]:
        """Get paper trading virtual capital using the singleton service"""
        from services.paper_trading_account import paper_trading_service
        
        # Get actual paper account state
        paper_account = await paper_trading_service.get_account(user_id)
        
        if paper_account:
            # Calculate totals based on PaperAccount state
            # total_available_capital (PaperAccount.current_balance) includes Cash + PnL
            # total_used_margin (PaperAccount.used_margin) is blocked capital
            # total_free_margin (PaperAccount.available_margin) is free cash for new trades
            
            # Note: In PaperAccount logic:
            # available_margin = initial - used + pnl
            # current_balance = initial - used (cash balance) -- Wait, let's verify PaperAccount logic
            # Logic from execute_trade:
            # used_margin += invested
            # available_margin -= invested
            # current_balance -= invested
            # Logic from close_position:
            # available_margin += invested + pnl
            # current_balance += invested + pnl
            
            # So:
            # available_margin = Free Cash (Available for trading)
            # current_balance = Free Cash (Same as available_margin in this implementation)
            # used_margin = Blocked Margin
            # Total Equity = available_margin + used_margin
            
            total_free_margin = Decimal(str(paper_account.available_margin))
            total_used_margin = Decimal(str(paper_account.used_margin))
            paper_capital = total_free_margin + total_used_margin
            
        else:
            # Fallback if account doesn't exist yet (create it implicitly)
            await paper_trading_service.create_paper_account(user_id)
            paper_capital = Decimal('100000')
            total_used_margin = Decimal('0')
            total_free_margin = paper_capital

        return {
            "user_id": user_id,
            "trading_mode": "paper",
            "total_available_capital": float(paper_capital),
            "total_used_margin": float(total_used_margin),
            "total_free_margin": float(total_free_margin),
            "capital_utilization_percent": float((total_used_margin / paper_capital) * 100) if paper_capital > 0 else 0,
            "max_trade_allocation": float(paper_capital * self.max_per_trade_allocation_percent),
            "demats": [
                {
                    "broker_name": "paper_trading",
                    "available_margin": float(paper_capital),
                    "used_margin": float(total_used_margin),
                    "free_margin": float(total_free_margin),
                    "is_active": True,
                    "token_valid": True,
                    "utilization_percent": float((total_used_margin / paper_capital) * 100) if paper_capital > 0 else 0
                }
            ],
            "timestamp": datetime.now().isoformat()
        }

    def _get_live_trading_capital(self, user_id: int, db: Session) -> Dict[str, Any]:
        """Get live trading capital aggregated from all demats"""

        # Get all active broker configurations with valid tokens
        active_brokers = db.query(BrokerConfig).filter(
            BrokerConfig.user_id == user_id,
            BrokerConfig.is_active == True,
            BrokerConfig.access_token.isnot(None),
            BrokerConfig.available_margin.isnot(None)
        ).all()

        if not active_brokers:
            logger.warning(f"No active brokers found for user {user_id}")
            return {
                "user_id": user_id,
                "trading_mode": "live",
                "total_available_capital": 0.0,
                "total_used_margin": 0.0,
                "total_free_margin": 0.0,
                "capital_utilization_percent": 0.0,
                "max_trade_allocation": 0.0,
                "demats": [],
                "error": "No active demat accounts found with valid tokens",
                "timestamp": datetime.now().isoformat()
            }

        # Calculate totals and per-demat breakdown
        total_available = Decimal('0')
        total_used = Decimal('0')
        demats_info = []

        for broker in active_brokers:
            # Check token validity
            token_valid = self._check_token_validity(broker)

            if not token_valid:
                logger.warning(f"Token expired for {broker.broker_name} user {user_id}")
                continue

            # Get broker margin info
            available_margin = Decimal(str(broker.available_margin or 0))
            used_margin = Decimal(str(broker.used_margin or 0))

            # Calculate used capital from active positions for this broker
            broker_used_capital = self._calculate_used_capital_by_broker(
                user_id, broker.broker_name, db
            )

            # Use the maximum of broker's used_margin and our calculated used capital
            actual_used = max(used_margin, broker_used_capital)

            free_margin = max(Decimal('0'), available_margin - actual_used)

            total_available += available_margin
            total_used += actual_used

            demats_info.append({
                "broker_name": broker.broker_name,
                "broker_id": broker.id,
                "available_margin": float(available_margin),
                "used_margin": float(actual_used),
                "free_margin": float(free_margin),
                "is_active": broker.is_active,
                "token_valid": token_valid,
                "token_expiry": broker.access_token_expiry.isoformat() if broker.access_token_expiry else None,
                "utilization_percent": float((actual_used / available_margin) * 100) if available_margin > 0 else 0,
                "last_updated": broker.funds_last_updated.isoformat() if broker.funds_last_updated else None
            })

        total_free = total_available - total_used
        utilization_percent = (total_used / total_available * 100) if total_available > 0 else 0
        max_trade_allocation = total_available * self.max_per_trade_allocation_percent

        return {
            "user_id": user_id,
            "trading_mode": "live",
            "total_available_capital": float(total_available),
            "total_used_margin": float(total_used),
            "total_free_margin": float(total_free),
            "capital_utilization_percent": float(utilization_percent),
            "max_trade_allocation": float(max_trade_allocation),
            "demats": demats_info,
            "total_demats": len(demats_info),
            "active_demats": len([d for d in demats_info if d["token_valid"]]),
            "timestamp": datetime.now().isoformat()
        }

    def _check_token_validity(self, broker_config: BrokerConfig) -> bool:
        """Check if broker access token is still valid"""
        if not broker_config.access_token:
            return False

        if broker_config.access_token_expiry:
            if broker_config.access_token_expiry <= datetime.now():
                return False

        return True

    def _calculate_used_capital(
        self,
        user_id: int,
        db: Session,
        trading_mode: str = "live"
    ) -> Decimal:
        """Calculate total used capital from active positions"""
        try:
            # Get all active positions for user
            active_positions = db.query(ActivePosition).join(
                AutoTradeExecution,
                ActivePosition.trade_execution_id == AutoTradeExecution.id
            ).filter(
                AutoTradeExecution.user_id == user_id,
                ActivePosition.is_active == True,
                AutoTradeExecution.trading_mode == trading_mode
            ).all()

            total_used = Decimal('0')
            for position in active_positions:
                # Calculate position value (entry_price × quantity)
                position_value = Decimal(str(position.entry_price or 0)) * Decimal(str(position.quantity or 0))
                total_used += position_value

            return total_used

        except Exception as e:
            logger.error(f"Error calculating used capital for user {user_id}: {e}")
            return Decimal('0')

    def _calculate_used_capital_by_broker(
        self,
        user_id: int,
        broker_name: str,
        db: Session
    ) -> Decimal:
        """Calculate used capital for a specific broker"""
        try:
            # Get active positions for this broker
            active_positions = db.query(ActivePosition).join(
                AutoTradeExecution,
                ActivePosition.trade_execution_id == AutoTradeExecution.id
            ).filter(
                AutoTradeExecution.user_id == user_id,
                AutoTradeExecution.broker_name == broker_name,
                ActivePosition.is_active == True,
                AutoTradeExecution.trading_mode == "live"
            ).all()

            total_used = Decimal('0')
            for position in active_positions:
                position_value = Decimal(str(position.entry_price or 0)) * Decimal(str(position.quantity or 0))
                total_used += position_value

            return total_used

        except Exception as e:
            logger.error(f"Error calculating used capital for broker {broker_name}: {e}")
            return Decimal('0')

    def calculate_proportional_allocation(
        self,
        demats: List[Dict[str, Any]],
        total_allocation: Decimal
    ) -> List[Dict[str, Any]]:
        """
        Calculate proportional capital allocation across demats

        Args:
            demats: List of demat info dictionaries
            total_allocation: Total capital to allocate

        Returns:
            List of allocation dictionaries with broker-wise breakdown
        """
        try:
            # Filter only demats with valid tokens and free margin
            valid_demats = [
                d for d in demats
                if d.get("token_valid") and d.get("free_margin", 0) > 0
            ]

            if not valid_demats:
                logger.warning("No valid demats with free margin for allocation")
                return []

            # Calculate total free margin across all valid demats
            total_free_margin = sum(Decimal(str(d["free_margin"])) for d in valid_demats)

            if total_free_margin == 0:
                logger.warning("No free margin available across demats")
                return []

            # Calculate proportional allocation
            allocations = []
            for demat in valid_demats:
                free_margin = Decimal(str(demat["free_margin"]))
                proportion = free_margin / total_free_margin

                allocated_capital = total_allocation * proportion

                # Ensure we don't exceed demat's free margin
                allocated_capital = min(allocated_capital, free_margin)

                allocations.append({
                    "broker_name": demat["broker_name"],
                    "broker_id": demat.get("broker_id"),
                    "allocated_capital": float(allocated_capital),
                    "proportion_percent": float(proportion * 100),
                    "free_margin_before": float(free_margin),
                    "free_margin_after": float(free_margin - allocated_capital)
                })

            return allocations

        except Exception as e:
            logger.error(f"Error calculating proportional allocation: {e}")
            return []

    def get_capital_summary_for_trade(
        self,
        user_id: int,
        required_capital: Decimal,
        db: Session,
        trading_mode: str = "live"
    ) -> Dict[str, Any]:
        """
        Get capital summary and allocation plan for a trade

        Args:
            user_id: User identifier
            required_capital: Capital required for trade
            db: Database session
            trading_mode: Trading mode

        Returns:
            Dictionary with capital availability and allocation plan
        """
        try:
            # Get total capital overview
            capital_overview = self.get_user_total_capital(user_id, db, trading_mode)

            total_free = Decimal(str(capital_overview["total_free_margin"]))
            max_allocation = Decimal(str(capital_overview["max_trade_allocation"]))

            # Check if trade is possible
            can_execute = required_capital <= total_free and required_capital <= max_allocation

            # Calculate allocation plan
            allocation_plan = []
            if can_execute:
                allocation_plan = self.calculate_proportional_allocation(
                    capital_overview["demats"],
                    required_capital
                )

            return {
                "user_id": user_id,
                "trading_mode": trading_mode,
                "required_capital": float(required_capital),
                "total_free_margin": float(total_free),
                "max_trade_allocation": float(max_allocation),
                "can_execute": can_execute,
                "allocation_plan": allocation_plan,
                "total_demats": capital_overview["total_demats"],
                "active_demats": capital_overview["active_demats"],
                "reason": None if can_execute else self._get_rejection_reason(
                    required_capital, total_free, max_allocation
                ),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting capital summary for trade: {e}")
            raise

    def _get_rejection_reason(
        self,
        required: Decimal,
        available: Decimal,
        max_allowed: Decimal
    ) -> str:
        """Get reason for trade rejection"""
        if required > available:
            return f"Insufficient capital: Required ₹{required:,.2f}, Available ₹{available:,.2f}"
        elif required > max_allowed:
            return f"Exceeds max allocation: Required ₹{required:,.2f}, Max allowed ₹{max_allowed:,.2f} (20% of total)"
        else:
            return "Unknown rejection reason"


# Global service instance
multi_demat_capital_service = MultiDematCapitalService()
