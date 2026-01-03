# router/option_routes.py
"""
Option Chain API Routes
Provides endpoints for option contracts, option chains, and futures data
"""

import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from services.auth_service import get_current_user
from services.upstox_option_service import upstox_option_service

logger = logging.getLogger(__name__)

# Create router
option_router = APIRouter(prefix="/api/v1/options", tags=["Options & Futures"])


@option_router.get("/contracts")
async def get_option_contracts(
    instrument_key: str = Query(
        ..., description="Instrument key (e.g., NSE_INDEX|Nifty 50)"
    ),
    expiry_date: Optional[str] = Query(
        None, description="Specific expiry date (YYYY-MM-DD)"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get option contracts for an instrument key - EXACTLY as per Upstox API documentation

    Flow:
    1. Frontend provides instrument_key (e.g., "NSE_INDEX|Nifty 50")
    2. Calls Upstox API: GET /option/contract?instrument_key=NSE_INDEX|Nifty 50
    3. Returns contract list (raw Upstox items) + helper list of unique expiry_dates
    """
    try:
        res = upstox_option_service.get_option_contracts(
            instrument_key, db, expiry_date
        )

        if not res:
            raise HTTPException(
                status_code=404,
                detail=f"No option contracts found for instrument_key: {instrument_key}",
            )

        expiry_dates = sorted(
            {item.get("expiry") for item in res if item.get("expiry")}
        )

        return {
            "status": "success",
            "data": res,  # exact Upstox shape per docs
            "expiry_dates": expiry_dates,
            "count": len(res),
            "retrieved_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting option contracts for {instrument_key}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving option contracts: {str(e)}"
        )


@option_router.get("/chain")
async def get_option_chain(
    instrument_key: str = Query(
        ..., description="Instrument key (e.g., NSE_INDEX|Nifty 50)"
    ),
    expiry_date: str = Query(..., description="Expiry date (YYYY-MM-DD) - REQUIRED"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get put/call option chain - EXACT Upstox API format

    Flow:
    1. Frontend calls /contracts?instrument_key=... to get available expiry dates
    2. Frontend calls /chain?instrument_key=...&expiry_date=YYYY-MM-DD
    3. Service calls Upstox API: GET /option/chain?instrument_key=...&expiry_date=...
    4. Returns {"status":"success","data":[...]} plus analytics keys
    """
    try:
        res = upstox_option_service.get_option_chain(instrument_key, expiry_date, db)

        if res is None:
            raise HTTPException(
                status_code=404,
                detail=f"No option chain found for instrument_key: {instrument_key}",
            )

        # Pass-through (already in exact Upstox shape for 'data')
        return res

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting option chain for {instrument_key}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving option chain: {str(e)}"
        )


@option_router.get("/futures/key/{instrument_key:path}")
async def get_futures_contracts(
    instrument_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get futures contracts by instrument key
    """
    try:
        # Handle ISIN codes - return empty list
        import re

        if re.search(r"INE[A-Z0-9]{9}", instrument_key):
             return {
                "status": "success",
                "input": instrument_key,
                "symbol": instrument_key,
                "futures": [],
                "count": 0,
                "message": "ISIN codes not supported for futures",
                "retrieved_at": datetime.now().isoformat(),
            }

        futures = upstox_option_service.get_futures_contracts(instrument_key, db)

        if futures is None or len(futures) == 0:
            return {
                "status": "success",
                "input": instrument_key,
                "symbol": instrument_key,  # Just return input as symbol
                "futures": [],
                "count": 0,
                "message": f"No futures contracts found for {instrument_key}",
                "retrieved_at": datetime.now().isoformat(),
            }

        # Pass-through style for futures too (when implemented)
        return {
            "status": "success",
            "input": instrument_key,
            "symbol": instrument_key,
            "futures": futures,
            "count": len(futures),
            "retrieved_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting futures contracts for {instrument_key}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving futures contracts: {str(e)}"
        )
