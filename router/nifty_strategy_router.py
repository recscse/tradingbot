"""
NIFTY 09:40 Strategy Router

REST API endpoints for managing the NIFTY 09:40 EMA + Candle Strength strategy.
Provides control, monitoring, and configuration capabilities.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime, time
import logging

# Optional authentication - strategy can work independently
try:
    from services.auth_service import get_current_user_optional as get_current_user
    from database.models import User
    AUTH_AVAILABLE = True
except ImportError:
    # Fallback when auth is not available
    get_current_user = None
    User = None
    AUTH_AVAILABLE = False

from services.strategies.nifty_09_40_integration import (
    get_nifty_strategy_integration,
    initialize_nifty_strategy,
    NiftyStrategyConfig
)

logger = logging.getLogger(__name__)

# Helper function for optional authentication
def get_optional_user() -> Optional[User]:
    """Get current user if authentication is available, otherwise return None"""
    return None  # For now, make strategy completely independent

# Create a dependency that can be used optionally
def optional_auth_dependency():
    """Dependency function for optional authentication"""
    if AUTH_AVAILABLE and get_current_user:
        return Depends(get_current_user)
    return None

# Create router
nifty_strategy_router = APIRouter(prefix="/api/v1/nifty-strategy", tags=["NIFTY Strategy"])

# Pydantic models for API
class NiftyStrategyConfigUpdate(BaseModel):
    """Model for updating NIFTY strategy configuration"""
    ema_period: Optional[int] = Field(None, ge=5, le=50, description="EMA period (5-50)")
    strength_threshold: Optional[float] = Field(None, ge=0.1, le=1.0, description="Candle strength threshold (0.1-1.0)")
    volume_multiplier: Optional[float] = Field(None, ge=0.5, le=5.0, description="Volume multiplier (0.5-5.0)")
    stop_loss_pct: Optional[float] = Field(None, ge=0.5, le=10.0, description="Stop loss percentage (0.5-10.0)")
    target_pct: Optional[float] = Field(None, ge=1.0, le=20.0, description="Target percentage (1.0-20.0)")
    position_size: Optional[float] = Field(None, gt=0, description="Position size in rupees")
    max_daily_trades: Optional[int] = Field(None, ge=1, le=10, description="Maximum daily trades (1-10)")
    enabled: Optional[bool] = Field(None, description="Enable/disable strategy")

class NiftyStrategyResponse(BaseModel):
    """Standard response model for NIFTY strategy operations"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class NiftySignalResponse(BaseModel):
    """Response model for NIFTY trading signals"""
    signal: str
    confidence: float
    entry_price: float
    stop_loss: float
    target: float
    reason: str
    timestamp: str
    ema_value: float
    candle_strength: float
    volume_ratio: float

