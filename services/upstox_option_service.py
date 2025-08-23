# services/upstox_option_service.py
"""
Upstox Option Chain Service - HTTP REST API Integration
Handles option contracts and option chain data using Upstox APIs
"""

import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from sqlalchemy.orm import Session
from database.models import BrokerConfig, User
from database.connection import get_db

logger = logging.getLogger(__name__)

UPSTOX_BASE_URL = "https://api.upstox.com/v2"


@dataclass
class OptionContract:
    """Option contract data structure"""

    instrument_key: str
    name: str
    expiry: str
    strike_price: float
    option_type: str  # CE/PE
    exchange: str
    segment: str
    trading_symbol: str
    lot_size: int
    tick_size: float
    underlying_symbol: str


@dataclass
class FuturesContract:
    """Futures contract data structure"""

    instrument_key: str
    name: str
    expiry: str
    exchange: str
    segment: str
    trading_symbol: str
    lot_size: int
    tick_size: float
    underlying_symbol: str


@dataclass
class OptionChainData:
    """Complete option chain data with futures"""

    underlying_symbol: str
    underlying_key: str
    spot_price: Optional[float]
    expiry_dates: List[str]
    strike_prices: List[float]
    options: Dict[
        str, Dict[str, OptionContract]
    ]  # {strike: {CE: contract, PE: contract}}
    futures: List[FuturesContract]
    generated_at: datetime


