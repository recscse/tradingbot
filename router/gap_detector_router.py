"""
Gap Detector API Router - Complete Implementation

Provides comprehensive REST API endpoints for the new GapDetectorService with:
- Gap detection with ORB confirmation
- CPR (Central Pivot Range) calculations
- Pivot points (S1-S3, R1-R3)
- Bias determination (Bullish/Bearish/Neutral)
- Real-time gap signals
- Performance metrics
- Test simulation endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging
import asyncio

from services.gap_detector_service import (
    get_gap_detector_service,
    get_current_gaps,
    get_bias,
    process_gap_detection,
    test_gap_detection_simulation
)

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api/v1/gap-detector", tags=["Gap Detector"])

@router.get("/", summary="Get Gap Detector Service Status")
async def get_gap_detector_status() -> Dict[str, Any]:
    """
    Get comprehensive gap detector service status and metrics
    
    Returns:
    - Service status and configuration
    - Performance metrics 
    - Current gaps count
    - Market timing information
    """
    try:
        service = get_gap_detector_service()
        metrics = service.get_performance_metrics()
        
        return {
            "status": "success",
            "data": {
                "service_name": "GapDetectorService",
                "version": "1.0.0",
                "features": [
                    "Gap Up/Down Detection",
                    "ORB15/ORB30 Confirmation", 
                    "CPR Calculations",
                    "Pivot Points (S1-S3, R1-R3)",
                    "Bias Determination",
                    "Redis Publishing",
                    "WebSocket Broadcasting"
                ],
                "metrics": metrics,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "message": "Gap detector service status retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting gap detector status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get service status: {str(e)}")

@router.get("/gaps", summary="Get Current Gap Signals")
async def get_current_gap_signals(
    confirmed_only: bool = Query(True, description="Return only confirmed gaps"),
    limit: int = Query(50, description="Maximum number of results", ge=1, le=200)
) -> Dict[str, Any]:
    """
    Get current gap signals with full details including CPR and pivot levels
    
    Parameters:
    - confirmed_only: Filter for only confirmed gaps
    - limit: Maximum number of results
    """
    try:
        gaps = get_current_gaps()
        
        # Apply filters
        if confirmed_only:
            gaps = [gap for gap in gaps if gap.get('confirmed', False)]
        
        # Apply limit
        gaps = gaps[:limit]
        
        # Group by gap type
        gap_up_signals = [g for g in gaps if g.get('gap_type') == 'gap_up']
        gap_down_signals = [g for g in gaps if g.get('gap_type') == 'gap_down']
        
        return {
            "status": "success",
            "data": {
                "total_gaps": len(gaps),
                "gap_up_count": len(gap_up_signals),
                "gap_down_count": len(gap_down_signals),
                "gap_up_signals": gap_up_signals,
                "gap_down_signals": gap_down_signals,
                "all_signals": gaps,
                "filter_applied": {
                    "confirmed_only": confirmed_only,
                    "limit": limit
                },
                "market_bias": _calculate_overall_bias(gaps),
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "message": f"Retrieved {len(gaps)} gap signals"
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting gap signals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get gap signals: {str(e)}")

@router.get("/gaps/{symbol}", summary="Get Gap Signal for Specific Symbol")
async def get_gap_signal_by_symbol(symbol: str) -> Dict[str, Any]:
    """
    Get gap signal details for a specific symbol including all CPR and pivot data
    
    Parameters:
    - symbol: Stock symbol (e.g., INFY, TCS, RELIANCE)
    """
    try:
        service = get_gap_detector_service()
        
        # Check if symbol has a current gap
        if symbol in service.current_gaps:
            gap_signal = service.current_gaps[symbol]
            gap_data = gap_signal.to_dict()
            
            return {
                "status": "success",
                "data": {
                    "symbol": symbol,
                    "has_gap": True,
                    "gap_signal": gap_data,
                    "cpr_levels": {
                        "pivot": gap_data.get("pivot"),
                        "bc": gap_data.get("bc"),
                        "tc": gap_data.get("tc")
                    },
                    "support_levels": {
                        "s1": gap_data.get("s1"),
                        "s2": gap_data.get("s2"),
                        "s3": gap_data.get("s3")
                    },
                    "resistance_levels": {
                        "r1": gap_data.get("r1"),
                        "r2": gap_data.get("r2"),
                        "r3": gap_data.get("r3")
                    },
                    "bias": gap_data.get("bias"),
                    "orb_data": {
                        "orb_high": gap_data.get("orb_high"),
                        "orb_low": gap_data.get("orb_low"),
                        "orb_minutes": gap_data.get("orb_minutes"),
                        "confirmed": gap_data.get("confirmed")
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "message": f"Gap signal found for {symbol}"
            }
        else:
            # Get bias even if no gap
            bias = get_bias(symbol)
            
            return {
                "status": "success", 
                "data": {
                    "symbol": symbol,
                    "has_gap": False,
                    "bias": bias,
                    "message": "No gap detected for this symbol",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "message": f"No gap signal found for {symbol}"
            }
            
    except Exception as e:
        logger.error(f"❌ Error getting gap signal for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get gap signal for {symbol}: {str(e)}")

@router.get("/bias/{symbol}", summary="Get Market Bias for Symbol")
async def get_symbol_bias(symbol: str) -> Dict[str, Any]:
    """
    Get market bias for a specific symbol
    
    Parameters:
    - symbol: Stock symbol
    
    Returns:
    - Bias: "bullish", "bearish", or "neutral"
    """
    try:
        bias = get_bias(symbol)
        
        return {
            "status": "success",
            "data": {
                "symbol": symbol,
                "bias": bias,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "message": f"Bias for {symbol}: {bias}"
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting bias for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get bias for {symbol}: {str(e)}")

@router.post("/ingest/ohlc", summary="Ingest Yesterday's OHLC Data")
async def ingest_daily_ohlc(ohlc_data: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    """
    Ingest yesterday's OHLC data for gap detection
    
    Request Body:
    {
        "SYMBOL1": {"open": 1490, "high": 1520, "low": 1485, "close": 1510},
        "SYMBOL2": {"open": 3200, "high": 3250, "low": 3180, "close": 3230}
    }
    """
    try:
        service = get_gap_detector_service()
        results = {}
        success_count = 0
        
        for symbol, ohlc in ohlc_data.items():
            try:
                success = service.ingest_daily_ohlc(symbol, ohlc)
                results[symbol] = {"success": success}
                if success:
                    success_count += 1
            except Exception as e:
                results[symbol] = {"success": False, "error": str(e)}
        
        return {
            "status": "success",
            "data": {
                "total_symbols": len(ohlc_data),
                "successful_ingestions": success_count,
                "failed_ingestions": len(ohlc_data) - success_count,
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "message": f"Ingested OHLC data for {success_count}/{len(ohlc_data)} symbols"
        }
        
    except Exception as e:
        logger.error(f"❌ Error ingesting OHLC data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest OHLC data: {str(e)}")

@router.post("/ingest/candle", summary="Ingest Intraday Candle Data")
async def ingest_intraday_candle(candle_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Ingest today's intraday candle data
    
    Request Body:
    {
        "SYMBOL1": {"open": 1535, "high": 1542, "low": 1525, "close": 1530, "volume": 150000},
        "SYMBOL2": {"open": 3170, "high": 3175, "low": 3160, "close": 3165, "volume": 200000}
    }
    """
    try:
        service = get_gap_detector_service()
        results = {}
        success_count = 0
        
        for symbol, candle in candle_data.items():
            try:
                success = service.ingest_intraday_candle(symbol, candle)
                results[symbol] = {"success": success}
                if success:
                    success_count += 1
            except Exception as e:
                results[symbol] = {"success": False, "error": str(e)}
        
        return {
            "status": "success",
            "data": {
                "total_symbols": len(candle_data),
                "successful_ingestions": success_count,
                "failed_ingestions": len(candle_data) - success_count,
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "message": f"Ingested candle data for {success_count}/{len(candle_data)} symbols"
        }
        
    except Exception as e:
        logger.error(f"❌ Error ingesting candle data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest candle data: {str(e)}")

@router.post("/detect", summary="Detect Gaps for Symbol")
async def detect_gap_for_symbol(symbol: str) -> Dict[str, Any]:
    """
    Manually trigger gap detection for a specific symbol
    
    Parameters:
    - symbol: Stock symbol to analyze
    """
    try:
        service = get_gap_detector_service()
        gap_signal = service.detect_gap(symbol)
        
        if gap_signal:
            return {
                "status": "success",
                "data": {
                    "symbol": symbol,
                    "gap_detected": True,
                    "gap_signal": gap_signal.to_dict(),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "message": f"Gap detected for {symbol}: {gap_signal.gap_type} {gap_signal.gap_percentage:.2f}%"
            }
        else:
            return {
                "status": "success",
                "data": {
                    "symbol": symbol,
                    "gap_detected": False,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "message": f"No significant gap detected for {symbol}"
            }
            
    except Exception as e:
        logger.error(f"❌ Error detecting gap for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to detect gap for {symbol}: {str(e)}")

@router.post("/confirm/{symbol}", summary="Confirm Gap with ORB")
async def confirm_gap_for_symbol(
    symbol: str, 
    orb_minutes: int = Query(15, description="ORB window in minutes (15 or 30)")
) -> Dict[str, Any]:
    """
    Confirm gap for a symbol using ORB (Opening Range Breakout)
    
    Parameters:
    - symbol: Stock symbol
    - orb_minutes: ORB window (15 or 30 minutes)
    """
    try:
        service = get_gap_detector_service()
        
        if orb_minutes not in [15, 30]:
            raise HTTPException(status_code=400, detail="ORB minutes must be 15 or 30")
        
        confirmed = service.confirm_gap(symbol, orb_minutes)
        
        gap_signal = service.current_gaps.get(symbol)
        
        return {
            "status": "success",
            "data": {
                "symbol": symbol,
                "confirmed": confirmed,
                "orb_minutes": orb_minutes,
                "gap_signal": gap_signal.to_dict() if gap_signal else None,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "message": f"Gap confirmation for {symbol}: {'CONFIRMED' if confirmed else 'NOT CONFIRMED'}"
        }
        
    except Exception as e:
        logger.error(f"❌ Error confirming gap for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to confirm gap for {symbol}: {str(e)}")

@router.post("/process-batch", summary="Process Market Data Batch")
async def process_market_data_batch(market_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process a batch of market data for gap detection and confirmation
    
    Request Body:
    {
        "SYMBOL1": {"open": 1535, "high": 1542, "low": 1525, "ltp": 1530, "volume": 150000},
        "SYMBOL2": {"open": 3170, "high": 3175, "low": 3160, "ltp": 3165, "volume": 200000}
    }
    """
    try:
        service = get_gap_detector_service()
        gap_signals = await service.process_market_data_batch(market_data)
        
        # Convert to dict format for JSON response
        signals_data = [signal.to_dict() for signal in gap_signals]
        
        return {
            "status": "success", 
            "data": {
                "processed_symbols": len(market_data),
                "gaps_detected": len(gap_signals),
                "gap_signals": signals_data,
                "performance_metrics": service.get_performance_metrics(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "message": f"Processed {len(market_data)} symbols, detected {len(gap_signals)} gaps"
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing market data batch: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process market data batch: {str(e)}")

@router.get("/test/simulation", summary="Run Test Simulation")
async def run_test_simulation() -> Dict[str, Any]:
    """
    Run comprehensive test simulation with sample data
    
    Tests:
    - Gap detection logic
    - CPR and pivot calculations
    - ORB confirmation
    - Bias determination
    - WebSocket broadcasting
    """
    try:
        gap_signals = await test_gap_detection_simulation()
        
        # Convert to dict format
        signals_data = [signal.to_dict() for signal in gap_signals]
        
        return {
            "status": "success",
            "data": {
                "simulation_type": "comprehensive_gap_detection",
                "test_scenarios": ["gap_up", "gap_down", "no_gap"],
                "gaps_detected": len(gap_signals),
                "test_results": signals_data,
                "features_tested": [
                    "Gap Detection Rules",
                    "CPR Calculations", 
                    "Pivot Points",
                    "Bias Determination",
                    "Volume Analysis",
                    "Confidence Scoring"
                ],
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "message": f"Test simulation completed: {len(gap_signals)} gaps detected"
        }
        
    except Exception as e:
        logger.error(f"❌ Error running test simulation: {e}")
        raise HTTPException(status_code=500, detail=f"Test simulation failed: {str(e)}")

@router.get("/metrics", summary="Get Performance Metrics")
async def get_performance_metrics() -> Dict[str, Any]:
    """
    Get detailed performance metrics for the gap detector service
    """
    try:
        service = get_gap_detector_service()
        metrics = service.get_performance_metrics()
        
        return {
            "status": "success",
            "data": {
                "performance_metrics": metrics,
                "service_info": {
                    "name": "GapDetectorService",
                    "version": "1.0.0",
                    "capabilities": [
                        "Real-time gap detection",
                        "ORB confirmation",
                        "CPR calculations", 
                        "Pivot point analysis",
                        "Market bias determination"
                    ]
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "message": "Performance metrics retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")

@router.get("/cpr/{symbol}", summary="Get CPR and Pivot Levels")
async def get_cpr_pivot_levels(symbol: str) -> Dict[str, Any]:
    """
    Get CPR (Central Pivot Range) and pivot levels for a symbol
    
    Parameters:
    - symbol: Stock symbol
    """
    try:
        service = get_gap_detector_service()
        
        if symbol in service.current_gaps:
            gap_signal = service.current_gaps[symbol]
            
            return {
                "status": "success",
                "data": {
                    "symbol": symbol,
                    "cpr_levels": {
                        "pivot": gap_signal.pivot,
                        "bc": gap_signal.bc,  # Bottom Central Pivot
                        "tc": gap_signal.tc   # Top Central Pivot
                    },
                    "support_levels": {
                        "s1": gap_signal.s1,
                        "s2": gap_signal.s2,
                        "s3": gap_signal.s3
                    },
                    "resistance_levels": {
                        "r1": gap_signal.r1,
                        "r2": gap_signal.r2,
                        "r3": gap_signal.r3
                    },
                    "yesterday_ohlc": {
                        "high": gap_signal.yesterday_high,
                        "low": gap_signal.yesterday_low,
                        "close": gap_signal.yesterday_close
                    },
                    "calculation_formulas": {
                        "pivot": "(High + Low + Close) / 3",
                        "bc": "(High + Low) / 2", 
                        "tc": "(Pivot - BC) + Pivot",
                        "r1": "2 * Pivot - Low",
                        "s1": "2 * Pivot - High",
                        "r2": "Pivot + (High - Low)",
                        "s2": "Pivot - (High - Low)",
                        "r3": "High + 2 * (Pivot - Low)",
                        "s3": "Low - 2 * (High - Pivot)"
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "message": f"CPR and pivot levels for {symbol}"
            }
        else:
            return {
                "status": "success",
                "data": {
                    "symbol": symbol,
                    "message": "No gap signal found - CPR levels require yesterday's OHLC data",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "message": f"No CPR data available for {symbol}"
            }
            
    except Exception as e:
        logger.error(f"❌ Error getting CPR levels for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get CPR levels for {symbol}: {str(e)}")

def _calculate_overall_bias(gaps: List[Dict[str, Any]]) -> str:
    """Calculate overall market bias from gap signals"""
    try:
        if not gaps:
            return "neutral"
        
        bullish_count = len([g for g in gaps if g.get('bias') == 'bullish'])
        bearish_count = len([g for g in gaps if g.get('bias') == 'bearish'])
        
        if bullish_count > bearish_count:
            return "bullish"
        elif bearish_count > bullish_count:
            return "bearish"
        else:
            return "neutral"
            
    except Exception:
        return "neutral"

# Export router
__all__ = ["router"]