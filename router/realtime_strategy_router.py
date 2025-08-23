"""
Real-Time Strategy API Router

This router provides API endpoints for managing and monitoring the real-time
trading strategy system.

Endpoints:
- GET /api/v1/strategies/status - Get system status
- POST /api/v1/strategies/create-momentum - Create momentum strategy  
- POST /api/v1/strategies/create-mean-reversion - Create mean reversion strategy
- GET /api/v1/strategies/performance - Get performance summary
- GET /api/v1/strategies/positions - Get all positions
- POST /api/v1/strategies/engine/start - Start strategy engine
- POST /api/v1/strategies/engine/stop - Stop strategy engine
- DELETE /api/v1/strategies/{strategy_name} - Remove strategy
- POST /api/v1/strategies/emergency-stop - Emergency stop all positions
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/strategies", tags=["Real-Time Strategies"])

# Pydantic models for API requests
class CreateMomentumStrategyRequest(BaseModel):
    strategy_name: str = Field(..., description="Unique name for the strategy")
    instruments: List[str] = Field(..., description="List of instrument keys")
    momentum_threshold: float = Field(0.02, description="Momentum threshold (default 2%)")
    auto_start: bool = Field(True, description="Auto-start the strategy")

class CreateMeanReversionStrategyRequest(BaseModel):
    strategy_name: str = Field(..., description="Unique name for the strategy") 
    instruments: List[str] = Field(..., description="List of instrument keys")
    sma_period: int = Field(20, description="SMA period for mean calculation")
    deviation_threshold: float = Field(2.0, description="Standard deviation threshold")
    auto_start: bool = Field(True, description="Auto-start the strategy")

class StrategyResponse(BaseModel):
    success: bool
    message: str
    strategy_name: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# Dependency to check if real-time system is available
async def check_realtime_system():
    """Dependency to verify real-time trading system is available"""
    try:
        from services.startup_integration import get_system_status
        
        status = get_system_status()
        
        # Check if core components are available
        registry_available = status['components'].get('instrument_registry', {}).get('available', False)
        engine_available = status['components'].get('strategy_engine', {}).get('available', False)
        
        if not (registry_available and engine_available):
            raise HTTPException(
                status_code=503,
                detail="Real-time trading system not fully available. Please check system status."
            )
        
        return status
        
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Real-time trading system not installed: {e}"
        )

@router.get("/status", response_model=Dict[str, Any])
async def get_system_status():
    """Get comprehensive system status"""
    try:
        from services.startup_integration import get_system_status
        
        status = get_system_status()
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "system_status": status,
            "message": "System status retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting system status: {e}")

@router.get("/performance", response_model=Dict[str, Any])
async def get_performance_summary():
    """Get performance summary for all strategies"""
    try:
        from services.startup_integration import get_all_strategy_performance
        
        performance = get_all_strategy_performance()
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "performance": performance,
            "message": "Performance summary retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting performance summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting performance: {e}")

@router.get("/positions", response_model=Dict[str, Any])
async def get_all_positions(status: Dict = Depends(check_realtime_system)):
    """Get all positions across all strategies"""
    try:
        from services.enhanced_strategy_engine import get_strategy_engine
        
        engine = get_strategy_engine()
        positions = engine.get_all_positions()
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "positions": positions,
            "total_positions": len(positions),
            "message": "Positions retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting positions: {e}")

@router.post("/create-momentum", response_model=StrategyResponse)
async def create_momentum_strategy(
    request: CreateMomentumStrategyRequest,
    background_tasks: BackgroundTasks,
    status: Dict = Depends(check_realtime_system)
):
    """Create a new momentum strategy"""
    try:
        from services.startup_integration import create_custom_momentum_strategy
        
        # Validate strategy name is unique
        from services.enhanced_strategy_engine import get_strategy_engine
        engine = get_strategy_engine()
        
        if engine.get_strategy(request.strategy_name):
            raise HTTPException(
                status_code=400,
                detail=f"Strategy '{request.strategy_name}' already exists"
            )
        
        # Create strategy in background
        async def create_strategy():
            success = await create_custom_momentum_strategy(
                request.strategy_name,
                request.instruments,
                request.momentum_threshold,
                request.auto_start
            )
            
            if success:
                logger.info(f"✅ Created momentum strategy: {request.strategy_name}")
            else:
                logger.error(f"❌ Failed to create momentum strategy: {request.strategy_name}")
        
        background_tasks.add_task(create_strategy)
        
        return StrategyResponse(
            success=True,
            message=f"Momentum strategy '{request.strategy_name}' creation initiated",
            strategy_name=request.strategy_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating momentum strategy: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating strategy: {e}")

@router.post("/create-mean-reversion", response_model=StrategyResponse)
async def create_mean_reversion_strategy(
    request: CreateMeanReversionStrategyRequest,
    background_tasks: BackgroundTasks,
    status: Dict = Depends(check_realtime_system)
):
    """Create a new mean reversion strategy"""
    try:
        from services.startup_integration import create_custom_mean_reversion_strategy
        
        # Validate strategy name is unique
        from services.enhanced_strategy_engine import get_strategy_engine
        engine = get_strategy_engine()
        
        if engine.get_strategy(request.strategy_name):
            raise HTTPException(
                status_code=400,
                detail=f"Strategy '{request.strategy_name}' already exists"
            )
        
        # Create strategy in background
        async def create_strategy():
            success = await create_custom_mean_reversion_strategy(
                request.strategy_name,
                request.instruments,
                request.sma_period,
                request.deviation_threshold,
                request.auto_start
            )
            
            if success:
                logger.info(f"✅ Created mean reversion strategy: {request.strategy_name}")
            else:
                logger.error(f"❌ Failed to create mean reversion strategy: {request.strategy_name}")
        
        background_tasks.add_task(create_strategy)
        
        return StrategyResponse(
            success=True,
            message=f"Mean reversion strategy '{request.strategy_name}' creation initiated",
            strategy_name=request.strategy_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating mean reversion strategy: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating strategy: {e}")

@router.delete("/{strategy_name}", response_model=StrategyResponse)
async def remove_strategy(
    strategy_name: str,
    status: Dict = Depends(check_realtime_system)
):
    """Remove a strategy"""
    try:
        from services.enhanced_strategy_engine import get_strategy_engine
        from services.strategy_data_service import stop_strategy_service
        
        engine = get_strategy_engine()
        
        # Check if strategy exists
        if not engine.get_strategy(strategy_name):
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_name}' not found"
            )
        
        # Remove from engine
        engine_success = engine.remove_strategy(strategy_name)
        
        # Remove from data service
        service_success = stop_strategy_service(strategy_name)
        
        if engine_success or service_success:
            return StrategyResponse(
                success=True,
                message=f"Strategy '{strategy_name}' removed successfully",
                strategy_name=strategy_name
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to remove strategy '{strategy_name}'"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error removing strategy {strategy_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error removing strategy: {e}")

@router.post("/engine/start", response_model=StrategyResponse)
async def start_strategy_engine(
    background_tasks: BackgroundTasks,
    status: Dict = Depends(check_realtime_system)
):
    """Start the strategy engine"""
    try:
        from services.enhanced_strategy_engine import get_strategy_engine
        
        engine = get_strategy_engine()
        
        if engine.is_running:
            return StrategyResponse(
                success=True,
                message="Strategy engine is already running"
            )
        
        # Start engine in background
        async def start_engine():
            success = await engine.start()
            if success:
                logger.info("✅ Strategy engine started via API")
            else:
                logger.error("❌ Failed to start strategy engine via API")
        
        background_tasks.add_task(start_engine)
        
        return StrategyResponse(
            success=True,
            message="Strategy engine start initiated"
        )
        
    except Exception as e:
        logger.error(f"❌ Error starting strategy engine: {e}")
        raise HTTPException(status_code=500, detail=f"Error starting engine: {e}")

@router.post("/engine/stop", response_model=StrategyResponse)
async def stop_strategy_engine(
    background_tasks: BackgroundTasks,
    status: Dict = Depends(check_realtime_system)
):
    """Stop the strategy engine"""
    try:
        from services.enhanced_strategy_engine import get_strategy_engine
        
        engine = get_strategy_engine()
        
        if not engine.is_running:
            return StrategyResponse(
                success=True,
                message="Strategy engine is already stopped"
            )
        
        # Stop engine in background
        async def stop_engine():
            success = await engine.stop()
            if success:
                logger.info("✅ Strategy engine stopped via API")
            else:
                logger.error("❌ Failed to stop strategy engine via API")
        
        background_tasks.add_task(stop_engine)
        
        return StrategyResponse(
            success=True,
            message="Strategy engine stop initiated"
        )
        
    except Exception as e:
        logger.error(f"❌ Error stopping strategy engine: {e}")
        raise HTTPException(status_code=500, detail=f"Error stopping engine: {e}")

@router.post("/emergency-stop", response_model=Dict[str, Any])
async def emergency_stop_all_positions(
    status: Dict = Depends(check_realtime_system)
):
    """Emergency stop - close all positions immediately"""
    try:
        from services.enhanced_strategy_engine import get_strategy_engine
        
        engine = get_strategy_engine()
        positions_closed = engine.force_exit_all_positions()
        
        logger.warning(f"🚨 Emergency stop executed: {positions_closed} positions closed")
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "positions_closed": positions_closed,
            "message": f"Emergency stop completed - {positions_closed} positions closed"
        }
        
    except Exception as e:
        logger.error(f"❌ Error in emergency stop: {e}")
        raise HTTPException(status_code=500, detail=f"Error in emergency stop: {e}")

@router.get("/strategies", response_model=Dict[str, Any])
async def list_all_strategies(status: Dict = Depends(check_realtime_system)):
    """List all registered strategies with details"""
    try:
        from services.enhanced_strategy_engine import get_strategy_engine
        
        engine = get_strategy_engine()
        engine_status = engine.get_engine_status()
        
        strategies_list = []
        for strategy_name, strategy_status in engine_status.get('strategies', {}).items():
            strategies_list.append({
                'name': strategy_name,
                'is_active': strategy_status.get('is_active', False),
                'total_instruments': strategy_status.get('data_service_status', {}).get('total_instruments', 0),
                'total_positions': strategy_status.get('total_positions', 0),
                'total_pnl': strategy_status.get('total_pnl', 0.0),
                'signals_generated': strategy_status.get('signals_generated', 0),
                'trades_executed': strategy_status.get('trades_executed', 0)
            })
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "strategies": strategies_list,
            "total_strategies": len(strategies_list),
            "engine_running": engine_status.get('is_running', False),
            "message": "Strategies listed successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing strategies: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing strategies: {e}")

@router.get("/strategy/{strategy_name}", response_model=Dict[str, Any])
async def get_strategy_details(
    strategy_name: str,
    status: Dict = Depends(check_realtime_system)
):
    """Get detailed information about a specific strategy"""
    try:
        from services.enhanced_strategy_engine import get_strategy_engine
        
        engine = get_strategy_engine()
        strategy = engine.get_strategy(strategy_name)
        
        if not strategy:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_name}' not found"
            )
        
        strategy_status = strategy.get_portfolio_status()
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "strategy": strategy_status,
            "message": f"Strategy '{strategy_name}' details retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting strategy details: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting strategy details: {e}")

# Health check endpoint
@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health check endpoint for the real-time strategy system"""
    try:
        from services.startup_integration import get_system_status
        
        status = get_system_status()
        
        # Determine overall health
        components = status.get('components', {})
        healthy_components = sum(1 for comp in components.values() if comp.get('available', False))
        total_components = len(components)
        
        health_percentage = (healthy_components / max(total_components, 1)) * 100
        
        overall_status = "healthy" if health_percentage >= 80 else "degraded" if health_percentage >= 50 else "unhealthy"
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "health_percentage": round(health_percentage, 1),
            "healthy_components": healthy_components,
            "total_components": total_components,
            "components": components,
            "message": f"System is {overall_status}"
        }
        
    except Exception as e:
        logger.error(f"❌ Error in health check: {e}")
        return {
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "overall_status": "error",
            "error": str(e),
            "message": "Health check failed"
        }

# Include router in main app
def get_realtime_strategy_router():
    """Get the real-time strategy router for inclusion in main app"""
    return router