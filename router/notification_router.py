from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from database.connection import get_db
from database.models import Notification, User, UserNotificationPreferences
from services.auth_service import get_current_user
from services.notification_service import (
    notification_service,
    NotificationTypes,
    NotificationPriority,
)
from services.token_monitor_service import token_monitor_service
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ================== SCHEMAS ==================
class NotificationCreate(BaseModel):
    title: str
    message: str
    type: str
    priority: str = NotificationPriority.NORMAL
    category: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationPreferencesUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    email_types: Optional[Dict[str, bool]] = None
    sms_types: Optional[Dict[str, bool]] = None
    push_types: Optional[Dict[str, bool]] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_start_time: Optional[str] = None
    quiet_end_time: Optional[str] = None
    max_emails_per_hour: Optional[int] = None
    max_sms_per_day: Optional[int] = None
    max_push_per_hour: Optional[int] = None
    critical_override_quiet_hours: Optional[bool] = None
    critical_override_limits: Optional[bool] = None


class TestNotificationRequest(BaseModel):
    type: str
    channel: str = "all"  # all, email, sms, push


class TradingNotificationRequest(BaseModel):
    symbol: str
    notification_type: str
    data: Dict[str, Any]


# ================== NOTIFICATIONS ==================
@router.get("")
async def get_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    priority: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user notifications with enhanced pagination and filtering"""
    try:
        notifications = notification_service.get_user_notifications(
            user_id=user.id,
            limit=limit,
            offset=(page - 1) * limit,
            notification_type=type,
            is_read=is_read,
            priority=priority,
            db=db,
        )

        # Get total count for pagination
        query = db.query(Notification).filter(Notification.user_id == user.id)
        if type:
            query = query.filter(Notification.type == type)
        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)
        if priority:
            query = query.filter(Notification.priority == priority)

        total = query.count()
        unread_count = notification_service.get_unread_count(user.id, db)

        return {
            "notifications": [
                {
                    "id": n.id,
                    "title": n.title,
                    "message": n.message,
                    "type": n.type,
                    "priority": n.priority,
                    "category": n.category,
                    "is_read": n.is_read,
                    "created_at": n.created_at,
                    "read_at": n.read_at,
                }
                for n in notifications
            ],
            "total": total,
            "unread_count": unread_count,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch notifications: {str(e)}"
        )


@router.patch("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a notification as read"""
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user.id)
        .first()
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()

    return {"message": "Notification marked as read"}


@router.patch("/mark-all-read")
async def mark_all_notifications_as_read(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Mark all notifications as read"""
    db.query(Notification).filter(
        Notification.user_id == user.id, Notification.is_read == False
    ).update({"is_read": True, "read_at": datetime.utcnow()})
    db.commit()

    return {"message": "All notifications marked as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a notification"""
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user.id)
        .first()
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    db.delete(notification)
    db.commit()

    return {"message": "Notification deleted"}


# ================== PREFERENCES ==================
@router.get("/preferences")
async def get_notification_preferences(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get user notification preferences"""
    preferences = (
        db.query(UserNotificationPreferences)
        .filter(UserNotificationPreferences.user_id == user.id)
        .first()
    )

    if not preferences:
        preferences = UserNotificationPreferences(user_id=user.id)
        db.add(preferences)
        db.commit()
        db.refresh(preferences)

    return {
        "email_enabled": preferences.email_enabled,
        "sms_enabled": preferences.sms_enabled,
        "push_enabled": preferences.push_enabled,
        "email_types": preferences.email_types,
        "sms_types": preferences.sms_types,
        "push_types": preferences.push_types,
        "quiet_hours_enabled": preferences.quiet_hours_enabled,
        "quiet_start_time": preferences.quiet_start_time,
        "quiet_end_time": preferences.quiet_end_time,
        "max_emails_per_hour": preferences.max_emails_per_hour,
        "max_sms_per_day": preferences.max_sms_per_day,
        "max_push_per_hour": preferences.max_push_per_hour,
        "critical_override_quiet_hours": preferences.critical_override_quiet_hours,
        "critical_override_limits": preferences.critical_override_limits,
    }


@router.patch("/preferences")
async def update_notification_preferences(
    preferences_update: NotificationPreferencesUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user notification preferences"""
    preferences = (
        db.query(UserNotificationPreferences)
        .filter(UserNotificationPreferences.user_id == user.id)
        .first()
    )

    if not preferences:
        preferences = UserNotificationPreferences(user_id=user.id)
        db.add(preferences)

    update_data = preferences_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(preferences, field, value)

    preferences.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Notification preferences updated successfully"}


# ================== TOKEN STATUS ==================
@router.get("/tokens/status")
async def get_token_status(user: User = Depends(get_current_user)):
    """Get token expiry status for current user"""
    try:
        summary = await token_monitor_service.get_expiring_tokens_summary(
            user_id=user.id
        )

        return {
            "expired_tokens": summary["expired"],
            "critical_tokens": summary["critical"],
            "high_priority_tokens": summary["high"],
            "normal_tokens": summary["normal"],
            "reminder_tokens": summary["reminder"],
            "summary": {
                "total_expired": len(summary["expired"]),
                "total_expiring_soon": len(summary["critical"]) + len(summary["high"]),
                "needs_attention": len(summary["expired"]) + len(summary["critical"])
                > 0,
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get token status: {str(e)}"
        )


@router.post("/tokens/refresh")
async def refresh_expired_tokens(user: User = Depends(get_current_user)):
    """Attempt to refresh expired tokens"""
    try:
        results = await token_monitor_service.refresh_expired_tokens(user_id=user.id)
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        return {
            "message": f"Token refresh completed: {success_count}/{total_count} successful",
            "results": results,
            "success_count": success_count,
            "total_count": total_count,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to refresh tokens: {str(e)}"
        )