class UpstoxOptionService:
    """Service for Upstox option chain and futures data"""

    def __init__(self):
        self.base_url = UPSTOX_BASE_URL
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes cache for contracts

    def _get_admin_token(self, db: Session) -> Optional[str]:
        """Get admin Upstox token for API calls"""
        try:
            # Get admin user's Upstox token
            admin_config = (
                db.query(BrokerConfig)
                .join(User)
                .filter(
                    User.role == "admin",
                    BrokerConfig.broker_name.ilike("upstox"),
                    BrokerConfig.is_active == True,
                    BrokerConfig.access_token.isnot(None),
                )
                .first()
            )

            if admin_config and admin_config.access_token:
                # Check if token is not expired
                if (
                    admin_config.access_token_expiry
                    and admin_config.access_token_expiry > datetime.now()
                ):
                    return admin_config.access_token

            logger.warning("No valid admin Upstox token found")
            return None

        except Exception as e:
            logger.error(f"Error getting admin token: {e}")
            return None

    def _make_upstox_request(
        self, endpoint: str, params: Dict = None, db: Session = None
    ) -> Optional[Dict]:
        """Make authenticated request to Upstox API"""
        try:
            token = self._get_admin_token(db)
            if not token:
                logger.error("No valid Upstox token available")
                return None

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            url = f"{self.base_url}{endpoint}"

            logger.info(f"Making Upstox API call to: {endpoint}")
            response = requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    return data.get("data", {})
                else:
                    logger.error(f"Upstox API error: {data}")
                    return None
            elif response.status_code == 401:
                logger.error("Upstox token expired or invalid")
                return None
            else:
                logger.error(
                    f"Upstox API error {response.status_code}: {response.text}"
                )
                return None

        except requests.RequestException as e:
            logger.error(f"Network error calling Upstox API: {e}")
            return None
        except Exception as e:
            logger.error(f"Error making Upstox request: {e}")
            return None

    def get_live_prices_batch(self, instrument_keys: List[str], db: Session) -> Dict[str, Dict]:
        """Get live prices for multiple instruments in a single API call - MUCH MORE EFFICIENT"""
        try:
            if not instrument_keys:
                return {}
                
            # Check cache first - return cached data for instruments that are still fresh
            cached_prices = {}
            uncached_keys = []
            current_time = datetime.now()
            
            for key in instrument_keys:
                cache_key = f"live_price_{key}"
                if cache_key in self.cache:
                    cached_data, timestamp = self.cache[cache_key]
                    if current_time - timestamp < timedelta(seconds=30):  # 30 second cache
                        cached_prices[key] = cached_data
                    else:
                        uncached_keys.append(key)
                else:
                    uncached_keys.append(key)
            
            # If all data is cached, return it
            if not uncached_keys:
                logger.debug(f"Returning cached prices for {len(cached_prices)} instruments")
                return cached_prices
            
            # Make batch API call for uncached instruments
            endpoint = "/market-quote/quotes"
            # Upstox API supports comma-separated instrument keys
            params = {"instrument_key": ','.join(uncached_keys)}
            
            logger.info(f"Fetching live prices for {len(uncached_keys)} instruments in batch")
            response_data = self._make_upstox_request(endpoint, params, db)
            
            batch_prices = {}
            
            if response_data:
                # Process each instrument's data from batch response
                # IMPORTANT: Upstox API returns data with different key format!
                # Request: NSE_FO|121002 -> Response: NSE_FO:RELIANCE25OCT1480CE
                for key in uncached_keys:
                    # Try direct key first
                    quote_data = response_data.get(key, {})
                    
                    # If not found, search for key with different format (| vs :)
                    if not quote_data:
                        # Convert NSE_FO|121002 to NSE_FO:* pattern and search
                        search_prefix = key.replace('|', ':')
                        for response_key, data in response_data.items():
                            if response_key.startswith(search_prefix.split(':')[0] + ':'):
                                quote_data = data
                                logger.info(f"Found data for {key} under response key {response_key}")
                                break
                    
                    if quote_data:
                        # Format price data from Upstox API response
                        price_data = {
                            "ltp": quote_data.get("last_price", 0),
                            "volume": quote_data.get("volume", 0),
                            "oi": quote_data.get("oi", 0),
                            "close_price": quote_data.get("close_price", 0),  
                            "change": quote_data.get("net_change", 0),
                            "change_percent": quote_data.get("percentage_change", 0),
                            "bid_price": quote_data.get("depth", {}).get("buy", [{}])[0].get("price", 0) if quote_data.get("depth", {}).get("buy") else 0,
                            "ask_price": quote_data.get("depth", {}).get("sell", [{}])[0].get("price", 0) if quote_data.get("depth", {}).get("sell") else 0,
                            "high": quote_data.get("ohlc", {}).get("high", 0),
                            "low": quote_data.get("ohlc", {}).get("low", 0),
                            "average_price": quote_data.get("average_price", 0),
                            "total_buy_quantity": quote_data.get("total_buy_quantity", 0),
                            "total_sell_quantity": quote_data.get("total_sell_quantity", 0),
                            "lower_circuit": quote_data.get("lower_circuit_limit", 0),
                            "upper_circuit": quote_data.get("upper_circuit_limit", 0),
                            "oi_day_high": quote_data.get("oi_day_high", 0),
                            "oi_day_low": quote_data.get("oi_day_low", 0),
                            "_api_success": True  # Flag to indicate real API data
                        }
                        
                        # Cache the result
                        cache_key = f"live_price_{key}"
                        self.cache[cache_key] = (price_data, current_time)
                        batch_prices[key] = price_data
                    else:
                        # No data for this instrument - return basic structure with zeros
                        logger.warning(f"No quote data found for instrument: {key}")
                        zero_data = {
                            "ltp": 0.0,
                            "volume": 0,
                            "oi": 0.0,
                            "close_price": 0.0,
                            "change": 0.0,
                            "change_percent": 0.0,
                            "bid_price": 0.0,
                            "ask_price": 0.0,
                            "high": 0.0,
                            "low": 0.0,
                            "_api_success": False
                        }
                        cache_key = f"live_price_{key}"
                        self.cache[cache_key] = (zero_data, current_time)
                        batch_prices[key] = zero_data
            else:
                # API call failed - return zero data for all uncached instruments
                logger.warning(f"Batch API call failed, returning zero data for {len(uncached_keys)} instruments")
                for key in uncached_keys:
                    zero_data = {
                        "ltp": 0.0,
                        "volume": 0,
                        "oi": 0.0,
                        "close_price": 0.0,
                        "change": 0.0,
                        "change_percent": 0.0,
                        "bid_price": 0.0,
                        "ask_price": 0.0,
                        "high": 0.0,
                        "low": 0.0,
                        "_api_success": False
                    }
                    cache_key = f"live_price_{key}"
                    self.cache[cache_key] = (zero_data, current_time)
                    batch_prices[key] = zero_data
            
            # Combine cached and newly fetched prices
            all_prices = {**cached_prices, **batch_prices}
            logger.info(f"Returning prices for {len(all_prices)} instruments ({len(cached_prices)} cached, {len(batch_prices)} fetched)")
            
            return all_prices

        except Exception as e:
            logger.error(f"Error getting batch live prices: {e}")
            # Fallback: return zero data for all instruments
            zero_prices = {}
            for key in instrument_keys:
                zero_prices[key] = {
                    "ltp": 0.0,
                    "volume": 0,
                    "oi": 0.0,
                    "close_price": 0.0,
                    "change": 0.0,
                    "change_percent": 0.0,
                    "bid_price": 0.0,
                    "ask_price": 0.0,
                    "high": 0.0,
                    "low": 0.0,
                    "_api_success": False
                }
            return zero_prices

    def get_live_price(self, instrument_key: str, db: Session) -> Optional[Dict]:
        """Get live price for a single instrument - delegates to batch method for efficiency"""
        batch_result = self.get_live_prices_batch([instrument_key], db)
        return batch_result.get(instrument_key)

    def _get_mock_price_data(self, instrument_key: str) -> Dict:
        """Generate realistic mock price data for development/testing"""
        try:
            import random
            import hashlib
            
            # Use instrument key to generate consistent mock data
            seed = int(hashlib.md5(instrument_key.encode()).hexdigest()[:8], 16)
            random.seed(seed)
            
            # Generate base price based on instrument type
            if "NIFTY" in instrument_key or "INDEX" in instrument_key:
                base_price = random.uniform(50, 500)  # Index options
            else:
                base_price = random.uniform(10, 100)   # Stock options
            
            change = random.uniform(-5, 5)
            change_percent = (change / base_price) * 100 if base_price > 0 else 0
            
            mock_data = {
                "ltp": round(base_price, 2),
                "volume": random.randint(1000, 50000),
                "oi": random.randint(500, 25000),
                "close_price": round(base_price - change, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "bid_price": round(base_price - 0.5, 2),
                "ask_price": round(base_price + 0.5, 2),
                "high": round(base_price + random.uniform(0, 5), 2),
                "low": round(base_price - random.uniform(0, 5), 2),
                "_is_mock": True  # Flag to indicate this is mock data
            }
            
            logger.info(f"Generated mock price data for {instrument_key}: LTP={mock_data['ltp']}")
            return mock_data
            
        except Exception as e:
            logger.error(f"Error generating mock data: {e}")
            return {
                "ltp": 50.0,
                "volume": 1000,
                "oi": 500,
                "close_price": 48.0,
                "change": 2.0,
                "change_percent": 4.17,
                "bid_price": 49.5,
                "ask_price": 50.5,
                "high": 52.0,
                "low": 47.0,
                "_is_mock": True
            }

    def _get_instrument_data_from_csv(self, db: Session) -> List:
        """Get instrument data from local JSON file"""
        try:
            import os
            import json
            
            json_path = os.path.join(os.path.dirname(__file__), '../data/filtered_instruments.json')
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    instruments = json.load(f)
                    return instruments
            
            logger.warning("Filtered instruments file not found")
            return []
            
        except Exception as e:
            logger.error(f"Error reading instrument data: {e}")
            return []

    def _convert_timestamp_to_date(self, timestamp: int) -> str:
        """Convert timestamp to date string"""
        try:
            from datetime import datetime
            dt = datetime.fromtimestamp(timestamp / 1000)  # Convert milliseconds to seconds
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return ""

    def get_expiry_dates(self, instrument_key: str, db: Session) -> Optional[List[str]]:
        """Get available expiry dates for an instrument using Upstox API"""
        try:
            cache_key = f"expiry_dates_{instrument_key}"

            # Check cache (cache for 1 hour since expiries don't change often)
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if datetime.now() - timestamp < timedelta(seconds=3600):  # 1 hour cache
                    logger.info(f"Returning cached expiry dates for {instrument_key}")
                    return cached_data

            # Make API call to get expiry dates - exactly as per documentation
            endpoint = "/expired-instruments/expiries"
            params = {"instrument_key": instrument_key}

            logger.info(f"Fetching expiry dates for instrument: {instrument_key}")
            response_data = self._make_upstox_request(endpoint, params, db)
            
            if not response_data:
                logger.warning(f"No expiry data received for {instrument_key}")
                return None

            expiry_dates = []
            
            # Parse response - API returns array of expiry date strings
            if isinstance(response_data, list):
                expiry_dates = response_data
            elif isinstance(response_data, dict) and 'expiry_dates' in response_data:
                expiry_dates = response_data['expiry_dates']
            else:
                logger.warning(f"Unexpected expiry data format for {instrument_key}: {response_data}")
                return None

            # Filter out past dates and sort
            current_date = datetime.now().date()
            valid_expiries = []
            
            for expiry_str in expiry_dates:
                try:
                    # Parse expiry date (expecting YYYY-MM-DD format)
                    expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                    if expiry_date >= current_date:
                        valid_expiries.append(expiry_str)
                except ValueError:
                    logger.warning(f"Invalid expiry date format: {expiry_str}")
                    continue

            # Sort expiries (nearest first)
            valid_expiries.sort()

            # Cache the results
            self.cache[cache_key] = (valid_expiries, datetime.now())

            logger.info(f"Found {len(valid_expiries)} valid expiry dates for {instrument_key}: {valid_expiries[:3]}...")
            return valid_expiries

        except Exception as e:
            logger.error(f"Error fetching expiry dates for {instrument_key}: {e}")
            return None

    def get_nearest_expiry(self, instrument_key: str, db: Session) -> Optional[str]:
        """Get the nearest (current week/month) expiry date for an instrument"""
        try:
            expiry_dates = self.get_expiry_dates(instrument_key, db)
            if expiry_dates and len(expiry_dates) > 0:
                # Return the nearest expiry (first in sorted list)
                nearest_expiry = expiry_dates[0]
                logger.info(f"Nearest expiry for {instrument_key}: {nearest_expiry}")
                return nearest_expiry
            else:
                logger.warning(f"No valid expiry dates found for {instrument_key}")
                return None
        except Exception as e:
            logger.error(f"Error getting nearest expiry for {instrument_key}: {e}")
            return None

    def get_option_contracts(
        self, instrument_key: str, db: Session, expiry_date: str = None
    ) -> Optional[List[OptionContract]]:
        """Get option contracts using Upstox API with instrument_key from UI"""
        try:
            # If no expiry_date provided, get the nearest expiry first
            if not expiry_date:
                logger.info(f"No expiry provided, fetching nearest expiry for {instrument_key}")
                expiry_date = self.get_nearest_expiry(instrument_key, db)
                if not expiry_date:
                    logger.warning(f"Could not get valid expiry date for {instrument_key}")
                    # Continue anyway, API might still return some data
                else:
                    logger.info(f"Using nearest expiry: {expiry_date} for {instrument_key}")

            cache_key = f"contracts_{instrument_key}_{expiry_date or 'all'}"

            # Check cache
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if datetime.now() - timestamp < timedelta(seconds=self.cache_timeout):
                    logger.info(f"Returning cached option contracts for {instrument_key}")
                    return cached_data

            # Make API call to get option contracts - EXACTLY as per documentation
            endpoint = "/option/contract"
            params = {"instrument_key": instrument_key}
            if expiry_date:
                params["expiry_date"] = expiry_date
                logger.info(f"Fetching option contracts for {instrument_key} with expiry {expiry_date}")
            else:
                logger.info(f"Fetching option contracts for {instrument_key} (all expiries)")

            response_data = self._make_upstox_request(endpoint, params, db)
            if not response_data:
                logger.error("API call failed for option contracts")
                return None

            contracts = []
            for contract_data in response_data:
                try:
                    # Parse exactly as per documentation response format
                    contract = OptionContract(
                        instrument_key=contract_data.get("instrument_key", ""),
                        name=contract_data.get("name", ""),
                        expiry=contract_data.get("expiry", ""),
                        strike_price=float(contract_data.get("strike_price", 0)),
                        option_type=contract_data.get("instrument_type", ""),  # CE or PE
                        exchange=contract_data.get("exchange", ""),
                        segment=contract_data.get("segment", ""),
                        trading_symbol=contract_data.get("trading_symbol", ""),
                        lot_size=int(contract_data.get("lot_size", 0)),
                        tick_size=float(contract_data.get("tick_size", 0.05)),
                        underlying_symbol=contract_data.get("underlying_symbol", ""),
                    )
                    contracts.append(contract)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing contract data: {e}")
                    continue

            # Cache the results
            self.cache[cache_key] = (contracts, datetime.now())

            logger.info(f"Retrieved {len(contracts)} option contracts for {instrument_key}")
            return contracts

        except Exception as e:
            logger.error(f"Error getting option contracts for {instrument_key}: {e}")
            return None

    def _get_underlying_key(self, symbol: str, db: Session) -> Optional[str]:
        """Get underlying instrument key for a symbol"""
        try:
            instruments_data = self._get_instrument_data_from_csv(db)
            symbol_upper = symbol.upper()
            
            for instrument in instruments_data:
                if (instrument.get('name', '').upper() == symbol_upper or 
                    instrument.get('underlying_symbol', '').upper() == symbol_upper):
                    if instrument.get('strike_price') is None:  # This is the underlying
                        return instrument.get("underlying_key") or instrument.get("asset_key") or instrument.get("instrument_key")
            
            # If not found in instruments, try common patterns
            if symbol_upper in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']:
                return f"NSE_INDEX|{symbol_upper}"
            else:
                return f"NSE_EQ|{symbol_upper}"
                
        except Exception as e:
            logger.error(f"Error getting underlying key for {symbol}: {e}")
            return None

    def _get_contracts_from_local_data(
        self, symbol: str, db: Session, expiry_date: str = None
    ) -> Optional[List[OptionContract]]:
        """Fallback method to get contracts from local data"""
        try:
            instruments_data = self._get_instrument_data_from_csv(db)
            if not instruments_data:
                return None

            contracts = []
            symbol_upper = symbol.upper()

            for instrument in instruments_data:
                try:
                    if (instrument.get('name', '').upper() == symbol_upper or 
                        instrument.get('underlying_symbol', '').upper() == symbol_upper):
                        
                        if (instrument.get('strike_price') is not None and 
                            instrument.get('instrument_type') in ['CE', 'PE']):
                            
                            expiry = self._convert_timestamp_to_date(instrument.get('expiry', 0))
                            
                            # Filter by expiry if specified
                            if expiry_date and expiry != expiry_date:
                                continue
                            
                            contract = OptionContract(
                                instrument_key=instrument.get("instrument_key", ""),
                                name=instrument.get("name", ""),
                                expiry=expiry,
                                strike_price=float(instrument.get("strike_price", 0)),
                                option_type=instrument.get("instrument_type", ""),
                                exchange=instrument.get("exchange", ""),
                                segment=instrument.get("segment", ""),
                                trading_symbol=instrument.get("trading_symbol", ""),
                                lot_size=int(instrument.get("lot_size", 0)),
                                tick_size=float(instrument.get("tick_size", 0.05)),
                                underlying_symbol=symbol_upper,
                            )
                            contracts.append(contract)
                            
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing local contract data: {e}")
                    continue

            return contracts

        except Exception as e:
            logger.error(f"Error getting contracts from local data: {e}")
            return None

    def get_futures_contracts(
        self, symbol: str, db: Session
    ) -> Optional[List[FuturesContract]]:
        """Get futures contracts for a symbol"""
        try:
            # Get instrument data from local file
            instruments_data = self._get_instrument_data_from_csv(db)
            if not instruments_data:
                logger.error("No instrument data available")
                return None

            futures = []
            symbol_upper = symbol.upper()

            # Filter instruments for this symbol and futures contracts
            for instrument in instruments_data:
                try:
                    if (instrument.get('name', '').upper() == symbol_upper or 
                        instrument.get('underlying_symbol', '').upper() == symbol_upper):
                        
                        # Check if this is a futures contract (no strike price and segment includes FUT)
                        if (instrument.get('strike_price') is None and 
                            'FUT' in instrument.get('segment', '').upper()):
                            
                            expiry_date = self._convert_timestamp_to_date(instrument.get('expiry', 0))
                            
                            future = FuturesContract(
                                instrument_key=instrument.get("instrument_key", ""),
                                name=instrument.get("name", ""),
                                expiry=expiry_date,
                                exchange=instrument.get("exchange", ""),
                                segment=instrument.get("segment", ""),
                                trading_symbol=instrument.get("trading_symbol", ""),
                                lot_size=int(instrument.get("lot_size", 0)),
                                tick_size=float(instrument.get("tick_size", 0.05)),
                                underlying_symbol=symbol_upper,
                            )
                            futures.append(future)

                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing futures contract data: {e}")
                    continue

            logger.info(f"Retrieved {len(futures)} futures contracts for {symbol}")
            return futures

        except Exception as e:
            logger.error(f"Error getting futures contracts for {symbol}: {e}")
            return None

    def get_option_chain(
        self, instrument_key: str, expiry_date: str = None, db: Session = None
    ) -> Optional[OptionChainData]:
        """Get option chain using Upstox API - EXACTLY as per documentation"""
        try:
            # If no expiry_date provided, get the nearest expiry first
            if not expiry_date:
                logger.info(f"No expiry provided for option chain, fetching nearest expiry for {instrument_key}")
                expiry_date = self.get_nearest_expiry(instrument_key, db)
                if not expiry_date:
                    logger.error(f"Could not get valid expiry date for option chain {instrument_key}")
                    return None
                else:
                    logger.info(f"Using nearest expiry for option chain: {expiry_date}")

            cache_key = f"chain_{instrument_key}_{expiry_date}"

            # Check cache (shorter timeout for chain data)
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if datetime.now() - timestamp < timedelta(seconds=60):  # 1 minute cache
                    logger.info(f"Returning cached option chain for {instrument_key}")
                    return cached_data

            # Make API call to get option chain - EXACTLY as per documentation
            endpoint = "/option/chain"
            params = {
                "instrument_key": instrument_key,
                "expiry_date": expiry_date  # Required parameter as per docs
            }
            
            logger.info(f"Fetching option chain for {instrument_key} with expiry {expiry_date}")

            api_response = self._make_upstox_request(endpoint, params, db)
            if not api_response:
                logger.error("API call failed for option chain")
                return None

            # Parse API response exactly as per documentation format
            options_map = {}
            strike_prices = set()
            underlying_spot_price = None
            pcr = None

            for option_data in api_response:
                try:
                    strike_price = float(option_data.get("strike_price", 0))
                    underlying_spot_price = option_data.get("underlying_spot_price")
                    pcr = option_data.get("pcr")
                    
                    strike_prices.add(strike_price)
                    strike_key = str(strike_price)
                    
                    if strike_key not in options_map:
                        options_map[strike_key] = {}

                    # Process call options
                    if "call_options" in option_data:
                        call_data = option_data["call_options"]
                        call_contract = OptionContract(
                            instrument_key=call_data.get("instrument_key", ""),
                            name="",  # Not provided in chain API
                            expiry=expiry_date,
                            strike_price=strike_price,
                            option_type="CE",
                            exchange="",  # Extract from instrument_key if needed
                            segment="",   # Extract from instrument_key if needed
                            trading_symbol="",  # Not provided in chain API
                            lot_size=0,   # Not provided in chain API
                            tick_size=0,  # Not provided in chain API
                            underlying_symbol="",  # Extract from instrument_key if needed
                        )
                        options_map[strike_key]["CE"] = call_contract

                    # Process put options
                    if "put_options" in option_data:
                        put_data = option_data["put_options"]
                        put_contract = OptionContract(
                            instrument_key=put_data.get("instrument_key", ""),
                            name="",  # Not provided in chain API
                            expiry=expiry_date,
                            strike_price=strike_price,
                            option_type="PE",
                            exchange="",  # Extract from instrument_key if needed
                            segment="",   # Extract from instrument_key if needed
                            trading_symbol="",  # Not provided in chain API
                            lot_size=0,   # Not provided in chain API
                            tick_size=0,  # Not provided in chain API
                            underlying_symbol="",  # Extract from instrument_key if needed
                        )
                        options_map[strike_key]["PE"] = put_contract

                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing option chain data: {e}")
                    continue

            # Create option chain data
            option_chain = OptionChainData(
                underlying_symbol="",  # Extract from instrument_key if needed
                underlying_key=instrument_key,
                spot_price=underlying_spot_price,
                expiry_dates=[expiry_date],
                strike_prices=sorted(list(strike_prices)),
                options=options_map,
                futures=[],  # Chain API doesn't provide futures
                generated_at=datetime.now(),
            )

            # Cache the results
            self.cache[cache_key] = (option_chain, datetime.now())

            logger.info(f"Retrieved option chain for {instrument_key}: {len(strike_prices)} strikes")
            return option_chain

        except Exception as e:
            logger.error(f"Error getting option chain for {instrument_key}: {e}")
            return None

    def _parse_api_option_chain(self, api_response: dict, symbol: str) -> dict:
        """Parse API response into option chain data"""
        try:
            expiry_dates = set()
            strike_prices = set()
            options_map = {}
            spot_price = api_response.get('underlying_spot_price')

            # Parse options data from API
            for option_data in api_response.get('data', []):
                expiry_date = option_data.get('expiry', '')
                strike_price = float(option_data.get('strike_price', 0))
                option_type = option_data.get('instrument_type', '')

                expiry_dates.add(expiry_date)
                strike_prices.add(strike_price)

                # Create contract
                contract = OptionContract(
                    instrument_key=option_data.get("instrument_key", ""),
                    name=option_data.get("name", ""),
                    expiry=expiry_date,
                    strike_price=strike_price,
                    option_type=option_type,
                    exchange=option_data.get("exchange", ""),
                    segment=option_data.get("segment", ""),
                    trading_symbol=option_data.get("trading_symbol", ""),
                    lot_size=int(option_data.get("lot_size", 0)),
                    tick_size=float(option_data.get("tick_size", 0.05)),
                    underlying_symbol=symbol,
                )

                # Organize by strike and option type
                strike_key = str(strike_price)
                if strike_key not in options_map:
                    options_map[strike_key] = {}

                options_map[strike_key][option_type] = contract

            return {
                'options': options_map,
                'expiry_dates': sorted(list(expiry_dates)),
                'strike_prices': sorted(list(strike_prices)),
                'spot_price': spot_price
            }

        except Exception as e:
            logger.error(f"Error parsing API option chain data: {e}")
            return None

    def _get_option_chain_from_local_data(self, symbol: str, expiry: str = None, db: Session = None) -> dict:
        """Get option chain from local data as fallback"""
        try:
            instruments_data = self._get_instrument_data_from_csv(db)
            if not instruments_data:
                return None

            symbol_upper = symbol.upper()
            underlying_key = ""
            
            expiry_dates = set()
            strike_prices = set()
            options_map = {}

            # Process options data from instrument file
            for instrument in instruments_data:
                try:
                    if (instrument.get('name', '').upper() == symbol_upper or 
                        instrument.get('underlying_symbol', '').upper() == symbol_upper):
                        
                        # Check if it's an option contract
                        if (instrument.get('strike_price') is not None and 
                            instrument.get('instrument_type') in ['CE', 'PE']):
                            
                            expiry_timestamp = instrument.get("expiry", 0)
                            expiry_date = self._convert_timestamp_to_date(expiry_timestamp)
                            strike_price = float(instrument.get("strike_price", 0))
                            option_type = instrument.get("instrument_type", "")

                            # Filter by expiry if specified
                            if expiry and expiry_date != expiry:
                                continue

                            expiry_dates.add(expiry_date)
                            strike_prices.add(strike_price)

                            # Create contract
                            contract = OptionContract(
                                instrument_key=instrument.get("instrument_key", ""),
                                name=instrument.get("name", ""),
                                expiry=expiry_date,
                                strike_price=strike_price,
                                option_type=option_type,
                                exchange=instrument.get("exchange", ""),
                                segment=instrument.get("segment", ""),
                                trading_symbol=instrument.get("trading_symbol", ""),
                                lot_size=int(instrument.get("lot_size", 0)),
                                tick_size=float(instrument.get("tick_size", 0.05)),
                                underlying_symbol=symbol_upper,
                            )

                            # Organize by strike and option type
                            strike_key = str(strike_price)
                            if strike_key not in options_map:
                                options_map[strike_key] = {}

                            options_map[strike_key][option_type] = contract
                        
                        # Check for underlying stock
                        elif (instrument.get('name', '').upper() == symbol_upper and 
                              instrument.get('strike_price') is None and
                              instrument.get('asset_type') in ['EQUITY', 'INDEX']):
                            underlying_key = instrument.get("underlying_key", "") or instrument.get("asset_key", "")

                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing local option chain data: {e}")
                    continue

            return {
                'options': options_map,
                'expiry_dates': sorted(list(expiry_dates)),
                'strike_prices': sorted(list(strike_prices)),
                'spot_price': None  # Will be fetched from live data
            }

        except Exception as e:
            logger.error(f"Error getting option chain from local data: {e}")
            return None

    def get_fno_instruments(self, db: Session) -> Optional[List[str]]:
        """Get list of F&O eligible instruments"""
        try:
            cache_key = "fno_instruments"

            # Check cache (longer timeout for instrument list)
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if datetime.now() - timestamp < timedelta(seconds=3600):  # 1 hour cache
                    return cached_data

            # Get instrument data from local file
            instruments_data = self._get_instrument_data_from_csv(db)
            if not instruments_data:
                logger.error("No instrument data available")
                return []

            fno_symbols = set()
            
            # Extract all symbols that have option contracts
            for instrument in instruments_data:
                if instrument.get('strike_price') is not None:
                    underlying = instrument.get('underlying_symbol', '').upper()
                    name = instrument.get('name', '').upper()
                    if underlying:
                        fno_symbols.add(underlying)
                    elif name:
                        fno_symbols.add(name)

            fno_stocks = sorted(list(fno_symbols))

            # Cache the results
            self.cache[cache_key] = (fno_stocks, datetime.now())

            logger.info(f"Found {len(fno_stocks)} F&O eligible instruments")
            return fno_stocks

        except Exception as e:
            logger.error(f"Error getting F&O instruments: {e}")
            return []

    def is_fno_stock(self, symbol: str, db: Session) -> bool:
        """Check if a symbol is F&O eligible"""
        try:
            fno_instruments = self.get_fno_instruments(db)
            return (
                symbol.upper() in [s.upper() for s in fno_instruments]
                if fno_instruments
                else False
            )
        except Exception as e:
            logger.error(f"Error checking F&O eligibility for {symbol}: {e}")
            return False

    def clear_cache(self):
        """Clear the service cache"""
        self.cache.clear()
        logger.info("Option service cache cleared")


# Singleton instance
upstox_option_service = UpstoxOptionService()


# Convenience functions
def get_option_contracts_for_instrument_key(
    instrument_key: str, db: Session = None, expiry_date: str = None
) -> Optional[List[OptionContract]]:
    """Get option contracts for an instrument key"""
    if not db:
        from database.connection import SessionLocal
        db = SessionLocal()

    return upstox_option_service.get_option_contracts(instrument_key, db, expiry_date)


def get_option_chain_for_instrument_key(
    instrument_key: str, expiry_date: str, db: Session = None
) -> Optional[OptionChainData]:
    """Get complete option chain for an instrument key"""
    if not db:
        from database.connection import SessionLocal
        db = SessionLocal()

    return upstox_option_service.get_option_chain(instrument_key, expiry_date, db)


def get_fno_instruments_list(db: Session = None) -> List[str]:
    """Get list of F&O eligible instruments"""
    if not db:
        from database.connection import SessionLocal

        db = SessionLocal()

    return upstox_option_service.get_fno_instruments(db) or []


def is_symbol_fno_eligible(symbol: str, db: Session = None) -> bool:
    """Check if symbol is F&O eligible"""
    if not db:
        from database.connection import SessionLocal

        db = SessionLocal()

    return upstox_option_service.is_fno_stock(symbol, db)


def get_instrument_expiry_dates(instrument_key: str, db: Session = None) -> List[str]:
    """Get available expiry dates for an instrument"""
    if not db:
        from database.connection import SessionLocal
        db = SessionLocal()

    return upstox_option_service.get_expiry_dates(instrument_key, db) or []


def get_instrument_nearest_expiry(instrument_key: str, db: Session = None) -> str:
    """Get the nearest expiry date for an instrument"""
    if not db:
        from database.connection import SessionLocal
        db = SessionLocal()

    return upstox_option_service.get_nearest_expiry(instrument_key, db)
