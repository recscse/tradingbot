# router/option_routes.py
"""
Option Chain API Routes
Provides endpoints for option contracts, option chains, and futures data
"""

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.connection import get_db
from database.models import User
from services.auth_service import get_current_user
from services.upstox_option_service import (
    upstox_option_service,
    get_option_contracts_for_instrument_key,
    get_option_chain_for_instrument_key,
    get_fno_instruments_list,
    is_symbol_fno_eligible,
)

logger = logging.getLogger(__name__)

# Create router
option_router = APIRouter(prefix="/api/v1/options", tags=["Options & Futures"])


# Response models
class OptionContractResponse(BaseModel):
    instrument_key: str
    name: str
    expiry: str
    strike_price: float
    option_type: str
    exchange: str
    segment: str
    trading_symbol: str
    lot_size: int
    tick_size: float
    underlying_symbol: str


class FuturesContractResponse(BaseModel):
    instrument_key: str
    name: str
    expiry: str
    exchange: str
    segment: str
    trading_symbol: str
    lot_size: int
    tick_size: float
    underlying_symbol: str


class OptionChainResponse(BaseModel):
    underlying_symbol: str
    underlying_key: str
    spot_price: Optional[float]
    expiry_dates: List[str]
    strike_prices: List[float]
    options: dict  # Complex nested structure
    futures: List[dict]
    generated_at: str
    total_strikes: int
    total_expiries: int


class FNOInstrumentsResponse(BaseModel):
    instruments: List[str]
    count: int
    last_updated: str


