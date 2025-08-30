"""
Broker Profile Router
Unified API endpoints for broker profile and funds management
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from router.auth_router import get_current_user
from services.broker_profile_service import BrokerProfileService

logger = logging.getLogger(__name__)

broker_profile_router = APIRouter(
    prefix="/api/v1/broker-profile", tags=["Broker Profile"]
)


@broker_profile_router.get("/profile/{broker_name}")
async def get_broker_profile(
    broker_name: str = Path(..., description="Broker name (upstox, angel, dhan, etc.)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get user profile information for a specific broker

    Supported brokers:
    - upstox: Upstox broker profile with exchanges, products, order types
    - angel: Angel One broker profile (coming soon)
    - dhan: Dhan broker profile (coming soon)
    """
    try:
        service = BrokerProfileService(db)
        profile_data = service.get_user_broker_profile(current_user.id, broker_name)

        return {
            "success": True,
            "broker": broker_name.lower(),
            "user_id": current_user.id,
            **profile_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_broker_profile for {broker_name}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch {broker_name} profile: {str(e)}"
        )


@broker_profile_router.get("/funds/{broker_name}")
async def get_broker_funds(
    broker_name: str = Path(..., description="Broker name (upstox, angel, dhan, etc.)"),
    segment: Optional[str] = Query(
        None, description="Market segment: SEC for Equity, COM for Commodity"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get user funds and margin information for a specific broker

    Query Parameters:
    - segment: Optional market segment
      - SEC: Equity segment
      - COM: Commodity segment
      - If not specified, returns both (where supported)

    Supported brokers:
    - upstox: Full funds and margin support with segment filtering
    - angel: Angel One funds (coming soon)
    - dhan: Dhan funds (coming soon)
    """
    try:
        service = BrokerProfileService(db)
        funds_data = service.get_user_funds_and_margin(
            current_user.id, broker_name, segment
        )

        return {
            "success": True,
            "broker": broker_name.lower(),
            "user_id": current_user.id,
            **funds_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_broker_funds for {broker_name}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch {broker_name} funds: {str(e)}"
        )


@broker_profile_router.get("/profile/all")
async def get_all_broker_profiles(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get profile information for all active brokers of the user

    Returns profiles for all configured and active brokers.
    If a broker profile fails to load, it will be included with error details.
    """
    try:
        service = BrokerProfileService(db)
        profiles_data = service.get_all_user_broker_profiles(current_user.id)

        return {"success": True, "user_id": current_user.id, **profiles_data}

    except Exception as e:
        logger.error(f"Error in get_all_broker_profiles: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch broker profiles: {str(e)}"
        )


@broker_profile_router.get("/funds-summary")
async def get_combined_funds_summary(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get combined funds summary across all active brokers

    Returns:
    - Individual broker funds data
    - Combined summary with total available/used margins
    - Utilization percentage across all brokers
    """
    try:
        logger.info(
            f"Getting funds summary for user: {current_user.id} ({current_user.email})"
        )
        service = BrokerProfileService(db)
        funds_summary = service.get_combined_funds_summary(current_user.id)

        return {"success": True, "user_id": current_user.id, **funds_summary}

    except Exception as e:
        logger.error(f"Error in get_combined_funds_summary: {e}")
        import traceback

        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch combined funds summary: {str(e)}"
        )


@broker_profile_router.get("/supported-brokers")
async def get_supported_brokers():
    """
    Get list of supported brokers and their available features
    """
    return {
        "success": True,
        "supported_brokers": {
            "upstox": {
                "name": "Upstox",
                "profile_supported": True,
                "funds_supported": True,
                "segments": ["SEC", "COM"],
                "features": [
                    "User profile with exchanges and products",
                    "Funds and margin data",
                    "Segment-wise filtering",
                    "Real-time balance updates",
                ],
            },
            "angel": {
                "name": "Angel One",
                "profile_supported": False,
                "funds_supported": False,
                "segments": [],
                "features": ["Coming soon"],
                "status": "under_development",
            },
            "dhan": {
                "name": "Dhan",
                "profile_supported": False,
                "funds_supported": False,
                "segments": [],
                "features": ["Coming soon"],
                "status": "under_development",
            },
        },
        "total_supported": 1,
        "total_planned": 2,
    }


# Backward compatibility - redirect to unified endpoints
@broker_profile_router.get("/upstox/profile")
async def get_upstox_profile_compat(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Backward compatibility endpoint - redirects to unified profile endpoint"""
    return await get_broker_profile("upstox", current_user, db)


@broker_profile_router.get("/upstox/funds-and-margin")
async def get_upstox_funds_compat(
    segment: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Backward compatibility endpoint - redirects to unified funds endpoint"""
    return await get_broker_funds("upstox", segment, current_user, db)
