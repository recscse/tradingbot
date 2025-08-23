# # router/unified_trading_router.py
# """
# 🎯 UNIFIED TRADING API ROUTER
# Handles both Paper Trading and Live Trading modes with comprehensive features
# """

# from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
# from sqlalchemy.orm import Session
# from datetime import datetime, date
# from typing import List, Dict, Any, Optional
# import logging
# import json
# import asyncio

# from database.connection import get_db
# from database.models import User, BrokerConfig, PaperTrade, TradingSession
# from services.trading_stock_selector import TradingStockSelector
# from services.enhanced_market_analytics import enhanced_analytics
# from services.auth_service import get_current_user

# logger = logging.getLogger(__name__)

# # Import broker services
# try:
#     from brokers.upstox_broker import UpstoxBroker

#     # from brokers.angel_one_broker import AngelOneBroker
#     from brokers.dhan_broker import DhanBroker

#     # from brokers.fyers_broker import FyersBroker
#     from brokers.zerodha_broker import ZerodhaBroker

#     BROKER_SERVICES_AVAILABLE = True
# except ImportError as e:
#     logger.warning(f"⚠️ Broker services not available: {e}")
#     BROKER_SERVICES_AVAILABLE = False

# router = APIRouter(prefix="/api/unified-trading", tags=["Unified Trading"])

# # Broker mapping
# BROKER_CLASSES = {
#     "upstox": UpstoxBroker if BROKER_SERVICES_AVAILABLE else None,
#     # "angel_one": AngelOneBroker if BROKER_SERVICES_AVAILABLE else None,
#     "dhan": DhanBroker if BROKER_SERVICES_AVAILABLE else None,
#     # "fyers": FyersBroker if BROKER_SERVICES_AVAILABLE else None,
#     "zerodha": ZerodhaBroker if BROKER_SERVICES_AVAILABLE else None,
# }


# # Trading modes
# class TradingMode:
#     PAPER = "PAPER"
#     LIVE = "LIVE"


# def get_user_broker(user_id: int, db: Session):
#     """Get user's primary broker configuration and instance"""
#     try:
#         broker_config = (
#             db.query(BrokerConfig)
#             .filter(BrokerConfig.user_id == user_id, BrokerConfig.is_active == True)
#             .first()
#         )

#         if not broker_config:
#             return None, None

#         broker_name = broker_config.broker_name.lower()
#         BrokerClass = BROKER_CLASSES.get(broker_name)

#         if not BrokerClass:
#             return None, None

#         broker_credentials = (
#             json.loads(broker_config.credentials) if broker_config.credentials else {}
#         )
#         broker_instance = BrokerClass(
#             api_key=broker_credentials.get("api_key"),
#             api_secret=broker_credentials.get("api_secret"),
#             access_token=broker_config.access_token,
#             **broker_credentials,
#         )

#         return broker_instance, broker_config

#     except Exception as e:
#         logger.error(f"Error getting user broker: {e}")
#         return None, None


# def get_or_create_paper_portfolio(user_id: int, db: Session) -> dict:
#     """Get or create paper trading portfolio"""
#     session = (
#         db.query(TradingSession)
#         .filter(TradingSession.user_id == user_id)
#         .order_by(TradingSession.start_time.desc())
#         .first()
#     )

#     if not session:
#         return {
#             "initial_balance": 1000000.0,
#             "current_balance": 1000000.0,
#             "current_portfolio_value": 1000000.0,
#             "total_pnl": 0.0,
#             "total_pnl_pct": 0.0,
#             "is_active": False,
#             "positions_count": 0,
#             "winning_trades": 0,
#             "total_trades": 0,
#             "win_rate": 0.0,
#         }

#     is_active = session.end_time is None

#     # Get active positions
#     positions = (
#         db.query(PaperTrade)
#         .filter(PaperTrade.user_id == user_id, PaperTrade.status == "OPEN")
#         .all()
#     )

#     # Get total trades
#     total_trades = db.query(PaperTrade).filter(PaperTrade.user_id == user_id).count()

#     # Get winning trades
#     winning_trades = (
#         db.query(PaperTrade)
#         .filter(PaperTrade.user_id == user_id, PaperTrade.profit_loss > 0)
#         .count()
#     )

#     win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

