from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import json
from pathlib import Path

# Import the instrument registry
try:
    from services.trading_execution.shared_instrument_registry import shared_registry as instrument_registry
except ImportError:
    instrument_registry = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/instruments", tags=["instruments"])


@router.get("/dashboard")
async def get_dashboard_data():
    """Get dashboard data with live prices"""
    try:
        if not instrument_registry:
             raise HTTPException(status_code=503, detail="Instrument registry not available")
             
        dashboard_data = {}
        if hasattr(instrument_registry, 'get_dashboard_data'):
            dashboard_data = instrument_registry.get_dashboard_data()
        else:
            dashboard_data = {"indices": [], "top_stocks": []}

        return {
            "success": True,
            "data": dashboard_data,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_instruments(query: Optional[str] = None, q: Optional[str] = None, limit: int = 20):
    """Search for instruments by symbol or name"""
    try:
        search_query = query or q
        if not search_query:
            raise HTTPException(status_code=400, detail="Query parameter required (use 'query' or 'q')")

        from services.instrument_refresh_service import get_trading_service
        service = get_trading_service()
        
        results = []
        if hasattr(service, 'search_instruments'):
            results = service.search_instruments(search_query)

        limited_results = results[:limit]

        return {
            "success": True,
            "query": search_query,
            "results": limited_results,
            "count": len(limited_results),
        }
    except Exception as e:
        logger.error(f"Error searching instruments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fno-stocks")
async def get_fno_stocks(categorized: bool = False):
    """Get complete list of F&O stocks with consistent data structure"""
    try:
        logger.info(f"FNO stocks request - categorized: {categorized}")
        
        if categorized:
            # Try to get categorized data
            try:
                from services.fno_stock_service import get_categorized_fno_data
                categorized_data = get_categorized_fno_data()
                return {
                    "success": True,
                    "data": categorized_data,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                logger.warning(f"Categorized data fetch failed, falling back: {e}")

        # Fallback to standard list
        from services.fno_stock_service import get_fno_stocks_from_file
        fno_stocks = get_fno_stocks_from_file()
        
        return {
            "success": True,
            "stocks": fno_stocks,
            "count": len(fno_stocks),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting F&O stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fno-stocks/refresh")
async def refresh_fno_stocks():
    """Refresh F&O stocks list"""
    try:
        from services.fno_stock_service import update_fno_stock_list
        # Check if it's async or sync
        import inspect
        if inspect.iscoroutinefunction(update_fno_stock_list):
            result = await update_fno_stock_list()
        else:
            result = update_fno_stock_list()
            
        return {
            "success": True,
            "message": "F&O stocks list refreshed",
            "result": result
        }
    except Exception as e:
        logger.error(f"Error refreshing F&O stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fno-stocks/stats")
async def get_fno_stocks_stats():
    """Get stats about F&O stocks data"""
    try:
        json_file_path = Path("data/fno_stock_list.json")
        if not json_file_path.exists():
            return {"success": False, "message": "File not found"}

        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return {
            "success": True,
            "stats": {
                "total_securities": len(data.get("securities", [])),
                "last_updated": data.get("last_updated")
            }
        }
    except Exception as e:
        logger.error(f"Error getting F&O stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
