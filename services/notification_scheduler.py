"""
Notification Scheduler Service

This service handles scheduled notification tasks including token monitoring,
daily summaries, and system health checks.
"""

import asyncio
import logging
import schedule
import threading
import time
from datetime import datetime, time as dt_time
from typing import Dict, List

from services.notification_service import notification_service, NotificationTypes, NotificationPriority
from services.token_monitor_service import token_monitor_service

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """
    Service to schedule and run periodic notification tasks.
    """
    
    def __init__(self):
        self.running = False
        self.scheduler_thread = None
        
    def start_scheduler(self):
        """Start the notification scheduler in a background thread."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
            
        self.running = True
        
        # Schedule tasks
        self._setup_schedules()
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("🚀 Notification scheduler started")
    
    def stop_scheduler(self):
        """Stop the notification scheduler."""
        self.running = False
        schedule.clear()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
            
        logger.info("⏹️ Notification scheduler stopped")
    
    def _setup_schedules(self):
        """Setup all scheduled tasks."""
        
        # Token monitoring - every 30 minutes
        schedule.every(30).minutes.do(self._run_async_task, self.monitor_token_expiry)
        
        # Market opening reminder - at 8:45 AM IST
        schedule.every().day.at("08:45").do(self._run_async_task, self.send_market_opening_reminder)
        
        # Daily P&L summary - at 6:30 PM IST  
        schedule.every().day.at("18:30").do(self._run_async_task, self.send_daily_pnl_summaries)
        
        # System health check - every hour
        schedule.every().hour.do(self._run_async_task, self.perform_system_health_check)
        
        # Cleanup old notifications - daily at 2:00 AM
        schedule.every().day.at("02:00").do(self._run_async_task, self.cleanup_old_notifications)
        
        # Weekly token status report - Mondays at 9:00 AM
        schedule.every().monday.at("09:00").do(self._run_async_task, self.send_weekly_token_report)
        
        logger.info("📅 Scheduled tasks configured")
    
    def _run_scheduler(self):
        """Run the scheduler loop."""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"❌ Scheduler error: {e}")
                time.sleep(60)
    
    def _run_async_task(self, coro_func):
        """
        Helper to run async functions in scheduler (non-blocking).

        CRITICAL FIX: Uses asyncio.create_task() to avoid blocking the main thread.
        """
        try:
            # Get the existing event loop instead of creating new one
            try:
                loop = asyncio.get_running_loop()
                # Schedule as background task - DON'T WAIT
                asyncio.create_task(coro_func())
                logger.debug(f"✅ Scheduled {coro_func.__name__} as background task")
            except RuntimeError:
                # No event loop running - fall back to thread pool execution
                import concurrent.futures
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                executor.submit(self._run_in_new_loop, coro_func)
                logger.debug(f"✅ Scheduled {coro_func.__name__} in thread pool")
        except Exception as e:
            logger.error(f"❌ Async task scheduling error: {e}")

    def _run_in_new_loop(self, coro_func):
        """Run coroutine in new event loop (for thread pool execution)"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(coro_func())
            loop.close()
        except Exception as e:
            logger.error(f"❌ Async task error in new loop: {e}")
    
    async def monitor_token_expiry(self):
        """Monitor broker tokens for expiry and send notifications."""
        try:
            logger.info("🔍 Running token expiry monitoring...")
            
            results = await token_monitor_service.monitor_all_tokens()
            
            logger.info(f"📊 Token monitoring completed: {results}")
            
            # Send summary to admins if there are critical issues
            total_critical = results.get("critical", 0) + results.get("expired", 0)
            if total_critical > 0:
                # This would send to admin users
                logger.warning(f"⚠️ {total_critical} critical token issues detected")
                
        except Exception as e:
            logger.error(f"❌ Token monitoring failed: {e}")
    
    async def send_market_opening_reminder(self):
        """Send market opening reminders to users."""
        try:
            from database.connection import get_db
            from database.models import User
            
            # Check if it's a trading day (not weekend)
            now = datetime.now()
            if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
                return
                
            logger.info("📢 Sending market opening reminders...")
            
            db = next(get_db())
            active_users = db.query(User).filter(User.is_active == True).all()
            
            for user in active_users:
                try:
                    await notification_service.send_multi_channel_notification(
                        user_id=user.id,
                        title="🔔 Market Opening Soon",
                        message="Indian stock market opens in 15 minutes (9:15 AM). Good luck with your trades today!",
                        notification_type="market_opening",
                        priority=NotificationPriority.NORMAL,
                        channels=["database", "push"],
                        metadata={"market_time": "09:15", "timezone": "IST"},
                        db=db
                    )
                except Exception as e:
                    logger.error(f"Failed to send market reminder to user {user.id}: {e}")
            
            db.close()
            logger.info(f"📤 Market opening reminders sent to {len(active_users)} users")
            
        except Exception as e:
            logger.error(f"❌ Failed to send market opening reminders: {e}")
    
    async def send_daily_pnl_summaries(self):
        """Send daily P&L summaries to users."""
        try:
            from database.connection import get_db
            from database.models import User, Trade
            from sqlalchemy import func, and_
            from datetime import date
            
            logger.info("📊 Generating daily P&L summaries...")
            
            db = next(get_db())
            today = date.today()
            
            # Get users with trades today
            users_with_trades = (
                db.query(User.id, User.email, User.full_name)
                .join(Trade)
                .filter(
                    and_(
                        User.is_active == True,
                        func.date(Trade.created_at) == today
                    )
                )
                .distinct()
                .all()
            )
            
            for user_id, email, full_name in users_with_trades:
                try:
                    # Calculate daily P&L
                    daily_trades = (
                        db.query(Trade)
                        .filter(
                            and_(
                                Trade.user_id == user_id,
                                func.date(Trade.created_at) == today
                            )
                        )
                        .all()
                    )
                    
                    total_pnl = sum(trade.pnl or 0 for trade in daily_trades)
                    winning_trades = len([t for t in daily_trades if (t.pnl or 0) > 0])
                    total_trades = len(daily_trades)
                    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                    
                    # Determine message tone based on P&L
                    if total_pnl > 0:
                        emoji = "💰"
                        tone = "Great job!"
                    elif total_pnl < 0:
                        emoji = "📊"
                        tone = "Keep learning!"
                    else:
                        emoji = "📈"
                        tone = "Steady trading!"
                    
                    await notification_service.send_multi_channel_notification(
                        user_id=user_id,
                        title=f"{emoji} Daily Trading Summary",
                        message=(
                            f"{tone} Today's results: {total_trades} trades, "
                            f"₹{total_pnl:,.2f} P&L, {win_rate:.1f}% win rate."
                        ),
                        notification_type=NotificationTypes.DAILY_PNL_SUMMARY,
                        priority=NotificationPriority.NORMAL,
                        channels=["database", "email", "push"],
                        metadata={
                            "date": today.isoformat(),
                            "total_trades": total_trades,
                            "total_pnl": float(total_pnl),
                            "winning_trades": winning_trades,
                            "win_rate": round(win_rate, 1)
                        },
                        db=db
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to send daily summary to user {user_id}: {e}")
            
            db.close()
            logger.info(f"📤 Daily P&L summaries sent to {len(users_with_trades)} users")
            
        except Exception as e:
            logger.error(f"❌ Failed to send daily P&L summaries: {e}")
    
    async def perform_system_health_check(self):
        """Perform system health checks and send alerts if needed."""
        try:
            logger.info("🏥 Performing system health check...")
            
            health_issues = []
            
            # Check database connectivity
            try:
                from database.connection import get_db
                db = next(get_db())
                db.execute("SELECT 1")
                db.close()
            except Exception as e:
                health_issues.append(f"Database connectivity: {str(e)}")
            
            # Check Redis connectivity (if enabled)
            try:
                import os
                if os.getenv("REDIS_ENABLED", "false").lower() == "true":
                    import redis
                    redis_client = redis.Redis(
                        host=os.getenv("REDIS_HOST", "localhost"),
                        port=int(os.getenv("REDIS_PORT", 6379)),
                        db=int(os.getenv("REDIS_DB", 0))
                    )
                    redis_client.ping()
            except Exception as e:
                health_issues.append(f"Redis connectivity: {str(e)}")
            
            # Check disk space (NON-BLOCKING with timeout)
            try:
                import shutil
                import concurrent.futures

                # Run disk_usage in thread pool with timeout to avoid blocking
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(shutil.disk_usage, ".")
                    disk_usage = future.result(timeout=5)  # 5 second timeout
                    free_gb = disk_usage.free / (1024**3)
                    if free_gb < 1:  # Less than 1GB free
                        health_issues.append(f"Low disk space: {free_gb:.1f}GB remaining")
            except concurrent.futures.TimeoutError:
                logger.warning("⚠️ Disk space check timed out after 5 seconds - skipping")
            except Exception as disk_error:
                logger.warning(f"⚠️ Disk space check failed: {disk_error} - skipping")
            
            # If there are health issues, send alert to admins
            if health_issues:
                from database.connection import get_db
                from database.models import User
                
                db = next(get_db())
                admin_users = db.query(User).filter(User.role == "Admin").all()
                
                for admin in admin_users:
                    await notification_service.send_multi_channel_notification(
                        user_id=admin.id,
                        title="🚨 System Health Alert",
                        message=f"System health issues detected: {'; '.join(health_issues)}",
                        notification_type="system_health_alert",
                        priority=NotificationPriority.HIGH,
                        channels=["database", "email", "sms"],
                        metadata={"issues": health_issues, "timestamp": datetime.utcnow().isoformat()},
                        db=db
                    )
                
                db.close()
                logger.warning(f"⚠️ Health issues detected: {health_issues}")
            else:
                logger.info("✅ System health check passed")
                
        except Exception as e:
            logger.error(f"❌ System health check failed: {e}")
    
    async def cleanup_old_notifications(self):
        """Clean up old notifications to save database space."""
        try:
            logger.info("🧹 Starting notification cleanup...")
            
            deleted_count = notification_service.cleanup_old_notifications(days_old=30)
            
            logger.info(f"🗑️ Cleaned up {deleted_count} old notifications")
            
            # Send summary to admins if significant cleanup occurred
            if deleted_count > 100:
                from database.connection import get_db
                from database.models import User
                
                db = next(get_db())
                admin_users = db.query(User).filter(User.role == "Admin").all()
                
                for admin in admin_users:
                    await notification_service.send_multi_channel_notification(
                        user_id=admin.id,
                        title="🧹 Notification Cleanup Summary",
                        message=f"Cleaned up {deleted_count} notifications older than 30 days.",
                        notification_type="system_maintenance",
                        priority=NotificationPriority.LOW,
                        channels=["database"],
                        metadata={"deleted_count": deleted_count, "days_old": 30},
                        db=db
                    )
                
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Notification cleanup failed: {e}")
    
    async def send_weekly_token_report(self):
        """Send weekly token status reports to users."""
        try:
            logger.info("📅 Sending weekly token status reports...")
            
            from database.connection import get_db
            from database.models import User, BrokerConfig
            
            db = next(get_db())
            
            # Get users with broker configurations
            users_with_brokers = (
                db.query(User.id, User.email, User.full_name)
                .join(BrokerConfig)
                .filter(User.is_active == True)
                .distinct()
                .all()
            )
            
            for user_id, email, full_name in users_with_brokers:
                try:
                    # Get token status summary for this user
                    summary = await token_monitor_service.get_expiring_tokens_summary(user_id=user_id)
                    
                    total_tokens = (
                        len(summary["expired"]) + len(summary["critical"]) + 
                        len(summary["high"]) + len(summary["normal"]) + 
                        len(summary["reminder"])
                    )
                    
                    if total_tokens == 0:
                        continue
                    
                    needs_attention = len(summary["expired"]) + len(summary["critical"])
                    
                    if needs_attention > 0:
                        priority = NotificationPriority.HIGH
                        title = "⚠️ Weekly Token Report - Action Required"
                        message = f"You have {needs_attention} broker tokens that need immediate attention."
                    else:
                        priority = NotificationPriority.NORMAL
                        title = "📊 Weekly Token Status Report"
                        message = f"All {total_tokens} broker tokens are healthy. Keep up the good work!"
                    
                    await notification_service.send_multi_channel_notification(
                        user_id=user_id,
                        title=title,
                        message=message,
                        notification_type="weekly_token_report",
                        priority=priority,
                        channels=["database", "email"] if needs_attention > 0 else ["database"],
                        metadata={
                            "total_tokens": total_tokens,
                            "needs_attention": needs_attention,
                            "summary": summary
                        },
                        db=db
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to send weekly report to user {user_id}: {e}")
            
            db.close()
            logger.info(f"📤 Weekly token reports sent to {len(users_with_brokers)} users")
            
        except Exception as e:
            logger.error(f"❌ Failed to send weekly token reports: {e}")
    
    def get_scheduler_status(self) -> Dict:
        """Get current scheduler status and next scheduled runs."""
        try:
            next_runs = {}
            for job in schedule.jobs:
                job_name = job.job_func.__name__ if hasattr(job.job_func, '__name__') else str(job.job_func)
                next_runs[job_name] = job.next_run.isoformat() if job.next_run else None
            
            return {
                "running": self.running,
                "total_jobs": len(schedule.jobs),
                "next_runs": next_runs,
                "thread_alive": self.scheduler_thread.is_alive() if self.scheduler_thread else False
            }
        except Exception as e:
            logger.error(f"❌ Failed to get scheduler status: {e}")
            return {"error": str(e)}


# Global notification scheduler instance
notification_scheduler = NotificationScheduler()