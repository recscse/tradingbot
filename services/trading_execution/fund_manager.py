"""
Fund Management Service
Handles capital, ledger entries, and balance tracking for Paper and Live accounts.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database.models import User, PaperTradingAccount, BrokerConfig, FundLedger, AutoTradeExecution
from utils.timezone_utils import get_ist_now_naive

logger = logging.getLogger("fund_manager")

class FundManagementService:
    """
    Manages all fund-related operations.
    Acts as a central authority for balance updates and ledger entries.
    """

    def _add_ledger_entry(
        self,
        db: Session,
        user_id: int,
        trading_mode: str,
        transaction_type: str,
        category: str,
        amount: Decimal,
        balance_before: Decimal,
        balance_after: Decimal,
        description: str,
        reference_id: Optional[str] = None
    ) -> FundLedger:
        """Helper to create a ledger entry"""
        entry = FundLedger(
            user_id=user_id,
            trading_mode=trading_mode,
            transaction_type=transaction_type,
            category=category,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            reference_id=reference_id,
            timestamp=get_ist_now_naive()
        )
        db.add(entry)
        return entry

    def get_balances(self, user_id: int, db: Session, trading_mode: str = "paper") -> Dict[str, Any]:
        """Get available, used, and total balances"""
        if trading_mode == "paper":
            account = db.query(PaperTradingAccount).filter(PaperTradingAccount.user_id == user_id).first()
            if not account:
                # Create default if not exists
                account = PaperTradingAccount(
                    user_id=user_id,
                    initial_capital=100000.0,
                    current_balance=100000.0,
                    available_margin=100000.0,
                    used_margin=0.0
                )
                db.add(account)
                db.commit()
                db.refresh(account)
            
            return {
                "available_margin": float(account.available_margin),
                "used_margin": float(account.used_margin),
                "current_balance": float(account.current_balance),
                "total_pnl": float(account.total_pnl),
                "trading_mode": "paper"
            }
        else:
            # Live Trading
            broker_config = db.query(BrokerConfig).filter(
                BrokerConfig.user_id == user_id, 
                BrokerConfig.is_active == True
            ).first()
            
            if not broker_config:
                return {
                    "available_margin": 0.0,
                    "used_margin": 0.0,
                    "current_balance": 0.0,
                    "trading_mode": "live",
                    "error": "No active broker found"
                }
            
            available = broker_config.available_margin or 0.0
            used = broker_config.used_margin or 0.0
            
            return {
                "available_margin": float(available),
                "used_margin": float(used),
                "current_balance": float(available + used),
                "trading_mode": "live"
            }

    def add_paper_funds(self, user_id: int, amount: float, db: Session, description: str = "Funds added by user") -> Dict[str, Any]:
        """Add virtual funds to paper trading account"""
        try:
            account = db.query(PaperTradingAccount).filter(PaperTradingAccount.user_id == user_id).first()
            if not account:
                # Create default
                account = PaperTradingAccount(
                    user_id=user_id,
                    initial_capital=float(amount),
                    current_balance=float(amount),
                    available_margin=float(amount),
                    used_margin=0.0
                )
                db.add(account)
                db.flush()
                balance_before = Decimal('0.0')
            else:
                balance_before = Decimal(str(account.current_balance))
                account.current_balance += float(amount)
                account.available_margin += float(amount)
                account.initial_capital += float(amount)
            
            balance_after = Decimal(str(account.current_balance))
            
            # Sync in-memory service
            from services.paper_trading_account import paper_trading_service
            mem_acc = paper_trading_service.accounts.get(user_id)
            if mem_acc:
                mem_acc.available_margin = float(account.available_margin)
                mem_acc.current_balance = float(account.current_balance)
                mem_acc.initial_capital = float(account.initial_capital)

            # Ledger Entry
            self._add_ledger_entry(
                db=db,
                user_id=user_id,
                trading_mode="paper",
                transaction_type="CREDIT",
                category="FUND_ADDED",
                amount=Decimal(str(amount)),
                balance_before=balance_before,
                balance_after=balance_after,
                description=description
            )
            
            db.commit()
            logger.info(f"✅ Added ₹{amount:,.2f} to paper account for user {user_id}")
            
            return {
                "success": True, 
                "amount": amount, 
                "new_balance": float(account.current_balance)
            }
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error adding paper funds: {e}")
            return {"success": False, "error": str(e)}

    def block_margin(self, user_id: int, amount: float, trading_mode: str, reference_id: str, db: Session) -> bool:
        """Block margin for a new trade"""
        try:
            amt_decimal = Decimal(str(amount))
            if trading_mode == "paper":
                account = db.query(PaperTradingAccount).filter(PaperTradingAccount.user_id == user_id).first()
                if not account or account.available_margin < float(amount):
                    return False
                
                balance_before = Decimal(str(account.available_margin))
                account.available_margin -= float(amount)
                account.used_margin += float(amount)
                balance_after = Decimal(str(account.available_margin))
                
                # Sync in-memory service if it exists
                from services.paper_trading_account import paper_trading_service
                mem_acc = paper_trading_service.accounts.get(user_id)
                if mem_acc:
                    mem_acc.available_margin = float(account.available_margin)
                    mem_acc.used_margin = float(account.used_margin)

                # Ledger entry for margin blocking (DEBIT from available margin)
                self._add_ledger_entry(
                    db=db,
                    user_id=user_id,
                    trading_mode="paper",
                    transaction_type="DEBIT",
                    category="TRADE_MARGIN_BLOCKED",
                    amount=amt_decimal,
                    balance_before=balance_before,
                    balance_after=balance_after,
                    description=f"Margin blocked for trade {reference_id}",
                    reference_id=reference_id
                )
                return True
            else:
                # For Live, we assume broker already blocked it, but we record it for statement
                broker_config = db.query(BrokerConfig).filter(BrokerConfig.user_id == user_id, BrokerConfig.is_active == True).first()
                if broker_config:
                    # Optional: locally update used_margin if we want to track it
                    pass
                
                # Still add ledger entry for consistency in statement
                # Balance for live is 'available_margin'
                bal = Decimal(str(broker_config.available_margin or 0))
                self._add_ledger_entry(
                    db=db,
                    user_id=user_id,
                    trading_mode="live",
                    transaction_type="DEBIT",
                    category="TRADE_MARGIN_BLOCKED",
                    amount=amt_decimal,
                    balance_before=bal,
                    balance_after=bal - amt_decimal, # Estimated local balance
                    description=f"Margin blocked for live trade {reference_id}",
                    reference_id=reference_id
                )
                return True
        except Exception as e:
            logger.error(f"Error blocking margin: {e}")
            return False

    def release_margin_and_settle(
        self, 
        user_id: int, 
        trading_mode: str, 
        reference_id: str, 
        invested_amount: float,
        gross_pnl: float,
        brokerage: float,
        taxes: float,
        db: Session
    ) -> bool:
        """Release margin and settle P&L after trade exit"""
        try:
            net_pnl = gross_pnl - brokerage - taxes
            invested_decimal = Decimal(str(invested_amount))
            net_pnl_decimal = Decimal(str(net_pnl))
            total_release = invested_decimal + net_pnl_decimal
            
            if trading_mode == "paper":
                account = db.query(PaperTradingAccount).filter(PaperTradingAccount.user_id == user_id).first()
                if not account: return False
                
                bal_before = Decimal(str(account.available_margin))
                
                # Release used margin
                account.used_margin = max(0.0, account.used_margin - invested_amount)
                
                # Update balances
                account.available_margin += float(total_release)
                account.current_balance += float(net_pnl)
                account.total_pnl += float(net_pnl)
                
                # Sync in-memory service
                from services.paper_trading_account import paper_trading_service
                mem_acc = paper_trading_service.accounts.get(user_id)
                if mem_acc:
                    mem_acc.available_margin = float(account.available_margin)
                    mem_acc.used_margin = float(account.used_margin)
                    mem_acc.current_balance = float(account.current_balance)
                    mem_acc.total_pnl = float(account.total_pnl)

                bal_after = Decimal(str(account.available_margin))
                
                # Ledger entry: Margin Released + P&L Settlement
                self._add_ledger_entry(
                    db=db,
                    user_id=user_id,
                    trading_mode="paper",
                    transaction_type="CREDIT" if total_release >= 0 else "DEBIT",
                    category="PNL_SETTLEMENT",
                    amount=abs(total_release),
                    balance_before=bal_before,
                    balance_after=bal_after,
                    description=f"PnL Settlement for {reference_id} (Net: ₹{net_pnl:.2f})",
                    reference_id=reference_id
                )
                
                # Optional: Detail entries for Charges
                if brokerage > 0 or taxes > 0:
                    self._add_ledger_entry(
                        db=db,
                        user_id=user_id,
                        trading_mode="paper",
                        transaction_type="DEBIT",
                        category="CHARGES",
                        amount=Decimal(str(brokerage + taxes)),
                        balance_before=bal_after + Decimal(str(brokerage + taxes)),
                        balance_after=bal_after,
                        description=f"Brokerage & Taxes for {reference_id}",
                        reference_id=reference_id
                    )
                
                return True
            else:
                # Live settlement (Local record only)
                broker_config = db.query(BrokerConfig).filter(BrokerConfig.user_id == user_id, BrokerConfig.is_active == True).first()
                bal = Decimal(str(broker_config.available_margin or 0)) if broker_config else Decimal('0')
                
                self._add_ledger_entry(
                    db=db,
                    user_id=user_id,
                    trading_mode="live",
                    transaction_type="CREDIT" if total_release >= 0 else "DEBIT",
                    category="PNL_SETTLEMENT",
                    amount=abs(total_release),
                    balance_before=bal,
                    balance_after=bal + net_pnl_decimal, # Estimated
                    description=f"Live PnL Settlement for {reference_id} (Net: ₹{net_pnl:.2f})",
                    reference_id=reference_id
                )
                return True
        except Exception as e:
            logger.error(f"Error releasing margin: {e}")
            return False

    def get_statement(self, user_id: int, db: Session, trading_mode: str = "paper", limit: int = 50) -> List[Dict[str, Any]]:
        """Get fund statement (ledger entries)"""
        entries = db.query(FundLedger).filter(
            FundLedger.user_id == user_id,
            FundLedger.trading_mode == trading_mode
        ).order_by(desc(FundLedger.timestamp)).limit(limit).all()
        
        return [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "type": e.transaction_type,
                "category": e.category,
                "amount": float(e.amount),
                "balance_before": float(e.balance_before),
                "balance_after": float(e.balance_after),
                "description": e.description,
                "reference_id": e.reference_id
            } for e in entries
        ]

fund_manager = FundManagementService()
