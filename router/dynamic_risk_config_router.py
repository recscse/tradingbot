"""
Dynamic Risk Configuration API Router
Allows runtime configuration of risk parameters per strategy
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from services.dynamic_risk_config import (
    dynamic_risk_manager,
    RiskProfile,
    MarketVolatility,
    DynamicRiskConfig
)
from services.enhanced_trading_phases import TradingPhaseManager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/risk-config", tags=["Dynamic Risk Configuration"]
)


class CreateStrategyConfigRequest(BaseModel):
    strategy_name: str
    base_profile: str = "moderate"  # conservative, moderate, aggressive
    custom_overrides: Optional[Dict[str, Any]] = None


class UpdateRiskConfigRequest(BaseModel):
    max_loss_per_position: Optional[float] = None
    max_total_exposure: Optional[float] = None
    max_daily_loss: Optional[float] = None
    position_size_multiplier: Optional[float] = None
    max_positions: Optional[int] = None
    trailing_stop_activation: Optional[float] = None
    trailing_stop_percentage: Optional[float] = None
    profit_booking_levels: Optional[list] = None


@router.get("/status")
async def get_risk_config_status():
    """Get current risk configuration status"""
    try:
        # Get current trading phase
        current_phase = TradingPhaseManager.get_current_trading_phase()
        phase_timing = TradingPhaseManager.get_next_phase_timing()

        # Get risk summary
        risk_summary = dynamic_risk_manager.get_risk_summary()

        status_data = {
            "trading_phase": {
                "current_phase": current_phase.value,
                "phase_description": TradingPhaseManager.get_phase_description(current_phase),
                "recommended_action": TradingPhaseManager.get_recommended_action(current_phase),
                "next_phase_timing": phase_timing,
            },
            "risk_configuration": risk_summary,
            "market_timing": {
                "premarket_window": "9:00 AM - 9:15 AM",
                "market_open_window": "9:15 AM - 9:25 AM",
                "live_trading_window": "9:25 AM - 3:30 PM",
                "current_time": datetime.now().strftime("%H:%M:%S"),
            }
        }

        return JSONResponse(
            content={
                "success": True,
                "data": status_data,
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Error getting risk config status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profiles")
async def get_risk_profiles():
    """Get available risk profiles and their configurations"""
    try:
        profiles_data = {}

        for profile in RiskProfile:
            if profile in dynamic_risk_manager.risk_templates:
                template = dynamic_risk_manager.risk_templates[profile]
                profiles_data[profile.value] = {
                    "max_loss_per_position_percent": template.max_loss_per_position * 100,
                    "max_total_exposure_percent": template.max_total_exposure * 100,
                    "max_daily_loss_percent": template.max_daily_loss * 100,
                    "position_size_multiplier": template.position_size_multiplier,
                    "max_positions": template.max_positions,
                    "trailing_stop_activation_percent": template.trailing_stop_activation * 100,
                    "trailing_stop_percentage": template.trailing_stop_percentage * 100,
                    "profit_booking_levels_percent": [level * 100 for level in template.profit_booking_levels],
                    "description": f"{profile.value.title()} risk profile"
                }

        return JSONResponse(
            content={
                "success": True,
                "data": {
                    "available_profiles": profiles_data,
                    "recommended_usage": {
                        "conservative": "New traders, small capital, bearish markets",
                        "moderate": "Experienced traders, balanced approach, normal markets",
                        "aggressive": "Expert traders, large capital, bullish markets"
                    }
                },
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Error getting risk profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategies/create")
async def create_strategy_config(request: CreateStrategyConfigRequest):
    """Create a new risk configuration for a trading strategy"""
    try:
        # Validate risk profile
        try:
            base_profile = RiskProfile(request.base_profile.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid risk profile. Available: {[p.value for p in RiskProfile]}"
            )

        # Create the configuration
        config = dynamic_risk_manager.create_strategy_config(
            strategy_name=request.strategy_name,
            base_profile=base_profile,
            custom_overrides=request.custom_overrides or {}
        )

        config_data = {
            "strategy_name": config.strategy_name,
            "risk_profile": config.risk_profile.value,
            "created_at": config.created_at,
            "parameters": {
                "max_loss_per_position_percent": config.max_loss_per_position * 100,
                "max_total_exposure_percent": config.max_total_exposure * 100,
                "max_daily_loss_percent": config.max_daily_loss * 100,
                "position_size_multiplier": config.position_size_multiplier,
                "max_positions": config.max_positions,
                "trailing_stop_activation_percent": config.trailing_stop_activation * 100,
                "trailing_stop_percentage": config.trailing_stop_percentage * 100,
                "profit_booking_levels_percent": [level * 100 for level in config.profit_booking_levels],
            },
            "overrides_applied": list(request.custom_overrides.keys()) if request.custom_overrides else [],
        }

        return JSONResponse(
            content={
                "success": True,
                "message": f"Strategy configuration '{request.strategy_name}' created successfully",
                "data": config_data,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating strategy config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategies/{strategy_name}/activate")
async def activate_strategy_config(strategy_name: str):
    """Activate a specific risk configuration"""
    try:
        success = dynamic_risk_manager.activate_strategy_config(strategy_name)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy configuration '{strategy_name}' not found"
            )

        # Get the activated configuration
        active_config = dynamic_risk_manager.active_config
        current_risk_summary = dynamic_risk_manager.get_risk_summary()

        return JSONResponse(
            content={
                "success": True,
                "message": f"Strategy configuration '{strategy_name}' activated successfully",
                "data": {
                    "active_strategy": strategy_name,
                    "risk_profile": active_config.risk_profile.value,
                    "activated_at": datetime.now().isoformat(),
                    "configuration": current_risk_summary,
                },
                "timestamp": datetime.now().isoformat(),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating strategy config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/active/update")
async def update_active_config(request: UpdateRiskConfigRequest):
    """Update the currently active risk configuration"""
    try:
        # Convert request to updates dict, filtering out None values
        updates = {
            key: value for key, value in request.dict().items()
            if value is not None
        }

        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")

        success = dynamic_risk_manager.update_active_config(updates)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to update configuration")

        # Get updated configuration
        updated_summary = dynamic_risk_manager.get_risk_summary()

        return JSONResponse(
            content={
                "success": True,
                "message": f"Active risk configuration updated successfully",
                "data": {
                    "updated_parameters": list(updates.keys()),
                    "updated_at": datetime.now().isoformat(),
                    "new_configuration": updated_summary,
                },
                "timestamp": datetime.now().isoformat(),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating active config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_config():
    """Get currently active risk configuration"""
    try:
        summary = dynamic_risk_manager.get_risk_summary()

        return JSONResponse(
            content={
                "success": True,
                "data": summary,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Error getting active config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/position-limits")
async def get_position_limits(capital: float = Query(..., description="Total capital amount")):
    """Get position size limits based on current risk configuration"""
    try:
        limits = dynamic_risk_manager.get_position_size_limits(capital)

        limits_data = {
            "capital_input": capital,
            "position_limits": {
                "min_position_capital": limits["min_position_capital"],
                "max_position_capital": limits["max_position_capital"],
                "recommended_position_capital": limits["recommended_position_capital"],
                "total_max_exposure": limits["total_max_exposure"],
                "max_positions": limits["max_positions"],
                "position_size_multiplier": limits["position_size_multiplier"],
            },
            "risk_percentages": {
                "max_loss_per_position_percent": dynamic_risk_manager.active_config.max_loss_per_position * 100,
                "max_total_exposure_percent": dynamic_risk_manager.active_config.max_total_exposure * 100,
                "position_allocation_percent": (limits["recommended_position_capital"] / capital) * 100,
            }
        }

        return JSONResponse(
            content={
                "success": True,
                "data": limits_data,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Error getting position limits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market-adjustment")
async def apply_market_condition_adjustment(
    market_sentiment: str = Query(..., description="Market sentiment: bullish, bearish, neutral"),
    volatility_level: str = Query("medium", description="Volatility level: low, medium, high, extreme")
):
    """Apply market condition adjustments to risk configuration"""
    try:
        # Validate volatility level
        try:
            volatility = MarketVolatility(volatility_level.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid volatility level. Available: {[v.value for v in MarketVolatility]}"
            )

        # Apply adjustments
        adjusted_config = dynamic_risk_manager.adjust_for_market_conditions(
            market_sentiment.lower(), volatility
        )

        adjustment_data = {
            "market_conditions": {
                "sentiment": market_sentiment.lower(),
                "volatility_level": volatility.value,
            },
            "original_config": {
                "max_loss_per_position_percent": dynamic_risk_manager.active_config.max_loss_per_position * 100,
                "max_total_exposure_percent": dynamic_risk_manager.active_config.max_total_exposure * 100,
                "position_size_multiplier": dynamic_risk_manager.active_config.position_size_multiplier,
            },
            "adjusted_config": {
                "max_loss_per_position_percent": adjusted_config.max_loss_per_position * 100,
                "max_total_exposure_percent": adjusted_config.max_total_exposure * 100,
                "position_size_multiplier": adjusted_config.position_size_multiplier,
            },
            "adjustments_applied": {
                "sentiment_adjustment": "Applied bear/bull market multiplier",
                "volatility_adjustment": f"Applied {volatility.value} volatility adjustments",
            }
        }

        return JSONResponse(
            content={
                "success": True,
                "message": "Market condition adjustments calculated",
                "data": adjustment_data,
                "note": "These are calculated adjustments. Use /active/update to apply them permanently.",
                "timestamp": datetime.now().isoformat(),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying market adjustments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies")
async def list_all_strategies():
    """List all available strategy configurations"""
    try:
        strategies_data = {}

        for name, config in dynamic_risk_manager.risk_configs.items():
            strategies_data[name] = {
                "risk_profile": config.risk_profile.value,
                "created_at": config.created_at,
                "updated_at": config.updated_at,
                "is_active": name == dynamic_risk_manager.active_strategy_name,
                "parameters": {
                    "max_loss_per_position_percent": config.max_loss_per_position * 100,
                    "max_total_exposure_percent": config.max_total_exposure * 100,
                    "max_positions": config.max_positions,
                }
            }

        return JSONResponse(
            content={
                "success": True,
                "data": {
                    "strategies": strategies_data,
                    "active_strategy": dynamic_risk_manager.active_strategy_name,
                    "total_strategies": len(strategies_data),
                },
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Error listing strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/strategies/{strategy_name}")
async def delete_strategy_config(strategy_name: str):
    """Delete a strategy configuration"""
    try:
        if strategy_name not in dynamic_risk_manager.risk_configs:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy configuration '{strategy_name}' not found"
            )

        if strategy_name == dynamic_risk_manager.active_strategy_name:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the currently active strategy configuration"
            )

        # Delete the configuration
        del dynamic_risk_manager.risk_configs[strategy_name]

        return JSONResponse(
            content={
                "success": True,
                "message": f"Strategy configuration '{strategy_name}' deleted successfully",
                "remaining_strategies": list(dynamic_risk_manager.risk_configs.keys()),
                "timestamp": datetime.now().isoformat(),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting strategy config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup/save")
async def save_configurations_backup(filepath: str = Query("risk_config_backup.json")):
    """Save all risk configurations to backup file"""
    try:
        success = dynamic_risk_manager.save_config_to_file(filepath)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to save configurations")

        return JSONResponse(
            content={
                "success": True,
                "message": f"Configurations saved to {filepath}",
                "saved_strategies": list(dynamic_risk_manager.risk_configs.keys()),
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Error saving backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup/load")
async def load_configurations_backup(filepath: str = Query("risk_config_backup.json")):
    """Load risk configurations from backup file"""
    try:
        success = dynamic_risk_manager.load_config_from_file(filepath)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to load configurations")

        return JSONResponse(
            content={
                "success": True,
                "message": f"Configurations loaded from {filepath}",
                "loaded_strategies": list(dynamic_risk_manager.risk_configs.keys()),
                "active_strategy": dynamic_risk_manager.active_strategy_name,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Error loading backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))