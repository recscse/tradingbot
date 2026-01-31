# router/market_analytics_router.py - SIMPLIFIED FIXED VERSION
import asyncio
import logging
import json
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Query, HTTPException, WebSocket, WebSocketDisconnect
from datetime import datetime

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
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

    def _get_optimized_service(self):
        """Lazy load optimized market data service"""
        if self._enhanced_analytics is None:
            try:
                from services.optimized_market_data_service import (
                    optimized_market_service,
                )

                self._enhanced_analytics = optimized_market_service
                return self._enhanced_analytics
            except ImportError as e:
                logger.warning(f"Optimized market service not available: {e}")
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
        service = self._get_optimized_service()
        if service:
            try:
                gainers = service.get_top_gainers(limit)
                losers = service.get_top_losers(limit)
                return {
                    "gainers": gainers,
                    "losers": losers,
                    "analysis": {
                        "avg_gainer_change": (
                            sum(g.get("change_percent", 0) for g in gainers)
                            / len(gainers)
                            if gainers
                            else 0
                        ),
                        "avg_loser_change": (
                            sum(l.get("change_percent", 0) for l in losers)
                            / len(losers)
                            if losers
                            else 0
                        ),
                        "total_analyzed": len(gainers) + len(losers),
                    },
                }
            except Exception as e:
                logger.error(f"Error getting top movers: {e}")

        return {"gainers": [], "losers": [], "summary": {}}

    def get_volume_analysis(self, limit=20):
        """Get volume analysis"""
        service = self._get_optimized_service()
        if service:
            try:
                volume_leaders = service.get_volume_leaders(limit)
                return {
                    "volume_leaders": volume_leaders,
                    "unusual_volume": [],  # Can be implemented later
                    "volume_momentum": [],  # Can be implemented later
                }
            except Exception as e:
                logger.error(f"Error getting volume analysis: {e}")

        return {"volume_leaders": [], "unusual_volume": [], "volume_momentum": []}

    def get_market_sentiment(self):
        """Get market sentiment"""
        service = self._get_optimized_service()
        if service:
            try:
                return service.get_market_sentiment()
            except Exception as e:
                logger.error(f"Error getting market sentiment: {e}")

        return {"sentiment": "unknown", "confidence": 0, "metrics": {}}

    async def get_gap_analysis(self):
        """Get gap analysis from gap detection service"""
        try:
            # Import gap detection service function
            from services.gapdetection_service import get_todays_gap_analysis

            # Get today's gaps (both up and down)
            all_gaps = await get_todays_gap_analysis(limit=50)

            # Separate gap up and gap down
            gap_up = []
            gap_down = []

            for gap in all_gaps:
                gap_data = {
                    "symbol": gap["symbol"],
                    "gap_percentage": gap["gap_percentage"],
                    "gap_strength": gap["gap_strength"],
                    "open_price": gap["open_price"],
                    "close_price": gap.get("current_price", gap["open_price"]),
                    "previous_close": gap["previous_close"],
                    "volume": gap["volume"],
                    "sector": gap["sector"],
                    "market_cap": gap.get("market_cap", "UNKNOWN"),
                    "timestamp": gap["timestamp"],
                    "last_price": gap.get("current_price", gap["open_price"]),
                    "change_percent": gap["gap_percentage"],
                }

                if gap["gap_percentage"] > 0:
                    gap_up.append(gap_data)
                else:
                    gap_down.append(gap_data)

            # Create summary
            summary = {
                "total_gaps": len(all_gaps),
                "gap_up_count": len(gap_up),
                "gap_down_count": len(gap_down),
                "data_source": "gap_detection_service",
                "analysis_time": "9:08 AM IST",
            }

            return {"gap_up": gap_up, "gap_down": gap_down, "summary": summary}

        except Exception as e:
            logger.error(f"Error getting gap analysis: {e}")
            return {"gap_up": [], "gap_down": [], "summary": {}}

    def get_breakout_analysis(self):
        """Get breakout analysis"""
        service = self._get_optimized_service()
        if service:
            try:
                # Get new highs and lows as proxies for breakouts/breakdowns
                new_highs = service.get_new_highs(20)
                new_lows = service.get_new_lows(20)

                return {
                    "breakouts": new_highs,  # Stocks near day high can be considered breakouts
                    "breakdowns": new_lows,  # Stocks near day low can be considered breakdowns
                    "summary": {
                        "total_breakouts": len(new_highs),
                        "total_breakdowns": len(new_lows),
                        "market_momentum": (
                            "bullish"
                            if len(new_highs) > len(new_lows)
                            else (
                                "bearish"
                                if len(new_lows) > len(new_highs)
                                else "neutral"
                            )
                        ),
                    },
                }
            except Exception as e:
                logger.error(f"Error getting breakout analysis: {e}")

        return {"breakouts": [], "breakdowns": [], "summary": {}}

    def get_intraday_stocks(self):
        """Get intraday stocks"""
        service = self._get_optimized_service()
        if service:
            try:
                # Get biggest movers and volume leaders for intraday trading
                biggest_movers = service.get_biggest_movers(30)
                volume_leaders = service.get_volume_leaders(30)

                # Categorize by risk based on volatility and volume
                low_risk = []
                medium_risk = []
                high_risk = []

                for stock in biggest_movers:
                    change_percent = abs(stock.get("change_percent", 0))
                    volume = stock.get("volume", 0)

                    if change_percent < 2 and volume > 50000:
                        low_risk.append(stock)
                    elif change_percent < 5 and volume > 25000:
                        medium_risk.append(stock)
                    elif change_percent >= 5 or volume > 100000:
                        high_risk.append(stock)

                return {
                    "low_risk": low_risk[:10],
                    "medium_risk": medium_risk[:10],
                    "high_risk": high_risk[:10],
                    "summary": {
                        "total_analyzed": len(biggest_movers),
                        "low_risk_count": len(low_risk),
                        "medium_risk_count": len(medium_risk),
                        "high_risk_count": len(high_risk),
                    },
                }
            except Exception as e:
                logger.error(f"Error getting intraday stocks: {e}")

        return {"low_risk": [], "medium_risk": [], "high_risk": [], "summary": {}}

    def get_record_movers(self):
        """Get record movers"""
        service = self._get_optimized_service()
        if service:
            try:
                new_highs = service.get_new_highs(20)
                new_lows = service.get_new_lows(20)

                return {
                    "new_highs": new_highs,
                    "new_lows": new_lows,
                    "summary": {
                        "new_highs_count": len(new_highs),
                        "new_lows_count": len(new_lows),
                        "high_low_ratio": (
                            len(new_highs) / len(new_lows) if new_lows else float("inf")
                        ),
                    },
                }
            except Exception as e:
                logger.error(f"Error getting record movers: {e}")

        return {"new_highs": [], "new_lows": [], "summary": {}}

    def generate_sector_heatmap(
        self, size_metric="market_cap", color_metric="change_percent"
    ):
        """Generate sector heatmap"""
        service = self._get_optimized_service()
        if service:
            try:
                sector_performance = service.get_sector_performance()

                sectors = []
                for sector_name, data in sector_performance.items():
                    if data["total_stocks"] > 0:
                        sectors.append(
                            {
                                "sector": sector_name,
                                "avg_change_percent": data["avg_change_percent"],
                                "advancing": data["advancing"],
                                "declining": data["declining"],
                                "total_stocks": data["total_stocks"],
                                "strength_score": data["strength_score"],
                            }
                        )

                return {
                    "heatmap": {"sectors": sectors},
                    "metadata": {
                        "size_metric": size_metric,
                        "color_metric": color_metric,
                        "total_sectors": len(sectors),
                    },
                }
            except Exception as e:
                logger.error(f"Error generating sector heatmap: {e}")

        return {"heatmap": {"sectors": []}, "metadata": {}}

    async def get_complete_analytics(self):
        """Get all analytics data"""
        service = self._get_optimized_service()
        if service:
            try:
                # Use optimized service methods directly for better performance
                return {
                    "top_movers": self.get_top_gainers_losers(),
                    "volume_analysis": self.get_volume_analysis(),
                    "market_sentiment": self.get_market_sentiment(),
                    "gap_analysis": await self.get_gap_analysis(),
                    "breakout_analysis": self.get_breakout_analysis(),
                    "intraday_stocks": self.get_intraday_stocks(),
                    "record_movers": self.get_record_movers(),
                    "sector_heatmap": self.generate_sector_heatmap(),
                    "market_breadth": service.get_advance_decline_analysis(),
                    "generated_at": datetime.now().isoformat(),
                    "data_source": "optimized_market_service",
                }
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
        self._locks = {}

    def _get_lock(self):
        loop = asyncio.get_running_loop()
        if loop not in self._locks:
            self._locks[loop] = asyncio.Lock()
        return self._locks[loop]

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        async with self._get_lock():
            self.active_connections[client_id] = websocket
        logger.info(f"Analytics client connected: {client_id}")

    async def disconnect(self, client_id: str):
        async with self._get_lock():
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
        result = await analytics_service.get_gap_analysis()
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
        result = await analytics_service.get_complete_analytics()
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
            "data": await analytics_service.get_complete_analytics(),
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
                    result = await analytics_service.get_complete_analytics()
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
