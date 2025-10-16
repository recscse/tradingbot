"""
Trading Execution API Router
API endpoints for automated trading with paper/live modes, real-time PnL, and position management
"""

import asyncio
from datetime import date
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from decimal import Decimal

from database.connection import get_db
from database.models import (
    BrokerConfig,
    SelectedStock,
    User,
    ActivePosition,
    AutoTradeExecution,
    UserTradingConfig,
)
from router.auth_router import get_current_user
from services.trading_execution import (
    trade_prep_service,
    execution_handler,
    pnl_tracker,
    TradingMode,
    TradeStatus,
)
from services.enhanced_intelligent_options_selection import enhanced_options_service
from services.trading_execution.multi_demat_capital_service import (
    multi_demat_capital_service,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/trading/execution", tags=["Trading Execution"])


# ==================== Request Models ====================


class ExecuteTradeRequest(BaseModel):
    """Request model for trade execution"""

    stock_symbol: str = Field(..., description="Stock symbol")
    option_instrument_key: str = Field(..., description="Option instrument key")
    option_type: str = Field(..., description="CE or PE")
    strike_price: Decimal = Field(..., description="Strike price")
    expiry_date: str = Field(..., description="Expiry date (YYYY-MM-DD)")
    lot_size: int = Field(..., description="Lot size")
    trading_mode: str = Field("paper", description="Trading mode: paper or live")


class TradingModeConfig(BaseModel):
    """Trading mode configuration"""

    mode: str = Field(..., description="paper or live")
    auto_execute: bool = Field(False, description="Auto-execute trades")


# ==================== Endpoints ====================


@router.post("/prepare-trade")
async def prepare_trade(
    request: ExecuteTradeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Prepare trade with validation, capital check, and strategy signal

    **Process:**
    1. Validates user's broker configuration
    2. Checks available capital
    3. Fetches live option premium
    4. Generates SuperTrend + EMA trading signal
    5. Calculates position size and risk
    6. Returns prepared trade ready for execution

    **Returns:** PreparedTrade with complete execution details
    """
    try:
        trading_mode = TradingMode(request.trading_mode)

        prepared_trade = await trade_prep_service.prepare_trade(
            user_id=current_user.id,
            stock_symbol=request.stock_symbol,
            option_instrument_key=request.option_instrument_key,
            option_type=request.option_type,
            strike_price=request.strike_price,
            expiry_date=request.expiry_date,
            lot_size=request.lot_size,
            db=db,
            trading_mode=trading_mode,
        )

        return {
            "success": prepared_trade.status == TradeStatus.READY,
            "status": prepared_trade.status.value,
            "prepared_trade": {
                "stock_symbol": prepared_trade.stock_symbol,
                "option_type": prepared_trade.option_type,
                "strike_price": float(prepared_trade.strike_price),
                "expiry_date": prepared_trade.expiry_date,
                "current_premium": float(prepared_trade.current_premium),
                "entry_price": float(prepared_trade.entry_price),
                "stop_loss": float(prepared_trade.stop_loss),
                "target_price": float(prepared_trade.target_price),
                "position_size_lots": prepared_trade.position_size_lots,
                "total_investment": float(prepared_trade.total_investment),
                "max_loss_amount": float(prepared_trade.max_loss_amount),
                "risk_reward_ratio": float(prepared_trade.risk_reward_ratio),
                "trading_mode": prepared_trade.trading_mode,
                "broker_name": prepared_trade.broker_name,
                "signal": prepared_trade.signal,
                "capital_allocation": prepared_trade.capital_allocation,
                "metadata": prepared_trade.metadata,
            },
        }

    except Exception as e:
        logger.error(f"Error preparing trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute-trade")
async def execute_trade(
    request: ExecuteTradeRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Execute trade (paper or live) after preparation

    **Process:**
    1. Prepares trade with full validation
    2. Executes via broker API (live) or mock execution (paper)
    3. Creates trade execution record
    4. Creates active position for PnL tracking
    5. Starts real-time monitoring

    **Returns:** Execution result with trade ID and position details
    """
    try:
        # Prepare trade
        trading_mode = TradingMode(request.trading_mode)
        prepared_trade = await trade_prep_service.prepare_trade(
            user_id=current_user.id,
            stock_symbol=request.stock_symbol,
            option_instrument_key=request.option_instrument_key,
            option_type=request.option_type,
            strike_price=request.strike_price,
            expiry_date=request.expiry_date,
            lot_size=request.lot_size,
            db=db,
            trading_mode=trading_mode,
        )

        if prepared_trade.status != TradeStatus.READY:
            raise HTTPException(
                status_code=400,
                detail=f"Trade not ready: {prepared_trade.metadata.get('error', 'Unknown error')}",
            )

        # Execute trade
        execution_result = execution_handler.execute_trade(prepared_trade, db)

        if not execution_result.success:
            raise HTTPException(status_code=400, detail=execution_result.message)

        return {
            "success": True,
            "message": "Trade executed successfully",
            "trade_id": execution_result.trade_id,
            "order_id": execution_result.order_id,
            "entry_price": float(execution_result.entry_price),
            "quantity": execution_result.quantity,
            "status": execution_result.status,
            "trade_execution_id": execution_result.trade_execution_id,
            "active_position_id": execution_result.active_position_id,
            "metadata": execution_result.metadata,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-execute-selected-stocks")
async def auto_execute_selected_stocks(
    trading_mode: str = Query("paper", description="Trading mode: paper or live"),
    execution_mode: str = Query(
        "multi_demat", description="Execution mode: single_demat or multi_demat"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Auto-execute trades for all final selected stocks with options

    **Execution Modes:**
    - single_demat: Execute on default/first active broker only
    - multi_demat: Execute across ALL active brokers with proportional allocation

    **Process:**
    1. Gets final selected stocks with option contracts
    2. Prepares and executes trade for each stock
    3. Creates active positions for monitoring
    4. Returns summary of executions

    **Use Case:** Automated trading after stock selection completes
    """
    try:
        mode = TradingMode(trading_mode)

        # Get final options selections from database
        final_selections = enhanced_options_service.get_final_options_selections(db)

        if not final_selections:
            return {
                "success": False,
                "message": "No final stock selections with option contracts available",
                "executions": [],
                "total_selections": 0,
                "successful_executions": 0,
            }

        executions = []
        successful_executions = 0
        total_allocated_capital = 0
        total_quantity = 0

        # Multi-demat execution mode
        if execution_mode == "multi_demat":
            from services.trading_execution.multi_demat_executor import (
                multi_demat_executor,
            )

            logger.info(
                f"🚀 Multi-demat execution mode for {len(final_selections)} stocks"
            )

            for selection in final_selections:
                if not selection.get("option_instrument_key"):
                    continue

                try:
                    # Execute across all demats
                    multi_result = await multi_demat_executor.execute_across_all_demats(
                        user_id=current_user.id,
                        stock_symbol=selection["symbol"],
                        option_instrument_key=selection["option_instrument_key"],
                        option_type=selection["option_type"],
                        strike_price=Decimal(str(selection["strike_price"])),
                        expiry_date=selection["expiry_date"],
                        lot_size=selection["lot_size"],
                        premium_per_lot=Decimal(str(selection.get("premium", 0))),
                        db=db,
                        trading_mode=mode,
                    )

                    if multi_result.success:
                        successful_executions += multi_result.successful_executions
                        total_allocated_capital += float(
                            multi_result.total_allocated_capital
                        )
                        total_quantity += multi_result.total_quantity

                    executions.append(
                        {
                            "symbol": selection["symbol"],
                            "success": multi_result.success,
                            "parent_trade_id": multi_result.parent_trade_id,
                            "total_demats": multi_result.total_demats,
                            "successful_executions": multi_result.successful_executions,
                            "failed_executions": multi_result.failed_executions,
                            "total_allocated_capital": float(
                                multi_result.total_allocated_capital
                            ),
                            "total_quantity": multi_result.total_quantity,
                            "demat_executions": multi_result.executions,
                            "message": (
                                multi_result.error_message
                                if not multi_result.success
                                else "Success"
                            ),
                        }
                    )

                except Exception as e:
                    logger.error(
                        f"Error in multi-demat execution for {selection['symbol']}: {e}"
                    )
                    executions.append(
                        {
                            "symbol": selection["symbol"],
                            "success": False,
                            "message": str(e),
                        }
                    )

            return {
                "success": successful_executions > 0,
                "execution_mode": "multi_demat",
                "message": f"Multi-demat execution: {successful_executions} total trades executed",
                "total_selections": len(final_selections),
                "total_allocated_capital": total_allocated_capital,
                "total_quantity": total_quantity,
                "successful_executions": successful_executions,
                "executions": executions,
            }

        # Single demat execution mode (legacy)
        else:
            logger.info(
                f"📝 Single-demat execution mode for {len(final_selections)} stocks"
            )

            for selection in final_selections:
                if not selection.get("option_instrument_key"):
                    continue

                try:
                    # Prepare trade
                    prepared_trade = await trade_prep_service.prepare_trade(
                        user_id=current_user.id,
                        stock_symbol=selection["symbol"],
                        option_instrument_key=selection["option_instrument_key"],
                        option_type=selection["option_type"],
                        strike_price=Decimal(str(selection["strike_price"])),
                        expiry_date=selection["expiry_date"],
                        lot_size=selection["lot_size"],
                        db=db,
                        trading_mode=mode,
                    )

                    if prepared_trade.status == TradeStatus.READY:
                        # Execute trade
                        result = execution_handler.execute_trade(prepared_trade, db)

                        if result.success:
                            successful_executions += 1

                        executions.append(
                            {
                                "symbol": selection["symbol"],
                                "success": result.success,
                                "trade_id": result.trade_id,
                                "message": result.message,
                                "entry_price": float(result.entry_price),
                                "quantity": result.quantity,
                            }
                        )
                    else:
                        executions.append(
                            {
                                "symbol": selection["symbol"],
                                "success": False,
                                "message": f"Trade not ready: {prepared_trade.status.value}",
                            }
                        )

                except Exception as e:
                    logger.error(
                        f"Error executing trade for {selection['symbol']}: {e}"
                    )
                    executions.append(
                        {
                            "symbol": selection["symbol"],
                            "success": False,
                            "message": str(e),
                        }
                    )

            return {
                "success": successful_executions > 0,
                "execution_mode": "single_demat",
                "message": f"Executed {successful_executions}/{len(final_selections)} trades",
                "total_selections": len(final_selections),
                "successful_executions": successful_executions,
                "executions": executions,
            }

    except Exception as e:
        logger.error(f"Error in auto-execute: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active-positions")
async def get_active_positions(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get all active positions with real-time PnL

    **Returns:** List of active positions with current PnL, SL, targets
    """
    try:
        positions = (
            db.query(ActivePosition)
            .filter(
                ActivePosition.user_id == current_user.id,
                ActivePosition.is_active == True,
            )
            .all()
        )

        active_positions = []

        for position in positions:
            trade = (
                db.query(AutoTradeExecution)
                .filter(AutoTradeExecution.id == position.trade_execution_id)
                .first()
            )

            if trade:
                active_positions.append(
                    {
                        "position_id": position.id,
                        "trade_id": trade.trade_id,
                        "symbol": position.symbol,
                        "instrument_key": position.instrument_key,
                        "entry_price": float(trade.entry_price),
                        "current_price": (
                            float(position.current_price)
                            if position.current_price
                            else 0
                        ),
                        "quantity": trade.quantity,
                        "current_pnl": (
                            float(position.current_pnl) if position.current_pnl else 0
                        ),
                        "current_pnl_percentage": (
                            float(position.current_pnl_percentage)
                            if position.current_pnl_percentage
                            else 0
                        ),
                        "stop_loss": (
                            float(position.current_stop_loss)
                            if position.current_stop_loss
                            else 0
                        ),
                        "target": float(trade.target_1) if trade.target_1 else 0,
                        "highest_price_reached": (
                            float(position.highest_price_reached)
                            if position.highest_price_reached
                            else 0
                        ),
                        "trailing_stop_active": position.trailing_stop_triggered,
                        "entry_time": (
                            trade.entry_time.isoformat() if trade.entry_time else None
                        ),
                        "last_updated": (
                            position.last_updated.isoformat()
                            if position.last_updated
                            else None
                        ),
                    }
                )

        return {
            "success": True,
            "active_positions_count": len(active_positions),
            "active_positions": active_positions,
        }

    except Exception as e:
        logger.error(f"Error getting active positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pnl-summary")
async def get_pnl_summary(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get aggregate PnL summary for user

    **Returns:** Total PnL, investment, win rate, and position counts
    """
    try:
        summary = pnl_tracker.get_user_positions_summary(current_user.id, db)
        return {"success": True, "summary": summary}

    except Exception as e:
        logger.error(f"Error getting PnL summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start-auto-trading")
async def start_auto_trading(
    trading_mode: str = Query("paper", description="Trading mode: paper or live"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Start auto-trading for selected stocks

    **Process:**
    1. Loads user's selected stocks from database
    2. Subscribes to live feed for spot + option instruments
    3. Runs strategy on real-time data
    4. Auto-executes trades on valid signals
    5. Manages positions with trailing SL

    **Returns:** Auto-trading session details
    """
    try:
        from services.trading_execution.auto_trade_live_feed import auto_trade_live_feed

        # Get active broker for access token
        broker_config = (
            db.query(BrokerConfig)
            .filter(
                BrokerConfig.user_id == current_user.id,
                BrokerConfig.is_active == True,
                BrokerConfig.access_token.isnot(None),
            )
            .first()
        )

        if not broker_config:
            raise HTTPException(
                status_code=400,
                detail="No active broker configuration found. Please configure broker first.",
            )

        # Validate token expiry
        from datetime import datetime

        if (
            broker_config.access_token_expiry
            and broker_config.access_token_expiry < datetime.now()
        ):
            raise HTTPException(
                status_code=400, detail="Broker token expired. Please refresh token."
            )

        # Start auto-trading in background
        mode = TradingMode(trading_mode)
        asyncio.create_task(
            auto_trade_live_feed.start_auto_trading(
                user_id=current_user.id,
                access_token=broker_config.access_token,
                trading_mode=mode,
            )
        )

        return {
            "success": True,
            "message": "Auto-trading started successfully",
            "trading_mode": trading_mode,
            "broker": broker_config.broker_name,
            "monitored_stocks": len(auto_trade_live_feed.monitored_instruments),
            "stats": auto_trade_live_feed.stats,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting auto-trading: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop-auto-trading")
async def stop_auto_trading(current_user: User = Depends(get_current_user)):
    """
    Stop auto-trading

    **Process:**
    1. Stops WebSocket connection
    2. Stops strategy monitoring
    3. Does NOT close open positions

    **Returns:** Stop confirmation
    """
    try:
        from services.trading_execution.auto_trade_live_feed import auto_trade_live_feed

        await auto_trade_live_feed.stop()

        return {
            "success": True,
            "message": "Auto-trading stopped successfully",
            "final_stats": auto_trade_live_feed.stats,
        }

    except Exception as e:
        logger.error(f"Error stopping auto-trading: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enable-auto-mode")
async def enable_auto_mode(
    trading_mode: str = Query("paper", description="Trading mode: paper or live"),
    current_user: User = Depends(get_current_user),
):
    """
    Enable auto-mode: WebSocket starts automatically when stocks selected at 9:15 AM

    **Process:**
    1. Starts scheduler service
    2. Monitors stock selection
    3. Auto-starts WebSocket at 9:15 AM when stocks are selected
    4. Auto-stops when all positions closed

    **Returns:** Scheduler status
    """
    try:
        from services.trading_execution.auto_trade_scheduler import auto_trade_scheduler

        # Start scheduler in background
        mode = TradingMode(trading_mode)
        asyncio.create_task(
            auto_trade_scheduler.start_scheduler(
                user_id=current_user.id, trading_mode=mode
            )
        )

        return {
            "success": True,
            "message": "Auto-mode enabled - WebSocket will start automatically at 9:15 AM when stocks are selected",
            "trading_mode": trading_mode,
            "auto_start_time": "09:15 AM",
            "auto_stop": "When all positions closed",
        }

    except Exception as e:
        logger.error(f"Error enabling auto-mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disable-auto-mode")
async def disable_auto_mode(current_user: User = Depends(get_current_user)):
    """
    Disable auto-mode and stop scheduler

    **Returns:** Disable confirmation
    """
    try:
        from services.trading_execution.auto_trade_scheduler import auto_trade_scheduler
        from services.trading_execution.auto_trade_live_feed import auto_trade_live_feed

        # Stop scheduler
        await auto_trade_scheduler.stop_scheduler()

        # Stop auto-trading if running
        if auto_trade_live_feed.is_running:
            await auto_trade_live_feed.stop()

        return {"success": True, "message": "Auto-mode disabled successfully"}

    except Exception as e:
        logger.error(f"Error disabling auto-mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auto-trading-status")
async def get_auto_trading_status(current_user: User = Depends(get_current_user)):
    """
    Get auto-trading status

    **Returns:** Current auto-trading state and monitored instruments
    """
    try:
        from services.trading_execution.auto_trade_live_feed import auto_trade_live_feed
        from services.trading_execution.auto_trade_scheduler import auto_trade_scheduler

        monitored = []
        for inst_key, inst in auto_trade_live_feed.monitored_instruments.items():
            monitored.append(
                {
                    "symbol": inst.stock_symbol,
                    "option_type": inst.option_type,
                    "strike_price": float(inst.strike_price),
                    "state": inst.state.value,
                    "live_spot_price": float(inst.live_spot_price),
                    "live_option_premium": float(inst.live_option_premium),
                    "last_signal": (
                        inst.last_signal.signal_type.value if inst.last_signal else None
                    ),
                    "active_position_id": inst.active_position_id,
                }
            )

        return {
            "success": True,
            "auto_mode_enabled": auto_trade_scheduler.is_running,
            "websocket_running": auto_trade_live_feed.is_running,
            "auto_started_today": auto_trade_scheduler.auto_started_today,
            "monitored_stocks_count": len(auto_trade_live_feed.monitored_instruments),
            "monitored_stocks": monitored,
            "stats": auto_trade_live_feed.stats,
        }

    except Exception as e:
        logger.error(f"Error getting auto-trading status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/selected-stocks")
async def get_selected_stock(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Auto selected stock for trading"""
    try:

        # Query today's active selections
        selected_records = (
            db.query(SelectedStock)
            .filter(
                SelectedStock.selection_date == date.today(),
                SelectedStock.is_active == True,
            )
            .all()
        )

        def safe_parse_json(maybe_json):
            if not maybe_json:
                return {}
            if isinstance(maybe_json, dict):
                return maybe_json
            if isinstance(maybe_json, str):
                s = maybe_json.strip()
                if not s:
                    return {}
                try:
                    return json.loads(s)
                except Exception:
                    return {}
            return {}

        stocks = []
        for record in selected_records:
            try:
                # Parse stored JSON text columns
                score_breakdown_raw = getattr(record, "score_breakdown", None)
                score_breakdown = safe_parse_json(score_breakdown_raw)

                option_contract_raw = getattr(record, "option_contract", None)
                option_contract = safe_parse_json(option_contract_raw)

                # If option_contract missing, try to build a minimal contract from available columns
                # We treat instrument_key (SelectedStock.instrument_key) as the primary instrument identifier
                if not option_contract:
                    option_contract = {
                        "option_instrument_key": getattr(record, "instrument_key", "")
                        or "",
                        "option_type": getattr(record, "option_type", None) or "N/A",
                        # 'strike_price' might live inside score_breakdown under atm_strike or not exist
                        "strike_price": score_breakdown.get("atm_strike")
                        or getattr(record, "price_at_selection", 0)
                        or 0,
                        "expiry_date": getattr(record, "option_expiry_date", "") or "",
                        "premium": float(getattr(record, "price_at_selection", 0) or 0),
                        # lot_size may not be available on the SelectedStock row; default 0
                        "lot_size": int(score_breakdown.get("lot_size", 0) or 0),
                    }

                # Ensure instrument_key is present on the contract (helpful for websocket matching)
                if (
                    "option_instrument_key" not in option_contract
                    or not option_contract.get("option_instrument_key")
                ):
                    option_contract["option_instrument_key"] = (
                        getattr(record, "instrument_key", "") or ""
                    )

                # Normalize numeric types in score_breakdown
                normalized_score = {
                    "capital_allocation": float(
                        score_breakdown.get("capital_allocation", 0) or 0
                    ),
                    "position_size_lots": int(
                        score_breakdown.get("position_size_lots", 0) or 0
                    ),
                    "max_loss": float(score_breakdown.get("max_loss", 0) or 0),
                    "target_profit": float(
                        score_breakdown.get("target_profit", 0) or 0
                    ),
                }
                if "components" in score_breakdown and isinstance(
                    score_breakdown["components"], dict
                ):
                    normalized_score["components"] = score_breakdown["components"]

                # Build market_sentiment object from model columns (if present)
                market_sentiment_obj = {}
                if getattr(record, "market_sentiment", None):
                    market_sentiment_obj["sentiment"] = record.market_sentiment
                    market_sentiment_obj["confidence"] = float(
                        record.market_sentiment_confidence or 0
                    )
                    market_sentiment_obj["advance_decline_ratio"] = float(
                        record.advance_decline_ratio or 0
                    )
                    market_sentiment_obj["market_breadth_percent"] = float(
                        record.market_breadth_percent or 0
                    )
                    market_sentiment_obj["advancing_stocks"] = int(
                        record.advancing_stocks or 0
                    )
                    market_sentiment_obj["declining_stocks"] = int(
                        record.declining_stocks or 0
                    )
                # If not present, leave empty dict (frontend should treat {} as "no data")

                stock_data = {
                    "id": record.id,
                    "symbol": record.symbol,
                    "sector": record.sector,
                    "selection_score": record.selection_score,
                    "selection_reason": record.selection_reason,
                    "price_at_selection": record.price_at_selection,
                    "option_type": record.option_type or "NEUTRAL",
                    "atm_strike": score_breakdown.get("atm_strike", 0.0),
                    "adr_score": score_breakdown.get("adr_score", 0.5),
                    "sector_momentum": score_breakdown.get("sector_momentum", 0.0),
                    "volume_score": score_breakdown.get("volume_score", 0.5),
                    "technical_score": score_breakdown.get("technical_score", 0.5),
                    "expiry_date": record.option_expiry_date or "",
                    "market_sentiment_alignment": record.option_type in ["CE", "PE"],
                    "selection_date": record.selection_date.isoformat(),
                    "change_percent": 0.0,  # Will be updated with real-time data
                }
                stocks.append(stock_data)
            except Exception as e:
                logger.exception(
                    f"selected-stocks: failed to process record {getattr(record,'symbol','?')}: {e}"
                )
                continue
        market_sentiment = {}
        # If global auto_stock_selection_service or another provider is present, prefer it.
        return {
            "success": True,
            "stocks": stocks,
            "market_sentiment": market_sentiment,
        }

    except Exception as e:
        logger.exception(f"Error getting selected stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/selected-stocks-live-prices")
async def get_selected_stocks_live_prices(
    current_user: User = Depends(get_current_user),
):
    """
    Get live prices for selected stocks from auto-trading WebSocket

    **Returns:**
    - Live spot prices
    - Live option premiums
    - Price changes from selection
    - Unrealized PnL (hypothetical if not in position, actual if in position)
    - State (monitoring, position_open, etc.)

    **Use Case:** Display live prices in Selected Stocks table with real-time updates
    """
    try:
        from services.trading_execution.auto_trade_live_feed import auto_trade_live_feed

        if not auto_trade_live_feed.is_running:
            return {
                "success": False,
                "message": "Auto-trading WebSocket not running. Start auto-trading first.",
                "live_prices": [],
            }

        live_prices = auto_trade_live_feed.get_live_prices()

        return {
            "success": True,
            "live_prices": live_prices,
            "count": len(live_prices),
            "websocket_running": auto_trade_live_feed.is_running,
        }

    except Exception as e:
        logger.error(f"Error getting live prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trade-history")
async def get_trade_history(
    limit: int = Query(50, description="Number of trades to fetch"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get trade execution history

    **Returns:** List of closed trades with PnL details
    """
    try:
        trades = (
            db.query(AutoTradeExecution)
            .filter(
                AutoTradeExecution.user_id == current_user.id,
                AutoTradeExecution.status == "CLOSED",
            )
            .order_by(AutoTradeExecution.exit_time.desc())
            .limit(limit)
            .all()
        )

        trade_history = []

        for trade in trades:
            trade_history.append(
                {
                    "trade_id": trade.trade_id,
                    "symbol": trade.symbol,
                    "signal_type": trade.signal_type,
                    "entry_time": (
                        trade.entry_time.isoformat() if trade.entry_time else None
                    ),
                    "exit_time": (
                        trade.exit_time.isoformat() if trade.exit_time else None
                    ),
                    "entry_price": float(trade.entry_price),
                    "exit_price": float(trade.exit_price) if trade.exit_price else 0,
                    "quantity": trade.quantity,
                    "gross_pnl": float(trade.gross_pnl) if trade.gross_pnl else 0,
                    "net_pnl": float(trade.net_pnl) if trade.net_pnl else 0,
                    "pnl_percentage": (
                        float(trade.pnl_percentage) if trade.pnl_percentage else 0
                    ),
                    "exit_reason": trade.exit_reason,
                    "strategy_name": trade.strategy_name,
                }
            )

        return {
            "success": True,
            "trade_count": len(trade_history),
            "trades": trade_history,
        }

    except Exception as e:
        logger.error(f"Error getting trade history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-trading-preferences")
async def get_user_trading_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get user's trading mode and execution mode preferences

    Returns:
        trading_mode: "paper" or "live"
        execution_mode: "single_demat" or "multi_demat"
    """
    try:
        # Get or create user trading config
        trading_config = (
            db.query(UserTradingConfig)
            .filter(UserTradingConfig.user_id == current_user.id)
            .first()
        )

        if not trading_config:
            # Create default config
            trading_config = UserTradingConfig(
                user_id=current_user.id,
                trading_mode="paper",
                execution_mode="multi_demat",
            )
            db.add(trading_config)
            db.commit()
            db.refresh(trading_config)

        return {
            "success": True,
            "trading_mode": trading_config.trading_mode or "paper",
            "execution_mode": trading_config.execution_mode or "multi_demat",
        }

    except Exception as e:
        logger.error(f"Error getting user trading preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user-trading-preferences")
async def update_user_trading_preferences(
    trading_mode: str = Query(..., description="Trading mode: paper or live"),
    execution_mode: str = Query(
        ..., description="Execution mode: single_demat or multi_demat"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update user's trading mode and execution mode preferences

    Args:
        trading_mode: "paper" or "live"
        execution_mode: "single_demat" or "multi_demat"
    """
    try:
        # Validate inputs
        if trading_mode not in ["paper", "live"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid trading_mode. Must be 'paper' or 'live'",
            )

        if execution_mode not in ["single_demat", "multi_demat"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid execution_mode. Must be 'single_demat' or 'multi_demat'",
            )

        # Get or create user trading config
        trading_config = (
            db.query(UserTradingConfig)
            .filter(UserTradingConfig.user_id == current_user.id)
            .first()
        )

        if not trading_config:
            # Create new config
            trading_config = UserTradingConfig(
                user_id=current_user.id,
                trading_mode=trading_mode,
                execution_mode=execution_mode,
            )
            db.add(trading_config)
        else:
            # Update existing config
            trading_config.trading_mode = trading_mode
            trading_config.execution_mode = execution_mode

        db.commit()
        db.refresh(trading_config)

        logger.info(
            f"Updated trading preferences for user {current_user.id}: mode={trading_mode}, execution={execution_mode}"
        )

        return {
            "success": True,
            "message": "Trading preferences updated successfully",
            "trading_mode": trading_config.trading_mode,
            "execution_mode": trading_config.execution_mode,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user trading preferences: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error(f"Error getting trade history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/close-position/{position_id}")
async def close_position_manually(
    position_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Manually close an active position

    **Args:** position_id - Active position ID to close

    **Returns:** Closure confirmation with final PnL
    """
    try:
        position = (
            db.query(ActivePosition)
            .filter(
                ActivePosition.id == position_id,
                ActivePosition.user_id == current_user.id,
                ActivePosition.is_active == True,
            )
            .first()
        )

        if not position:
            raise HTTPException(status_code=404, detail="Active position not found")

        trade_execution = (
            db.query(AutoTradeExecution)
            .filter(AutoTradeExecution.id == position.trade_execution_id)
            .first()
        )

        if not trade_execution:
            raise HTTPException(status_code=404, detail="Trade execution not found")

        # Get current price
        from services.realtime_market_engine import get_market_engine

        market_engine = get_market_engine()

        current_price = Decimal("0")
        if position.instrument_key in market_engine.instruments:
            current_price = Decimal(
                str(market_engine.instruments[position.instrument_key].current_price)
            )
        else:
            current_price = Decimal(str(position.current_price))

        # Close position
        await pnl_tracker._close_position(
            position, trade_execution, current_price, "MANUAL_EXIT", db
        )

        return {
            "success": True,
            "message": "Position closed successfully",
            "trade_id": trade_execution.trade_id,
            "exit_price": float(current_price),
            "pnl": float(trade_execution.net_pnl) if trade_execution.net_pnl else 0,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-capital-overview")
async def get_user_capital_overview(
    trading_mode: str = Query("paper", description="Trading mode: paper or live"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get aggregated capital overview from all user's demat accounts

    **Returns:**
    - Total available capital across all demats
    - Per-demat capital breakdown
    - Capital utilization percentage
    - Max trade allocation allowed
    - Token validity status per demat

    **Use Case:** Display capital dashboard in UI before trade execution
    """
    try:
        capital_overview = multi_demat_capital_service.get_user_total_capital(
            user_id=current_user.id, db=db, trading_mode=trading_mode
        )

        return {"success": True, "capital_overview": capital_overview}

    except Exception as e:
        logger.error(f"Error getting capital overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/capital-allocation-plan")
async def get_capital_allocation_plan(
    required_capital: float = Query(..., description="Required capital for trade"),
    trading_mode: str = Query("paper", description="Trading mode: paper or live"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get capital allocation plan across demats for a trade

    **Returns:**
    - Whether trade can be executed
    - Proportional allocation across demats
    - Per-demat allocation details
    - Rejection reason if trade cannot be executed

    **Use Case:** Validate and plan trade before execution
    """
    try:
        required_decimal = Decimal(str(required_capital))

        allocation_plan = multi_demat_capital_service.get_capital_summary_for_trade(
            user_id=current_user.id,
            required_capital=required_decimal,
            db=db,
            trading_mode=trading_mode,
        )

        return {"success": True, "allocation_plan": allocation_plan}

    except Exception as e:
        logger.error(f"Error getting allocation plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))
