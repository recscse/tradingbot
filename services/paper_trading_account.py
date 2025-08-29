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
    
    async def create_paper_account(self, user_id: int, initial_capital: float = 500000) -> PaperAccount:
        """
        Create new paper trading account
        
        Args:
            user_id: User ID
            initial_capital: Starting virtual capital (default ₹5 lakhs)
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
    
    async def get_account(self, user_id: int) -> Optional[PaperAccount]:
        """Get paper trading account for user"""
        return self.accounts.get(user_id)
    
    async def update_account_settings(self, user_id: int, settings: Dict[str, Any]) -> bool:
        """
        Update account settings (capital, risk limits, etc.)
        
        Args:
            user_id: User ID
            settings: Dictionary with settings to update
        """
        try:
            account = self.accounts.get(user_id)
            if not account:
                return False
            
            # Update allowed settings
            if 'initial_capital' in settings:
                new_capital = float(settings['initial_capital'])
                # Adjust current balance proportionally
                ratio = new_capital / account.initial_capital
                account.current_balance *= ratio
                account.available_margin *= ratio
                account.initial_capital = new_capital
                
            if 'max_positions' in settings:
                account.max_positions = int(settings['max_positions'])
                
            if 'max_risk_per_trade' in settings:
                account.max_risk_per_trade = float(settings['max_risk_per_trade'])
                
            if 'max_daily_loss' in settings:
                account.max_daily_loss = float(settings['max_daily_loss'])
            
            account.updated_at = datetime.now(timezone.utc)
            
            logger.info(f"✅ Account settings updated for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating account settings: {e}")
            return False
    
    async def validate_trade(self, user_id: int, trade_amount: float) -> Dict[str, Any]:
        """
        Validate if trade can be executed
        
        Returns:
            Dictionary with validation result and details
        """
        try:
            account = self.accounts.get(user_id)
            if not account:
                return {"valid": False, "reason": "Account not found"}
            
            # Check available margin
            if trade_amount > account.available_margin:
                return {
                    "valid": False, 
                    "reason": f"Insufficient margin. Available: ₹{account.available_margin:,.2f}, Required: ₹{trade_amount:,.2f}"
                }
            
            # Check max positions limit
            if account.positions_count >= account.max_positions:
                return {
                    "valid": False,
                    "reason": f"Maximum positions limit reached ({account.max_positions})"
                }
            
            # Check per-trade risk limit
            risk_amount = account.initial_capital * account.max_risk_per_trade
            if trade_amount > risk_amount:
                return {
                    "valid": False,
                    "reason": f"Trade exceeds risk limit. Max allowed: ₹{risk_amount:,.2f}"
                }
            
            # Check daily loss limit
            daily_loss_limit = account.initial_capital * account.max_daily_loss
            if abs(account.daily_pnl) > daily_loss_limit and account.daily_pnl < 0:
                return {
                    "valid": False,
                    "reason": f"Daily loss limit reached. Limit: ₹{daily_loss_limit:,.2f}"
                }
            
            return {
                "valid": True,
                "available_margin": account.available_margin,
                "risk_amount": risk_amount,
                "positions_used": account.positions_count,
                "max_positions": account.max_positions
            }
            
        except Exception as e:
            logger.error(f"❌ Error validating trade: {e}")
            return {"valid": False, "reason": "Validation error"}
    
    async def execute_paper_trade(self, user_id: int, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute paper trade (virtual execution)
        
        Args:
            trade_data: Complete trade information
        """
        try:
            account = self.accounts.get(user_id)
            if not account:
                return {"success": False, "error": "Account not found"}
            
            # Validate trade
            validation = await self.validate_trade(user_id, trade_data['invested_amount'])
            if not validation['valid']:
                return {"success": False, "error": validation['reason']}
            
            # Create position
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
                invested_amount=trade_data['invested_amount'],
                current_value=trade_data['invested_amount'],
                pnl=0.0,
                pnl_percentage=0.0,
                stop_loss=trade_data.get('stop_loss', 0.0),
                target=trade_data.get('target', 0.0),
                entry_time=datetime.now(timezone.utc)
            )
            
            # Update account
            account.used_margin += trade_data['invested_amount']
            account.available_margin -= trade_data['invested_amount']
            account.positions_count += 1
            account.updated_at = datetime.now(timezone.utc)
            
            # Add position
            if user_id not in self.positions:
                self.positions[user_id] = []
            self.positions[user_id].append(position)
            
            # Add to trade history
            if user_id not in self.trade_history:
                self.trade_history[user_id] = []
            self.trade_history[user_id].append({
                "action": "BUY",
                "position_id": position.position_id,
                "symbol": position.symbol,
                "price": position.entry_price,
                "quantity": position.quantity,
                "amount": position.invested_amount,
                "timestamp": position.entry_time.isoformat()
            })
            
            logger.info(f"✅ Paper trade executed: {position.symbol} {position.option_type} @ ₹{position.entry_price}")
            
            return {
                "success": True,
                "position_id": position.position_id,
                "message": "Trade executed successfully",
                "position": asdict(position)
            }
            
        except Exception as e:
            logger.error(f"❌ Error executing paper trade: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_position_price(self, user_id: int, instrument_key: str, current_price: float):
        """Update position with current market price"""
        try:
            if user_id not in self.positions:
                return
            
            account = self.accounts.get(user_id)
            if not account:
                return
            
            for position in self.positions[user_id]:
                if position.instrument_key == instrument_key and position.status == "ACTIVE":
                    position.current_price = current_price
                    position.current_value = current_price * position.quantity * position.lot_size
                    position.pnl = position.current_value - position.invested_amount
                    position.pnl_percentage = (position.pnl / position.invested_amount) * 100
            
            # Update account P&L
            await self._recalculate_account_pnl(user_id)
            
        except Exception as e:
            logger.error(f"❌ Error updating position price: {e}")
    
    async def _recalculate_account_pnl(self, user_id: int):
        """Recalculate total account P&L"""
        try:
            account = self.accounts.get(user_id)
            positions = self.positions.get(user_id, [])
            
            if not account:
                return
            
            total_pnl = sum(pos.pnl for pos in positions if pos.status == "ACTIVE")
            account.total_pnl = total_pnl
            # For demo, assuming daily_pnl = total_pnl (reset daily at market open)
            account.daily_pnl = total_pnl
            
            account.updated_at = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"❌ Error recalculating P&L: {e}")
    
    async def close_position(self, user_id: int, position_id: str, exit_price: float) -> Dict[str, Any]:
        """Close a paper trading position"""
        try:
            if user_id not in self.positions:
                return {"success": False, "error": "No positions found"}
            
            account = self.accounts.get(user_id)
            if not account:
                return {"success": False, "error": "Account not found"}
            
            # Find position
            position = None
            for pos in self.positions[user_id]:
                if pos.position_id == position_id and pos.status == "ACTIVE":
                    position = pos
                    break
            
            if not position:
                return {"success": False, "error": "Position not found"}
            
            # Calculate final P&L
            exit_value = exit_price * position.quantity * position.lot_size
            final_pnl = exit_value - position.invested_amount
            final_pnl_percentage = (final_pnl / position.invested_amount) * 100
            
            # Update position
            position.current_price = exit_price
            position.current_value = exit_value
            position.pnl = final_pnl
            position.pnl_percentage = final_pnl_percentage
            position.status = "CLOSED"
            
            # Update account
            account.used_margin -= position.invested_amount
            account.available_margin += exit_value  # Add exit value to available margin
            account.current_balance = account.current_balance - position.invested_amount + exit_value
            account.positions_count -= 1
            account.updated_at = datetime.now(timezone.utc)
            
            # Add to trade history
            self.trade_history[user_id].append({
                "action": "SELL",
                "position_id": position.position_id,
                "symbol": position.symbol,
                "price": exit_price,
                "quantity": position.quantity,
                "amount": exit_value,
                "pnl": final_pnl,
                "pnl_percentage": final_pnl_percentage,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            await self._recalculate_account_pnl(user_id)
            
            logger.info(f"✅ Position closed: {position.symbol} P&L: ₹{final_pnl:,.2f} ({final_pnl_percentage:.2f}%)")
            
            return {
                "success": True,
                "final_pnl": final_pnl,
                "pnl_percentage": final_pnl_percentage,
                "exit_value": exit_value,
                "message": "Position closed successfully"
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