#     return {
#         "initial_balance": 1000000.0,
#         "current_balance": 1000000.0 + session.total_pnl,
#         "current_portfolio_value": 1000000.0 + session.total_pnl,
#         "total_pnl": session.total_pnl,
#         "total_pnl_pct": (
#             (session.total_pnl / 1000000.0 * 100) if session.total_pnl else 0.0
#         ),
#         "is_active": is_active,
#         "positions_count": len(positions),
#         "winning_trades": winning_trades,
#         "total_trades": total_trades,
#         "win_rate": win_rate,
#         "unrealized_pnl": sum(pos.profit_loss or 0 for pos in positions),
#     }


#     # Get winning trades
#     winning_trades = (
#         db.query(LiveTrade)
#         .filter(LiveTrade.user_id == user_id, LiveTrade.realized_pnl > 0)
#         .count()
#     )

#     win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

#     return {
#         "initial_balance": portfolio.initial_balance,
#         "current_balance": portfolio.current_balance,
#         "current_portfolio_value": portfolio.current_portfolio_value,
#         "total_pnl": portfolio.total_pnl,
#         "total_pnl_pct": portfolio.total_pnl_pct,
#         "is_active": portfolio.is_active,
#         "positions_count": len(positions),
#         "winning_trades": winning_trades,
#         "total_trades": total_trades,
#         "win_rate": win_rate,
#         "unrealized_pnl": sum(pos.unrealized_pnl or 0 for pos in positions),
#     }


# @router.post("/start")
# async def start_unified_trading(
#     request_data: Dict[str, Any],
#     background_tasks: BackgroundTasks,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     """
#     🚀 Start unified trading (Paper or Live mode)
#     """
#     try:
#         trading_mode = request_data.get("trading_mode", TradingMode.PAPER)
#         selected_stocks = request_data.get("selected_stocks", [])
#         strategy_config = request_data.get("strategy_config", {})
#         initial_balance = request_data.get("initial_balance", 1000000.0)

#         if not selected_stocks:
#             raise HTTPException(
#                 status_code=400, detail="No stocks selected for trading"
#             )

#         logger.info(f"🎯 Starting {trading_mode} trading for user {current_user.id}")

#         if trading_mode == TradingMode.LIVE:
#             # Live trading validation
#             if not BROKER_SERVICES_AVAILABLE:
#                 raise HTTPException(
#                     status_code=503,
#                     detail="Broker services are not available. Live trading is disabled.",
#                 )

#             broker, broker_config = get_user_broker(current_user.id, db)
#             if not broker:
#                 raise HTTPException(
#                     status_code=400,
#                     detail="No active broker configuration found. Please configure a broker first.",
#                 )

#             # Validate broker connection
#             try:
#                 profile = await broker.get_profile()
#                 funds = await broker.get_funds()
#                 available_margin = funds.get("available_margin", 0.0)

#                 if available_margin < 10000:  # Minimum ₹10,000 required
#                     raise HTTPException(
#                         status_code=400,
#                         detail=f"Insufficient funds: ₹{available_margin:,.2f} available. Minimum ₹10,000 required.",
#                     )

#             except Exception as e:
#                 raise HTTPException(
#                     status_code=400,
#                     detail=f"Broker connection failed: {str(e)}. Please check your broker configuration.",
#                 )

#             # Create/update live portfolio
#             portfolio = (
#                 db.query(LivePortfolio)
#                 .filter(LivePortfolio.user_id == current_user.id)
#                 .first()
#             )
#             if not portfolio:
#                 portfolio = LivePortfolio(
#                     user_id=current_user.id,
#                     initial_balance=available_margin,
#                     current_balance=available_margin,
#                     current_portfolio_value=available_margin,
#                     total_pnl=0.0,
#                     total_pnl_pct=0.0,
#                     is_active=True,
#                     created_at=datetime.utcnow(),
#                 )
#                 db.add(portfolio)
#             else:
#                 portfolio.current_balance = available_margin
#                 portfolio.is_active = True
#                 portfolio.updated_at = datetime.utcnow()

#             portfolio.strategy_config = json.dumps(strategy_config)
#             portfolio.selected_stocks = json.dumps(selected_stocks)

#         else:
#             # Paper trading
#             session = (
#                 db.query(TradingSession)
#                 .filter(
#                     TradingSession.user_id == current_user.id,
#                     TradingSession.end_time == None,
#                 )
#                 .first()
#             )

#             if not session:
#                 session = TradingSession(
#                     user_id=current_user.id,
#                     start_time=datetime.utcnow(),
#                     total_pnl=0.0,
#                 )
#                 db.add(session)
#                 db.commit()
#                 db.refresh(session)

