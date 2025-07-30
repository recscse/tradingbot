# router/market_analytics_router.py - SIMPLIFIED FIXED VERSION
import asyncio
import logging
import json
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Query, HTTPException, WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)

# Simple flags - no complex imports
INSTRUMENT_REGISTRY_AVAILABLE = True
ANALYTICS_SERVICE_AVAILABLE = True

# Create router first
router = APIRouter()


# Simple analytics service that loads dependencies lazily
class SimpleAnalyticsService:
    def __init__(self):
        self._enhanced_analytics = None
        self._registry = None

    def _get_enhanced_analytics(self):
        """Lazy load enhanced analytics"""
        if self._enhanced_analytics is None:
            try:
                from services.enhanced_market_analytics import enhanced_analytics

                self._enhanced_analytics = enhanced_analytics
                return self._enhanced_analytics
            except ImportError as e:
                logger.warning(f"Enhanced analytics not available: {e}")
                return None
        return self._enhanced_analytics

    def _get_registry(self):
        """Lazy load registry"""
        if self._registry is None:
            try:
                from services.instrument_registry import instrument_registry

                self._registry = instrument_registry
                return self._registry
            except ImportError as e:
                logger.warning(f"Registry not available: {e}")
                return None
        return self._registry

    def get_top_gainers_losers(self, limit=20):
        """Get top gainers and losers"""
        analytics = self._get_enhanced_analytics()
        if analytics:
            try:
                return analytics.get_top_gainers_losers(limit)
            except Exception as e:
                logger.error(f"Error getting top movers: {e}")

        return {"gainers": [], "losers": [], "summary": {}}

    def get_volume_analysis(self, limit=20):
        """Get volume analysis"""
        analytics = self._get_enhanced_analytics()
        if analytics:
            try:
                return analytics.get_volume_analysis(limit)
            except Exception as e:
                logger.error(f"Error getting volume analysis: {e}")

        return {"volume_leaders": [], "unusual_volume": [], "volume_momentum": []}

    def get_market_sentiment(self):
        """Get market sentiment"""
        analytics = self._get_enhanced_analytics()
        if analytics:
            try:
                return analytics.get_market_sentiment()
            except Exception as e:
                logger.error(f"Error getting market sentiment: {e}")

        return {"sentiment": "unknown", "confidence": 0, "metrics": {}}

    def get_gap_analysis(self):
        """Get gap analysis"""
        analytics = self._get_enhanced_analytics()
        if analytics:
            try:
                return analytics.get_gap_analysis()
            except Exception as e:
                logger.error(f"Error getting gap analysis: {e}")

        return {"gap_up": [], "gap_down": [], "summary": {}}

    def get_breakout_analysis(self):
        """Get breakout analysis"""
        analytics = self._get_enhanced_analytics()
        if analytics:
            try:
                return analytics.get_breakout_analysis()
            except Exception as e:
                logger.error(f"Error getting breakout analysis: {e}")

        return {"breakouts": [], "breakdowns": [], "summary": {}}

    def get_intraday_stocks(self):
        """Get intraday stocks"""
        analytics = self._get_enhanced_analytics()
        if analytics:
            try:
                return analytics.get_intraday_stocks()
            except Exception as e:
                logger.error(f"Error getting intraday stocks: {e}")

        return {"low_risk": [], "medium_risk": [], "high_risk": [], "summary": {}}

    def get_record_movers(self):
        """Get record movers"""
        analytics = self._get_enhanced_analytics()
        if analytics:
            try:
                return analytics.get_record_movers()
            except Exception as e:
                logger.error(f"Error getting record movers: {e}")

        return {"new_highs": [], "new_lows": [], "summary": {}}

    def generate_sector_heatmap(
        self, size_metric="market_cap", color_metric="change_percent"
    ):
        """Generate sector heatmap"""
        analytics = self._get_enhanced_analytics()
        if analytics:
            try:
                return analytics.generate_sector_heatmap(size_metric, color_metric)
            except Exception as e:
                logger.error(f"Error generating sector heatmap: {e}")

        return {"heatmap": {"sectors": []}, "metadata": {}}

    def get_complete_analytics(self):
        """Get all analytics data"""
        analytics = self._get_enhanced_analytics()
        if analytics:
            try:
                return analytics.get_complete_analytics()
            except Exception as e:
                logger.error(f"Error getting complete analytics: {e}")

        return {
            "top_movers": {"gainers": [], "losers": []},
            "gap_analysis": {"gap_up": [], "gap_down": []},
            "breakout_analysis": {"breakouts": [], "breakdowns": []},
            "market_sentiment": {"sentiment": "unknown", "confidence": 0},
            "sector_heatmap": {"heatmap": {"sectors": []}},
            "volume_analysis": {
                "volume_leaders": [],
                "unusual_volume": [],
                "volume_momentum": [],
            },
            "intraday_stocks": {"low_risk": [], "medium_risk": [], "high_risk": []},
            "record_movers": {"new_highs": [], "new_lows": []},
            "error": "Analytics service not fully available",
        }


# Create service instance
analytics_service = SimpleAnalyticsService()


