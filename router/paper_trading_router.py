from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, List
from pydantic import BaseModel
import asyncio

from database.connection import get_db
from services.auth_service import get_current_user
from services.screener.automated_screener_service import automated_screener
from services.trading_services.trading_analytics_service import analytics_service
from services.trading_services.paper_trading_engine import paper_trading_engine

router = APIRouter(prefix="/api/auto-paper-trading", tags=["Automated Paper Trading"])


class AutoTradingConfig(BaseModel):
    enable_auto_screening: bool = True
    max_stocks: int = 10
    min_score_threshold: int = 70
    risk_per_trade: float = 0.02
    stop_loss_pct: float = 0.04
    target_pct: float = 0.08
    enable_notifications: bool = True


@router.post("/enable-auto-mode")
async def enable_auto_trading_mode(
    config: AutoTradingConfig,
    background_tasks: BackgroundTasks,
    current_user: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enable automatic stock screening and trading"""
    try:
        # Store user's auto-trading preferences
        user_config = {
            "user_id": current_user,
            "auto_enabled": True,
            "config": config.dict(),
            "enabled_at": datetime.now(),
        }

        # Initialize portfolio if needed
        if current_user not in paper_trading_engine.user_portfolios:
            paper_trading_engine.initialize_portfolio(current_user, 1000000)

        # Store config in portfolio
        paper_trading_engine.user_portfolios[current_user][
            "auto_config"
        ] = config.dict()

        # Start automated screener if not already running
        if not hasattr(automated_screener, "_task_started"):
            background_tasks.add_task(automated_screener.start_automated_system)
            automated_screener._task_started = True

        return {
            "status": "enabled",
            "message": "Automated paper trading enabled successfully",
            "config": config.dict(),
            "next_screening_time": "9:15 AM (Market Open)",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to enable auto-trading: {str(e)}"
        )


@router.get("/auto-status")
async def get_auto_trading_status(current_user: int = Depends(get_current_user)):
    """Get current auto-trading status"""
    try:
        # Get screening status
        screening_status = automated_screener.get_screening_status()

        # Get user's daily picks
        daily_picks = automated_screener.get_daily_picks_for_user(current_user)

        # Get portfolio status
        portfolio = (
            paper_trading_engine.get_portfolio_summary(current_user)
            if current_user in paper_trading_engine.user_portfolios
            else None
        )

        return {
            "auto_enabled": current_user in paper_trading_engine.user_portfolios
            and paper_trading_engine.user_portfolios[current_user].get("auto_config")
            is not None,
            "market_session_active": screening_status["is_market_session_active"],
            "daily_picks": daily_picks,
            "portfolio_active": portfolio is not None
            and portfolio.get("is_active", False),
            "screening_status": screening_status,
            "current_time": datetime.now().strftime("%H:%M:%S"),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/today-picks")
async def get_today_stock_picks(current_user: int = Depends(get_current_user)):
    """Get today's automatically selected stocks"""
    try:
        daily_picks = automated_screener.get_daily_picks_for_user(current_user)

        if not daily_picks:
            return {
                "message": "No stocks picked today. Auto-screening happens at market open (9:15 AM)",
                "has_picks": False,
            }

        return {
            "has_picks": True,
            "stocks": daily_picks.get("stocks", []),
            "screening_time": daily_picks.get("screening_time"),
            "screening_results": daily_picks.get("screening_results", [])[
                :10
            ],  # Top 10
            "total_screened": len(daily_picks.get("screening_results", [])),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get picks: {str(e)}")


@router.get("/comprehensive-analytics")
async def get_comprehensive_analytics(current_user: int = Depends(get_current_user)):
    """Get comprehensive trading analytics and performance metrics"""
    try:
        analytics = analytics_service.calculate_comprehensive_metrics(current_user)

        if "error" in analytics:
            return {
                "message": "No trading data available for analysis",
                "has_data": False,
            }

        return {
            "has_data": True,
            "analytics": analytics,
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get analytics: {str(e)}"
        )


@router.get("/performance-summary")
async def get_performance_summary(current_user: int = Depends(get_current_user)):
    """Get AI-generated performance summary with recommendations"""
    try:
        summary = analytics_service.generate_performance_summary(current_user)

        if "error" in summary:
            return {
                "message": "No trading data available for performance summary",
                "has_data": False,
            }

        return {
            "has_data": True,
            "summary": summary,
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate summary: {str(e)}"
        )


@router.get("/real-time-metrics")
async def get_real_time_metrics(current_user: int = Depends(get_current_user)):
    """Get real-time trading metrics for dashboard"""
    try:
        if current_user not in paper_trading_engine.user_portfolios:
            return {"has_data": False, "message": "No active portfolio"}

        portfolio = paper_trading_engine.user_portfolios[current_user]

        # Calculate real-time metrics
        current_positions = len(portfolio["positions"])
        total_unrealized = sum(
            [pos["unrealized_pnl"] for pos in portfolio["positions"].values()]
        )

        # Today's trades
        today_trades = [
            t
            for t in portfolio["trade_history"]
            if t["timestamp"].date() == datetime.now().date()
        ]

        today_pnl = sum([t.get("pnl", 0) for t in today_trades if "pnl" in t])
        today_trades_count = len(today_trades)

        # Win rate for today
        today_wins = len([t for t in today_trades if t.get("pnl", 0) > 0])
        today_win_rate = (
            (today_wins / today_trades_count * 100) if today_trades_count > 0 else 0
        )

        return {
            "has_data": True,
            "real_time_metrics": {
                "current_portfolio_value": portfolio.get("risk_metrics", {}).get(
                    "current_value", 0
                ),
                "current_balance": portfolio["balance"],
                "total_unrealized_pnl": total_unrealized,
                "active_positions": current_positions,
                "today_pnl": today_pnl,
                "today_trades": today_trades_count,
                "today_win_rate": today_win_rate,
                "is_trading_active": portfolio.get("is_active", False),
                "last_trade_time": (
                    portfolio["trade_history"][-1]["timestamp"].isoformat()
                    if portfolio["trade_history"]
                    else None
                ),
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get real-time metrics: {str(e)}"
        )


@router.get("/strategy-performance")
async def get_strategy_performance_breakdown(
    current_user: int = Depends(get_current_user),
):
    """Get detailed strategy performance breakdown"""
    try:
        if current_user not in paper_trading_engine.user_portfolios:
            return {"has_data": False}

        portfolio = paper_trading_engine.user_portfolios[current_user]
        closed_trades = [
            t
            for t in portfolio["trade_history"]
            if t["status"] == "CLOSED" and "pnl" in t
        ]

        if not closed_trades:
            return {"has_data": False, "message": "No closed trades for analysis"}

        # Strategy breakdown by exit reason
        exit_analysis = {}
        for trade in closed_trades:
            reason = trade.get("exit_reason", "UNKNOWN")
            if reason not in exit_analysis:
                exit_analysis[reason] = {
                    "count": 0,
                    "total_pnl": 0,
                    "wins": 0,
                    "avg_holding_hours": 0,
                }

            exit_analysis[reason]["count"] += 1
            exit_analysis[reason]["total_pnl"] += trade["pnl"]
            if trade["pnl"] > 0:
                exit_analysis[reason]["wins"] += 1

            holding_hours = (
                trade.get("holding_period", timedelta()).total_seconds() / 3600
            )
            exit_analysis[reason]["avg_holding_hours"] += holding_hours

        # Calculate averages
        for reason, data in exit_analysis.items():
            data["win_rate"] = (
                (data["wins"] / data["count"] * 100) if data["count"] > 0 else 0
            )
            data["avg_pnl"] = (
                data["total_pnl"] / data["count"] if data["count"] > 0 else 0
            )
            data["avg_holding_hours"] = (
                data["avg_holding_hours"] / data["count"] if data["count"] > 0 else 0
            )

        # Time-based performance
        hourly_performance = {}
        for trade in closed_trades:
            hour = trade["timestamp"].hour
            if hour not in hourly_performance:
                hourly_performance[hour] = {"trades": 0, "pnl": 0, "wins": 0}

            hourly_performance[hour]["trades"] += 1
            hourly_performance[hour]["pnl"] += trade["pnl"]
            if trade["pnl"] > 0:
                hourly_performance[hour]["wins"] += 1

        # Calculate hourly win rates
        for hour, data in hourly_performance.items():
            data["win_rate"] = (
                (data["wins"] / data["trades"] * 100) if data["trades"] > 0 else 0
            )
            data["avg_pnl"] = data["pnl"] / data["trades"] if data["trades"] > 0 else 0

        return {
            "has_data": True,
            "strategy_breakdown": {
                "exit_reason_analysis": exit_analysis,
                "hourly_performance": hourly_performance,
                "total_trades_analyzed": len(closed_trades),
                "analysis_period": {
                    "start": min([t["timestamp"] for t in closed_trades]).isoformat(),
                    "end": max([t["timestamp"] for t in closed_trades]).isoformat(),
                },
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get strategy performance: {str(e)}"
        )


@router.post("/force-screening")
async def force_stock_screening(current_user: int = Depends(get_current_user)):
    """Force immediate stock screening (for testing)"""
    try:
        selected_stocks = await automated_screener._screen_and_select_stocks(
            current_user
        )

        if selected_stocks:
            return {
                "status": "success",
                "message": f"Screened and selected {len(selected_stocks)} stocks",
                "selected_stocks": selected_stocks,
            }
        else:
            return {
                "status": "no_picks",
                "message": "No stocks met the selection criteria",
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screening failed: {str(e)}")


@router.get("/market-sentiment")
async def get_market_sentiment_analysis(current_user: int = Depends(get_current_user)):
    """Get current market sentiment analysis"""
    try:
        # Get NIFTY data for market sentiment
        import yfinance as yf

        nifty_data = yf.download("^NSEI", period="1d", interval="5m")

        if nifty_data.empty:
            return {"error": "Market data not available"}

        current_price = nifty_data["Close"].iloc[-1]
        open_price = nifty_data["Open"].iloc[0]
        high_price = nifty_data["High"].max()
        low_price = nifty_data["Low"].min()

        market_move = (current_price - open_price) / open_price * 100
        volatility = nifty_data["Close"].pct_change().std() * 100

        # Sentiment classification
        if market_move > 1.5:
            sentiment = "VERY_BULLISH"
        elif market_move > 0.5:
            sentiment = "BULLISH"
        elif market_move > -0.5:
            sentiment = "NEUTRAL"
        elif market_move > -1.5:
            sentiment = "BEARISH"
        else:
            sentiment = "VERY_BEARISH"

        return {
            "market_sentiment": {
                "sentiment": sentiment,
                "nifty_current": float(current_price),
                "nifty_open": float(open_price),
                "nifty_high": float(high_price),
                "nifty_low": float(low_price),
                "market_move_pct": float(market_move),
                "volatility_pct": float(volatility),
                "last_updated": datetime.now().isoformat(),
            }
        }

    except Exception as e:
        return {"error": f"Failed to get market sentiment: {str(e)}"}
