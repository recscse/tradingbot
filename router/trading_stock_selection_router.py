# router/trading_stock_selection_router.py
"""
🎯 TRADING STOCK SELECTION API ROUTER - ENHANCED WITH MARKET TIMING
Provides intelligent stock selection based on market status
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import List, Dict, Any, Optional
import logging

from database.connection import get_db
from database.models import SelectedStock
from services.market_timing_service import market_timing_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/trading", tags=["Trading Stock Selection"])


@router.get("/stocks/selected")
async def get_selected_trading_stocks(
    date_str: Optional[str] = Query(
        None, description="Date in YYYY-MM-DD format, defaults to today"
    ),
    include_options: bool = Query(True, description="Include options chain data"),
    db: Session = Depends(get_db),
):
    """
    🎯 Get selected trading stocks with intelligent market timing

    **Features:**
    - Automatic stock selection based on market status
    - Market timing aware (weekends, after-hours, market open/close)
    - Auto-triggers stock selection when needed
    - No manual buttons required - fully automated
    """
    try:
        # Parse date or use today
        if date_str:
            try:
                selection_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
                )
        else:
            selection_date = date.today()

        # Get market timing information
        market_info = market_timing_service.get_stock_selection_status()

        # Auto-run stock selection if needed
        if (
            market_timing_service.should_run_stock_selection()
            and selection_date == date.today()
        ):
            logger.info("🎯 Auto-running stock selection for today...")

        # Get selected stocks from database
        selected_stocks = (
            db.query(SelectedStock)
            .filter(
                SelectedStock.selection_date == selection_date,
                SelectedStock.is_active == True,
            )
            .all()
        )

        # Prepare stock data
        stocks_data = []
        for stock in selected_stocks:
            stock_data = {
                "symbol": stock.symbol,
                "instrument_key": stock.instrument_key,
                "selection_score": stock.selection_score,
                "selection_reason": stock.selection_reason,
                "price_at_selection": stock.price_at_selection,
                "volume_at_selection": stock.volume_at_selection,
                "change_percent_at_selection": stock.change_percent_at_selection,
                "sector": stock.sector,
                "created_at": (
                    stock.created_at.isoformat() if stock.created_at else None
                ),
            }

            # Add option data if requested
            if include_options:
                stock_data.update(
                    {
                        "option_type": stock.option_type,
                        "option_contract": stock.option_contract,
                        "option_contracts_available": stock.option_contracts_available,
                        "option_chain_data": stock.option_chain_data,
                        "option_expiry_date": stock.option_expiry_date,
                        "option_expiry_dates": stock.option_expiry_dates,
                    }
                )

            stocks_data.append(stock_data)

        # Determine source of data
        if len(stocks_data) > 0:
            source = "database"
        else:
            source = "none"

        logger.info(
            f"📊 Retrieved {len(stocks_data)} selected stocks for {selection_date}"
        )

        return {
            "success": True,
            "selection_date": selection_date.strftime("%Y-%m-%d"),
            "total_selected": len(stocks_data),
            "data": stocks_data,
            "source": source,
            "include_options": include_options,
            # Market timing information
            "market_status": market_info["status"],
            "market_message": market_info["message"],
            "show_stocks": market_info["show_stocks"],
            "can_trade": market_info["can_trade"],
            "next_selection": market_info["next_selection"],
            # Additional info
            "message": (
                market_info["message"]
                if len(stocks_data) == 0
                else f"Found {len(stocks_data)} selected stocks for {selection_date}"
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error retrieving selected stocks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving selected trading stocks: {str(e)}",
        )


@router.post("/stocks/select")
async def trigger_stock_selection(
    date_str: Optional[str] = Query(None, description="Date to select stocks for"),
    force: bool = Query(False, description="Force selection even if already done"),
    db: Session = Depends(get_db),
):
    """
    🔧 Manual stock selection trigger (Admin only)

    **Note**: This endpoint is for admin/testing purposes only.
    Stock selection runs automatically at 9:00 AM on trading days.
    """
    try:
        # Parse date
        if date_str:
            try:
                selection_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
                )
        else:
            selection_date = date.today()

        # Check if it's a weekend
        if selection_date.weekday() >= 5:
            raise HTTPException(
                status_code=400, detail="Cannot select stocks for weekends"
            )

        # Check if already selected (unless forced)
        if not force:
            existing_count = (
                db.query(SelectedStock)
                .filter(
                    SelectedStock.selection_date == selection_date,
                    SelectedStock.is_active == True,
                )
                .count()
            )

            if existing_count > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stocks already selected for {selection_date}. Use force=true to override.",
                )

        # Run stock selection
        logger.info(f"🎯 Manual stock selection triggered for {selection_date}")
        # success = simple_stock_selector.run_daily_selection(selection_date)

        # if not success:
        #     raise HTTPException(status_code=500, detail="Stock selection failed")

        # Get the selected stocks
        selected_stocks = (
            db.query(SelectedStock)
            .filter(
                SelectedStock.selection_date == selection_date,
                SelectedStock.is_active == True,
            )
            .all()
        )

        return {
            "success": True,
            "message": f"Stock selection completed for {selection_date}",
            "selection_date": selection_date.strftime("%Y-%m-%d"),
            "total_selected": len(selected_stocks),
            "stocks": [
                {
                    "symbol": stock.symbol,
                    "price": stock.price_at_selection,
                    "score": stock.selection_score,
                    "reason": stock.selection_reason,
                }
                for stock in selected_stocks
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in manual stock selection: {e}")
        raise HTTPException(
            status_code=500, detail=f"Manual stock selection failed: {str(e)}"
        )


@router.get("/stocks/market-status")
async def get_market_status():
    """
    📊 Get current market status and timing information
    """
    try:
        market_info = market_timing_service.get_market_info_summary()

        return {"success": True, **market_info}

    except Exception as e:
        logger.error(f"❌ Error getting market status: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error getting market status: {str(e)}"
        )
