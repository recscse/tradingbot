"""
Unified Alert Manager (Production Grade)
Orchestrates notifications across different channels and manages tracing.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from enum import Enum

from services.notifications.telegram_service import telegram_notifier
from services.notification_service import notification_service, NotificationPriority, NotificationTypes

logger = logging.getLogger("alert_manager")

class AlertManager:
    """
    Central hub for system and trading alerts.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AlertManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.telegram = telegram_notifier
            self.db_service = notification_service
            self.initialized = True
            # Deduplication cache for system alerts {(component, status): last_sent_time}
            self._system_alert_cache = {}
            logger.info("Alert Manager initialized")

    # ============================================================================
    # ADMIN SYSTEM ALERTS
    # ============================================================================

    async def send_admin_system_status(self, component: str, status: str, details: str = ""):
        """Send service-specific status update with 5-minute deduplication"""
        import datetime
        now = datetime.datetime.now()
        cache_key = (component, status)
        
        # Check deduplication window (5 minutes)
        if cache_key in self._system_alert_cache:
            last_sent = self._system_alert_cache[cache_key]
            if (now - last_sent).total_seconds() < 300:
                logger.debug(f"Skipping duplicate system alert for {component}:{status} (last sent {last_sent})")
                return

        # Update cache
        self._system_alert_cache[cache_key] = now
        
        await self.telegram.send_system_alert(component, details, level="INFO" if status == "SUCCESS" else "ERROR")
        
        await self.db_service.create_trading_notification(
            user_id=1,
            notification_type=NotificationTypes.SYSTEM_STARTUP,
            symbol=component,
            data={"status": status, "details": details}
        )

    async def send_market_intelligence(self, sentiment: str, ad_ratio: float, top_sectors: List[str]):
        """Clean Market Intelligence Template"""
        safe_sentiment = self.telegram._clean(sentiment.upper())
        safe_sectors = self.telegram._clean(", ".join(top_sectors))
        
        msg = (
            f"<b>🧠 MARKET INTELLIGENCE</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>Sentiment:</b> {safe_sentiment}\n"
            f"<b>A/D Ratio:</b> {ad_ratio:.2f}\n"
            f"<b>Hot Sectors:</b> {safe_sectors}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📈 <i>Ready for pre-open strategy.</i>"
        )
        await self.telegram.send_message(msg)

    async def send_stock_selection_summary(self, count: int, stocks: List[str], phase: str):
        """Clean Stock Selection Template"""
        safe_phase = self.telegram._clean(phase.upper())
        safe_stocks = self.telegram._clean(", ".join(stocks))
        
        msg = (
            f"<b>🎯 STRATEGY STOCK SELECTION</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>Phase:</b>   {safe_phase}\n"
            f"<b>Count:</b>   {count} High-Quality Stocks\n"
            f"<b>Symbols:</b> <code>{safe_stocks}</code>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✅ <i>Auto-Trade Feed configured.</i>"
        )
        await self.telegram.send_message(msg)

    # ============================================================================
    # TRADING ALERTS (User & Service Tracing)
    # ============================================================================

    async def _get_user_chat_id(self, user_id: int) -> Optional[str]:
        from database.connection import SessionLocal
        from database.models import User
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            return user.telegram_chat_id if user else None
        except Exception as e:
            logger.error(f"Tracing Error: {e}")
            return None
        finally:
            db.close()

    async def notify_trade_entry(self, user_id: int, trade_data: Dict[str, Any]):
        user_chat_id = await self._get_user_chat_id(user_id)
        await self.telegram.send_trade_entry(trade_data, chat_id=user_chat_id)
        await self.db_service.create_trading_notification(
            user_id=user_id,
            notification_type=NotificationTypes.POSITION_OPENED,
            symbol=trade_data.get('symbol', 'Unknown'),
            data=trade_data
        )

    async def notify_trade_exit(self, user_id: int, trade_data: Dict[str, Any]):
        user_chat_id = await self._get_user_chat_id(user_id)
        await self.telegram.send_trade_exit(trade_data, chat_id=user_chat_id)
        await self.db_service.create_trading_notification(
            user_id=user_id,
            notification_type=NotificationTypes.POSITION_CLOSED,
            symbol=trade_data.get('symbol', 'Unknown'),
            data=trade_data
        )

    async def notify_critical_error(self, user_id: int, component: str, error: str):
        """Alert with specific service tracing"""
        await self.telegram.send_system_alert(component, error, level="ERROR")
        await self.db_service.create_notification(
            user_id=user_id,
            title=f"Tracing ERROR: {component}",
            message=error,
            notification_type=NotificationTypes.SYSTEM_SHUTDOWN,
            priority=NotificationPriority.CRITICAL
        )

# Global singleton
alert_manager = AlertManager()
