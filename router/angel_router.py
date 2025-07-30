# routes/angel_router.py
import os
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

import requests
from pydantic import BaseModel
from typing import Dict, Optional

from database.connection import get_db
from database.models import BrokerConfig, User
from router.broker_router import BrokerAuthRequest
from services.angel_service import (
    generate_angel_auth_url,
    exchange_angel_token,
    verify_angel_credentials,
    get_angel_profile,
)
from services.auth_service import get_current_user

logger = logging.getLogger(__name__)

angel_router = APIRouter(tags=["Angel One Integration"])


@angel_router.post("/init-auth")
def initiate_upstox_auth(data: dict, user_id: int = Depends(get_current_user)):
    client_id = data.get("config").get("api_key")
    api_secret = data.get("config").get("api_secret")
    if not client_id:
        raise HTTPException(status_code=400, detail="Missing api_key")
    state = str(user_id.id)
    auth_url = generate_angel_auth_url(client_id, user_id.id)
    return {"auth_url": auth_url}


@angel_router.get("/callback")
def angel_callback(
    auth_token: str = Query(..., description="JWT auth token from Angel One"),
    feed_token: str = Query(..., description="Feed token for real-time data"),
    refresh_token: str = Query(..., description="Refresh token for token renewal"),
    db: Session = Depends(get_db),
):
    """
    Handle Angel One OAuth callback and save tokens
    """
    try:
        # Validate required parameters
        if not auth_token or not feed_token or not refresh_token:
            raise HTTPException(
                status_code=400,
                detail="Missing required tokens: auth_token, feed_token, or refresh_token",
            )

        # Decode and validate the auth token to get user info
        try:
            decoded_token = decode_angel_jwt(auth_token)
            client_code = decoded_token.get("username")  # Use username as client code

            # Get user profile using the service function
            profile = get_angel_profile(auth_token)

        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid auth token: {str(e)}")

        # Calculate token expiry (typically JWT exp field)
        try:
            import jwt

            decoded = jwt.decode(auth_token, options={"verify_signature": False})
            token_expiry = (
                datetime.fromtimestamp(decoded["exp"]) if "exp" in decoded else None
            )
        except:
            # Default expiry if we can't decode
            token_expiry = datetime.now() + timedelta(hours=8)

        # ✅ FIX: Get the user properly
        user = db.query(User).first()
        if not user:
            raise HTTPException(status_code=404, detail="No user found")

        client_code = client_code or "default_client_code"  # Fallback if not found
        api_key = os.getenv("ANGEL_API_KEY", "default_api_key")
        api_secret = os.getenv("ANGEL_API_SECRET", "default_api_secret")

        # Check if broker config already exists for this user
        existing_config = (
            db.query(BrokerConfig)
            .filter(
                BrokerConfig.user_id == user.id, BrokerConfig.broker_name == "Angel One"
            )
            .first()
        )

        if existing_config:
            # Update existing configuration
            existing_config.access_token = auth_token
            existing_config.refresh_token = refresh_token
            existing_config.feed_token = feed_token
            existing_config.access_token_expiry = token_expiry
            existing_config.client_id = client_code
            existing_config.api_key = api_key
            existing_config.api_secret = api_secret
            existing_config.is_active = True
            existing_config.config = {"profile": profile, "auth_method": "oauth"}
            existing_config.created_at = datetime.now()
        else:
            # Create new broker configuration
            broker_config = BrokerConfig(
                user_id=user.id,
                broker_name="Angel One",
                access_token=auth_token,
                api_key=api_key,
                api_secret=api_secret,
                refresh_token=refresh_token,
                feed_token=feed_token,
                access_token_expiry=token_expiry,
                client_id=client_code,
                is_active=True,
                config={
                    "profile": profile,
                    "auth_method": "oauth",
                },
            )
            db.add(broker_config)

        db.commit()

        # Return success response (could redirect to frontend)
        return {
            "message": "Angel One connected successfully",
            "profile": profile,
            "client_code": client_code,
            "token_expiry": token_expiry.isoformat() if token_expiry else None,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Angel One callback error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def decode_angel_jwt(token: str) -> dict:
    """
    Decode Angel One JWT token without verification
    You might need to implement proper verification based on Angel One's public key
    """
    try:
        import jwt

        # Decode without verification for now - implement proper verification in production
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
    except Exception as e:
        raise ValueError(f"Failed to decode JWT: {str(e)}")


# Additional helper function for token refresh
@angel_router.post("/refresh-token")
def refresh_angel_token(user_id: int, db: Session = Depends(get_db)):
    """
    Refresh Angel One access token using refresh token
    """
    try:
        broker_config = (
            db.query(BrokerConfig)
            .filter(
                BrokerConfig.user_id == user_id,
                BrokerConfig.broker_name == "Angel One",
                BrokerConfig.is_active == True,
            )
            .first()
        )

        if not broker_config:
            raise HTTPException(
                status_code=404, detail="Angel One configuration not found"
            )

        # Use refresh token to get new access token
        new_tokens = refresh_angel_access_token(broker_config.refresh_token)

        # Update the configuration
        broker_config.access_token = new_tokens["access_token"]
        broker_config.access_token_expiry = new_tokens["expiry"]
        broker_config.updated_at = datetime.now()

        db.commit()

        return {"message": "Token refreshed successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


def refresh_angel_access_token(refresh_token: str) -> dict:
    """
    Refresh Angel One access token
    """
    try:
        # Implement based on Angel One's token refresh API
        # This is a placeholder implementation
        headers = {"Content-Type": "application/json"}

        data = {"refreshToken": refresh_token}

        response = requests.post(
            "https://apiconnect.angelbroking.com/rest/auth/angelbroking/jwt/v1/generateTokens",
            headers=headers,
            json=data,
        )

        if response.status_code == 200:
            result = response.json()
            return {
                "access_token": result["data"]["jwtToken"],
                "expiry": datetime.now()
                + timedelta(hours=8),  # Adjust based on actual expiry
            }
        else:
            raise ValueError(f"Token refresh failed: {response.status_code}")

    except Exception as e:
        raise ValueError(f"Failed to refresh token: {str(e)}")


@angel_router.post("/connect")
def connect_angel(
    request: BrokerAuthRequest,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Connect Angel One account using direct credentials (client code, password, TOTP)
    """
    try:
        # Verify credentials
        tokens = verify_angel_credentials(request.credentials)

        # Get user profile
        profile = get_angel_profile(tokens["access_token"])

        # Save broker configuration
        broker_config = BrokerConfig(
            user_id=user_id,
            broker_name="Angel One",
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            feed_token=tokens["feed_token"],
            access_token_expiry=tokens["access_token_expiry"],
            client_id=request.credentials.get("client_code"),
            is_active=True,
            meta_data={"profile": profile, "auth_method": "direct"},
        )

        db.add(broker_config)
        db.commit()

        return {"message": "Angel One connected successfully", "profile": profile}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@angel_router.get("/profile")
def get_profile(
    user_id: int = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get Angel One user profile
    """
    try:
        # Get latest active broker config
        config = (
            db.query(BrokerConfig)
            .filter(
                BrokerConfig.user_id == user_id,
                BrokerConfig.broker_name == "Angel One",
                BrokerConfig.is_active == True,
            )
            .order_by(BrokerConfig.created_at.desc())
            .first()
        )

        if not config:
            raise HTTPException(
                status_code=404, detail="No active Angel One configuration found"
            )

        profile = get_angel_profile(config.access_token)
        return {"profile": profile}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
