import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import logging

from database.models import User, TradePerformance
from database.connection import get_db
from services.trading_services.paper_trading_engine import paper_trading_engine

logger = logging.getLogger(__name__)


class TradingAnalyticsService:
    def __init__(self):
        self.performance_cache = {}

    def calculate_comprehensive_metrics(self, user_id: int) -> Dict:
        """Calculate comprehensive trading metrics"""
        try:
            if user_id not in paper_trading_engine.user_portfolios:
                return {"error": "No trading data found"}

            portfolio = paper_trading_engine.user_portfolios[user_id]
            trades = portfolio["trade_history"]
            closed_trades = [
                t for t in trades if t["status"] == "CLOSED" and "pnl" in t
            ]

            if not closed_trades:
                return {"error": "No closed trades for analysis"}

            metrics = {}

            # Basic Metrics
            metrics["basic"] = self._calculate_basic_metrics(portfolio, closed_trades)

            # Performance Metrics
            metrics["performance"] = self._calculate_performance_metrics(
                portfolio, closed_trades
            )

            # Risk Metrics
            metrics["risk"] = self._calculate_risk_metrics(portfolio, closed_trades)

            # Strategy Metrics
            metrics["strategy"] = self._calculate_strategy_metrics(closed_trades)

            # Time-based Analysis
            metrics["time_analysis"] = self._calculate_time_analysis(closed_trades)

            # Win/Loss Analysis
            metrics["win_loss"] = self._calculate_win_loss_analysis(closed_trades)

            # Drawdown Analysis
            metrics["drawdown"] = self._calculate_drawdown_analysis(portfolio)

            return metrics

        except Exception as e:
            logger.error(f"Analytics calculation error: {e}")
            return {"error": str(e)}

    def _calculate_basic_metrics(self, portfolio: Dict, closed_trades: List) -> Dict:
        """Calculate basic trading metrics"""
        total_trades = len(closed_trades)
        winning_trades = len([t for t in closed_trades if t["pnl"] > 0])
        losing_trades = len([t for t in closed_trades if t["pnl"] < 0])

        total_pnl = sum([t["pnl"] for t in closed_trades])
        gross_profit = sum([t["pnl"] for t in closed_trades if t["pnl"] > 0])
        gross_loss = abs(sum([t["pnl"] for t in closed_trades if t["pnl"] < 0]))

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": (
                (winning_trades / total_trades * 100) if total_trades > 0 else 0
            ),
            "total_pnl": total_pnl,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "net_profit": gross_profit - gross_loss,
            "profit_factor": gross_profit / gross_loss if gross_loss > 0 else 0,
            "current_portfolio_value": portfolio.get("risk_metrics", {}).get(
                "current_value", 0
            ),
            "initial_balance": portfolio.get("initial_balance", 0),
        }

    def _calculate_performance_metrics(
        self, portfolio: Dict, closed_trades: List
    ) -> Dict:
        """Calculate performance metrics"""
        if not closed_trades:
            return {}

        pnl_values = [t["pnl"] for t in closed_trades]
        pnl_pcts = [t.get("pnl_pct", 0) for t in closed_trades]

        # Average metrics
        avg_win = (
            np.mean([pnl for pnl in pnl_values if pnl > 0])
            if any(pnl > 0 for pnl in pnl_values)
            else 0
        )
        avg_loss = (
            np.mean([pnl for pnl in pnl_values if pnl < 0])
            if any(pnl < 0 for pnl in pnl_values)
            else 0
        )

        # Best and worst
        best_trade = max(pnl_values)
        worst_trade = min(pnl_values)

        # Consecutive wins/losses
        consecutive_wins = self._calculate_consecutive_wins(closed_trades)
        consecutive_losses = self._calculate_consecutive_losses(closed_trades)

        # Return metrics
        total_return = sum(pnl_values)
        initial_balance = portfolio.get("initial_balance", 1000000)
        total_return_pct = (total_return / initial_balance) * 100

        # Average holding period
        holding_periods = [
            t.get("holding_period", timedelta()).total_seconds() / 3600
            for t in closed_trades
        ]
        avg_holding_hours = np.mean(holding_periods) if holding_periods else 0

        return {
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "avg_win_pct": (
                np.mean([pct for pct in pnl_pcts if pct > 0])
                if any(pct > 0 for pct in pnl_pcts)
                else 0
            ),
            "avg_loss_pct": (
                np.mean([pct for pct in pnl_pcts if pct < 0])
                if any(pct < 0 for pct in pnl_pcts)
                else 0
            ),
            "best_trade": best_trade,
            "worst_trade": worst_trade,
            "risk_reward_ratio": abs(avg_win / avg_loss) if avg_loss != 0 else 0,
            "expectancy": np.mean(pnl_values),
            "total_return": total_return,
            "total_return_pct": total_return_pct,
            "avg_holding_hours": avg_holding_hours,
            "max_consecutive_wins": consecutive_wins,
            "max_consecutive_losses": consecutive_losses,
        }

    def _calculate_risk_metrics(self, portfolio: Dict, closed_trades: List) -> Dict:
        """Calculate risk metrics"""
        if not closed_trades:
            return {}

        pnl_values = [t["pnl"] for t in closed_trades]

        # Volatility of returns
        volatility = np.std(pnl_values)

        # Value at Risk (95% confidence)
        var_95 = np.percentile(pnl_values, 5)

        # Maximum drawdown
        running_pnl = np.cumsum(pnl_values)
        running_max = np.maximum.accumulate(running_pnl)
        drawdown = running_pnl - running_max
        max_drawdown = np.min(drawdown)

        # Sharpe ratio (simplified, assuming risk-free rate = 0)
        sharpe_ratio = np.mean(pnl_values) / volatility if volatility != 0 else 0

        # Calmar ratio
        calmar_ratio = (
            np.mean(pnl_values) / abs(max_drawdown) if max_drawdown != 0 else 0
        )

        # Downside deviation
        negative_returns = [pnl for pnl in pnl_values if pnl < 0]
        downside_deviation = np.std(negative_returns) if negative_returns else 0

        return {
            "volatility": volatility,
            "var_95": var_95,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "calmar_ratio": calmar_ratio,
            "downside_deviation": downside_deviation,
            "risk_per_trade": (
                volatility / len(closed_trades) if len(closed_trades) > 0 else 0
            ),
        }

    def _calculate_strategy_metrics(self, closed_trades: List) -> Dict:
        """Calculate strategy-specific metrics"""
        if not closed_trades:
            return {}

        # Exit reason analysis
        exit_reasons = {}
        for trade in closed_trades:
            reason = trade.get("exit_reason", "UNKNOWN")
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        # Stop loss vs target analysis
        stop_loss_hits = exit_reasons.get("STOP_LOSS", 0)
        target_hits = exit_reasons.get("TARGET_HIT", 0)
        strategy_exits = exit_reasons.get("STRATEGY_SIGNAL", 0)

        # Average time to exit by reason
        time_to_exit = {}
        for reason in exit_reasons.keys():
            reason_trades = [t for t in closed_trades if t.get("exit_reason") == reason]
            if reason_trades:
                avg_time = np.mean(
                    [
                        t.get("holding_period", timedelta()).total_seconds() / 3600
                        for t in reason_trades
                    ]
                )
                time_to_exit[reason] = avg_time

        return {
            "exit_reasons": exit_reasons,
            "stop_loss_hit_rate": (
                (stop_loss_hits / len(closed_trades) * 100) if closed_trades else 0
            ),
            "target_hit_rate": (
                (target_hits / len(closed_trades) * 100) if closed_trades else 0
            ),
            "strategy_exit_rate": (
                (strategy_exits / len(closed_trades) * 100) if closed_trades else 0
            ),
            "avg_time_to_exit_by_reason": time_to_exit,
        }

    def _calculate_time_analysis(self, closed_trades: List) -> Dict:
        """Calculate time-based analysis"""
        if not closed_trades:
            return {}

        # Group by hour of day
        hourly_pnl = {}
        for trade in closed_trades:
            hour = trade["timestamp"].hour
            if hour not in hourly_pnl:
                hourly_pnl[hour] = []
            hourly_pnl[hour].append(trade["pnl"])

        # Best and worst trading hours
        hourly_avg = {hour: np.mean(pnls) for hour, pnls in hourly_pnl.items()}
        best_hour = (
            max(hourly_avg.keys(), key=lambda k: hourly_avg[k]) if hourly_avg else None
        )
        worst_hour = (
            min(hourly_avg.keys(), key=lambda k: hourly_avg[k]) if hourly_avg else None
        )

        # Group by day of week
        daily_pnl = {}
        for trade in closed_trades:
            day = trade["timestamp"].strftime("%A")
            if day not in daily_pnl:
                daily_pnl[day] = []
            daily_pnl[day].append(trade["pnl"])

        daily_avg = {day: np.mean(pnls) for day, pnls in daily_pnl.items()}

        return {
            "hourly_analysis": hourly_avg,
            "daily_analysis": daily_avg,
            "best_trading_hour": best_hour,
            "worst_trading_hour": worst_hour,
            "hourly_trade_count": {
                hour: len(pnls) for hour, pnls in hourly_pnl.items()
            },
        }

    def _calculate_win_loss_analysis(self, closed_trades: List) -> Dict:
        """Calculate detailed win/loss analysis"""
        if not closed_trades:
            return {}

        wins = [t for t in closed_trades if t["pnl"] > 0]
        losses = [t for t in closed_trades if t["pnl"] < 0]

        # Win/Loss distribution
        win_distribution = self._create_pnl_distribution([t["pnl"] for t in wins])
        loss_distribution = self._create_pnl_distribution(
            [abs(t["pnl"]) for t in losses]
        )

        # Streak analysis
        current_streak = self._calculate_current_streak(closed_trades)

        return {
            "win_distribution": win_distribution,
            "loss_distribution": loss_distribution,
            "current_streak": current_streak,
            "avg_win_size": np.mean([t["pnl"] for t in wins]) if wins else 0,
            "avg_loss_size": np.mean([abs(t["pnl"]) for t in losses]) if losses else 0,
            "largest_win_streak": self._calculate_consecutive_wins(closed_trades),
            "largest_loss_streak": self._calculate_consecutive_losses(closed_trades),
        }

    def _calculate_drawdown_analysis(self, portfolio: Dict) -> Dict:
        """Calculate detailed drawdown analysis"""
        daily_pnl = portfolio.get("daily_pnl", [])

        if not daily_pnl:
            return {}

        # Calculate running P&L
        portfolio_values = [day["portfolio_value"] for day in daily_pnl]

        if not portfolio_values:
            return {}

        # Calculate drawdowns
        # Calculate drawdowns
        running_max = np.maximum.accumulate(portfolio_values)
        drawdowns = [
            (value - max_val) / max_val * 100
            for value, max_val in zip(portfolio_values, running_max)
        ]

        # Find drawdown periods
        drawdown_periods = self._identify_drawdown_periods(drawdowns, portfolio_values)

        return {
            "current_drawdown": drawdowns[-1] if drawdowns else 0,
            "max_drawdown": min(drawdowns) if drawdowns else 0,
            "avg_drawdown": (
                np.mean([dd for dd in drawdowns if dd < 0])
                if any(dd < 0 for dd in drawdowns)
                else 0
            ),
            "drawdown_periods": len(drawdown_periods),
            "longest_drawdown_days": (
                max([period["duration_days"] for period in drawdown_periods])
                if drawdown_periods
                else 0
            ),
            "recovery_factor": (
                abs(max(portfolio_values) - min(portfolio_values)) / abs(min(drawdowns))
                if drawdowns and min(drawdowns) != 0
                else 0
            ),
        }

    def _create_pnl_distribution(self, pnl_list: List[float]) -> Dict:
        """Create P&L distribution buckets"""
        if not pnl_list:
            return {}

        buckets = {
            "0-1000": 0,
            "1000-5000": 0,
            "5000-10000": 0,
            "10000-25000": 0,
            "25000+": 0,
        }

        for pnl in pnl_list:
            abs_pnl = abs(pnl)
            if abs_pnl <= 1000:
                buckets["0-1000"] += 1
            elif abs_pnl <= 5000:
                buckets["1000-5000"] += 1
            elif abs_pnl <= 10000:
                buckets["5000-10000"] += 1
            elif abs_pnl <= 25000:
                buckets["10000-25000"] += 1
            else:
                buckets["25000+"] += 1

        return buckets

    def _calculate_consecutive_wins(self, trades: List) -> int:
        """Calculate maximum consecutive wins"""
        max_consecutive = 0
        current_consecutive = 0

        for trade in trades:
            if trade["pnl"] > 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive

    def _calculate_consecutive_losses(self, trades: List) -> int:
        """Calculate maximum consecutive losses"""
        max_consecutive = 0
        current_consecutive = 0

        for trade in trades:
            if trade["pnl"] < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive

    def _calculate_current_streak(self, trades: List) -> Dict:
        """Calculate current win/loss streak"""
        if not trades:
            return {"type": "none", "count": 0}

        # Sort by timestamp to get most recent
        sorted_trades = sorted(trades, key=lambda x: x["timestamp"])

        current_streak_type = "win" if sorted_trades[-1]["pnl"] > 0 else "loss"
        streak_count = 1

        # Count backwards
        for i in range(len(sorted_trades) - 2, -1, -1):
            trade = sorted_trades[i]
            if (current_streak_type == "win" and trade["pnl"] > 0) or (
                current_streak_type == "loss" and trade["pnl"] < 0
            ):
                streak_count += 1
            else:
                break

        return {"type": current_streak_type, "count": streak_count}

    def _identify_drawdown_periods(
        self, drawdowns: List, portfolio_values: List
    ) -> List[Dict]:
        """Identify distinct drawdown periods"""
        periods = []
        in_drawdown = False
        start_idx = 0

        for i, dd in enumerate(drawdowns):
            if dd < -1 and not in_drawdown:  # Start of drawdown (>1% loss)
                in_drawdown = True
                start_idx = i
            elif dd >= 0 and in_drawdown:  # End of drawdown (recovery)
                in_drawdown = False
                periods.append(
                    {
                        "start_idx": start_idx,
                        "end_idx": i,
                        "duration_days": i - start_idx,
                        "max_drawdown": min(drawdowns[start_idx : i + 1]),
                        "recovery_days": i - start_idx,
                    }
                )

        return periods

    def generate_performance_summary(self, user_id: int) -> Dict:
        """Generate a comprehensive performance summary"""
        try:
            metrics = self.calculate_comprehensive_metrics(user_id)

            if "error" in metrics:
                return metrics

            # Create performance summary
            summary = {
                "overall_performance": {
                    "grade": self._calculate_performance_grade(metrics),
                    "total_return_pct": metrics["performance"]["total_return_pct"],
                    "win_rate": metrics["basic"]["win_rate"],
                    "profit_factor": metrics["basic"]["profit_factor"],
                    "sharpe_ratio": metrics["risk"]["sharpe_ratio"],
                },
                "key_strengths": self._identify_strengths(metrics),
                "areas_for_improvement": self._identify_weaknesses(metrics),
                "recommendations": self._generate_recommendations(metrics),
                "risk_assessment": self._assess_risk_level(metrics),
                "strategy_effectiveness": self._assess_strategy_effectiveness(metrics),
            }

            return {
                "summary": summary,
                "detailed_metrics": metrics,
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Performance summary generation error: {e}")
            return {"error": str(e)}

    def _calculate_performance_grade(self, metrics: Dict) -> str:
        """Calculate overall performance grade A-F"""
        score = 0

        # Win rate scoring (30%)
        win_rate = metrics["basic"]["win_rate"]
        if win_rate >= 60:
            score += 30
        elif win_rate >= 50:
            score += 25
        elif win_rate >= 40:
            score += 20
        else:
            score += 10

        # Profit factor scoring (25%)
        profit_factor = metrics["basic"]["profit_factor"]
        if profit_factor >= 2.0:
            score += 25
        elif profit_factor >= 1.5:
            score += 20
        elif profit_factor >= 1.2:
            score += 15
        elif profit_factor >= 1.0:
            score += 10

        # Risk-reward ratio scoring (20%)
        risk_reward = metrics["performance"]["risk_reward_ratio"]
        if risk_reward >= 2.0:
            score += 20
        elif risk_reward >= 1.5:
            score += 15
        elif risk_reward >= 1.0:
            score += 10

        # Max drawdown scoring (15%)
        max_drawdown = abs(metrics["risk"]["max_drawdown"])
        if max_drawdown <= 5:
            score += 15
        elif max_drawdown <= 10:
            score += 12
        elif max_drawdown <= 15:
            score += 8
        elif max_drawdown <= 20:
            score += 5

        # Sharpe ratio scoring (10%)
        sharpe = metrics["risk"]["sharpe_ratio"]
        if sharpe >= 2.0:
            score += 10
        elif sharpe >= 1.0:
            score += 7
        elif sharpe >= 0.5:
            score += 5

        # Grade assignment
        if score >= 85:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 75:
            return "A-"
        elif score >= 70:
            return "B+"
        elif score >= 65:
            return "B"
        elif score >= 60:
            return "B-"
        elif score >= 55:
            return "C+"
        elif score >= 50:
            return "C"
        elif score >= 45:
            return "C-"
        elif score >= 40:
            return "D"
        else:
            return "F"

    def _identify_strengths(self, metrics: Dict) -> List[str]:
        """Identify trading strengths"""
        strengths = []

        if metrics["basic"]["win_rate"] >= 55:
            strengths.append(f"High win rate ({metrics['basic']['win_rate']:.1f}%)")

        if metrics["basic"]["profit_factor"] >= 1.5:
            strengths.append(
                f"Strong profit factor ({metrics['basic']['profit_factor']:.2f})"
            )

        if metrics["performance"]["risk_reward_ratio"] >= 1.5:
            strengths.append(
                f"Good risk-reward ratio ({metrics['performance']['risk_reward_ratio']:.2f})"
            )

        if abs(metrics["risk"]["max_drawdown"]) <= 10:
            strengths.append(
                f"Low maximum drawdown ({abs(metrics['risk']['max_drawdown']):.1f}%)"
            )

        if metrics["strategy"]["target_hit_rate"] >= 30:
            strengths.append(
                f"High target achievement rate ({metrics['strategy']['target_hit_rate']:.1f}%)"
            )

        return strengths

    def _identify_weaknesses(self, metrics: Dict) -> List[str]:
        """Identify areas for improvement"""
        weaknesses = []

        if metrics["basic"]["win_rate"] < 45:
            weaknesses.append(
                f"Low win rate ({metrics['basic']['win_rate']:.1f}%) - consider refining entry criteria"
            )

        if metrics["basic"]["profit_factor"] < 1.2:
            weaknesses.append(
                f"Low profit factor ({metrics['basic']['profit_factor']:.2f}) - losses too large relative to wins"
            )

        if metrics["performance"]["risk_reward_ratio"] < 1.0:
            weaknesses.append(
                f"Poor risk-reward ratio ({metrics['performance']['risk_reward_ratio']:.2f}) - average loss exceeds average win"
            )

        if abs(metrics["risk"]["max_drawdown"]) > 20:
            weaknesses.append(
                f"High maximum drawdown ({abs(metrics['risk']['max_drawdown']):.1f}%) - improve risk management"
            )

        if metrics["strategy"]["stop_loss_hit_rate"] > 60:
            weaknesses.append(
                f"High stop loss rate ({metrics['strategy']['stop_loss_hit_rate']:.1f}%) - stops may be too tight"
            )

        return weaknesses

    def _generate_recommendations(self, metrics: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        if metrics["basic"]["win_rate"] < 50:
            recommendations.append(
                "Focus on improving entry timing and market analysis"
            )

        if metrics["performance"]["risk_reward_ratio"] < 1.5:
            recommendations.append(
                "Consider wider profit targets or tighter stop losses"
            )

        if metrics["strategy"]["stop_loss_hit_rate"] > 50:
            recommendations.append("Review stop loss placement - may be too aggressive")

        if abs(metrics["risk"]["max_drawdown"]) > 15:
            recommendations.append(
                "Implement position sizing rules to reduce portfolio risk"
            )

        if metrics["performance"]["avg_holding_hours"] < 2:
            recommendations.append(
                "Consider holding positions longer to capture more profit"
            )

        return recommendations

    def _assess_risk_level(self, metrics: Dict) -> Dict:
        """Assess overall risk level"""
        risk_factors = []
        risk_score = 0

        # Drawdown risk
        max_dd = abs(metrics["risk"]["max_drawdown"])
        if max_dd > 20:
            risk_factors.append("High drawdown risk")
            risk_score += 3
        elif max_dd > 10:
            risk_factors.append("Moderate drawdown risk")
            risk_score += 2

        # Volatility risk
        volatility = metrics["risk"]["volatility"]
        if volatility > 10000:
            risk_factors.append("High volatility")
            risk_score += 2

        # Concentration risk
        if len(metrics.get("positions", [])) > 8:
            risk_factors.append("High position concentration")
            risk_score += 1

        # Risk level
        if risk_score >= 5:
            risk_level = "HIGH"
        elif risk_score >= 3:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"

        return {"level": risk_level, "score": risk_score, "factors": risk_factors}

    def _assess_strategy_effectiveness(self, metrics: Dict) -> Dict:
        """Assess strategy effectiveness"""
        effectiveness_score = 0

        # Win rate contribution
        if metrics["basic"]["win_rate"] >= 55:
            effectiveness_score += 25
        elif metrics["basic"]["win_rate"] >= 45:
            effectiveness_score += 15

        # Profit factor contribution
        if metrics["basic"]["profit_factor"] >= 1.5:
            effectiveness_score += 25
        elif metrics["basic"]["profit_factor"] >= 1.2:
            effectiveness_score += 15

        # Exit strategy effectiveness
        target_rate = metrics["strategy"]["target_hit_rate"]
        stop_rate = metrics["strategy"]["stop_loss_hit_rate"]

        if target_rate > stop_rate:
            effectiveness_score += 20
        elif target_rate > stop_rate * 0.7:
            effectiveness_score += 10

        # Consistency (low volatility of returns)
        if metrics["risk"]["sharpe_ratio"] > 1.0:
            effectiveness_score += 15
        elif metrics["risk"]["sharpe_ratio"] > 0.5:
            effectiveness_score += 10

        # Overall assessment
        if effectiveness_score >= 70:
            effectiveness = "EXCELLENT"
        elif effectiveness_score >= 55:
            effectiveness = "GOOD"
        elif effectiveness_score >= 40:
            effectiveness = "AVERAGE"
        elif effectiveness_score >= 25:
            effectiveness = "BELOW_AVERAGE"
        else:
            effectiveness = "POOR"

        return {"rating": effectiveness, "score": effectiveness_score, "max_score": 85}


# Global instance
analytics_service = TradingAnalyticsService()
