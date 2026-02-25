"""
Telegram Notification Service (Production Grade)
Handles asynchronous alerts for trade execution, system health, and PnL updates.
Uses HTML Parse Mode for professional formatting and reliability.
"""

import logging
import asyncio
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from decimal import Decimal

from core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils.timezone_utils import get_ist_now_naive

logger = logging.getLogger("telegram_service")

class TelegramNotificationService:
    """
    Singleton service for sending formatted Telegram notifications.
    """
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TelegramNotificationService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.bot_token = TELEGRAM_BOT_TOKEN
            self.admin_chat_id = TELEGRAM_CHAT_ID
            self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            self.initialized = True
            logger.info("Telegram Notification Service initialized (HTML Mode)")

    def _clean(self, text: Any) -> str:
        if text is None: return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    async def send_message(self, message: str, priority: str = "INFO", chat_id: Optional[str] = None) -> bool:
        target_chat_id = chat_id or self.admin_chat_id
        if self.bot_token == "YOUR_TELEGRAM_BOT_TOKEN" or not target_chat_id:
            return False

        payload = {
            "chat_id": str(target_chat_id),
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(self.api_url, json=payload)
                if response.status_code == 429:
                    retry_after = response.json().get("parameters", {}).get("retry_after", 5)
                    await asyncio.sleep(retry_after)
                    response = await client.post(self.api_url, json=payload)
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Telegram Alert Failed: {e}")
            return False

    async def send_trade_entry(self, trade_data: Dict[str, Any], chat_id: Optional[str] = None):
        """Clean & Professional Trade Entry Template"""
        symbol = self._clean(trade_data.get('symbol', 'Unknown'))
        opt_type = self._clean(trade_data.get('option_type', ''))
        entry = f"{trade_data.get('entry_price', 0):.2f}"
        sl = f"{trade_data.get('stop_loss', 0):.2f}"
        tgt = f"{trade_data.get('target', 0):.2f}"
        mode = trade_data.get('trading_mode', 'PAPER').upper()
        
        msg = (
            f"<b>🚀 NEW TRADE EXECUTED</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>Symbol:</b>  <code>{symbol} {opt_type}</code>\n"
            f"<b>Mode:</b>    {mode}\n"
            f"<b>Entry:</b>   ₹{entry}\n"
            f"<b>Stop Loss:</b> ₹{sl}\n"
            f"<b>Target:</b>  ₹{tgt}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕒 {get_ist_now_naive().strftime('%I:%M:%S %p')} IST"
        )
        await self.send_message(msg, chat_id=chat_id)

    async def send_trade_exit(self, trade_data: Dict[str, Any], chat_id: Optional[str] = None):
        """Clean & Professional Trade Exit Template"""
        symbol = self._clean(trade_data.get('symbol', 'Unknown'))
        exit_p = f"{trade_data.get('exit_price', 0):.2f}"
        pnl = float(trade_data.get('pnl', 0))
        reason = self._clean(trade_data.get('exit_reason', 'SIGNAL')).replace('_', ' ')
        
        emoji = "🟢" if pnl >= 0 else "🔴"
        pnl_label = "PROFIT" if pnl >= 0 else "LOSS"

        msg = (
            f"<b>{emoji} POSITION CLOSED</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>Symbol:</b>  <code>{symbol}</code>\n"
            f"<b>Reason:</b>  {reason}\n"
            f"<b>Exit Price:</b> ₹{exit_p}\n"
            f"<b>Net {pnl_label}:</b> <b>₹{pnl:+.2f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕒 {get_ist_now_naive().strftime('%I:%M:%S %p')} IST"
        )
        await self.send_message(msg, chat_id=chat_id)

    async def send_system_alert(self, component: str, message: str, level: str = "ERROR", chat_id: Optional[str] = None):
        """Clean System Health Template with Service Tracing"""
        header = "🚨 CRITICAL SYSTEM ERROR" if level == "ERROR" else "ℹ️ SYSTEM INFORMATION"
        color = "red" if level == "ERROR" else "blue"
        comp = self._clean(component.upper())
        msg_text = self._clean(message)
        
        msg = (
            f"<b>{header}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>Service:</b>  <code>{comp}</code>\n"
            f"<b>Status:</b>   {level}\n"
            f"<b>Details:</b>  <i>{msg_text}</i>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕒 {get_ist_now_naive().strftime('%I:%M:%S %p')} IST"
        )
        await self.send_message(msg, priority=level, chat_id=chat_id)

# Singleton instance
telegram_notifier = TelegramNotificationService()
