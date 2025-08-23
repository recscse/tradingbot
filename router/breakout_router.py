#!/usr/bin/env python3
"""
Breakout Scanner API Router

Provides REST API endpoints for the breakout scanner service
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from enum import Enum

logger = logging.getLogger(__name__)

# Import Enhanced Breakout Engine with fallback to legacy
try:
    from services.enhanced_breakout_engine import (
        enhanced_breakout_engine,
        get_enhanced_breakouts_data,
        health_check,
        BreakoutType
    )
    ENHANCED_BREAKOUT_AVAILABLE = True
    BREAKOUT_SERVICE_AVAILABLE = True
    breakout_scanner = enhanced_breakout_engine  # Compatibility alias
    get_breakouts_data = get_enhanced_breakouts_data  # Compatibility alias
    logger.info("✅ Enhanced Breakout Engine imported successfully (vectorized)")
except ImportError:
    logger.warning("Enhanced Breakout Engine not available, trying legacy...")
    try:
        from services.breakout_scanner_service import (
            breakout_scanner,
            get_breakouts_data,
            health_check,
            BreakoutType
        )
        ENHANCED_BREAKOUT_AVAILABLE = False
        BREAKOUT_SERVICE_AVAILABLE = True
        logger.info("✅ Legacy breakout scanner service imported")
    except ImportError as e:
        logger.error(f"❌ No breakout service available: {e}")
        ENHANCED_BREAKOUT_AVAILABLE = False
        BREAKOUT_SERVICE_AVAILABLE = False
        breakout_scanner = None

router = APIRouter(prefix="/api/v1/breakout", tags=["Breakout Scanner"])

# Pydantic models for API responses
class BreakoutTypeEnum(str, Enum):
    VOLUME_BREAKOUT = "volume_breakout"
    PRICE_BREAKOUT = "price_breakout"
    MOMENTUM_BREAKOUT = "momentum_breakout"
    RESISTANCE_BREAKOUT = "resistance_breakout"
    SUPPORT_BREAKDOWN = "support_breakdown"

class BreakoutSignalResponse(BaseModel):
    instrument_key: str
    symbol: str
    breakout_type: str
    current_price: float
    breakout_price: float
    volume: int
    percentage_move: float
    strength: float
    timestamp: str
    market_cap_category: str = "unknown"
    sector: str = "unknown"
    time_ago: str

class BreakoutSummaryResponse(BaseModel):
    total_breakouts_today: int
    breakouts_by_type: Dict[str, List[BreakoutSignalResponse]]
    top_breakouts: List[BreakoutSignalResponse]
    recent_breakouts: List[BreakoutSignalResponse]
    scanner_stats: Dict[str, Any]
    timestamp: str

class HealthCheckResponse(BaseModel):
    service: str
    status: str
    market_open: bool
    instruments_tracked: int
    breakouts_today: int
    last_scan: Optional[str]
    timestamp: str

def check_service_available():
    """Dependency to check if breakout service is available"""
    if not BREAKOUT_SERVICE_AVAILABLE or not breakout_scanner:
        raise HTTPException(
            status_code=503,
            detail="Breakout scanner service is not available"
        )
    return True

@router.get("/health", response_model=HealthCheckResponse)
async def get_health_status(service_check: bool = Depends(check_service_available)):
    """Get health status of breakout scanner service"""
    try:
        health_data = health_check()
        return JSONResponse(content=health_data)
    except Exception as e:
        logger.error(f"❌ Error getting health status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary", response_model=BreakoutSummaryResponse)
async def get_breakouts_summary(service_check: bool = Depends(check_service_available)):
    """Get comprehensive summary of today's breakouts"""
    try:
        summary_data = get_breakouts_data()
        return JSONResponse(content=summary_data)
    except Exception as e:
        logger.error(f"❌ Error getting breakouts summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recent")
