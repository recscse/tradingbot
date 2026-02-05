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
        """Send system health/lifecycle status to Admin"""
        safe_comp = self.telegram._escape_markdown(component)
        safe_status = self.telegram._escape_markdown(status)
        safe_details = self.telegram._escape_markdown(details)
        
        msg = (
            f"🛠️ *ADMIN SYSTEM STATUS*\n\n"
            f"⚙️ *Component:* {safe_comp}\n"
            f"✅ *Status:* {safe_status}\n"
            f"📑 *Details:* {safe_details}"
        )
        # Send to Telegram Admin
        await self.telegram.send_message(msg, priority="INFO")
        
        # Log to Database (Admin is user_id 1)
        self.db_service.create_notification(
            user_id=1,
            title=f"System Status: {component}",
            message=f"{status}: {details}",
            notification_type=NotificationTypes.SYSTEM_STARTUP,
            priority=NotificationPriority.NORMAL
        )

    async def send_market_intelligence(self, sentiment: str, ad_ratio: float, top_sectors: List[str]):
        """Send market sentiment and analysis to Admin"""
        safe_sentiment = self.telegram._escape_markdown(sentiment.upper())
        safe_ad_ratio = self.telegram._escape_markdown(f"{ad_ratio:.2f}")
        safe_sectors = self.telegram._escape_markdown(", ".join(top_sectors))
        
        msg = (
            f"🧠 *MARKET INTELLIGENCE*\n\n"
            f"📊 *Sentiment:* {safe_sentiment}\n"
            f"⚖️ *A/D Ratio:* {safe_ad_ratio}\n"
            f"🏢 *Top Sectors:* {safe_sectors}"
        )
        await self.telegram.send_message(msg)

    async def send_stock_selection_summary(self, count: int, stocks: List[str], phase: str):
        """Send daily stock selection results to Admin"""
        safe_phase = self.telegram._escape_markdown(phase.upper())
        safe_stocks = self.telegram._escape_markdown(", ".join(stocks))
        
        msg = (
            f"🎯 *STOCK SELECTION COMPLETED*\n\n"
            f"📑 *Phase:* {safe_phase}\n"
            f"🔢 *Count:* {count} Stocks\n"
            f"✅ *Symbols:* `{safe_stocks}`"
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
        # 1. Fetch personal chat ID
        user_chat_id = await self._get_user_chat_id(user_id)
        
        # 2. External (Telegram)
        await self.telegram.send_trade_entry(trade_data, chat_id=user_chat_id)
        
        # 3. Internal (Database)
        self.db_service.create_trading_notification(
            user_id=user_id,
            notification_type=NotificationTypes.POSITION_OPENED,
            symbol=trade_data.get('symbol', 'Unknown'),
            data=trade_data
        )

    async def notify_trade_exit(self, user_id: int, trade_data: Dict[str, Any]):
        """Notify user about a trade exit"""
        # 1. Fetch personal chat ID
        user_chat_id = await self._get_user_chat_id(user_id)
        
        # 2. External (Telegram)
        await self.telegram.send_trade_exit(trade_data, chat_id=user_chat_id)
        
        # 3. Internal (Database)
        self.db_service.create_trading_notification(
            user_id=user_id,
            notification_type=NotificationTypes.POSITION_CLOSED,
            symbol=trade_data.get('symbol', 'Unknown'),
            data=trade_data
        )

    async def notify_critical_error(self, user_id: int, component: str, error: str):
        """Notify user/admin of a critical failure"""
        await self.telegram.send_system_alert(component, error, level="ERROR")
        
        self.db_service.create_notification(
            user_id=user_id,
            title=f"Critical Error: {component}",
            message=error,
            notification_type=NotificationTypes.SYSTEM_SHUTDOWN,
            priority=NotificationPriority.CRITICAL
        )

# Global singleton
alert_manager = AlertManager()