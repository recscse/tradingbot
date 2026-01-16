"""
Trade Performance Analytics Service
Comprehensive analytics for trade performance tracking with date-wise breakdowns

Features:
- Daily, Weekly, Monthly, 6-Month, 1-Year, Overall performance
- Win ratio, profit factor, Sharpe ratio, maximum drawdown
- Average profit/loss per trade
- Detailed trade-by-trade analysis
"""

import logging
from datetime import datetime, date, timedelta, timezone as dt_timezone
from typing import Dict, List, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_

from database.models import AutoTradeExecution, User

logger = logging.getLogger(__name__)


# IST timezone constant
IST = dt_timezone(timedelta(hours=5, minutes=30))


@dataclass
class PerformanceMetrics:
    """
    Performance metrics structure

    Attributes:
        total_trades: Total number of trades
        winning_trades: Number of profitable trades
        losing_trades: Number of losing trades
        breakeven_trades: Number of breakeven trades
        win_rate: Win ratio percentage (winning_trades / total_trades)
        profit_factor: Gross profit / Gross loss
        average_profit: Average profit per winning trade
        average_loss: Average loss per losing trade
        largest_win: Largest single winning trade
        largest_loss: Largest single losing trade
        max_drawdown: Maximum drawdown from peak
        sharpe_ratio: Sharpe ratio (risk-adjusted returns)
        total_pnl: Total profit/loss
        gross_profit: Sum of all winning trades
        gross_loss: Sum of all losing trades
        average_trade_duration_minutes: Average holding period
        total_investment: Total capital invested
        roi_percent: Return on investment percentage
    """
    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    win_rate: float
    profit_factor: float
    average_profit: float
    average_loss: float
    largest_win: float
    largest_loss: float
    max_drawdown: float
    sharpe_ratio: float
    total_pnl: float
    gross_profit: float
    gross_loss: float
    average_trade_duration_minutes: int
    total_investment: float
    roi_percent: float
    expectancy: float


