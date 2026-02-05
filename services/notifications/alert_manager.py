"""
Unified Alert Manager (Production Grade)
Orchestrates notifications across different channels (Telegram, Email, etc.)
and manages target audiences (Admin vs. Users).
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from enum import Enum

from services.notifications.telegram_service import telegram_notifier
from services.notification_service import notification_service, NotificationPriority, NotificationTypes

logger = logging.getLogger("alert_manager")

class AlertAudience(Enum):
    ADMIN = "admin"
    USER = "user"
    BOTH = "both"

class AlertManager:
    """
    Central hub for all system and trading alerts.
    Routes messages to correct providers based on audience and priority.
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
            logger.info("Alert Manager initialized")

    # ============================================================================
    # ADMIN SYSTEM ALERTS
    # ============================================================================

    async def send_admin_system_status(self, component: str, status: str, details: str = ""):
        """Send system health/lifecycle status to Admin (HTML)"""
        safe_comp = self.telegram._clean(component)
        safe_status = self.telegram._clean(status)
        safe_details = self.telegram._clean(details)
        
        msg = (
            f"🛠 <b>SYSTEM STATUS</b>\n\n"
            f"⚙ <b>Comp:</b> {safe_comp}\n"
            f"✅ <b>Status:</b> {safe_status}\n"
            f"📑 <b>Info:</b> {safe_details}"
        )
        await self.telegram.send_message(msg, priority="INFO")
        
        # Log to Database
        await self.db_service.create_trading_notification(
            user_id=1,
            notification_type=NotificationTypes.SYSTEM_STARTUP,
            symbol=component,
            data={"status": status, "details": details}
        )

    async def send_market_intelligence(self, sentiment: str, ad_ratio: float, top_sectors: List[str]):
        """Send market sentiment and analysis to Admin (HTML)"""
        safe_sentiment = self.telegram._clean(sentiment.upper())
        safe_ad_ratio = f"{ad_ratio:.2f}"
        safe_sectors = self.telegram._clean(", ".join(top_sectors))
        
        msg = (
            f"🧠 <b>MARKET INTEL</b>\n\n"
            f"📊 <b>Sentiment:</b> {safe_sentiment}\n"
            f"⚖ <b>A/D Ratio:</b> {safe_ad_ratio}\n"
            f"🏢 <b>Sectors:</b> {safe_sectors}"
        )
        await self.telegram.send_message(msg)

    async def send_stock_selection_summary(self, count: int, stocks: List[str], phase: str):
        """Send daily stock selection results to Admin (HTML)"""
        safe_phase = self.telegram._clean(phase.upper())
        safe_stocks = self.telegram._clean(", ".join(stocks))
        
        msg = (
            f"🎯 <b>STOCKS SELECTED</b>\n\n"
            f"📑 <b>Phase:</b> {safe_phase}\n"
            f"🔢 <b>Count:</b> {count}\n"
            f"✅ <b>Symbols:</b> <code>{safe_stocks}</code>"
        )
        await self.telegram.send_message(msg)

    # ============================================================================
    # TRADING ALERTS (User Specific)
    # ============================================================================

    async def _get_user_chat_id(self, user_id: int) -> Optional[str]:
        """Fetch user's personal telegram chat ID from DB"""
        from database.connection import SessionLocal
        from database.models import User
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            return user.telegram_chat_id if user else None
        except Exception as e:
            logger.error(f"Error fetching chat_id for user {user_id}: {e}")
            return None
        finally:
            db.close()

    async def notify_trade_entry(self, user_id: int, trade_data: Dict[str, Any]):
        """Notify user about a new trade entry"""
        user_chat_id = await self._get_user_chat_id(user_id)
        await self.telegram.send_trade_entry(trade_data, chat_id=user_chat_id)
        
        # Internal (Database)
        await self.db_service.create_trading_notification(
            user_id=user_id,
            notification_type=NotificationTypes.POSITION_OPENED,
            symbol=trade_data.get('symbol', 'Unknown'),
            data=trade_data
        )

    async def notify_trade_exit(self, user_id: int, trade_data: Dict[str, Any]):
        """Notify user about a trade exit"""
        user_chat_id = await self._get_user_chat_id(user_id)
        await self.telegram.send_trade_exit(trade_data, chat_id=user_chat_id)
        
        # Internal (Database)
        await self.db_service.create_trading_notification(
            user_id=user_id,
            notification_type=NotificationTypes.POSITION_CLOSED,
            symbol=trade_data.get('symbol', 'Unknown'),
            data=trade_data
        )

    async def notify_critical_error(self, user_id: int, component: str, error: str):
        """Notify user/admin of a critical failure"""
        await self.telegram.send_system_alert(component, error, level="ERROR")
        
        await self.db_service.create_notification(
            user_id=user_id,
            title=f"Critical Error: {component}",
            message=error,
            notification_type=NotificationTypes.SYSTEM_SHUTDOWN,
            priority=NotificationPriority.CRITICAL
        )

# Global singleton
alert_manager = AlertManager()