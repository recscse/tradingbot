"""
Trading Notification Triggers

This service integrates with the trading system to automatically create notifications
for various trading events like order execution, stop loss hits, broker disconnections, etc.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional

from database.models import Trade, Order, BrokerConfig, User
from services.notification_service import notification_service, NotificationTypes, NotificationPriority

logger = logging.getLogger(__name__)


class TradingNotificationTriggers:
    """
    Service to trigger notifications based on trading events.
    This integrates with the existing trading system.
    """
    
    def __init__(self):
        self.enabled = True
        
    async def on_order_executed(
        self,
        user_id: int,
        order_data: Dict[str, Any],
        db_session=None
    ) -> bool:
        """
        Trigger notification when an order is executed.
        
        Args:
            user_id: User ID who placed the order
            order_data: Dictionary with order execution data
            db_session: Database session (optional)
        """
        if not self.enabled:
            return False
            
        try:
            symbol = order_data.get('symbol', 'Unknown')
            quantity = order_data.get('quantity', 0)
            price = order_data.get('price', 0)
            order_type = order_data.get('order_type', 'Unknown')
            trade_type = order_data.get('trade_type', 'Unknown')  # BUY/SELL
            
            # Create notification
            await notification_service.create_trading_notification(
                user_id=user_id,
                notification_type=NotificationTypes.ORDER_EXECUTED,
                symbol=symbol,
                data={
                    'quantity': quantity,
                    'price': price,
                    'order_type': order_type,
                    'trade_type': trade_type,
                    'executed_at': datetime.utcnow().isoformat()
                },
                db=db_session
            )
            
            logger.info(f"📈 Order executed notification sent: {symbol} {quantity}@₹{price}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to trigger order executed notification: {e}")
            return False
    
    async def on_stop_loss_hit(
        self,
        user_id: int,
        position_data: Dict[str, Any],
        db_session=None
    ) -> bool:
        """
        Trigger notification when stop loss is hit.
        """
        if not self.enabled:
            return False
            
        try:
            symbol = position_data.get('symbol', 'Unknown')
            sl_price = position_data.get('sl_price', 0)
            loss_amount = position_data.get('loss_amount', 0)
            quantity = position_data.get('quantity', 0)
            
            await notification_service.create_trading_notification(
                user_id=user_id,
                notification_type=NotificationTypes.STOP_LOSS_HIT,
                symbol=symbol,
                data={
                    'price': sl_price,
                    'loss': abs(loss_amount),
                    'quantity': quantity,
                    'triggered_at': datetime.utcnow().isoformat()
                },
                db=db_session
            )
            
            logger.warning(f"🔴 Stop loss hit notification sent: {symbol} loss ₹{abs(loss_amount)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to trigger stop loss notification: {e}")
            return False
    
    async def on_target_reached(
        self,
        user_id: int,
        position_data: Dict[str, Any],
        db_session=None
    ) -> bool:
        """
        Trigger notification when target price is reached.
        """
        if not self.enabled:
            return False
            
        try:
            symbol = position_data.get('symbol', 'Unknown')
            target_price = position_data.get('target_price', 0)
            profit_amount = position_data.get('profit_amount', 0)
            quantity = position_data.get('quantity', 0)
            
            await notification_service.create_trading_notification(
                user_id=user_id,
                notification_type=NotificationTypes.TARGET_REACHED,
                symbol=symbol,
                data={
                    'price': target_price,
                    'profit': profit_amount,
                    'quantity': quantity,
                    'achieved_at': datetime.utcnow().isoformat()
                },
                db=db_session
            )
            
            logger.info(f"🎯 Target reached notification sent: {symbol} profit ₹{profit_amount}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to trigger target reached notification: {e}")
            return False
    
    async def on_position_opened(
        self,
        user_id: int,
        position_data: Dict[str, Any],
        db_session=None
    ) -> bool:
        """
        Trigger notification when a new position is opened.
        """
        if not self.enabled:
            return False
            
        try:
            symbol = position_data.get('symbol', 'Unknown')
            quantity = position_data.get('quantity', 0)
            entry_price = position_data.get('entry_price', 0)
            position_type = position_data.get('position_type', 'LONG')
            
            await notification_service.create_trading_notification(
                user_id=user_id,
                notification_type=NotificationTypes.POSITION_OPENED,
                symbol=symbol,
                data={
                    'quantity': quantity,
                    'price': entry_price,
                    'position_type': position_type,
                    'opened_at': datetime.utcnow().isoformat()
                },
                db=db_session
            )
            
            logger.info(f"🎯 Position opened notification sent: {symbol} {quantity}@₹{entry_price}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to trigger position opened notification: {e}")
            return False
    
    async def on_position_closed(
        self,
        user_id: int,
        position_data: Dict[str, Any],
        db_session=None
    ) -> bool:
        """
        Trigger notification when a position is closed.
        """
        if not self.enabled:
            return False
            
        try:
            symbol = position_data.get('symbol', 'Unknown')
            pnl = position_data.get('pnl', 0)
            exit_price = position_data.get('exit_price', 0)
            quantity = position_data.get('quantity', 0)
            hold_duration = position_data.get('hold_duration', 'Unknown')
            
            await notification_service.create_trading_notification(
                user_id=user_id,
                notification_type=NotificationTypes.POSITION_CLOSED,
                symbol=symbol,
                data={
                    'pnl': pnl,
                    'exit_price': exit_price,
                    'quantity': quantity,
                    'hold_duration': hold_duration,
                    'closed_at': datetime.utcnow().isoformat()
                },
                db=db_session
            )
            
            pnl_str = f"₹{pnl:+,.2f}" if isinstance(pnl, (int, float, Decimal)) else str(pnl)
            logger.info(f"💰 Position closed notification sent: {symbol} P&L {pnl_str}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to trigger position closed notification: {e}")
            return False
    
    async def on_margin_call(
        self,
        user_id: int,
        margin_data: Dict[str, Any],
        db_session=None
    ) -> bool:
        """
        Trigger CRITICAL notification for margin calls.
        """
        if not self.enabled:
            return False
            
        try:
            available_margin = margin_data.get('available_margin', 0)
            required_margin = margin_data.get('required_margin', 0)
            broker_name = margin_data.get('broker_name', 'Unknown')
            
            await notification_service.send_multi_channel_notification(
                user_id=user_id,
                title="⚠️ MARGIN CALL - IMMEDIATE ACTION REQUIRED",
                message=(
                    f"URGENT: Margin call on {broker_name}. "
                    f"Available: ₹{available_margin:,.2f}, Required: ₹{required_margin:,.2f}. "
                    f"Please add funds or reduce positions immediately."
                ),
                notification_type=NotificationTypes.MARGIN_CALL,
                priority=NotificationPriority.CRITICAL,
                channels=["database", "email", "sms", "push"],
                metadata={
                    'available': float(available_margin),
                    'required': float(required_margin),
                    'broker_name': broker_name,
                    'margin_shortfall': float(required_margin - available_margin)
                },
                db=db_session
            )
            
            logger.critical(f"🚨 MARGIN CALL notification sent to user {user_id}: shortfall ₹{required_margin - available_margin:,.2f}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to trigger margin call notification: {e}")
            return False
    
    async def on_broker_disconnected(
        self,
        user_id: int,
        broker_data: Dict[str, Any],
        db_session=None
    ) -> bool:
        """
        Trigger notification when broker connection is lost.
        """
        if not self.enabled:
            return False
            
        try:
            broker_name = broker_data.get('broker_name', 'Unknown')
            error_message = broker_data.get('error', 'Connection lost')
            
            await notification_service.send_multi_channel_notification(
                user_id=user_id,
                title=f"🔴 {broker_name} Connection Lost",
                message=(
                    f"Your {broker_name} connection has been lost. "
                    f"Error: {error_message}. Please reconnect to resume trading."
                ),
                notification_type=NotificationTypes.BROKER_DISCONNECTED,
                priority=NotificationPriority.HIGH,
                channels=["database", "email", "push"],
                metadata={
                    'broker_name': broker_name,
                    'error': error_message,
                    'disconnected_at': datetime.utcnow().isoformat()
                },
                db=db_session
            )
            
            logger.warning(f"🔴 Broker disconnection notification sent: {broker_name} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to trigger broker disconnection notification: {e}")
            return False
    
    async def on_broker_connected(
        self,
        user_id: int,
        broker_data: Dict[str, Any],
        db_session=None
    ) -> bool:
        """
        Trigger notification when broker connection is established/restored.
        """
        if not self.enabled:
            return False
            
        try:
            broker_name = broker_data.get('broker_name', 'Unknown')
            was_reconnection = broker_data.get('was_reconnection', False)
            
            title = f"✅ {broker_name} {'Reconnected' if was_reconnection else 'Connected'}"
            
            await notification_service.send_multi_channel_notification(
                user_id=user_id,
                title=title,
                message=(
                    f"Your {broker_name} connection is now active. "
                    f"{'Trading has been resumed.' if was_reconnection else 'You can start trading.'}"
                ),
                notification_type=NotificationTypes.BROKER_CONNECTED,
                priority=NotificationPriority.NORMAL,
                channels=["database", "push"],
                metadata={
                    'broker_name': broker_name,
                    'was_reconnection': was_reconnection,
                    'connected_at': datetime.utcnow().isoformat()
                },
                db=db_session
            )
            
            logger.info(f"✅ Broker connection notification sent: {broker_name} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to trigger broker connection notification: {e}")
            return False
    
    async def on_daily_loss_limit_hit(
        self,
        user_id: int,
        loss_data: Dict[str, Any],
        db_session=None
    ) -> bool:
        """
        Trigger notification when daily loss limit is hit.
        """
        if not self.enabled:
            return False
            
        try:
            daily_loss = loss_data.get('daily_loss', 0)
            loss_limit = loss_data.get('loss_limit', 0)
            trades_count = loss_data.get('trades_count', 0)
            
            await notification_service.send_multi_channel_notification(
                user_id=user_id,
                title="🛑 Daily Loss Limit Hit - Trading Suspended",
                message=(
                    f"Your daily loss limit of ₹{loss_limit:,.2f} has been reached. "
                    f"Current loss: ₹{abs(daily_loss):,.2f} across {trades_count} trades. "
                    f"Trading has been automatically suspended for today."
                ),
                notification_type=NotificationTypes.DAILY_LOSS_LIMIT,
                priority=NotificationPriority.CRITICAL,
                channels=["database", "email", "sms", "push"],
                metadata={
                    'daily_loss': float(daily_loss),
                    'loss_limit': float(loss_limit),
                    'trades_count': trades_count,
                    'suspended_at': datetime.utcnow().isoformat()
                },
                db=db_session
            )
            
            logger.critical(f"🛑 Daily loss limit notification sent to user {user_id}: ₹{abs(daily_loss):,.2f}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to trigger daily loss limit notification: {e}")
            return False
    
    async def on_ai_signal_generated(
        self,
        user_id: int,
        signal_data: Dict[str, Any],
        db_session=None
    ) -> bool:
        """
        Trigger notification when AI generates trading signals.
        """
        if not self.enabled:
            return False
            
        try:
            signal_type = signal_data.get('signal_type', 'BUY')  # BUY/SELL
            symbol = signal_data.get('symbol', 'Unknown')
            confidence = signal_data.get('confidence', 0)
            price = signal_data.get('price', 0)
            
            notification_type = NotificationTypes.AI_BUY_SIGNAL if signal_type == 'BUY' else NotificationTypes.AI_SELL_SIGNAL
            
            await notification_service.create_trading_notification(
                user_id=user_id,
                notification_type=notification_type,
                symbol=symbol,
                data={
                    'confidence': confidence,
                    'price': price,
                    'signal_type': signal_type,
                    'generated_at': datetime.utcnow().isoformat()
                },
                db=db_session
            )
            
            logger.info(f"🤖 AI signal notification sent: {signal_type} {symbol} confidence {confidence}%")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to trigger AI signal notification: {e}")
            return False
    
    async def on_price_alert_triggered(
        self,
        user_id: int,
        alert_data: Dict[str, Any],
        db_session=None
    ) -> bool:
        """
        Trigger notification when price alert is triggered.
        """
        if not self.enabled:
            return False
            
        try:
            symbol = alert_data.get('symbol', 'Unknown')
            current_price = alert_data.get('current_price', 0)
            alert_price = alert_data.get('alert_price', 0)
            direction = alert_data.get('direction', 'above')  # above/below
            
            direction_emoji = "⬆️" if direction == "above" else "⬇️"
            
            await notification_service.send_multi_channel_notification(
                user_id=user_id,
                title=f"🔔 Price Alert: {symbol}",
                message=(
                    f"{symbol} has moved {direction} your alert price. "
                    f"Current: ₹{current_price}, Alert: ₹{alert_price} {direction_emoji}"
                ),
                notification_type=NotificationTypes.PRICE_ALERT_TRIGGERED,
                priority=NotificationPriority.HIGH,
                channels=["database", "email", "push"],
                metadata={
                    'symbol': symbol,
                    'current_price': float(current_price),
                    'alert_price': float(alert_price),
                    'direction': direction,
                    'triggered_at': datetime.utcnow().isoformat()
                },
                db=db_session
            )
            
            logger.info(f"🔔 Price alert notification sent: {symbol} ₹{current_price} {direction} ₹{alert_price}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to trigger price alert notification: {e}")
            return False
    
    def enable_notifications(self):
        """Enable notification triggers."""
        self.enabled = True
        logger.info("✅ Trading notification triggers enabled")
    
    def disable_notifications(self):
        """Disable notification triggers."""
        self.enabled = False
        logger.info("⏸️ Trading notification triggers disabled")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of notification triggers."""
        return {
            "enabled": self.enabled,
            "available_triggers": [
                "order_executed",
                "stop_loss_hit", 
                "target_reached",
                "position_opened",
                "position_closed",
                "margin_call",
                "broker_connected",
                "broker_disconnected",
                "daily_loss_limit_hit",
                "ai_signal_generated",
                "price_alert_triggered"
            ]
        }


# Global trading notification triggers instance
trading_notification_triggers = TradingNotificationTriggers()