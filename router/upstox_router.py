from datetime import datetime, timedelta
import os
import logging
from sqlalchemy.orm import Session
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import Dict, Optional
import requests
from database.connection import SessionLocal, get_db
from database.models import BrokerConfig, User
from services.auth_service import get_current_user
from services.upstox_service import (
    calculate_upstox_expiry,
    exchange_code_for_token,
    generate_upstox_auth_url,
)
from services.upstox_temp_store import (
    store_upstox_credentials_temp,
    get_upstox_credentials_temp,
    clear_upstox_credentials_temp,
)

logger = logging.getLogger(__name__)
db = SessionLocal()

# Initialize router without prefix
upstox_router = APIRouter()
UPSTOX_REDIRECT_URI = os.getenv("UPSTOX_REDIRECT_URI")


class UpstoxConfiguration(BaseModel):
    broker: str
    config: Dict[str, str]


@upstox_router.get("/status")
async def check_status():
    """
    Check Upstox connection status
    """
    # TODO: Implement status check logic
    return {"status": "operational"}


@upstox_router.post("/init-auth")
def initiate_upstox_auth(data: dict, user_id: int = Depends(get_current_user)):
    client_id = data.get("api_key")
    api_secret = data.get("api_secret")
    if not client_id:
        raise HTTPException(status_code=400, detail="Missing api_key")
    state = str(user_id.id)
    store_upstox_credentials_temp(state, client_id, api_secret)
    auth_url = generate_upstox_auth_url(client_id, user_id.id)
    return {"auth_url": auth_url}