@option_router.get("/instruments", response_model=FNOInstrumentsResponse)
async def get_fno_instruments(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get list of F&O eligible instruments
    """
    try:
        instruments = get_fno_instruments_list(db)

        return FNOInstrumentsResponse(
            instruments=instruments,
            count=len(instruments),
            last_updated="2024-01-01T00:00:00Z",  # This should be dynamic
        )

    except Exception as e:
        logger.error(f"Error getting F&O instruments: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving F&O instruments: {str(e)}"
        )


@option_router.get("/check/{symbol}")
async def check_fno_eligibility(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Check if a symbol is F&O eligible
    """
    try:
        is_eligible = is_symbol_fno_eligible(symbol.upper(), db)

        return {
            "symbol": symbol.upper(),
            "is_fno_eligible": is_eligible,
            "checked_at": "2024-01-01T00:00:00Z",
        }

    except Exception as e:
        logger.error(f"Error checking F&O eligibility for {symbol}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error checking F&O eligibility: {str(e)}"
        )


@option_router.get("/contracts")
async def get_option_contracts(
    instrument_key: str = Query(..., description="Instrument key (e.g., NSE_INDEX|Nifty 50)"),
    expiry_date: Optional[str] = Query(None, description="Specific expiry date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get option contracts for an instrument key - EXACTLY as per Upstox API documentation
    
    Correct Flow:
    1. Frontend provides instrument_key (e.g., "NSE_INDEX|Nifty 50")
    2. Calls Upstox API: GET /option/contract?instrument_key=NSE_INDEX|Nifty 50
    3. Returns contract list with expiry dates and instrument_keys for each option
    4. Frontend uses these instrument_keys for option chain API and WebSocket subscriptions
    """
    try:
        contracts = upstox_option_service.get_option_contracts(instrument_key, db, expiry_date)

        if contracts is None or len(contracts) == 0:
            raise HTTPException(
                status_code=404, detail=f"No option contracts found for instrument_key: {instrument_key}"
            )

        # Convert to response format - EXACTLY as per API documentation
        contract_responses = []
        expiry_dates = set()
        
        for contract in contracts:
            contract_responses.append(
                OptionContractResponse(
                    instrument_key=contract.instrument_key,
                    name=contract.name,
                    expiry=contract.expiry,
                    strike_price=contract.strike_price,
                    option_type=contract.option_type,
                    exchange=contract.exchange,
                    segment=contract.segment,
                    trading_symbol=contract.trading_symbol,
                    lot_size=contract.lot_size,
                    tick_size=contract.tick_size,
                    underlying_symbol=contract.underlying_symbol,
                )
            )
            expiry_dates.add(contract.expiry)

        return {
            "status": "success",  # As per Upstox API format
            "data": contract_responses,
            "expiry_dates": sorted(list(expiry_dates)),
            "count": len(contract_responses),
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
    instrument_key: str = Query(..., description="Instrument key (e.g., NSE_INDEX|Nifty 50)"),
    expiry_date: str = Query(..., description="Expiry date (YYYY-MM-DD) - REQUIRED"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get put/call option chain - EXACTLY as per Upstox API documentation
    
    Correct Flow:
    1. Frontend calls /contracts?instrument_key=NSE_INDEX|Nifty 50 to get available expiry dates
    2. Frontend calls /chain?instrument_key=NSE_INDEX|Nifty 50&expiry_date=2024-03-28
    3. Calls Upstox API: GET /option/chain?instrument_key=NSE_INDEX|Nifty 50&expiry_date=2024-03-28
    4. Returns option chain with call_options and put_options for each strike
    5. Frontend uses instrument_key from call_options/put_options for live price updates
    """
    try:
        option_chain = upstox_option_service.get_option_chain(instrument_key, expiry_date, db)

        if option_chain is None:
            raise HTTPException(
                status_code=404, detail=f"No option chain found for instrument_key: {instrument_key}"
            )

        # BATCH OPTIMIZATION: Collect all instrument keys first, then fetch prices in one API call
        all_instrument_keys = []
        for strike_price in option_chain.strike_prices:
            strike_key = str(strike_price)
            option_contracts = option_chain.options.get(strike_key, {})
            
            if "CE" in option_contracts:
                all_instrument_keys.append(option_contracts["CE"].instrument_key)
            if "PE" in option_contracts:
                all_instrument_keys.append(option_contracts["PE"].instrument_key)
        
        # Fetch all live prices in a single batch API call - MUCH MORE EFFICIENT!
        logger.info(f"Fetching live prices for {len(all_instrument_keys)} option instruments in batch")
        batch_live_data = upstox_option_service.get_live_prices_batch(all_instrument_keys, db)
        
        # Convert to Upstox API response format
        data = []
        for strike_price in option_chain.strike_prices:
            strike_key = str(strike_price)
            option_contracts = option_chain.options.get(strike_key, {})
            
            strike_data = {
                "expiry": expiry_date,
                "pcr": 0,  # Calculate if needed
                "strike_price": strike_price,
                "underlying_key": instrument_key,
                "underlying_spot_price": option_chain.spot_price,
            }
            
            # Add call options data
            if "CE" in option_contracts:
                call_contract = option_contracts["CE"]
                # Get live price data from batch result
                call_live_data = batch_live_data.get(call_contract.instrument_key, {})
                
                strike_data["call_options"] = {
                    "instrument_key": call_contract.instrument_key,
                    "market_data": {
                        "ltp": call_live_data.get("ltp", call_live_data.get("last_price", 0)),
                        "volume": call_live_data.get("volume", 0),
                        "oi": call_live_data.get("oi", call_live_data.get("open_interest", 0)),
                        "close_price": call_live_data.get("close_price", call_live_data.get("prev_close", 0)),
                        "bid_price": call_live_data.get("bid_price", 0),
                        "bid_qty": call_live_data.get("bid_qty", 0),
                        "ask_price": call_live_data.get("ask_price", 0),
                        "ask_qty": call_live_data.get("ask_qty", 0),
                        "prev_oi": call_live_data.get("prev_oi", 0),
                        "change": call_live_data.get("change", 0),
                        "change_percent": call_live_data.get("change_percent", 0),
                        "high": call_live_data.get("high", 0),
                        "low": call_live_data.get("low", 0),
                        "total_buy_quantity": call_live_data.get("total_buy_quantity", 0),
                        "total_sell_quantity": call_live_data.get("total_sell_quantity", 0)
                    },
                    "option_greeks": {
                        "vega": call_live_data.get("vega", 0),
                        "theta": call_live_data.get("theta", 0),
                        "gamma": call_live_data.get("gamma", 0),
                        "delta": call_live_data.get("delta", 0),
                        "iv": call_live_data.get("iv", call_live_data.get("implied_volatility", 0)),
                        "pop": call_live_data.get("pop", 0)
                    }
                }
            
            # Add put options data
            if "PE" in option_contracts:
                put_contract = option_contracts["PE"]
                # Get live price data from batch result
                put_live_data = batch_live_data.get(put_contract.instrument_key, {})
                
                strike_data["put_options"] = {
                    "instrument_key": put_contract.instrument_key,
                    "market_data": {
                        "ltp": put_live_data.get("ltp", put_live_data.get("last_price", 0)),
                        "volume": put_live_data.get("volume", 0),
                        "oi": put_live_data.get("oi", put_live_data.get("open_interest", 0)),
                        "close_price": put_live_data.get("close_price", put_live_data.get("prev_close", 0)),
                        "bid_price": put_live_data.get("bid_price", 0),
                        "bid_qty": put_live_data.get("bid_qty", 0),
                        "ask_price": put_live_data.get("ask_price", 0),
                        "ask_qty": put_live_data.get("ask_qty", 0),
                        "prev_oi": put_live_data.get("prev_oi", 0),
                        "change": put_live_data.get("change", 0),
                        "change_percent": put_live_data.get("change_percent", 0),
                        "high": put_live_data.get("high", 0),
                        "low": put_live_data.get("low", 0),
                        "total_buy_quantity": put_live_data.get("total_buy_quantity", 0),
                        "total_sell_quantity": put_live_data.get("total_sell_quantity", 0)
                    },
                    "option_greeks": {
                        "vega": put_live_data.get("vega", 0),
                        "theta": put_live_data.get("theta", 0),
                        "gamma": put_live_data.get("gamma", 0),
                        "delta": put_live_data.get("delta", 0),
                        "iv": put_live_data.get("iv", put_live_data.get("implied_volatility", 0)),
                        "pop": put_live_data.get("pop", 0)
                    }
                }
            
            data.append(strike_data)

        return {
            "status": "success",  # As per Upstox API format
            "data": data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting option chain for {instrument_key}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving option chain: {str(e)}"
        )


@option_router.get("/futures/{symbol}")
async def get_futures_contracts(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get futures contracts for a symbol
    """
    try:
        symbol = symbol.upper()

        # Check if symbol is F&O eligible
        if not is_symbol_fno_eligible(symbol, db):
            raise HTTPException(
                status_code=400, detail=f"Symbol {symbol} is not F&O eligible"
            )

        futures = upstox_option_service.get_futures_contracts(symbol, db)

        if futures is None:
            raise HTTPException(
                status_code=404, detail=f"No futures contracts found for {symbol}"
            )

        # Convert to response format
        futures_responses = []
        for future in futures:
            futures_responses.append(
                FuturesContractResponse(
                    instrument_key=future.instrument_key,
                    name=future.name,
                    expiry=future.expiry,
                    exchange=future.exchange,
                    segment=future.segment,
                    trading_symbol=future.trading_symbol,
                    lot_size=future.lot_size,
                    tick_size=future.tick_size,
                    underlying_symbol=future.underlying_symbol,
                )
            )

        return {
            "symbol": symbol,
            "futures": futures_responses,
            "count": len(futures_responses),
            "retrieved_at": "2024-01-01T00:00:00Z",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting futures contracts for {symbol}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving futures contracts: {str(e)}"
        )


@option_router.get("/futures/key/{instrument_key:path}")
async def get_futures_contracts_by_instrument_key(
    instrument_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get futures contracts by instrument key (e.g., NSE_EQ|RELIANCE)
    """
    try:
        # Extract symbol from instrument key
        if '|' in instrument_key:
            parts = instrument_key.split('|')
            symbol = parts[1] if len(parts) > 1 else parts[0]
        else:
            symbol = instrument_key
        
        symbol = symbol.upper()
        
        # Handle ISIN codes - return empty list
        import re
        if re.match(r'^INE[A-Z0-9]{9}$', symbol):
            return {
                "instrument_key": instrument_key,
                "symbol": symbol,
                "futures": [],
                "count": 0,
                "message": "ISIN codes not supported for futures",
                "retrieved_at": datetime.now().isoformat(),
            }

        # Check if symbol is F&O eligible
        if not is_symbol_fno_eligible(symbol, db):
            raise HTTPException(
                status_code=400, detail=f"Symbol {symbol} is not F&O eligible"
            )

        futures = upstox_option_service.get_futures_contracts(symbol, db)

        if futures is None or len(futures) == 0:
            return {
                "instrument_key": instrument_key,
                "symbol": symbol,
                "futures": [],
                "count": 0,
                "message": f"No futures contracts found for {symbol}",
                "retrieved_at": datetime.now().isoformat(),
            }

        # Convert to response format
        futures_responses = []
        for future in futures:
            futures_responses.append(
                FuturesContractResponse(
                    instrument_key=future.instrument_key,
                    name=future.name,
                    expiry=future.expiry,
                    exchange=future.exchange,
                    segment=future.segment,
                    trading_symbol=future.trading_symbol,
                    lot_size=future.lot_size,
                    tick_size=future.tick_size,
                    underlying_symbol=future.underlying_symbol,
                )
            )

        return {
            "instrument_key": instrument_key,
            "symbol": symbol,
            "futures": futures_responses,
            "count": len(futures_responses),
            "retrieved_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting futures contracts for instrument key {instrument_key}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving futures contracts: {str(e)}"
        )


@option_router.post("/cache/clear")
async def clear_option_cache(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Clear option service cache (admin only)
    """
    try:
        # Check if user is admin
        if not current_user.role or current_user.role.lower() != "admin":
            raise HTTPException(
                status_code=403, detail="Only admin users can clear the cache"
            )

        upstox_option_service.clear_cache()

        return {
            "success": True,
            "message": "Option service cache cleared successfully",
            "cleared_at": "2024-01-01T00:00:00Z",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing option cache: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")


@option_router.get("/symbol/{symbol}/instrument-key")
async def get_instrument_key_for_symbol(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the primary instrument_key for a symbol - Bridge for UI to get instrument_key
    
    This endpoint helps the UI convert symbols to instrument_keys for the Upstox API calls.
    For example: NIFTY -> NSE_INDEX|Nifty 50, RELIANCE -> NSE_EQ|RELIANCE-EB
    """
    try:
        from services.instrument_refresh_service import get_fno_instrument_keys
        
        # Get F&O instrument data for the symbol
        fno_data = get_fno_instrument_keys(symbol.upper())
        
        if "error" in fno_data:
            raise HTTPException(
                status_code=404, 
                detail=f"Symbol {symbol} not found in F&O instruments"
            )
        
        # Get the primary instrument key (underlying/spot)
        primary_instrument_key = None
        if fno_data.get("spot") and len(fno_data["spot"]) > 0:
            primary_instrument_key = fno_data["spot"][0]["instrument_key"]
        
        if not primary_instrument_key:
            # For indices like NIFTY, BANKNIFTY, construct manually
            symbol_upper = symbol.upper()
            if symbol_upper in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']:
                primary_instrument_key = f"NSE_INDEX|{symbol_upper}"
            else:
                primary_instrument_key = f"NSE_EQ|{symbol_upper}"
        
        return {
            "status": "success",
            "symbol": symbol.upper(),
            "instrument_key": primary_instrument_key,
            "fno_data": {
                "futures_count": len(fno_data.get("futures", [])),
                "call_options_count": len(fno_data.get("call_options", [])),
                "put_options_count": len(fno_data.get("put_options", [])),
                "total_instruments": len(fno_data.get("futures", [])) + len(fno_data.get("call_options", [])) + len(fno_data.get("put_options", []))
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting instrument key for {symbol}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error resolving instrument key: {str(e)}"
        )


@option_router.get("/health")
async def option_service_health():
    """
    Health check for option service
    """
    try:
        return {
            "status": "healthy",
            "service": "option_chain",
            "timestamp": "2024-01-01T00:00:00Z",
            "cache_size": len(upstox_option_service.cache),
            "version": "1.0.0",
        }

    except Exception as e:
        logger.error(f"Option service health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": "2024-01-01T00:00:00Z",
            },
        )