# Simple WebSocket manager
class SimpleAnalyticsManager:
    def __init__(self):
        self.active_connections = {}
        self._connection_lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        async with self._connection_lock:
            self.active_connections[client_id] = websocket
        logger.info(f"Analytics client connected: {client_id}")

    async def disconnect(self, client_id: str):
        async with self._connection_lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
        logger.info(f"Analytics client disconnected: {client_id}")

    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_text(json.dumps(message))
                return True
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                await self.disconnect(client_id)
        return False


# Create manager instance
analytics_manager = SimpleAnalyticsManager()

# ===== REST API ENDPOINTS =====


@router.get("/top-movers")
async def get_top_movers(limit: int = Query(20, ge=5, le=50)):
    """Get top gainers and losers"""
    try:
        result = analytics_service.get_top_gainers_losers(limit)
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in top movers endpoint: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {"gainers": [], "losers": []},
        }


@router.get("/volume-analysis")
async def get_volume_analysis(limit: int = Query(20, ge=5, le=50)):
    """Get volume analysis"""
    try:
        result = analytics_service.get_volume_analysis(limit)
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in volume analysis endpoint: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {"volume_leaders": []},
        }


@router.get("/market-sentiment")
async def get_market_sentiment():
    """Get market sentiment"""
    try:
        result = analytics_service.get_market_sentiment()
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in market sentiment endpoint: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {"sentiment": "unknown"},
        }


@router.get("/gap-analysis")
async def get_gap_analysis():
    """Get gap up/down analysis"""
    try:
        result = analytics_service.get_gap_analysis()
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in gap analysis endpoint: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {"gap_up": [], "gap_down": []},
        }


@router.get("/breakout-analysis")
async def get_breakout_analysis():
    """Get breakout/breakdown analysis"""
    try:
        result = analytics_service.get_breakout_analysis()
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in breakout analysis endpoint: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {"breakouts": [], "breakdowns": []},
        }


@router.get("/intraday-stocks")
async def get_intraday_stocks():
    """Get intraday trading stocks"""
    try:
        result = analytics_service.get_intraday_stocks()
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in intraday stocks endpoint: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {"low_risk": [], "medium_risk": [], "high_risk": []},
        }


@router.get("/record-movers")
async def get_record_movers():
    """Get record movers (new highs/lows)"""
    try:
        result = analytics_service.get_record_movers()
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in record movers endpoint: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {"new_highs": [], "new_lows": []},
        }


@router.get("/sector-heatmap")
async def get_sector_heatmap(
    size_metric: str = Query("market_cap", description="Metric for cell size"),
    color_metric: str = Query("change_percent", description="Metric for cell color"),
):
    """Get sector heatmap"""
    try:
        result = analytics_service.generate_sector_heatmap(size_metric, color_metric)
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in sector heatmap endpoint: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {"heatmap": {"sectors": []}},
        }


@router.get("/complete")
async def get_complete_analytics():
    """Get all analytics data in one call"""
    try:
        result = analytics_service.get_complete_analytics()
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in complete analytics endpoint: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {
                "top_movers": {"gainers": [], "losers": []},
                "gap_analysis": {"gap_up": [], "gap_down": []},
                "breakout_analysis": {"breakouts": [], "breakdowns": []},
                "market_sentiment": {"sentiment": "unknown", "confidence": 0},
                "sector_heatmap": {"heatmap": {"sectors": []}},
                "volume_analysis": {
                    "volume_leaders": [],
                    "unusual_volume": [],
                    "volume_momentum": [],
                },
                "intraday_stocks": {"low_risk": [], "medium_risk": [], "high_risk": []},
                "record_movers": {"new_highs": [], "new_lows": []},
            },
        }


@router.get("/status")
async def get_analytics_status():
    """Get analytics system status"""
    return {
        "success": True,
        "status": "running",
        "analytics_available": ANALYTICS_SERVICE_AVAILABLE,
        "registry_available": INSTRUMENT_REGISTRY_AVAILABLE,
        "active_connections": len(analytics_manager.active_connections),
        "timestamp": datetime.now().isoformat(),
    }


# ===== WEBSOCKET ENDPOINT =====


@router.websocket("/ws/market-analytics")
async def websocket_market_analytics(websocket: WebSocket):
    """WebSocket endpoint for real-time market analytics"""
    client_id = f"analytics_{datetime.now().timestamp()}"

    try:
        await analytics_manager.connect(websocket, client_id)

        # Send initial data
        initial_data = {
            "type": "initial_data",
            "data": analytics_service.get_complete_analytics(),
            "timestamp": datetime.now().isoformat(),
        }
        await analytics_manager.send_personal_message(initial_data, client_id)

        # Handle messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                message_type = message.get("type", "unknown")

                if message_type == "get_complete":
                    result = analytics_service.get_complete_analytics()
                    await analytics_manager.send_personal_message(
                        {
                            "type": "complete_data",
                            "data": result,
                            "timestamp": datetime.now().isoformat(),
                        },
                        client_id,
                    )

                elif message_type == "ping":
                    await analytics_manager.send_personal_message(
                        {
                            "type": "pong",
                            "timestamp": datetime.now().isoformat(),
                        },
                        client_id,
                    )

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error for {client_id}: {e}")
                break

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        await analytics_manager.disconnect(client_id)
