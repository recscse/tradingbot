"""
Paper Trading API Routes
Handles virtual capital management, positions, and trade execution
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
from datetime import datetime

from database.connection import get_db
from database.models import User, PaperTradingAccount
from services.auth_service import get_current_user
from services.paper_trading_account import paper_trading_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/paper-trading", tags=["Paper Trading"])


@router.post("/account/create")
async def create_paper_account(
    initial_capital: Optional[float] = 500000,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new paper trading account"""
    try:
        # Check if account already exists
        existing_account = await paper_trading_service.get_account(current_user.id)
        if existing_account:
            return {
                "message": "Paper trading account already exists",
                "account": existing_account,
            }

        # Create new account
        account = await paper_trading_service.create_paper_account(
            current_user.id, initial_capital
        )

        # Also create database record
        db_account = PaperTradingAccount(
            user_id=current_user.id,
            initial_capital=initial_capital,
            current_balance=initial_capital,
            available_margin=initial_capital,
        )
        db.add(db_account)
        db.commit()

        logger.info(f"✅ Paper account created for user {current_user.id}")
        return {"message": "Paper account created successfully", "account": account}

    except Exception as e:
        logger.error(f"❌ Error creating paper account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/account")
async def get_paper_account(current_user: User = Depends(get_current_user)):
    """Get current paper trading account details"""
    try:
        account = await paper_trading_service.get_account(current_user.id)
        if not account:
            raise HTTPException(
                status_code=404, detail="Paper trading account not found"
            )

        return {"account": account}

    except Exception as e:
        logger.error(f"❌ Error getting paper account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/account/summary")
async def get_account_summary(current_user: User = Depends(get_current_user)):
    """Get complete account summary with performance metrics"""
    try:
        summary = await paper_trading_service.get_account_summary(current_user.id)
        if "error" in summary:
            raise HTTPException(status_code=404, detail=summary["error"])

        return summary

    except Exception as e:
        logger.error(f"❌ Error getting account summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/account/settings")
async def update_account_settings(
    settings: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update account settings

    Allowed settings:
    - initial_capital: Starting capital amount
    - max_positions: Maximum number of concurrent positions
    - max_risk_per_trade: Maximum risk percentage per trade (0.01 = 1%)
    - max_daily_loss: Maximum daily loss percentage (0.05 = 5%)
    """
    try:
        success = await paper_trading_service.update_account_settings(
            current_user.id, settings
        )
        if not success:
            raise HTTPException(status_code=404, detail="Account not found")

        # Also update database
        db_account = (
            db.query(PaperTradingAccount)
            .filter(PaperTradingAccount.user_id == current_user.id)
            .first()
        )

        if db_account:
            if "initial_capital" in settings:
                db_account.initial_capital = float(settings["initial_capital"])
            if "max_positions" in settings:
                db_account.max_positions = int(settings["max_positions"])
            if "max_risk_per_trade" in settings:
                db_account.max_risk_per_trade = float(settings["max_risk_per_trade"])
            if "max_daily_loss" in settings:
                db_account.max_daily_loss = float(settings["max_daily_loss"])

            db.commit()

        logger.info(f"✅ Account settings updated for user {current_user.id}")
        return {"message": "Settings updated successfully"}

    except Exception as e:
        logger.error(f"❌ Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-trade")
async def validate_trade(
    trade_data: Dict[str, Any], current_user: User = Depends(get_current_user)
):
    """
    Validate if a trade can be executed

    Required fields:
    - invested_amount: Amount to invest
    """
    try:
        if "invested_amount" not in trade_data:
            raise HTTPException(status_code=400, detail="invested_amount is required")

        validation = await paper_trading_service.validate_trade(
            current_user.id, float(trade_data["invested_amount"])
        )

        return validation

    except Exception as e:
        logger.error(f"❌ Error validating trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute-trade")
async def execute_paper_trade(
    trade_data: Dict[str, Any], current_user: User = Depends(get_current_user)
):
    """
    Execute paper trade

    Required fields:
    - symbol: Stock symbol
    - instrument_key: Option instrument key
    - option_type: CE or PE
    - strike_price: Strike price
    - entry_price: Entry price
    - quantity: Number of lots
    - lot_size: Lot size
    - invested_amount: Total investment
    - stop_loss: Stop loss price (optional)
    - target: Target price (optional)
    """
    try:
        required_fields = [
            "symbol",
            "instrument_key",
            "option_type",
            "strike_price",
            "entry_price",
            "quantity",
            "lot_size",
            "invested_amount",
        ]

        for field in required_fields:
            if field not in trade_data:
                raise HTTPException(status_code=400, detail=f"{field} is required")

        result = await paper_trading_service.execute_paper_trade(
            current_user.id, trade_data
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except Exception as e:
        logger.error(f"❌ Error executing trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/close-position/{position_id}")
async def close_position(
    position_id: str, exit_price: float, current_user: User = Depends(get_current_user)
):
    """Close a paper trading position"""
    try:
        result = await paper_trading_service.close_position(
            current_user.id, position_id, exit_price
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except Exception as e:
        logger.error(f"❌ Error closing position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions")
async def get_positions(current_user: User = Depends(get_current_user)):
    """Get all positions (active and closed)"""
    try:
        summary = await paper_trading_service.get_account_summary(current_user.id)
        if "error" in summary:
            raise HTTPException(status_code=404, detail=summary["error"])

        return {
            "active_positions": summary.get("active_positions", []),
            "closed_positions_count": summary.get("closed_positions_count", 0),
        }

    except Exception as e:
        logger.error(f"❌ Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_performance_metrics(current_user: User = Depends(get_current_user)):
    """Get detailed performance metrics"""
    try:
        summary = await paper_trading_service.get_account_summary(current_user.id)
        if "error" in summary:
            raise HTTPException(status_code=404, detail=summary["error"])

        return summary.get("performance", {})

    except Exception as e:
        logger.error(f"❌ Error getting performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-account")
async def reset_account(
    new_capital: Optional[float] = 500000,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reset paper trading account to initial state"""
    try:
        # Reset in-memory service
        account = await paper_trading_service.create_paper_account(
            current_user.id, new_capital
        )

        # Update database
        db_account = (
            db.query(PaperTradingAccount)
            .filter(PaperTradingAccount.user_id == current_user.id)
            .first()
        )

        if db_account:
            db_account.initial_capital = new_capital
            db_account.current_balance = new_capital
            db_account.used_margin = 0.0
            db_account.available_margin = new_capital
            db_account.total_pnl = 0.0
            db_account.daily_pnl = 0.0
            db_account.positions_count = 0
            db.commit()

        logger.info(f"✅ Paper account reset for user {current_user.id}")
        return {"message": "Account reset successfully", "account": account}

    except Exception as e:
        logger.error(f"❌ Error resetting account: {e}")
        raise HTTPException(status_code=500, detail=str(e))
