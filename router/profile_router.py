from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import shutil
import os
from datetime import datetime
import uuid

from database.connection import get_db
from database.models import User, BrokerConfig, TradePerformance, UserCapital
from services.auth_service import get_current_user

# from services.profile_service import ProfileService  # Comment out if this doesn't exist

router = APIRouter(prefix="/api", tags=["User Profile"])


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    country_code: Optional[str] = None


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get user profile with complete information"""
    try:
        # Get broker accounts
        broker_accounts = (
            db.query(BrokerConfig).filter(BrokerConfig.user_id == current_user.id).all()
        )

        # Get basic trading stats
        trade_performance = (
            db.query(TradePerformance)
            .filter(TradePerformance.user_id == current_user.id)
            .all()
        )

        total_pnl = sum(trade.profit_loss or 0 for trade in trade_performance)
        today_pnl = sum(
            trade.profit_loss or 0
            for trade in trade_performance
            if trade.trade_time and trade.trade_time.date() == datetime.now().date()
        )

        return {
            "id": current_user.id,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "phone_number": current_user.phone_number,
            "country_code": current_user.country_code,
            "country": "India",
            "avatar": None,
            "isVerified": current_user.isVerified,
            "is_verified": current_user.isVerified,
            "isPremium": False,
            "created_at": (
                current_user.created_at.isoformat() if current_user.created_at else None
            ),
            "last_login": (
                current_user.last_login.isoformat() if current_user.last_login else None
            ),
            "totalBalance": 0,  # Calculate from actual balance if needed
            "todayPnl": today_pnl,
            "brokerAccounts": [
                {
                    "id": broker.id,
                    "broker_name": broker.broker_name,
                    "balance": 0,
                    "is_active": broker.is_active,
                    "created_at": (
                        broker.created_at.isoformat() if broker.created_at else None
                    ),
                }
                for broker in broker_accounts
            ],
            "twoFactorEnabled": False,
            "role": current_user.role or "trader",
            "is_active": current_user.is_active,
            "failed_login_attempts": current_user.failed_login_attempts or 0,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch profile: {str(e)}",
        )


@router.put("/profile")
async def update_profile(
    profile_data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user profile information"""
    try:
        # Update user fields
        if profile_data.full_name:
            current_user.full_name = profile_data.full_name
        if profile_data.phone_number:
            current_user.phone_number = profile_data.phone_number
        if profile_data.country_code:
            current_user.country_code = profile_data.country_code

        current_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(current_user)

        return {
            "message": "Profile updated successfully",
            "id": current_user.id,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "phone_number": current_user.phone_number,
            "country_code": current_user.country_code,
            "updated_at": current_user.updated_at.isoformat(),
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}",
        )


@router.get("/profile/stats")
async def get_trading_stats(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get user trading statistics"""
    try:
        # Get trading performance data
        trades = (
            db.query(TradePerformance)
            .filter(TradePerformance.user_id == current_user.id)
            .all()
        )

        if not trades:
            return {
                "totalPnL": 0,
                "totalTrades": 0,
                "winRate": 0,
                "activePositions": 0,
                "total_pnl": 0,
                "total_trades": 0,
                "successful_trades": 0,
                "win_rate": 0,
                "best_performing_stock": None,
                "last_trade_date": None,
                "recentActivity": [],
            }

        total_pnl = sum(trade.profit_loss or 0 for trade in trades)
        total_trades = len(trades)
        successful_trades = len([t for t in trades if (t.profit_loss or 0) > 0])
        win_rate = (successful_trades / total_trades * 100) if total_trades > 0 else 0
        active_positions = len([t for t in trades if t.status == "OPEN"])

        # Get best performing stock
        stock_performance = {}
        for trade in trades:
            if trade.profit_loss:
                if trade.symbol not in stock_performance:
                    stock_performance[trade.symbol] = 0
                stock_performance[trade.symbol] += trade.profit_loss

        best_stock = (
            max(stock_performance.items(), key=lambda x: x[1])[0]
            if stock_performance
            else None
        )
        last_trade_date = max(
            [t.trade_time for t in trades if t.trade_time], default=None
        )

        return {
            "totalPnL": total_pnl,
            "totalTrades": total_trades,
            "winRate": win_rate,
            "activePositions": active_positions,
            "total_pnl": total_pnl,
            "total_trades": total_trades,
            "successful_trades": successful_trades,
            "win_rate": win_rate,
            "best_performing_stock": best_stock,
            "last_trade_date": last_trade_date.isoformat() if last_trade_date else None,
            "recentActivity": [
                {
                    "description": f"{trade.trade_type} {trade.symbol} - {trade.status}",
                    "timestamp": (
                        trade.trade_time.isoformat() if trade.trade_time else None
                    ),
                }
                for trade in trades[-5:]  # Last 5 trades
            ],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch trading stats: {str(e)}",
        )


@router.post("/profile/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change user password"""
    try:
        if password_data.new_password != password_data.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New passwords do not match",
            )

        # Verify current password
        if not current_user.verify_password(password_data.current_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        # Update password
        current_user.set_password(password_data.new_password)
        current_user.updated_at = datetime.utcnow()
        db.commit()

        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to change password: {str(e)}",
        )


@router.post("/profile/upload-avatar")
async def upload_avatar(
    avatar: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload user avatar image"""
    try:
        # Validate file
        if not avatar.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image"
            )

        if avatar.size > 5 * 1024 * 1024:  # 5MB limit
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size must be less than 5MB",
            )

        # Create upload directory if it doesn't exist
        upload_dir = "uploads/avatars"
        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename
        file_extension = avatar.filename.split(".")[-1]
        filename = f"{current_user.id}_{uuid.uuid4().hex}.{file_extension}"
        file_path = os.path.join(upload_dir, filename)

        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(avatar.file, buffer)

        avatar_url = f"/uploads/avatars/{filename}"

        return {"avatarUrl": avatar_url, "message": "Avatar uploaded successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload avatar: {str(e)}",
        )


# Add placeholder endpoints for notifications and API keys if your frontend needs them
@router.get("/profile/notifications")
async def get_notifications(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get user notifications - placeholder implementation"""
    return {
        "notifications": [],
        "unread_count": 0,
        "message": "Notifications feature not implemented yet",
    }


@router.patch("/profile/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark notification as read - placeholder implementation"""
    return {"message": f"Notification {notification_id} marked as read"}


@router.get("/profile/api-keys")
async def get_api_keys(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get user API keys - placeholder implementation"""
    return {"api_keys": [], "message": "API keys feature not implemented yet"}


@router.post("/profile/api-keys")
async def generate_api_key(
    key_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate new API key - placeholder implementation"""
    return {
        "api_key": "placeholder_key",
        "message": "API key generation not implemented yet",
    }


@router.delete("/profile/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete API key - placeholder implementation"""
    return {"message": f"API key {key_id} deletion not implemented yet"}