async def get_recent_breakouts(
    limit: int = Query(default=20, ge=1, le=100, description="Number of recent breakouts to return"),
    breakout_type: Optional[BreakoutTypeEnum] = Query(default=None, description="Filter by breakout type"),
    service_check: bool = Depends(check_service_available)
):
    """Get recent breakout signals with optional filtering"""
    try:
        summary_data = get_breakouts_data()
        recent_breakouts = summary_data.get("recent_breakouts", [])
        
        # Filter by breakout type if specified
        if breakout_type:
            recent_breakouts = [
                b for b in recent_breakouts 
                if b.get("breakout_type") == breakout_type.value
            ]
        
        # Apply limit
        recent_breakouts = recent_breakouts[:limit]
        
        return JSONResponse(content={
            "breakouts": recent_breakouts,
            "total_count": len(recent_breakouts),
            "filter_applied": breakout_type.value if breakout_type else None,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting recent breakouts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/top")
async def get_top_breakouts(
    limit: int = Query(default=10, ge=1, le=50, description="Number of top breakouts to return"),
    min_strength: float = Query(default=0.0, ge=0.0, le=10.0, description="Minimum strength filter"),
    service_check: bool = Depends(check_service_available)
):
    """Get top breakouts by strength"""
    try:
        summary_data = get_breakouts_data()
        top_breakouts = summary_data.get("top_breakouts", [])
        
        # Filter by minimum strength
        if min_strength > 0:
            top_breakouts = [
                b for b in top_breakouts 
                if b.get("strength", 0) >= min_strength
            ]
        
        # Apply limit
        top_breakouts = top_breakouts[:limit]
        
        return JSONResponse(content={
            "breakouts": top_breakouts,
            "total_count": len(top_breakouts),
            "min_strength_filter": min_strength,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting top breakouts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/by-type/{breakout_type}")
async def get_breakouts_by_type(
    breakout_type: BreakoutTypeEnum,
    limit: int = Query(default=20, ge=1, le=100, description="Number of breakouts to return"),
    service_check: bool = Depends(check_service_available)
):
    """Get breakouts filtered by specific type"""
    try:
        summary_data = get_breakouts_data()
        breakouts_by_type = summary_data.get("breakouts_by_type", {})
        
        type_breakouts = breakouts_by_type.get(breakout_type.value, [])
        
        # Sort by timestamp (most recent first) and apply limit
        type_breakouts = sorted(
            type_breakouts,
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )[:limit]
        
        return JSONResponse(content={
            "breakout_type": breakout_type.value,
            "breakouts": type_breakouts,
            "total_count": len(type_breakouts),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting breakouts by type: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_scanner_statistics(service_check: bool = Depends(check_service_available)):
    """Get detailed scanner statistics and performance metrics"""
    try:
        summary_data = get_breakouts_data()
        scanner_stats = summary_data.get("scanner_stats", {})
        
        # Calculate additional statistics
        breakouts_by_type = summary_data.get("breakouts_by_type", {})
        type_counts = {
            breakout_type: len(breakouts)
            for breakout_type, breakouts in breakouts_by_type.items()
        }
        
        # Calculate breakout frequency (per hour)
        total_breakouts = summary_data.get("total_breakouts_today", 0)
        hours_since_start = 8  # Assume 8-hour trading day
        breakouts_per_hour = total_breakouts / hours_since_start if hours_since_start > 0 else 0
        
        stats = {
            **scanner_stats,
            "breakout_type_distribution": type_counts,
            "breakouts_per_hour": round(breakouts_per_hour, 2),
            "scanner_efficiency": {
                "instruments_scanned": scanner_stats.get("instruments_tracked", 0),
                "breakouts_detected": total_breakouts,
                "detection_rate": f"{(total_breakouts / max(1, scanner_stats.get('instruments_tracked', 1))) * 100:.2f}%"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(content=stats)
        
    except Exception as e:
        logger.error(f"❌ Error getting scanner statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/symbol/{symbol}")
async def get_symbol_breakouts(
    symbol: str,
    days_back: int = Query(default=1, ge=1, le=7, description="Number of days to look back"),
    service_check: bool = Depends(check_service_available)
):
    """Get breakout history for a specific symbol"""
    try:
        # For now, we only have today's data
        # In future, this could query historical breakout data
        summary_data = get_breakouts_data()
        all_breakouts = []
        
        # Collect all breakouts from all types
        breakouts_by_type = summary_data.get("breakouts_by_type", {})
        for type_breakouts in breakouts_by_type.values():
            all_breakouts.extend(type_breakouts)
        
        # Filter by symbol
        symbol_breakouts = [
            b for b in all_breakouts
            if b.get("symbol", "").upper() == symbol.upper()
        ]
        
        # Sort by timestamp (most recent first)
        symbol_breakouts = sorted(
            symbol_breakouts,
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        
        return JSONResponse(content={
            "symbol": symbol.upper(),
            "breakouts": symbol_breakouts,
            "total_count": len(symbol_breakouts),
            "days_searched": days_back,
            "timestamp": datetime.now().isoformat(),
            "timestamp_formatted": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "query_time": datetime.now().strftime("%I:%M:%S %p")
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting symbol breakouts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/timestamps")
async def get_breakouts_with_timestamps(
    from_time: Optional[str] = Query(default=None, description="Start time (ISO format or HH:MM)"),
    to_time: Optional[str] = Query(default=None, description="End time (ISO format or HH:MM)"),
    limit: int = Query(default=50, ge=1, le=200, description="Number of breakouts to return"),
    service_check: bool = Depends(check_service_available)
):
    """Get breakouts filtered by timestamp range"""
    try:
        summary_data = get_breakouts_data()
        all_breakouts = []
        
        # Collect all breakouts from all types
        breakouts_by_type = summary_data.get("breakouts_by_type", {})
        for type_breakouts in breakouts_by_type.values():
            all_breakouts.extend(type_breakouts)
        
        # Parse time filters
        filtered_breakouts = all_breakouts
        
        if from_time or to_time:
            filtered_breakouts = []
            today = datetime.now().date()
            
            for breakout in all_breakouts:
                breakout_time = datetime.fromisoformat(breakout.get("timestamp", "").replace('Z', '+00:00'))
                
                # Check from_time filter
                if from_time:
                    if ":" in from_time and len(from_time) <= 5:  # HH:MM format
                        from_dt = datetime.combine(today, datetime.strptime(from_time, "%H:%M").time())
                    else:  # ISO format
                        from_dt = datetime.fromisoformat(from_time.replace('Z', '+00:00'))
                    
                    if breakout_time < from_dt:
                        continue
                
                # Check to_time filter
                if to_time:
                    if ":" in to_time and len(to_time) <= 5:  # HH:MM format
                        to_dt = datetime.combine(today, datetime.strptime(to_time, "%H:%M").time())
                    else:  # ISO format
                        to_dt = datetime.fromisoformat(to_time.replace('Z', '+00:00'))
                    
                    if breakout_time > to_dt:
                        continue
                
                filtered_breakouts.append(breakout)
        
        # Sort by timestamp (most recent first) and apply limit
        filtered_breakouts = sorted(
            filtered_breakouts,
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )[:limit]
        
        return JSONResponse(content={
            "breakouts": filtered_breakouts,
            "total_count": len(filtered_breakouts),
            "filters": {
                "from_time": from_time,
                "to_time": to_time,
                "limit": limit
            },
            "timestamp": datetime.now().isoformat(),
            "timestamp_formatted": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "query_time": datetime.now().strftime("%I:%M:%S %p")
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting breakouts by timestamp: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start")
async def start_scanner(service_check: bool = Depends(check_service_available)):
    """Start the breakout scanner service"""
    try:
        if breakout_scanner.is_running:
            return JSONResponse(content={
                "message": "Breakout scanner is already running",
                "status": "running",
                "timestamp": datetime.now().isoformat()
            })
        
        await breakout_scanner.start()
        
        return JSONResponse(content={
            "message": "Breakout scanner started successfully",
            "status": "running",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error starting breakout scanner: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_scanner(service_check: bool = Depends(check_service_available)):
    """Stop the breakout scanner service"""
    try:
        if not breakout_scanner.is_running:
            return JSONResponse(content={
                "message": "Breakout scanner is already stopped",
                "status": "stopped",
                "timestamp": datetime.now().isoformat()
            })
        
        await breakout_scanner.stop()
        
        return JSONResponse(content={
            "message": "Breakout scanner stopped successfully",
            "status": "stopped",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error stopping breakout scanner: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
async def get_scanner_config(service_check: bool = Depends(check_service_available)):
    """Get current scanner configuration"""
    try:
        config = {
            "price_range": {
                "min_price": breakout_scanner.min_price,
                "max_price": breakout_scanner.max_price
            },
            "volume_settings": {
                "min_volume": breakout_scanner.min_volume,
                "volume_multiplier": breakout_scanner.volume_multiplier
            },
            "breakout_settings": {
                "breakout_threshold": breakout_scanner.breakout_threshold,
                "resistance_lookback": breakout_scanner.resistance_lookback
            },
            "service_status": {
                "is_running": breakout_scanner.is_running,
                "is_market_open": breakout_scanner.is_market_open,
                "current_trading_day": breakout_scanner.current_trading_day.isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(content=config)
        
    except Exception as e:
        logger.error(f"❌ Error getting scanner config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time breakout updates
@router.websocket("/ws")
async def breakout_websocket(websocket):
    """WebSocket endpoint for real-time breakout updates"""
    await websocket.accept()
    
    try:
        logger.info("🔌 Breakout WebSocket client connected")
        
        # Send initial data
        if BREAKOUT_SERVICE_AVAILABLE:
            initial_data = get_breakouts_data()
            await websocket.send_json({
                "type": "initial_data",
                "data": initial_data
            })
        
        # Keep connection alive and send updates
        while True:
            # In a real implementation, this would listen to breakout_scanner events
            # For now, we'll send periodic updates
            await asyncio.sleep(30)  # Send update every 30 seconds
            
            if BREAKOUT_SERVICE_AVAILABLE and breakout_scanner.is_running:
                update_data = get_breakouts_data()
                await websocket.send_json({
                    "type": "breakout_update",
                    "data": update_data,
                    "timestamp": datetime.now().isoformat()
                })
            
    except Exception as e:
        logger.error(f"❌ Breakout WebSocket error: {e}")
    finally:
        logger.info("🔌 Breakout WebSocket client disconnected")

# Enhanced endpoints for Enhanced Breakout Engine
if ENHANCED_BREAKOUT_AVAILABLE:
    
    @router.get("/enhanced/metrics")
    async def get_enhanced_metrics(service_check: bool = Depends(check_service_available)):
        """Get comprehensive enhanced engine metrics"""
        try:
            metrics = enhanced_breakout_engine.get_metrics()
            return JSONResponse(content={
                "engine_version": "2.0_vectorized",
                "capabilities": [
                    "vectorized_processing",
                    "16_breakout_types",
                    "memory_efficient_storage", 
                    "real_time_analytics"
                ],
                "metrics": metrics,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"❌ Error getting enhanced metrics: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/enhanced/performance")
    async def get_performance_stats(service_check: bool = Depends(check_service_available)):
        """Get detailed performance statistics"""
        try:
            metrics = enhanced_breakout_engine.get_metrics()
            storage_stats = {
                "memory_usage_mb": enhanced_breakout_engine.storage.get_memory_usage(),
                "instruments_tracked": enhanced_breakout_engine.storage.next_index,
                "max_instruments": enhanced_breakout_engine.storage.max_instruments,
                "buffer_size": enhanced_breakout_engine.storage.buffer_size,
                "storage_efficiency": f"{(enhanced_breakout_engine.storage.next_index / enhanced_breakout_engine.storage.max_instruments) * 100:.2f}%"
            }
            
            return JSONResponse(content={
                "performance_metrics": metrics,
                "storage_statistics": storage_stats,
                "processing_speed": {
                    "target_latency_ms": 5.0,
                    "actual_latency_ms": metrics.get("avg_processing_time_ms", 0),
                    "performance_ratio": f"{(5.0 / max(0.1, metrics.get('avg_processing_time_ms', 5.0))) * 100:.1f}%"
                },
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"❌ Error getting performance stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/enhanced/types")
    async def get_all_breakout_types():
        """Get all available breakout types in enhanced engine"""
        types = [breakout_type.value for breakout_type in BreakoutType]
        return JSONResponse(content={
            "total_types": len(types),
            "breakout_types": types,
            "enhanced_types": [
                "volume_surge", "unusual_volume", "strong_momentum", 
                "acceleration", "high_breakout", "low_breakdown",
                "gap_up", "gap_down", "volatility_expansion", 
                "price_squeeze", "triangular_breakout", "channel_breakout"
            ],
            "legacy_compatible": True,
            "timestamp": datetime.now().isoformat()
        })

# Fallback endpoints when service is not available
if not BREAKOUT_SERVICE_AVAILABLE:
    
    @router.get("/health")
    async def get_health_status_fallback():
        """Fallback health check when service is not available"""
        return JSONResponse(
            status_code=503,
            content={
                "service": "breakout_scanner",
                "status": "unavailable",
                "error": "Breakout scanner service not available",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    @router.get("/summary")
    async def get_breakouts_summary_fallback():
        """Fallback summary when service is not available"""
        return JSONResponse(
            status_code=503,
            content={
                "error": "Breakout scanner service not available",
                "total_breakouts_today": 0,
                "breakouts_by_type": {},
                "top_breakouts": [],
                "recent_breakouts": [],
                "timestamp": datetime.now().isoformat()
            }
        )