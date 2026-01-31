import logging
import os
import psutil
import redis
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text

# Import Service Singletons/Getters
try:
    from services.intelligent_stock_selection_service import intelligent_stock_selector
    from services.token_monitor_service import token_monitor_service
    from services.instrument_refresh_service import get_trading_service
    from services.market_schedule_service import get_market_scheduler
    from services.centralized_ws_manager import get_centralized_manager
    from services.trading_execution.auto_trade_scheduler import auto_trade_scheduler
    from services.upstox_automation_service import get_automation_status
    # Try to import auto trading coordinator if available globally or via scheduler
    # Note: AutoTradingCoordinator might be accessed via MarketScheduleService
except ImportError as e:
    logging.getLogger(__name__).warning(f"Failed to import some services: {e}")

logger = logging.getLogger(__name__)

class SystemCheckService:
    def check_database(self, db: Session) -> Dict[str, Any]:
        """Check database connectivity and latency"""
        try:
            start_time = datetime.now()
            db.execute(text("SELECT 1"))
            latency = (datetime.now() - start_time).total_seconds() * 1000
            return {"status": "connected", "latency_ms": round(latency, 2)}
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and latency"""
        if os.getenv("REDIS_ENABLED", "true").lower() != "true":
            return {"status": "disabled"}
        
        try:
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", 6379))
            db_num = int(os.getenv("REDIS_DB", 0))
            password = os.getenv("REDIS_PASSWORD")
            
            # Short timeout for health check
            client = redis.Redis(
                host=host, 
                port=port, 
                db=db_num, 
                password=password, 
                socket_connect_timeout=2,
                socket_timeout=2
            )
            
            start_time = datetime.now()
            client.ping()
            latency = (datetime.now() - start_time).total_seconds() * 1000
            client.close()
            return {"status": "connected", "latency_ms": round(latency, 2)}
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_system_resources(self) -> Dict[str, Any]:
        """Check CPU, Memory, and Disk usage"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=None) # Non-blocking
            
            # Memory
            memory = psutil.virtual_memory()
            
            # Disk
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_mb": round(memory.total / (1024 * 1024), 2),
                    "available_mb": round(memory.available / (1024 * 1024), 2),
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024 * 1024 * 1024), 2),
                    "free_gb": round(disk.free / (1024 * 1024 * 1024), 2),
                    "percent": disk.percent
                }
            }
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_broker_tokens(self) -> Dict[str, Any]:
        """Check if broker tokens are present in environment/config"""
        # Basic check for Upstox
        upstox_access = bool(os.getenv("UPSTOX_ACCESS_TOKEN"))
        upstox_refresh = bool(os.getenv("UPSTOX_REFRESH_TOKEN"))
        
        return {
            "upstox": {
                "access_token_present": upstox_access,
                "refresh_token_present": upstox_refresh
            }
        }

    def check_automation_status(self) -> Dict[str, Any]:
        """Check status of Upstox automation service"""
        try:
            status = get_automation_status()
            
            # Format for dashboard
            result = {
                "status": "healthy" if status.get("success") else "error" if status.get("error") else "unknown",
                "last_run": status.get("timestamp"),
                "message": status.get("message"),
                "error": status.get("error")
            }
            
            return result
        except Exception as e:
            logger.error(f"Automation status check failed: {e}")
            return {"status": "error", "error": str(e)}

    async def check_stock_selection_status(self) -> Dict[str, Any]:
        """Check intelligent stock selection status"""
        try:
            status = intelligent_stock_selector.get_selection_status()
            
            # Enhance with simplified status summary
            summary = {
                "status": "complete" if status.get("final_selection_done") else "pending",
                "phase": status.get("current_phase"),
                "selected_count": status.get("final_selections") if status.get("final_selection_done") else status.get("premarket_selections"),
                "sentiment": status.get("market_open_sentiment") if status.get("market_open_sentiment") != "neutral" else status.get("premarket_sentiment"),
                "last_run": status.get("last_selection_time"),
                "ready_for_trading": status.get("final_selection_done") and status.get("final_selections", 0) > 0,
                "last_error": status.get("last_error")  # Include detailed error if any
            }
            
            if status.get("last_error"):
                summary["status"] = "error"
                summary["error"] = status.get("last_error")
                
            return summary
        except Exception as e:
            logger.error(f"Stock selection check failed: {e}")
            return {"status": "error", "error": str(e)}

    async def check_token_status(self) -> Dict[str, Any]:
        """Check broker token expiry status"""
        try:
            summary = await token_monitor_service.get_expiring_tokens_summary()
            
            # Determine overall health
            overall_status = "healthy"
            if summary["expired"]:
                overall_status = "critical"
            elif summary["critical"]:
                overall_status = "warning"
                
            return {
                "status": overall_status,
                "expired_count": len(summary["expired"]),
                "critical_count": len(summary["critical"]),
                "active_tokens": len(summary["normal"]) + len(summary["high"]) + len(summary["reminder"]),
                "details": summary
            }
        except Exception as e:
            logger.error(f"Token status check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_instrument_status(self) -> Dict[str, Any]:
        """Check instrument service status"""
        try:
            service = get_trading_service()
            is_init = service.is_initialized()
            last_error = getattr(service, "last_error", None)
            
            # Access internal stats if possible, safely
            stats = {
                "initialized": is_init,
                "last_refresh": getattr(service, "_last_refresh", None),
                "total_instruments": 0,
                "last_error": last_error
            }
            
            if last_error:
                stats["status"] = "error"
                stats["error"] = last_error
            elif is_init:
                # Try to get counts if exposed or infer from private vars if python allows (it does)
                # But prefer public methods if available. 
                # service.initialize_service returns a result, but we don't store it publicly in the service instance easily accessible here
                # We can check the length of keys loaded
                nse_keys = getattr(service, "_websocket_keys", [])
                stats["total_instruments"] = len(nse_keys)
                
            return stats
        except Exception as e:
            logger.error(f"Instrument check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_scheduler_status(self) -> Dict[str, Any]:
        """Check market scheduler status"""
        try:
            scheduler = get_market_scheduler()
            status = scheduler.get_status()
            
            # Check for task errors
            if status.get("task_errors"):
                status["status"] = "warning"
                # If critical tasks failed, escalate to error
                if "fno_update" in status["task_errors"] or "preopen_selection" in status["task_errors"]:
                    status["status"] = "error"
                    status["error"] = "Critical market tasks failed"
            
            return status
        except Exception as e:
            logger.error(f"Scheduler check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_live_feed_status(self) -> Dict[str, Any]:
        """Check live feed connection and subscription"""
        try:
            # Check centralized manager
            manager = get_centralized_manager()
            manager_status = manager.get_auto_trading_status() if manager else {}
            
            # Check auto trade live feed service
            try:
                from services.trading_execution.auto_trade_live_feed import auto_trade_live_feed
                feed_status = auto_trade_live_feed.get_status()
            except (ImportError, AttributeError):
                feed_status = {"status": "unknown", "message": "AutoTradeLiveFeed instance not found"}

            return {
                "connected": manager_status.get("websocket_connected", False),
                "subscribed_count": manager_status.get("subscribed_instrument_count", 0),
                "connection_uptime": manager_status.get("uptime_seconds", 0),
                "last_data_time": manager_status.get("last_data_received_time"),
                "mode": "admin_feed",
                "feed_service": feed_status,
                "last_error": manager_status.get("last_error") or feed_status.get("last_error")
            }
        except Exception as e:
            logger.error(f"Live feed check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_trade_prep_status(self) -> Dict[str, Any]:
        """Check trade preparation service status"""
        try:
            from services.trading_execution.trade_prep import trade_prep_service
            return trade_prep_service.get_status()
        except Exception as e:
            logger.error(f"Trade prep check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_realtime_analytics_status(self) -> Dict[str, Any]:
        """Check real-time market analytics engine status"""
        try:
            from services.realtime_market_engine import get_analytics_status
            return get_analytics_status()
        except Exception as e:
            logger.error(f"Real-time analytics check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_option_service_status(self) -> Dict[str, Any]:
        """Check status of Upstox option service"""
        try:
            from services.upstox_option_service import upstox_option_service
            return upstox_option_service.get_status()
        except Exception as e:
            logger.error(f"Option service check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_strategy_status(self) -> Dict[str, Any]:
        """Check strategy execution status via Scheduler"""
        try:
            scheduler = get_market_scheduler()
            # Try to access auto_trading_coordinator if it exists on scheduler
            coordinator = getattr(scheduler, "auto_trading_coordinator", None)
            
            status = {
                "status": "inactive",
                "message": "Coordinator not initialized in scheduler",
                "sessions_active": getattr(scheduler, "trading_sessions_active", False),
                "system_state": "STOPPED"
            }
            
            if coordinator:
                status = coordinator.get_system_status()
                # Ensure status string is consistent
                status["status"] = "active" if status.get("is_running") else "inactive"
                
                # Check for critical errors
                if status.get("system_health", {}).get("error_count_24h", 0) > 0:
                    status["status"] = "warning"
                    status["message"] = f"Errors detected: {status['system_health']['error_count_24h']}"
                if status.get("emergency_stop_active"):
                    status["status"] = "critical"
                    status["error"] = "Emergency Stop Active"
            
            # Check auto trade scheduler for top-level errors
            if hasattr(auto_trade_scheduler, "last_error") and auto_trade_scheduler.last_error:
                status["auto_trade_scheduler_error"] = auto_trade_scheduler.last_error
                status["status"] = "error"
                status["error"] = f"Scheduler Error: {auto_trade_scheduler.last_error}"
                
            return status
            
        except Exception as e:
            logger.error(f"Strategy check failed: {e}")
            return {"status": "error", "error": str(e)}

# Singleton instance
system_check_service = SystemCheckService()
