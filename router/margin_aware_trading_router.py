"""
Margin-Aware Trading Router
API endpoints for margin-integrated trading operations
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from services.auth_service import get_current_user
from services.margin_aware_trading_service import get_margin_aware_trading_service
from services.broker_funds_sync_service import broker_funds_sync_service

logger = logging.getLogger(__name__)

margin_trading_router = APIRouter(prefix="/api/v1/margin-trading", tags=["Margin-Aware Trading"])


class PositionSizeRequest(BaseModel):
    stock_price: float
    broker_name: Optional[str] = None
    risk_percentage: Optional[float] = None


class TradeValidationRequest(BaseModel):
    quantity: int
    stock_price: float
    order_type: str = "BUY"
    broker_name: Optional[str] = None


@margin_trading_router.post("/calculate-position-size")
async def calculate_position_size(
    request: PositionSizeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculate optimal position size based on available margin
    
    This endpoint helps determine how many shares/contracts to buy
    based on the user's current margin availability and risk parameters.
    """
    try:
        service = get_margin_aware_trading_service(db)
        
        result = service.calculate_position_size(
            user_id=current_user.id,
            stock_price=request.stock_price,
            broker_name=request.broker_name,
            risk_percentage=request.risk_percentage
        )
        
        return {
            "success": True,
            "user_id": current_user.id,
            "calculation": result,
            "timestamp": "now"
        }
        
    except Exception as e:
        logger.error(f"Error calculating position size for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@margin_trading_router.post("/validate-trade")
async def validate_trade_order(
    request: TradeValidationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate if a trade order can be placed based on current margins
    
    Use this before placing actual orders to ensure sufficient margin
    and get risk warnings.
    """
    try:
        service = get_margin_aware_trading_service(db)
        
        result = service.validate_trade_order(
            user_id=current_user.id,
            quantity=request.quantity,
            stock_price=request.stock_price,
            order_type=request.order_type,
            broker_name=request.broker_name
        )
        
        return {
            "success": True,
            "user_id": current_user.id,
            "validation": result,
            "timestamp": "now"
        }
        
    except Exception as e:
        logger.error(f"Error validating trade for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@margin_trading_router.get("/trading-limits")
async def get_trading_limits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current trading limits based on available margin
    
    Returns daily trading limits, max trade value, and risk recommendations
    based on current margin utilization.
    """
    try:
        service = get_margin_aware_trading_service(db)
        
        limits = service.get_trading_limits(current_user.id)
        
        return {
            "success": True,
            "user_id": current_user.id,
            "limits": limits,
            "timestamp": "now"
        }
        
    except Exception as e:
        logger.error(f"Error getting trading limits for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@margin_trading_router.get("/margin-status")
async def get_margin_status(
    current_user: User = Depends(get_current_user),
):
    """
    Get comprehensive margin status across all brokers
    
    Returns detailed margin utilization, available funds, and risk metrics.
    """
    try:
        margin_summary = broker_funds_sync_service.get_user_margin_summary(current_user.id)
        
        return {
            "success": True,
            "user_id": current_user.id,
            "margin_summary": margin_summary,
            "timestamp": "now"
        }
        
    except Exception as e:
        logger.error(f"Error getting margin status for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@margin_trading_router.post("/sync-margin-data")
async def force_sync_margin_data(
    current_user: User = Depends(get_current_user),
):
    """
    Force immediate sync of margin data from all brokers
    
    Use this when you need the most up-to-date margin information
    before making critical trading decisions.
    """
    try:
        sync_result = await broker_funds_sync_service.force_sync_user_brokers(current_user.id)
        
        return {
            "success": True,
            "user_id": current_user.id,
            "sync_result": sync_result
        }
        
    except Exception as e:
        logger.error(f"Error syncing margin data for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@margin_trading_router.get("/available-margin")
async def get_available_margin(
    broker_name: Optional[str] = Query(None, description="Specific broker name (optional)"),
    current_user: User = Depends(get_current_user),
):
    """
    Get total available margin for trading
    
    Returns the sum of free margin across all active brokers,
    or for a specific broker if specified.
    """
    try:
        available_margin = broker_funds_sync_service.get_broker_available_margin(
            current_user.id, broker_name
        )
        
        return {
            "success": True,
            "user_id": current_user.id,
            "broker_name": broker_name or "all",
            "available_margin": available_margin,
            "formatted_margin": f"₹{available_margin:,.2f}",
            "timestamp": "now"
        }
        
    except Exception as e:
        logger.error(f"Error getting available margin for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@margin_trading_router.get("/monitor-trade/{trade_id}")
async def monitor_trade_margin(
    trade_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Monitor margin levels for an active trade
    
    Returns margin status and recommended actions for position management.
    """
    try:
        service = get_margin_aware_trading_service(db)
        
        monitoring_result = service.monitor_margin_during_trade(
            current_user.id, trade_id
        )
        
        return {
            "success": True,
            "user_id": current_user.id,
            "trade_id": trade_id,
            "monitoring": monitoring_result,
            "timestamp": "now"
        }
        
    except Exception as e:
        logger.error(f"Error monitoring trade {trade_id} for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@margin_trading_router.post("/sync-and-calculate")
async def sync_and_calculate_position(
    request: PositionSizeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Force sync margin data and calculate position size
    
    This endpoint first syncs the latest margin data from brokers,
    then calculates the optimal position size. Use for critical trades.
    """
    try:
        service = get_margin_aware_trading_service(db)
        
        result = await service.sync_and_calculate(
            current_user.id, request.stock_price
        )
        
        return {
            "success": True,
            "user_id": current_user.id,
            "result": result,
            "note": "Margin data synced before calculation"
        }
        
    except Exception as e:
        logger.error(f"Error in sync-and-calculate for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@margin_trading_router.get("/risk-assessment")
async def get_risk_assessment(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive risk assessment based on current margin usage
    
    Returns risk level, recommendations, and safety metrics.
    """
    try:
        service = get_margin_aware_trading_service(db)
        
        limits = service.get_trading_limits(current_user.id)
        margin_summary = broker_funds_sync_service.get_user_margin_summary(current_user.id)
        
        risk_assessment = {
            "risk_level": limits.get("risk_level", "UNKNOWN"),
            "margin_utilization": margin_summary.get("overall_utilization", 0),
            "recommendations": limits.get("recommendations", []),
            "trading_limits": {
                "max_trade_value": limits.get("max_trade_value", 0),
                "max_daily_trades": limits.get("max_daily_trades", 0)
            },
            "margin_breakdown": margin_summary.get("brokers", [])
        }
        
        return {
            "success": True,
            "user_id": current_user.id,
            "risk_assessment": risk_assessment,
            "timestamp": "now"
        }
        
    except Exception as e:
        logger.error(f"Error getting risk assessment for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))