#             # Create paper trades for selected stocks
#             trades_created = 0
#             for stock in selected_stocks:
#                 symbol = stock.get("symbol")
#                 quantity = stock.get("quantity", 1)
#                 price = stock.get("price_at_selection", 0.0)

#                 if not symbol or price <= 0:
#                     continue

#                 paper_trade = PaperTrade(
#                     user_id=current_user.id,
#                     strategy_id=None,
#                     symbol=symbol,
#                     trade_type="BUY",
#                     entry_price=price,
#                     quantity=quantity,
#                     status="OPEN",
#                     profit_loss=0.0,
#                     created_at=datetime.utcnow(),
#                 )

#                 db.add(paper_trade)
#                 trades_created += 1

#         db.commit()

#         # Start background trading process
#         background_tasks.add_task(
#             execute_trading_strategy,
#             user_id=current_user.id,
#             trading_mode=trading_mode,
#             selected_stocks=selected_stocks,
#             strategy_config=strategy_config,
#         )

#         return {
#             "success": True,
#             "message": f"{trading_mode} trading started successfully",
#             "trading_mode": trading_mode,
#             "selected_stocks_count": len(selected_stocks),
#             "initial_balance": (
#                 initial_balance
#                 if trading_mode == TradingMode.PAPER
#                 else available_margin
#             ),
#             "warning": (
#                 "⚠️ LIVE TRADING ACTIVE - Real money will be used!"
#                 if trading_mode == TradingMode.LIVE
#                 else None
#             ),
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"❌ Error starting unified trading: {e}")
#         raise HTTPException(
#             status_code=500, detail=f"Failed to start trading: {str(e)}"
#         )


# @router.post("/stop")
# async def stop_unified_trading(
#     request_data: Dict[str, Any],
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     """
#     🛑 Stop unified trading (Paper or Live mode)
#     """
#     try:
#         trading_mode = request_data.get("trading_mode", TradingMode.PAPER)

#         logger.info(f"🛑 Stopping {trading_mode} trading for user {current_user.id}")

#         if trading_mode == TradingMode.LIVE:
#             # Stop live trading
#             portfolio = (
#                 db.query(LivePortfolio)
#                 .filter(LivePortfolio.user_id == current_user.id)
#                 .first()
#             )
#             if portfolio:
#                 portfolio.is_active = False
#                 portfolio.updated_at = datetime.utcnow()

#             # Get active positions for square off count
#             positions = (
#                 db.query(LivePosition)
#                 .filter(
#                     LivePosition.user_id == current_user.id,
#                     LivePosition.is_active == True,
#                 )
#                 .all()
#             )

#             # In a real implementation, you would square off positions here
#             squared_off_count = len(positions)

#         else:
#             # Stop paper trading
#             session = (
#                 db.query(TradingSession)
#                 .filter(
#                     TradingSession.user_id == current_user.id,
#                     TradingSession.end_time == None,
#                 )
#                 .first()
#             )

#             if session:
#                 session.end_time = datetime.utcnow()

#             trades = (
#                 db.query(PaperTrade)
#                 .filter(
#                     PaperTrade.user_id == current_user.id, PaperTrade.status == "OPEN"
#                 )
#                 .all()
#             )

#             squared_off_count = len(trades)

#         db.commit()

#         return {
#             "success": True,
#             "message": f"{trading_mode} trading stopped successfully",
#             "trading_mode": trading_mode,
#             "squared_off_positions": squared_off_count,
#         }

#     except Exception as e:
#         logger.error(f"❌ Error stopping unified trading: {e}")
#         raise HTTPException(status_code=500, detail=f"Failed to stop trading: {str(e)}")


# @router.get("/portfolio")
# async def get_unified_portfolio(
#     trading_mode: str = TradingMode.PAPER,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     """Get unified trading portfolio (Paper or Live mode)"""
#     try:
#         if trading_mode == TradingMode.LIVE:
#             portfolio_data = get_or_create_live_portfolio(current_user.id, db)

#             # Try to get real-time data from broker
#             broker, _ = get_user_broker(current_user.id, db)
#             if broker:
#                 try:
#                     funds = await broker.get_funds()
#                     portfolio_data["current_balance"] = funds.get(
#                         "available_margin", portfolio_data["current_balance"]
#                     )
#                     portfolio_data["current_portfolio_value"] = funds.get(
#                         "available_margin", portfolio_data["current_portfolio_value"]
#                     )
#                 except Exception as e:
#                     logger.warning(f"Could not fetch real-time broker data: {e}")
#         else:
#             portfolio_data = get_or_create_paper_portfolio(current_user.id, db)