class TradeAnalyticsService:
    """
    Comprehensive trade analytics service

    Provides detailed performance tracking across multiple time periods:
    - Daily: Today's performance
    - Weekly: Last 7 days
    - Monthly: Last 30 days
    - 6-Month: Last 180 days
    - 1-Year: Last 365 days
    - Overall: All-time performance
    """

    def __init__(self):
        """Initialize trade analytics service"""
        logger.info("Trade Analytics Service initialized")

    def _get_ist_now(self) -> datetime:
        """Get current time in IST timezone"""
        return datetime.now(IST)

    def _to_ist(self, dt: datetime) -> datetime:
        """Convert datetime to IST timezone"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            # Assume UTC if no timezone info
            dt = dt.replace(tzinfo=dt_timezone.utc)
        return dt.astimezone(IST)

    def get_daily_performance(
        self,
        user_id: int,
        db: Session,
        target_date: Optional[date] = None,
        trading_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get daily performance metrics

        Args:
            user_id: User identifier
            db: Database session
            target_date: Target date (default: today)
            trading_mode: Trading mode filter (paper/live)

        Returns:
            Dictionary with daily performance metrics
        """
        try:
            if target_date is None:
                target_date = self._get_ist_now().date()

            # Base query
            query = db.query(AutoTradeExecution).filter(
                and_(
                    AutoTradeExecution.user_id == user_id,
                    AutoTradeExecution.status == "CLOSED",
                    func.date(AutoTradeExecution.exit_time) == target_date
                )
            )

            # Apply trading mode filter if provided
            if trading_mode:
                query = query.filter(AutoTradeExecution.trading_mode == trading_mode)

            trades = query.all()

            if not trades:
                return self._empty_performance("daily", target_date)

            metrics = self._calculate_metrics(trades)

            return {
                "success": True,
                "period": "daily",
                "date": target_date.isoformat(),
                "metrics": asdict(metrics),
                "trades_detail": self._format_trades_detail(trades)
            }

        except Exception as e:
            logger.error(f"Error getting daily performance: {e}")
            return {"success": False, "error": str(e)}

    def get_weekly_performance(
        self,
        user_id: int,
        db: Session,
        trading_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get weekly performance metrics (last 7 days)

        Args:
            user_id: User identifier
            db: Database session
            trading_mode: Trading mode filter (paper/live)

        Returns:
            Dictionary with weekly performance metrics
        """
        try:
            now_ist = self._get_ist_now()
            week_ago = now_ist - timedelta(days=7)

            query = db.query(AutoTradeExecution).filter(
                and_(
                    AutoTradeExecution.user_id == user_id,
                    AutoTradeExecution.status == "CLOSED",
                    AutoTradeExecution.exit_time >= week_ago
                )
            )

            if trading_mode:
                query = query.filter(AutoTradeExecution.trading_mode == trading_mode)

            trades = query.all()

            if not trades:
                return self._empty_performance("weekly", now_ist.date())

            metrics = self._calculate_metrics(trades)

            # Group by day
            daily_breakdown = self._get_daily_breakdown(trades, 7)

            return {
                "success": True,
                "period": "weekly",
                "start_date": week_ago.date().isoformat(),
                "end_date": now_ist.date().isoformat(),
                "metrics": asdict(metrics),
                "daily_breakdown": daily_breakdown
            }

        except Exception as e:
            logger.error(f"Error getting weekly performance: {e}")
            return {"success": False, "error": str(e)}

    def get_monthly_performance(
        self,
        user_id: int,
        db: Session,
        trading_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get monthly performance metrics (last 30 days)

        Args:
            user_id: User identifier
            db: Database session
            trading_mode: Trading mode filter (paper/live)

        Returns:
            Dictionary with monthly performance metrics
        """
        try:
            now_ist = self._get_ist_now()
            month_ago = now_ist - timedelta(days=30)

            query = db.query(AutoTradeExecution).filter(
                and_(
                    AutoTradeExecution.user_id == user_id,
                    AutoTradeExecution.status == "CLOSED",
                    AutoTradeExecution.exit_time >= month_ago
                )
            )

            if trading_mode:
                query = query.filter(AutoTradeExecution.trading_mode == trading_mode)

            trades = query.all()

            if not trades:
                return self._empty_performance("monthly", now_ist.date())

            metrics = self._calculate_metrics(trades)

            # Group by day
            daily_breakdown = self._get_daily_breakdown(trades, 30)

            return {
                "success": True,
                "period": "monthly",
                "start_date": month_ago.date().isoformat(),
                "end_date": now_ist.date().isoformat(),
                "metrics": asdict(metrics),
                "daily_breakdown": daily_breakdown
            }

        except Exception as e:
            logger.error(f"Error getting monthly performance: {e}")
            return {"success": False, "error": str(e)}

    def get_six_month_performance(
        self,
        user_id: int,
        db: Session,
        trading_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get 6-month performance metrics (last 180 days)

        Args:
            user_id: User identifier
            db: Database session
            trading_mode: Trading mode filter (paper/live)

        Returns:
            Dictionary with 6-month performance metrics
        """
        try:
            now_ist = self._get_ist_now()
            six_months_ago = now_ist - timedelta(days=180)

            query = db.query(AutoTradeExecution).filter(
                and_(
                    AutoTradeExecution.user_id == user_id,
                    AutoTradeExecution.status == "CLOSED",
                    AutoTradeExecution.exit_time >= six_months_ago
                )
            )

            if trading_mode:
                query = query.filter(AutoTradeExecution.trading_mode == trading_mode)

            trades = query.all()

            if not trades:
                return self._empty_performance("6-month", now_ist.date())

            metrics = self._calculate_metrics(trades)

            # Group by week
            weekly_breakdown = self._get_weekly_breakdown(trades)

            return {
                "success": True,
                "period": "6-month",
                "start_date": six_months_ago.date().isoformat(),
                "end_date": now_ist.date().isoformat(),
                "metrics": asdict(metrics),
                "weekly_breakdown": weekly_breakdown
            }

        except Exception as e:
            logger.error(f"Error getting 6-month performance: {e}")
            return {"success": False, "error": str(e)}

    def get_yearly_performance(
        self,
        user_id: int,
        db: Session,
        trading_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get 1-year performance metrics (last 365 days)

        Args:
            user_id: User identifier
            db: Database session
            trading_mode: Trading mode filter (paper/live)

        Returns:
            Dictionary with 1-year performance metrics
        """
        try:
            now_ist = self._get_ist_now()
            year_ago = now_ist - timedelta(days=365)

            query = db.query(AutoTradeExecution).filter(
                and_(
                    AutoTradeExecution.user_id == user_id,
                    AutoTradeExecution.status == "CLOSED",
                    AutoTradeExecution.exit_time >= year_ago
                )
            )

            if trading_mode:
                query = query.filter(AutoTradeExecution.trading_mode == trading_mode)

            trades = query.all()

            if not trades:
                return self._empty_performance("yearly", now_ist.date())

            metrics = self._calculate_metrics(trades)

            # Group by month
            monthly_breakdown = self._get_monthly_breakdown(trades)

            return {
                "success": True,
                "period": "yearly",
                "start_date": year_ago.date().isoformat(),
                "end_date": now_ist.date().isoformat(),
                "metrics": asdict(metrics),
                "monthly_breakdown": monthly_breakdown
            }

        except Exception as e:
            logger.error(f"Error getting yearly performance: {e}")
            return {"success": False, "error": str(e)}

    def get_overall_performance(
        self,
        user_id: int,
        db: Session,
        trading_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get overall all-time performance metrics

        Args:
            user_id: User identifier
            db: Database session
            trading_mode: Trading mode filter (paper/live)

        Returns:
            Dictionary with overall performance metrics
        """
        try:
            query = db.query(AutoTradeExecution).filter(
                and_(
                    AutoTradeExecution.user_id == user_id,
                    AutoTradeExecution.status == "CLOSED"
                )
            )

            if trading_mode:
                query = query.filter(AutoTradeExecution.trading_mode == trading_mode)

            trades = query.all()

            if not trades:
                return self._empty_performance("overall", self._get_ist_now().date())

            metrics = self._calculate_metrics(trades)

            # Get first and last trade dates
            first_trade = min(trades, key=lambda t: t.entry_time)
            last_trade = max(trades, key=lambda t: t.exit_time)

            return {
                "success": True,
                "period": "overall",
                "start_date": self._to_ist(first_trade.entry_time).date().isoformat(),
                "end_date": self._to_ist(last_trade.exit_time).date().isoformat(),
                "metrics": asdict(metrics),
                "trades_summary": {
                    "total_trades": len(trades),
                    "symbols_traded": list(set(t.symbol for t in trades)),
                    "strategies_used": list(set(t.strategy_name for t in trades))
                }
            }

        except Exception as e:
            logger.error(f"Error getting overall performance: {e}")
            return {"success": False, "error": str(e)}

    def get_detailed_performance(
        self,
        user_id: int,
        db: Session,
        limit: int = 100,
        trading_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get detailed trade-by-trade analysis

        Args:
            user_id: User identifier
            db: Database session
            limit: Maximum number of trades to return
            trading_mode: Trading mode filter (paper/live)

        Returns:
            Dictionary with detailed trade information
        """
        try:
            query = db.query(AutoTradeExecution).filter(
                and_(
                    AutoTradeExecution.user_id == user_id,
                    AutoTradeExecution.status == "CLOSED"
                )
            )

            # Apply trading mode filter if provided
            if trading_mode:
                query = query.filter(AutoTradeExecution.trading_mode == trading_mode)

            trades = query.order_by(AutoTradeExecution.exit_time.desc()).limit(limit).all()

            if not trades:
                return {
                    "success": True,
                    "trades": [],
                    "total_trades": 0
                }

            detailed_trades = []

            for trade in trades:
                entry_time_ist = self._to_ist(trade.entry_time)
                exit_time_ist = self._to_ist(trade.exit_time) if trade.exit_time else None

                # Calculate duration
                duration_minutes = 0
                if trade.entry_time and trade.exit_time:
                    duration_minutes = int((trade.exit_time - trade.entry_time).total_seconds() / 60)

                # Calculate total investment
                total_investment = float(trade.total_investment) if trade.total_investment else (float(trade.entry_price) * trade.quantity)

                detailed_trades.append({
                    "trade_id": trade.trade_id,
                    "symbol": trade.symbol,
                    "signal_type": trade.signal_type,
                    "strategy": trade.strategy_name,
                    "entry_time": entry_time_ist.isoformat() if entry_time_ist else None,
                    "exit_time": exit_time_ist.isoformat() if exit_time_ist else None,
                    "entry_price": float(trade.entry_price),
                    "exit_price": float(trade.exit_price) if trade.exit_price else 0,
                    "quantity": trade.quantity,
                    "lot_size": trade.lot_size,
                    "total_investment": total_investment,
                    "gross_pnl": float(trade.gross_pnl) if trade.gross_pnl else 0,
                    "net_pnl": float(trade.net_pnl) if trade.net_pnl else 0,
                    "pnl_percentage": float(trade.pnl_percentage) if trade.pnl_percentage else 0,
                    "exit_reason": trade.exit_reason,
                    "duration_minutes": duration_minutes,
                    "broker_name": trade.broker_name or "N/A",
                    "trading_mode": trade.trading_mode or "paper"
                })

            return {
                "success": True,
                "trades": detailed_trades,
                "total_trades": len(detailed_trades)
            }

        except Exception as e:
            logger.error(f"Error getting detailed performance: {e}")
            return {"success": False, "error": str(e)}

    def get_system_health_analytics(
        self,
        user_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Get system health and operational analytics

        Args:
            user_id: User identifier
            db: Database session

        Returns:
            Dictionary with system health metrics
        """
        try:
            # Get all trades for latency analysis
            trades = db.query(AutoTradeExecution).filter(
                AutoTradeExecution.user_id == user_id
            ).all()

            if not trades:
                return {
                    "success": True,
                    "latency_metrics": {"avg_signal_latency": 0, "avg_execution_latency": 0},
                    "hourly_distribution": [],
                    "broker_performance": []
                }

            # 1. Latency Analysis
            signal_latencies = [t.signal_generation_latency_ms for t in trades if t.signal_generation_latency_ms is not None]
            exec_latencies = [t.order_execution_latency_ms for t in trades if t.order_execution_latency_ms is not None]

            avg_signal_latency = sum(signal_latencies) / len(signal_latencies) if signal_latencies else 0
            avg_exec_latency = sum(exec_latencies) / len(exec_latencies) if exec_latencies else 0

            # 2. Hourly Distribution
            hourly_stats = {}
            for trade in trades:
                if not trade.entry_time:
                    continue
                
                # Convert to IST for correct hourly bucketing
                entry_time_ist = self._to_ist(trade.entry_time)
                hour = entry_time_ist.hour
                
                if hour not in hourly_stats:
                    hourly_stats[hour] = {"hour": f"{hour:02d}:00", "trades": 0, "wins": 0, "pnl": 0.0}
                
                hourly_stats[hour]["trades"] += 1
                if trade.net_pnl:
                    hourly_stats[hour]["pnl"] += float(trade.net_pnl)
                    if trade.net_pnl > 0:
                        hourly_stats[hour]["wins"] += 1

            hourly_distribution = sorted(hourly_stats.values(), key=lambda x: x["hour"])

            # 3. Broker Performance
            broker_stats = {}
            for trade in trades:
                broker = trade.broker_name or "Unknown"
                if broker not in broker_stats:
                    broker_stats[broker] = {"broker": broker, "trades": 0, "pnl": 0.0}
                
                broker_stats[broker]["trades"] += 1
                if trade.net_pnl:
                    broker_stats[broker]["pnl"] += float(trade.net_pnl)

            broker_performance = list(broker_stats.values())

            return {
                "success": True,
                "latency_metrics": {
                    "avg_signal_latency_ms": round(avg_signal_latency, 2),
                    "avg_execution_latency_ms": round(avg_exec_latency, 2),
                    "total_trades_analyzed": len(trades)
                },
                "hourly_distribution": hourly_distribution,
                "broker_performance": broker_performance
            }

        except Exception as e:
            logger.error(f"Error getting system health analytics: {e}")
            return {"success": False, "error": str(e)}

    def _calculate_metrics(self, trades: List[AutoTradeExecution]) -> PerformanceMetrics:
        """
        Calculate performance metrics from list of trades

        Args:
            trades: List of closed trade executions

        Returns:
            PerformanceMetrics object with all calculated metrics
        """
        try:
            if not trades:
                return self._empty_metrics()

            total_trades = len(trades)

            # Categorize trades
            winning_trades = [t for t in trades if t.net_pnl and t.net_pnl > 0]
            losing_trades = [t for t in trades if t.net_pnl and t.net_pnl < 0]
            breakeven_trades = [t for t in trades if t.net_pnl == 0]

            # Calculate basic metrics
            win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0

            # Calculate P&L metrics
            gross_profit = sum(Decimal(str(t.net_pnl)) for t in winning_trades)
            gross_loss = abs(sum(Decimal(str(t.net_pnl)) for t in losing_trades))
            total_pnl = gross_profit - gross_loss

            # Profit factor
            profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else float(gross_profit) if gross_profit > 0 else 0

            # Average profit and loss
            average_profit = float(gross_profit / len(winning_trades)) if winning_trades else 0.0
            average_loss = float(gross_loss / len(losing_trades)) if losing_trades else 0.0

            # Calculate Expectancy
            # Expectancy = (Win Rate * Average Win) - (Loss Rate * Average Loss)
            win_rate_decimal = win_rate / 100.0
            loss_rate_decimal = 1.0 - win_rate_decimal
            expectancy = (win_rate_decimal * average_profit) - (loss_rate_decimal * average_loss)

            # Largest win and loss
            largest_win = max((float(t.net_pnl) for t in winning_trades), default=0.0)
            largest_loss = abs(min((float(t.net_pnl) for t in losing_trades), default=0.0))

            # Calculate maximum drawdown
            max_drawdown = self._calculate_max_drawdown(trades)

            # Calculate Sharpe ratio
            sharpe_ratio = self._calculate_sharpe_ratio(trades)

            # Average trade duration
            durations = []
            for trade in trades:
                if trade.entry_time and trade.exit_time:
                    duration = (trade.exit_time - trade.entry_time).total_seconds() / 60
                    durations.append(duration)

            average_duration = int(sum(durations) / len(durations)) if durations else 0

            # Total investment
            total_investment = Decimal('0')
            for trade in trades:
                if trade.total_investment:
                    total_investment += Decimal(str(trade.total_investment))
                else:
                    total_investment += Decimal(str(trade.entry_price)) * Decimal(str(trade.quantity))

            # ROI percentage
            roi_percent = float((total_pnl / total_investment * Decimal('100')) if total_investment > 0 else Decimal('0'))

            return PerformanceMetrics(
                total_trades=total_trades,
                winning_trades=len(winning_trades),
                losing_trades=len(losing_trades),
                breakeven_trades=len(breakeven_trades),
                win_rate=win_rate,
                profit_factor=profit_factor,
                average_profit=average_profit,
                average_loss=average_loss,
                largest_win=largest_win,
                largest_loss=largest_loss,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                total_pnl=float(total_pnl),
                gross_profit=float(gross_profit),
                gross_loss=float(gross_loss),
                average_trade_duration_minutes=average_duration,
                total_investment=float(total_investment),
                roi_percent=roi_percent,
                expectancy=float(expectancy)
            )

        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return self._empty_metrics()

    def _calculate_max_drawdown(self, trades: List[AutoTradeExecution]) -> float:
        """
        Calculate maximum drawdown from peak equity

        Args:
            trades: List of trades sorted by exit time

        Returns:
            Maximum drawdown as positive number
        """
        try:
            if not trades:
                return 0.0

            # Sort trades by exit time
            sorted_trades = sorted(trades, key=lambda t: t.exit_time if t.exit_time else datetime.min)

            # Calculate running P&L
            running_pnl = Decimal('0')
            peak_pnl = Decimal('0')
            max_drawdown = Decimal('0')

            for trade in sorted_trades:
                if trade.net_pnl:
                    running_pnl += Decimal(str(trade.net_pnl))

                    # Update peak
                    if running_pnl > peak_pnl:
                        peak_pnl = running_pnl

                    # Calculate drawdown from peak
                    drawdown = peak_pnl - running_pnl

                    # Update max drawdown
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown

            return float(max_drawdown)

        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0.0

    def _calculate_sharpe_ratio(self, trades: List[AutoTradeExecution]) -> float:
        """
        Calculate Sharpe ratio (risk-adjusted returns)

        Args:
            trades: List of trades

        Returns:
            Sharpe ratio
        """
        try:
            if len(trades) < 2:
                return 0.0

            # Calculate returns for each trade
            returns = []
            for trade in trades:
                if trade.net_pnl and trade.total_investment:
                    trade_return = float(trade.net_pnl) / float(trade.total_investment)
                    returns.append(trade_return)
                elif trade.net_pnl and trade.entry_price and trade.quantity:
                    investment = float(trade.entry_price) * trade.quantity
                    trade_return = float(trade.net_pnl) / investment
                    returns.append(trade_return)

            if not returns:
                return 0.0

            # Calculate average return
            avg_return = sum(returns) / len(returns)

            # Calculate standard deviation
            variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
            std_dev = variance ** 0.5

            if std_dev == 0:
                return 0.0

            # Risk-free rate (assume 6% annually = ~0.016% per trade)
            risk_free_rate = 0.00016

            # Sharpe ratio
            sharpe = (avg_return - risk_free_rate) / std_dev

            return round(sharpe, 4)

        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0.0

    def _get_daily_breakdown(self, trades: List[AutoTradeExecution], days: int) -> List[Dict[str, Any]]:
        """Get daily breakdown of trades"""
        try:
            daily_data = {}

            for trade in trades:
                if not trade.exit_time:
                    continue

                trade_date = self._to_ist(trade.exit_time).date()

                if trade_date not in daily_data:
                    daily_data[trade_date] = []

                daily_data[trade_date].append(trade)

            breakdown = []
            for trade_date, day_trades in sorted(daily_data.items()):
                day_metrics = self._calculate_metrics(day_trades)
                breakdown.append({
                    "date": trade_date.isoformat(),
                    "trades_count": len(day_trades),
                    "pnl": day_metrics.total_pnl,
                    "win_rate": day_metrics.win_rate
                })

            return breakdown

        except Exception as e:
            logger.error(f"Error getting daily breakdown: {e}")
            return []

    def _get_weekly_breakdown(self, trades: List[AutoTradeExecution]) -> List[Dict[str, Any]]:
        """Get weekly breakdown of trades"""
        try:
            weekly_data = {}

            for trade in trades:
                if not trade.exit_time:
                    continue

                trade_date = self._to_ist(trade.exit_time).date()
                week_start = trade_date - timedelta(days=trade_date.weekday())

                if week_start not in weekly_data:
                    weekly_data[week_start] = []

                weekly_data[week_start].append(trade)

            breakdown = []
            for week_start, week_trades in sorted(weekly_data.items()):
                week_metrics = self._calculate_metrics(week_trades)
                breakdown.append({
                    "week_start": week_start.isoformat(),
                    "trades_count": len(week_trades),
                    "pnl": week_metrics.total_pnl,
                    "win_rate": week_metrics.win_rate
                })

            return breakdown

        except Exception as e:
            logger.error(f"Error getting weekly breakdown: {e}")
            return []

    def _get_monthly_breakdown(self, trades: List[AutoTradeExecution]) -> List[Dict[str, Any]]:
        """Get monthly breakdown of trades"""
        try:
            monthly_data = {}

            for trade in trades:
                if not trade.exit_time:
                    continue

                trade_date = self._to_ist(trade.exit_time).date()
                month_key = (trade_date.year, trade_date.month)

                if month_key not in monthly_data:
                    monthly_data[month_key] = []

                monthly_data[month_key].append(trade)

            breakdown = []
            for (year, month), month_trades in sorted(monthly_data.items()):
                month_metrics = self._calculate_metrics(month_trades)
                breakdown.append({
                    "month": f"{year}-{month:02d}",
                    "trades_count": len(month_trades),
                    "pnl": month_metrics.total_pnl,
                    "win_rate": month_metrics.win_rate
                })

            return breakdown

        except Exception as e:
            logger.error(f"Error getting monthly breakdown: {e}")
            return []

    def _format_trades_detail(self, trades: List[AutoTradeExecution]) -> List[Dict[str, Any]]:
        """Format trades for detailed view"""
        try:
            formatted = []

            for trade in trades:
                entry_time_ist = self._to_ist(trade.entry_time)
                exit_time_ist = self._to_ist(trade.exit_time) if trade.exit_time else None

                formatted.append({
                    "trade_id": trade.trade_id,
                    "symbol": trade.symbol,
                    "signal_type": trade.signal_type,
                    "entry_time": entry_time_ist.isoformat() if entry_time_ist else None,
                    "exit_time": exit_time_ist.isoformat() if exit_time_ist else None,
                    "net_pnl": float(trade.net_pnl) if trade.net_pnl else 0,
                    "pnl_percentage": float(trade.pnl_percentage) if trade.pnl_percentage else 0,
                    "exit_reason": trade.exit_reason
                })

            return formatted

        except Exception as e:
            logger.error(f"Error formatting trades: {e}")
            return []

    def _empty_performance(self, period: str, target_date: date) -> Dict[str, Any]:
        """Return empty performance structure"""
        return {
            "success": True,
            "period": period,
            "date": target_date.isoformat(),
            "metrics": asdict(self._empty_metrics()),
            "message": "No closed trades found for this period"
        }

    def _empty_metrics(self) -> PerformanceMetrics:
        """Return empty metrics structure"""
        return PerformanceMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            breakeven_trades=0,
            win_rate=0.0,
            profit_factor=0.0,
            average_profit=0.0,
            average_loss=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            total_pnl=0.0,
            gross_profit=0.0,
            gross_loss=0.0,
            average_trade_duration_minutes=0,
            total_investment=0.0,
            roi_percent=0.0,
            expectancy=0.0
        )


# Create singleton instance
trade_analytics_service = TradeAnalyticsService()
