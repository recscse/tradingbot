# services/angel_service.py
"""
Angel One Broker Integration Service
Handles authentication, token exchange, and API interactions with Angel One
"""
import os
import json
import logging
from urllib.parse import urlencode
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import HTTPException
from pydantic import BaseModel

# Configure logging
logger = logging.getLogger(__name__)

# Base URL for Angel One API
ANGEL_BASE_URL = "https://apiconnect.angelone.in"

# Common headers for Angel One API requests
COMMON_HEADERS = {
    "X-UserType": "USER",
    "X-SourceID": "WEB",
    "X-ClientLocalIP": "127.0.0.1",  # Can be configured via env vars
    "X-ClientPublicIP": "127.0.0.1",  # Can be configured via env vars
    "X-MACAddress": "00:00:00:00:00:00",  # Can be configured via env vars
    "X-PrivateKey": os.getenv("ANGEL_API_KEY"),
}


class AngelAuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    feed_token: str
    access_token_expiry: datetime
    client_code: str


def generate_angel_auth_url(api_key: str, user_id: str = None) -> str:
    """
    Generate the Angel One authentication URL for OAuth flow
    """
    base_url = "https://smartapi.angelone.in/publisher-login"
    params = {
        "api_key": api_key,
        "state": user_id or "",
    }
    return f"{base_url}?{urlencode(params)}"


def exchange_angel_token(code: str, client_code: str) -> Dict:
    """
    Exchange authorization code for access tokens
    """
    try:
        payload = {
            "clientCode": client_code,
            "code": code,
        }

        headers = {
            **COMMON_HEADERS,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        response = requests.post(
            f"{ANGEL_BASE_URL}/rest/auth/angelbroking/user/v1/loginByCode",
            json=payload,
            headers=headers,
            timeout=10,
        )

        if response.status_code != 200:
            logger.error(f"Angel token exchange failed: {response.text}")
            raise HTTPException(
                status_code=400, detail=f"Token exchange failed: {response.text}"
            )

        data = response.json().get("data")
        if not data:
            logger.error("No token data returned from Angel One")
            raise HTTPException(
                status_code=400, detail="No token data returned from Angel One"
            )

        return {
            "access_token": data["jwtToken"],
            "refresh_token": data.get("refreshToken"),
            "feed_token": data.get("feedToken"),
            "access_token_expiry": datetime.now() + timedelta(hours=24),
            "client_code": client_code,
        }

    except requests.RequestException as e:
        logger.error(f"Angel token exchange request failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to exchange Angel One token: {str(e)}"
        )


def login_with_password(client_code: str, password: str, totp: str) -> Dict:
    """
    Authenticate with Angel One using client code, password and TOTP
    """
    try:
        payload = {"clientcode": client_code, "password": password, "totp": totp}

        headers = {
            **COMMON_HEADERS,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        response = requests.post(
            f"{ANGEL_BASE_URL}/rest/auth/angelbroking/user/v1/loginByPassword",
            json=payload,
            headers=headers,
            timeout=10,
        )

        if response.status_code != 200:
            logger.error(f"Angel login failed: {response.text}")
            raise HTTPException(
                status_code=400, detail=f"Login failed: {response.text}"
            )

        data = response.json().get("data")
        if not data:
            logger.error("No data returned from Angel login")
            raise HTTPException(
                status_code=400, detail="No data returned from Angel login"
            )

        return {
            "access_token": data["jwtToken"],
            "refresh_token": data.get("refreshToken"),
            "feed_token": data.get("feedToken"),
            "access_token_expiry": datetime.now() + timedelta(hours=24),
            "client_code": client_code,
        }

    except requests.RequestException as e:
        logger.error(f"Angel login request failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to login to Angel One: {str(e)}"
        )


def refresh_angel_token(refresh_token: str) -> Dict:
    """
    Refresh expired Angel One access token using refresh token
    """
    try:
        payload = {"refreshToken": refresh_token}

        headers = {
            **COMMON_HEADERS,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        response = requests.post(
            f"{ANGEL_BASE_URL}/rest/auth/angelbroking/jwt/v1/generateTokens",
            json=payload,
            headers=headers,
            timeout=10,
        )

        if response.status_code != 200:
            logger.error(f"Angel token refresh failed: {response.text}")
            raise HTTPException(
                status_code=400, detail=f"Token refresh failed: {response.text}"
            )

        data = response.json().get("data")
        if not data:
            logger.error("No token data returned from Angel refresh")
            raise HTTPException(
                status_code=400, detail="No token data returned from Angel refresh"
            )

        return {
            "access_token": data["jwtToken"],
            "refresh_token": data.get("refreshToken"),
            "feed_token": data.get("feedToken"),
            "access_token_expiry": datetime.now() + timedelta(hours=24),
        }

    except requests.RequestException as e:
        logger.error(f"Angel token refresh request failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to refresh Angel One token: {str(e)}"
        )


def get_angel_profile(access_token: str) -> Dict:
    """
    Get user profile from Angel One
    """
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "00:00:00:00:00:00",
            "X-PrivateKey": os.getenv(
                "ANGEL_API_KEY"
            ),  # ✅ Make sure this env var is set correctly
        }

        response = requests.get(
            f"{ANGEL_BASE_URL}/rest/secure/angelbroking/user/v1/getProfile",
            headers=headers,
            timeout=10,
        )

        if response.status_code != 200:
            logger.error(f"Angel profile fetch failed: {response.text}")
            raise HTTPException(
                status_code=400, detail=f"Profile fetch failed: {response.text}"
            )

        return response.json()

    except requests.RequestException as e:
        logger.error(f"Angel profile request failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch Angel One profile: {str(e)}"
        )

    except requests.RequestException as e:
        logger.error(f"Angel profile request failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch Angel One profile: {str(e)}"
        )


def verify_angel_credentials(credentials: Dict) -> Dict:
    """
    Verify Angel One credentials either via OAuth or direct login
    """
    try:
        # If using OAuth flow
        if "code" in credentials and "client_code" in credentials:
            return exchange_angel_token(
                code=credentials["code"], client_code=credentials["client_code"]
            )

        # If using direct login
        elif all(k in credentials for k in ["client_code", "password", "totp"]):
            return login_with_password(
                client_code=credentials["client_code"],
                password=credentials["password"],
                totp=credentials["totp"],
            )

        else:
            raise HTTPException(
                status_code=400, detail="Invalid credential format for Angel One"
            )

    except Exception as e:
        logger.error(f"Angel credential verification failed: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Angel One credential verification failed: {str(e)}",
        )
