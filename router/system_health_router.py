from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List
from datetime import datetime
import logging
import os
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
    # ... (existing code remains same)
    try:
        # 1. WebSocket Status
        ws_manager = get_centralized_manager()
        # ... rest of the function ...
        ws_status = ws_manager.get_auto_trading_status() if ws_manager else {"error": "Manager not initialized"}

        # 2. Market Schedule Status
        market_scheduler = get_market_scheduler()
        scheduler_status = market_scheduler.get_status() if market_scheduler else {"error": "Scheduler not initialized"}

        # 3. Token Automation Status (Basic check)
        automation_enabled = bool(os.getenv("UPSTOX_MOBILE") and os.getenv("UPSTOX_PIN"))
        
        # 4. Infrastructure Checks
        db_status = system_check_service.check_database(db)
        redis_status = system_check_service.check_redis()
        resource_status = system_check_service.check_system_resources()
        
        # 5. Business Logic & Live Operations Checks
        stock_selection_status = await system_check_service.check_stock_selection_status()
        token_status = await system_check_service.check_token_status()
        instrument_status = system_check_service.check_instrument_status()
        live_feed_status = system_check_service.check_live_feed_status()
        strategy_status = system_check_service.check_strategy_status()
        automation_status = system_check_service.check_automation_status()
        trade_prep_status = system_check_service.check_trade_prep_status()
        capital_status = system_check_service.check_capital_manager_status()
        analytics_status = system_check_service.check_realtime_analytics_status()
        option_status = system_check_service.check_option_service_status()
        
        # Aggregate Errors
        errors = []
        for check_name, status in [
            ("database", db_status), ("redis", redis_status), 
            ("stock_selection", stock_selection_status), ("tokens", token_status),
            ("instruments", instrument_status), ("live_feed", live_feed_status),
            ("strategy", strategy_status), ("scheduler", scheduler_status),
            ("automation", automation_status), ("trade_prep", trade_prep_status),
            ("capital_manager", capital_status),
            ("analytics", analytics_status), ("options", option_status)
        ]:
            if isinstance(status, dict):
                # Standard error status
                if status.get("status") == "error":
                    errors.append({"component": check_name, "error": status.get("error")})
                
                # Check for nested task errors (Scheduler)
                if check_name == "scheduler" and status.get("task_errors"):
                    for task, err in status["task_errors"].items():
                        errors.append({"component": f"scheduler:{task}", "error": err})

                # Check for function-level health errors
                if status.get("function_health"):
                    for func, health in status["function_health"].items():
                        if health.get("status") == "error" or health.get("error"):
                            errors.append({
                                "component": f"{check_name}:{func}", 
                                "error": health.get("error") or f"Function {func} failed",
                                "last_run": health.get("last_run")
                            })

                # Check for service-specific errors (Live Feed)
                if status.get("service_errors"):
                    for svc, err_info in status["service_errors"].items():
                        if err_info:
                            errors.append({
                                "component": f"{check_name}:{svc}", 
                                "error": err_info.get("error"),
                                "timestamp": err_info.get("timestamp")
                            })

                # Check for auto-trade scheduler errors (Strategy)
                if check_name == "strategy" and status.get("auto_trade_scheduler_error"):
                    errors.append({"component": "auto_trade_scheduler", "error": status["auto_trade_scheduler_error"]})
                
                # Check for last_error in other components
                if status.get("last_error") and status.get("status") != "error":
                     errors.append({"component": f"{check_name}:last_error", "error": status["last_error"]})

        # Determine overall health
        overall_health = "healthy"
        if errors:
            overall_health = "degraded"
        if db_status.get("status") == "error" or (live_feed_status.get("status") == "error" and live_feed_status.get("is_running")):
            overall_health = "unhealthy"

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
            },
            "live_operations": {
                "feed_status": live_feed_status,
                "instrument_service": instrument_status,
                "strategy_status": strategy_status,
                "analytics_engine": analytics_status,
                "websocket_manager": ws_status, # Legacy support
            },
            "infrastructure": {
                "database": db_status,
                "redis": redis_status,
                "resources": resource_status,
                "automation_config": { # Legacy support
                    "enabled": automation_enabled,
                    "headless": os.getenv("UPSTOX_HEADLESS", "true").lower() == "true",
                }
            },
            "errors": errors
        }
    except Exception as e:
        logger.error(f"System status error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
