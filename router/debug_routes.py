from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/debug", tags=["Debug"])


@router.get("/registry")
async def debug_registry():
    """Debug endpoint for instrument registry"""
    try:
        from services.instrument_registry import instrument_registry

        # Get registry stats
        stats = instrument_registry.get_stats()

        # Get sample live prices
        live_prices_sample = {}
        count = 0

        if hasattr(instrument_registry, "_live_prices"):
            for key, data in instrument_registry._live_prices.items():
                if count < 10:  # Limit to 10 samples
                    live_prices_sample[key] = data
                    count += 1

        # Check if registry is initialized
        initialized = (
            hasattr(instrument_registry, "_initialized")
            and instrument_registry._initialized
        )

        return {
            "success": True,
            "initialized": initialized,
            "stats": stats,
            "live_prices_sample": live_prices_sample,
            "live_prices_count": len(getattr(instrument_registry, "_live_prices", {})),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error debugging registry: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/centralized-ws")
async def debug_centralized_ws():
    """Debug endpoint for centralized WebSocket manager"""
    try:
        from services.centralized_ws_manager import centralized_manager

        # Get manager status
        status = centralized_manager.get_status()

        # Get health check
        health = await centralized_manager.health_check()

        # Get client info
        client_info = {
            "dashboard_clients": len(centralized_manager.dashboard_clients),
            "trading_clients": len(centralized_manager.trading_clients),
            "client_subscriptions": len(centralized_manager.client_subscriptions),
        }

        # Get data stats
        data_stats = {
            "data_count": centralized_manager.data_count,
            "update_count": centralized_manager.update_count,
            "cache_size": len(centralized_manager.market_data_cache),
            "last_data_received": (
                centralized_manager.last_data_received.isoformat()
                if centralized_manager.last_data_received
                else None
            ),
        }

        return {
            "success": True,
            "is_running": centralized_manager.is_running,
            "is_connected": centralized_manager.connection_ready.is_set(),
            "market_status": centralized_manager.market_status,
            "status": status,
            "health": health,
            "client_info": client_info,
            "data_stats": data_stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error debugging centralized WebSocket: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/websocket-clients")
async def debug_websocket_clients():
    """Debug endpoint for WebSocket clients"""
    try:
        from router.websocket_routes import active_connections, client_subscriptions

        # Get client info
        clients = []
        for client_id, ws in active_connections.items():
            subscriptions = list(client_subscriptions.get(client_id, set()))
            clients.append(
                {
                    "client_id": client_id,
                    "subscriptions_count": len(subscriptions),
                    "subscriptions_sample": subscriptions[:5] if subscriptions else [],
                }
            )

        return {
            "success": True,
            "total_clients": len(active_connections),
            "clients": clients,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error debugging WebSocket clients: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.post("/test-broadcast")
async def test_broadcast(message: str = "Test broadcast"):
    """Test the WebSocket broadcast mechanism"""
    try:
        from router.websocket_routes import broadcast_market_data
        from services.instrument_registry import instrument_registry

        # Get sample data from registry
        sample_data = {}
        sample_count = 0

        # Try to get actual data from registry
        if (
            hasattr(instrument_registry, "_live_prices")
            and instrument_registry._live_prices
        ):
            for key, data in instrument_registry._live_prices.items():
                if sample_count < 5:  # Limit to 5 instruments
                    sample_data[key] = data
                    sample_count += 1

        # If no data found, create dummy data
        if not sample_data:
            sample_data = {
                "NSE_INDEX|Nifty 50": {
                    "ltp": 25000.0,
                    "ltq": 0,
                    "cp": 24800.0,
                    "change": 200.0,
                    "change_percent": 0.81,
                    "timestamp": datetime.now().isoformat(),
                },
                "NSE_EQ|INE002A01018": {  # RELIANCE
                    "ltp": 2500.0,
                    "ltq": 100,
                    "cp": 2475.0,
                    "change": 25.0,
                    "change_percent": 1.01,
                    "timestamp": datetime.now().isoformat(),
                },
            }

        # Add test message
        for key in sample_data:
            sample_data[key]["test_message"] = message
            sample_data[key]["timestamp"] = datetime.now().isoformat()

        # Create task to broadcast data
        import asyncio

        asyncio.create_task(broadcast_market_data(sample_data))

        return {
            "success": True,
            "message": f"Test broadcast initiated with {len(sample_data)} instruments",
            "data_sample": sample_data,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error testing broadcast: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/instrument/{symbol}")
async def debug_instrument(symbol: str):
    """Debug endpoint for a specific instrument"""
    try:
        from services.instrument_registry import instrument_registry

        # Get instrument data
        spot_data = instrument_registry.get_spot_price(symbol.upper())

        # Get all keys associated with this symbol
        keys = instrument_registry.get_instrument_keys_for_trading(symbol.upper())

        # Get live prices for these keys
        live_prices = {}
        if hasattr(instrument_registry, "_live_prices"):
            for key in keys:
                if key in instrument_registry._live_prices:
                    live_prices[key] = instrument_registry._live_prices[key]

        return {
            "success": True,
            "symbol": symbol.upper(),
            "spot_data": spot_data,
            "instrument_keys": keys,
            "live_prices": live_prices,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error debugging instrument {symbol}: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/index-data")
async def debug_index_data():
    """Debug endpoint to inspect all index data"""
    try:
        from services.instrument_registry import instrument_registry

        debug_data = instrument_registry.debug_index_data()

        return {
            "success": True,
            "data": debug_data,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Error debugging index data: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/mcx-data")
async def debug_mcx_data():
    """Debug endpoint to inspect MCX data"""
    try:
        from services.instrument_registry import instrument_registry

        debug_data = instrument_registry.debug_mcx_data()

        return {
            "success": True,
            "data": debug_data,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Error debugging MCX data: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
