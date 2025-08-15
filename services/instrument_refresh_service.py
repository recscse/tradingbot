# service/instrument_refresh_service.py
"""
Complete Trading Instrument Service with Upstox Symbol Mappings + Advanced Key System
"""

import asyncio
import gzip
import json
import logging
import time
import aiohttp
from io import BytesIO
from datetime import datetime, timedelta, time as dt_time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from collections import defaultdict
import aiofiles
from functools import wraps
from dataclasses import dataclass, asdict
import pytz
import psutil
import gc

# Redis import with fallback
try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Configuration constants
UPSTOX_COMPLETE_URL = (
    "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"
)
CACHE_TTL = 86400  # 24 hours
MAX_WEBSOCKET_INSTRUMENTS = 1500  # Upstox limit
BATCH_SIZE = 1000
OPTION_STRIKE_RANGE = 40  # ±40 strikes

# HARDCODED Essential Instruments - Always the same
ESSENTIAL_INDICES = {
    "NIFTY", "NIFTY 50", "NIFTY50",
    "BANKNIFTY", "NIFTYBANK", "BANK NIFTY", 
    "FINNIFTY", "FIN NIFTY", "NIFTY FINANCIAL SERVICES",
    "SENSEX",
    "MIDCPNIFTY", "NIFTY MIDCAP 50"
}

ESSENTIAL_COMMODITIES = {
    "CRUDEOIL", "CRUDEOILM", "CRUDE", "CRUDEOLI",  # Crude oil variations
    "GOLD", "GOLDM", "GOLDPETAL"  # Gold variations
}

# Index keywords for filtering  
ESSENTIAL_INDEX_KEYWORDS = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]


def get_memory_usage():
    """Get current memory usage in MB"""
    try:
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except:
        return None

def performance_timer(func):
    """Decorator to measure function performance and memory usage"""

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = get_memory_usage()
        result = await func(*args, **kwargs)
        duration = time.time() - start_time
        end_memory = get_memory_usage()
        
        memory_str = ""
        if start_memory and end_memory:
            memory_diff = end_memory - start_memory
            memory_str = f", Memory: {end_memory:.1f}MB ({memory_diff:+.1f}MB)"
        
        logger.info(f"⚡ {func.__name__} executed in {duration:.3f}s{memory_str}")
        return result

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = get_memory_usage()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        end_memory = get_memory_usage()
        
        memory_str = ""
        if start_memory and end_memory:
            memory_diff = end_memory - start_memory
            memory_str = f", Memory: {end_memory:.1f}MB ({memory_diff:+.1f}MB)"
        
        logger.info(f"⚡ {func.__name__} executed in {duration:.3f}s{memory_str}")
        return result

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


@dataclass
class InstrumentData:
    """Optimized instrument data structure"""

    instrument_key: str
    trading_symbol: str
    name: str
    exchange: str
    segment: str
    instrument_type: str
    expiry: Optional[str]
    strike_price: Optional[float]
    lot_size: int
    tick_size: float
    underlying_symbol: Optional[str]
    asset_symbol: Optional[str]
    last_price: Optional[float]
    close_price: Optional[float]


@dataclass
class ServiceStats:
    """Service statistics"""

    initialized: bool
    total_stocks_mapped: int
    total_instrument_keys: int
    websocket_keys: int
    dashboard_keys: int
    trading_stocks_count: int
    mcx_instruments: int
    cache_available: bool
    last_update: str
    processing_time: Optional[float] = None
    memory_usage_mb: Optional[float] = None


@dataclass
class InitializationResult:
    """Initialization result"""

    status: str
    processing_time: float
    total_stocks: int
    filtered_instruments: int
    mapped_stocks: int
    websocket_instruments: int
    dashboard_instruments: int
    trading_instruments: int
    mcx_instruments: int
    cache_keys_created: int
    memory_saved_mb: float
    initialized_at: str
    error: Optional[str] = None


@dataclass
class MarketDataSubscription:
    """Market data subscription configuration"""

    total_keys: int
    spot_keys: List[str]
    index_keys: List[str]
    futures_keys: List[str]
    options_keys: List[str]
    mcx_keys: List[str]
    breakdown: Dict[str, int]
    strategy: str
    created_at: str


class OptimizedCache:
    """High-performance in-memory cache with TTL support"""

    def __init__(self):
        self._data = {}
        self._expiry = {}
        self._lock = asyncio.Lock()

    async def ping(self):
        return True

    async def setex(self, key: str, ttl: int, value: str):
        async with self._lock:
            self._data[key] = value
            self._expiry[key] = time.time() + ttl

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            if key in self._data:
                if key in self._expiry and time.time() > self._expiry[key]:
                    del self._data[key]
                    del self._expiry[key]
                    return None
                return self._data[key]
            return None

    async def mget(self, keys: List[str]) -> List[Optional[str]]:
        async with self._lock:
            self._cleanup_expired()
            return [self._data.get(key) for key in keys]

    async def keys(self, pattern: str) -> List[str]:
        import fnmatch

        async with self._lock:
            self._cleanup_expired()
            return [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]

    async def delete(self, *keys):
        async with self._lock:
            for key in keys:
                self._data.pop(key, None)
                self._expiry.pop(key, None)

    def _cleanup_expired(self):
        current_time = time.time()
        expired_keys = [
            k for k, exp_time in self._expiry.items() if current_time > exp_time
        ]
        for k in expired_keys:
            self._data.pop(k, None)
            self._expiry.pop(k, None)


class TradingInstrumentKeyManager:
    """Advanced instrument key manager with two-tier strategy"""

    def __init__(self, trading_service):
        self.service = trading_service
        self.MAX_REALTIME_KEYS = 1500
        self.MAX_TRADING_KEYS = 5000  # Higher limit for active trading

        # Dashboard configuration
        self.DASHBOARD_CONFIG = {
            "spot_stocks_limit": 250,  # Top liquid stocks
            "index_limit": 15,  # Major indices
            "nifty_futures_limit": 5,  # Near month NIFTY futures
            "nifty_options_strikes": 20,  # ±10 strikes from ATM
            "mcx_crude_futures": 3,  # Current + next 2 months
            "mcx_crude_options": 30,  # ±8 strikes from ATM
            "mcx_gold_futures": 3,  # Current + next 2 months
            "mcx_gold_options": 20,  # ±5 strikes from ATM
        }

        # Active trading configuration (when stock selected)
        self.TRADING_CONFIG = {
            "spot_key": 1,  # Single spot instrument
            "futures_limit": 3,  # Near 3 months
            "options_strikes_range": 40,  # ±20 strikes from ATM
            "include_weekly": True,  # Include weekly expiries
        }

    def get_dashboard_realtime_keys(self) -> MarketDataSubscription:
        """Get optimized keys for dashboard and stock analysis"""
        if not self.service.is_initialized():
            return self._empty_subscription("Service not initialized")

        logger.info("🔧 Building dashboard real-time subscription keys...")

        # Step 1: Get spot stocks from top_stocks.json
        spot_keys = self._get_top_spot_stocks()

        # Step 2: Get major indices
        index_keys = self._get_major_indices()

        # Step 3: Get NIFTY 50 futures (limited)
        nifty_futures = self._get_nifty_futures_limited()

        # Step 4: Get NIFTY 50 options (ATM range)
        nifty_options = self._get_nifty_options_atm()

        # Step 5: Get MCX CRUDE OIL instruments
        mcx_crude_keys = self._get_mcx_crude_limited()

        # Step 6: Get MCX GOLD instruments
        mcx_gold_keys = self._get_mcx_gold_limited()

        # Combine all keys
        all_keys = []
        all_keys.extend(spot_keys)
        all_keys.extend(index_keys)
        all_keys.extend(nifty_futures)
        all_keys.extend(nifty_options)
        all_keys.extend(mcx_crude_keys)
        all_keys.extend(mcx_gold_keys)

        # Remove duplicates and apply limit
        unique_keys = list(set([k for k in all_keys if k]))
        if len(unique_keys) > self.MAX_REALTIME_KEYS:
            unique_keys = unique_keys[: self.MAX_REALTIME_KEYS]
            logger.warning(
                f"⚠️ Truncated to {self.MAX_REALTIME_KEYS} keys for dashboard"
            )

        # Calculate breakdown
        breakdown = self._calculate_breakdown(unique_keys, "dashboard")

        return MarketDataSubscription(
            total_keys=len(unique_keys),
            spot_keys=spot_keys,
            index_keys=index_keys,
            futures_keys=nifty_futures,
            options_keys=nifty_options
            + [k for k in mcx_crude_keys + mcx_gold_keys if self._is_option_key(k)],
            mcx_keys=mcx_crude_keys + mcx_gold_keys,
            breakdown=breakdown,
            strategy="dashboard_analysis",
            created_at=datetime.now().isoformat(),
        )

    def get_active_trading_keys(self, symbol: str) -> MarketDataSubscription:
        """Get comprehensive keys for active trading of selected stock"""
        if not self.service.is_initialized():
            return self._empty_subscription("Service not initialized")

        symbol = symbol.upper()
        logger.info(f"🎯 Building active trading keys for {symbol}...")

        stock_data = self.service.get_stock_instruments(symbol)
        if not stock_data:
            return self._empty_subscription(f"Stock {symbol} not found")

        instruments = stock_data.get("instruments", {})

        # Step 1: Get spot instrument (single key)
        spot_key = self._get_stock_spot_key(instruments)

        # Step 2: Get futures (3 near months)
        futures_keys = self._get_stock_futures_extended(instruments)

        # Step 3: Get options (±20 strikes = 40 total strikes)
        options_keys = self._get_stock_options_full_range(instruments, symbol)

        # Combine all keys for this stock
        all_keys = []
        if spot_key:
            all_keys.append(spot_key)
        all_keys.extend(futures_keys)
        all_keys.extend(options_keys)

        # Remove duplicates
        unique_keys = list(set([k for k in all_keys if k]))

        # Calculate breakdown
        breakdown = self._calculate_breakdown(unique_keys, "trading", symbol)

        logger.info(f"🎯 Active trading keys for {symbol}: {len(unique_keys)} total")

        return MarketDataSubscription(
            total_keys=len(unique_keys),
            spot_keys=[spot_key] if spot_key else [],
            index_keys=[],  # Not needed for individual stock trading
            futures_keys=futures_keys,
            options_keys=options_keys,
            mcx_keys=[],  # Not needed for equity trading
            breakdown=breakdown,
            strategy=f"active_trading_{symbol}",
            created_at=datetime.now().isoformat(),
        )

    def _get_top_spot_stocks(self) -> List[str]:
        """Get top liquid spot stocks from top_stocks.json"""
        spot_keys = []

        # Get all stock mappings
        for symbol, mapping in self.service._stock_mappings.items():
            instruments = mapping.get("instruments", {})

            # Get EQ (spot) instruments only
            for instr in instruments.get("EQ", []):
                if instr.instrument_key and "NSE_EQ|" in instr.instrument_key:
                    spot_keys.append(instr.instrument_key)
                    break  # One spot key per stock

        # Limit to configured amount
        limited_keys = spot_keys[: self.DASHBOARD_CONFIG["spot_stocks_limit"]]
        logger.info(f"📈 Selected {len(limited_keys)} spot stock keys")
        return limited_keys

    def _get_major_indices(self) -> List[str]:
        """Get major index keys"""
        index_keys = []
        major_indices = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]

        for index_symbol in major_indices:
            if index_symbol in self.service._stock_mappings:
                instruments = self.service._stock_mappings[index_symbol].get(
                    "instruments", {}
                )

                # Get INDEX instruments
                for instr in instruments.get("INDEX", []):
                    if instr.instrument_key:
                        index_keys.append(instr.instrument_key)
                        break  # One index key per index

        # Limit to configured amount
        limited_keys = index_keys[: self.DASHBOARD_CONFIG["index_limit"]]
        logger.info(f"📊 Selected {len(limited_keys)} index keys")
        return limited_keys

    def _get_nifty_futures_limited(self) -> List[str]:
        """Get limited NIFTY 50 futures for dashboard"""
        futures_keys = []

        if "NIFTY" in self.service._stock_mappings:
            instruments = self.service._stock_mappings["NIFTY"].get("instruments", {})

            # Get futures and sort by expiry (nearest first)
            nifty_futures = instruments.get("FUT", [])
            if nifty_futures:
                # Sort by expiry to get nearest months
                sorted_futures = sorted(nifty_futures, key=lambda x: x.expiry or "")

                # Take limited number for dashboard
                for fut in sorted_futures[
                    : self.DASHBOARD_CONFIG["nifty_futures_limit"]
                ]:
                    if fut.instrument_key:
                        futures_keys.append(fut.instrument_key)

        logger.info(f"📅 Selected {len(futures_keys)} NIFTY futures for dashboard")
        return futures_keys

    def _get_nifty_options_atm(self) -> List[str]:
        """Get ATM NIFTY 50 options for dashboard"""
        options_keys = []

        if "NIFTY" in self.service._stock_mappings:
            instruments = self.service._stock_mappings["NIFTY"].get("instruments", {})

            ce_options = instruments.get("CE", [])
            pe_options = instruments.get("PE", [])

            if ce_options and pe_options:
                # Get ATM range (middle strikes)
                strikes_range = self.DASHBOARD_CONFIG["nifty_options_strikes"] // 2

                # CE options (middle range)
                if len(ce_options) > strikes_range * 2:
                    mid_point = len(ce_options) // 2
                    atm_ce = ce_options[
                        mid_point - strikes_range : mid_point + strikes_range
                    ]
                    options_keys.extend(
                        [opt.instrument_key for opt in atm_ce if opt.instrument_key]
                    )

                # PE options (middle range)
                if len(pe_options) > strikes_range * 2:
                    mid_point = len(pe_options) // 2
                    atm_pe = pe_options[
                        mid_point - strikes_range : mid_point + strikes_range
                    ]
                    options_keys.extend(
                        [opt.instrument_key for opt in atm_pe if opt.instrument_key]
                    )

        logger.info(f"🎯 Selected {len(options_keys)} NIFTY ATM options for dashboard")
        return options_keys

    def _get_mcx_crude_limited(self) -> List[str]:
        """Get limited MCX CRUDE OIL instruments for dashboard"""
        mcx_keys = []

        for crude_symbol in ["CRUDEOIL", "CRUDEOILM"]:
            if crude_symbol in self.service._stock_mappings:
                instruments = self.service._stock_mappings[crude_symbol].get(
                    "instruments", {}
                )

                # Get limited futures (near months only)
                futures = instruments.get("FUT", [])
                if futures:
                    sorted_futures = sorted(futures, key=lambda x: x.expiry or "")
                    for fut in sorted_futures[
                        : self.DASHBOARD_CONFIG["mcx_crude_futures"]
                    ]:
                        if fut.instrument_key and "MCX_FO|" in fut.instrument_key:
                            mcx_keys.append(fut.instrument_key)

                # Get ATM options (limited range)
                ce_options = instruments.get("CE", [])
                pe_options = instruments.get("PE", [])

                if ce_options and pe_options:
                    strikes_range = (
                        self.DASHBOARD_CONFIG["mcx_crude_options"] // 4
                    )  # ±8 strikes

                    # ATM CE options
                    if len(ce_options) > strikes_range * 2:
                        mid_point = len(ce_options) // 2
                        atm_ce = ce_options[
                            mid_point - strikes_range : mid_point + strikes_range
                        ]
                        mcx_keys.extend(
                            [
                                opt.instrument_key
                                for opt in atm_ce
                                if opt.instrument_key
                                and "MCX_FO|" in opt.instrument_key
                            ]
                        )

                    # ATM PE options
                    if len(pe_options) > strikes_range * 2:
                        mid_point = len(pe_options) // 2
                        atm_pe = pe_options[
                            mid_point - strikes_range : mid_point + strikes_range
                        ]
                        mcx_keys.extend(
                            [
                                opt.instrument_key
                                for opt in atm_pe
                                if opt.instrument_key
                                and "MCX_FO|" in opt.instrument_key
                            ]
                        )

                break  # Use first available (CRUDEOIL preferred over CRUDEOILM)

        logger.info(f"🛢️ Selected {len(mcx_keys)} CRUDE OIL instruments for dashboard")
        return mcx_keys

    def _get_mcx_gold_limited(self) -> List[str]:
        """Get limited MCX GOLD instruments for dashboard"""
        mcx_keys = []

        for gold_symbol in ["GOLD", "GOLDM"]:
            if gold_symbol in self.service._stock_mappings:
                instruments = self.service._stock_mappings[gold_symbol].get(
                    "instruments", {}
                )

                # Get limited futures
                futures = instruments.get("FUT", [])
                if futures:
                    sorted_futures = sorted(futures, key=lambda x: x.expiry or "")
                    for fut in sorted_futures[
                        : self.DASHBOARD_CONFIG["mcx_gold_futures"]
                    ]:
                        if fut.instrument_key and "MCX_FO|" in fut.instrument_key:
                            mcx_keys.append(fut.instrument_key)

                # Get ATM options
                ce_options = instruments.get("CE", [])
                pe_options = instruments.get("PE", [])

                if ce_options and pe_options:
                    strikes_range = (
                        self.DASHBOARD_CONFIG["mcx_gold_options"] // 4
                    )  # ±5 strikes

                    # ATM CE options
                    if len(ce_options) > strikes_range * 2:
                        mid_point = len(ce_options) // 2
                        atm_ce = ce_options[
                            mid_point - strikes_range : mid_point + strikes_range
                        ]
                        mcx_keys.extend(
                            [
                                opt.instrument_key
                                for opt in atm_ce
                                if opt.instrument_key
                                and "MCX_FO|" in opt.instrument_key
                            ]
                        )

                    # ATM PE options
                    if len(pe_options) > strikes_range * 2:
                        mid_point = len(pe_options) // 2
                        atm_pe = pe_options[
                            mid_point - strikes_range : mid_point + strikes_range
                        ]
                        mcx_keys.extend(
                            [
                                opt.instrument_key
                                for opt in atm_pe
                                if opt.instrument_key
                                and "MCX_FO|" in opt.instrument_key
                            ]
                        )

                break  # Use first available

        logger.info(f"🥇 Selected {len(mcx_keys)} GOLD instruments for dashboard")
        return mcx_keys

    def _get_stock_spot_key(self, instruments: Dict) -> Optional[str]:
        """Get single spot key for active trading"""
        for instr in instruments.get("EQ", []):
            if instr.instrument_key:
                return instr.instrument_key
        return None

    def _get_stock_futures_extended(self, instruments: Dict) -> List[str]:
        """Get extended futures for active trading (3 months)"""
        futures_keys = []

        futures = instruments.get("FUT", [])
        if futures:
            # Sort by expiry and take near months
            sorted_futures = sorted(futures, key=lambda x: x.expiry or "")
            for fut in sorted_futures[: self.TRADING_CONFIG["futures_limit"]]:
                if fut.instrument_key:
                    futures_keys.append(fut.instrument_key)

        logger.info(f"📅 Selected {len(futures_keys)} futures for active trading")
        return futures_keys

    def _get_stock_options_full_range(
        self, instruments: Dict, symbol: str
    ) -> List[str]:
        """Get full options range for active trading (±20 strikes)"""
        options_keys = []

        ce_options = instruments.get("CE", [])
        pe_options = instruments.get("PE", [])

        if ce_options and pe_options:
            strikes_range = (
                self.TRADING_CONFIG["options_strikes_range"] // 2
            )  # ±20 strikes

            # For indices, we might want wider range
            if symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY"]:
                strikes_range = min(strikes_range, 25)  # Cap at ±25 for indices

            # CE options (extended range)
            if len(ce_options) > strikes_range * 2:
                mid_point = len(ce_options) // 2
                extended_ce = ce_options[
                    max(0, mid_point - strikes_range) : mid_point + strikes_range
                ]
                options_keys.extend(
                    [opt.instrument_key for opt in extended_ce if opt.instrument_key]
                )
            else:
                # If total options < range, take all
                options_keys.extend(
                    [opt.instrument_key for opt in ce_options if opt.instrument_key]
                )

            # PE options (extended range)
            if len(pe_options) > strikes_range * 2:
                mid_point = len(pe_options) // 2
                extended_pe = pe_options[
                    max(0, mid_point - strikes_range) : mid_point + strikes_range
                ]
                options_keys.extend(
                    [opt.instrument_key for opt in extended_pe if opt.instrument_key]
                )
            else:
                # If total options < range, take all
                options_keys.extend(
                    [opt.instrument_key for opt in pe_options if opt.instrument_key]
                )

        logger.info(
            f"🎯 Selected {len(options_keys)} options for {symbol} active trading"
        )
        return options_keys

    def _is_option_key(self, instrument_key: str) -> bool:
        """Check if instrument key is an option"""
        if instrument_key in self.service._instrument_by_key:
            instr = self.service._instrument_by_key[instrument_key]
            trading_symbol = getattr(instr, "trading_symbol", "")
            instr_type = getattr(instr, "instrument_type", "").upper()
            return (
                instr_type in ["CE", "PE"]
                or " CE " in trading_symbol
                or " PE " in trading_symbol
            )
        return False

    def _calculate_breakdown(
        self, keys: List[str], strategy: str, symbol: str = None
    ) -> Dict[str, int]:
        """Calculate detailed breakdown of instrument keys"""
        breakdown = {
            "total": len(keys),
            "spot_stocks": 0,
            "indices": 0,
            "equity_futures": 0,
            "index_futures": 0,
            "equity_options": 0,
            "index_options": 0,
            "mcx_futures": 0,
            "mcx_options": 0,
        }

        for key in keys:
            if not key or key not in self.service._instrument_by_key:
                continue

            instr = self.service._instrument_by_key[key]
            trading_symbol = getattr(instr, "trading_symbol", "")
            instr_type = getattr(instr, "instrument_type", "").upper()

            # Categorize by exchange and type
            if "NSE_EQ|" in key:
                breakdown["spot_stocks"] += 1
            elif "NSE_INDEX|" in key or "BSE_INDEX|" in key:
                breakdown["indices"] += 1
            elif "NSE_FO|" in key:
                # Check if it's index or equity derivative
                is_index = any(
                    idx in trading_symbol
                    for idx in ["NIFTY", "SENSEX", "FINNIFTY", "MIDCPNIFTY"]
                )

                if instr_type in ["FUT", "FUTIDX"] or "FUT" in trading_symbol:
                    if is_index:
                        breakdown["index_futures"] += 1
                    else:
                        breakdown["equity_futures"] += 1
                elif (
                    instr_type in ["CE", "PE"]
                    or " CE " in trading_symbol
                    or " PE " in trading_symbol
                ):
                    if is_index:
                        breakdown["index_options"] += 1
                    else:
                        breakdown["equity_options"] += 1
            elif "MCX_FO|" in key:
                if (
                    instr_type in ["CE", "PE"]
                    or " CE " in trading_symbol
                    or " PE " in trading_symbol
                ):
                    breakdown["mcx_options"] += 1
                elif instr_type in ["FUT", "FUTCOM"] or "FUT" in trading_symbol:
                    breakdown["mcx_futures"] += 1

        # Add strategy-specific info
        breakdown["strategy"] = strategy
        if symbol:
            breakdown["target_symbol"] = symbol

        return breakdown

    def _empty_subscription(self, reason: str) -> MarketDataSubscription:
        """Return empty subscription with error reason"""
        return MarketDataSubscription(
            total_keys=0,
            spot_keys=[],
            index_keys=[],
            futures_keys=[],
            options_keys=[],
            mcx_keys=[],
            breakdown={"error": reason, "total": 0},
            strategy="error",
            created_at=datetime.now().isoformat(),
        )


