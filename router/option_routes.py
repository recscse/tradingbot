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
    Get futures contracts by instrument key or symbol
    Supports both: /futures/key/RELIANCE and /futures/key/NSE_EQ|RELIANCE
    """
    try:
        # Handle both formats: symbol (RELIANCE) or instrument_key (NSE_EQ|RELIANCE)
        if "|" in instrument_key:
            parts = instrument_key.split("|", 1)
            symbol = parts[1] if len(parts) > 1 else parts[0]
        else:
            symbol = instrument_key

        symbol = symbol.upper()

        # Handle ISIN codes - return empty list
        import re

        if re.match(r"^INE[A-Z0-9]{9}$", symbol):
            return {
                "status": "success",
                "input": instrument_key,
                "symbol": symbol,
                "futures": [],
                "count": 0,
                "message": "ISIN codes not supported for futures",
                "retrieved_at": datetime.now().isoformat(),
            }

        futures = upstox_option_service.get_futures_contracts(symbol, db)

        if futures is None or len(futures) == 0:
            return {
                "status": "success",
                "input": instrument_key,
                "symbol": symbol,
                "futures": [],
                "count": 0,
                "message": f"No futures contracts found for {symbol}",
                "retrieved_at": datetime.now().isoformat(),
            }

        # Pass-through style for futures too (when implemented)
        return {
            "status": "success",
            "input": instrument_key,
            "symbol": symbol,
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


@option_router.get("/symbol/{symbol}/instrument-key")
async def get_instrument_key_for_symbol(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the primary instrument_key for a symbol using the service's mapping.
    Example: NIFTY -> NSE_INDEX|Nifty 50, RELIANCE -> NSE_EQ|RELIANCE
    """
    try:
        symbol_upper = symbol.upper()

        # Use service logic to resolve instrument key
        primary_instrument_key = upstox_option_service._get_underlying_key(
            symbol_upper, db
        )

        # Quick stats: try contracts count (optional)
        try:
            contracts = upstox_option_service.get_option_contracts(
                primary_instrument_key, db
            )
            contract_count = len(contracts) if contracts else 0
        except Exception:
            contract_count = 0

        return {
            "status": "success",
            "symbol": symbol_upper,
            "instrument_key": primary_instrument_key,
            "fno_data": {
                "option_contracts_count": contract_count,
                "message": "Direct API integration - no redundant fetching!",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting instrument key for {symbol}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error resolving instrument key: {str(e)}"
        )
