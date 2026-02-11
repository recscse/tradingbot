from fastapi import APIRouter, HTTPException
from services.strategies_registry.registry import strategy_registry
from typing import Dict, Any

router = APIRouter(prefix="/api/v2/strategies", tags=["Strategies V2"])

@router.get("/")
def list_strategies():
    """List all available hot-swappable strategies"""
    return {"strategies": strategy_registry.list_strategies()}

@router.post("/execute/{strategy_name}")
def execute_strategy(strategy_name: str, market_data: Dict[str, Any]):
    """
    Execute a specific strategy on-demand.
    Payload: {"ltp": 100, "ohlc": {...}}
    """
    result = strategy_registry.execute_strategy(strategy_name, market_data)
    if "error" in result:
        if "not found" in result["error"]:
            raise HTTPException(status_code=404, detail=result["error"])
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result