# OAuth Callback Endpoint
@upstox_router.get("/callback")
def upstox_callback(code: str, state: str = None, db: Session = Depends(get_db)):
    try:
        user_id = int(state)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # ✅ Retrieve existing broker config if present
        existing_config = (
            db.query(BrokerConfig)
            .filter(
                BrokerConfig.user_id == user_id,
                BrokerConfig.broker_name.ilike("upstox"),
            )
            .first()
        )

        # ✅ Retrieve credentials: from DB or temp store
        if existing_config:
            creds = {
                "client_id": existing_config.api_key,
                "client_secret": existing_config.api_secret,
            }
        else:
            creds = get_upstox_credentials_temp(user_id)

        if not creds:
            raise HTTPException(status_code=400, detail="Missing temporary credentials")

        # ✅ Exchange code for tokens
        token_response = exchange_code_for_token(
            code, creds["client_id"], creds["client_secret"]
        )
        access_token_expiry = calculate_upstox_expiry()

        if existing_config:
            # 🔄 Update existing config
            existing_config.access_token = token_response["access_token"]
            existing_config.api_key = creds["client_id"]
            existing_config.api_secret = creds["client_secret"]
            existing_config.access_token_expiry = access_token_expiry
            existing_config.additional_params = token_response
            existing_config.is_active = token_response.get("is_active", True)
            existing_config.config = {
                "email": token_response.get("email"),
                "user_name": token_response.get("user_name"),
                "user_type": token_response.get("user_type"),
                "poa": token_response.get("poa"),
                "ddpi": token_response.get("ddpi"),
                "exchanges": token_response.get("exchanges"),
                "products": token_response.get("products"),
                "order_types": token_response.get("order_types"),
                "extended_token": token_response.get("extended_token"),
            }
        else:
            # 🆕 Create new config
            new_config = BrokerConfig(
                user_id=user_id,
                client_id=token_response["user_id"],
                broker_name=token_response["broker"],
                api_key=creds["client_id"],
                api_secret=creds["client_secret"],
                access_token=token_response["access_token"],
                access_token_expiry=access_token_expiry,
                created_at=datetime.now(),
                is_active=token_response.get("is_active", True),
                additional_params=token_response,
                config={
                    "email": token_response.get("email"),
                    "user_name": token_response.get("user_name"),
                    "user_type": token_response.get("user_type"),
                    "poa": token_response.get("poa"),
                    "ddpi": token_response.get("ddpi"),
                    "exchanges": token_response.get("exchanges"),
                    "products": token_response.get("products"),
                    "order_types": token_response.get("order_types"),
                    "extended_token": token_response.get("extended_token"),
                },
            )
            db.add(new_config)

        db.commit()
        clear_upstox_credentials_temp(user_id)

        logger.info(f"✅ Upstox linked successfully for user_id={user_id}")
        return {"message": "Upstox broker linked successfully."}

    except Exception as e:
        logger.exception(f"❌ Upstox callback failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@upstox_router.get("/token")
def get_upstox_token(current_user: User = Depends(get_current_user)):
    upstox_token = None

    for broker in current_user.brokers:
        if broker.broker_name.lower() == "upstox":
            upstox_token = broker.access_token  # or broker.upstox_access_token
            break

    if not upstox_token:
        return {"error": "No Upstox token found"}

    return {"access_token": upstox_token}


@upstox_router.post("/refresh/{broker_id}")
def refresh_upstox_token(broker_id: int, db: Session = Depends(get_db)):
    broker = db.query(BrokerConfig).filter(BrokerConfig.id == broker_id).first()

    if not broker:
        raise HTTPException(status_code=404, detail="Broker not found")

    if broker.broker_name.lower() != "upstox":
        raise HTTPException(
            status_code=400, detail="Token refresh only supported for Upstox"
        )

    if not broker.api_key or not broker.api_secret:
        raise HTTPException(status_code=400, detail="Missing Upstox credentials")

    # Generate OAuth2 auth URL again
    auth_url = generate_upstox_auth_url(api_key=broker.api_key, user_id=broker.user_id)

    # Return auth_url so frontend can open it in a popup
    return {"auth_url": auth_url}


@upstox_router.post("/automation/refresh-all")
async def automated_refresh_all_tokens(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Automated refresh of expired Upstox tokens
    - Admin users: Can refresh admin account token using API credentials from database
    - Regular users: Can only refresh their own tokens
    """
    try:
        from services.upstox_automation_service import UpstoxAutomationService
        
        automation_service = UpstoxAutomationService()
        
        # Check user role
        is_admin = current_user.role and current_user.role.lower() == "admin"
        
        if is_admin:
            logger.info(f"Admin user {current_user.id} triggered automated refresh for admin account")
            # Admin can refresh the admin account's token using admin's DB credentials
            result = await automation_service.refresh_admin_upstox_token()
        else:
            logger.info(f"Regular user {current_user.id} triggered automated refresh for own tokens")
            # Regular users can only refresh their own tokens
            result = await automation_service.refresh_user_tokens(current_user.id)
        
        return {
            "success": result["success"],
            "message": result.get("message", "Token refresh completed"),
            "user_role": current_user.role,
            "scope": "admin_account" if is_admin else "own_tokens",
            "details": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Automated refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@upstox_router.post("/automation/force-refresh")
async def force_immediate_refresh(db: Session = Depends(get_db)):
    """
    Force immediate token refresh for expired tokens - Emergency endpoint
    """
    try:
        from services.upstox_automation_service import UpstoxAutomationService
        
        logger.info("🚨 Emergency token refresh triggered via API")
        automation_service = UpstoxAutomationService()
        
        # Force refresh regardless of expiry time
        result = await automation_service.refresh_admin_upstox_token()
        
        # Also trigger WebSocket reconnection if available
        try:
            from services.centralized_ws_manager import CentralizedWebSocketManager
            ws_manager = CentralizedWebSocketManager()
            
            if ws_manager.admin_token:
                logger.info("🔄 Triggering WebSocket reconnection with new token...")
                await ws_manager._load_admin_token()  # Reload the new token
                ws_manager.reconnect_attempts = 0  # Reset retry counter
                ws_manager.connection_ready.clear()  # Force reconnect
                
        except Exception as ws_error:
            logger.warning(f"⚠️ Could not trigger WebSocket reconnection: {ws_error}")
        
        return {
            "success": result["success"],
            "message": f"Emergency refresh completed: {result.get('message', 'Token refreshed')}",
            "force_refresh": True,
            "details": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Emergency refresh failed: {e}")
        raise HTTPException(status_code=500, detail=f"Emergency refresh failed: {str(e)}")


@upstox_router.get("/automation/status")
async def get_automation_status(db: Session = Depends(get_db)):
    """
    Get status of Upstox automation system
    """
    try:
        from services.upstox_automation_service import get_upstox_scheduler
        
        # Get scheduler status
        scheduler = get_upstox_scheduler()
        
        # Count expired brokers
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        expired_count = db.query(BrokerConfig).filter(
            BrokerConfig.broker_name.ilike("upstox"),
            BrokerConfig.is_active == True,
            BrokerConfig.access_token_expiry <= tomorrow
        ).count()
        
        total_upstox = db.query(BrokerConfig).filter(
            BrokerConfig.broker_name.ilike("upstox")
        ).count()
        
        return {
            "success": True,
            "automation_enabled": True,
            "scheduler_running": scheduler.is_running,
            "total_upstox_brokers": total_upstox,
            "brokers_needing_refresh": expired_count,
            "next_scheduled_run": "04:00 AM daily",
            "credentials_configured": bool(
                os.getenv("UPSTOX_MOBILE") and 
                os.getenv("UPSTOX_PIN")
            ),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting automation status: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
