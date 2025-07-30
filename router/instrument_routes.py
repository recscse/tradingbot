from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from services.instrument_registry import instrument_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/instruments", tags=["instruments"])


@router.get("/dashboard")
async def get_dashboard_data():
    """Get dashboard data with live prices"""
    try:
        dashboard_data = instrument_registry.get_dashboard_data()

        # Log data details for debugging
        logger.info(
            f"Dashboard data: {len(dashboard_data.get('indices', []))} indices, {len(dashboard_data.get('top_stocks', []))} top stocks"
        )

        return {
            "success": True,
            "data": dashboard_data,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_instruments(query: str, limit: int = 20):
    """Search for instruments by symbol or name"""
    try:
        # Use the instrument registry to search
        from services.instrument_refresh_service import get_trading_service

        service = get_trading_service()
        results = service.search_instruments(query)

        # Limit the results
        limited_results = results[:limit]

        return {
            "success": True,
            "query": query,
            "results": limited_results,
            "count": len(limited_results),
        }
    except Exception as e:
        logger.error(f"Error searching instruments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fno-stocks")
async def get_fno_stocks():
    """Get list of available F&O stocks"""
    try:
        from services.instrument_refresh_service import get_available_fno_stocks

        fno_stocks = await get_available_fno_stocks()

        return {"success": True, "stocks": fno_stocks, "count": len(fno_stocks)}
    except Exception as e:
        logger.error(f"Error getting F&O stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options-chain/{symbol}")
async def get_options_chain(
    symbol: str,
    expiry: Optional[str] = None,
    with_greeks: bool = False,
    with_analytics: bool = True,
):
    """Get enhanced options chain for a symbol with live prices"""
    try:
        # Add expiry parameter to get_options_chain
        options_chain = instrument_registry.get_options_chain(symbol.upper(), expiry)

        if "error" in options_chain:
            raise HTTPException(status_code=404, detail=options_chain["error"])

        # Get spot price for ATM identification
        spot_data = instrument_registry.get_spot_price(symbol.upper())
        spot_price = spot_data.get("last_price") if spot_data else None

        # Add ATM strike identification
        if spot_price and "strikes" in options_chain:
            options_chain["atm_strike"] = min(
                options_chain["strikes"], key=lambda x: abs(x - spot_price)
            )

        # Add analytics if requested
        if with_analytics:
            analytics = {}

            # Calculate Put-Call Ratio
            call_volume = sum(
                call.get("volume", 0) or 0
                for call in options_chain.get("call_data", [])
            )
            put_volume = sum(
                put.get("volume", 0) or 0 for put in options_chain.get("put_data", [])
            )

            if call_volume > 0:
                analytics["pcr_volume"] = round(put_volume / call_volume, 2)

            call_oi = sum(
                call.get("oi", 0) or 0 for call in options_chain.get("call_data", [])
            )
            put_oi = sum(
                put.get("oi", 0) or 0 for put in options_chain.get("put_data", [])
            )

            if call_oi > 0:
                analytics["pcr_oi"] = round(put_oi / call_oi, 2)

            # Add analytics to response
            options_chain["analytics"] = analytics

        return {
            "success": True,
            "symbol": symbol.upper(),
            "spot_price": spot_price,
            "data": options_chain,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting options chain for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trading-data/{symbol}")
async def get_trading_data(symbol: str):
    """Get comprehensive trading data for a symbol"""
    try:
        # Get spot price
        spot_data = instrument_registry.get_spot_price(symbol.upper())
        if not spot_data:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

        # Get options chain
        options_chain = instrument_registry.get_options_chain(symbol.upper())

        # Return combined data
        return {
            "success": True,
            "symbol": symbol.upper(),
            "spot": spot_data,
            "options_chain": options_chain,
            "updated_at": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trading data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/websocket-keys/dashboard")
async def get_dashboard_websocket_keys():
    """Get instrument keys for dashboard WebSocket subscription"""
    try:
        keys = instrument_registry.get_instrument_keys_for_dashboard()

        return {
            "success": True,
            "keys": keys,
            "count": len(keys),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting dashboard WebSocket keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/websocket-keys/trading/{symbol}")
async def get_trading_websocket_keys(symbol: str):
    """Get instrument keys for trading a specific symbol"""
    try:
        keys = instrument_registry.get_instrument_keys_for_trading(symbol.upper())

        return {
            "success": True,
            "symbol": symbol.upper(),
            "keys": keys,
            "count": len(keys),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting trading WebSocket keys for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live-prices/{symbol}")
async def get_live_price(symbol: str):
    """Get live price for a specific symbol"""
    try:
        price_data = instrument_registry.get_spot_price(symbol.upper())
        if not price_data:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

        return {
            "success": True,
            "symbol": symbol.upper(),
            "data": price_data,
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting live price for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_registry_stats():
    """Get registry statistics"""
    try:
        stats = instrument_registry.get_stats()

        # Add last update time in a more readable format
        if "last_update" in stats and stats["last_update"]:
            try:
                last_update = datetime.fromisoformat(stats["last_update"])
                stats["last_update_ago"] = (
                    f"{(datetime.now() - last_update).total_seconds():.0f} seconds ago"
                )
            except:
                pass

        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting registry stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def refresh_registry():
    """Manually refresh the instrument registry"""
    try:
        # Re-initialize the registry
        result = await instrument_registry.initialize_registry()

        return {
            "success": result,
            "message": (
                "Registry refresh completed" if result else "Registry refresh failed"
            ),
            "stats": instrument_registry.get_stats(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error refreshing registry: {e}")
        raise HTTPException(status_code=500, detail=str(e))
