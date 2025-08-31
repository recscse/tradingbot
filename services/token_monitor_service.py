"""
Token Expiry Monitoring Service

This service monitors broker token expiry times and sends proactive notifications
to users before their tokens expire, preventing trading disruptions.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.connection import get_db
from database.models import BrokerConfig, User, Notification
from services.notification_service import notification_service, NotificationTypes

logger = logging.getLogger(__name__)


class TokenMonitorService:
    """
    Service to monitor broker token expiry and send proactive notifications.
    """
    
    def __init__(self):
        self.monitoring_intervals = {
            "critical": timedelta(hours=2),    # 2 hours before expiry
            "high": timedelta(hours=12),       # 12 hours before expiry  
            "normal": timedelta(hours=48),     # 48 hours before expiry
            "reminder": timedelta(days=7)      # 7 days before expiry
        }
        
        self.notification_sent_flags = {}  # Track sent notifications to avoid spam
        
    async def monitor_all_tokens(self) -> Dict[str, int]:
        """
        Monitor all broker tokens and send notifications as needed.
        
        Returns:
            Dictionary with counts of notifications sent by priority level
        """
        db = next(get_db())
        results = {
            "critical": 0,
            "high": 0, 
            "normal": 0,
            "reminder": 0,
            "expired": 0,
            "errors": 0
        }
        
        try:
            # Get all active broker configurations with token expiry
            active_configs = (
                db.query(BrokerConfig)
                .filter(
                    and_(
                        BrokerConfig.is_active == True,
                        BrokerConfig.token_expiry.isnot(None)
                    )
                )
                .all()
            )
            
            logger.info(f"🔍 Monitoring {len(active_configs)} active broker configurations")
            
            for config in active_configs:
                try:
                    result = await self.check_token_expiry(config, db)
                    if result:
                        results[result] += 1
                        
                except Exception as e:
                    logger.error(f"❌ Error checking token for {config.broker_name}: {e}")
                    results["errors"] += 1
            
            logger.info(f"📊 Token monitoring results: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Token monitoring failed: {e}")
            results["errors"] += 1
            return results
        finally:
            db.close()
    
    async def check_token_expiry(
        self, 
        config: BrokerConfig, 
        db: Session
    ) -> Optional[str]:
        """
        Check individual broker config token expiry and send notifications.
        
        Args:
            config: BrokerConfig object
            db: Database session
            
        Returns:
            String indicating the priority level of notification sent, or None
        """
        if not config.token_expiry:
            return None
            
        now = datetime.utcnow()
        time_until_expiry = config.token_expiry - now
        hours_remaining = time_until_expiry.total_seconds() / 3600
        
        # Create unique key for tracking notifications
        notification_key = f"{config.user_id}_{config.broker_name}_{config.id}"
        
        try:
            if hours_remaining <= 0:
                # Token has expired
                await self.handle_expired_token(config, db)
                return "expired"
                
            elif hours_remaining <= 2:
                # Critical: expires in 2 hours
                if not self.was_notification_sent(notification_key, "critical"):
                    await notification_service.create_token_expiry_notification(
                        user_id=config.user_id,
                        broker_name=config.broker_name,
                        hours_remaining=hours_remaining,
                        db=db
                    )
                    self.mark_notification_sent(notification_key, "critical")
                    return "critical"
                    
            elif hours_remaining <= 12:
                # High priority: expires in 12 hours
                if not self.was_notification_sent(notification_key, "high"):
                    await notification_service.create_token_expiry_notification(
                        user_id=config.user_id,
                        broker_name=config.broker_name,
                        hours_remaining=hours_remaining,
                        db=db
                    )
                    self.mark_notification_sent(notification_key, "high")
                    return "high"
                    
            elif hours_remaining <= 48:
                # Normal priority: expires in 48 hours
                if not self.was_notification_sent(notification_key, "normal"):
                    await notification_service.create_token_expiry_notification(
                        user_id=config.user_id,
                        broker_name=config.broker_name,
                        hours_remaining=hours_remaining,
                        db=db
                    )
                    self.mark_notification_sent(notification_key, "normal")
                    return "normal"
                    
            elif hours_remaining <= 168:  # 7 days
                # Reminder: expires in 7 days
                if not self.was_notification_sent(notification_key, "reminder"):
                    await notification_service.create_token_expiry_notification(
                        user_id=config.user_id,
                        broker_name=config.broker_name,
                        hours_remaining=hours_remaining,
                        db=db
                    )
                    self.mark_notification_sent(notification_key, "reminder")
                    return "reminder"
                    
        except Exception as e:
            logger.error(f"❌ Error processing token expiry for {config.broker_name}: {e}")
            
        return None
    
    async def handle_expired_token(self, config: BrokerConfig, db: Session):
        """
        Handle expired token - disable broker and send critical notification.
        """
        try:
            # Disable the broker configuration
            config.is_active = False
            config.status = "token_expired"
            config.last_error = f"Token expired at {config.token_expiry}"
            
            db.commit()
            
            # Send critical notification
            await notification_service.send_multi_channel_notification(
                user_id=config.user_id,
                title=f"🔴 {config.broker_name} Token Expired - Trading Disabled",
                message=(
                    f"Your {config.broker_name} token has expired and all trading "
                    "for this broker has been automatically disabled. "
                    "Please reconnect immediately to resume trading."
                ),
                notification_type=NotificationTypes.TOKEN_EXPIRED,
                priority="critical",
                channels=["database", "email", "sms", "push"],
                metadata={
                    "broker_name": config.broker_name,
                    "broker_id": config.id,
                    "expired_at": config.token_expiry.isoformat(),
                    "auto_disabled": True
                },
                db=db
            )
            
            # Additional system notification for multiple expired tokens
            user_expired_count = (
                db.query(BrokerConfig)
                .filter(
                    and_(
                        BrokerConfig.user_id == config.user_id,
                        BrokerConfig.status == "token_expired",
                        BrokerConfig.token_expiry < datetime.utcnow()
                    )
                )
                .count()
            )
            
            if user_expired_count >= 2:
                # Multiple tokens expired - send additional alert
                expired_brokers = (
                    db.query(BrokerConfig.broker_name)
                    .filter(
                        and_(
                            BrokerConfig.user_id == config.user_id,
                            BrokerConfig.status == "token_expired"
                        )
                    )
                    .all()
                )
                
                broker_list = ", ".join([broker[0] for broker in expired_brokers])
                
                await notification_service.send_multi_channel_notification(
                    user_id=config.user_id,
                    title="🚨 Multiple Broker Tokens Expired",
                    message=(
                        f"Multiple broker tokens have expired: {broker_list}. "
                        "All automated trading has been suspended. "
                        "Please reconnect all brokers immediately."
                    ),
                    notification_type=NotificationTypes.MULTIPLE_TOKENS_EXPIRED,
                    priority="critical",
                    channels=["database", "email", "sms", "push"],
                    metadata={
                        "expired_brokers": broker_list,
                        "count": user_expired_count
                    },
                    db=db
                )
            
            logger.warning(
                f"⚠️ Disabled expired token: {config.broker_name} "
                f"for user {config.user_id}"
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to handle expired token: {e}")
            db.rollback()
    
    def was_notification_sent(self, key: str, priority: str) -> bool:
        """Check if notification was already sent for this key and priority."""
        full_key = f"{key}_{priority}"
        
        # Check if notification was sent in the last 24 hours
        if full_key in self.notification_sent_flags:
            sent_time = self.notification_sent_flags[full_key]
            if datetime.utcnow() - sent_time < timedelta(hours=24):
                return True
        
        return False
    
    def mark_notification_sent(self, key: str, priority: str):
        """Mark notification as sent for this key and priority."""
        full_key = f"{key}_{priority}"
        self.notification_sent_flags[full_key] = datetime.utcnow()
        
        # Clean up old entries to prevent memory leak
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        self.notification_sent_flags = {
            k: v for k, v in self.notification_sent_flags.items() 
            if v > cutoff_time
        }
    
    async def get_expiring_tokens_summary(
        self, 
        user_id: Optional[int] = None
    ) -> Dict[str, List[Dict]]:
        """
        Get summary of tokens expiring in different time windows.
        
        Args:
            user_id: Optional user ID to filter results
            
        Returns:
            Dictionary with expiring tokens grouped by urgency
        """
        db = next(get_db())
        summary = {
            "expired": [],
            "critical": [],  # < 2 hours
            "high": [],      # < 12 hours
            "normal": [],    # < 48 hours
            "reminder": []   # < 7 days
        }
        
        try:
            query = db.query(BrokerConfig).filter(
                and_(
                    BrokerConfig.token_expiry.isnot(None)
                )
            )
            
            if user_id:
                query = query.filter(BrokerConfig.user_id == user_id)
            
            configs = query.all()
            now = datetime.utcnow()
            
            for config in configs:
                time_until_expiry = config.token_expiry - now
                hours_remaining = time_until_expiry.total_seconds() / 3600
                
                token_info = {
                    "broker_name": config.broker_name,
                    "user_id": config.user_id,
                    "expires_at": config.token_expiry.isoformat(),
                    "hours_remaining": round(hours_remaining, 1),
                    "is_active": config.is_active
                }
                
                if hours_remaining <= 0:
                    summary["expired"].append(token_info)
                elif hours_remaining <= 2:
                    summary["critical"].append(token_info)
                elif hours_remaining <= 12:
                    summary["high"].append(token_info)
                elif hours_remaining <= 48:
                    summary["normal"].append(token_info)
                elif hours_remaining <= 168:  # 7 days
                    summary["reminder"].append(token_info)
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Failed to get expiring tokens summary: {e}")
            return summary
        finally:
            db.close()
    
    async def refresh_expired_tokens(self, user_id: int) -> Dict[str, bool]:
        """
        Attempt to refresh expired tokens for a user.
        This would integrate with broker APIs for automatic token refresh.
        
        Returns:
            Dictionary with refresh results per broker
        """
        results = {}
        db = next(get_db())
        
        try:
            expired_configs = (
                db.query(BrokerConfig)
                .filter(
                    and_(
                        BrokerConfig.user_id == user_id,
                        BrokerConfig.status == "token_expired",
                        BrokerConfig.token_expiry < datetime.utcnow()
                    )
                )
                .all()
            )
            
            for config in expired_configs:
                try:
                    # This would integrate with actual broker APIs
                    # For now, we'll just log the attempt
                    logger.info(
                        f"🔄 Attempting to refresh token for {config.broker_name}"
                    )
                    
                    # Placeholder for actual token refresh logic
                    # success = await refresh_broker_token(config)
                    success = False  # Placeholder
                    
                    results[config.broker_name] = success
                    
                    if success:
                        # Update config status
                        config.is_active = True
                        config.status = "active"
                        config.last_error = None
                        # config.token_expiry would be updated with new expiry
                        
                        # Send success notification
                        await notification_service.send_multi_channel_notification(
                            user_id=user_id,
                            title=f"✅ {config.broker_name} Token Refreshed",
                            message=f"Your {config.broker_name} token has been successfully refreshed. Trading is now enabled.",
                            notification_type=NotificationTypes.TOKEN_REFRESHED,
                            priority="normal",
                            channels=["database", "push"],
                            db=db
                        )
                    else:
                        # Send failure notification
                        await notification_service.send_multi_channel_notification(
                            user_id=user_id,
                            title=f"❌ Failed to Refresh {config.broker_name} Token",
                            message=f"Unable to automatically refresh {config.broker_name} token. Manual reconnection required.",
                            notification_type=NotificationTypes.TOKEN_REFRESH_FAILED,
                            priority="high",
                            channels=["database", "email", "push"],
                            db=db
                        )
                        
                except Exception as e:
                    logger.error(f"❌ Token refresh failed for {config.broker_name}: {e}")
                    results[config.broker_name] = False
            
            db.commit()
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to refresh expired tokens: {e}")
            db.rollback()
            return results
        finally:
            db.close()


# Global token monitor service instance
token_monitor_service = TokenMonitorService()