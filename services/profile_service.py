from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from database.models import User, BrokerConfig, TradePerformance, UserCapital
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ProfileService:
    def __init__(self, db: Session):
        self.db = db

    async def get_complete_profile(self, user_id: int) -> Dict:
        """Get complete profile information including trading stats"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("User not found")

            # Get broker accounts
            broker_accounts = (
                self.db.query(BrokerConfig)
                .filter(BrokerConfig.user_id == user_id)
                .all()
            )

            # Get user capital info
            user_capital = (
                self.db.query(UserCapital)
                .filter(UserCapital.user_id == user_id)
                .first()
            )

            # Calculate total balance (placeholder - implement based on your broker integration)
            total_balance = user_capital.total_capital if user_capital else 0

            # Get today's P&L
            today = datetime.now().date()
            today_trades = (
                self.db.query(TradePerformance)
                .filter(
                    and_(
                        TradePerformance.user_id == user_id,
                        func.date(TradePerformance.trade_time) == today,
                        TradePerformance.status == "CLOSED",
                        TradePerformance.profit_loss.isnot(None),
                    )
                )
                .all()
            )

            today_pnl = (
                sum(trade.profit_loss for trade in today_trades) if today_trades else 0
            )

            return {
                "avatar_url": None,  # Implement avatar storage
                "total_balance": float(total_balance),
                "today_pnl": float(today_pnl),
                "broker_accounts": [
                    {
                        "id": broker.id,
                        "broker_name": broker.broker_name,
                        "is_active": broker.is_active,
                        "created_at": (
                            broker.created_at.isoformat() if broker.created_at else None
                        ),
                    }
                    for broker in broker_accounts
                ],
            }
        except Exception as e:
            logger.error(f"Error getting complete profile: {e}")
            return {
                "avatar_url": None,
                "total_balance": 0,
                "today_pnl": 0,
                "broker_accounts": [],
            }

    async def get_trading_statistics(self, user_id: int) -> Dict:
        """Get comprehensive trading statistics"""
        try:
            # Get all trades
            all_trades = (
                self.db.query(TradePerformance)
                .filter(TradePerformance.user_id == user_id)
                .all()
            )

            # Get closed trades for calculations
            closed_trades = [
                trade
                for trade in all_trades
                if trade.status == "CLOSED" and trade.profit_loss is not None
            ]

            if not closed_trades:
                return self._get_empty_stats()

            # Calculate basic metrics
            total_trades = len(all_trades)
            total_pnl = sum(trade.profit_loss for trade in closed_trades)
            profitable_trades = [
                trade for trade in closed_trades if trade.profit_loss > 0
            ]
            win_rate = (
                (len(profitable_trades) / len(closed_trades)) * 100
                if closed_trades
                else 0
            )

            # Calculate average profit per trade
            avg_profit_per_trade = (
                total_pnl / len(closed_trades) if closed_trades else 0
            )

            # Get active positions
            active_positions = len(
                [trade for trade in all_trades if trade.status == "OPEN"]
            )

            # Get recent trades
            recent_trades = sorted(
                all_trades, key=lambda x: x.trade_time, reverse=True
            )[:10]

            # Best performing stock
            stock_performance = {}
            for trade in closed_trades:
                if trade.symbol not in stock_performance:
                    stock_performance[trade.symbol] = 0
                stock_performance[trade.symbol] += trade.profit_loss

            best_stock = (
                max(stock_performance.items(), key=lambda x: x[1])[0]
                if stock_performance
                else "N/A"
            )

            # Last trade date
            last_trade_date = recent_trades[0].trade_time if recent_trades else None

            return {
                "total_trades": total_trades,
                "successful_trades": len(profitable_trades),
                "total_pnl": float(total_pnl),
                "win_rate": float(win_rate),
                "best_performing_stock": best_stock,
                "last_trade_date": (
                    last_trade_date.isoformat() if last_trade_date else None
                ),
                "totalPnL": float(total_pnl),
                "totalPnLChange": 0,  # Calculate based on previous period
                "winRate": float(win_rate),
                "winRateChange": 0,
                "totalTrades": total_trades,
                "totalTradesChange": 0,
                "activePositions": active_positions,
                "activePositionsChange": 0,
                "avgProfitPerTrade": float(avg_profit_per_trade),
                "recentTrades": [
                    {
                        "date": trade.trade_time.isoformat(),
                        "symbol": trade.symbol,
                        "type": trade.trade_type,
                        "quantity": trade.quantity,
                        "pnl": float(trade.profit_loss) if trade.profit_loss else 0,
                        "status": trade.status,
                    }
                    for trade in recent_trades
                ],
                "recentActivity": [
                    {
                        "description": f"{trade.trade_type} {trade.symbol} - {trade.quantity} shares",
                        "timestamp": trade.trade_time.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    for trade in recent_trades[:5]
                ],
            }
        except Exception as e:
            logger.error(f"Error getting trading statistics: {e}")
            return self._get_empty_stats()

    def _get_empty_stats(self) -> Dict:
        """Return empty statistics structure"""
        return {
            "total_trades": 0,
            "successful_trades": 0,
            "total_pnl": 0,
            "win_rate": 0,
            "best_performing_stock": "N/A",
            "last_trade_date": None,
            "totalPnL": 0,
            "totalPnLChange": 0,
            "winRate": 0,
            "winRateChange": 0,
            "totalTrades": 0,
            "totalTradesChange": 0,
            "activePositions": 0,
            "activePositionsChange": 0,
            "avgProfitPerTrade": 0,
            "recentTrades": [],
            "recentActivity": [],
        }