class TradingInstrumentService:
    """High-Performance Trading Instrument Service with Upstox Mappings + Advanced Key System"""

    _instance = None
    _lock = asyncio.Lock()

    # Upstox-specific symbol mappings - Based on actual top_stocks.json
    UPSTOX_SYMBOL_MAPPINGS = {
        "ZOMATO": ["ZOMATO", "ETERNAL", "ZOMATOLIMITED"],
        # Index mappings based on your top_stocks.json
        "NIFTY": [
            "NIFTY",
            "NIFTY 50",
            "NIFTY50",
        ],  # From your data: trading_symbol="NIFTY", name="Nifty 50"
        "BANKNIFTY": ["BANKNIFTY", "NIFTYBANK", "BANK NIFTY"],
        "FINNIFTY": ["FINNIFTY", "FIN NIFTY", "NIFTY FINANCIAL SERVICES"],
        "SENSEX": ["SENSEX"],  # From your data: trading_symbol="SENSEX", name="SENSEX"
        "MIDCPNIFTY": ["MIDCPNIFTY", "NIFTY MIDCAP 50"],
        # MCX commodities
        "CRUDEOIL": ["CRUDEOIL", "CRUDEOILM", "CRUDE", "CRUDEOLI"],
        "GOLD": ["GOLD", "GOLDM", "GOLDPETAL", "GLD"],
        "SILVER": ["SILVER", "SILVERM", "SILVERPETAL"],
        "COPPER": ["COPPER", "COPPERM"],
        # Stock mappings
        "M&M": ["MM", "MAHINDRA", "MAHINDRAMAHINDRA", "M&M"],
        "BAJAJ-AUTO": ["BAJAJAUTO", "BAJAJ_AUTO", "BAJAJ", "BAJAJ-AUTO"],
        "PERSISTENT": ["PERSISTENT"],
    }

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self, redis_url: str = "redis://localhost:6379/1", use_redis: bool = True
    ):
        if hasattr(self, "_initialized_instance"):
            return

        self._initialized = False  # Ensure _initialized attribute exists

        self.redis_client = None
        self.redis_url = redis_url
        self.use_redis = use_redis and REDIS_AVAILABLE

        # Data paths
        self.data_dir = Path("data")

        if self.has_stock_data():
            self.top_stocks_file = self.data_dir / "fno_stock_list.json"

        else:
            self.top_stocks_file = self.data_dir / "top_stocks.json"

        self.filtered_instruments_file = self.data_dir / "filtered_instruments.json"

        # High-performance in-memory indexes
        self._instrument_by_key = {}
        self._instruments_by_symbol = defaultdict(list)
        self._instruments_by_exchange_symbol = defaultdict(list)
        self._instruments_by_type = defaultdict(list)

        # Pre-built stock mappings for instant access
        self._stock_mappings = {}
        self._dashboard_keys = []
        self._websocket_keys = []
        self._trading_stock_keys = {}
        self._mcx_keys = []

        # Service state
        self._service_initialized = False
        self._initialization_time = None
        self._last_refresh = None
        self._selected_trading_stocks = set()

        # Market schedule integration
        self.ist = pytz.timezone("Asia/Kolkata")
        self.market_hours = {
            'early_start': dt_time(8, 0),    # 8:00 AM - Early preparation
            'premarket': dt_time(9, 0),      # 9:00 AM - Pre-market  
            'market_open': dt_time(9, 15),   # 9:15 AM - Market open
            'trading_start': dt_time(9, 30), # 9:30 AM - Trading start
            'market_close': dt_time(15, 30)  # 3:30 PM - Market close
        }

        self._initialized_instance = True
        logger.info("🔧 TradingInstrumentService instance created")

    # ========== NULL-SAFE HELPER FUNCTIONS ==========

    def has_stock_data(self) -> bool:
        """Simple check if JSON file has stock data"""
        try:
            data_dir = Path("data")
            path = data_dir / "fno_stock_list.json"
            if not path.exists():
                return False
            with open(path, "r") as f:
                data = json.load(f)
                securities = data.get("securities", [])
                if not securities:
                    return False
            securities = data.get("securities", [])
            return len(securities) > 0

        except:
            logger.warning("⚠️ Error checking stock data file")
            return False

    def safe_upper(self, value):
        """Safely convert value to uppercase string"""
        if value is None:
            return ""
        try:
            return str(value).strip().upper()
        except (TypeError, AttributeError):
            return ""

    def safe_get_string(self, obj, key, default=""):
        """Safely get string value from dict/object"""
        try:
            if hasattr(obj, "get"):
                value = obj.get(key)
            else:
                value = getattr(obj, key, None)
            return str(value or default).strip()
        except (TypeError, AttributeError):
            return default

    def safe_get_float(self, obj, key, default=0.0):
        """Safely get float value from dict/object"""
        try:
            if hasattr(obj, "get"):
                value = obj.get(key)
            else:
                value = getattr(obj, key, None)
            return float(value) if value is not None else default
        except (TypeError, ValueError, AttributeError):
            return default

    def safe_get_int(self, obj, key, default=0):
        """Safely get int value from dict/object"""
        try:
            if hasattr(obj, "get"):
                value = obj.get(key)
            else:
                value = getattr(obj, key, None)
            return int(value) if value is not None else default
        except (TypeError, ValueError, AttributeError):
            return default

    # ========== ADVANCED KEY MANAGEMENT METHODS ==========

    def add_advanced_key_management(self):
        """Add advanced key management capabilities"""
        if not hasattr(self, "key_manager"):
            self.key_manager = TradingInstrumentKeyManager(self)
            logger.info("🔧 Advanced key management system initialized")

    def _is_call_option(self, instrument_key: str) -> bool:
        """Helper to identify call options"""
        if instrument_key in self._instrument_by_key:
            instr = self._instrument_by_key[instrument_key]
            trading_symbol = getattr(instr, "trading_symbol", "")
            instr_type = getattr(instr, "instrument_type", "").upper()
            return instr_type == "CE" or " CE " in trading_symbol
        return False

    def _is_put_option(self, instrument_key: str) -> bool:
        """Helper to identify put options"""
        if instrument_key in self._instrument_by_key:
            instr = self._instrument_by_key[instrument_key]
            trading_symbol = getattr(instr, "trading_symbol", "")
            instr_type = getattr(instr, "instrument_type", "").upper()
            return instr_type == "PE" or " PE " in trading_symbol
        return False

    def get_quick_market_snapshot_keys(self) -> List[str]:
        """Get minimal keys for quick market snapshot"""
        if not hasattr(self, "key_manager"):
            self.add_advanced_key_management()

        snapshot_keys = []

        # Top 50 spot stocks
        spot_keys = self.key_manager._get_top_spot_stocks()
        snapshot_keys.extend(spot_keys[:50])

        # Major indices
        index_keys = self.key_manager._get_major_indices()
        snapshot_keys.extend(index_keys)

        # Current month NIFTY futures only
        if "NIFTY" in self._stock_mappings:
            instruments = self._stock_mappings["NIFTY"].get("instruments", {})
            nifty_futures = instruments.get("FUT", [])
            if nifty_futures:
                sorted_futures = sorted(nifty_futures, key=lambda x: x.expiry or "")
                if sorted_futures[0].instrument_key:
                    snapshot_keys.append(sorted_futures[0].instrument_key)

        # MCX current month only
        for commodity in ["CRUDEOIL", "GOLD"]:
            if commodity in self._stock_mappings:
                instruments = self._stock_mappings[commodity].get("instruments", {})
                futures = instruments.get("FUT", [])
                if futures:
                    sorted_futures = sorted(futures, key=lambda x: x.expiry or "")
                    if sorted_futures[0].instrument_key:
                        snapshot_keys.append(sorted_futures[0].instrument_key)

        return list(set(snapshot_keys))

    # ========== CORE SERVICE METHODS ==========

    async def _ensure_cache_connection(self):
        """Ensure cache connection is established"""
        if self.redis_client is None:
            if self.use_redis:
                try:
                    self.redis_client = redis.from_url(
                        self.redis_url,
                        decode_responses=True,
                        socket_connect_timeout=2,
                        socket_timeout=2,
                    )
                    await self.redis_client.ping()
                    logger.info("✅ Redis connection established")
                    return
                except Exception as e:
                    logger.warning(f"⚠️ Redis unavailable, using in-memory cache: {e}")

            self.redis_client = OptimizedCache()
            logger.info("✅ Using optimized in-memory cache")

    @performance_timer
    async def download_and_filter_instruments(self) -> Tuple[int, int]:
        """Download complete instruments and filter intelligently"""
        logger.info("⬇️ Downloading instruments from complete.json.gz...")

        top_stocks = await self._load_top_stocks()
        if not top_stocks:
            raise ValueError("No top stocks found")

        required_symbols = self._build_symbol_requirements(top_stocks)
        logger.info(f"📋 Filtering for {len(required_symbols)} symbols")

        timeout = aiohttp.ClientTimeout(total=300)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(UPSTOX_COMPLETE_URL) as response:
                if response.status != 200:
                    raise Exception(
                        f"Failed to download instruments: {response.status}"
                    )

                content = await response.read()
                logger.info(f"📦 Downloaded {len(content)} bytes")

        # Process data with memory optimization
        filtered_instruments = []
        current_time = datetime.now()
        total_count = 0
        
        try:
            with gzip.GzipFile(fileobj=BytesIO(content)) as gz:
                # Load and process in memory-efficient way
                all_instruments = json.load(gz)
                total_count = len(all_instruments)
                logger.info(f"📦 Parsed {total_count} total instruments")
                
                # Process in batches to reduce memory pressure
                batch_size = 1000
                for i in range(0, len(all_instruments), batch_size):
                    batch = all_instruments[i:i + batch_size]
                    for instrument in batch:
                        if self._should_include_instrument(
                            instrument, required_symbols, current_time
                        ):
                            filtered_instruments.append(instrument)
                    
                    # Progress logging and memory monitoring
                    if i % 10000 == 0:
                        current_memory = get_memory_usage()
                        logger.info(f"🔄 Processed {i}/{total_count} instruments, filtered: {len(filtered_instruments)}, Memory: {current_memory:.1f}MB")
                        
                        # If memory usage is getting too high, limit processing
                        if current_memory and current_memory > 1500:  # 1.5GB limit
                            logger.warning(f"⚠️ Memory usage high ({current_memory:.1f}MB), limiting to {len(filtered_instruments)} instruments")
                            break
                
                # Clear the large array from memory
                del all_instruments
                    
        except Exception as e:
            logger.error(f"❌ Failed to decompress/parse data: {e}")
            raise
        finally:
            # Clear content from memory
            del content

        # Write filtered data efficiently to avoid memory spikes
        self.data_dir.mkdir(exist_ok=True)
        
        # Use compact JSON format to reduce memory usage
        async with aiofiles.open(self.filtered_instruments_file, "w") as f:
            await f.write(json.dumps(filtered_instruments, separators=(',', ':')))

        logger.info(f"💾 Saved {len(filtered_instruments)} filtered instruments")
        return total_count, len(filtered_instruments)

    def _build_symbol_requirements(self, top_stocks: List[Dict]) -> Set[str]:
        """Build FOCUSED symbol requirements - FnO stocks + HARDCODED indices + Essential commodities"""
        required_symbols = set()

        logger.info("🎯 Building FOCUSED symbol requirements (FnO stocks + Hardcoded indices + Commodities)")

        # 1. HARDCODED Essential Indices - Always the same
        required_symbols.update(ESSENTIAL_INDICES)
        logger.info(f"📈 Added {len(ESSENTIAL_INDICES)} hardcoded indices")

        # 2. HARDCODED Essential MCX Commodities - Always the same
        required_symbols.update(ESSENTIAL_COMMODITIES)
        logger.info(f"🛢️ Added {len(ESSENTIAL_COMMODITIES)} hardcoded commodity variations")

        # 3. DYNAMIC FnO stocks from the provided list
        fno_count = 0
        for stock in top_stocks:
            symbol = self.safe_upper(stock.get("symbol"))
            exchange = self.safe_upper(stock.get("exchange"))

            if symbol and exchange == "NSE":  # Only NSE F&O stocks
                required_symbols.add(symbol)
                required_symbols.add(symbol.replace("-", ""))
                required_symbols.add(symbol.replace("&", ""))
                required_symbols.add(symbol.replace(" ", ""))

                # Add Upstox-specific mappings for F&O stocks only
                if symbol in self.UPSTOX_SYMBOL_MAPPINGS:
                    upstox_variations = self.UPSTOX_SYMBOL_MAPPINGS[symbol]
                    required_symbols.update(upstox_variations)

                fno_count += 1

        logger.info(f"📊 Added {fno_count} dynamic FnO stocks from NSE")

        logger.info(f"🎯 FOCUSED filtering: {len(required_symbols)} total symbols")
        logger.info(f"   📈 Indices: {len(ESSENTIAL_INDICES)} (hardcoded)")
        logger.info(f"   🛢️ Commodities: {len(ESSENTIAL_COMMODITIES)} (hardcoded)")
        logger.info(f"   📊 FnO Stocks: {fno_count} (dynamic)")
        return required_symbols

    def _should_include_instrument(
        self, instrument: Dict, required_symbols: Set[str], current_time: datetime
    ) -> bool:
        """FOCUSED filtering: ONLY FnO stocks + Crude Oil + Gold + Sensex"""
        if not instrument.get("instrument_key"):
            return False

        # Check expiry to filter out expired instruments
        expiry = instrument.get("expiry")
        if expiry:
            try:
                if isinstance(expiry, (int, float)):
                    expiry_date = datetime.fromtimestamp(expiry / 1000)
                elif isinstance(expiry, str) and expiry:
                    for fmt in ["%Y-%m-%d", "%d %b %Y", "%Y%m%d"]:
                        try:
                            expiry_date = datetime.strptime(expiry, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        expiry_date = None

                if expiry_date and expiry_date < (current_time - timedelta(days=2)):
                    return False
            except (ValueError, TypeError):
                pass

        # Get key instrument fields
        trading_symbol = self.safe_upper(instrument.get("trading_symbol"))
        name = self.safe_upper(instrument.get("name"))
        exchange = self.safe_upper(instrument.get("exchange"))
        symbol = self.safe_upper(instrument.get("symbol"))
        underlying_symbol = self.safe_upper(instrument.get("underlying_symbol"))
        instrument_type = self.safe_upper(instrument.get("instrument_type"))

        # FOCUSED: Include hardcoded essential indices only
        if instrument_type == "INDEX":
            for keyword in ESSENTIAL_INDEX_KEYWORDS:
                if (keyword in trading_symbol or keyword in name or 
                    keyword in underlying_symbol):
                    return True
            return False  # Exclude all other indices

        # FOCUSED: MCX - only include essential commodities
        if exchange == "MCX":
            commodity_keywords = ["CRUDEOIL", "CRUDE", "GOLD"]
            for keyword in commodity_keywords:
                if (keyword in trading_symbol or keyword in name or 
                    keyword in underlying_symbol or keyword in symbol):
                    return True
            return False  # Exclude all other MCX instruments
        
        # FOCUSED: BSE - only include SENSEX derivatives
        if exchange == "BSE":
            if ("SENSEX" not in trading_symbol and "SENSEX" not in name and 
                "SENSEX" not in underlying_symbol):
                return False

        # For all other instruments, check if they match required symbols
        search_fields = [
            "trading_symbol",
            "name",
            "symbol",
            "short_name",
            "underlying_symbol",
            "asset_symbol",
            "display_name",
        ]

        for field in search_fields:
            field_value = instrument.get(field)
            if not field_value:
                continue

            field_value = self.safe_upper(field_value)
            if not field_value:
                continue

            # Direct match with required symbols
            if field_value in required_symbols:
                return True

            # Check for partial matches or prefix matches
            for req_symbol in required_symbols:
                if not req_symbol:
                    continue

                try:
                    # Full symbol match
                    if req_symbol == field_value:
                        return True

                    # Partial symbol match
                    if (
                        req_symbol in field_value
                        or field_value.startswith(req_symbol)
                        or (field == "underlying_symbol" and req_symbol == field_value)
                    ):
                        return True

                    # FOCUSED: Simple matching for our limited set
                    # No complex NIFTY logic needed since we only want SENSEX + FnO stocks + commodities
                except (TypeError, AttributeError):
                    continue

        # If we get here, no match was found
        return False

    async def _load_top_stocks(self) -> List[Dict]:
        """Load top stocks configuration"""
        try:
            if not self.top_stocks_file.exists():

                logger.warning(f"⚠️ Top stocks file not found: {self.top_stocks_file}")

                return self._get_fallback_stocks()

            async with aiofiles.open(self.top_stocks_file, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

            if isinstance(data, dict) and "securities" in data:
                stocks = data["securities"]
            elif isinstance(data, list):
                stocks = data
            else:
                logger.warning("⚠️ Invalid top_stocks.json format")
                return self._get_fallback_stocks()

            logger.info(f"📋 Loaded {len(stocks)} stocks from top_stocks.json")
            return stocks

        except Exception as e:
            logger.warning(f"⚠️ Error loading top stocks: {e}")
            return self._get_fallback_stocks()

    def _get_fallback_stocks(self) -> List[Dict]:
        """Fallback stock data - Updated to match actual Upstox data structure"""
        return [
            {"symbol": "RELIANCE", "name": "Reliance Industries", "exchange": "NSE"},
            {"symbol": "TCS", "name": "Tata Consultancy Services", "exchange": "NSE"},
            {"symbol": "HDFCBANK", "name": "HDFC Bank", "exchange": "NSE"},
            {"symbol": "INFY", "name": "Infosys", "exchange": "NSE"},
            {"symbol": "ICICIBANK", "name": "ICICI Bank", "exchange": "NSE"},
            {"symbol": "ZOMATO", "name": "Zomato", "exchange": "NSE"},
            {"symbol": "PERSISTENT", "name": "Persistent Systems", "exchange": "NSE"},
            # Index mappings based on actual data structure
            {
                "symbol": "NIFTY50-INDEX",
                "name": "Nifty 50",
                "exchange": "NSE",
            },  # Maps to trading_symbol="NIFTY"
            {"symbol": "NIFTYBANK-INDEX", "name": "Bank Nifty", "exchange": "NSE"},
            {"symbol": "FINNIFTY-INDEX", "name": "Fin Nifty", "exchange": "NSE"},
            {
                "symbol": "SENSEX-INDEX",
                "name": "SENSEX",
                "exchange": "BSE",
            },  # Maps to trading_symbol="SENSEX"
            {"symbol": "CRUDEOIL", "name": "Crude Oil", "exchange": "MCX"},
            {"symbol": "GOLD", "name": "Gold", "exchange": "MCX"},
            {"symbol": "SILVER", "name": "Silver", "exchange": "MCX"},
        ]

    def _get_primary_instrument_key(self, instruments: Dict) -> Optional[str]:
        """Get primary instrument key (EQ > INDEX > FUT)"""
        for instr_type in ["EQ", "INDEX", "FUT"]:
            if instruments.get(instr_type):
                return instruments[instr_type][0].instrument_key
        return None

    def _get_websocket_keys_for_stock(self, instruments: Dict) -> List[str]:
        """Enhanced WebSocket key generation"""
        keys = []

        # Always include primary (EQ/INDEX)
        for instr_type in ["EQ", "INDEX"]:
            for instr in instruments.get(instr_type, []):
                if instr.instrument_key:
                    keys.append(instr.instrument_key)

        # Include futures (up to 5 nearest)
        for instr in instruments.get("FUT", [])[:5]:
            if instr.instrument_key:
                keys.append(instr.instrument_key)

        # Include options with ATM selection
        for instr_type in ["CE", "PE"]:
            options = instruments.get(instr_type, [])
            if options:
                if len(options) > 20:
                    mid_start = max(0, len(options) // 2 - 10)
                    mid_end = min(len(options), len(options) // 2 + 10)
                    selected = options[mid_start:mid_end]
                    keys.extend(
                        [
                            instr.instrument_key
                            for instr in selected
                            if instr.instrument_key
                        ]
                    )
                else:
                    keys.extend(
                        [
                            instr.instrument_key
                            for instr in options
                            if instr.instrument_key
                        ]
                    )

        return keys

    def _get_all_trading_keys_for_stock(self, instruments: Dict) -> List[str]:
        """Get ALL instrument keys for trading"""
        keys = []

        for instr_type in ["EQ", "INDEX", "FUT", "CE", "PE"]:
            for instr in instruments.get(instr_type, []):
                if instr.instrument_key:
                    keys.append(instr.instrument_key)

        return keys

    def _build_dashboard_keys(self) -> List[str]:
        """Build dashboard keys (all EQ and INDEX)"""
        dashboard_keys = []

        for instr_type in ["EQ", "INDEX"]:
            for instr in self._instruments_by_type.get(instr_type, []):
                if instr.instrument_key:
                    dashboard_keys.append(instr.instrument_key)

        logger.info(f"📊 Built {len(dashboard_keys)} dashboard keys")
        return dashboard_keys

    def _build_websocket_keys(self) -> List[str]:
        """Build WebSocket keys with enhanced safety"""
        logger.info("🔗 Building WebSocket keys...")
        all_keys = []

        # Collect from all stock mappings
        for symbol, mapping in self._stock_mappings.items():
            websocket_keys = mapping.get("websocket_keys", [])
            if isinstance(websocket_keys, list) and websocket_keys:
                all_keys.extend([key for key in websocket_keys if key])
                logger.info(
                    f"✅ Added {len(websocket_keys)} WebSocket keys for {symbol}"
                )

        # Add MCX keys
        if isinstance(self._mcx_keys, list) and self._mcx_keys:
            all_keys.extend([key for key in self._mcx_keys if key])
            logger.info(f"✅ Added {len(self._mcx_keys)} MCX keys to WebSocket")

        # Add dashboard keys if we're short
        if len(all_keys) < 500:
            dashboard_keys = self._dashboard_keys[:1000]
            if isinstance(dashboard_keys, list) and dashboard_keys:
                all_keys.extend([key for key in dashboard_keys if key])
                logger.info(
                    f"✅ Added {len(dashboard_keys)} dashboard keys to WebSocket"
                )

        # Remove duplicates
        unique_keys = list(
            set([key for key in all_keys if key and isinstance(key, str)])
        )
        logger.info(f"📊 Total unique WebSocket keys before limit: {len(unique_keys)}")

        # Apply Upstox limit with prioritization
        if len(unique_keys) > MAX_WEBSOCKET_INSTRUMENTS:
            priority_keys = []
            secondary_keys = []
            option_keys = []

            for key in unique_keys:
                if key and isinstance(key, str):
                    if "_EQ|" in key or "_INDEX|" in key:
                        priority_keys.append(key)
                    elif "_FO|" in key and ("FUT" in key or "FUTIDX" in key):
                        secondary_keys.append(key)
                    elif "_FO|" in key and (
                        "CE" in key or "PE" in key or "OPTIDX" in key
                    ):
                        option_keys.append(key)
                    elif "_COM|" in key:  # MCX commodities
                        priority_keys.append(key)
                    else:
                        secondary_keys.append(key)

            final_keys = []
            # Prioritize: EQ/INDEX (400) + MCX (200) + Futures (300) + Options (600)
            final_keys.extend(priority_keys[:600])

            remaining = MAX_WEBSOCKET_INSTRUMENTS - len(final_keys)
            final_keys.extend(secondary_keys[: remaining // 2])

            remaining = MAX_WEBSOCKET_INSTRUMENTS - len(final_keys)
            final_keys.extend(option_keys[:remaining])

            unique_keys = final_keys[:MAX_WEBSOCKET_INSTRUMENTS]

            logger.info(
                f"🎯 Prioritized WebSocket keys: EQ/INDEX={len(priority_keys[:600])}, FUT={len(secondary_keys[:remaining//2])}, Options={len(option_keys[:remaining])}"
            )

        logger.info(
            f"🔗 Built {len(unique_keys)} WebSocket keys (limit: {MAX_WEBSOCKET_INSTRUMENTS})"
        )
        return unique_keys

    def _build_mcx_keys(self) -> List[str]:
        """Build MCX commodity keys"""
        mcx_keys = []

        # Use hardcoded essential commodities
        mcx_symbols = ["CRUDEOIL", "GOLD"]  # Only essential commodities
        for symbol in mcx_symbols:
            search_symbols = [symbol]
            if symbol in self.UPSTOX_SYMBOL_MAPPINGS:
                search_symbols.extend(self.UPSTOX_SYMBOL_MAPPINGS[symbol])

            for search_symbol in search_symbols:
                mcx_instruments = self._instruments_by_exchange_symbol.get(
                    f"MCX_{search_symbol}", []
                )

                # Add futures first
                for instr in mcx_instruments:
                    try:
                        if (
                            self.safe_upper(instr.instrument_type) in ["FUT", "FUTCOM"]
                            and instr.instrument_key
                            and "MCX_FO|" in instr.instrument_key
                        ):
                            mcx_keys.append(instr.instrument_key)
                    except (TypeError, AttributeError):
                        continue

                # Add options (CE and PE)
                for instr in mcx_instruments:
                    try:
                        if (
                            self.safe_upper(instr.instrument_type) in ["CE", "PE"]
                            and instr.instrument_key
                            and "MCX_FO|" in instr.instrument_key
                        ):
                            mcx_keys.append(instr.instrument_key)
                    except (TypeError, AttributeError):
                        continue

        mcx_keys = list(set(mcx_keys))
        logger.info(f"🏭 Built {len(mcx_keys)} MCX keys (format: MCX_FO|)")
        return mcx_keys

    async def _should_download_fresh_data(self) -> bool:
        """Check if fresh data download is needed with market schedule compliance"""
        # Check market schedule compliance first
        schedule_check = self.is_market_schedule_compliant()
        logger.info(f"🕰️ Market schedule: {schedule_check['message']}")
        
        # If market schedule says use cache, honor it (unless data doesn't exist)
        if not schedule_check["compliant"] and schedule_check.get("use_cache", False):
            if self.filtered_instruments_file.exists():
                logger.info("📂 Market schedule restricts refresh - using cached data")
                return False
            else:
                logger.warning("⚠️ Market schedule restricts refresh but no cached data available - allowing download")
        
        # Original logic continues
        if not self.filtered_instruments_file.exists():
            return True

        file_stat = self.filtered_instruments_file.stat()
        file_age = datetime.now() - datetime.fromtimestamp(file_stat.st_mtime)

        if file_age > timedelta(hours=6):
            logger.info("📅 Filtered instruments file is old, downloading fresh data")
            return True

        # Check if file was created on a different day
        file_date = datetime.fromtimestamp(file_stat.st_mtime).date()
        current_date = datetime.now().date()
        if file_date < current_date:
            logger.info("📅 New trading day detected, downloading fresh data")
            return True

        return False
    
    def is_market_schedule_compliant(self) -> Dict[str, Any]:
        """
        Check if instrument refresh is allowed based on market schedule
        """
        try:
            current_time = datetime.now(self.ist)
            current_dt_time = current_time.time()
            
            # Check if it's a weekday
            if current_time.weekday() >= 5:
                return {
                    "compliant": False,
                    "reason": "weekend",
                    "message": "Market closed - Weekend",
                    "next_update_time": "Monday 08:00 AM",
                    "use_cache": True
                }
            
            # Allow updates during early preparation (8:00-9:00 AM)
            if self.market_hours['early_start'] <= current_dt_time < self.market_hours['premarket']:
                return {
                    "compliant": True,
                    "reason": "early_preparation",
                    "message": "Early preparation window - safe to refresh instruments",
                    "current_time": current_time.strftime("%H:%M:%S"),
                    "use_cache": False
                }
            
            # Check if data is stale (older than 12 hours) - force refresh
            if self.filtered_instruments_file.exists():
                file_mtime = datetime.fromtimestamp(self.filtered_instruments_file.stat().st_mtime, tz=self.ist)
                hours_old = (current_time - file_mtime).total_seconds() / 3600
                
                if hours_old > 12:
                    return {
                        "compliant": True,
                        "reason": "stale_data", 
                        "message": f"Instrument data is {hours_old:.1f} hours old - refresh needed",
                        "last_update": file_mtime.strftime("%Y-%m-%d %H:%M:%S"),
                        "use_cache": False
                    }
            
            # During market hours, use cached data only
            if self.market_hours['market_open'] <= current_dt_time <= self.market_hours['market_close']:
                return {
                    "compliant": False,
                    "reason": "market_hours",
                    "message": "Market is open - using cached data to avoid disruption",
                    "next_update_time": "After 3:30 PM",
                    "use_cache": True
                }
            
            # Before market or after market - allow limited updates
            return {
                "compliant": True,
                "reason": "off_hours",
                "message": "Market closed - safe to refresh if needed",
                "current_time": current_time.strftime("%H:%M:%S"),
                "use_cache": False
            }
            
        except Exception as e:
            logger.error(f"Market schedule compliance check failed: {e}")
            return {
                "compliant": True,
                "reason": "error_fallback",
                "message": f"Schedule check error: {str(e)}",
                "use_cache": False
            }

    async def _count_existing_instruments(self) -> int:
        """Count existing instruments"""
        try:
            async with aiofiles.open(self.filtered_instruments_file, "r") as f:
                content = await f.read()
                instruments = json.loads(content)
                return len(instruments)
        except Exception:
            return 0

    async def _load_filtered_instruments(self) -> List[Dict]:
        """Load filtered instruments"""
        try:
            async with aiofiles.open(self.filtered_instruments_file, "r") as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"❌ Error loading filtered instruments: {e}")
            return []

    async def _cache_all_data(
        self,
        stock_mappings: Dict,
        dashboard_keys: List[str],
        websocket_keys: List[str],
        mcx_keys: List[str],
    ) -> int:
        """Cache all data for production use"""
        logger.info("💾 Caching all data...")

        try:
            cache_count = 0

            for symbol, mapping in stock_mappings.items():
                cache_key = f"stock_mapping:{symbol}"
                await self.redis_client.setex(
                    cache_key, CACHE_TTL, json.dumps(mapping, default=str)
                )
                cache_count += 1

            await self.redis_client.setex(
                "dashboard_keys", CACHE_TTL, json.dumps(dashboard_keys)
            )
            await self.redis_client.setex(
                "websocket_keys", CACHE_TTL, json.dumps(websocket_keys)
            )
            await self.redis_client.setex("mcx_keys", CACHE_TTL, json.dumps(mcx_keys))
            cache_count += 3

            for symbol, keys in self._trading_stock_keys.items():
                cache_key = f"trading_keys:{symbol}"
                await self.redis_client.setex(cache_key, CACHE_TTL, json.dumps(keys))
                cache_count += 1

            logger.info(f"💾 Cached {cache_count} data sets")
            return cache_count

        except Exception as e:
            logger.error(f"❌ Error caching data: {e}")
            return 0

    @performance_timer
    async def initialize_service(self) -> InitializationResult:
        """Complete service initialization"""
        start_time = time.time()
        logger.info("🚀 Initializing Trading Instrument Service...")

        try:
            await self._ensure_cache_connection()

            should_download = await self._should_download_fresh_data()
            if should_download:
                total_downloaded, filtered_count = (
                    await self.download_and_filter_instruments()
                )
            else:
                logger.info("📂 Using existing filtered instruments")
                filtered_count = await self._count_existing_instruments()
                total_downloaded = 0

            instruments = await self._load_filtered_instruments()
            await self._build_high_performance_indexes(instruments)

            top_stocks = await self._load_top_stocks()
            stock_mappings = await self._build_stock_mappings(top_stocks)

            dashboard_keys = self._build_dashboard_keys()
            mcx_keys = self._build_mcx_keys()

            # Set MCX keys first, then build WebSocket keys
            self._mcx_keys = mcx_keys
            websocket_keys = self._build_websocket_keys()

            cache_keys_created = await self._cache_all_data(
                stock_mappings, dashboard_keys, websocket_keys, mcx_keys
            )

            self._stock_mappings = stock_mappings
            self._dashboard_keys = dashboard_keys
            self._websocket_keys = websocket_keys
            self._mcx_keys = mcx_keys
            self._service_initialized = True
            self._initialization_time = datetime.now()
            self._last_refresh = datetime.now()

            # Initialize advanced key management
            self.add_advanced_key_management()

            # Log what was built
            logger.info(
                f"📊 Final counts: Dashboard={len(dashboard_keys)}, WebSocket={len(websocket_keys)}, MCX={len(mcx_keys)}"
            )

            end_time = time.time()
            processing_time = end_time - start_time

            result = InitializationResult(
                status="success",
                processing_time=processing_time,
                total_stocks=len(top_stocks),
                filtered_instruments=filtered_count,
                mapped_stocks=len(stock_mappings),
                websocket_instruments=len(websocket_keys),
                dashboard_instruments=len(dashboard_keys),
                trading_instruments=len(self._trading_stock_keys),
                mcx_instruments=len(mcx_keys),
                cache_keys_created=cache_keys_created,
                memory_saved_mb=(total_downloaded - filtered_count) * 0.001,
                initialized_at=datetime.now().isoformat(),
            )

            logger.info(
                f"✅ Service initialized successfully in {processing_time:.2f}s"
            )
            return result

        except Exception as e:
            error_msg = f"Service initialization failed: {e}"
            logger.error(f"❌ {error_msg}")
            return InitializationResult(
                status="error",
                processing_time=time.time() - start_time,
                total_stocks=0,
                filtered_instruments=0,
                mapped_stocks=0,
                websocket_instruments=0,
                dashboard_instruments=0,
                trading_instruments=0,
                mcx_instruments=0,
                cache_keys_created=0,
                memory_saved_mb=0,
                initialized_at=datetime.now().isoformat(),
                error=error_msg,
            )

    @performance_timer
    async def _build_high_performance_indexes(self, instruments: List[Dict]):
        """Build O(1) lookup indexes with memory optimization"""
        logger.info(f"🏗️ Building indexes for {len(instruments)} instruments...")
        
        # Clear existing indexes to free memory
        self._instrument_by_key.clear()
        self._instruments_by_symbol.clear()
        self._instruments_by_exchange_symbol.clear()
        self._instruments_by_type.clear()

        # Count instruments by type for logging
        count_by_type = defaultdict(int)
        count_by_exchange = defaultdict(int)
        processed = 0

        # Process instruments in batches to reduce memory pressure
        batch_size = 500
        for i in range(0, len(instruments), batch_size):
            batch = instruments[i:i + batch_size]
            
            for instrument in batch:
                instrument_key = instrument.get("instrument_key")
                if not instrument_key:
                    continue

                try:
                    instr_data = InstrumentData(
                        instrument_key=instrument_key,
                        trading_symbol=self.safe_get_string(instrument, "trading_symbol"),
                        name=self.safe_get_string(instrument, "name"),
                        exchange=self.safe_get_string(instrument, "exchange"),
                        segment=self.safe_get_string(instrument, "segment"),
                        instrument_type=self.safe_get_string(instrument, "instrument_type"),
                        expiry=instrument.get("expiry"),
                        strike_price=self.safe_get_float(instrument, "strike_price"),
                        lot_size=self.safe_get_int(instrument, "lot_size", 1),
                        tick_size=self.safe_get_float(instrument, "tick_size", 0.01),
                        underlying_symbol=instrument.get("underlying_symbol"),
                        asset_symbol=instrument.get("asset_symbol"),
                        last_price=self.safe_get_float(instrument, "last_price"),
                        close_price=self.safe_get_float(instrument, "close_price"),
                    )

                    # Track counts for logging
                    count_by_type[instr_data.instrument_type] += 1
                    count_by_exchange[instr_data.exchange] += 1
                    processed += 1

                except (TypeError, ValueError) as e:
                    logger.warning(
                        f"⚠️ Error creating InstrumentData for {instrument_key}: {e}"
                    )
                    continue

                self._instrument_by_key[instrument_key] = instr_data

                # Optimized symbol indexing - avoid duplicates
                symbol_fields = [
                    "trading_symbol",
                    "symbol", 
                    "name",
                    "underlying_symbol",  # Added to ensure derivatives are properly indexed
                ]

                # Use set to avoid duplicate indexing
                indexed_symbols = set()
                
                # First index the primary identifiers
                for field in symbol_fields:
                    symbol_value = instrument.get(field)
                    if symbol_value:
                        symbol = self.safe_upper(symbol_value)
                        if symbol and symbol not in indexed_symbols:
                            self._instruments_by_symbol[symbol].append(instr_data)
                            indexed_symbols.add(symbol)
                            
                            # Also index without spaces for better matching (only if different)
                            symbol_no_space = symbol.replace(" ", "")
                            if symbol_no_space != symbol and symbol_no_space not in indexed_symbols:
                                self._instruments_by_symbol[symbol_no_space].append(instr_data)
                                indexed_symbols.add(symbol_no_space)

                # Handle asset_symbol separately (avoid duplicates)
                asset_symbol = self.safe_upper(instrument.get("asset_symbol", ""))
                if asset_symbol and asset_symbol not in indexed_symbols:
                    # Index directly by asset_symbol
                    self._instruments_by_symbol[asset_symbol].append(instr_data)
                    indexed_symbols.add(asset_symbol)

                # Create mapping from asset_symbol to actual symbols
                if not hasattr(self, "_asset_symbol_mappings"):
                    self._asset_symbol_mappings = {}
                if asset_symbol not in self._asset_symbol_mappings:
                    self._asset_symbol_mappings[asset_symbol] = set()
                trading_symbol = self.safe_upper(instrument.get("trading_symbol", ""))
                self._asset_symbol_mappings[asset_symbol].add(trading_symbol)

                # Index by exchange_symbol combination (optimized)
                exchange_value = instrument.get("exchange")
                if exchange_value:
                    exchange = self.safe_upper(exchange_value)
                    if exchange:
                        exchange_symbols = set()
                        for field in symbol_fields:
                            symbol_value = instrument.get(field)
                            if symbol_value:
                                symbol = self.safe_upper(symbol_value)
                                if symbol:
                                    key = f"{exchange}_{symbol}"
                                    if key not in exchange_symbols:
                                        self._instruments_by_exchange_symbol[key].append(instr_data)
                                        exchange_symbols.add(key)

                # Index by instrument type
                instr_type_value = instrument.get("instrument_type")
                if instr_type_value:
                    instr_type = self.safe_upper(instr_type_value)
                    if instr_type:
                        self._instruments_by_type[instr_type].append(instr_data)
            
            # Progress logging and memory cleanup
            if (i + batch_size) % 2500 == 0 or (i + batch_size) >= len(instruments):
                current_memory = get_memory_usage()
                logger.info(f"🏗️ Processed {min(i + batch_size, len(instruments))}/{len(instruments)} instruments, Memory: {current_memory:.1f}MB")
                # Force garbage collection periodically to free memory
                gc.collect()
                
                # Emergency memory protection
                if current_memory and current_memory > 1800:  # 1.8GB emergency limit
                    logger.error(f"🚨 Emergency memory limit reached ({current_memory:.1f}MB), stopping indexing")
                    break

        # Log any asset symbols that map to multiple trading symbols
        if hasattr(self, "_asset_symbol_mappings"):
            for asset_symbol, trading_symbols in self._asset_symbol_mappings.items():
                if len(trading_symbols) > 1:
                    logger.info(
                        f"ℹ️ Asset symbol {asset_symbol} maps to multiple trading symbols: {trading_symbols}"
                    )

        # Log detailed instrument breakdown
        logger.info(f"🏗️ Built indexes for {len(self._instrument_by_key)} instruments")
        logger.info(f"📊 Instruments by type: {dict(count_by_type)}")
        logger.info(f"📊 Instruments by exchange: {dict(count_by_exchange)}")

        # Calculate derivative coverage
        futures_count = (
            count_by_type.get("FUT", 0)
            + count_by_type.get("FUTIDX", 0)
            + count_by_type.get("FUTCOM", 0)
        )
        options_count = (
            count_by_type.get("CE", 0)
            + count_by_type.get("PE", 0)
            + count_by_type.get("OPTIDX", 0)
        )
        logger.info(
            f"📊 Derivatives coverage: {futures_count} futures, {options_count} options"
        )

    @performance_timer
    async def _build_stock_mappings(self, top_stocks: List[Dict]) -> Dict:
        """Build comprehensive stock mappings"""
        logger.info(f"🎯 Building stock mappings for {len(top_stocks)} stocks...")

        stock_mappings = {}

        for stock in top_stocks:
            symbol = self.safe_upper(stock.get("symbol"))
            exchange = self.safe_upper(stock.get("exchange")) or "NSE"
            name = self.safe_get_string(stock, "name")

            if not symbol:
                continue

            instruments = self._find_all_stock_instruments(symbol, exchange)

            if not instruments or not any(
                len(instr_list) > 0 for instr_list in instruments.values()
            ):
                logger.warning(f"⚠️ No instruments found for {symbol} on {exchange}")
                continue

            primary_key = self._get_primary_instrument_key(instruments)
            websocket_keys = self._get_websocket_keys_for_stock(instruments)
            trading_keys = self._get_all_trading_keys_for_stock(instruments)

            stock_mappings[symbol] = {
                "symbol": symbol,
                "name": name,
                "exchange": exchange,
                "instruments": instruments,
                "primary_instrument_key": primary_key,
                "websocket_keys": websocket_keys,
                "trading_keys": trading_keys,
                "instrument_count": sum(
                    len(instr_list) for instr_list in instruments.values()
                ),
                "has_futures": len(instruments.get("FUT", [])) > 0,
                "has_options": len(instruments.get("CE", [])) > 0
                or len(instruments.get("PE", [])) > 0,
                "last_updated": datetime.now().isoformat(),
            }

            self._trading_stock_keys[symbol] = trading_keys

            # Debug logging for WebSocket keys
            logger.info(f"🔗 WebSocket keys for {symbol}: {len(websocket_keys)} keys")

        logger.info(f"🎯 Built mappings for {len(stock_mappings)} stocks")
        return stock_mappings

    def _find_all_stock_instruments(self, symbol: str, exchange: str) -> Dict:
        """Find all instruments with Upstox mappings"""
        instruments = {"EQ": [], "INDEX": [], "FUT": [], "CE": [], "PE": []}

        if not symbol or not exchange:
            return instruments

        # Get Upstox-specific mappings first
        if symbol in self.UPSTOX_SYMBOL_MAPPINGS:
            search_keys = self.UPSTOX_SYMBOL_MAPPINGS[symbol].copy()
            logger.info(f"🔍 Using Upstox mappings for {symbol}: {search_keys}")
        else:
            search_keys = [
                symbol,
                symbol.replace("-", ""),
                symbol.replace("&", ""),
                symbol.replace(" ", ""),
            ]

        # Add base symbol variations for better matching
        base_search_keys = search_keys.copy()

        # For INDEX symbols, also search without -INDEX suffix
        if "-INDEX" in symbol:
            base_symbol = symbol.replace("-INDEX", "")
            base_search_keys.append(base_symbol)
            if base_symbol in self.UPSTOX_SYMBOL_MAPPINGS:
                base_search_keys.extend(self.UPSTOX_SYMBOL_MAPPINGS[base_symbol])

        search_keys = list(set(base_search_keys))  # Remove duplicates
        logger.info(f"🔍 Final search keys for {symbol}: {search_keys}")

        exchange_prefixed_keys = []
        for key in search_keys:
            exchange_prefixed_keys.extend([f"{exchange}_{key}", key])

        found_instruments = []

        # Search in exchange-symbol index
        for key in exchange_prefixed_keys:
            matches = self._instruments_by_exchange_symbol.get(key, [])
            if matches:
                logger.info(
                    f"✅ Found {len(matches)} instruments for exchange key: {key}"
                )
            found_instruments.extend(matches)

        # Search in general symbol index
        for key in search_keys:
            matches = self._instruments_by_symbol.get(key, [])
            if matches:
                logger.info(f"✅ Found {len(matches)} instruments for symbol: {key}")
            found_instruments.extend(matches)

        # Enhanced partial matching for derivatives and indices - FIXED VERSION
        partial_matches = 0
        for instr_key, instr_data in self._instrument_by_key.items():
            try:
                trading_symbol = self.safe_upper(instr_data.trading_symbol)
                name = self.safe_upper(getattr(instr_data, "name", ""))
                underlying = self.safe_upper(
                    getattr(instr_data, "underlying_symbol", "")
                )
                asset_symbol = self.safe_upper(getattr(instr_data, "asset_symbol", ""))

                # First priority: Check if trading_symbol or name matches
                primary_match = False
                for search_symbol in search_keys:
                    if (
                        search_symbol in trading_symbol
                        or search_symbol in name
                        or trading_symbol.startswith(search_symbol)
                    ):
                        found_instruments.append(instr_data)
                        partial_matches += 1
                        primary_match = True
                        break

                # Only if no primary match, check underlying and asset_symbol, but verify these aren't empty
                if not primary_match:
                    for search_symbol in search_keys:
                        # Only use underlying_symbol and asset_symbol if they're not empty and match the search criteria
                        underlying_match = underlying and (
                            search_symbol in underlying
                            or underlying.startswith(search_symbol)
                        )
                        asset_match = asset_symbol and (
                            search_symbol in asset_symbol
                            or asset_symbol.startswith(search_symbol)
                        )

                        if underlying_match or asset_match:
                            # Verify this actually maps to the target symbol by checking if any primary identifiers contain the target symbol
                            if (
                                symbol in trading_symbol
                                or symbol in name
                                or trading_symbol.startswith(symbol)
                                or any(
                                    alt_symbol in trading_symbol
                                    for alt_symbol in search_keys
                                )
                            ):
                                found_instruments.append(instr_data)
                                partial_matches += 1
                                break

            except (TypeError, AttributeError):
                continue

        if partial_matches > 0:
            logger.info(f"✅ Found {partial_matches} instruments via partial matching")

        # Remove duplicates and categorize
        unique_instruments = {
            instr.instrument_key: instr for instr in found_instruments
        }

        logger.info(
            f"📊 Total unique instruments found for {symbol}: {len(unique_instruments)}"
        )

        for instr in unique_instruments.values():
            try:
                instr_type = self.safe_upper(instr.instrument_type)
                if instr_type in instruments:
                    instruments[instr_type].append(instr)
                else:
                    # Handle other instrument types by mapping them
                    if instr_type in ["FUT", "FUTIDX"]:
                        instruments["FUT"].append(instr)
                    elif instr_type in ["CE", "OPTIDX"]:
                        instruments["CE"].append(instr)
                    elif instr_type in ["PE"]:
                        instruments["PE"].append(instr)
                    elif instr_type in ["EQ", "EQUITY"]:
                        instruments["EQ"].append(instr)
                    elif instr_type in ["INDEX", "IDX"]:
                        instruments["INDEX"].append(instr)
            except (TypeError, AttributeError):
                continue

        # Sort for optimal access
        self._sort_instruments(instruments)

        # Log final results
        total_found = sum(len(instr_list) for instr_list in instruments.values())
        logger.info(
            f"📈 Final categorized instruments for {symbol}: EQ={len(instruments['EQ'])}, INDEX={len(instruments['INDEX'])}, FUT={len(instruments['FUT'])}, CE={len(instruments['CE'])}, PE={len(instruments['PE'])}"
        )

        return instruments

    def _sort_instruments(self, instruments: Dict):
        """Sort instruments for optimal access"""
        if instruments.get("FUT"):
            instruments["FUT"].sort(key=lambda x: str(x.expiry or ""))

        for opt_type in ["CE", "PE"]:
            if instruments.get(opt_type):
                instruments[opt_type].sort(
                    key=lambda x: (str(x.expiry or ""), float(x.strike_price or 0))
                )

    # ========== FIXED OPTIMIZED REAL-TIME KEYS METHOD ==========

    def get_optimized_realtime_keys(self) -> Dict[str, List[str]]:
        """Get optimized keys for real-time data subscription (within 1500 limit) - FIXED"""
        if not self._service_initialized:
            logger.warning("⚠️ Service not initialized")
            return {}

        # Priority 1: Spot prices (EQ + INDEX) - Most important
        spot_keys = self.get_spot_instrument_keys()
        index_keys = self.get_index_instrument_keys()

        # Priority 2: MCX commodities futures and options - FIXED DETECTION
        mcx_futures = []
        mcx_options = []

        for key in self._mcx_keys:
            if key and key in self._instrument_by_key:
                instr = self._instrument_by_key[key]
                trading_symbol = getattr(instr, "trading_symbol", "")
                instr_type = getattr(instr, "instrument_type", "").upper()

                # Proper option detection using instrument_type and trading_symbol
                if (
                    instr_type in ["CE", "PE"]
                    or " CE " in trading_symbol
                    or " PE " in trading_symbol
                ):
                    mcx_options.append(key)
                elif instr_type in ["FUT", "FUTCOM"] or (
                    "FUT" in trading_symbol
                    and "CE" not in trading_symbol
                    and "PE" not in trading_symbol
                ):
                    mcx_futures.append(key)

        # Limit MCX to reasonable numbers
        mcx_futures = mcx_futures[:20]  # Near month futures
        mcx_options = mcx_options[:100]  # ATM options

        # Priority 3: NIFTY futures and options - FIXED DETECTION
        nifty_futures = []
        nifty_options = []

        if "NIFTY" in self._stock_mappings:
            nifty_instruments = self._stock_mappings["NIFTY"].get("instruments", {})

            # Get NIFTY futures (proper detection)
            for instr in nifty_instruments.get("FUT", [])[:10]:  # Limit to 10
                if instr.instrument_key:
                    nifty_futures.append(instr.instrument_key)

            # Get NIFTY options (both CE and PE) - ATM selection
            ce_options = nifty_instruments.get("CE", [])
            pe_options = nifty_instruments.get("PE", [])

            if ce_options and pe_options:
                # Take middle strikes (ATM region)
                mid_ce = len(ce_options) // 2
                mid_pe = len(pe_options) // 2

                # Take ±15 strikes from ATM for both CE and PE
                atm_ce = ce_options[max(0, mid_ce - 15) : mid_ce + 15]
                atm_pe = pe_options[max(0, mid_pe - 15) : mid_pe + 15]

                nifty_options.extend(
                    [instr.instrument_key for instr in atm_ce if instr.instrument_key]
                )
                nifty_options.extend(
                    [instr.instrument_key for instr in atm_pe if instr.instrument_key]
                )

        # Priority 4: BANKNIFTY options (if space allows)
        banknifty_options = []
        if "BANKNIFTY" in self._stock_mappings:
            bn_instruments = self._stock_mappings["BANKNIFTY"].get("instruments", {})
            ce_opts = bn_instruments.get("CE", [])
            pe_opts = bn_instruments.get("PE", [])

            if ce_opts and pe_opts:
                mid_ce = len(ce_opts) // 2
                mid_pe = len(pe_opts) // 2

                # Smaller range for BANKNIFTY (±10 strikes)
                atm_ce = ce_opts[max(0, mid_ce - 10) : mid_ce + 10]
                atm_pe = pe_opts[max(0, mid_pe - 10) : mid_pe + 10]

                banknifty_options.extend(
                    [instr.instrument_key for instr in atm_ce if instr.instrument_key]
                )
                banknifty_options.extend(
                    [instr.instrument_key for instr in atm_pe if instr.instrument_key]
                )

        # Combine all keys with smart prioritization
        all_keys = []
        all_keys.extend(spot_keys[:100])  # Top 100 spot prices
        all_keys.extend(index_keys[:15])  # Top 15 indices
        all_keys.extend(mcx_futures)  # MCX futures (~20)
        all_keys.extend(mcx_options)  # MCX options (~100)
        all_keys.extend(nifty_futures)  # NIFTY futures (~10)
        all_keys.extend(nifty_options[:80])  # NIFTY options (~80)
        all_keys.extend(banknifty_options[:60])  # BANKNIFTY options (~60)

        # Fill remaining space with more spot stocks if under limit
        remaining_space = MAX_WEBSOCKET_INSTRUMENTS - len(set(all_keys))
        if remaining_space > 0:
            additional_spots = [k for k in spot_keys[100:] if k not in all_keys]
            all_keys.extend(additional_spots[:remaining_space])

        # Remove duplicates and apply final limit
        unique_keys = list(set(all_keys))[:MAX_WEBSOCKET_INSTRUMENTS]

        # Calculate accurate breakdown using fixed detection logic
        breakdown = {
            "spot_stocks": len([k for k in unique_keys if "NSE_EQ|" in k]),
            "indices": len(
                [k for k in unique_keys if "NSE_INDEX|" in k or "BSE_INDEX|" in k]
            ),
            "mcx_futures": 0,
            "mcx_options": 0,
            "nifty_futures": 0,
            "nifty_options": 0,
            "banknifty_options": 0,
        }

        # Accurate counting using instrument data
        for key in unique_keys:
            if key in self._instrument_by_key:
                instr = self._instrument_by_key[key]
                trading_symbol = getattr(instr, "trading_symbol", "")
                instr_type = getattr(instr, "instrument_type", "").upper()

                if "MCX_FO|" in key:
                    if (
                        instr_type in ["CE", "PE"]
                        or " CE " in trading_symbol
                        or " PE " in trading_symbol
                    ):
                        breakdown["mcx_options"] += 1
                    elif instr_type in ["FUT", "FUTCOM"] or "FUT" in trading_symbol:
                        breakdown["mcx_futures"] += 1
                elif "NSE_FO|" in key:
                    if "NIFTY" in trading_symbol and "BANKNIFTY" not in trading_symbol:
                        if (
                            instr_type in ["CE", "PE"]
                            or " CE " in trading_symbol
                            or " PE " in trading_symbol
                        ):
                            breakdown["nifty_options"] += 1
                        elif instr_type in ["FUT", "FUTIDX"] or "FUT" in trading_symbol:
                            breakdown["nifty_futures"] += 1
                    elif "BANKNIFTY" in trading_symbol:
                        if (
                            instr_type in ["CE", "PE"]
                            or " CE " in trading_symbol
                            or " PE " in trading_symbol
                        ):
                            breakdown["banknifty_options"] += 1

        result = {
            "total_keys": len(unique_keys),
            "all_keys": unique_keys,
            "breakdown": breakdown,
            "optimization_strategy": {
                "spot_priority": "Top liquid stocks for price discovery",
                "index_coverage": "Major indices (NIFTY, BANKNIFTY, SENSEX)",
                "mcx_focus": "CRUDEOIL, GOLD near-month contracts + ATM options",
                "options_strategy": "ATM ±15 strikes for NIFTY, ±10 for BANKNIFTY",
                "total_utilization": f"{len(unique_keys)}/{MAX_WEBSOCKET_INSTRUMENTS} ({len(unique_keys)/MAX_WEBSOCKET_INSTRUMENTS*100:.1f}%)",
            },
        }

        logger.info(f"🎯 Fixed real-time key optimization: {breakdown}")
        return result

    def get_spot_only_instrument_keys() -> List[Dict[str, Any]]:
        """Get ONLY spot equity instrument keys with essential metadata for dashboard"""
        service = get_trading_service()

        if not service.is_initialized():
            logger.warning("⚠️ Service not initialized")
            return []

        spot_instruments = []

        # Loop through stock mappings to get spot instruments
        for symbol, mapping in service._stock_mappings.items():
            instruments = mapping.get("instruments", {})

            # Get EQ instruments only
            for instr in instruments.get("EQ", []):
                if instr.instrument_key and "NSE_EQ|" in instr.instrument_key:
                    # Include essential metadata for display
                    spot_instruments.append(
                        {
                            "symbol": symbol,
                            "instrument_key": instr.instrument_key,
                            "trading_symbol": getattr(instr, "trading_symbol", symbol),
                            "name": getattr(instr, "name", symbol),
                            "isin": getattr(instr, "isin", ""),
                            "exchange": getattr(instr, "exchange", "NSE"),
                        }
                    )
                    break  # Take only first EQ instrument per stock

        # Add indices
        for index_symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]:
            if index_symbol in service._stock_mappings:
                instruments = service._stock_mappings[index_symbol].get(
                    "instruments", {}
                )

                for instr in instruments.get("INDEX", []):
                    if instr.instrument_key:
                        spot_instruments.append(
                            {
                                "symbol": index_symbol,
                                "instrument_key": instr.instrument_key,
                                "trading_symbol": getattr(
                                    instr, "trading_symbol", index_symbol
                                ),
                                "name": getattr(instr, "name", index_symbol),
                                "is_index": True,
                                "exchange": getattr(instr, "exchange", "NSE"),
                            }
                        )
                        break  # Take only first INDEX instrument per index

        logger.info(
            f"📊 Built {len(spot_instruments)} spot-only instruments for dashboard"
        )
        return spot_instruments

    # ========== PUBLIC API METHODS ==========

    def is_initialized(self) -> bool:
        """Check if service is initialized"""
        return self._service_initialized

    def get_dashboard_instrument_keys(self) -> List[str]:
        """Get all dashboard instrument keys - INSTANT ACCESS"""
        if not self._service_initialized:
            logger.warning("⚠️ Service not initialized")
            return []
        return self._dashboard_keys.copy()

    def get_websocket_instrument_keys(self) -> List[str]:
        """Get WebSocket instrument keys - INSTANT ACCESS"""
        if not self._service_initialized:
            logger.warning("⚠️ Service not initialized")
            return []
        return self._websocket_keys.copy()

    def get_spot_instrument_keys(self) -> List[str]:
        """Get ONLY spot instrument keys (EQ + INDEX) for real-time price data"""
        if not self._service_initialized:
            logger.warning("⚠️ Service not initialized")
            return []

        spot_keys = []

        # Get EQ instruments for all stocks from top_stocks.json
        for symbol, mapping in self._stock_mappings.items():
            instruments = mapping.get("instruments", {})
            # Add EQ (equity spot) instruments
            for instr in instruments.get("EQ", []):
                if instr.instrument_key:
                    spot_keys.append(instr.instrument_key)
            # Add INDEX instruments
            for instr in instruments.get("INDEX", []):
                if instr.instrument_key:
                    spot_keys.append(instr.instrument_key)

        logger.info(f"💰 Built {len(spot_keys)} spot instrument keys")
        return spot_keys

    def get_index_instrument_keys(self) -> List[str]:
        """Get ONLY index instrument keys (NIFTY, BANKNIFTY, SENSEX, etc.)"""
        if not self._service_initialized:
            logger.warning("⚠️ Service not initialized")
            return []

        index_keys = []
        index_symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]

        for symbol in index_symbols:
            if symbol in self._stock_mappings:
                instruments = self._stock_mappings[symbol].get("instruments", {})
                for instr in instruments.get("INDEX", []):
                    if instr.instrument_key:
                        index_keys.append(instr.instrument_key)

        logger.info(f"📈 Built {len(index_keys)} index instrument keys")
        return index_keys

    def get_fno_equity_spot_keys(self) -> List[str]:
        """Get ONLY F&O equity spot keys (NSE_EQ) - for live feed"""
        if not self._service_initialized:
            logger.warning("⚠️ Service not initialized")
            return []

        fno_spot_keys = []

        # Get F&O stocks from the service's stock mappings
        for symbol, mapping in self._stock_mappings.items():
            instruments = mapping.get("instruments", {})

            # Check if stock has F&O instruments (FUT or CE/PE)
            has_futures = len(instruments.get("FUT", [])) > 0
            has_options = (
                len(instruments.get("CE", [])) > 0 or len(instruments.get("PE", [])) > 0
            )

            # Only include if it has F&O and is on NSE
            if (has_futures or has_options) and mapping.get("exchange") == "NSE":
                # Get ONLY EQ (spot) instrument key
                for instr in instruments.get("EQ", []):
                    if instr.instrument_key and "NSE_EQ|" in instr.instrument_key:
                        fno_spot_keys.append(instr.instrument_key)
                        break  # Only one spot key per stock

        logger.info(f"📈 Built {len(fno_spot_keys)} F&O equity spot keys")
        return fno_spot_keys

    def get_selected_index_keys(self, indices: List[str] = None) -> List[str]:
        """Get selected index keys only"""
        if not self._service_initialized:
            logger.warning("⚠️ Service not initialized")
            return []

        if indices is None:
            indices = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]

        index_keys = []

        for index_symbol in indices:
            if index_symbol in self._stock_mappings:
                instruments = self._stock_mappings[index_symbol].get("instruments", {})

                # Get INDEX instrument key
                for instr in instruments.get("INDEX", []):
                    if instr.instrument_key:
                        index_keys.append(instr.instrument_key)
                        logger.debug(f"✅ Index {index_symbol}: {instr.instrument_key}")
                        break  # Only one index key per index

        logger.info(f"📊 Built {len(index_keys)} selected index keys")
        return index_keys

    def get_mcx_futures_keys_only(
        self, commodities: List[str] = None, max_per_commodity: int = 3
    ) -> List[str]:
        """Get MCX futures keys ONLY (no options) for specified commodities"""
        if not self._service_initialized:
            logger.warning("⚠️ Service not initialized")
            return []

        if commodities is None:
            commodities = ["CRUDEOIL", "GOLD"]

        mcx_futures_keys = []

        for commodity in commodities:
            if commodity in self._stock_mappings:
                instruments = self._stock_mappings[commodity].get("instruments", {})

                # Get ONLY FUT instruments (no options)
                commodity_futures = []
                for instr in instruments.get("FUT", []):
                    if instr.instrument_key and "MCX_FO|" in instr.instrument_key:
                        commodity_futures.append(instr.instrument_key)

                # Sort by expiry and take only near months
                if commodity_futures:
                    try:
                        sorted_futures = sorted(
                            commodity_futures,
                            key=lambda x: self._instrument_by_key.get(
                                x, type("obj", (object,), {"expiry": ""})
                            ).expiry
                            or "",
                        )
                    except:
                        sorted_futures = (
                            commodity_futures  # If sorting fails, use as-is
                        )

                    # Take only specified number of near month futures
                    selected_futures = sorted_futures[:max_per_commodity]
                    mcx_futures_keys.extend(selected_futures)

                    logger.debug(f"✅ {commodity}: {len(selected_futures)} futures")

        logger.info(f"🏭 Built {len(mcx_futures_keys)} MCX futures keys")
        return mcx_futures_keys

    def get_focused_websocket_keys(self) -> Dict[str, Any]:
        """Get focused instrument keys for WebSocket subscription"""
        if not self._service_initialized:
            logger.warning("⚠️ Service not initialized")
            return {"keys": [], "breakdown": {}, "total": 0}

        all_keys = []
        breakdown = {
            "fno_equity_spots": 0,
            "selected_indices": 0,
            "mcx_futures": 0,
            "total": 0,
        }

        # 1. Get F&O equity spot keys
        fno_keys = self.get_fno_equity_spot_keys()
        all_keys.extend(fno_keys)
        breakdown["fno_equity_spots"] = len(fno_keys)

        # 2. Get selected index keys
        index_keys = self.get_selected_index_keys()
        index_keys.append("BSE_INDEX|SENSEX")
        all_keys.extend(index_keys)
        breakdown["selected_indices"] = len(index_keys)

        # 3. Get MCX futures keys
        mcx_keys = self.get_mcx_futures_keys_only()
        all_keys.extend(mcx_keys)
        breakdown["mcx_futures"] = len(mcx_keys)

        # Remove duplicates
        unique_keys = list(set(all_keys))
        breakdown["total"] = len(unique_keys)

        logger.info(f"🎯 Built focused WebSocket keys: {breakdown}")

        return {
            "keys": unique_keys,
            "breakdown": breakdown,
            "total": len(unique_keys),
            "strategy": "focused_fno_indices_mcx",
        }


def get_mcx_futures_and_options_keys(
    self, commodities: List[str] = None
) -> Dict[str, List[str]]:
    """Get MCX futures and options keys for specified commodities (MCX_FO only)"""
    if not self._service_initialized:
        logger.warning("⚠️ Service not initialized")
        return {}

    if commodities is None:
        commodities = ["CRUDEOIL", "GOLD", "SILVER"]

    mcx_data = {}

    for commodity in commodities:
        if commodity in self._stock_mappings:
            instruments = self._stock_mappings[commodity].get("instruments", {})

            futures_keys = []
            options_keys = []

            # Get futures (only from MCX_FO)
            for instr in instruments.get("FUT", []):
                if instr.instrument_key and "MCX_FO|" in instr.instrument_key:
                    futures_keys.append(instr.instrument_key)

            # Get options (only from MCX_FO) - both CE and PE
            for instr in instruments.get("CE", []):
                if instr.instrument_key and "MCX_FO|" in instr.instrument_key:
                    options_keys.append(instr.instrument_key)

            for instr in instruments.get("PE", []):
                if instr.instrument_key and "MCX_FO|" in instr.instrument_key:
                    options_keys.append(instr.instrument_key)

            mcx_data[commodity] = {
                "futures": futures_keys,
                "options": options_keys,
                "total_futures": len(futures_keys),
                "total_options": len(options_keys),
            }

            logger.info(
                f"🏭 {commodity} (MCX_FO only): {len(futures_keys)} futures, {len(options_keys)} options"
            )

    return mcx_data


def get_mcx_instrument_keys(self) -> List[str]:
    """Get MCX commodity keys - INSTANT ACCESS"""
    if not self._service_initialized:
        logger.warning("⚠️ Service not initialized")
        return []
    return self._mcx_keys.copy()


def get_stock_trading_keys(self, symbol: str) -> List[str]:
    """Get ALL trading keys for a selected stock - INSTANT ACCESS"""
    if not self._service_initialized:
        logger.warning("⚠️ Service not initialized")
        return []
    return self._trading_stock_keys.get(symbol.upper(), [])


def select_stock_for_trading(self, symbol: str) -> Dict[str, Any]:
    """Select a stock for active trading - returns ALL instrument keys instantly"""
    if not self._service_initialized:
        return {"error": "Service not initialized", "keys": []}

    symbol = symbol.upper()

    # Debug: Check what's in our stock mappings
    if symbol not in self._stock_mappings:
        logger.warning(f"🐛 DEBUG: Stock {symbol} not found in mappings")
        logger.warning(
            f"🐛 DEBUG: Available symbols: {list(self._stock_mappings.keys())[:10]}..."
        )

        # Try to find similar symbols
        similar_symbols = [s for s in self._stock_mappings.keys() if "NIFTY" in s]
        if similar_symbols:
            logger.warning(f"🐛 DEBUG: Similar NIFTY symbols found: {similar_symbols}")

        return {"error": f"Stock {symbol} not found", "keys": []}

    self._selected_trading_stocks.add(symbol)

    trading_keys = self._trading_stock_keys.get(symbol, [])
    stock_data = self._stock_mappings[symbol]

    option_chain = self._get_option_chain_with_range(symbol, OPTION_STRIKE_RANGE)

    return {
        "symbol": symbol,
        "status": "selected_for_trading",
        "total_keys": len(trading_keys),
        "instrument_keys": trading_keys,
        "spot_key": stock_data.get("primary_instrument_key"),
        "has_futures": stock_data.get("has_futures", False),
        "has_options": stock_data.get("has_options", False),
        "option_chain_strikes": len(option_chain.get("strikes", [])),
        "option_chain": option_chain,
        "selected_at": datetime.now().isoformat(),
    }


def get_selected_trading_stocks(self) -> List[str]:
    """Get list of currently selected trading stocks"""
    return list(self._selected_trading_stocks)


def _get_option_chain_with_range(self, symbol: str, strike_range: int) -> Dict:
    """Get option chain with specified strike range"""
    stock_data = self._stock_mappings.get(symbol.upper())
    if not stock_data:
        return {"strikes": [], "ce": [], "pe": []}

    instruments = stock_data.get("instruments", {})
    ce_options = instruments.get("CE", [])
    pe_options = instruments.get("PE", [])

    if not ce_options and not pe_options:
        return {"strikes": [], "ce": [], "pe": []}

    all_strikes = set()
    for opt in ce_options + pe_options:
        if hasattr(opt, "strike_price") and opt.strike_price:
            all_strikes.add(opt.strike_price)

    if not all_strikes:
        return {"strikes": [], "ce": [], "pe": []}

    sorted_strikes = sorted(all_strikes)
    atm_strike = sorted_strikes[len(sorted_strikes) // 2]

    min_strike = atm_strike - strike_range
    max_strike = atm_strike + strike_range

    valid_strikes = [s for s in sorted_strikes if min_strike <= s <= max_strike]

    option_chain = []
    for strike in valid_strikes:
        ce_options_at_strike = [
            opt
            for opt in ce_options
            if hasattr(opt, "strike_price") and opt.strike_price == strike
        ]
        pe_options_at_strike = [
            opt
            for opt in pe_options
            if hasattr(opt, "strike_price") and opt.strike_price == strike
        ]

        option_chain.append(
            {
                "strike": strike,
                "ce": (
                    ce_options_at_strike[0].__dict__ if ce_options_at_strike else None
                ),
                "pe": (
                    pe_options_at_strike[0].__dict__ if pe_options_at_strike else None
                ),
            }
        )

    return {
        "atm_strike": atm_strike,
        "strike_range": f"±{strike_range}",
        "strikes": valid_strikes,
        "chain": option_chain,
    }


def search_instruments(
    self,
    query: str,
    exchange: Optional[str] = None,
    instrument_type: Optional[str] = None,
) -> List[Dict]:
    """Search instruments - OPTIMIZED"""
    if not self._service_initialized:
        return []

    query = self.safe_upper(query)
    results = []

    matches = self._instruments_by_symbol.get(query, [])

    for symbol, instruments in self._instruments_by_symbol.items():
        if query in symbol:
            matches.extend(instruments)

    if exchange:
        exchange_upper = self.safe_upper(exchange)
        matches = [
            instr
            for instr in matches
            if self.safe_upper(instr.exchange) == exchange_upper
        ]

    if instrument_type:
        type_upper = self.safe_upper(instrument_type)
        matches = [
            instr
            for instr in matches
            if self.safe_upper(instr.instrument_type) == type_upper
        ]

    for instr in matches[:50]:
        results.append(instr.__dict__)

    return results


# Add to TradingInstrumentService class


async def get_fno_stocks(self) -> List[str]:
    """Get list of F&O stocks from NSE"""
    return await self._get_fno_stocks_list()


def get_fno_instruments(self, symbol: str) -> Dict[str, Any]:
    """Get F&O instruments for a specific stock"""
    return self._get_fno_instrument_keys(symbol)


async def build_complete_fno_registry(self) -> Dict[str, Any]:
    """Build complete F&O registry"""
    return await self._build_fno_registry()


# Add global functions


def get_spot_instruments_for_dashboard() -> List[Dict[str, Any]]:
    """Get spot instruments for dashboard"""
    service = get_trading_service()

    if not service:
        logger.error("❌ Trading service not available")
        return []

    if not service.is_initialized():
        logger.error("❌ Trading service not initialized - attempting initialization")
        try:
            # Try to initialize immediately if not initialized
            asyncio.create_task(service.initialize_service())
            logger.info("✅ Initialization task created for trading service")
        except Exception as e:
            logger.error(f"❌ Failed to initialize trading service: {e}")

    # Check again if it's initialized now
    if not service.is_initialized():
        logger.error("❌ Trading service still not initialized")

    # Get instruments with detailed logging
    logger.info("🔍 Getting spot-only instruments from trading service")
    instruments = service.get_spot_only_instruments()
    logger.info(
        f"📊 Retrieved {len(instruments)} spot instruments from trading service"
    )

    return instruments


async def get_available_fno_stocks() -> List[str]:
    """Get list of available F&O stocks"""
    service = get_trading_service()
    return await service.get_fno_stocks()


def get_stock_fno_instruments(symbol: str) -> Dict[str, Any]:
    """Get F&O instruments for a specific stock"""
    service = get_trading_service()
    return service.get_fno_instruments(symbol)


# ========== CONVENIENCE FUNCTIONS ==========


def get_all_dashboard_instruments(self) -> List[str]:
    """Backward compatibility"""
    return self.get_dashboard_instrument_keys()


def get_all_websocket_keys(self) -> List[str]:
    """Backward compatibility"""
    return self.get_websocket_instrument_keys()


# ========== SINGLETON INSTANCE AND GLOBAL FUNCTIONS ==========

_service_instance = None


def get_focused_instrument_keys() -> Dict[str, Any]:
    """Get all focused instrument keys for WebSocket - GLOBAL FUNCTION"""
    service = get_trading_service()
    return service.get_focused_websocket_keys()


def get_fno_equity_spots() -> List[str]:
    """Get F&O equity spot keys - GLOBAL FUNCTION"""
    service = get_trading_service()
    return service.get_fno_equity_spot_keys()


def get_selected_indices(indices: List[str] = None) -> List[str]:
    """Get selected index keys - GLOBAL FUNCTION"""
    service = get_trading_service()
    return service.get_selected_index_keys(indices)


def get_mcx_futures_only(
    commodities: List[str] = None, max_per_commodity: int = 3
) -> List[str]:
    """Get MCX futures keys only - GLOBAL FUNCTION"""
    service = get_trading_service()
    return service.get_mcx_futures_keys_only(commodities, max_per_commodity)


def get_trading_service() -> TradingInstrumentService:
    """Get singleton service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = TradingInstrumentService()
    return _service_instance


# ========== PUBLIC API FUNCTIONS ==========
async def initialize_trading_system() -> InitializationResult:
    """Initialize the complete trading system"""
    service = get_trading_service()
    return await service.initialize_service()


def get_dashboard_keys() -> List[str]:
    """Get all dashboard instrument keys (EQ + INDEX) - INSTANT"""
    service = get_trading_service()
    return service.get_dashboard_instrument_keys()


def get_websocket_keys() -> List[str]:
    """Get WebSocket instrument keys - INSTANT"""
    service = get_trading_service()
    return service.get_websocket_instrument_keys()


def get_mcx_keys() -> List[str]:
    """Get MCX commodity keys - INSTANT"""
    service = get_trading_service()
    return service.get_mcx_instrument_keys()


def get_spot_keys() -> List[str]:
    """Get ONLY spot instrument keys (EQ + INDEX) for real-time prices"""
    service = get_trading_service()
    return service.get_spot_instrument_keys()


def get_index_keys() -> List[str]:
    """Get ONLY index instrument keys (NIFTY, BANKNIFTY, SENSEX, etc.)"""
    service = get_trading_service()
    return service.get_index_instrument_keys()


def get_mcx_futures_and_options(commodities: List[str] = None) -> Dict[str, List[str]]:
    """Get MCX futures and options for CRUDEOIL, GOLD, SILVER"""
    service = get_trading_service()
    return service.get_mcx_futures_and_options_keys(commodities)


def get_optimized_realtime_subscription() -> Dict[str, List[str]]:
    """Get optimized keys for real-time data subscription with proper balance"""
    service = get_trading_service()

    if not service._service_initialized:
        logger.warning("⚠️ Service not initialized")
        return {}

    # Priority 1: Spot prices (EQ + INDEX) - Most important
    spot_keys = service.get_spot_instrument_keys()
    index_keys = service.get_index_instrument_keys()

    # Filter out unwanted BSE keys from spot_keys
    filtered_spot_keys = [
        key
        for key in spot_keys
        if key.startswith("NSE_") or (key.startswith("BSE_") and "SENSEX" in key)
    ]

    # For index_keys, keep only NSE indices and SENSEX from BSE
    filtered_index_keys = [
        key
        for key in index_keys
        if key.startswith("NSE_") or (key.startswith("BSE_") and "SENSEX" in key)
    ]

    # Priority 2: MCX commodities futures and options
    mcx_futures = []
    mcx_options = []

    for key in service._mcx_keys:
        if key and key in service._instrument_by_key:
            instr = service._instrument_by_key[key]
            trading_symbol = getattr(instr, "trading_symbol", "")
            instr_type = getattr(instr, "instrument_type", "").upper()

            # Proper option detection using instrument_type and trading_symbol
            if (
                instr_type in ["CE", "PE"]
                or " CE " in trading_symbol
                or " PE " in trading_symbol
            ):
                mcx_options.append(key)
            elif instr_type in ["FUT", "FUTCOM"] or (
                "FUT" in trading_symbol
                and "CE" not in trading_symbol
                and "PE" not in trading_symbol
            ):
                mcx_futures.append(key)

    # Limit MCX to reasonable numbers
    mcx_futures = mcx_futures[:3]  # Near month futures only
    mcx_options = mcx_options[:40]  # Up to 40 MCX options

    # Combine all keys - ONLY WHAT'S NEEDED FOR LIVE FEED
    all_keys = []
    all_keys.extend(filtered_spot_keys)  # All spot stocks
    all_keys.extend(filtered_index_keys)  # All indices
    all_keys.extend(mcx_futures)  # MCX futures (limited)
    all_keys.extend(mcx_options)  # MCX options (limited)

    # Remove duplicates
    unique_keys = list(set([k for k in all_keys if k]))

    # Log breakdown
    nse_eq_count = len([k for k in unique_keys if k.startswith("NSE_EQ|")])
    nse_index_count = len([k for k in unique_keys if k.startswith("NSE_INDEX|")])
    bse_sensex_count = len([k for k in unique_keys if k.startswith("BSE_INDEX|")])
    mcx_fut_count = len(
        [
            k
            for k in unique_keys
            if k.startswith("MCX_") and any(x in k for x in ["FUT", "FUTCOM"])
        ]
    )
    mcx_opt_count = len(
        [
            k
            for k in unique_keys
            if k.startswith("MCX_") and any(x in k for x in ["CE", "PE", "OPT"])
        ]
    )

    logger.info(
        f"🔗 Built {len(unique_keys)} optimized WebSocket keys: "
        f"NSE EQ={nse_eq_count}, NSE INDEX={nse_index_count}, "
        f"BSE SENSEX={bse_sensex_count}, MCX FUT={mcx_fut_count}, MCX OPT={mcx_opt_count}"
    )

    return {
        "total_keys": len(unique_keys),
        "all_keys": unique_keys,
        "breakdown": {
            "nse_eq": nse_eq_count,
            "nse_index": nse_index_count,
            "bse_sensex": bse_sensex_count,
            "mcx_futures": mcx_fut_count,
            "mcx_options": mcx_opt_count,
            "total": len(unique_keys),
        },
        "optimization_strategy": {
            "spot_priority": "All NSE stocks from top_stocks.json",
            "index_coverage": "All NSE indices + SENSEX only",
            "mcx_focus": "Near-month futures and ATM options",
            "derivatives": "MCX options included, index/equity derivatives excluded from live feed",
        },
    }


# ========== NEW ADVANCED KEY MANAGEMENT FUNCTIONS ==========


def get_futures_for_symbol(self, symbol: str) -> List[Dict]:
    """Get futures contracts for a specific symbol"""
    if not self._service_initialized:
        logger.warning("⚠️ Service not initialized")
        return []

    symbol = symbol.upper()
    if symbol not in self._stock_mappings:
        logger.warning(f"⚠️ Symbol {symbol} not found in mappings")
        return []

    futures = []
    for instr in self._stock_mappings[symbol].get("instruments", {}).get("FUT", []):
        futures.append(instr.__dict__)

    # Sort by expiry
    futures.sort(key=lambda x: x.get("expiry", ""))

    logger.info(f"📅 Found {len(futures)} futures for {symbol}")
    return futures


def get_options_for_symbol(
    self, symbol: str, option_type: str = None, strike_range: int = 40
) -> List[Dict]:
    """Get options for a specific symbol with strike range filtering"""
    if not self._service_initialized:
        logger.warning("⚠️ Service not initialized")
        return []

    symbol = symbol.upper()
    if symbol not in self._stock_mappings:
        logger.warning(f"⚠️ Symbol {symbol} not found in mappings")
        return []

    instruments = self._stock_mappings[symbol].get("instruments", {})
    options = []

    # Determine which option types to include
    option_types = []
    if option_type:
        if option_type.upper() in ["CE", "CALL"]:
            option_types = ["CE"]
        elif option_type.upper() in ["PE", "PUT"]:
            option_types = ["PE"]
    else:
        option_types = ["CE", "PE"]

    # Get all strikes
    all_strikes = set()
    for opt_type in option_types:
        for instr in instruments.get(opt_type, []):
            if hasattr(instr, "strike_price") and instr.strike_price:
                all_strikes.add(instr.strike_price)

    if not all_strikes:
        logger.warning(f"⚠️ No strike prices found for {symbol}")
        return []

    # Find ATM strike (middle of range)
    sorted_strikes = sorted(all_strikes)
    mid_idx = len(sorted_strikes) // 2
    atm_strike = sorted_strikes[mid_idx]

    # Calculate strike range
    min_strike = atm_strike - strike_range
    max_strike = atm_strike + strike_range

    # Filter options by strike range
    for opt_type in option_types:
        for instr in instruments.get(opt_type, []):
            if (
                hasattr(instr, "strike_price")
                and instr.strike_price
                and min_strike <= instr.strike_price <= max_strike
            ):
                options.append(instr.__dict__)

    # Sort by expiry and strike
    options.sort(key=lambda x: (x.get("expiry", ""), x.get("strike_price", 0)))

    logger.info(
        f"🎯 Found {len(options)} {'/'.join(option_types)} options for {symbol} within ±{strike_range} of ATM"
    )
    return options


def get_derivatives_for_symbol(
    self,
    symbol: str,
    include_futures: bool = True,
    include_options: bool = True,
    strike_range: int = 40,
) -> Dict:
    """Get all derivatives for a specific symbol"""
    result = {
        "symbol": symbol.upper(),
        "futures": [],
        "call_options": [],
        "put_options": [],
        "atm_strike": None,
    }

    if not self._service_initialized:
        return result

    # Get futures if requested
    if include_futures:
        result["futures"] = self.get_futures_for_symbol(symbol)

    # Get options if requested
    if include_options:
        # Get call options
        result["call_options"] = self.get_options_for_symbol(symbol, "CE", strike_range)

        # Get put options
        result["put_options"] = self.get_options_for_symbol(symbol, "PE", strike_range)

        # Calculate ATM strike
        if result["call_options"] or result["put_options"]:
            all_strikes = set()
            for opt in result["call_options"] + result["put_options"]:
                if "strike_price" in opt:
                    all_strikes.add(opt["strike_price"])

            if all_strikes:
                sorted_strikes = sorted(all_strikes)
                mid_idx = len(sorted_strikes) // 2
                result["atm_strike"] = sorted_strikes[mid_idx]

    # Add summary information
    result["futures_count"] = len(result["futures"])
    result["call_options_count"] = len(result["call_options"])
    result["put_options_count"] = len(result["put_options"])
    result["total_derivatives"] = (
        result["futures_count"]
        + result["call_options_count"]
        + result["put_options_count"]
    )

    return result


def get_dashboard_market_data_keys() -> Dict[str, Any]:
    """Get dashboard real-time market data keys"""
    service = get_trading_service()
    return service.get_dashboard_realtime_keys()


def get_stock_trading_data_keys(symbol: str) -> Dict[str, Any]:
    """Get active trading keys for specific stock"""
    service = get_trading_service()
    return service.get_active_trading_keys(symbol)


def get_market_snapshot_keys() -> List[str]:
    """Get minimal keys for quick market snapshot"""
    service = get_trading_service()
    return service.get_quick_market_snapshot_keys()


def select_stock_for_trading(symbol: str) -> Dict[str, Any]:
    """Select stock for active trading - returns ALL keys INSTANTLY"""
    service = get_trading_service()
    return service.select_stock_for_trading(symbol)


def deselect_stock_for_trading(symbol: str) -> Dict[str, Any]:
    """Remove stock from active trading"""
    service = get_trading_service()
    return service.deselect_stock_for_trading(symbol)


def get_stock_instruments(symbol: str) -> Optional[Dict]:
    """Get complete stock instrument data - INSTANT"""
    service = get_trading_service()
    return service.get_stock_instruments(symbol)


def get_instrument_by_key(instrument_key: str) -> Optional[Dict]:
    """Get instrument by key - O(1) INSTANT"""
    service = get_trading_service()
    return service.get_instrument_by_key(instrument_key)


async def health_check() -> Dict[str, Any]:
    """Service health check"""
    service = get_trading_service()
    return await service.health_check()


def is_service_ready() -> bool:
    """Check if service is ready"""
    service = get_trading_service()
    return service.is_initialized()


async def refresh_daily_instruments(self) -> InitializationResult:
    """Daily refresh of instrument data to get latest keys"""
    logger.info("🔄 Starting daily instrument refresh...")

    # Force download of fresh data regardless of file age
    total_downloaded, filtered_count = await self.download_and_filter_instruments(
        force_refresh=True
    )

    # Reload and rebuild all indexes and mappings
    instruments = await self._load_filtered_instruments()
    await self._build_high_performance_indexes(instruments)

    top_stocks = await self._load_top_stocks()
    stock_mappings = await self._build_stock_mappings(top_stocks)

    dashboard_keys = self._build_dashboard_keys()
    mcx_keys = self._build_mcx_keys()

    # Update MCX keys and rebuild WebSocket keys
    self._mcx_keys = mcx_keys
    websocket_keys = self._build_websocket_keys()

    # Cache the updated data
    cache_keys_created = await self._cache_all_data(
        stock_mappings, dashboard_keys, websocket_keys, mcx_keys
    )

    # Update instance variables
    self._stock_mappings = stock_mappings
    self._dashboard_keys = dashboard_keys
    self._websocket_keys = websocket_keys
    self._mcx_keys = mcx_keys
    self._last_refresh = datetime.now()

    logger.info(
        f"✅ Daily instrument refresh complete: {len(websocket_keys)} WebSocket keys"
    )

    return InitializationResult(
        status="success",
        processing_time=0,  # Calculate actual time
        total_stocks=len(top_stocks),
        filtered_instruments=filtered_count,
        mapped_stocks=len(stock_mappings),
        websocket_instruments=len(websocket_keys),
        dashboard_instruments=len(dashboard_keys),
        trading_instruments=len(self._trading_stock_keys),
        mcx_instruments=len(mcx_keys),
        cache_keys_created=cache_keys_created,
        memory_saved_mb=(total_downloaded - filtered_count) * 0.001,
        initialized_at=datetime.now().isoformat(),
    )


# Add these module-level functions at the end of instrument_refresh_service.py

# ========== MODULE LEVEL FUNCTIONS FOR COMPATIBILITY ==========


def get_spot_only_instruments() -> List[Dict[str, Any]]:
    """Get ONLY spot equity instrument keys with essential metadata for dashboard"""
    service = get_trading_service()

    if not service.is_initialized():
        logger.warning("⚠️ Service not initialized")
        return []

    spot_instruments = []

    # Loop through stock mappings to get spot instruments
    for symbol, mapping in service._stock_mappings.items():
        instruments = mapping.get("instruments", {})

        # Get EQ instruments only
        for instr in instruments.get("EQ", []):
            if instr.instrument_key and "NSE_EQ|" in instr.instrument_key:
                # Include essential metadata for display
                spot_instruments.append(
                    {
                        "symbol": symbol,
                        "instrument_key": instr.instrument_key,
                        "trading_symbol": getattr(instr, "trading_symbol", symbol),
                        "name": getattr(instr, "name", symbol),
                        "isin": getattr(instr, "isin", ""),
                        "exchange": getattr(instr, "exchange", "NSE"),
                    }
                )
                break  # Take only first EQ instrument per stock

    # Add indices
    for index_symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]:
        if index_symbol in service._stock_mappings:
            instruments = service._stock_mappings[index_symbol].get("instruments", {})

            for instr in instruments.get("INDEX", []):
                if instr.instrument_key:
                    spot_instruments.append(
                        {
                            "symbol": index_symbol,
                            "instrument_key": instr.instrument_key,
                            "trading_symbol": getattr(
                                instr, "trading_symbol", index_symbol
                            ),
                            "name": getattr(instr, "name", index_symbol),
                            "is_index": True,
                            "exchange": getattr(instr, "exchange", "NSE"),
                        }
                    )
                    break  # Take only first INDEX instrument per index

    logger.info(f"📊 Built {len(spot_instruments)} spot-only instruments for dashboard")
    return spot_instruments


async def get_fno_stocks_list() -> List[str]:
    """Get list of stocks available for F&O trading from NSE's website"""
    # Use web_fetch to get the NSE F&O list
    try:
        url = "https://www.nseindia.com/products-services/equity-derivatives-list-underlyings-information"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers={"User-Agent": "Mozilla/5.0"}
            ) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch NSE F&O list: {response.status}")
                    return []

                html = await response.text()

                # Simple parsing to extract symbols - you might need a proper HTML parser
                # This is just a basic approach
                symbols = []
                import re

                # Extract symbols from HTML table (this is simplified and may need adjustment)
                matches = re.findall(r"<td>([\w&\-]+)</td>", html)
                symbols = [m.upper() for m in matches if m and len(m) > 1]

                # Filter out duplicates
                unique_symbols = list(set(symbols))

                logger.info(f"📊 Fetched {len(unique_symbols)} F&O symbols from NSE")
                return unique_symbols
    except Exception as e:
        logger.error(f"Error fetching NSE F&O list: {e}")

        # Fallback to a static list (update periodically)
        fallback_fno = [
            "RELIANCE",
            "TCS",
            "HDFCBANK",
            "INFY",
            "ICICIBANK",
            "HDFC",
            "ITC",
            "SBIN",
            "BHARTIARTL",
            "KOTAKBANK",
            "HINDUNILVR",
            "BAJFINANCE",
            "AXISBANK",
            "ASIANPAINT",
            "MARUTI",
            "TATAMOTORS",
            "M&M",
            "SUNPHARMA",
            "WIPRO",
            "HCLTECH",
            "ULTRACEMCO",
            "ADANIPORTS",
            "TATASTEEL",
            "JSWSTEEL",
            "ADANIENT",
            "BAJAJ-AUTO",
            "TITAN",
            "NTPC",
            "POWERGRID",
            "BPCL",
            "ONGC",
            "GRASIM",
            "DRREDDY",
            "CIPLA",
            "DIVISLAB",
            "TATACONSUM",
            "INDUSINDBK",
            "HINDALCO",
            "TECHM",
            "APOLLOHOSP",
            "HEROMOTOCO",
            "EICHERMOT",
            "UPL",
            "NESTLEIND",
            "BRITANNIA",
            "SHREECEM",
            "ADANIGREEN",
            "COALINDIA",
            "BAJAJFINSV",
            "VEDL",
            "LT",
        ]
        logger.warning(f"⚠️ Using fallback F&O list with {len(fallback_fno)} symbols")
        return fallback_fno


def get_fno_instrument_keys(symbol: str) -> Dict[str, Any]:
    """Get F&O instrument keys for a specific stock with full metadata"""
    service = get_trading_service()

    if not service.is_initialized():
        return {
            "error": "Service not initialized",
            "symbol": symbol,
            "instruments": [],
        }

    # Normalize symbol
    symbol = symbol.upper()

    # Check if symbol exists in stock mappings
    if symbol not in service._stock_mappings:
        return {
            "error": f"Symbol {symbol} not found",
            "symbol": symbol,
            "instruments": [],
        }

    stock_data = service._stock_mappings[symbol]
    instruments = stock_data.get("instruments", {})

    result = {
        "symbol": symbol,
        "name": stock_data.get("name", symbol),
        "exchange": stock_data.get("exchange", "NSE"),
        "spot": [],
        "futures": [],
        "call_options": [],
        "put_options": [],
        "instrument_count": 0,
    }

    # Get spot (EQ) instruments
    for instr in instruments.get("EQ", []):
        if instr.instrument_key and "NSE_EQ|" in instr.instrument_key:
            result["spot"].append(
                {
                    "instrument_key": instr.instrument_key,
                    "trading_symbol": getattr(instr, "trading_symbol", ""),
                    "lot_size": getattr(instr, "lot_size", 1),
                    "tick_size": getattr(instr, "tick_size", 0.05),
                    "isin": getattr(instr, "isin", ""),
                }
            )

    # Get futures
    for instr in instruments.get("FUT", []):
        if instr.instrument_key and "NSE_FO|" in instr.instrument_key:
            result["futures"].append(
                {
                    "instrument_key": instr.instrument_key,
                    "trading_symbol": getattr(instr, "trading_symbol", ""),
                    "expiry": getattr(instr, "expiry", ""),
                    "lot_size": getattr(instr, "lot_size", 1),
                    "tick_size": getattr(instr, "tick_size", 0.05),
                }
            )

    # Get call options (CE)
    for instr in instruments.get("CE", []):
        if instr.instrument_key and "NSE_FO|" in instr.instrument_key:
            result["call_options"].append(
                {
                    "instrument_key": instr.instrument_key,
                    "trading_symbol": getattr(instr, "trading_symbol", ""),
                    "expiry": getattr(instr, "expiry", ""),
                    "strike_price": getattr(instr, "strike_price", 0),
                    "lot_size": getattr(instr, "lot_size", 1),
                    "tick_size": getattr(instr, "tick_size", 0.05),
                }
            )

    # Get put options (PE)
    for instr in instruments.get("PE", []):
        if instr.instrument_key and "NSE_FO|" in instr.instrument_key:
            result["put_options"].append(
                {
                    "instrument_key": instr.instrument_key,
                    "trading_symbol": getattr(instr, "trading_symbol", ""),
                    "expiry": getattr(instr, "expiry", ""),
                    "strike_price": getattr(instr, "strike_price", 0),
                    "lot_size": getattr(instr, "lot_size", 1),
                    "tick_size": getattr(instr, "tick_size", 0.05),
                }
            )

    # Sort by expiry and strike price
    result["futures"].sort(key=lambda x: x.get("expiry", "") or "")
    result["call_options"].sort(
        key=lambda x: (x.get("expiry", "") or "", x.get("strike_price", 0) or 0)
    )
    result["put_options"].sort(
        key=lambda x: (x.get("expiry", "") or "", x.get("strike_price", 0) or 0)
    )

    # Count total instruments
    result["instrument_count"] = (
        len(result["spot"])
        + len(result["futures"])
        + len(result["call_options"])
        + len(result["put_options"])
    )

    return result


async def build_fno_registry() -> Dict[str, Any]:
    """Build complete F&O registry with instrument keys for all F&O stocks"""
    service = get_trading_service()

    if not service.is_initialized():
        logger.warning("⚠️ Service not initialized")
        return {"error": "Service not initialized", "stocks": []}

    # Get F&O stock list from NSE
    fno_symbols = await get_fno_stocks_list()

    # Build registry
    registry = {
        "created_at": datetime.now().isoformat(),
        "total_stocks": len(fno_symbols),
        "stocks": {},
    }

    # Process each F&O stock
    for symbol in fno_symbols:
        stock_data = get_fno_instrument_keys(symbol)
        if "error" not in stock_data:
            registry["stocks"][symbol] = stock_data

    logger.info(f"📊 Built F&O registry with {len(registry['stocks'])} stocks")

    # Store in Redis for future use
    if service.redis_client:
        await service.redis_client.setex(
            "fno_registry", CACHE_TTL, json.dumps(registry)
        )
        logger.info("💾 Stored F&O registry in Redis")

    return registry


def get_dashboard_data() -> Dict[str, Any]:
    """Get structured data for dashboard"""
    service = get_trading_service()

    # Get spot instruments
    spot_instruments = get_spot_only_instruments()

    # Get index data
    indices = [instr for instr in spot_instruments if instr.get("is_index", False)]

    # Get top stocks
    top_stocks = [
        instr for instr in spot_instruments if not instr.get("is_index", False)
    ][:200]

    # Structure the data
    dashboard_data = {
        "indices": indices,
        "top_stocks": top_stocks,
        "all_stocks": spot_instruments,
        "instrument_keys": [instr["instrument_key"] for instr in spot_instruments],
        "updated_at": datetime.now().isoformat(),
    }

    return dashboard_data


def _get_atm_options(
    options: List[Dict[str, Any]], range_count: int
) -> List[Dict[str, Any]]:
    """Get ATM options within a range"""
    if not options:
        return []

    # Group by expiry
    by_expiry = {}
    for opt in options:
        expiry = opt.get("expiry", "")
        if expiry not in by_expiry:
            by_expiry[expiry] = []
        by_expiry[expiry].append(opt)

    # Sort by strike and get ATM range for each expiry
    atm_options = []
    for expiry, opts in by_expiry.items():
        sorted_opts = sorted(opts, key=lambda x: x.get("strike_price", 0) or 0)
        if sorted_opts:
            mid_idx = len(sorted_opts) // 2
            start = max(0, mid_idx - range_count)
            end = min(len(sorted_opts), mid_idx + range_count + 1)
            atm_options.extend(sorted_opts[start:end])

    return atm_options


def get_trading_analysis_data(symbol: str) -> Dict[str, Any]:
    """Get structured data for trading analysis"""
    # Get F&O data for the stock
    fno_data = get_fno_instrument_keys(symbol)

    # Structure for trading analysis
    trading_data = {
        "symbol": symbol,
        "name": fno_data.get("name", symbol),
        "spot": fno_data.get("spot", []),
        "spot_key": (
            fno_data.get("spot", [{}])[0].get("instrument_key")
            if fno_data.get("spot")
            else None
        ),
        "current_month_futures": fno_data.get("futures", [])[:1],  # Current month only
        "all_futures": fno_data.get("futures", []),
        "atm_call_options": _get_atm_options(
            fno_data.get("call_options", []), 5
        ),  # ±5 strikes from ATM
        "atm_put_options": _get_atm_options(
            fno_data.get("put_options", []), 5
        ),  # ±5 strikes from ATM
        "all_call_options": fno_data.get("call_options", []),
        "all_put_options": fno_data.get("put_options", []),
        "instrument_keys": {
            "spot": [instr["instrument_key"] for instr in fno_data.get("spot", [])],
            "futures": [
                instr["instrument_key"] for instr in fno_data.get("futures", [])
            ],
            "calls": [
                instr["instrument_key"] for instr in fno_data.get("call_options", [])
            ],
            "puts": [
                instr["instrument_key"] for instr in fno_data.get("put_options", [])
            ],
        },
        "updated_at": datetime.now().isoformat(),
    }

    return trading_data


# Add to the end of instrument_refresh_service.py


def get_symbol_derivatives(
    symbol: str,
    include_futures: bool = True,
    include_options: bool = True,
    strike_range: int = 40,
) -> Dict:
    """Get derivatives for a specific symbol - GLOBAL FUNCTION"""
    service = get_trading_service()
    return service.get_derivatives_for_symbol(
        symbol, include_futures, include_options, strike_range
    )
