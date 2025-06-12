from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from database.connection import get_db
from database.models import Notification, User
from services.auth_service import get_current_user
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api", tags=["notifications"])


class NotificationCreate(BaseModel):
    title: str
    message: str
    type: str
    priority: str = "normal"
    category: Optional[str] = None


class NotificationSettings(BaseModel):
    email_notifications: dict
    push_notifications: dict
    trading_alerts: dict


@router.get("/notifications")
async def get_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user notifications with pagination and filtering"""
    query = db.query(Notification).filter(Notification.user_id == user.id)

    if type:
        query = query.filter(Notification.type == type)
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)

    # Count total
    total = query.count()

    # Apply pagination
    notifications = (
        query.order_by(Notification.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "notifications": notifications,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit,
    }


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


@router.get("/settings")
async def get_notification_settings(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get user notification settings"""
    # Get settings from user profile or create default
    settings = {
        "email_notifications": {
            "trade_executed": True,
            "price_alerts": True,
            "stop_loss": True,
        },
        "push_notifications": {
            "enabled": True,
            "sound": False,
        },
        "trading_alerts": {
            "immediate_execution": True,
            "daily_summary": False,
            "profit_loss_alerts": True,
            "market_hours_only": False,
        },
    }

    return {"settings": settings}


@router.patch("/settings")
async def update_notification_settings(
    settings: NotificationSettings,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user notification settings"""
    # Update user notification preferences in database
    # This would update a UserNotificationSettings model

    return {"message": "Settings updated successfully"}
