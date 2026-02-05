"""
Telegram Notification Service (Production Grade)
Handles asynchronous alerts for trade execution, system health, and PnL updates.
Supports both Admin (Global) and User (Personal) alerts.
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
    Uses HTML Parse Mode for better reliability and simpler escaping.
    """
    
    _instance = None
    _client: Optional[httpx.AsyncClient] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TelegramNotificationService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Only initialize once
        if not hasattr(self, 'initialized'):
            self.bot_token = TELEGRAM_BOT_TOKEN
            self.admin_chat_id = TELEGRAM_CHAT_ID
            self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            self.initialized = True
            logger.info("Telegram Notification Service initialized (HTML Mode)")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the shared httpx client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    def _clean(self, text: Any) -> str:
        """Clean text for HTML mode"""
        if text is None: return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    async def send_message(self, message: str, priority: str = "INFO", chat_id: Optional[str] = None) -> bool:
        """Send a raw message to Telegram"""
        target_chat_id = chat_id or self.admin_chat_id
        
        if self.bot_token == "YOUR_TELEGRAM_BOT_TOKEN" or not target_chat_id:
            logger.debug(f"Telegram alert skipped: Bot token or Chat ID ({target_chat_id}) missing")
            return False

        payload = {
            "chat_id": str(target_chat_id),
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        try:
            client = await self._get_client()
            response = await client.post(self.api_url, json=payload)
            
            if response.status_code == 429: # Rate limited
                retry_after = response.json().get("parameters", {}).get("retry_after", 5)
                logger.warning(f"Telegram rate limited. Retrying after {retry_after}s")
                await asyncio.sleep(retry_after)
                response = await client.post(self.api_url, json=payload)

            if response.status_code != 200:
                logger.error(f"Telegram HTML Error {response.status_code}: {response.text}")

            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message to {target_chat_id}: {e}")
            return False

    async def send_trade_entry(self, trade_data: Dict[str, Any], chat_id: Optional[str] = None):
        """Send professional trade entry alert (HTML)"""
        symbol = self._clean(trade_data.get('symbol', 'Unknown'))
        option_type = self._clean(trade_data.get('option_type', ''))
        entry_price = f"{trade_data.get('entry_price', 0):.2f}"
        sl = f"{trade_data.get('stop_loss', 0):.2f}"
        target = f"{trade_data.get('target', 0):.2f}"
        mode = trade_data.get('trading_mode', 'PAPER').upper()
        
        msg = (
            f"🚀 <b>TRADE EXECUTED ({mode})</b>\n\n"
            f"📈 <b>Symbol:</b> {symbol} {option_type}\n"
            f"🎯 <b>Entry:</b> ₹{entry_price}\n"
            f"🛡️ <b>Stop Loss:</b> ₹{sl}\n"
            f"🎯 <b>Target:</b> ₹{target}\n\n"
            f"🕒 {get_ist_now_naive().strftime('%H:%M:%S')} IST"
        )
        await self.send_message(msg, chat_id=chat_id)

    async def send_trade_exit(self, trade_data: Dict[str, Any], chat_id: Optional[str] = None):
        """Send professional trade exit alert (HTML)"""
        symbol = self._clean(trade_data.get('symbol', 'Unknown'))
        exit_price = f"{trade_data.get('exit_price', 0):.2f}"
        pnl = float(trade_data.get('pnl', 0))
        pnl_str = f"{pnl:+.2f}"
        reason = self._clean(trade_data.get('exit_reason', 'Signal').replace('_', ' '))
        
        emoji = "✅" if pnl >= 0 else "❌"
        pnl_label = "PROFIT" if pnl >= 0 else "LOSS"

        msg = (
            f"{emoji} <b>POSITION CLOSED</b>\n\n"
            f"📈 <b>Symbol:</b> {symbol}\n"
            f"🚪 <b>Exit Reason:</b> {reason}\n"
            f"🧾 <b>Exit Price:</b> ₹{exit_price}\n"
            f"💰 <b>{pnl_label}:</b> <b>₹{pnl_str}</b>\n\n"
            f"🕒 {get_ist_now_naive().strftime('%H:%M:%S')} IST"
        )
        await self.send_message(msg, chat_id=chat_id)

    async def send_system_alert(self, component: str, message: str, level: str = "ERROR", chat_id: Optional[str] = None):
        """Send system health alert (HTML)"""
        level_emoji = "⚠️" if level == "ERROR" else "ℹ️"
        comp = self._clean(component.upper())
        msg_text = self._clean(message)
        
        msg = (
            f"{level_emoji} <b>SYSTEM ALERT: {comp}</b>\n\n"
            f"<i>{msg_text}</i>\n\n"
            f"🕒 {get_ist_now_naive().strftime('%H:%M:%S')} IST"
        )
        await self.send_message(msg, priority=level, chat_id=chat_id)

# Singleton instance
telegram_notifier = TelegramNotificationService()