#         return {
#             "success": True,
#             "trading_mode": trading_mode,
#             "portfolio": portfolio_data,
#         }

#     except Exception as e:
#         logger.error(f"Error getting unified portfolio: {e}")
#         raise HTTPException(status_code=500, detail="Failed to get portfolio")


# @router.get("/positions")
# async def get_unified_positions(
#     trading_mode: str = TradingMode.PAPER,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     """Get unified trading positions (Paper or Live mode)"""
#     try:
#         positions_data = []

#         if trading_mode == TradingMode.LIVE:
#             positions = (
#                 db.query(LivePosition)
#                 .filter(LivePosition.user_id == current_user.id)
#                 .order_by(LivePosition.created_at.desc())
#                 .all()
#             )

#             for pos in positions:
#                 positions_data.append(
#                     {
#                         "symbol": pos.symbol,
#                         "side": pos.side,
#                         "quantity": pos.quantity,
#                         "avg_price": pos.avg_price,
#                         "current_price": pos.current_price,
#                         "unrealized_pnl": pos.unrealized_pnl,
#                         "unrealized_pnl_pct": pos.unrealized_pnl_pct,
#                         "is_active": pos.is_active,
#                         "entry_time": (
#                             pos.entry_time.isoformat() if pos.entry_time else None
#                         ),
#                         "exit_time": (
#                             pos.exit_time.isoformat() if pos.exit_time else None
#                         ),
#                         "stop_loss": getattr(pos, "stop_loss", None),
#                         "target_price": getattr(pos, "target_price", None),
#                     }
#                 )
#         else:
#             positions = (
#                 db.query(PaperTrade)
#                 .filter(
#                     PaperTrade.user_id == current_user.id, PaperTrade.status == "OPEN"
#                 )
#                 .order_by(PaperTrade.created_at.desc())
#                 .all()
#             )

#             for pos in positions:
#                 positions_data.append(
#                     {
#                         "symbol": pos.symbol,
#                         "side": pos.trade_type,
#                         "quantity": pos.quantity,
#                         "avg_price": pos.entry_price,
#                         "current_price": pos.entry_price,  # In paper trading, use entry price
#                         "unrealized_pnl": pos.profit_loss or 0,
#                         "unrealized_pnl_pct": 0.0,
#                         "is_active": pos.status == "OPEN",
#                         "entry_time": (
#                             pos.created_at.isoformat() if pos.created_at else None
#                         ),
#                         "exit_time": None,
#                         "stop_loss": None,
#                         "target_price": None,
#                     }
#                 )

#         return {
#             "success": True,
#             "trading_mode": trading_mode,
#             "positions": positions_data,
#         }

#     except Exception as e:
#         logger.error(f"Error getting unified positions: {e}")
#         raise HTTPException(status_code=500, detail="Failed to get positions")


# @router.get("/trades")
# async def get_unified_trades(
#     trading_mode: str = TradingMode.PAPER,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
#     limit: int = 50,
# ):
#     """Get unified trading history (Paper or Live mode)"""
#     try:
#         trades_data = []

#         if trading_mode == TradingMode.LIVE:
#             trades = (
#                 db.query(LiveTrade)
#                 .filter(LiveTrade.user_id == current_user.id)
#                 .order_by(LiveTrade.timestamp.desc())
#                 .limit(limit)
#                 .all()
#             )

#             for trade in trades:
#                 trades_data.append(
#                     {
#                         "symbol": trade.symbol,
#                         "action": trade.action,
#                         "quantity": trade.quantity,
#                         "price": trade.price,
#                         "order_type": trade.order_type,
#                         "status": trade.status,
#                         "pnl": trade.realized_pnl,
#                         "timestamp": trade.timestamp.isoformat(),
#                         "exit_reason": getattr(trade, "exit_reason", None),
#                         "strategy": getattr(trade, "strategy", None),
#                     }
#                 )
#         else:
#             trades = (
#                 db.query(PaperTrade)
#                 .filter(PaperTrade.user_id == current_user.id)
#                 .order_by(PaperTrade.created_at.desc())
#                 .limit(limit)
#                 .all()
#             )

