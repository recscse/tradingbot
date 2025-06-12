import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import yfinance as yf
import pandas as pd
import numpy as np

from database.models import User, TradeSignal, AutoTradingSession
from database.connection import get_db
from services.screener.stock_screening_service import StockScreeningService
from services.trading_services.paper_trading_engine import paper_trading_engine

logger = logging.getLogger(__name__)


class AutomatedScreenerService:
    def __init__(self):
        self.screener = StockScreeningService()
        self.is_market_session_active = False
        self.daily_stock_picks = {}  # {user_id: [selected_stocks]}
        self.screening_config = {
            "max_stocks_per_user": 10,
            "min_score_threshold": 70,
            "sectors_to_include": [
                "Technology",
                "Banking",
                "Pharmaceuticals",
                "Automotive",
            ],
            "market_cap_min": 1000,  # Crores
            "volume_min": 100000,
            "price_range": {"min": 50, "max": 3000},
        }

    async def start_automated_system(self):
        """Start the automated screening and trading system"""
        logger.info("🤖 Automated Trading System Started")

        while True:
            try:
                current_time = datetime.now().time()

                # Check if market is about to open (9:10 AM)
                if (
                    self._is_pre_market_time(current_time)
                    and not self.is_market_session_active
                ):
                    await self._pre_market_preparation()

                # Market open screening (9:15 AM)
                elif (
                    self._is_market_open_time(current_time)
                    and not self.is_market_session_active
                ):
                    await self._market_open_screening()
                    self.is_market_session_active = True

                # During market hours - monitor and trade
                elif (
                    self._is_market_hours(current_time)
                    and self.is_market_session_active
                ):
                    await self._monitor_and_trade()

                # Market close cleanup (3:30 PM)
                elif (
                    self._is_market_close_time(current_time)
                    and self.is_market_session_active
                ):
                    await self._market_close_cleanup()
                    self.is_market_session_active = False

                # Wait before next check
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Automated system error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    def _is_pre_market_time(self, current_time: time) -> bool:
        """Check if it's pre-market preparation time (9:10 AM)"""
        return time(9, 10) <= current_time <= time(9, 14)

    def _is_market_open_time(self, current_time: time) -> bool:
        """Check if market just opened (9:15 AM)"""
        return time(9, 15) <= current_time <= time(9, 20)

    def _is_market_hours(self, current_time: time) -> bool:
        """Check if it's during market hours"""
        return time(9, 15) <= current_time <= time(15, 30)

    def _is_market_close_time(self, current_time: time) -> bool:
        """Check if market is closing"""
        return time(15, 25) <= current_time <= time(15, 35)

    async def _pre_market_preparation(self):
        """Prepare for market open - pre-screen stocks"""
        logger.info("📋 Pre-market preparation started")

        try:
            # Get all active paper trading users
            db = next(get_db())
            active_users = self._get_active_users(db)

            for user_id in active_users:
                # Pre-screen stocks for faster market open execution
                await self._pre_screen_stocks_for_user(user_id)

            logger.info(
                f"Pre-market preparation completed for {len(active_users)} users"
            )

        except Exception as e:
            logger.error(f"Pre-market preparation error: {e}")
        finally:
            db.close()

    async def _market_open_screening(self):
        """Screen and select stocks at market open"""
        logger.info("🔍 Market Open: Starting automated stock screening")

        try:
            db = next(get_db())
            active_users = self._get_active_users(db)

            for user_id in active_users:
                selected_stocks = await self._screen_and_select_stocks(user_id)

                if selected_stocks:
                    # Auto-start paper trading with selected stocks
                    await self._auto_start_paper_trading(user_id, selected_stocks)

                    # Save session record
                    await self._create_trading_session(user_id, selected_stocks, db)

            logger.info(
                f"Market open screening completed for {len(active_users)} users"
            )

        except Exception as e:
            logger.error(f"Market open screening error: {e}")
        finally:
            db.close()

    async def _screen_and_select_stocks(self, user_id: int) -> List[str]:
        """Screen and automatically select best stocks for user"""
        try:
            logger.info(f"Screening stocks for user {user_id}")

            # Get comprehensive stock universe
            stock_universe = self._get_stock_universe()

            # Screen each stock
            screened_results = []
            for symbol in stock_universe:
                try:
                    analysis = self.screener._analyze_stock(symbol)
                    if analysis and self._meets_selection_criteria(analysis):
                        screened_results.append(
                            {
                                "symbol": symbol,
                                "analysis": analysis,
                                "selection_score": self._calculate_selection_score(
                                    analysis
                                ),
                            }
                        )
                except Exception as e:
                    logger.warning(f"Error screening {symbol}: {e}")
                    continue

            # Sort by selection score and pick top stocks
            screened_results.sort(key=lambda x: x["selection_score"], reverse=True)
            selected_stocks = [
                result["symbol"]
                for result in screened_results[
                    : self.screening_config["max_stocks_per_user"]
                ]
            ]

            # Store picks for this user
            self.daily_stock_picks[user_id] = {
                "stocks": selected_stocks,
                "screening_time": datetime.now(),
                "screening_results": screened_results[:20],  # Keep top 20 for analysis
            }

            logger.info(
                f"Selected {len(selected_stocks)} stocks for user {user_id}: {selected_stocks}"
            )
            return selected_stocks

        except Exception as e:
            logger.error(f"Stock screening error for user {user_id}: {e}")
            return []

    def _get_stock_universe(self) -> List[str]:
        """Get the stock universe for screening"""
        # Top liquid stocks from different sectors
        stock_universe = [
            # Banking & Financial
            "HDFCBANK",
            "ICICIBANK",
            "KOTAKBANK",
            "AXISBANK",
            "SBIN",
            "INDUSINDBK",
            # Technology
            "TCS",
            "INFY",
            "WIPRO",
            "HCLTECH",
            "TECHM",
            "LTI",
            "MPHASIS",
            "LTTS",
            # Consumer & Retail
            "RELIANCE",
            "HINDUNILVR",
            "ITC",
            "NESTLEIND",
            "BRITANNIA",
            "DABUR",
            # Pharmaceuticals
            "SUNPHARMA",
            "DRREDDY",
            "CIPLA",
            "LUPIN",
            "BIOCON",
            "DIVISLAB",
            # Automotive
            "MARUTI",
            "TATAMOTORS",
            "M&M",
            "BAJAJ-AUTO",
            "HEROMOTOCO",
            "EICHERMOT",
            # Infrastructure & Capital Goods
            "LT",
            "ULTRACEMCO",
            "GRASIM",
            "JSWSTEEL",
            "TATASTEEL",
            "HINDALCO",
            # Energy & Utilities
            "ONGC",
            "BPCL",
            "IOC",
            "HINDPETRO",
            "POWERGRID",
            "NTPC",
            # Telecom & Media
            "BHARTIARTL",
            "IDEA",
            "SUNTV",
            # Others
            "ASIANPAINT",
            "TITAN",
            "BAJFINANCE",
            "HDFCLIFE",
            "SBILIFE",
            "ADANIENT",
        ]

        return stock_universe

    def _meets_selection_criteria(self, analysis: Dict) -> bool:
        """Check if stock meets automated selection criteria"""
        criteria_checks = [
            analysis["score"] >= self.screening_config["min_score_threshold"],
            analysis["current_price"] >= self.screening_config["price_range"]["min"],
            analysis["current_price"] <= self.screening_config["price_range"]["max"],
            analysis["volatility"] < 8.0,  # Not too volatile
            analysis["indicators"]["rsi"] < 75,  # Not overbought
            analysis["trend"] in ["UPTREND", "STRONG_UPTREND", "SIDEWAYS"],
            analysis["recommendation"]["confidence"] >= 65,
        ]

        return all(criteria_checks)

    def _calculate_selection_score(self, analysis: Dict) -> float:
        """Calculate comprehensive selection score"""
        base_score = analysis["score"]

        # Bonus points for strong fundamentals
        if analysis["fundamental_score"] > 80:
            base_score += 10

        # Bonus for strong technical setup
        if analysis["trend"] == "STRONG_UPTREND":
            base_score += 15
        elif analysis["trend"] == "UPTREND":
            base_score += 10

        # Bonus for good recommendation
        if analysis["recommendation"]["action"] == "STRONG_BUY":
            base_score += 20
        elif analysis["recommendation"]["action"] == "BUY":
            base_score += 10

        # Volume factor
        if analysis["volume_score"] > 70:
            base_score += 5

        # Risk adjustment
        if analysis["risk_metrics"]["volatility"] < 3:
            base_score += 5

        return min(base_score, 150)  # Cap at 150

    async def _auto_start_paper_trading(self, user_id: int, selected_stocks: List[str]):
        """Automatically start paper trading with selected stocks"""
        try:
            # Auto-configuration based on user risk profile
            strategy_config = self._get_auto_strategy_config(user_id)

            # Initialize portfolio if needed
            if user_id not in paper_trading_engine.user_portfolios:
                paper_trading_engine.initialize_portfolio(user_id, 1000000)

            # Start automated trading
            result = await paper_trading_engine.start_paper_trading(
                user_id, selected_stocks, strategy_config
            )

            logger.info(
                f"Auto-started paper trading for user {user_id} with {len(selected_stocks)} stocks"
            )
            return result

        except Exception as e:
            logger.error(f"Auto-start paper trading error for user {user_id}: {e}")
            return None

    def _get_auto_strategy_config(self, user_id: int) -> Dict:
        """Get automated strategy configuration"""
        return {
            "risk_per_trade": 0.02,  # 2% risk per trade
            "stop_loss_pct": 0.04,  # 4% stop loss
            "target_pct": 0.08,  # 8% target (2:1 risk-reward)
            "min_confidence": 75,  # Higher confidence for auto-trading
            "analysis_interval": 180,  # 3 minutes (more frequent)
            "use_trailing_stop": True,
            "trailing_stop_pct": 0.02,
            "max_positions": 8,  # Max 8 positions
            "auto_mode": True,  # Flag for automated trading
        }

    def _get_active_users(self, db: Session) -> List[int]:
        """Get users who have auto-trading enabled"""
        # For now, return all users. Later add user preference table
        users = db.query(User).filter(User.is_active == True).all()
        return [user.id for user in users]

    async def _create_trading_session(
        self, user_id: int, selected_stocks: List[str], db: Session
    ):
        """Create trading session record"""
        try:
            session = AutoTradingSession(
                user_id=user_id,
                session_date=datetime.now().date(),
                selected_stocks=selected_stocks,
                screening_config=self.screening_config,
                stocks_screened=len(self._get_stock_universe()),
                session_type="AUTO_PAPER_TRADING",
                status="ACTIVE",
            )

            db.add(session)
            db.commit()

        except Exception as e:
            logger.error(f"Error creating trading session: {e}")
            db.rollback()

    async def _monitor_and_trade(self):
        """Monitor markets and execute trades during market hours"""
        try:
            # This will be handled by the paper trading engine
            # But we can add additional monitoring here

            # Check for any system-wide alerts or pattern changes
            await self._check_market_conditions()

        except Exception as e:
            logger.error(f"Monitoring error: {e}")

    async def _check_market_conditions(self):
        """Check overall market conditions"""
        try:
            # Get NIFTY data for market sentiment
            nifty_data = yf.download("^NSEI", period="1d", interval="5m")

            if not nifty_data.empty:
                current_price = nifty_data["Close"].iloc[-1]
                open_price = nifty_data["Open"].iloc[0]
                market_move = (current_price - open_price) / open_price * 100

                # Log significant market moves
                if abs(market_move) > 2:
                    logger.warning(
                        f"Significant market move detected: NIFTY {market_move:.2f}%"
                    )

                    # Could implement position sizing adjustments here
                    # await self._adjust_position_sizes_for_market_conditions(market_move)

        except Exception as e:
            logger.warning(f"Market condition check error: {e}")

    async def _market_close_cleanup(self):
        """Cleanup and generate reports at market close"""
        logger.info("📊 Market Close: Generating daily reports")

        try:
            db = next(get_db())

            for user_id in self.daily_stock_picks.keys():
                await self._generate_daily_report(user_id, db)

            # Reset for next day
            self.daily_stock_picks.clear()

        except Exception as e:
            logger.error(f"Market close cleanup error: {e}")
        finally:
            db.close()

    async def _generate_daily_report(self, user_id: int, db: Session):
        """Generate daily trading report for user"""
        try:
            if user_id not in paper_trading_engine.user_portfolios:
                return

            portfolio = paper_trading_engine.user_portfolios[user_id]

            # Get today's trades
            today_trades = [
                trade
                for trade in portfolio["trade_history"]
                if trade["timestamp"].date() == datetime.now().date()
            ]

            # Calculate daily metrics
            daily_pnl = sum(
                [trade.get("pnl", 0) for trade in today_trades if trade.get("pnl")]
            )
            trades_executed = len(today_trades)
            winning_trades = len([t for t in today_trades if t.get("pnl", 0) > 0])

            report = {
                "user_id": user_id,
                "date": datetime.now().date(),
                "stocks_selected": self.daily_stock_picks.get(user_id, {}).get(
                    "stocks", []
                ),
                "trades_executed": trades_executed,
                "daily_pnl": daily_pnl,
                "winning_trades": winning_trades,
                "win_rate": (
                    (winning_trades / trades_executed * 100)
                    if trades_executed > 0
                    else 0
                ),
                "portfolio_value": portfolio.get("risk_metrics", {}).get(
                    "current_value", 0
                ),
            }

            # Save report to database (implement DailyTradingReport model)
            logger.info(
                f"Daily report for user {user_id}: P&L ₹{daily_pnl:.2f}, Trades: {trades_executed}"
            )

        except Exception as e:
            logger.error(f"Daily report generation error for user {user_id}: {e}")

    def get_daily_picks_for_user(self, user_id: int) -> Dict:
        """Get today's stock picks for a user"""
        return self.daily_stock_picks.get(user_id, {})

    def get_screening_status(self) -> Dict:
        """Get current screening status"""
        return {
            "is_market_session_active": self.is_market_session_active,
            "users_with_picks": len(self.daily_stock_picks),
            "screening_config": self.screening_config,
            "last_screening_time": max(
                [
                    picks.get("screening_time")
                    for picks in self.daily_stock_picks.values()
                ],
                default=None,
            ),
        }


# Global instance
automated_screener = AutomatedScreenerService()