@nifty_strategy_router.get("/status", response_model=NiftyStrategyResponse)
async def get_nifty_strategy_status():
    """Get current NIFTY strategy status and statistics"""
    try:
        strategy = await get_nifty_strategy_integration()
        status = await strategy.get_strategy_status()
        
        return NiftyStrategyResponse(
            success=True,
            message="NIFTY strategy status retrieved successfully",
            data=status
        )
        
    except Exception as e:
        logger.error(f"❌ Error getting NIFTY strategy status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@nifty_strategy_router.post("/start", response_model=NiftyStrategyResponse)
async def start_nifty_strategy():
    """Start the NIFTY 09:40 strategy"""
    try:
        # Import websocket manager here to avoid circular imports
        from services.websocket.auto_trading_websocket import get_websocket_manager
        
        websocket_manager = await get_websocket_manager()
        result = await initialize_nifty_strategy(websocket_manager)
        
        if result:
            return NiftyStrategyResponse(
                success=True,
                message="NIFTY 09:40 strategy started successfully",
                data={"status": "started"}
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to start NIFTY strategy")
            
    except Exception as e:
        logger.error(f"❌ Error starting NIFTY strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@nifty_strategy_router.post("/stop", response_model=NiftyStrategyResponse)
async def stop_nifty_strategy():
    """Stop the NIFTY 09:40 strategy"""
    try:
        strategy = await get_nifty_strategy_integration()
        await strategy.stop_strategy()
        
        return NiftyStrategyResponse(
            success=True,
            message="NIFTY 09:40 strategy stopped successfully",
            data={"status": "stopped"}
        )
        
    except Exception as e:
        logger.error(f"❌ Error stopping NIFTY strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@nifty_strategy_router.put("/config", response_model=NiftyStrategyResponse)
async def update_nifty_strategy_config(
    config_update: NiftyStrategyConfigUpdate
):
    """Update NIFTY strategy configuration"""
    try:
        strategy = await get_nifty_strategy_integration()
        
        # Convert Pydantic model to dict, excluding None values
        update_dict = config_update.dict(exclude_none=True)
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No configuration parameters provided")
        
        await strategy.update_config(update_dict)
        
        return NiftyStrategyResponse(
            success=True,
            message="NIFTY strategy configuration updated successfully",
            data={
                "updated_config": update_dict
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error updating NIFTY strategy config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@nifty_strategy_router.get("/config", response_model=NiftyStrategyResponse)
async def get_nifty_strategy_config():
    """Get current NIFTY strategy configuration"""
    try:
        strategy = await get_nifty_strategy_integration()
        config = strategy.config
        
        config_dict = {
            "strategy_name": config.strategy_name,
            "nifty_symbol": config.nifty_symbol,
            "timeframe": config.timeframe,
            "start_time": config.start_time.isoformat(),
            "end_time": config.end_time.isoformat(),
            "ema_period": config.ema_period,
            "strength_threshold": config.strength_threshold,
            "volume_multiplier": config.volume_multiplier,
            "stop_loss_pct": config.stop_loss_pct,
            "target_pct": config.target_pct,
            "position_size": config.position_size,
            "max_daily_trades": config.max_daily_trades,
            "enabled": config.enabled
        }
        
        return NiftyStrategyResponse(
            success=True,
            message="NIFTY strategy configuration retrieved successfully",
            data=config_dict
        )
        
    except Exception as e:
        logger.error(f"❌ Error getting NIFTY strategy config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@nifty_strategy_router.get("/performance", response_model=NiftyStrategyResponse)
async def get_nifty_strategy_performance():
    """Get NIFTY strategy performance metrics"""
    try:
        strategy = await get_nifty_strategy_integration()
        status = await strategy.get_strategy_status()
        
        performance_data = {
            "daily_stats": status.get("daily_stats", {}),
            "is_active": status.get("is_active", False),
            "daily_trades_count": status.get("daily_trades_count", 0),
            "max_daily_trades": status.get("max_daily_trades", 3),
            "buffer_size": status.get("buffer_size", 0),
            "last_signal_time": status.get("last_signal_time")
        }
        
        return NiftyStrategyResponse(
            success=True,
            message="NIFTY strategy performance retrieved successfully",
            data=performance_data
        )
        
    except Exception as e:
        logger.error(f"❌ Error getting NIFTY strategy performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@nifty_strategy_router.get("/info", response_model=NiftyStrategyResponse)
async def get_nifty_strategy_info():
    """Get NIFTY strategy information and metadata"""
    try:
        from strategies.nifty_09_40 import get_strategy_info
        
        strategy_info = get_strategy_info()
        
        return NiftyStrategyResponse(
            success=True,
            message="NIFTY strategy information retrieved successfully",
            data=strategy_info
        )
        
    except Exception as e:
        logger.error(f"❌ Error getting NIFTY strategy info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@nifty_strategy_router.post("/test-signal", response_model=NiftyStrategyResponse)
async def test_nifty_strategy_signal():
    """Test NIFTY strategy signal generation with current data"""
    try:
        strategy = await get_nifty_strategy_integration()
        
        # Generate a test signal
        signal = await strategy._generate_strategy_signal()
        
        if signal:
            return NiftyStrategyResponse(
                success=True,
                message="NIFTY strategy test signal generated successfully",
                data={
                    "signal": signal,
                    "test_mode": True,
                    "timestamp": datetime.now().isoformat()
                }
            )
        else:
            return NiftyStrategyResponse(
                success=True,
                message="No NIFTY strategy signal generated (HOLD condition)",
                data={
                    "signal": None,
                    "test_mode": True,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
    except Exception as e:
        logger.error(f"❌ Error testing NIFTY strategy signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@nifty_strategy_router.get("/live-data", response_model=NiftyStrategyResponse)
async def get_nifty_live_data():
    """Get current NIFTY live data and OHLCV buffer"""
    try:
        strategy = await get_nifty_strategy_integration()
        
        # Get OHLCV buffer data (last 10 candles)
        buffer_data = strategy.ohlcv_buffer.tail(10).to_dict('records') if not strategy.ohlcv_buffer.empty else []
        
        # Get current instrument data from registry
        from services.instrument_registry import InstrumentRegistry
        registry = InstrumentRegistry()
        
        current_price_data = registry.get_live_price(strategy.config.nifty_instrument_key)
        
        return NiftyStrategyResponse(
            success=True,
            message="NIFTY live data retrieved successfully",
            data={
                "ohlcv_buffer": buffer_data,
                "buffer_length": len(strategy.ohlcv_buffer),
                "current_price_data": current_price_data,
                "instrument_key": strategy.config.nifty_instrument_key,
                "symbol": strategy.config.nifty_symbol
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error getting NIFTY live data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@nifty_strategy_router.get("/health")
async def nifty_strategy_health():
    """Health check for NIFTY strategy service"""
    try:
        strategy = await get_nifty_strategy_integration()
        status = await strategy.get_strategy_status()
        
        return {
            "status": "healthy",
            "strategy_active": status.get("is_active", False),
            "strategy_enabled": status.get("enabled", False),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ NIFTY strategy health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }