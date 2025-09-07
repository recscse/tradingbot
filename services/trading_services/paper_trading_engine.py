import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import yfinance as yf
import uuid

from database.models import TradePerformance, TradeSignal, User
from database.connection import get_db
from services.screener.stock_screening_service import StockScreeningService

# Import instrument registry for HFT producer-consumer pattern
try:
    from services.instrument_registry import instrument_registry
    INSTRUMENT_REGISTRY_AVAILABLE = True
except ImportError:
    INSTRUMENT_REGISTRY_AVAILABLE = False

logger = logging.getLogger(__name__)


class PaperTradingEngine:
    def __init__(self):
        self.is_active = False
        self.user_portfolios = {}  # {user_id: portfolio_data}
        self.screener = StockScreeningService()
        self.active_position_instruments = set()  # Track active positions for subscriptions
        
        # 🚀 HFT PRODUCER-CONSUMER: Register as consumer for active position updates
        self._register_as_consumer()

    def initialize_portfolio(self, user_id: int, initial_balance: float = 1000000):
        """Initialize user portfolio for paper trading"""
        self.user_portfolios[user_id] = {
            "balance": initial_balance,
            "initial_balance": initial_balance,
            "positions": {},  # {symbol: position_data}
            "trade_history": [],
            "daily_pnl": [],
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "largest_win": 0,
            "largest_loss": 0,
            "current_drawdown": 0,
            "max_drawdown": 0,
            "risk_metrics": {},
            "created_at": datetime.now(),
        }
        logger.info(
            f"Portfolio initialized for user {user_id} with ₹{initial_balance:,.2f}"
        )

    async def start_paper_trading(
        self, user_id: int, selected_stocks: List[str], strategy_config: Dict
    ):
        """Start paper trading for user"""
        if user_id not in self.user_portfolios:
            self.initialize_portfolio(user_id)

        self.user_portfolios[user_id]["is_active"] = True
        self.user_portfolios[user_id]["strategy_config"] = strategy_config
        self.user_portfolios[user_id]["selected_stocks"] = selected_stocks

        logger.info(
            f"Paper trading started for user {user_id} with {len(selected_stocks)} stocks"
        )

        # Start trading loop
        asyncio.create_task(self._trading_loop(user_id))

        return {
            "status": "started",
            "message": "Paper trading initiated successfully",
            "portfolio": self.get_portfolio_summary(user_id),
        }

    async def _trading_loop(self, user_id: int):
        """Main trading loop for paper trading"""
        portfolio = self.user_portfolios[user_id]

        while portfolio.get("is_active", False):
            try:
                # Analyze selected stocks
                for symbol in portfolio["selected_stocks"]:
                    await self._analyze_and_trade(user_id, symbol)

                # Update portfolio metrics
                await self._update_portfolio_metrics(user_id)

                # Monitor existing positions
                await self._monitor_positions(user_id)

                # Wait for next analysis cycle
                await asyncio.sleep(
                    portfolio["strategy_config"].get("analysis_interval", 300)
                )  # 5 minutes

            except Exception as e:
                logger.error(f"Trading loop error for user {user_id}: {e}")
                await asyncio.sleep(60)

    async def _analyze_and_trade(self, user_id: int, symbol: str):
        """Analyze stock and execute trades"""
        try:
            portfolio = self.user_portfolios[user_id]

            # Get current market data
            ticker = yf.Ticker(f"{symbol}.NS")
            data = ticker.history(period="30d", interval="5m")

            if len(data) < 50:
                return

            # Perform analysis
            analysis = self.screener._analyze_stock(symbol)
            if not analysis:
                return

            recommendation = analysis["recommendation"]
            current_price = analysis["current_price"]

            # Check trading conditions
            if recommendation["confidence"] > portfolio["strategy_config"].get(
                "min_confidence", 70
            ):

                if recommendation["action"] in ["BUY", "STRONG_BUY"]:
                    await self._execute_buy_order(
                        user_id, symbol, current_price, analysis, recommendation
                    )

                elif (
                    recommendation["action"] == "SELL"
                    and symbol in portfolio["positions"]
                ):
                    await self._execute_sell_order(
                        user_id, symbol, current_price, analysis, recommendation
                    )

        except Exception as e:
            logger.error(f"Analysis error for {symbol}: {e}")

    async def _execute_buy_order(
        self,
        user_id: int,
        symbol: str,
        price: float,
        analysis: Dict,
        recommendation: Dict,
    ):
        """Execute paper buy order"""
        portfolio = self.user_portfolios[user_id]

        # Check if already have position
        if symbol in portfolio["positions"]:
            return

        # Calculate position size
        risk_amount = portfolio["balance"] * portfolio["strategy_config"].get(
            "risk_per_trade", 0.02
        )

        # Calculate stop loss
        stop_loss_pct = portfolio["strategy_config"].get("stop_loss_pct", 0.05)
        stop_loss = price * (1 - stop_loss_pct)
        risk_per_share = price - stop_loss

        if risk_per_share <= 0:
            return

        quantity = int(risk_amount / risk_per_share)
        total_cost = quantity * price

        # Check if sufficient balance
        if total_cost > portfolio["balance"]:
            quantity = int(portfolio["balance"] / price)
            total_cost = quantity * price

        if quantity < 1:
            return

        # Execute order
        trade_id = str(uuid.uuid4())

        # Create position
        portfolio["positions"][symbol] = {
            "symbol": symbol,
            "quantity": quantity,
            "entry_price": price,
            "entry_time": datetime.now(),
            "stop_loss": stop_loss,
            "target_price": price
            * (1 + portfolio["strategy_config"].get("target_pct", 0.10)),
            "trade_id": trade_id,
            "analysis": analysis,
            "recommendation": recommendation,
            "current_price": price,
            "unrealized_pnl": 0,
            "max_profit": 0,
            "max_loss": 0,
        }

        # Update balance
        portfolio["balance"] -= total_cost

        # Record trade
        trade_record = {
            "trade_id": trade_id,
            "symbol": symbol,
            "action": "BUY",
            "quantity": quantity,
            "price": price,
            "total_amount": total_cost,
            "timestamp": datetime.now(),
            "analysis": analysis,
            "recommendation": recommendation,
            "status": "OPEN",
        }

        portfolio["trade_history"].append(trade_record)
        portfolio["total_trades"] += 1

        # Save to database
        await self._save_trade_to_db(user_id, trade_record)

        logger.info(
            f"BUY executed: {symbol} qty:{quantity} price:₹{price} total:₹{total_cost:,.2f}"
        )

    async def _execute_sell_order(
        self,
        user_id: int,
        symbol: str,
        price: float,
        analysis: Dict,
        recommendation: Dict,
    ):
        """Execute paper sell order"""
        portfolio = self.user_portfolios[user_id]
        position = portfolio["positions"][symbol]

        quantity = position["quantity"]
        entry_price = position["entry_price"]
        total_proceeds = quantity * price

        # Calculate P&L
        pnl = (price - entry_price) * quantity
        pnl_pct = (pnl / (entry_price * quantity)) * 100

        # Update balance
        portfolio["balance"] += total_proceeds

        # Update statistics
        if pnl > 0:
            portfolio["winning_trades"] += 1
            portfolio["largest_win"] = max(portfolio["largest_win"], pnl)
        else:
            portfolio["losing_trades"] += 1
            portfolio["largest_loss"] = min(portfolio["largest_loss"], pnl)

        # Record trade
        trade_record = {
            "trade_id": position["trade_id"],
            "symbol": symbol,
            "action": "SELL",
            "quantity": quantity,
            "price": price,
            "total_amount": total_proceeds,
            "entry_price": entry_price,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "holding_period": datetime.now() - position["entry_time"],
            "timestamp": datetime.now(),
            "analysis": analysis,
            "recommendation": recommendation,
            "status": "CLOSED",
            "exit_reason": "STRATEGY_SIGNAL",
        }

        portfolio["trade_history"].append(trade_record)

        # Update trade in database
        await self._update_trade_in_db(user_id, trade_record)

        # Remove position
        del portfolio["positions"][symbol]

        logger.info(
            f"SELL executed: {symbol} qty:{quantity} price:₹{price} P&L:₹{pnl:,.2f} ({pnl_pct:.2f}%)"
        )

    async def _monitor_positions(self, user_id: int):
        """Monitor existing positions for stop loss and target"""
        portfolio = self.user_portfolios[user_id]

        positions_to_close = []

        for symbol, position in portfolio["positions"].items():
            try:
                # Get current price
                ticker = yf.Ticker(f"{symbol}.NS")
                current_data = ticker.history(period="1d", interval="1m")

                if current_data.empty:
                    continue

                current_price = float(current_data["Close"].iloc[-1])
                position["current_price"] = current_price

                # Calculate unrealized P&L
                unrealized_pnl = (current_price - position["entry_price"]) * position[
                    "quantity"
                ]
                position["unrealized_pnl"] = unrealized_pnl

                # Update max profit/loss
                position["max_profit"] = max(position["max_profit"], unrealized_pnl)
                position["max_loss"] = min(position["max_loss"], unrealized_pnl)

                # Check stop loss
                if current_price <= position["stop_loss"]:
                    positions_to_close.append((symbol, "STOP_LOSS"))

                # Check target
                elif current_price >= position["target_price"]:
                    positions_to_close.append((symbol, "TARGET_HIT"))

                # Check trailing stop loss if enabled
                elif portfolio["strategy_config"].get("use_trailing_stop", False):
                    trailing_stop_pct = portfolio["strategy_config"].get(
                        "trailing_stop_pct", 0.03
                    )
                    if position["max_profit"] > 0:  # Only if in profit
                        trailing_stop = position["entry_price"] + (
                            position["max_profit"] / position["quantity"]
                        ) * (1 - trailing_stop_pct)
                        if current_price <= trailing_stop:
                            positions_to_close.append((symbol, "TRAILING_STOP"))

            except Exception as e:
                logger.error(f"Error monitoring position {symbol}: {e}")

        # Close positions that hit stop loss or target
        for symbol, reason in positions_to_close:
            await self._close_position(user_id, symbol, reason)

    async def _close_position(self, user_id: int, symbol: str, reason: str):
        """Close position due to stop loss, target, or trailing stop"""
        portfolio = self.user_portfolios[user_id]
        position = portfolio["positions"][symbol]

        current_price = position["current_price"]
        quantity = position["quantity"]
        entry_price = position["entry_price"]
        total_proceeds = quantity * current_price

        # Calculate P&L
        pnl = (current_price - entry_price) * quantity
        pnl_pct = (pnl / (entry_price * quantity)) * 100

        # Update balance
        portfolio["balance"] += total_proceeds

        # Update statistics
        if pnl > 0:
            portfolio["winning_trades"] += 1
            portfolio["largest_win"] = max(portfolio["largest_win"], pnl)
        else:
            portfolio["losing_trades"] += 1
            portfolio["largest_loss"] = min(portfolio["largest_loss"], pnl)

        # Record trade
        trade_record = {
            "trade_id": position["trade_id"],
            "symbol": symbol,
            "action": "SELL",
            "quantity": quantity,
            "price": current_price,
            "total_amount": total_proceeds,
            "entry_price": entry_price,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "holding_period": datetime.now() - position["entry_time"],
            "timestamp": datetime.now(),
            "status": "CLOSED",
            "exit_reason": reason,
        }

        portfolio["trade_history"].append(trade_record)

        # Update trade in database
        await self._update_trade_in_db(user_id, trade_record)

        # Remove position
        del portfolio["positions"][symbol]

        logger.info(
            f"Position closed: {symbol} reason:{reason} P&L:₹{pnl:,.2f} ({pnl_pct:.2f}%)"
        )

    async def _update_portfolio_metrics(self, user_id: int):
        """Update portfolio performance metrics"""
        portfolio = self.user_portfolios[user_id]

        # Calculate current portfolio value
        current_value = portfolio["balance"]
        for position in portfolio["positions"].values():
            current_value += position["quantity"] * position["current_price"]

        # Calculate total P&L
        total_pnl = current_value - portfolio["initial_balance"]
        total_pnl_pct = (total_pnl / portfolio["initial_balance"]) * 100

        # Calculate drawdown
        portfolio["current_drawdown"] = total_pnl if total_pnl < 0 else 0
        portfolio["max_drawdown"] = min(
            portfolio["max_drawdown"], portfolio["current_drawdown"]
        )

        # Store daily P&L
        today = datetime.now().date()
        if not portfolio["daily_pnl"] or portfolio["daily_pnl"][-1]["date"] != today:
            portfolio["daily_pnl"].append(
                {
                    "date": today,
                    "portfolio_value": current_value,
                    "total_pnl": total_pnl,
                    "total_pnl_pct": total_pnl_pct,
                    "daily_pnl": total_pnl
                    - (
                        portfolio["daily_pnl"][-1]["total_pnl"]
                        if portfolio["daily_pnl"]
                        else 0
                    ),
                    "positions_count": len(portfolio["positions"]),
                    "balance": portfolio["balance"],
                }
            )

        # Calculate win rate
        total_closed_trades = portfolio["winning_trades"] + portfolio["losing_trades"]
        win_rate = (
            (portfolio["winning_trades"] / total_closed_trades * 100)
            if total_closed_trades > 0
            else 0
        )

        # Calculate average win/loss
        closed_trades = [
            t
            for t in portfolio["trade_history"]
            if t["status"] == "CLOSED" and "pnl" in t
        ]

        avg_win = 0
        avg_loss = 0
        if closed_trades:
            winning_trades = [t["pnl"] for t in closed_trades if t["pnl"] > 0]
            losing_trades = [t["pnl"] for t in closed_trades if t["pnl"] < 0]

            avg_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0
            avg_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0

        # Risk-reward ratio
        risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        # Sharpe ratio (simplified)
        if len(portfolio["daily_pnl"]) > 1:
            daily_returns = [
                day["daily_pnl"] / portfolio["initial_balance"]
                for day in portfolio["daily_pnl"]
            ]
            avg_return = sum(daily_returns) / len(daily_returns)
            return_std = (
                sum([(r - avg_return) ** 2 for r in daily_returns]) / len(daily_returns)
            ) ** 0.5
            sharpe_ratio = (
                (avg_return * 252) / (return_std * (252**0.5)) if return_std != 0 else 0
            )
        else:
            sharpe_ratio = 0

        # Update metrics
        portfolio["risk_metrics"] = {
            "current_value": current_value,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "risk_reward_ratio": risk_reward,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": portfolio["max_drawdown"],
            "total_trades": portfolio["total_trades"],
            "winning_trades": portfolio["winning_trades"],
            "losing_trades": portfolio["losing_trades"],
        }

    async def _save_trade_to_db(self, user_id: int, trade_record: Dict):
        """Save trade to database"""
        db = next(get_db())
        try:
            trade = TradePerformance(
                user_id=user_id,
                symbol=trade_record["symbol"],
                trade_type=trade_record["action"],
                quantity=trade_record["quantity"],
                entry_price=trade_record["price"],
                status="OPEN",
                trade_time=trade_record["timestamp"],
            )

            # Add metadata
            trade.metadata = {
                "trade_id": trade_record["trade_id"],
                "analysis": trade_record.get("analysis", {}),
                "recommendation": trade_record.get("recommendation", {}),
                "is_paper_trade": True,
            }

            db.add(trade)
            db.commit()

        except Exception as e:
            logger.error(f"Error saving trade to DB: {e}")
            db.rollback()
        finally:
            db.close()

    async def _update_trade_in_db(self, user_id: int, trade_record: Dict):
        """Update trade in database when closed"""
        db = next(get_db())
        try:
            trade = (
                db.query(TradePerformance)
                .filter(
                    TradePerformance.user_id == user_id,
                    TradePerformance.symbol == trade_record["symbol"],
                    TradePerformance.status == "OPEN",
                )
                .first()
            )

            if trade:
                trade.exit_price = trade_record["price"]
                trade.profit_loss = trade_record["pnl"]
                trade.status = "CLOSED"

                # Update metadata
                if not trade.metadata:
                    trade.metadata = {}
                trade.metadata.update(
                    {
                        "exit_reason": trade_record.get("exit_reason", "UNKNOWN"),
                        "holding_period_minutes": int(
                            trade_record["holding_period"].total_seconds() / 60
                        ),
                        "pnl_pct": trade_record["pnl_pct"],
                    }
                )

                db.commit()

        except Exception as e:
            logger.error(f"Error updating trade in DB: {e}")
            db.rollback()
        finally:
            db.close()

    def stop_paper_trading(self, user_id: int):
        """Stop paper trading for user"""
        if user_id in self.user_portfolios:
            self.user_portfolios[user_id]["is_active"] = False

            # Close all open positions
            for symbol in list(self.user_portfolios[user_id]["positions"].keys()):
                asyncio.create_task(
                    self._close_position(user_id, symbol, "MANUAL_STOP")
                )

            logger.info(f"Paper trading stopped for user {user_id}")
            return True
        return False

    def get_portfolio_summary(self, user_id: int) -> Dict:
        """Get portfolio summary"""
        if user_id not in self.user_portfolios:
            return {}

        portfolio = self.user_portfolios[user_id]

        # Calculate current portfolio value
        current_value = portfolio["balance"]
        unrealized_pnl = 0

        positions_summary = []
        for symbol, position in portfolio["positions"].items():
            position_value = position["quantity"] * position["current_price"]
            current_value += position_value
            unrealized_pnl += position["unrealized_pnl"]

            positions_summary.append(
                {
                    "symbol": symbol,
                    "quantity": position["quantity"],
                    "entry_price": position["entry_price"],
                    "current_price": position["current_price"],
                    "unrealized_pnl": position["unrealized_pnl"],
                    "unrealized_pnl_pct": (
                        position["unrealized_pnl"]
                        / (position["entry_price"] * position["quantity"])
                    )
                    * 100,
                    "entry_time": position["entry_time"].isoformat(),
                    "stop_loss": position["stop_loss"],
                    "target_price": position["target_price"],
                }
            )

        return {
            "user_id": user_id,
            "is_active": portfolio.get("is_active", False),
            "initial_balance": portfolio["initial_balance"],
            "current_balance": portfolio["balance"],
            "current_portfolio_value": current_value,
            "total_pnl": current_value - portfolio["initial_balance"],
            "total_pnl_pct": (
                (current_value - portfolio["initial_balance"])
                / portfolio["initial_balance"]
            )
            * 100,
            "unrealized_pnl": unrealized_pnl,
            "positions": positions_summary,
            "risk_metrics": portfolio.get("risk_metrics", {}),
            "total_trades": portfolio["total_trades"],
            "winning_trades": portfolio["winning_trades"],
            "losing_trades": portfolio["losing_trades"],
            "created_at": (
                portfolio["created_at"].isoformat()
                if "created_at" in portfolio
                else None
            ),
        }

    def get_trade_history(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get trade history for user"""
        if user_id not in self.user_portfolios:
            return []

        trades = self.user_portfolios[user_id]["trade_history"]

        # Sort by timestamp (most recent first)
        sorted_trades = sorted(trades, key=lambda x: x["timestamp"], reverse=True)

        # Format for API response
        formatted_trades = []
        for trade in sorted_trades[:limit]:
            formatted_trade = {
                "trade_id": trade["trade_id"],
                "symbol": trade["symbol"],
                "action": trade["action"],
                "quantity": trade["quantity"],
                "price": trade["price"],
                "total_amount": trade["total_amount"],
                "timestamp": trade["timestamp"].isoformat(),
                "status": trade["status"],
            }

            # Add additional fields for closed trades
            if trade["status"] == "CLOSED":
                formatted_trade.update(
                    {
                        "entry_price": trade.get("entry_price"),
                        "pnl": trade.get("pnl"),
                        "pnl_pct": trade.get("pnl_pct"),
                        "holding_period_minutes": int(
                            trade.get("holding_period", timedelta()).total_seconds()
                            / 60
                        ),
                        "exit_reason": trade.get("exit_reason"),
                    }
                )

            formatted_trades.append(formatted_trade)

        return formatted_trades

    def get_performance_analytics(self, user_id: int) -> Dict:
        """Get detailed performance analytics"""
        if user_id not in self.user_portfolios:
            return {}

        portfolio = self.user_portfolios[user_id]
        closed_trades = [
            t
            for t in portfolio["trade_history"]
            if t["status"] == "CLOSED" and "pnl" in t
        ]

        if not closed_trades:
            return {
                "total_trades": 0,
                "message": "No closed trades available for analysis",
            }

        # Monthly performance
        monthly_performance = {}
        for trade in closed_trades:
            month_key = trade["timestamp"].strftime("%Y-%m")
            if month_key not in monthly_performance:
                monthly_performance[month_key] = {
                    "trades": 0,
                    "pnl": 0,
                    "winning_trades": 0,
                }

            monthly_performance[month_key]["trades"] += 1
            monthly_performance[month_key]["pnl"] += trade["pnl"]
            if trade["pnl"] > 0:
                monthly_performance[month_key]["winning_trades"] += 1

        # Best and worst trades
        best_trade = max(closed_trades, key=lambda x: x["pnl"])
        worst_trade = min(closed_trades, key=lambda x: x["pnl"])

        # Average holding period
        avg_holding_period = (
            sum([t["holding_period"].total_seconds() for t in closed_trades])
            / len(closed_trades)
            / 3600
        )  # hours

        # Profit factor
        gross_profit = sum([t["pnl"] for t in closed_trades if t["pnl"] > 0])
        gross_loss = abs(sum([t["pnl"] for t in closed_trades if t["pnl"] < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        return {
            "total_trades": len(closed_trades),
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "profit_factor": profit_factor,
            "avg_holding_period_hours": avg_holding_period,
            "best_trade": {
                "symbol": best_trade["symbol"],
                "pnl": best_trade["pnl"],
                "pnl_pct": best_trade["pnl_pct"],
                "date": best_trade["timestamp"].isoformat(),
            },
            "worst_trade": {
                "symbol": worst_trade["symbol"],
                "pnl": worst_trade["pnl"],
                "pnl_pct": worst_trade["pnl_pct"],
                "date": worst_trade["timestamp"].isoformat(),
            },
            "monthly_performance": monthly_performance,
            "daily_pnl_chart": (
                portfolio["daily_pnl"][-30:] if len(portfolio["daily_pnl"]) > 0 else []
            ),  # Last 30 days
        }
    
    def _register_as_consumer(self):
        """🚀 Register as consumer for active position instruments - HFT Producer-Consumer Pattern"""
        try:
            if INSTRUMENT_REGISTRY_AVAILABLE and instrument_registry:
                # Note: Initial registration with empty list - will update when positions are opened
                success = instrument_registry.register_strategy_callback(
                    strategy_name="paper_trading",
                    instruments=list(self.active_position_instruments),
                    callback=self._process_live_tick_callback
                )
                
                if success:
                    logger.info("✅ Paper Trading Engine registered as consumer (dynamic position tracking)")
                else:
                    logger.error("❌ Failed to register Paper Trading Engine as consumer")
            else:
                logger.warning("⚠️ Instrument registry not available for consumer registration")
                
        except Exception as e:
            logger.error(f"❌ Error registering Paper Trading Engine as consumer: {e}")
    
    def _update_position_subscriptions(self):
        """Update subscriptions when positions change"""
        try:
            if not INSTRUMENT_REGISTRY_AVAILABLE or not instrument_registry:
                return
            
            # Get all active position symbols across all users
            current_symbols = set()
            for user_portfolio in self.user_portfolios.values():
                if user_portfolio.get("is_active", False):
                    current_symbols.update(user_portfolio.get("positions", {}).keys())
            
            # Convert symbols to instrument keys
            new_instruments = set()
            for symbol in current_symbols:
                try:
                    if instrument_registry._symbols_map.get(symbol):
                        symbol_data = instrument_registry._symbols_map[symbol]
                        if symbol_data.get("spot"):
                            new_instruments.update(symbol_data["spot"])
                except Exception:
                    continue
            
            # Update subscriptions if instruments changed
            if new_instruments != self.active_position_instruments:
                self.active_position_instruments = new_instruments
                
                # Re-register with updated instrument list
                success = instrument_registry.register_strategy_callback(
                    strategy_name="paper_trading",
                    instruments=list(self.active_position_instruments),
                    callback=self._process_live_tick_callback
                )
                
                logger.info(f"📊 Updated Paper Trading subscriptions: {len(self.active_position_instruments)} instruments")
                
        except Exception as e:
            logger.error(f"❌ Error updating position subscriptions: {e}")
    
    def _process_live_tick_callback(self, instrument_key: str, price_data: dict):
        """
        🚀 ZERO-DELAY CALLBACK: Process live tick data for position P&L updates
        This is called directly by instrument_registry when price data arrives for active positions
        
        Args:
            instrument_key: Instrument identifier
            price_data: Live price data dictionary
        """
        try:
            # Extract price and symbol
            current_price = price_data.get('ltp') or price_data.get('last_price', 0)
            symbol = price_data.get('symbol') or self._get_symbol_from_instrument_key(instrument_key)
            
            if not current_price or not symbol:
                return
            
            # Update positions for all users holding this symbol
            for user_id, portfolio in self.user_portfolios.items():
                if symbol in portfolio.get("positions", {}):
                    position = portfolio["positions"][symbol]
                    
                    # Update current price and unrealized P&L
                    position["current_price"] = current_price
                    position["unrealized_pnl"] = (
                        (current_price - position["entry_price"]) * position["quantity"]
                    )
                    position["unrealized_pnl_pct"] = (
                        (current_price - position["entry_price"]) / position["entry_price"] * 100
                    )
                    position["last_updated"] = datetime.now()
                    
                    # Check stop loss and target triggers
                    self._check_exit_conditions(user_id, symbol, current_price, position)
            
        except Exception as e:
            logger.error(f"❌ Error processing live tick for paper trading: {e}")
    
    def _get_symbol_from_instrument_key(self, instrument_key: str) -> Optional[str]:
        """Extract symbol from instrument key"""
        try:
            if instrument_registry:
                # Check if instrument exists in registry
                spot_data = instrument_registry._spot_instruments.get(instrument_key)
                if spot_data:
                    return spot_data.get('symbol')
            return None
        except Exception:
            return None
    
    def _check_exit_conditions(self, user_id: int, symbol: str, current_price: float, position: dict):
        """Check if position should be closed based on stop loss or target"""
        try:
            # Stop loss check
            if position.get("stop_loss") and current_price <= position["stop_loss"]:
                asyncio.create_task(
                    self._close_position(user_id, symbol, "STOP_LOSS_HIT")
                )
                logger.info(f"🛑 Stop loss triggered for {symbol} @ ₹{current_price}")
                return
            
            # Target check
            if position.get("target_price") and current_price >= position["target_price"]:
                asyncio.create_task(
                    self._close_position(user_id, symbol, "TARGET_REACHED")
                )
                logger.info(f"🎯 Target reached for {symbol} @ ₹{current_price}")
                return
                
        except Exception as e:
            logger.debug(f"Error checking exit conditions for {symbol}: {e}")


# Global instance
paper_trading_engine = PaperTradingEngine()
