#!/usr/bin/env python3
"""
Gap Analysis API Router

Provides comprehensive REST API endpoints for gap up/gap down analysis:
- Real-time gap detection data
- Gap categorization and filtering
- Sustainability tracking
- Sector-wise gap analysis
- Historical gap data with timestamps
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from services.enhanced_gap_detection import enhanced_gap_detection, get_gap_data, health_check

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api/v1/gap-analysis", tags=["Gap Analysis"])

@router.get("/", summary="Get Complete Gap Analysis Data")
async def get_complete_gap_analysis() -> Dict[str, Any]:
    """
    Get comprehensive gap analysis data including gap up and gap down stocks
    
    Uses ONLY the enhanced gap detection service (numpy/pandas optimized)
    
    Returns:
    - All gap up stocks (categorized by size)
    - All gap down stocks (categorized by size) 
    - Recent gap activity
    - Sector analysis
    - Performance statistics
    """
    try:
        gap_data = get_gap_data()
        return {
            "status": "success",
            "data": gap_data,
            "service": "enhanced",
            "message": "Gap analysis data retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting gap analysis data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gap-up", summary="Get Gap Up Stocks")
async def get_gap_up_stocks(
    size: Optional[str] = Query(None, description="Filter by gap size: small, medium, large"),
    limit: int = Query(50, description="Maximum number of results", ge=1, le=200),
    min_gap: float = Query(1.0, description="Minimum gap percentage", ge=0.1)
) -> Dict[str, Any]:
    """
    Get stocks that gapped up at market open
    
    Parameters:
    - size: Filter by gap size (small: 1-2.5%, medium: 2.5-5%, large: >5%)
    - limit: Maximum number of results
    - min_gap: Minimum gap percentage threshold
    """
    try:
        gap_data = get_gap_data()
        gap_up_data = gap_data.get("gap_up", {})
        
        # Apply filters
        if size and size in ["small", "medium", "large"]:
            stocks = gap_up_data.get(size, [])
        else:
            stocks = gap_up_data.get("all", [])
        
        # Filter by minimum gap
        filtered_stocks = [
            stock for stock in stocks 
            if stock.get("gap_percent", 0) >= min_gap
        ]
        
        # Apply limit
        result_stocks = filtered_stocks[:limit]
        
        return {
            "status": "success",
            "data": {
                "gap_up_stocks": result_stocks,
                "total_found": len(filtered_stocks),
                "returned": len(result_stocks),
                "filter_applied": {
                    "size": size,
                    "min_gap": min_gap,
                    "limit": limit
                },
                "summary": gap_up_data.get("count", {}),
                "timestamp": datetime.now().isoformat()
            },
            "message": f"Found {len(result_stocks)} gap up stocks"
        }
    except Exception as e:
        logger.error(f"Error getting gap up stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gap-down", summary="Get Gap Down Stocks")
async def get_gap_down_stocks(
    size: Optional[str] = Query(None, description="Filter by gap size: small, medium, large"),
    limit: int = Query(50, description="Maximum number of results", ge=1, le=200),
    min_gap: float = Query(1.0, description="Minimum gap percentage (absolute)", ge=0.1)
) -> Dict[str, Any]:
    """
    Get stocks that gapped down at market open
    
    Parameters:
    - size: Filter by gap size (small: 1-2.5%, medium: 2.5-5%, large: >5%)
    - limit: Maximum number of results
    - min_gap: Minimum gap percentage threshold (absolute value)
    """
    try:
        gap_data = get_gap_data()
        gap_down_data = gap_data.get("gap_down", {})
        
        # Apply filters
        if size and size in ["small", "medium", "large"]:
            stocks = gap_down_data.get(size, [])
        else:
            stocks = gap_down_data.get("all", [])
        
        # Filter by minimum gap (absolute value)
        filtered_stocks = [
            stock for stock in stocks 
            if abs(stock.get("gap_percent", 0)) >= min_gap
        ]
        
        # Apply limit
        result_stocks = filtered_stocks[:limit]
        
        return {
            "status": "success",
            "data": {
                "gap_down_stocks": result_stocks,
                "total_found": len(filtered_stocks),
                "returned": len(result_stocks),
                "filter_applied": {
                    "size": size,
                    "min_gap": min_gap,
                    "limit": limit
                },
                "summary": gap_down_data.get("count", {}),
                "timestamp": datetime.now().isoformat()
            },
            "message": f"Found {len(result_stocks)} gap down stocks"
        }
    except Exception as e:
        logger.error(f"Error getting gap down stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recent", summary="Get Recent Gap Activity")
async def get_recent_gap_activity(
    hours: int = Query(2, description="Hours to look back", ge=1, le=24),
    limit: int = Query(30, description="Maximum number of results", ge=1, le=100)
) -> Dict[str, Any]:
    """
    Get recent gap activity within specified time frame
    
    Parameters:
    - hours: Number of hours to look back
    - limit: Maximum number of results
    """
    try:
        gap_data = get_gap_data()
        all_recent = gap_data.get("recent_gaps", [])
        
        # Filter by time frame
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        filtered_gaps = []
        for gap in all_recent:
            try:
                gap_time = datetime.fromisoformat(gap.get("timestamp", ""))
                if gap_time >= cutoff_time:
                    filtered_gaps.append(gap)
            except (ValueError, TypeError):
                continue
        
        # Apply limit
        result_gaps = filtered_gaps[:limit]
        
        return {
            "status": "success",
            "data": {
                "recent_gaps": result_gaps,
                "total_found": len(filtered_gaps),
                "returned": len(result_gaps),
                "time_range": {
                    "hours_back": hours,
                    "from_time": cutoff_time.isoformat(),
                    "to_time": datetime.now().isoformat()
                },
                "timestamp": datetime.now().isoformat()
            },
            "message": f"Found {len(result_gaps)} recent gaps in last {hours} hours"
        }
    except Exception as e:
        logger.error(f"Error getting recent gap activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics", summary="Get Gap Analysis Statistics")
async def get_gap_statistics() -> Dict[str, Any]:
    """
    Get comprehensive gap analysis statistics and market overview
    """
    try:
        gap_data = get_gap_data()
        
        statistics = gap_data.get("statistics", {})
        sustainability = gap_data.get("sustainability", {})
        sector_analysis = gap_data.get("sector_analysis", {})
        
        # Calculate additional metrics
        total_gaps = statistics.get("total_gaps_today", 0)
        gap_up_total = statistics.get("gap_up_total", 0)
        gap_down_total = statistics.get("gap_down_total", 0)
        
        gap_up_percentage = (gap_up_total / total_gaps * 100) if total_gaps > 0 else 0
        gap_down_percentage = (gap_down_total / total_gaps * 100) if total_gaps > 0 else 0
        
        # Top sectors by gap activity
        sorted_sectors = sorted(
            sector_analysis.items(),
            key=lambda x: x[1].get("total", 0),
            reverse=True
        )[:10]
        
        return {
            "status": "success",
            "data": {
                "overall_statistics": {
                    **statistics,
                    "gap_up_percentage": round(gap_up_percentage, 1),
                    "gap_down_percentage": round(gap_down_percentage, 1),
                    "market_bias": "gap_up" if gap_up_total > gap_down_total else ("gap_down" if gap_down_total > gap_up_total else "neutral")
                },
                "sustainability_analysis": sustainability,
                "top_sectors": [
                    {
                        "sector": sector,
                        "gap_up": data.get("gap_up", 0),
                        "gap_down": data.get("gap_down", 0),
                        "total": data.get("total", 0)
                    }
                    for sector, data in sorted_sectors
                ],
                "timestamp": datetime.now().isoformat()
            },
            "message": "Gap analysis statistics retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting gap statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/top-performers", summary="Get Top Gap Performers")
async def get_top_gap_performers(
    direction: str = Query("both", description="Direction: up, down, or both"),
    limit: int = Query(20, description="Number of top performers", ge=1, le=50)
) -> Dict[str, Any]:
    """
    Get top gap performers by gap percentage
    
    Parameters:
    - direction: Filter by gap direction (up, down, or both)
    - limit: Number of top performers to return
    """
    try:
        gap_data = get_gap_data()
        
        top_gap_up = gap_data.get("top_gap_up", [])[:limit]
        top_gap_down = gap_data.get("top_gap_down", [])[:limit]
        
        result = {
            "status": "success",
            "data": {
                "timestamp": datetime.now().isoformat()
            },
            "message": "Top gap performers retrieved successfully"
        }
        
        if direction in ["up", "both"]:
            result["data"]["top_gap_up"] = top_gap_up
            
        if direction in ["down", "both"]:
            result["data"]["top_gap_down"] = top_gap_down
            
        if direction == "both":
            # Combined list sorted by absolute gap percentage
            combined = []
            for gap in top_gap_up + top_gap_down:
                gap_copy = gap.copy()
                gap_copy["abs_gap_percent"] = abs(gap.get("gap_percent", 0))
                combined.append(gap_copy)
            
            combined.sort(key=lambda x: x["abs_gap_percent"], reverse=True)
            result["data"]["top_combined"] = combined[:limit]
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting top gap performers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sustainability", summary="Get Gap Sustainability Analysis")
async def get_gap_sustainability(
    sustainability_type: Optional[str] = Query(None, description="Filter by type: sustaining, fading, filled, expanding")
) -> Dict[str, Any]:
    """
    Get gap sustainability analysis
    
    Parameters:
    - sustainability_type: Filter by sustainability status
    """
    try:
        gap_data = get_gap_data()
        sustainability_stats = gap_data.get("sustainability", {})
        
        # Get all gaps with their sustainability info
        all_gaps = []
        for gap in gap_data.get("gap_up", {}).get("all", []) + gap_data.get("gap_down", {}).get("all", []):
            if sustainability_type is None or gap.get("sustainability") == sustainability_type:
                all_gaps.append(gap)
        
        # Group by sustainability type
        grouped_gaps = {}
        for gap in all_gaps:
            sust_type = gap.get("sustainability", "unknown")
            if sust_type not in grouped_gaps:
                grouped_gaps[sust_type] = []
            grouped_gaps[sust_type].append(gap)
        
        return {
            "status": "success",
            "data": {
                "sustainability_statistics": sustainability_stats,
                "gaps_by_sustainability": grouped_gaps,
                "filter_applied": sustainability_type,
                "total_analyzed": len(all_gaps),
                "timestamp": datetime.now().isoformat()
            },
            "message": "Gap sustainability analysis retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting gap sustainability: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sectors", summary="Get Sector-wise Gap Analysis")
async def get_sector_gap_analysis(
    sector: Optional[str] = Query(None, description="Filter by specific sector")
) -> Dict[str, Any]:
    """
    Get sector-wise gap analysis
    
    Parameters:
    - sector: Filter by specific sector name
    """
    try:
        gap_data = get_gap_data()
        sector_analysis = gap_data.get("sector_analysis", {})
        
        if sector:
            # Filter for specific sector
            sector_data = sector_analysis.get(sector, {})
            if not sector_data:
                return {
                    "status": "success",
                    "data": {
                        "sector": sector,
                        "message": "No gap data found for this sector",
                        "timestamp": datetime.now().isoformat()
                    },
                    "message": f"No gap data found for sector: {sector}"
                }
            
            return {
                "status": "success",
                "data": {
                    "sector": sector,
                    "gap_analysis": sector_data,
                    "timestamp": datetime.now().isoformat()
                },
                "message": f"Gap analysis for {sector} sector retrieved successfully"
            }
        else:
            # Return all sectors sorted by activity
            sorted_sectors = sorted(
                sector_analysis.items(),
                key=lambda x: x[1].get("total", 0),
                reverse=True
            )
            
            sector_summary = []
            for sector_name, data in sorted_sectors:
                sector_summary.append({
                    "sector": sector_name,
                    "gap_up": data.get("gap_up", 0),
                    "gap_down": data.get("gap_down", 0),
                    "total": data.get("total", 0),
                    "gap_bias": "up" if data.get("gap_up", 0) > data.get("gap_down", 0) else ("down" if data.get("gap_down", 0) > data.get("gap_up", 0) else "neutral")
                })
            
            return {
                "status": "success",
                "data": {
                    "sector_analysis": sector_summary,
                    "total_sectors": len(sector_summary),
                    "timestamp": datetime.now().isoformat()
                },
                "message": "Sector-wise gap analysis retrieved successfully"
            }
    except Exception as e:
        logger.error(f"Error getting sector gap analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/timestamps", summary="Get Gaps by Time Range")
async def get_gaps_by_time_range(
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    limit: int = Query(100, description="Maximum results", ge=1, le=500)
) -> Dict[str, Any]:
    """
    Get gaps within specific time range with detailed timestamps
    
    Parameters:
    - start_time: Start time in ISO format (optional)
    - end_time: End time in ISO format (optional)
    - limit: Maximum number of results
    """
    try:
        gap_data = get_gap_data()
        
        # Get all gaps
        all_gaps = []
        for gap in gap_data.get("gap_up", {}).get("all", []) + gap_data.get("gap_down", {}).get("all", []):
            all_gaps.append(gap)
        
        # Apply time filters
        filtered_gaps = []
        for gap in all_gaps:
            try:
                gap_time = datetime.fromisoformat(gap.get("timestamp", ""))
                
                # Check start time
                if start_time:
                    start_dt = datetime.fromisoformat(start_time)
                    if gap_time < start_dt:
                        continue
                
                # Check end time  
                if end_time:
                    end_dt = datetime.fromisoformat(end_time)
                    if gap_time > end_dt:
                        continue
                
                filtered_gaps.append(gap)
                
            except (ValueError, TypeError):
                continue
        
        # Sort by timestamp (newest first)
        filtered_gaps.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Apply limit
        result_gaps = filtered_gaps[:limit]
        
        return {
            "status": "success",
            "data": {
                "gaps": result_gaps,
                "total_found": len(filtered_gaps),
                "returned": len(result_gaps),
                "time_range": {
                    "start_time": start_time,
                    "end_time": end_time,
                    "limit": limit
                },
                "timestamp": datetime.now().isoformat()
            },
            "message": f"Found {len(result_gaps)} gaps in specified time range"
        }
    except Exception as e:
        logger.error(f"Error getting gaps by time range: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health", summary="Gap Analysis Service Health Check")
async def get_gap_analysis_health() -> Dict[str, Any]:
    """
    Get gap analysis service health status and performance metrics
    
    Uses ONLY the enhanced service (numpy/pandas optimized)
    """
    try:
        health_data = health_check()
        return {
            "status": "success",
            "data": health_data,
            "service": "enhanced",
            "message": "Gap analysis service health check completed"
        }
    except Exception as e:
        logger.error(f"Error getting gap analysis health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trigger-analysis", summary="Manually Trigger Gap Analysis")
async def trigger_gap_analysis() -> Dict[str, Any]:
    """
    Manually trigger gap analysis refresh (for testing/debugging)
    """
    try:
        if not enhanced_gap_detection.is_running:
            raise HTTPException(status_code=503, detail="Enhanced gap detection service is not running")
        
        # Force a data refresh - trigger morning capture if within window
        if enhanced_gap_detection.is_morning_capture_active:
            await enhanced_gap_detection._capture_all_instruments()
        
        current_stats = get_gap_data()
        
        return {
            "status": "success",
            "data": {
                "message": "Enhanced gap analysis refresh triggered",
                "current_statistics": current_stats.get("statistics", {}),
                "timestamp": datetime.now().isoformat()
            },
            "message": "Enhanced gap analysis refresh completed successfully"
        }
    except Exception as e:
        logger.error(f"Error triggering gap analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Export router
__all__ = ["router"]