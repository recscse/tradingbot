import logging
import os
import psutil
import redis
import asyncio
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
    def __init__(self):
        self._cache = {}
        self._cache_timeout = 30  # Increased to 30 seconds for general checks

    def _get_from_cache(self, key: str, custom_timeout: int = None):
        if key in self._cache:
            data, timestamp = self._cache[key]
            timeout = custom_timeout if custom_timeout is not None else self._cache_timeout
            if (datetime.now() - timestamp).total_seconds() < timeout:
                return data
        return None

    def _save_to_cache(self, key: str, data: Any):
        self._cache[key] = (data, datetime.now())

    def check_database(self, db: Session = None) -> Dict[str, Any]:
        """Check database connectivity and latency"""
        cached = self._get_from_cache("database")
        if cached: return cached
        
        # Use provided session or create a temporary one for the health check
        session = db
        temp_session = False
        
        if session is None:
            try:
                from database.connection import SessionLocal
                session = SessionLocal()
                temp_session = True
            except Exception as e:
                logger.error(f"Failed to create temp session for health check: {e}")
                return {"status": "error", "error": f"Session creation failed: {e}"}
        
        try:
            start_time = datetime.now()
            session.execute(text("SELECT 1"))
            latency = (datetime.now() - start_time).total_seconds() * 1000
            result = {"status": "connected", "latency_ms": round(latency, 2)}
            self._save_to_cache("database", result)
            return result
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            # Cache failure for longer to reduce load
            result = {"status": "error", "error": str(e)}
            self._save_to_cache("database", result)
            return result
        finally:
            if temp_session and session:
                session.close()

    def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and latency"""
        cached = self._get_from_cache("redis")
        if cached: return cached

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
                socket_connect_timeout=1,
                socket_timeout=1
            )
            
            start_time = datetime.now()
            client.ping()
            latency = (datetime.now() - start_time).total_seconds() * 1000
            client.close()
            result = {"status": "connected", "latency_ms": round(latency, 2)}
            self._save_to_cache("redis", result)
            return result
        except Exception as e:
            # logger.error(f"Redis health check failed: {e}")
            result = {"status": "error", "error": "Connection Timeout"}
            self._save_to_cache("redis", result)
            return result

    def check_system_resources(self) -> Dict[str, Any]:
        """Check CPU, Memory, and Disk usage"""
        cached = self._get_from_cache("resources", custom_timeout=60) # Resource check every 60s
        if cached: return cached

        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=None) # Non-blocking
            
            # Memory
            memory = psutil.virtual_memory()
            
            # Disk
            disk = psutil.disk_usage('/')
            
            result = {
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
            self._save_to_cache("resources", result)
            return result
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_broker_tokens(self) -> Dict[str, Any]:
        """Check if broker tokens are present in environment/config"""
        cached = self._get_from_cache("broker_tokens", custom_timeout=3600) # Token presence check every hour
        if cached: return cached

        # Basic check for Upstox
        upstox_access = bool(os.getenv("UPSTOX_ACCESS_TOKEN"))
        upstox_refresh = bool(os.getenv("UPSTOX_REFRESH_TOKEN"))
        
        result = {
            "upstox": {
                "access_token_present": upstox_access,
                "refresh_token_present": upstox_refresh
            }
        }
        self._save_to_cache("broker_tokens", result)
        return result

    def check_automation_status(self) -> Dict[str, Any]:
        """Check status of Upstox automation service"""
        cached = self._get_from_cache("automation")
        if cached: return cached

        try:
            status = get_automation_status()
            
            # Format for dashboard
            result = {
                "status": "healthy" if status.get("success") else "error" if status.get("error") else "unknown",
                "last_run": status.get("timestamp"),
                "message": status.get("message"),
                "error": status.get("error")
            }
            
            self._save_to_cache("automation", result)
            return result
        except Exception as e:
            logger.error(f"Automation status check failed: {e}")
            return {"status": "error", "error": str(e)}

    async def check_stock_selection_status(self) -> Dict[str, Any]:
        """Check intelligent stock selection status"""
        cached = self._get_from_cache("stock_selection", custom_timeout=300) # Selection check every 5m
        if cached: return cached

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
                
            self._save_to_cache("stock_selection", summary)
            return summary
        except Exception as e:
            logger.error(f"Stock selection check failed: {e}")
            return {"status": "error", "error": str(e)}

    async def check_token_status(self) -> Dict[str, Any]:
        """Check broker token expiry status"""
        cached = self._get_from_cache("token_status", custom_timeout=600) # Token expiry check every 10m
        if cached: return cached

        try:
            summary = await token_monitor_service.get_expiring_tokens_summary()
            
            # Determine overall health
            overall_status = "healthy"
            if summary["expired"]:
                overall_status = "critical"
            elif summary["critical"]:
                overall_status = "warning"
                
            result = {
                "status": overall_status,
                "expired_count": len(summary["expired"]),
                "critical_count": len(summary["critical"]),
                "active_tokens": len(summary["normal"]) + len(summary["high"]) + len(summary["reminder"]),
                "details": summary
            }
            self._save_to_cache("token_status", result)
            return result
        except Exception as e:
            logger.error(f"Token status check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_instrument_status(self) -> Dict[str, Any]:
        """Check instrument service status"""
        cached = self._get_from_cache("instrument_status", custom_timeout=300) # Instrument check every 5m
        if cached: return cached

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
                
            self._save_to_cache("instrument_status", stats)
            return stats
        except Exception as e:
            logger.error(f"Instrument check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_scheduler_status(self) -> Dict[str, Any]:
        """Check market scheduler status"""
        cached = self._get_from_cache("scheduler_status", custom_timeout=30)
        if cached: return cached

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
            
            self._save_to_cache("scheduler_status", status)
            return status
        except Exception as e:
            logger.error(f"Scheduler check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_live_feed_status(self) -> Dict[str, Any]:
        """Check live feed connection and subscription"""
        cached = self._get_from_cache("live_feed_status", custom_timeout=10) # Live feed check every 10s
        if cached: return cached

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

            result = {
                "connected": manager_status.get("websocket_connected", False),
                "subscribed_count": manager_status.get("subscribed_instrument_count", 0),
                "connection_uptime": manager_status.get("uptime_seconds", 0),
                "last_data_time": manager_status.get("last_data_received_time"),
                "mode": "admin_feed",
                "feed_service": feed_status,
                "last_error": manager_status.get("last_error") or feed_status.get("last_error")
            }
            self._save_to_cache("live_feed_status", result)
            return result
        except Exception as e:
            logger.error(f"Live feed check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_trade_prep_status(self) -> Dict[str, Any]:
        """Check trade preparation service status"""
        cached = self._get_from_cache("trade_prep_status")
        if cached: return cached

        try:
            from services.trading_execution.trade_prep import trade_prep_service
            result = trade_prep_service.get_status()
            self._save_to_cache("trade_prep_status", result)
            return result
        except Exception as e:
            logger.error(f"Trade prep check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_capital_manager_status(self) -> Dict[str, Any]:
        """Check capital manager service status"""
        cached = self._get_from_cache("capital_status")
        if cached: return cached

        try:
            from services.trading_execution.capital_manager import capital_manager
            result = capital_manager.get_status()
            self._save_to_cache("capital_status", result)
            return result
        except Exception as e:
            logger.error(f"Capital manager check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_realtime_analytics_status(self) -> Dict[str, Any]:
        """Check real-time market analytics engine status"""
        cached = self._get_from_cache("analytics_status", custom_timeout=30)
        if cached: return cached

        try:
            from services.realtime_market_engine import get_analytics_status
            result = get_analytics_status()
            self._save_to_cache("analytics_status", result)
            return result
        except Exception as e:
            logger.error(f"Real-time analytics check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_option_service_status(self) -> Dict[str, Any]:
        """Check status of Upstox option service"""
        cached = self._get_from_cache("option_status", custom_timeout=300) # Option service check every 5m
        if cached: return cached

        try:
            from services.upstox_option_service import upstox_option_service
            result = upstox_option_service.get_status()
            self._save_to_cache("option_status", result)
            return result
        except Exception as e:
            logger.error(f"Option service check failed: {e}")
            return {"status": "error", "error": str(e)}

    async def check_daily_tasks(self, db: Session) -> Dict[str, Any]:
        """Check status of daily system tasks (Stock Selection, Options, Automation)"""
        cached = self._get_from_cache("daily_tasks", custom_timeout=60) # Daily tasks every minute
        if cached: return cached

        from database.models import SelectedStock, AutoTradeExecution
        from utils.timezone_utils import get_ist_now_naive
        from sqlalchemy import func
        
        today = get_ist_now_naive().date()
        
        try:
            # 1. Stock Selection Check
            selection_count = db.query(SelectedStock).filter(
                SelectedStock.selection_date == today,
                SelectedStock.is_active == True
            ).count()
            
            # 2. Options Enhancement Check
            options_count = db.query(SelectedStock).filter(
                SelectedStock.selection_date == today,
                SelectedStock.is_active == True,
                SelectedStock.option_contract.isnot(None)
            ).count()
            
            # 3. Trade Execution Check
            trades = db.query(AutoTradeExecution).filter(
                func.date(AutoTradeExecution.entry_time) == today
            ).all()
            trade_count = len(trades)
            
            # Verify field correctness for today's trades
            malformed_trades = []
            for t in trades:
                missing_fields = []
                if not t.instrument_key: missing_fields.append("instrument_key")
                if not t.entry_price: missing_fields.append("entry_price")
                if not t.quantity: missing_fields.append("quantity")
                if not t.trading_mode: missing_fields.append("trading_mode")
                if missing_fields:
                    malformed_trades.append({"id": t.id, "symbol": t.symbol, "missing": missing_fields})

            # 4. Automation & Token Refresh Check
            from database.models import User, BrokerConfig
            import json
            
            admin_broker = db.query(BrokerConfig).join(User).filter(
                User.role == "admin",
                BrokerConfig.broker_name.ilike("upstox")
            ).first()
            
            token_refresh_status = "pending"
            last_refresh_time = None
            is_valid = False
            
            if admin_broker:
                # OPTIMIZED: Check validity ONLY IF NOT CACHED or expiring soon
                token_valid_cache = self._get_from_cache("token_validity", custom_timeout=1800) # 30 min cache
                if token_valid_cache is not None:
                    is_valid = token_valid_cache
                else:
                    from services.upstox_automation_service import UpstoxAutomationService
                    automation_service = UpstoxAutomationService()
                    # Run validity check in thread to avoid blocking event loop
                    is_valid = await asyncio.to_thread(automation_service._test_token_validity, admin_broker.access_token)
                    self._save_to_cache("token_validity", is_valid)
                
                # Check config for last automated run
                config_data = admin_broker.config or {}
                if isinstance(config_data, str):
                    try: config_data = json.loads(config_data)
                    except: config_data = {}
                
                last_refresh_str = config_data.get("last_automated_refresh")
                if last_refresh_str:
                    last_refresh_time = datetime.fromisoformat(last_refresh_str)
                    if last_refresh_time.date() == today:
                        token_refresh_status = "success" if is_valid else "failed"
                elif is_valid and admin_broker.access_token_expiry and admin_broker.access_token_expiry.date() >= today:
                    token_refresh_status = "success" # Assumed success if valid today
            
            automation = self.check_automation_status()
            
            result = {
                "timestamp": datetime.now().isoformat(),
                "tasks": {
                    "stock_selection": {
                        "status": "complete" if selection_count > 0 else "pending",
                        "count": selection_count,
                        "message": f"{selection_count} stocks selected today" if selection_count > 0 else "Waiting for selection"
                    },
                    "options_enhancement": {
                        "status": "complete" if options_count > 0 and options_count >= selection_count else "pending" if selection_count > 0 else "waiting",
                        "count": options_count,
                        "message": f"{options_count}/{selection_count} stocks enhanced with options" if selection_count > 0 else "Waiting for stock selection"
                    },
                    "auto_trading": {
                        "status": "running" if auto_trade_scheduler.is_running else "stopped",
                        "trades_today": trade_count,
                        "malformed_count": len(malformed_trades),
                        "malformed_details": malformed_trades[:5], # Show first 5
                        "message": f"System active, {trade_count} trades executed ({len(malformed_trades)} malformed)" if auto_trade_scheduler.is_running else "Scheduler not active"
                    },
                    "token_refresh": {
                        "status": token_refresh_status,
                        "last_run": last_refresh_time.isoformat() if last_refresh_time else None,
                        "error": automation.get("error") if token_refresh_status == "failed" else None,
                        "message": f"Last refresh: {last_refresh_time.strftime('%H:%M')} IST" if last_refresh_time else "No refresh recorded for today"
                    }
                }
            }
            
            self._save_to_cache("daily_tasks", result)
            return result
        except Exception as e:
            logger.error(f"Daily tasks check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_strategy_status(self) -> Dict[str, Any]:
        """Check strategy execution status via Scheduler"""
        cached = self._get_from_cache("strategy_status")
        if cached: return cached

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
                
            self._save_to_cache("strategy_status", status)
            return status
            
        except Exception as e:
            logger.error(f"Strategy check failed: {e}")
            return {"status": "error", "error": str(e)}

# Singleton instance
system_check_service = SystemCheckService()
