from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List
from datetime import datetime
import logging
import os
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import desc

from services.centralized_ws_manager import get_centralized_manager
from services.market_schedule_service import get_market_scheduler
from services.system_check_service import system_check_service
from database.connection import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/system", tags=["system"])

@router.get("/status")
async def get_system_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get comprehensive system status using parallelized checks for performance.
    """
    try:
        # Run ALL checks in parallel to minimize total response time
        # This includes sync calls moved to threads and async calls gathered
        (
            db_status,
            redis_status,
            resource_status,
            stock_selection_status,
            token_status,
            daily_tasks,
            ws_status,
            instrument_status,
            live_feed_status,
            strategy_status,
            scheduler_status,
            automation_status,
            trade_prep_status,
            capital_status,
            analytics_status,
            option_status
        ) = await asyncio.gather(
            asyncio.to_thread(system_check_service.check_database, db),
            asyncio.to_thread(system_check_service.check_redis),
            asyncio.to_thread(system_check_service.check_system_resources),
            system_check_service.check_stock_selection_status(),
            system_check_service.check_token_status(),
            system_check_service.check_daily_tasks(db),
            asyncio.to_thread(lambda: get_centralized_manager().get_auto_trading_status() if get_centralized_manager() else {"error": "Not initialized"}),
            asyncio.to_thread(system_check_service.check_instrument_status),
            asyncio.to_thread(system_check_service.check_live_feed_status),
            asyncio.to_thread(system_check_service.check_strategy_status),
            asyncio.to_thread(system_check_service.check_scheduler_status),
            asyncio.to_thread(system_check_service.check_automation_status),
            asyncio.to_thread(system_check_service.check_trade_prep_status),
            asyncio.to_thread(system_check_service.check_capital_manager_status),
            asyncio.to_thread(system_check_service.check_realtime_analytics_status),
            asyncio.to_thread(system_check_service.check_option_service_status)
        )
        
        # Aggregate Errors for dashboard
        errors = []
        for check_name, status in [
            ("database", db_status), 
            ("redis", redis_status), 
            ("stock_selection", stock_selection_status), 
            ("tokens", token_status),
            ("instruments", instrument_status), 
            ("live_feed", live_feed_status),
            ("strategy", strategy_status), 
            ("scheduler", scheduler_status),
            ("automation", automation_status), 
            ("trade_prep", trade_prep_status),
            ("capital_manager", capital_status),
            ("analytics", analytics_status), 
            ("options", option_status),
            ("daily_tasks", daily_tasks)
        ]:
            if isinstance(status, dict) and status.get("status") in ["error", "failed"]:
                errors.append({"component": check_name, "error": status.get("error") or status.get("message")})

        # Determine overall health
        overall_health = "healthy"
        if errors:
            overall_health = "degraded"
        if db_status.get("status") == "error":
            overall_health = "unhealthy"

        automation_enabled = bool(os.getenv("UPSTOX_MOBILE") and os.getenv("UPSTOX_PIN"))

        return {
            "timestamp": datetime.now().isoformat(),
            "environment": os.getenv("ENVIRONMENT", "development"),
            "health_status": overall_health,
            "health": {
                "websocket": "connected" if ws_status.get("websocket_connected") else "disconnected",
                "automation": "enabled" if automation_enabled else "disabled",
                "scheduler": "running" if scheduler_status.get("is_running") else "stopped",
                "database": db_status.get("status", "unknown"),
                "redis": redis_status.get("status", "unknown")
            },
            "business_logic": {
                "stock_selection": stock_selection_status,
                "market_schedule": scheduler_status,
                "token_status": token_status,
                "automation": automation_status,
                "trade_prep": trade_prep_status,
                "capital_manager": capital_status,
                "option_service": option_status,
                "daily_tasks": daily_tasks,
            },
            "live_operations": {
                "feed_status": live_feed_status,
                "instrument_service": instrument_status,
                "strategy_status": strategy_status,
                "analytics_engine": analytics_status,
                "websocket_manager": ws_status,
            },
            "infrastructure": {
                "database": db_status,
                "redis": redis_status,
                "resources": resource_status,
            },
            "errors": errors
        }
    except Exception as e:
        logger.error(f"System status error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
