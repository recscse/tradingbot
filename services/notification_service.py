"""
Comprehensive Notification Service for Trading Application

This service handles creation, management, and routing of notifications
including database storage, multi-channel delivery, and user preferences.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from database.connection import get_db
from database.models import Notification, User, BrokerConfig
from services.notifications import (
    send_notification_email,
    send_trade_sms,
    send_multi_channel_alert
)

logger = logging.getLogger(__name__)


class NotificationTypes:
    """Centralized notification type constants"""
    
    # Trading & Orders
    ORDER_PLACED = "order_placed"
    ORDER_EXECUTED = "order_executed"
    ORDER_PARTIALLY_FILLED = "order_partially_filled"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_REJECTED = "order_rejected"
    ORDER_MODIFIED = "order_modified"
    
    # Position Management
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    STOP_LOSS_HIT = "stop_loss_hit"
    TARGET_REACHED = "target_reached"
    TRAILING_STOP_ADJUSTED = "trailing_stop_adjusted"
    
    # Risk Management
    MARGIN_CALL = "margin_call"
    POSITION_LIMIT_REACHED = "position_limit_reached"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    MAX_DRAWDOWN_ALERT = "max_drawdown_alert"
    
    # Token & Authentication
    TOKEN_EXPIRING_SOON = "token_expiring_soon"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_REFRESH_FAILED = "token_refresh_failed"
    MULTIPLE_TOKENS_EXPIRED = "multiple_tokens_expired"
    TOKEN_REFRESHED = "token_refreshed"
    
    # Broker & System
    BROKER_CONNECTED = "broker_connected"
    BROKER_DISCONNECTED = "broker_disconnected"
    BROKER_RECONNECTED = "broker_reconnected"
    API_RATE_LIMIT = "api_rate_limit"
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    
    # Market Data & Analysis
    PRICE_ALERT_TRIGGERED = "price_alert_triggered"
    VOLUME_SPIKE = "volume_spike"
    VOLATILITY_ALERT = "volatility_alert"
    AI_BUY_SIGNAL = "ai_buy_signal"
    AI_SELL_SIGNAL = "ai_sell_signal"
    
    # Portfolio & Performance
    DAILY_PNL_SUMMARY = "daily_pnl_summary"
    PORTFOLIO_MILESTONE = "portfolio_milestone"
    NEW_EQUITY_HIGH = "new_equity_high"
    CONCENTRATION_RISK = "concentration_risk"


class NotificationPriority:
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationService:
    """
    Comprehensive notification service that handles database notifications,
    multi-channel delivery, and user preferences.
    """
    
    def __init__(self):
        self.priority_channels = {
            NotificationPriority.CRITICAL: ["database", "email", "sms", "push"],
            NotificationPriority.HIGH: ["database", "email", "push"],
            NotificationPriority.NORMAL: ["database", "push"],
            NotificationPriority.LOW: ["database"]
        }
        
    def create_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        notification_type: str,
        priority: str = NotificationPriority.NORMAL,
        category: Optional[str] = None,
        metadata: Optional[Dict] = None,
        db: Optional[Session] = None
    ) -> Notification:
        """
        Create a new database notification.
        
        Args:
            user_id: User ID to send notification to
            title: Notification title
            message: Notification message body
            notification_type: Type of notification (from NotificationTypes)
            priority: Priority level (from NotificationPriority)
            category: Optional category for grouping
            metadata: Optional metadata dictionary
            db: Database session (optional)
            
        Returns:
            Created Notification object
        """
        if db is None:
            db = next(get_db())
            
        try:
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                type=notification_type,
                priority=priority,
                category=category,
                is_read=False,
                created_at=datetime.utcnow()
            )
            
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            logger.info(
                f"✅ Created notification: {notification_type} for user {user_id}"
            )
            
            return notification
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to create notification: {e}")
            raise
    
    async def send_multi_channel_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        notification_type: str,
        priority: str = NotificationPriority.NORMAL,
        channels: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
        db: Optional[Session] = None
    ) -> Dict[str, bool]:
        """
        Send notification via multiple channels based on priority and user preferences.
        
        Returns:
            Dictionary with channel success status
        """
        if db is None:
            db = next(get_db())
            
        results = {}
        
        try:
            # Always create database notification
            db_notification = self.create_notification(
                user_id=user_id,
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority,
                metadata=metadata,
                db=db
            )
            results["database"] = True
            
            # Get user details for external channels
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found for notification")
                return results
            
            # Determine channels based on priority if not specified
            if channels is None:
                channels = self.priority_channels.get(priority, ["database"])
            
            # Send via external channels
            if "email" in channels and user.email:
                try:
                    email_success = send_notification_email(
                        subject=title,
                        body=message,
                        recipient_email=user.email
                    )
                    results["email"] = email_success
                except Exception as e:
                    logger.error(f"Email notification failed: {e}")
                    results["email"] = False
            
            if "sms" in channels and user.phone_number:
                try:
                    # Create shorter message for SMS
                    sms_message = f"{title}: {message[:120]}..."
                    sms_success = send_trade_sms(
                        message=sms_message,
                        recipient_number=user.phone_number
                    )
                    results["sms"] = sms_success
                except Exception as e:
                    logger.error(f"SMS notification failed: {e}")
                    results["sms"] = False
            
            # Note: Push notifications would be handled by WebSocket service
            if "push" in channels:
                results["push"] = True  # Placeholder for WebSocket push
            
            logger.info(
                f"📤 Multi-channel notification sent: {notification_type} "
                f"for user {user_id} via {list(results.keys())}"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Multi-channel notification failed: {e}")
            return {"error": True, "message": str(e)}
    
    def create_trading_notification(
        self,
        user_id: int,
        notification_type: str,
        symbol: str,
        data: Dict,
        db: Optional[Session] = None
    ) -> Notification:
        """
        Create trading-specific notifications with standardized formatting.
        
        Args:
            user_id: User ID
            notification_type: Type from NotificationTypes
            symbol: Trading symbol (e.g., "RELIANCE", "NIFTY")
            data: Dictionary with trading data (price, quantity, pnl, etc.)
            db: Database session
        """
        templates = {
            NotificationTypes.ORDER_EXECUTED: {
                "title": "✅ Order Executed",
                "message": "Order executed: {symbol} {quantity} shares @ ₹{price}",
                "priority": NotificationPriority.HIGH
            },
            NotificationTypes.STOP_LOSS_HIT: {
                "title": "🔴 Stop Loss Triggered",
                "message": "Stop Loss hit: {symbol} @ ₹{price} - Loss: ₹{loss}",
                "priority": NotificationPriority.CRITICAL
            },
            NotificationTypes.TARGET_REACHED: {
                "title": "🎯 Target Achieved",
                "message": "Target reached: {symbol} @ ₹{price} - Profit: ₹{profit}",
                "priority": NotificationPriority.HIGH
            },
            NotificationTypes.MARGIN_CALL: {
                "title": "⚠️ MARGIN CALL",
                "message": "Available margin ₹{available} below required ₹{required}",
                "priority": NotificationPriority.CRITICAL
            },
            NotificationTypes.POSITION_OPENED: {
                "title": "🎯 Position Opened",
                "message": "New position: {symbol} {quantity} shares @ ₹{price}",
                "priority": NotificationPriority.NORMAL
            },
            NotificationTypes.POSITION_CLOSED: {
                "title": "💰 Position Closed",
                "message": "Position closed: {symbol} - P&L: ₹{pnl}",
                "priority": NotificationPriority.HIGH
            }
        }
        
        template = templates.get(notification_type)
        if not template:
            # Generic template for unknown types
            template = {
                "title": f"📊 {notification_type.replace('_', ' ').title()}",
                "message": f"{symbol}: {data}",
                "priority": NotificationPriority.NORMAL
            }
        
        # Format message with data
        try:
            formatted_message = template["message"].format(symbol=symbol, **data)
        except KeyError as e:
            logger.warning(f"Missing template data for {notification_type}: {e}")
            formatted_message = f"{symbol}: {str(data)}"
        
        return self.send_multi_channel_notification(
            user_id=user_id,
            title=template["title"],
            message=formatted_message,
            notification_type=notification_type,
            priority=template["priority"],
            metadata={"symbol": symbol, **data},
            db=db
        )
    
    def create_token_expiry_notification(
        self,
        user_id: int,
        broker_name: str,
        hours_remaining: float,
        db: Optional[Session] = None
    ) -> Dict[str, bool]:
        """
        Create token expiry notification with appropriate urgency.
        
        Args:
            user_id: User ID
            broker_name: Name of broker (e.g., "Upstox", "Angel One")
            hours_remaining: Hours until token expires
            db: Database session
        """
        if hours_remaining <= 0:
            # Token expired - critical alert
            return self.send_multi_channel_notification(
                user_id=user_id,
                title=f"🔴 {broker_name} Token Expired",
                message=(
                    f"Your {broker_name} token has expired. All trading for this "
                    "broker is now disabled. Please reconnect immediately."
                ),
                notification_type=NotificationTypes.TOKEN_EXPIRED,
                priority=NotificationPriority.CRITICAL,
                channels=["database", "email", "sms", "push"],
                metadata={"broker_name": broker_name, "hours_remaining": hours_remaining},
                db=db
            )
        elif hours_remaining <= 2:
            # Critical - expires very soon
            return self.send_multi_channel_notification(
                user_id=user_id,
                title=f"🚨 {broker_name} Token Expiring Soon",
                message=(
                    f"URGENT: Your {broker_name} token expires in {hours_remaining:.1f} "
                    "hours. Reconnect now to avoid trading disruption."
                ),
                notification_type=NotificationTypes.TOKEN_EXPIRING_SOON,
                priority=NotificationPriority.CRITICAL,
                channels=["database", "email", "sms", "push"],
                metadata={"broker_name": broker_name, "hours_remaining": hours_remaining},
                db=db
            )
        elif hours_remaining <= 12:
            # High priority warning
            return self.send_multi_channel_notification(
                user_id=user_id,
                title=f"🟡 {broker_name} Token Expiring",
                message=(
                    f"Your {broker_name} token expires in {hours_remaining:.0f} hours. "
                    "Please reconnect to avoid interruption."
                ),
                notification_type=NotificationTypes.TOKEN_EXPIRING_SOON,
                priority=NotificationPriority.HIGH,
                channels=["database", "email", "push"],
                metadata={"broker_name": broker_name, "hours_remaining": hours_remaining},
                db=db
            )
        else:
            # Normal reminder
            return self.send_multi_channel_notification(
                user_id=user_id,
                title=f"ℹ️ {broker_name} Token Reminder",
                message=(
                    f"Your {broker_name} token expires in {hours_remaining:.0f} hours. "
                    "Consider reconnecting soon."
                ),
                notification_type=NotificationTypes.TOKEN_EXPIRING_SOON,
                priority=NotificationPriority.NORMAL,
                channels=["database", "push"],
                metadata={"broker_name": broker_name, "hours_remaining": hours_remaining},
                db=db
            )
    
    def get_user_notifications(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
        notification_type: Optional[str] = None,
        is_read: Optional[bool] = None,
        priority: Optional[str] = None,
        db: Optional[Session] = None
    ) -> List[Notification]:
        """
        Retrieve user notifications with filtering options.
        """
        if db is None:
            db = next(get_db())
        
        query = db.query(Notification).filter(Notification.user_id == user_id)
        
        if notification_type:
            query = query.filter(Notification.type == notification_type)
        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)
        if priority:
            query = query.filter(Notification.priority == priority)
        
        return (
            query.order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    def mark_notification_read(
        self,
        notification_id: int,
        user_id: int,
        db: Optional[Session] = None
    ) -> bool:
        """Mark a notification as read."""
        if db is None:
            db = next(get_db())
            
        try:
            notification = db.query(Notification).filter(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                )
            ).first()
            
            if notification:
                notification.is_read = True
                notification.read_at = datetime.utcnow()
                db.commit()
                return True
            return False
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to mark notification as read: {e}")
            return False
    
    def mark_all_notifications_read(
        self,
        user_id: int,
        db: Optional[Session] = None
    ) -> int:
        """Mark all user notifications as read. Returns count of updated notifications."""
        if db is None:
            db = next(get_db())
            
        try:
            updated_count = (
                db.query(Notification)
                .filter(
                    and_(
                        Notification.user_id == user_id,
                        Notification.is_read == False
                    )
                )
                .update({
                    "is_read": True,
                    "read_at": datetime.utcnow()
                })
            )
            db.commit()
            return updated_count
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to mark all notifications as read: {e}")
            return 0
    
    def get_unread_count(self, user_id: int, db: Optional[Session] = None) -> int:
        """Get count of unread notifications for a user."""
        if db is None:
            db = next(get_db())
            
        return (
            db.query(Notification)
            .filter(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            )
            .count()
        )
    
    def delete_notification(
        self,
        notification_id: int,
        user_id: int,
        db: Optional[Session] = None
    ) -> bool:
        """Delete a notification."""
        if db is None:
            db = next(get_db())
            
        try:
            notification = db.query(Notification).filter(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                )
            ).first()
            
            if notification:
                db.delete(notification)
                db.commit()
                return True
            return False
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to delete notification: {e}")
            return False
    
    def cleanup_old_notifications(
        self,
        days_old: int = 30,
        db: Optional[Session] = None
    ) -> int:
        """
        Clean up notifications older than specified days.
        Returns count of deleted notifications.
        """
        if db is None:
            db = next(get_db())
            
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        try:
            deleted_count = (
                db.query(Notification)
                .filter(Notification.created_at < cutoff_date)
                .delete()
            )
            db.commit()
            
            logger.info(f"🧹 Cleaned up {deleted_count} old notifications")
            return deleted_count
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to cleanup notifications: {e}")
            return 0


# Global notification service instance
notification_service = NotificationService()