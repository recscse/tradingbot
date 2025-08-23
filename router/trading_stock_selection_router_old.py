# router/trading_stock_selection_router.py
"""
🎯 TRADING STOCK SELECTION API ROUTER
Provides endpoints for stock selection with integrated options chain data
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import List, Dict, Any, Optional
import logging
from database.connection import get_db
from services.market_timing_service import market_timing_service
from services.simple_stock_selector import simple_stock_selector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/trading", tags=["Trading Stock Selection"])

@router.get("/stocks/selected")
async def get_selected_trading_stocks(
    date_str: Optional[str] = Query(None, description="Date in YYYY-MM-DD format, defaults to today"),
    include_options: bool = Query(True, description="Include options chain data"),
    db: Session = Depends(get_db)
):
    """
    🎯 Get selected trading stocks with market timing intelligence
    
    **Features:**
    - Automatic stock selection based on market timing
    - Market status aware (shows appropriate messages)
    - Handles weekends, after-hours, and market open/close
    - No manual intervention required
    """
    try:
        # Get market timing and stock selection status
        market_info = market_timing_service.get_stock_selection_status()
        
        # Parse date or use today
        if date_str:
            try:
                selection_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            selection_date = date.today()
        
        # Method 1: Try to get from market scheduler's current selection
        if selection_date == date.today() and hasattr(scheduler, 'selected_stocks') and scheduler.selected_stocks:
            logger.info(f"📊 Using current market scheduler selection for {selection_date}")
            
            stocks_data = []
            for symbol, data in scheduler.selected_stocks.items():
                stock_info = data.get('stock_data', {})
                analysis_info = data.get('analysis', {})
                
                stock_entry = {
                    "symbol": symbol,
                    "instrument_key": stock_info.get('instrument_key'),
                    "sector": stock_info.get('sector'),
                    "price_at_selection": stock_info.get('price_at_selection'),
                    "selection_score": stock_info.get('selection_score'),
                    "selection_reason": stock_info.get('selection_reason'),
                    "selected_at": stock_info.get('selected_at'),
                    
                    # Options data
                    "option_type": stock_info.get('option_type'),
                    "option_contract": stock_info.get('option_contract'),
                    "option_chain_data": stock_info.get('option_chain_data') if include_options else None,
                    "option_expiry_date": stock_info.get('option_expiry_date'),
                    "option_expiry_dates": stock_info.get('option_expiry_dates'),
                    "option_contracts_available": stock_info.get('option_contracts_available', 0),
                    
                    # Analysis
                    "strategy_score": stock_info.get('strategy_score'),
                    "has_options": data.get('options_ready', False),
                    "option_type_recommendation": analysis_info.get('option_type_recommendation'),
                    "market_sentiment_aligned": analysis_info.get('market_sentiment_aligned', False),
                }
                stocks_data.append(stock_entry)
            
            return {
                "success": True,
                "selection_date": selection_date.isoformat(),
                "total_selected": len(stocks_data),
                "data": stocks_data,
                "source": "market_scheduler_live",
                "include_options": include_options,
            }
        
        # Method 2: Try to get from Redis storage
        stored_stocks = scheduler.get_selected_stocks_from_storage(selection_date.isoformat())
        if stored_stocks:
            logger.info(f"📖 Using stored selection data for {selection_date}")
            
            # Format stored data
            stocks_data = []
            for stock in stored_stocks:
                stock_entry = {
                    "symbol": stock.get('symbol'),
                    "instrument_key": stock.get('instrument_key'),
                    "sector": stock.get('sector'),
                    "price_at_selection": stock.get('price_at_selection'),
                    "selection_score": stock.get('selection_score'),
                    "selection_reason": stock.get('selection_reason'),
                    "selected_at": stock.get('created_at'),
                    
                    # Options data
                    "option_type": stock.get('option_type'),
                    "option_contract": stock.get('option_contract'),
                    "option_chain_data": stock.get('option_chain_data') if include_options else None,
                    "option_expiry_date": stock.get('option_expiry_date'),
                    "option_expiry_dates": stock.get('option_expiry_dates'),
                    "option_contracts_available": stock.get('option_contracts_available', 0),
                    
                    # Analysis
                    "strategy_score": stock.get('strategy_score'),
                    "has_options": stock.get('option_chain_data') is not None,
                }
                stocks_data.append(stock_entry)
            
            return {
                "success": True,
                "selection_date": selection_date.isoformat(),
                "total_selected": len(stocks_data),
                "data": stocks_data,
                "source": "redis_storage",
                "include_options": include_options,
            }
        
        # Method 3: Try to get from database using TradingStockSelector
        logger.info(f"📋 Using database selection data for {selection_date}")
        
        stock_selector = TradingStockSelector(
            analytics=enhanced_analytics,
            user_id=1,  # Default admin user
        )
        
        db_stocks = stock_selector.get_selected_stocks_with_options(selection_date)
        if db_stocks:
            stocks_data = []
            for stock in db_stocks:
                stock_entry = {
                    "symbol": stock.get('symbol'),
                    "instrument_key": stock.get('instrument_key'),
                    "sector": stock.get('sector'),
                    "price_at_selection": stock.get('price_at_selection'),
                    "selection_score": stock.get('selection_score'),
                    "selection_reason": stock.get('selection_reason'),
                    "selected_at": stock.get('created_at'),
                    
                    # Options data
                    "option_type": stock.get('option_type'),
                    "option_contract": stock.get('option_contract'),
                    "option_chain_data": stock.get('option_chain_data') if include_options else None,
                    "option_expiry_date": stock.get('option_expiry_date'),
                    "option_expiry_dates": stock.get('option_expiry_dates'),
                    "option_contracts_available": stock.get('option_contracts_available', 0),
                    
                    # Analysis from score breakdown
                    "strategy_score": stock.get('score_breakdown', {}).get('strategy_score'),
                    "has_options": stock.get('option_chain_data') is not None,
                }
                stocks_data.append(stock_entry)
            
            return {
                "success": True,
                "selection_date": selection_date.isoformat(),
                "total_selected": len(stocks_data),
                "data": stocks_data,
                "source": "database",
                "include_options": include_options,
            }
        
        # No data found
        return {
            "success": True,
            "selection_date": selection_date.isoformat(),
            "total_selected": 0,
            "data": [],
            "source": "none",
            "message": f"No trading stocks selected for {selection_date}",
            "include_options": include_options,
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting selected trading stocks: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve selected stocks: {str(e)}"
        )

@router.post("/stocks/select")
async def run_stock_selection(
    user_id: Optional[int] = Query(1, description="User ID for personalized selection"),
    force_refresh: bool = Query(False, description="Force fresh selection even if today's data exists"),
    db: Session = Depends(get_db)
):
    """
    🎯 Run stock selection process with options integration
    
    **Process:**
    1. Analyze current market sentiment
    2. Select top-performing sector
    3. Choose 2 middle-performing stocks from that sector
    4. Fetch complete options chain data
    5. Identify ATM option contracts
    6. Store results for trading
    """
    try:
        today = date.today()
        
        # Check if selection already exists for today
        if not force_refresh:
            stock_selector = TradingStockSelector(user_id=user_id)
            existing_selection = stock_selector.get_selected_stocks_with_options(today)
            
            if existing_selection:
                return {
                    "success": True,
                    "message": f"Using existing selection for {today}",
                    "selection_date": today.isoformat(),
                    "total_selected": len(existing_selection),
                    "force_refresh": False,
                    "data": existing_selection[:2],  # Show first 2 for preview
                }
        
        # Run fresh selection
        logger.info(f"🔍 Running fresh stock selection for user {user_id}")
        
        stock_selector = TradingStockSelector(
            analytics=enhanced_analytics,
            user_id=user_id,
        )
        
        # Run the selection process
        selected_stocks = stock_selector.run_selection_sync()
        
        if not selected_stocks:
            return {
                "success": False,
                "message": "No stocks met selection criteria",
                "selection_date": today.isoformat(),
                "total_selected": 0,
                "data": [],
            }
        
        # Format response
        response_data = []
        for stock in selected_stocks:
            response_data.append({
                "symbol": stock.get('symbol'),
                "sector": stock.get('sector'),
                "selection_score": stock.get('selection_score'),
                "price_at_selection": stock.get('price_at_selection'),
                "option_type": stock.get('option_type'),
                "option_contracts_available": stock.get('option_contracts_available'),
                "has_option_chain": stock.get('has_option_chain', False),
                "option_expiry_date": stock.get('option_expiry_date'),
            })
        
        return {
            "success": True,
            "message": f"Successfully selected {len(selected_stocks)} stocks with options integration",
            "selection_date": today.isoformat(),
            "total_selected": len(selected_stocks),
            "force_refresh": force_refresh,
            "data": response_data,
        }
        
    except Exception as e:
        logger.error(f"❌ Error running stock selection: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Stock selection failed: {str(e)}"
        )

@router.get("/stocks/selection-status")
async def get_selection_status(
    db: Session = Depends(get_db)
):
    """
    📊 Get current stock selection status and market scheduler state
    """
    try:
        today = date.today()
        scheduler = get_market_scheduler()
        
        # Check current scheduler status
        scheduler_status = {
            "is_running": getattr(scheduler, 'is_running', False),
            "selected_stocks_count": len(getattr(scheduler, 'selected_stocks', {})),
            "current_stocks": list(getattr(scheduler, 'selected_stocks', {}).keys()),
        }
        
        # Check database for today's selection
        stock_selector = TradingStockSelector(user_id=1)
        db_selection = stock_selector.get_selected_stocks_with_options(today)
        
        # Check Redis storage
        stored_selection = scheduler.get_selected_stocks_from_storage()
        
        return {
            "success": True,
            "selection_date": today.isoformat(),
            "scheduler_status": scheduler_status,
            "database_selection": {
                "count": len(db_selection),
                "stocks": [s.get('symbol') for s in db_selection] if db_selection else [],
            },
            "redis_storage": {
                "count": len(stored_selection),
                "stocks": [s.get('symbol') for s in stored_selection] if stored_selection else [],
            },
            "recommendations": {
                "run_selection": len(db_selection) == 0,
                "start_scheduler": not scheduler_status["is_running"],
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting selection status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get selection status: {str(e)}"
        )

@router.get("/stocks/{symbol}/options")
async def get_stock_options_data(
    symbol: str,
    expiry_date: Optional[str] = Query(None, description="Specific expiry date (YYYY-MM-DD)"),
    option_type: Optional[str] = Query(None, description="Option type: CE or PE"),
    db: Session = Depends(get_db)
):
    """
    📈 Get complete options data for a specific stock symbol
    """
    try:
        from services.upstox_option_service import upstox_option_service
        
        # Try to get instrument key for the symbol
        # First check if it's in selected stocks
        scheduler = get_market_scheduler()
        instrument_key = None
        
        if hasattr(scheduler, 'selected_stocks') and symbol in scheduler.selected_stocks:
            instrument_key = scheduler.selected_stocks[symbol].get('stock_data', {}).get('instrument_key')
        
        if not instrument_key:
            # Try to get from analytics or registry
            try:
                from services.instrument_registry import instrument_registry
                instrument_key = instrument_registry.get_instrument_key_by_symbol(symbol)
            except Exception:
                pass
        
        if not instrument_key:
            raise HTTPException(
                status_code=404,
                detail=f"Instrument key not found for symbol: {symbol}"
            )
        
        # Get expiry dates
        expiry_dates = upstox_option_service.get_expiry_dates(instrument_key, db)
        
        if not expiry_dates:
            return {
                "success": False,
                "symbol": symbol,
                "message": "No expiry dates available for this stock",
                "data": None,
            }
        
        # Use specified expiry or nearest one
        target_expiry = expiry_date if expiry_date else expiry_dates[0]
        
        if expiry_date and target_expiry not in expiry_dates:
            raise HTTPException(
                status_code=400,
                detail=f"Expiry date {expiry_date} not available. Available: {expiry_dates}"
            )
        
        # Get option chain
        option_chain = upstox_option_service.get_option_chain(
            instrument_key, target_expiry, db
        )
        
        if not option_chain:
            return {
                "success": False,
                "symbol": symbol,
                "expiry_date": target_expiry,
                "message": "Option chain data not available",
                "data": None,
            }
        
        # Get option contracts
        option_contracts = upstox_option_service.get_option_contracts(
            instrument_key, db, target_expiry
        )
        
        # Filter by option type if specified
        if option_type and option_contracts:
            option_contracts = [
                contract for contract in option_contracts
                if contract.option_type == option_type.upper()
            ]
        
        # Format response
        contracts_data = []
        if option_contracts:
            for contract in option_contracts:
                contracts_data.append({
                    "instrument_key": contract.instrument_key,
                    "strike_price": contract.strike_price,
                    "option_type": contract.option_type,
                    "expiry": contract.expiry,
                    "trading_symbol": contract.trading_symbol,
                    "lot_size": contract.lot_size,
                })
        
        return {
            "success": True,
            "symbol": symbol,
            "instrument_key": instrument_key,
            "expiry_date": target_expiry,
            "available_expiry_dates": expiry_dates,
            "option_chain": {
                "underlying_symbol": option_chain.underlying_symbol,
                "spot_price": option_chain.spot_price,
                "strike_prices": option_chain.strike_prices,
                "options_count": len(option_chain.options),
                "futures_count": len(option_chain.futures),
            },
            "option_contracts": {
                "total": len(contracts_data),
                "filtered_by_type": option_type,
                "contracts": contracts_data,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting options data for {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get options data: {str(e)}"
        )