#             for trade in trades:
#                 trades_data.append(
#                     {
#                         "symbol": trade.symbol,
#                         "action": trade.trade_type,
#                         "quantity": trade.quantity,
#                         "price": trade.entry_price,
#                         "order_type": "MARKET",
#                         "status": trade.status,
#                         "pnl": trade.profit_loss,
#                         "timestamp": (
#                             trade.created_at.isoformat() if trade.created_at else None
#                         ),
#                         "exit_reason": None,
#                         "strategy": None,
#                     }
#                 )

#         return {
#             "success": True,
#             "trading_mode": trading_mode,
#             "trades": trades_data,
#         }

#     except Exception as e:
#         logger.error(f"Error getting unified trades: {e}")
#         raise HTTPException(status_code=500, detail="Failed to get trades")


# @router.get("/analytics")
# async def get_trading_analytics(
#     trading_mode: str = TradingMode.PAPER,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     """Get comprehensive trading analytics"""
#     try:
#         if trading_mode == TradingMode.LIVE:
#             trades = (
#                 db.query(LiveTrade).filter(LiveTrade.user_id == current_user.id).all()
#             )
#         else:
#             trades = (
#                 db.query(PaperTrade).filter(PaperTrade.user_id == current_user.id).all()
#             )

#         if not trades:
#             return {
#                 "success": True,
#                 "trading_mode": trading_mode,
#                 "analytics": {
#                     "total_trades": 0,
#                     "winning_trades": 0,
#                     "losing_trades": 0,
#                     "win_rate": 0.0,
#                     "gross_profit": 0.0,
#                     "gross_loss": 0.0,
#                     "net_profit": 0.0,
#                     "profit_factor": 0.0,
#                     "avg_win": 0.0,
#                     "avg_loss": 0.0,
#                     "largest_win": 0.0,
#                     "largest_loss": 0.0,
#                     "risk_reward_ratio": 0.0,
#                 },
#             }

#         # Calculate analytics
#         total_trades = len(trades)
#         winning_trades = []
#         losing_trades = []

#         for trade in trades:
#             pnl = (
#                 trade.realized_pnl
#                 if trading_mode == TradingMode.LIVE
#                 else trade.profit_loss
#             )
#             if pnl and pnl > 0:
#                 winning_trades.append(pnl)
#             elif pnl and pnl < 0:
#                 losing_trades.append(abs(pnl))

#         win_count = len(winning_trades)
#         loss_count = len(losing_trades)
#         win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0

#         gross_profit = sum(winning_trades) if winning_trades else 0.0
#         gross_loss = sum(losing_trades) if losing_trades else 0.0
#         net_profit = gross_profit - gross_loss
#         profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

#         avg_win = (gross_profit / win_count) if win_count > 0 else 0.0
#         avg_loss = (gross_loss / loss_count) if loss_count > 0 else 0.0
#         largest_win = max(winning_trades) if winning_trades else 0.0
#         largest_loss = max(losing_trades) if losing_trades else 0.0
#         risk_reward_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0.0

#         return {
#             "success": True,
#             "trading_mode": trading_mode,
#             "analytics": {
#                 "total_trades": total_trades,
#                 "winning_trades": win_count,
#                 "losing_trades": loss_count,
#                 "win_rate": win_rate,
#                 "gross_profit": gross_profit,
#                 "gross_loss": gross_loss,
#                 "net_profit": net_profit,
#                 "profit_factor": profit_factor,
#                 "avg_win": avg_win,
#                 "avg_loss": avg_loss,
#                 "largest_win": largest_win,
#                 "largest_loss": largest_loss,
#                 "risk_reward_ratio": risk_reward_ratio,
#             },
#         }

#     except Exception as e:
#         logger.error(f"Error getting trading analytics: {e}")
#         raise HTTPException(status_code=500, detail="Failed to get analytics")


# async def execute_trading_strategy(
#     user_id: int, trading_mode: str, selected_stocks: List[Dict], strategy_config: Dict
# ):
#     """
#     Background task to execute trading strategy
#     """
#     logger.info(f"🎯 Executing {trading_mode} trading strategy for user {user_id}")

#     # This is a placeholder for the actual trading strategy execution
#     # In a real implementation, this would:
#     # 1. Monitor selected stocks for entry/exit signals
#     # 2. Execute trades based on strategy configuration
#     # 3. Manage risk (stop-loss, take-profit)
#     # 4. Update positions and portfolio in real-time
#     # 5. Log all decisions and execution details

#     logger.info(
#         f"📊 {trading_mode} trading strategy started for {len(selected_stocks)} stocks"
#     )

#     # TODO: Implement actual strategy execution logic
#     await asyncio.sleep(1)  # Placeholder
