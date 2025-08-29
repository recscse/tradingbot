"""
Upstox Options Contract Resolver

Uses official Upstox REST APIs to resolve expiries, option contracts, and ATM options.
All API calls are cached with short TTL to minimize API usage while ensuring fresh data.
"""

import httpx
import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class OptionContract:
    """Standardized option contract data structure"""
    instrument_key: str
    symbol: str
    expiry: str
    strike_price: float
    option_type: str  # 'CE' or 'PE'
    lot_size: int
    exchange: str
    
class OptionsResolver:
    """
    Resolves option contracts using Upstox REST APIs.
    
    Features:
    - Cached API responses to minimize requests
    - ATM option detection
    - Expiry management
    - Error handling and retries
    """
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.upstox.com"
        self.client = httpx.AsyncClient()
        
        # Caching with TTL
        self.expiry_cache = {}
        self.option_contracts_cache = {}
        self.option_chain_cache = {}
        self.cache_ttl = 300  # 5 minutes TTL
        self.cache_timestamps = {}
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self.cache_timestamps:
            return False
        
        cache_time = self.cache_timestamps[cache_key]
        return (datetime.now() - cache_time).total_seconds() < self.cache_ttl
    
    def _update_cache_timestamp(self, cache_key: str):
        """Update cache timestamp for TTL tracking"""
        self.cache_timestamps[cache_key] = datetime.now()
    
    async def _make_request(self, endpoint: str) -> Dict[str, Any]:
        """Make authenticated request to Upstox API with error handling"""
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = await self.client.get(url, headers=headers, timeout=10.0)
            
            if response.status_code == 401:
                logger.error("❌ Upstox API authentication failed - token may be expired")
                raise Exception("Upstox authentication failed")
            
            if response.status_code != 200:
                logger.error(f"❌ Upstox API error: {response.status_code} - {response.text}")
                raise Exception(f"API request failed with status {response.status_code}")
            
            data = response.json()
            
            if data.get("status") != "success":
                logger.error(f"❌ Upstox API returned error: {data}")
                raise Exception(f"API returned error: {data.get('message', 'Unknown error')}")
            
            return data["data"]
            
        except httpx.TimeoutException:
            logger.error("❌ Upstox API request timeout")
            raise Exception("API request timeout")
        except Exception as e:
            logger.error(f"❌ Upstox API request error: {e}")
            raise
    
    async def get_expiries(self, symbol: str) -> List[str]:
        """
        Get available expiry dates for a symbol.
        
        API: https://upstox.com/developer/api-documentation/get-expiries
        
        Args:
            symbol: Trading symbol (e.g., 'NIFTY', 'BANKNIFTY')
            
        Returns:
            List of expiry dates in YYYY-MM-DD format, sorted chronologically
        """
        cache_key = f"expiries_{symbol}"
        
        # Return cached data if valid
        if self._is_cache_valid(cache_key) and cache_key in self.expiry_cache:
            logger.debug(f"📋 Returning cached expiries for {symbol}")
            return self.expiry_cache[cache_key]
        
        try:
            # https://api.upstox.com/v2/option/expiry?symbol=NIFTY&exchange=NSE
            endpoint = f"/v2/option/expiry?symbol={symbol}&exchange=NSE"
            data = await self._make_request(endpoint)
            
            expiries = data.get("expiry", [])
            
            # Sort expiries chronologically
            expiries.sort()
            
            # Cache the result
            self.expiry_cache[cache_key] = expiries
            self._update_cache_timestamp(cache_key)
            
            logger.info(f"✅ Retrieved {len(expiries)} expiries for {symbol}")
            return expiries
            
        except Exception as e:
            logger.error(f"❌ Error getting expiries for {symbol}: {e}")
            # Return cached data if available, even if stale
            return self.expiry_cache.get(cache_key, [])
    
    async def get_option_contracts(self, symbol: str, expiry: str) -> List[OptionContract]:
        """
        Get option contracts for a symbol and expiry.
        
        API: https://upstox.com/developer/api-documentation/get-option-contracts
        
        Args:
            symbol: Trading symbol  
            expiry: Expiry date in YYYY-MM-DD format
            
        Returns:
            List of OptionContract objects
        """
        cache_key = f"contracts_{symbol}_{expiry}"
        
        # Return cached data if valid
        if self._is_cache_valid(cache_key) and cache_key in self.option_contracts_cache:
            logger.debug(f"📋 Returning cached option contracts for {symbol} {expiry}")
            return self.option_contracts_cache[cache_key]
        
        try:
            # https://api.upstox.com/v2/option/contract?symbol=NIFTY&exchange=NSE&expiry=2024-01-25
            endpoint = f"/v2/option/contract?symbol={symbol}&exchange=NSE&expiry={expiry}"
            data = await self._make_request(endpoint)
            
            contracts = []
            for contract_data in data:
                try:
                    contract = OptionContract(
                        instrument_key=contract_data.get("instrument_key", ""),
                        symbol=contract_data.get("trading_symbol", symbol),
                        expiry=expiry,
                        strike_price=float(contract_data.get("strike_price", 0)),
                        option_type=contract_data.get("option_type", ""),
                        lot_size=int(contract_data.get("lot_size", 1)),
                        exchange=contract_data.get("exchange", "NSE")
                    )
                    contracts.append(contract)
                    
                except (ValueError, KeyError) as e:
                    logger.warning(f"⚠️ Error parsing contract data: {e}, Data: {contract_data}")
                    continue
            
            # Cache the result
            self.option_contracts_cache[cache_key] = contracts
            self._update_cache_timestamp(cache_key)
            
            logger.info(f"✅ Retrieved {len(contracts)} option contracts for {symbol} {expiry}")
            return contracts
            
        except Exception as e:
            logger.error(f"❌ Error getting option contracts for {symbol} {expiry}: {e}")
            # Return cached data if available, even if stale
            return self.option_contracts_cache.get(cache_key, [])
    
    async def get_option_chain(self, symbol: str, expiry: str) -> Dict[str, Any]:
        """
        Get complete option chain with live prices.
        
        API: https://upstox.com/developer/api-documentation/get-pc-option-chain
        
        Args:
            symbol: Trading symbol
            expiry: Expiry date
            
        Returns:
            Dict with option chain data including live prices
        """
        cache_key = f"chain_{symbol}_{expiry}"
        
        # Return cached data if valid (shorter TTL for live prices)
        chain_cache_ttl = 30  # 30 seconds for option chain
        if (cache_key in self.cache_timestamps and 
            (datetime.now() - self.cache_timestamps[cache_key]).total_seconds() < chain_cache_ttl and
            cache_key in self.option_chain_cache):
            logger.debug(f"📋 Returning cached option chain for {symbol} {expiry}")
            return self.option_chain_cache[cache_key]
        
        try:
            # https://api.upstox.com/v2/option/chain?symbol=NIFTY&exchange=NSE&expiry=2024-01-25
            endpoint = f"/v2/option/chain?symbol={symbol}&exchange=NSE&expiry={expiry}"
            data = await self._make_request(endpoint)
            
            # Cache the result with shorter TTL
            self.option_chain_cache[cache_key] = data
            self._update_cache_timestamp(cache_key)
            
            logger.info(f"✅ Retrieved option chain for {symbol} {expiry}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error getting option chain for {symbol} {expiry}: {e}")
            # Return cached data if available, even if stale
            return self.option_chain_cache.get(cache_key, {})
    
    async def find_atm_options(self, symbol: str, expiry: str, spot_price: float) -> Tuple[Optional[OptionContract], Optional[OptionContract]]:
        """
        Find At-The-Money (ATM) call and put options for a given spot price.
        
        Args:
            symbol: Trading symbol
            expiry: Expiry date
            spot_price: Current spot price
            
        Returns:
            Tuple of (ATM_call_contract, ATM_put_contract) or (None, None) if not found
        """
        try:
            contracts = await self.get_option_contracts(symbol, expiry)
            
            if not contracts:
                logger.warning(f"⚠️ No contracts found for {symbol} {expiry}")
                return None, None
            
            # Find the strike closest to spot price
            strikes = list(set(contract.strike_price for contract in contracts))
            strikes.sort()
            
            # Find ATM strike (closest to spot price)
            atm_strike = min(strikes, key=lambda x: abs(x - spot_price))
            
            logger.info(f"📍 ATM strike for {symbol} at spot {spot_price}: {atm_strike}")
            
            # Find call and put contracts for ATM strike
            atm_call = None
            atm_put = None
            
            for contract in contracts:
                if contract.strike_price == atm_strike:
                    if contract.option_type == 'CE':
                        atm_call = contract
                    elif contract.option_type == 'PE':
                        atm_put = contract
            
            if atm_call and atm_put:
                logger.info(f"✅ Found ATM options: Call={atm_call.instrument_key}, Put={atm_put.instrument_key}")
            else:
                logger.warning(f"⚠️ Could not find both ATM options for strike {atm_strike}")
            
            return atm_call, atm_put
            
        except Exception as e:
            logger.error(f"❌ Error finding ATM options for {symbol}: {e}")
            return None, None
    
    async def get_next_expiry(self, symbol: str, days_ahead: int = 0) -> Optional[str]:
        """
        Get the next available expiry date.
        
        Args:
            symbol: Trading symbol
            days_ahead: Minimum days from today (0 = current/next available expiry)
            
        Returns:
            Next expiry date string or None if not found
        """
        try:
            expiries = await self.get_expiries(symbol)
            
            if not expiries:
                return None
            
            today = datetime.now().date()
            target_date = today + timedelta(days=days_ahead)
            
            # Find first expiry on or after target date
            for expiry_str in expiries:
                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                if expiry_date >= target_date:
                    logger.info(f"📅 Next expiry for {symbol}: {expiry_str}")
                    return expiry_str
            
            # If no future expiry found, return the last available
            logger.warning(f"⚠️ No future expiry found for {symbol}, returning last available")
            return expiries[-1]
            
        except Exception as e:
            logger.error(f"❌ Error getting next expiry for {symbol}: {e}")
            return None
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get caching statistics for monitoring"""
        return {
            "expiry_cache_entries": len(self.expiry_cache),
            "contracts_cache_entries": len(self.option_contracts_cache), 
            "chain_cache_entries": len(self.option_chain_cache),
            "total_cache_entries": len(self.cache_timestamps),
            "cache_ttl_seconds": self.cache_ttl
        }

# Helper function to create resolver with token from database
async def create_options_resolver(user_id: int) -> Optional[OptionsResolver]:
    """
    Create OptionsResolver instance with user's Upstox token from database.
    
    Args:
        user_id: User ID to fetch token for
        
    Returns:
        OptionsResolver instance or None if token not available
    """
    try:
        from database.connection import get_db
        from database.models import BrokerConfig
        
        db = next(get_db())
        broker_config = db.query(BrokerConfig).filter_by(
            user_id=user_id, 
            broker_name="upstox",
            is_active=True
        ).first()
        
        if not broker_config or not broker_config.access_token:
            logger.warning(f"⚠️ No active Upstox token found for user {user_id}")
            return None
        
        resolver = OptionsResolver(broker_config.access_token)
        logger.info(f"✅ Created OptionsResolver for user {user_id}")
        return resolver
        
    except Exception as e:
        logger.error(f"❌ Error creating OptionsResolver for user {user_id}: {e}")
        return None