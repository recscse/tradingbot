from datetime import datetime, date
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from database.models import AutoTradingSession, DailyTradingReport, TradeExecution, User
import logging

logger = logging.getLogger(__name__)


class AutoTradingService:
    def __init__(self, db: Session):
        self.db = db

    async def create_trading_session(
        self,
        user_id: int,
        selected_stocks: List[Dict],
        screening_config: Dict = None,
        session_type: str = "AUTO_PAPER_TRADING",
        start_capital: float = 100000.0,
    ) -> AutoTradingSession:
        """Create a new auto trading session"""

        session = AutoTradingSession(
            user_id=user_id,
            session_date=date.today(),
            selected_stocks=selected_stocks,
            screening_config=screening_config,
            stocks_screened=len(selected_stocks),
            session_type=session_type,
            trading_mode="paper",  # Default to paper trading
            status="ACTIVE",
            start_capital=start_capital,
            end_capital=start_capital,
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        logger.info(f"Created auto trading session {session.id} for user {user_id}")
        return session

    async def execute_trade(
        self,
        session_id: int,
        symbol: str,
        trade_type: str,
        entry_price: float,
        quantity: int,
        confidence_score: float = None,
        technical_indicators: Dict = None,
    ) -> TradeExecution:
        """Execute a trade within a trading session"""

        session = (
            self.db.query(AutoTradingSession)
            .filter(AutoTradingSession.id == session_id)
            .first()
        )

        if not session:
            raise ValueError(f"Trading session {session_id} not found")

        trade = TradeExecution(
            user_id=session.user_id,
            session_id=session_id,
            symbol=symbol,
            trade_type=trade_type,
            entry_price=entry_price,
            quantity=quantity,
            confidence_score=confidence_score,
            technical_indicators=technical_indicators,
            status="OPEN",
        )

        self.db.add(trade)

        # Update session stats
        session.total_trades += 1

        self.db.commit()
        self.db.refresh(trade)

        logger.info(f"Executed {trade_type} trade for {symbol} in session {session_id}")
        return trade

    async def close_trade(
        self, trade_id: int, exit_price: float, exit_reason: str = "MANUAL"
    ) -> TradeExecution:
        """Close an open trade"""

        trade = (
            self.db.query(TradeExecution)
            .filter(TradeExecution.id == trade_id, TradeExecution.status == "OPEN")
            .first()
        )

        if not trade:
            raise ValueError(f"Open trade {trade_id} not found")

        # Calculate P&L
        if trade.trade_type == "BUY":
            pnl = (exit_price - trade.entry_price) * trade.quantity
        else:  # SELL
            pnl = (trade.entry_price - exit_price) * trade.quantity

        pnl_percentage = (pnl / (trade.entry_price * trade.quantity)) * 100

        # Update trade
        trade.exit_price = exit_price
        trade.exit_time = datetime.now()
        trade.pnl = pnl
        trade.pnl_percentage = pnl_percentage
        trade.status = "CLOSED"
        trade.exit_reason = exit_reason

        # Update session stats
        session = (
            self.db.query(AutoTradingSession)
            .filter(AutoTradingSession.id == trade.session_id)
            .first()
        )

        if session:
            if pnl > 0:
                session.successful_trades += 1
            else:
                session.failed_trades += 1

            session.session_pnl += pnl
            session.end_capital = session.start_capital + session.session_pnl

        self.db.commit()
        self.db.refresh(trade)

        logger.info(f"Closed trade {trade_id} with P&L: {pnl:.2f}")
        return trade

    async def generate_daily_report(
        self, user_id: int, report_date: date = None
    ) -> DailyTradingReport:
        """Generate daily trading report"""

        if not report_date:
            report_date = date.today()

        # Get all trades for the day
        trades = (
            self.db.query(TradeExecution)
            .filter(
                TradeExecution.user_id == user_id,
                TradeExecution.entry_time >= report_date,
                TradeExecution.entry_time
                < report_date.replace(day=report_date.day + 1),
            )
            .all()
        )

        # Calculate metrics
        total_trades = len(trades)
        closed_trades = [t for t in trades if t.status == "CLOSED"]
        winning_trades = len([t for t in closed_trades if t.pnl > 0])
        losing_trades = len([t for t in closed_trades if t.pnl <= 0])

        daily_pnl = sum([t.pnl for t in closed_trades if t.pnl])
        win_rate = (winning_trades / len(closed_trades)) * 100 if closed_trades else 0

        best_trade_pnl = max([t.pnl for t in closed_trades if t.pnl], default=0)
        worst_trade_pnl = min([t.pnl for t in closed_trades if t.pnl], default=0)

        # Get selected stocks
        session = (
            self.db.query(AutoTradingSession)
            .filter(
                AutoTradingSession.user_id == user_id,
                AutoTradingSession.session_date == report_date,
            )
            .first()
        )

        selected_stocks = session.selected_stocks if session else []

        # Create or update report
        existing_report = (
            self.db.query(DailyTradingReport)
            .filter(
                DailyTradingReport.user_id == user_id,
                DailyTradingReport.report_date == report_date,
            )
            .first()
        )

        if existing_report:
            report = existing_report
        else:
            report = DailyTradingReport(
                user_id=user_id,
                session_id=session.id if session else None,
                report_date=report_date,
                stocks_selected=selected_stocks,
            )
            self.db.add(report)

        # Update report data
        report.trades_executed = total_trades
        report.daily_pnl = daily_pnl
        report.winning_trades = winning_trades
        report.losing_trades = losing_trades
        report.win_rate = win_rate
        report.best_trade_pnl = best_trade_pnl
        report.worst_trade_pnl = worst_trade_pnl

        self.db.commit()
        self.db.refresh(report)

        logger.info(f"Generated daily report for user {user_id} on {report_date}")
        return report

    async def get_active_session(self, user_id: int) -> Optional[AutoTradingSession]:
        """Get active trading session for user"""
        return (
            self.db.query(AutoTradingSession)
            .filter(
                AutoTradingSession.user_id == user_id,
                AutoTradingSession.status == "ACTIVE",
            )
            .first()
        )

    async def end_session(self, session_id: int) -> AutoTradingSession:
        """End a trading session"""
        session = (
            self.db.query(AutoTradingSession)
            .filter(AutoTradingSession.id == session_id)
            .first()
        )

        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.status = "COMPLETED"
        session.completed_at = datetime.now()

        # Close any open trades
        open_trades = (
            self.db.query(TradeExecution)
            .filter(
                TradeExecution.session_id == session_id, TradeExecution.status == "OPEN"
            )
            .all()
        )

        for trade in open_trades:
            # For paper trading, we might close at current market price
            # This is a simplified implementation
            trade.status = "CANCELLED"
            trade.exit_reason = "SESSION_ENDED"
            trade.exit_time = datetime.now()

        self.db.commit()
        self.db.refresh(session)

        logger.info(f"Ended trading session {session_id}")
        return session
