"""
Paper Trading Account Management System
Manages virtual capital, positions, and P&L for paper trading mode
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP
import json

from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User

logger = logging.getLogger(__name__)

@dataclass
class PaperAccount:
    """Paper trading account structure"""
    user_id: int
    initial_capital: float
    current_balance: float
    used_margin: float
    available_margin: float
    total_pnl: float
    daily_pnl: float
    positions_count: int
    max_positions: int = 10
    max_risk_per_trade: float = 0.02  # 2%
    max_daily_loss: float = 0.05  # 5%
    created_at: datetime = None
    updated_at: datetime = None

@dataclass
class PaperPosition:
    """Paper trading position"""
    position_id: str
    user_id: int
    symbol: str
    instrument_key: str
    option_type: str  # CE/PE
    strike_price: float
    entry_price: float
    current_price: float
    quantity: int
    lot_size: int
    invested_amount: float
    current_value: float
    pnl: float
    pnl_percentage: float
    stop_loss: float
    target: float
    entry_time: datetime
    status: str = "ACTIVE"  # ACTIVE, CLOSED, PARTIAL

class PaperTradingAccountService:
    """Complete paper trading account management"""
    
    def __init__(self):
        self.accounts: Dict[int, PaperAccount] = {}  # user_id -> PaperAccount
        self.positions: Dict[int, List[PaperPosition]] = {}  # user_id -> positions
        self.trade_history: Dict[int, List[Dict]] = {}  # user_id -> trade history
    
    async def get_account(self, user_id: int, db: Optional[Session] = None) -> Optional[PaperAccount]:
        """
        Get account from memory or DB
        """
        account = self.accounts.get(user_id)
        if not account and db:
            account = await self.sync_with_db(user_id, db)
        return account

    async def create_paper_account(self, user_id: int, initial_capital: float = 100000) -> PaperAccount:
        """
        Create new paper trading account
        
        Args:
            user_id: User ID
            initial_capital: Starting virtual capital (default ₹1 lakh)
        """
        try:
            account = PaperAccount(
                user_id=user_id,
                initial_capital=initial_capital,
                current_balance=initial_capital,
                used_margin=0.0,
                available_margin=initial_capital,
                total_pnl=0.0,
                daily_pnl=0.0,
                positions_count=0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            self.accounts[user_id] = account
            self.positions[user_id] = []
            self.trade_history[user_id] = []
            
            logger.info(f"✅ Paper account created for user {user_id}: ₹{initial_capital:,.2f}")
            return account
            
        except Exception as e:
            logger.error(f"❌ Error creating paper account: {e}")
            raise
    
    async def sync_with_db(self, user_id: int, db: Session) -> Optional[PaperAccount]:
        """
        Synchronize in-memory account with database
        """
        try:
            from database.models import PaperTradingAccount
            
            db_account = db.query(PaperTradingAccount).filter(PaperTradingAccount.user_id == user_id).first()
            
            if not db_account:
                # Create default in DB if not exists
                db_account = PaperTradingAccount(
                    user_id=user_id,
                    initial_capital=100000.0,
                    current_balance=100000.0,
                    available_margin=100000.0,
                    used_margin=0.0,
                    total_pnl=0.0
                )
                db.add(db_account)
                db.commit()
                db.refresh(db_account)

            # Update in-memory
            account = PaperAccount(
                user_id=db_account.user_id,
                initial_capital=float(db_account.initial_capital),
                current_balance=float(db_account.current_balance),
                used_margin=float(db_account.used_margin),
                available_margin=float(db_account.available_margin),
                total_pnl=float(db_account.total_pnl),
                daily_pnl=float(db_account.daily_pnl),
                positions_count=db_account.positions_count,
                max_positions=db_account.max_positions,
                max_risk_per_trade=float(db_account.max_risk_per_trade),
                max_daily_loss=float(db_account.max_daily_loss),
                created_at=db_account.created_at,
                updated_at=db_account.updated_at
            )
            
            self.accounts[user_id] = account
            return account
            
        except Exception as e:
            logger.error(f"❌ Error syncing paper account: {e}")
            return self.accounts.get(user_id)

    def execute_paper_trade_sync(self, user_id: int, trade_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """
        Synchronous version of execute_paper_trade for use in non-async contexts
        """
        try:
            # Sync with DB first to ensure we have latest data
            from database.models import PaperTradingAccount
            db_acc = db.query(PaperTradingAccount).filter(PaperTradingAccount.user_id == user_id).first()
            
            if not db_acc:
                db_acc = PaperTradingAccount(
                    user_id=user_id,
                    initial_capital=100000.0,
                    current_balance=100000.0,
                    available_margin=100000.0,
                    used_margin=0.0,
                    total_pnl=0.0
                )
                db.add(db_acc)
                db.flush()

            invested_amount = float(trade_data['invested_amount'])
            entry_charges = 20.0
            total_entry_cost = invested_amount + entry_charges
            
            # Update DB
            db_acc.used_margin += invested_amount
            db_acc.available_margin -= total_entry_cost
            db_acc.current_balance -= total_entry_cost
            db_acc.total_pnl -= entry_charges
            db_acc.positions_count += 1
            db_acc.updated_at = datetime.now(timezone.utc)
            
            # Update in-memory if it exists
            account = self.accounts.get(user_id)
            if account:
                account.used_margin = float(db_acc.used_margin)
                account.available_margin = float(db_acc.available_margin)
                account.current_balance = float(db_acc.current_balance)
                account.total_pnl = float(db_acc.total_pnl)
                account.positions_count = db_acc.positions_count
            
            logger.info(f"✅ Paper trade executed (Sync): {trade_data['symbol']} (Invested: ₹{invested_amount})")
            return {"success": True}
            
        except Exception as e:
            logger.error(f"❌ Error executing paper trade sync: {e}")
            return {"success": False, "error": str(e)}

    async def execute_paper_trade(self, user_id: int, trade_data: Dict[str, Any], db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Execute paper trade (virtual execution) with CHARGES
        """
        try:
            account = self.accounts.get(user_id)
            if not account and db:
                account = await self.sync_with_db(user_id, db)
                
            if not account:
                return {"success": False, "error": "Account not found"}
            
            invested_amount = float(trade_data['invested_amount'])
            
            # Entry Charges: ₹20 brokerage
            entry_charges = 20.0
            total_entry_cost = invested_amount + entry_charges
            
            # Validate trade
            validation = await self.validate_trade(user_id, total_entry_cost)
            if not validation['valid']:
                return {"success": False, "error": validation['reason']}
            
            # Update account
            account.used_margin += invested_amount
            account.available_margin -= total_entry_cost
            account.current_balance -= total_entry_cost
            account.total_pnl -= entry_charges # Charges are an immediate loss
            account.positions_count += 1
            account.updated_at = datetime.now(timezone.utc)
            
            # Sync to DB if session provided
            if db:
                from database.models import PaperTradingAccount
                db_acc = db.query(PaperTradingAccount).filter(PaperTradingAccount.user_id == user_id).first()
                if db_acc:
                    db_acc.used_margin = account.used_margin
                    db_acc.available_margin = account.available_margin
                    db_acc.current_balance = account.current_balance
                    db_acc.total_pnl = account.total_pnl
                    db_acc.positions_count = account.positions_count
                    db_acc.updated_at = datetime.now(timezone.utc)
            
            # Create position object
            position = PaperPosition(
                position_id=f"P_{user_id}_{int(datetime.now().timestamp())}",
                user_id=user_id,
                symbol=trade_data['symbol'],
                instrument_key=trade_data['instrument_key'],
                option_type=trade_data['option_type'],
                strike_price=trade_data['strike_price'],
                entry_price=trade_data['entry_price'],
                current_price=trade_data['entry_price'],
                quantity=trade_data['quantity'],
                lot_size=trade_data['lot_size'],
                invested_amount=invested_amount,
                current_value=invested_amount,
                pnl=-entry_charges, # Start with negative PnL due to charges
                pnl_percentage=( -entry_charges / invested_amount * 100 ),
                stop_loss=trade_data.get('stop_loss', 0.0),
                target=trade_data.get('target', 0.0),
                entry_time=datetime.now(timezone.utc)
            )
            
            if user_id not in self.positions:
                self.positions[user_id] = []
            self.positions[user_id].append(position)
            
            logger.info(f"✅ Paper trade executed: {position.symbol} (Invested: ₹{invested_amount}, Charges: ₹{entry_charges})")
            
            return {
                "success": True,
                "position_id": position.position_id,
                "message": "Trade executed successfully",
                "position": asdict(position)
            }
            
        except Exception as e:
            logger.error(f"❌ Error executing paper trade: {e}")
            return {"success": False, "error": str(e)}

    async def close_position(self, user_id: int, position_id: str, exit_price: float, db: Optional[Session] = None) -> Dict[str, Any]:
        """Close a paper trading position with EXIT CHARGES"""
        try:
            account = self.accounts.get(user_id)
            if not account and db:
                account = await self.sync_with_db(user_id, db)
                
            if not account:
                return {"success": False, "error": "Account not found"}
            
            # Find position
            position = None
            for pos in self.positions.get(user_id, []):
                if pos.position_id == position_id and pos.status == "ACTIVE":
                    position = pos
                    break
            
            if not position:
                return {"success": False, "error": "Position not found"}
            
            # Calculate final P&L
            # Quantity is total units (lots * lot_size), so simple multiplication
            exit_value = exit_price * position.quantity
            gross_pnl = exit_value - position.invested_amount
            
            # Exit Charges: ₹20 brokerage + 0.1% taxes on turnover
            turnover = position.invested_amount + exit_value
            exit_charges = 20.0 + (turnover * 0.001)
            
            net_pnl = gross_pnl - exit_charges

            # Update position
            position.status = "CLOSED"
            position.pnl = net_pnl
            position.pnl_percentage = (net_pnl / position.invested_amount) * 100

            # Update account
            # Release Invested amount and add (Exit Value - Exit Charges)
            account.used_margin -= position.invested_amount
            release_amount = exit_value - exit_charges
            account.available_margin += release_amount
            account.current_balance += release_amount
            account.total_pnl += net_pnl
            account.daily_pnl += net_pnl
            account.positions_count = max(0, account.positions_count - 1)
            account.updated_at = datetime.now(timezone.utc)
            
            # Sync to DB
            if db:
                from database.models import PaperTradingAccount
                db_acc = db.query(PaperTradingAccount).filter(PaperTradingAccount.user_id == user_id).first()
                if db_acc:
                    db_acc.used_margin = account.used_margin
                    db_acc.available_margin = account.available_margin
                    db_acc.current_balance = account.current_balance
                    db_acc.total_pnl = account.total_pnl
                    db_acc.daily_pnl = account.daily_pnl
                    db_acc.positions_count = account.positions_count
                    db_acc.updated_at = datetime.now(timezone.utc)
            
            logger.info(f"✅ Position closed: {position.symbol} Net PnL: ₹{net_pnl:,.2f} (Charges: ₹{exit_charges:.2f})")
            
            return {
                "success": True,
                "net_pnl": net_pnl,
                "release_amount": release_amount
            }
            
        except Exception as e:
            logger.error(f"❌ Error closing position: {e}")
            return {"success": False, "error": str(e)}

    
    async def get_account_summary(self, user_id: int) -> Dict[str, Any]:
        """Get complete account summary"""
        try:
            account = self.accounts.get(user_id)
            positions = self.positions.get(user_id, [])
            history = self.trade_history.get(user_id, [])
            
            if not account:
                return {"error": "Account not found"}
            
            active_positions = [pos for pos in positions if pos.status == "ACTIVE"]
            closed_positions = [pos for pos in positions if pos.status == "CLOSED"]
            
            return {
                "account": asdict(account),
                "active_positions": [asdict(pos) for pos in active_positions],
                "closed_positions_count": len(closed_positions),
                "trade_history_count": len(history),
                "performance": {
                    "total_trades": len(history) // 2,  # Buy + Sell = 1 complete trade
                    "win_rate": self._calculate_win_rate(closed_positions),
                    "avg_profit": self._calculate_avg_profit(closed_positions),
                    "max_drawdown": self._calculate_max_drawdown(history),
                    "sharpe_ratio": self._calculate_sharpe_ratio(closed_positions)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting account summary: {e}")
            return {"error": str(e)}
    
    def _calculate_win_rate(self, closed_positions: List[PaperPosition]) -> float:
        """Calculate win rate from closed positions"""
        if not closed_positions:
            return 0.0
        
        winning_trades = sum(1 for pos in closed_positions if pos.pnl > 0)
        return (winning_trades / len(closed_positions)) * 100
    
    def _calculate_avg_profit(self, closed_positions: List[PaperPosition]) -> float:
        """Calculate average profit per trade"""
        if not closed_positions:
            return 0.0
        
        total_pnl = sum(pos.pnl for pos in closed_positions)
        return total_pnl / len(closed_positions)
    
    def _calculate_max_drawdown(self, trade_history: List[Dict]) -> float:
        """Calculate maximum drawdown"""
        if not trade_history:
            return 0.0
        
        # Simplified calculation - can be enhanced
        running_pnl = 0.0
        max_pnl = 0.0
        max_drawdown = 0.0
        
        for trade in trade_history:
            if 'pnl' in trade:
                running_pnl += trade['pnl']
                max_pnl = max(max_pnl, running_pnl)
                drawdown = max_pnl - running_pnl
                max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    def _calculate_sharpe_ratio(self, closed_positions: List[PaperPosition]) -> float:
        """Calculate Sharpe ratio (simplified)"""
        if len(closed_positions) < 2:
            return 0.0
        
        returns = [pos.pnl_percentage for pos in closed_positions]
        avg_return = sum(returns) / len(returns)
        
        # Calculate standard deviation
        variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return 0.0
        
        # Assuming risk-free rate of 6% annually
        risk_free_rate = 6.0 / 365  # Daily risk-free rate
        return (avg_return - risk_free_rate) / std_dev

# Global instance
paper_trading_service = PaperTradingAccountService()