# # services/optimized_instrument_service.py
# """
# Optimized Instrument Service - Production Ready with Bug Fixes

# Production-ready service that works efficiently with or without Redis.
# Fixed the is_initialized() method call issue and optimized for fast local development.
# """

# import asyncio
# import json
# import logging
# import time
# from datetime import datetime
# from typing import Dict, List, Set, Optional, Tuple, Any
# from pathlib import Path
# from collections import defaultdict
# import aiofiles
# from functools import wraps
# from dataclasses import dataclass, asdict

# # Try to import Redis, fall back to None if not available
# try:
#     import redis.asyncio as redis

#     REDIS_AVAILABLE = True
# except ImportError:
#     redis = None
#     REDIS_AVAILABLE = False

# logger = logging.getLogger(__name__)


# def async_performance_timer(func):
#     """Decorator to measure async function performance"""

#     @wraps(func)
#     async def wrapper(*args, **kwargs):
#         start_time = time.time()
#         result = await func(*args, **kwargs)
#         end_time = time.time()
#         duration = end_time - start_time
#         logger.info(f"⚡ {func.__name__} executed in {duration:.3f}s")
#         return result

#     return wrapper


# def performance_timer(func):
#     """Decorator to measure sync function performance"""

#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         start_time = time.time()
#         result = func(*args, **kwargs)
#         end_time = time.time()
#         duration = end_time - start_time
#         logger.info(f"⚡ {func.__name__} executed in {duration:.3f}s")
#         return result

#     return wrapper


# @dataclass
# class ServiceStats:
#     """Service statistics data structure"""

#     initialized: bool
#     total_stocks_mapped: int
#     total_instrument_keys: int
#     valid_instruments: int
#     websocket_keys: int
#     cache_available: bool
#     redis_connected: bool
#     last_update: str
#     processing_time: Optional[float] = None


# @dataclass
# class InitializationResult:
#     """Initialization result data structure"""

#     status: str
#     processing_time: float
#     total_stocks: int
#     total_instruments: int
#     mapped_stocks: int
#     websocket_instruments: int
#     cache_keys_created: int
#     initialized_at: str
#     error: Optional[str] = None


# class InMemoryCache:
#     """Fast in-memory cache as Redis alternative"""

#     def __init__(self):
#         self._data = {}
#         self._expiry = {}

#     async def ping(self):
#         return True

#     async def setex(self, key: str, ttl: int, value: str):
#         self._data[key] = value
#         self._expiry[key] = time.time() + ttl

#     async def get(self, key: str) -> Optional[str]:
#         if key in self._data:
#             if key in self._expiry and time.time() > self._expiry[key]:
#                 del self._data[key]
#                 del self._expiry[key]
#                 return None
#             return self._data[key]
#         return None

#     async def keys(self, pattern: str) -> List[str]:
#         import fnmatch

#         # Clean expired keys
#         current_time = time.time()
#         expired_keys = [
#             k for k, exp_time in self._expiry.items() if current_time > exp_time
#         ]
#         for k in expired_keys:
#             self._data.pop(k, None)
#             self._expiry.pop(k, None)

#         return [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]

#     async def delete(self, *keys):
#         for key in keys:
#             self._data.pop(key, None)
#             self._expiry.pop(key, None)

#     def pipeline(self):
#         return InMemoryPipeline(self)


# class InMemoryPipeline:
#     """Pipeline for batch operations"""

#     def __init__(self, cache):
#         self.cache = cache
#         self.commands = []

#     def setex(self, key: str, ttl: int, value: str):
#         self.commands.append(("setex", key, ttl, value))

#     async def execute(self):
#         for cmd in self.commands:
#             if cmd[0] == "setex":
#                 await self.cache.setex(cmd[1], cmd[2], cmd[3])
#         self.commands.clear()

#     async def __aenter__(self):
#         return self

#     async def __aexit__(self, exc_type, exc_val, exc_tb):
#         pass


# class OptimizedInstrumentService:
#     """
#     High-performance instrument service that works with or without Redis
#     """

#     _instance = None
#     _lock = asyncio.Lock()

#     def __new__(cls, *args, **kwargs):
#         if cls._instance is None:
#             cls._instance = super().__new__(cls)
#             cls._instance._service_initialized = False
#         return cls._instance

#     def __init__(
#         self, redis_url: str = "redis://localhost:6379/1", use_redis: bool = True
#     ):
#         if hasattr(self, "_service_initialized") and self._service_initialized:
#             return

#         self.redis_client = None
#         self.redis_url = redis_url
#         self.use_redis = use_redis and REDIS_AVAILABLE
#         self.cache_ttl = 86400  # 24 hours
#         self.batch_size = 1000

#         # In-memory caches for ultra-fast access
#         self._stock_mappings = {}
#         self._instrument_key_map = {}
#         self._valid_instruments = set()
#         self._websocket_keys = []
#         self._initialized = False
#         self._initialization_time = None

#         # Data paths
#         self.data_dir = Path("data")
#         self.top_stocks_file = self.data_dir / "top_stocks.json"
#         self.instruments_file = self.data_dir / "upstox_instruments.json"

#         self._service_initialized = True
#         logger.info("🔧 OptimizedInstrumentService instance created")

#     async def _ensure_cache_connection(self):
#         """Ensure cache connection is established"""
#         if self.redis_client is None:
#             if self.use_redis:
#                 try:
#                     self.redis_client = redis.from_url(
#                         self.redis_url,
#                         decode_responses=True,
#                         socket_connect_timeout=2,
#                         socket_timeout=2,
#                     )
#                     await self.redis_client.ping()
#                     logger.info("✅ Redis connection established")
#                     return
#                 except Exception as e:
#                     logger.warning(f"⚠️ Redis unavailable, using in-memory cache: {e}")

#             # Fall back to in-memory cache
#             self.redis_client = InMemoryCache()
#             logger.info("✅ Using in-memory cache")

#     @async_performance_timer
#     async def initialize_instruments_system(self) -> InitializationResult:
#         """
#         Complete instrument system initialization.
#         """
#         start_time = time.time()
#         logger.info("🔧 Initializing instruments system...")

#         try:
#             # Ensure cache connection
#             await self._ensure_cache_connection()

#             # Step 1: Load and validate data files
#             top_stocks, instruments = await self._load_data_files_async()

#             if not top_stocks or not instruments:
#                 # Use fallback data for testing
#                 top_stocks = self._get_fallback_stocks()
#                 instruments = self._get_fallback_instruments()

#             # Step 2: Build optimized indexes (with progress logging)
#             indexes = await self._build_optimized_indexes(instruments)

#             # Step 3: Generate instrument mappings for top stocks
#             stock_mappings = await self._generate_stock_mappings(top_stocks, indexes)

#             # Step 4: Cache everything for production use
#             cache_keys_created = await self._cache_all_mappings(stock_mappings, indexes)

#             # Step 5: Prepare WebSocket subscription lists
#             ws_instruments = await self._prepare_websocket_instruments(stock_mappings)

#             # Step 6: Store in memory for fast access
#             self._stock_mappings = stock_mappings
#             self._instrument_key_map = indexes["instrument_key_map"]
#             self._valid_instruments = indexes["valid_instruments"]
#             self._websocket_keys = ws_instruments
#             self._initialized = True
#             self._initialization_time = datetime.now()

#             end_time = time.time()
#             processing_time = end_time - start_time

#             result = InitializationResult(
#                 status="success",
#                 processing_time=processing_time,
#                 total_stocks=len(top_stocks),
#                 total_instruments=len(instruments),
#                 mapped_stocks=len(stock_mappings),
#                 websocket_instruments=len(ws_instruments),
#                 cache_keys_created=cache_keys_created,
#                 initialized_at=datetime.now().isoformat(),
#             )

#             logger.info(f"✅ Instruments system initialized in {processing_time:.2f}s")
#             logger.info(
#                 f"📊 Mapped {len(stock_mappings)} stocks, {len(ws_instruments)} WebSocket instruments"
#             )
#             return result

#         except Exception as e:
#             error_msg = f"Instruments initialization failed: {e}"
#             logger.error(f"❌ {error_msg}")
#             return InitializationResult(
#                 status="error",
#                 processing_time=time.time() - start_time,
#                 total_stocks=0,
#                 total_instruments=0,
#                 mapped_stocks=0,
#                 websocket_instruments=0,
#                 cache_keys_created=0,
#                 initialized_at=datetime.now().isoformat(),
#                 error=error_msg,
#             )

#     def _get_fallback_stocks(self) -> List[Dict]:
#         """Get fallback stock data for testing"""
#         return [
#             {
#                 "symbol": "RELIANCE",
#                 "name": "Reliance Industries Limited",
#                 "exchange": "NSE",
#             },
#             {
#                 "symbol": "TCS",
#                 "name": "Tata Consultancy Services Limited",
#                 "exchange": "NSE",
#             },
#             {"symbol": "HDFC", "name": "HDFC Bank Limited", "exchange": "NSE"},
#             {"symbol": "INFY", "name": "Infosys Limited", "exchange": "NSE"},
#             {"symbol": "ICICIBANK", "name": "ICICI Bank Limited", "exchange": "NSE"},
#             {
#                 "symbol": "KOTAKBANK",
#                 "name": "Kotak Mahindra Bank Limited",
#                 "exchange": "NSE",
#             },
#             {"symbol": "HDFCBANK", "name": "HDFC Bank Limited", "exchange": "NSE"},
#             {
#                 "symbol": "BAJFINANCE",
#                 "name": "Bajaj Finance Limited",
#                 "exchange": "NSE",
#             },
#             {"symbol": "LT", "name": "Larsen & Toubro Limited", "exchange": "NSE"},
#             {"symbol": "WIPRO", "name": "Wipro Limited", "exchange": "NSE"},
#         ]

#     def _get_fallback_instruments(self) -> List[Dict]:
#         """Get fallback instrument data for testing"""
#         return [
#             {
#                 "instrument_key": "NSE_EQ|INE002A01018",
#                 "exchange_token": "2885",
#                 "tradingsymbol": "RELIANCE",
#                 "name": "RELIANCE INDUSTRIES LTD",
#                 "last_price": 2500.0,
#                 "expiry": "",
#                 "strike_price": 0.0,
#                 "tick_size": 0.05,
#                 "lot_size": 1,
#                 "instrument_type": "EQ",
#                 "segment": "NSE_EQ",
#                 "exchange": "NSE",
#                 "isin": "INE002A01018",
#                 "multiplier": 1,
#                 "freeze_quantity": 50000,
#                 "underlying_symbol": "RELIANCE",
#                 "underlying_token": "2885",
#             },
#             {
#                 "instrument_key": "NSE_EQ|INE467B01029",
#                 "exchange_token": "11536",
#                 "tradingsymbol": "TCS",
#                 "name": "TATA CONSULTANCY SERVICES LTD",
#                 "last_price": 3500.0,
#                 "expiry": "",
#                 "strike_price": 0.0,
#                 "tick_size": 0.05,
#                 "lot_size": 1,
#                 "instrument_type": "EQ",
#                 "segment": "NSE_EQ",
#                 "exchange": "NSE",
#                 "isin": "INE467B01029",
#                 "multiplier": 1,
#                 "freeze_quantity": 50000,
#                 "underlying_symbol": "TCS",
#                 "underlying_token": "11536",
#             },
#             # Add more fallback instruments as needed
#         ]

#     @async_performance_timer
#     async def _load_data_files_async(self) -> Tuple[List[Dict], List[Dict]]:
#         """Load data files asynchronously with better error handling."""

#         async def load_json_file(file_path: Path) -> Any:
#             try:
#                 if not file_path.exists():
#                     logger.warning(f"⚠️ File not found: {file_path}")
#                     return []

#                 logger.info(f"📂 Loading {file_path.name}...")
#                 async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
#                     content = await f.read()
#                     data = json.loads(content)
#                     logger.info(f"✅ Loaded {file_path.name}")
#                     return data
#             except Exception as e:
#                 logger.warning(f"⚠️ Error loading {file_path}: {e}")
#                 return []

#         try:
#             # Load both files concurrently
#             top_stocks_task = load_json_file(self.top_stocks_file)
#             instruments_task = load_json_file(self.instruments_file)

#             top_stocks_data, instruments = await asyncio.gather(
#                 top_stocks_task, instruments_task
#             )

#             # Handle different JSON structure
#             if isinstance(top_stocks_data, dict) and "securities" in top_stocks_data:
#                 top_stocks = top_stocks_data["securities"]
#             elif isinstance(top_stocks_data, list):
#                 top_stocks = top_stocks_data
#             else:
#                 logger.warning("⚠️ Invalid top_stocks.json format, using fallback")
#                 top_stocks = []

#             if not isinstance(instruments, list):
#                 logger.warning(
#                     "⚠️ Invalid upstox_instruments.json format, using fallback"
#                 )
#                 instruments = []

#             logger.info(
#                 f"📊 Data loaded: {len(top_stocks)} stocks, {len(instruments)} instruments"
#             )
#             return top_stocks, instruments

#         except Exception as e:
#             logger.warning(f"⚠️ Error loading data files: {e}")
#             return [], []

#     @async_performance_timer
#     async def _build_optimized_indexes(self, instruments: List[Dict]) -> Dict:
#         """Build multiple indexes for ultra-fast lookups with progress tracking."""
#         logger.info(
#             f"🏗️ Building optimized indexes for {len(instruments)} instruments..."
#         )

#         indexes = {
#             "by_symbol": defaultdict(list),
#             "by_exchange_symbol": defaultdict(list),
#             "by_instrument_type": defaultdict(list),
#             "by_underlying": defaultdict(list),
#             "instrument_key_map": {},
#             "valid_instruments": set(),
#         }

#         current_time = datetime.now()
#         processed_count = 0
#         valid_count = 0

#         # Process in batches for better performance feedback
#         batch_size = 10000
#         for i in range(0, len(instruments), batch_size):
#             batch = instruments[i : i + batch_size]

#             for instrument in batch:
#                 try:
#                     processed_count += 1

#                     # Validate instrument
#                     if not self._is_instrument_valid(instrument, current_time):
#                         continue

#                     instrument_key = instrument.get("instrument_key")
#                     if not instrument_key:
#                         continue

#                     valid_count += 1

#                     # Add to valid instruments
#                     indexes["valid_instruments"].add(instrument_key)

#                     # Create instrument key mapping
#                     indexes["instrument_key_map"][instrument_key] = instrument

#                     # Index by multiple symbol fields
#                     symbol_fields = [
#                         "tradingsymbol",
#                         "underlying_symbol",
#                         "name",
#                         "symbol",
#                     ]
#                     for field in symbol_fields:
#                         symbol = instrument.get(field, "").strip().upper()
#                         if symbol:
#                             indexes["by_symbol"][symbol].append(instrument)

#                     # Index by exchange + symbol
#                     exchange = instrument.get("exchange", "").upper()
#                     for field in symbol_fields:
#                         symbol = instrument.get(field, "").strip().upper()
#                         if symbol and exchange:
#                             key = f"{exchange}_{symbol}"
#                             indexes["by_exchange_symbol"][key].append(instrument)

#                     # Index by instrument type
#                     instr_type = instrument.get("instrument_type", "").upper()
#                     if instr_type:
#                         indexes["by_instrument_type"][instr_type].append(instrument)

#                     # Index by underlying symbol
#                     underlying = instrument.get("underlying_symbol", "").strip().upper()
#                     if underlying:
#                         indexes["by_underlying"][underlying].append(instrument)

#                 except Exception as e:
#                     logger.warning(
#                         f"⚠️ Error indexing instrument {instrument.get('instrument_key', 'unknown')}: {e}"
#                     )
#                     continue

#             # Progress update
#             if processed_count % 50000 == 0:
#                 logger.info(
#                     f"📊 Processed {processed_count}/{len(instruments)} instruments, {valid_count} valid"
#                 )

#         logger.info(
#             f"🏗️ Indexing complete: {valid_count} valid instruments from {processed_count} processed"
#         )
#         logger.info(
#             f"📊 Index stats: {len(indexes['by_symbol'])} symbols, {len(indexes['by_exchange_symbol'])} exchange pairs"
#         )

#         return indexes

#     def _is_instrument_valid(self, instrument: Dict, current_time: datetime) -> bool:
#         """Check if instrument is valid for trading."""
#         # Check basic required fields
#         if not instrument.get("instrument_key"):
#             return False

#         # Check expiry for derivatives
#         expiry = instrument.get("expiry")
#         if expiry:
#             try:
#                 # Handle different expiry formats
#                 if isinstance(expiry, (int, float)):
#                     expiry_date = datetime.fromtimestamp(expiry / 1000)
#                 else:
#                     expiry_date = datetime.strptime(str(expiry), "%Y-%m-%d")

#                 if expiry_date < current_time:
#                     return False
#             except (ValueError, TypeError):
#                 pass  # Invalid expiry format, but don't reject

#         # Check if trading is allowed
#         segment = instrument.get("segment", "")
#         if "TEST" in segment.upper():
#             return False

#         return True

#     @async_performance_timer
#     async def _generate_stock_mappings(
#         self, top_stocks: List[Dict], indexes: Dict
#     ) -> Dict:
#         """Generate comprehensive mappings for each stock."""
#         logger.info(f"🎯 Generating mappings for {len(top_stocks)} stocks...")

#         stock_mappings = {}
#         processed_count = 0
#         mapped_count = 0

#         for stock in top_stocks:
#             try:
#                 processed_count += 1
#                 symbol = stock.get("symbol", "").strip().upper()
#                 exchange = stock.get("exchange", "NSE").strip().upper()
#                 name = stock.get("name", "")

#                 if not symbol:
#                     continue

#                 # Find all instruments for this stock
#                 instruments = self._find_stock_instruments(symbol, exchange, indexes)

#                 if instruments and any(
#                     len(instr_list) > 0 for instr_list in instruments.values()
#                 ):
#                     stock_mappings[symbol] = {
#                         "symbol": symbol,
#                         "name": name,
#                         "exchange": exchange,
#                         "instruments": instruments,
#                         "primary_instrument_key": self._get_primary_instrument_key(
#                             instruments
#                         ),
#                         "websocket_keys": self._get_websocket_keys(instruments),
#                         "instrument_count": sum(
#                             len(instr_list) for instr_list in instruments.values()
#                         ),
#                         "last_updated": datetime.now().isoformat(),
#                     }
#                     mapped_count += 1

#                     if mapped_count % 50 == 0:
#                         logger.info(f"📊 Mapped {mapped_count} stocks so far...")

#             except Exception as e:
#                 logger.warning(f"⚠️ Error mapping stock {symbol}: {e}")
#                 continue

#         logger.info(
#             f"🎯 Stock mapping complete: {mapped_count}/{processed_count} stocks mapped successfully"
#         )
#         return stock_mappings

#     def _find_stock_instruments(
#         self, symbol: str, exchange: str, indexes: Dict
#     ) -> Dict:
#         """Find all relevant instruments for a stock with enhanced matching."""
#         instruments = {"EQ": [], "INDEX": [], "FUT": [], "CE": [], "PE": []}

#         # Enhanced search strategies
#         search_keys = [
#             f"{exchange}_{symbol}",
#             symbol,
#             symbol.replace("-", ""),  # BAJAJ-AUTO -> BAJAJAUTO
#             symbol.replace("&", ""),  # M&M -> MM
#             symbol.replace(" ", ""),  # Handle spaces
#             symbol.replace(".", ""),  # Handle dots
#         ]

#         # Commodity and special symbol variations
#         special_variations = {
#             "CRUDEOIL": ["CRUDEOILM", "CRUDE"],
#             "GOLD": ["GOLDM", "GOLD MINI", "GOLDGUINEA"],
#             "SILVER": ["SILVERM", "SILVER MINI"],
#             "COPPER": ["COPPER MINI"],
#             "NATURALGAS": ["NATURALGAS MINI", "NATGAS"],
#             "NIFTY": ["NIFTY 50", "NIFTY50"],
#             "BANKNIFTY": ["BANK NIFTY", "BANKNIFTY"],
#         }

#         if symbol in special_variations:
#             search_keys.extend(special_variations[symbol])

#         # Search in all indexes
#         found_instruments = []

#         for key in search_keys:
#             # Search by exchange_symbol
#             found_instruments.extend(indexes["by_exchange_symbol"].get(key, []))
#             # Search by symbol
#             found_instruments.extend(indexes["by_symbol"].get(key, []))
#             # Search by underlying
#             found_instruments.extend(indexes["by_underlying"].get(key, []))

#         # Remove duplicates using instrument_key
#         unique_instruments = {}
#         for instr in found_instruments:
#             key = instr.get("instrument_key")
#             if key and key not in unique_instruments:
#                 unique_instruments[key] = instr

#         # Categorize instruments
#         categorized_count = 0
#         for instrument in unique_instruments.values():
#             instr_type = instrument.get("instrument_type", "").upper()
#             if instr_type in instruments:
#                 instruments[instr_type].append(instrument)
#                 categorized_count += 1

#         return instruments

#     def _get_primary_instrument_key(self, instruments: Dict) -> Optional[str]:
#         """Get the primary instrument key (EQ or INDEX)."""
#         for instr_type in ["EQ", "INDEX"]:
#             if instruments.get(instr_type):
#                 return instruments[instr_type][0].get("instrument_key")
#         return None

#     def _get_websocket_keys(self, instruments: Dict) -> List[str]:
#         """Get instrument keys suitable for WebSocket subscription."""
#         keys = []

#         # Always include EQ/INDEX
#         for instr_type in ["EQ", "INDEX"]:
#             for instr in instruments.get(instr_type, []):
#                 key = instr.get("instrument_key")
#                 if key:
#                     keys.append(key)

#         # Include limited futures and options
#         for instr in instruments.get("FUT", [])[:3]:  # Max 3 futures
#             key = instr.get("instrument_key")
#             if key:
#                 keys.append(key)

#         # Include ATM options with smart selection
#         for instr_type in ["CE", "PE"]:
#             options = instruments.get(instr_type, [])
#             if options:
#                 # Sort by strike price and select middle range
#                 sorted_options = sorted(options, key=lambda x: x.get("strike_price", 0))
#                 mid_count = min(15, len(sorted_options))  # Max 15 per type

#                 if mid_count > 0:
#                     start_idx = max(0, (len(sorted_options) - mid_count) // 2)
#                     selected_options = sorted_options[start_idx : start_idx + mid_count]

#                     for instr in selected_options:
#                         key = instr.get("instrument_key")
#                         if key:
#                             keys.append(key)

#         return [key for key in keys if key]

#     async def _cache_all_mappings(self, stock_mappings: Dict, indexes: Dict) -> int:
#         """Cache all mappings and return count of cached keys."""
#         logger.info("💾 Caching all mappings...")

#         try:
#             # Run caching operations in parallel
#             results = await asyncio.gather(
#                 self._cache_stock_mappings(stock_mappings),
#                 self._cache_reverse_mappings(stock_mappings),
#                 self._cache_indexes(indexes),
#                 self._cache_websocket_lists(stock_mappings),
#                 return_exceptions=True,
#             )

#             # Check for exceptions
#             exceptions = [r for r in results if isinstance(r, Exception)]
#             if exceptions:
#                 logger.warning(
#                     f"⚠️ Some caching operations failed: {len(exceptions)} errors"
#                 )

#             # Count cache keys
#             cache_count = await self._count_cache_keys()
#             logger.info(f"💾 Caching complete: {cache_count} keys cached")
#             return cache_count

#         except Exception as e:
#             logger.error(f"❌ Error in caching operations: {e}")
#             return 0

#     async def _cache_stock_mappings(self, stock_mappings: Dict):
#         """Cache individual stock mappings."""
#         try:
#             async with self.redis_client.pipeline() as pipe:
#                 for symbol, mapping in stock_mappings.items():
#                     cache_key = f"stock_mapping:{symbol}"
#                     pipe.setex(cache_key, self.cache_ttl, json.dumps(mapping))
#                 await pipe.execute()

#             logger.info(f"💾 Cached {len(stock_mappings)} stock mappings")
#         except Exception as e:
#             logger.error(f"❌ Error caching stock mappings: {e}")

#     async def _cache_reverse_mappings(self, stock_mappings: Dict):
#         """Cache reverse mappings for fast instrument_key -> stock lookups."""
#         try:
#             reverse_mapping = {}

#             for symbol, mapping in stock_mappings.items():
#                 for instr_type, instruments in mapping["instruments"].items():
#                     for instrument in instruments:
#                         instrument_key = instrument.get("instrument_key")
#                         if instrument_key:
#                             reverse_mapping[instrument_key] = {
#                                 "symbol": symbol,
#                                 "name": mapping["name"],
#                                 "exchange": mapping["exchange"],
#                                 "instrument_type": instr_type,
#                             }

#             cache_key = "reverse_instrument_mapping"
#             await self.redis_client.setex(
#                 cache_key, self.cache_ttl, json.dumps(reverse_mapping)
#             )

#             logger.info(
#                 f"💾 Cached reverse mapping for {len(reverse_mapping)} instruments"
#             )
#         except Exception as e:
#             logger.error(f"❌ Error caching reverse mappings: {e}")

#     async def _cache_indexes(self, indexes: Dict):
#         """Cache indexes for fast searches."""
#         try:
#             # Cache instrument key map
#             await self.redis_client.setex(
#                 "instrument_key_map",
#                 self.cache_ttl,
#                 json.dumps(indexes["instrument_key_map"]),
#             )

#             # Cache valid instruments set
#             await self.redis_client.setex(
#                 "valid_instruments",
#                 self.cache_ttl,
#                 json.dumps(list(indexes["valid_instruments"])),
#             )

#             logger.info("💾 Cached instrument indexes")
#         except Exception as e:
#             logger.error(f"❌ Error caching indexes: {e}")

#     async def _cache_websocket_lists(self, stock_mappings: Dict):
#         """Cache WebSocket subscription lists."""
#         try:
#             # Collect all WebSocket keys
#             all_ws_keys = []
#             for mapping in stock_mappings.values():
#                 all_ws_keys.extend(mapping["websocket_keys"])

#             # Remove duplicates
#             unique_ws_keys = list(set(all_ws_keys))

#             # Cache main list
#             await self.redis_client.setex(
#                 "websocket_instrument_keys", self.cache_ttl, json.dumps(unique_ws_keys)
#             )

#             # Cache by categories
#             categories = {"equity_keys": [], "futures_keys": [], "options_keys": []}

#             for key in unique_ws_keys:
#                 if "_EQ|" in key or "_INDEX|" in key:
#                     categories["equity_keys"].append(key)
#                 elif "_FO|" in key and ("FUT" in key or "FUTURE" in key):
#                     categories["futures_keys"].append(key)
#                 elif "_FO|" in key and ("CE" in key or "PE" in key):
#                     categories["options_keys"].append(key)

#             for category, keys in categories.items():
#                 await self.redis_client.setex(
#                     f"websocket_{category}", self.cache_ttl, json.dumps(keys)
#                 )

#             logger.info(f"💾 Cached {len(unique_ws_keys)} WebSocket keys in categories")
#         except Exception as e:
#             logger.error(f"❌ Error caching WebSocket lists: {e}")

#     @async_performance_timer
#     async def _prepare_websocket_instruments(self, stock_mappings: Dict) -> List[str]:
#         """Prepare optimized WebSocket instrument list."""
#         all_keys = []

#         for mapping in stock_mappings.values():
#             all_keys.extend(mapping["websocket_keys"])

#         # Remove duplicates
#         unique_keys = list(set(all_keys))

#         # Limit to prevent WebSocket overload
#         max_instruments = 1500  # Upstox limit
#         if len(unique_keys) > max_instruments:
#             # Prioritize EQ/INDEX instruments
#             priority_keys = [k for k in unique_keys if "_EQ|" in k or "_INDEX|" in k]
#             other_keys = [k for k in unique_keys if k not in priority_keys]

#             remaining_slots = max_instruments - len(priority_keys)
#             if remaining_slots > 0:
#                 unique_keys = priority_keys + other_keys[:remaining_slots]
#             else:
#                 unique_keys = priority_keys[:max_instruments]

#         logger.info(
#             f"🔗 Prepared {len(unique_keys)} WebSocket instruments (limit: {max_instruments})"
#         )
#         return unique_keys

#     async def _count_cache_keys(self) -> int:
#         """Count created cache keys."""
#         try:
#             patterns = ["stock_mapping:*", "websocket_*", "reverse_*", "instrument_*"]
#             total_keys = 0
#             for pattern in patterns:
#                 keys = await self.redis_client.keys(pattern)
#                 total_keys += len(keys)
#             return total_keys
#         except Exception as e:
#             logger.warning(f"⚠️ Error counting cache keys: {e}")
#             return 0

#     # ========== FAST ACCESS METHODS ==========

#     @performance_timer
#     def get_all_dashboard_instruments(self) -> List[str]:
#         """Get all dashboard instruments (spot keys for all stocks)."""
#         if not self._initialized:
#             logger.warning("⚠️ Service not initialized")
#             return []

#         dashboard_keys = []
#         for mapping in self._stock_mappings.values():
#             for instr_type in ["EQ", "INDEX"]:
#                 for instr in mapping["instruments"].get(instr_type, []):
#                     key = instr.get("instrument_key")
#                     if key:
#                         dashboard_keys.append(key)

#         return list(set(dashboard_keys))

#     @performance_timer
#     def get_trading_instruments_for_selected_stocks(
#         self, selected_stocks: List[Dict]
#     ) -> List[str]:
#         """Get comprehensive trading instruments for selected stocks."""
#         if not self._initialized:
#             logger.warning("⚠️ Service not initialized")
#             return []

#         trading_keys = []
#         processed_count = 0

#         for stock in selected_stocks[:10]:  # Limit to 10 stocks
#             symbol = stock.get("symbol", "").upper()
#             current_price = float(stock.get("ltp", stock.get("entry_price", 0)))

#             if symbol not in self._stock_mappings:
#                 logger.warning(f"⚠️ Symbol {symbol} not found in mappings")
#                 continue

#             mapping = self._stock_mappings[symbol]
#             instruments = mapping["instruments"]

#             # Add spot instrument
#             for instr in instruments.get("EQ", []) + instruments.get("INDEX", []):
#                 key = instr.get("instrument_key")
#                 if key:
#                     trading_keys.append(key)

#             # Add futures
#             futures = sorted(
#                 instruments.get("FUT", []), key=lambda x: x.get("expiry", 0)
#             )[:3]
#             for future in futures:
#                 key = future.get("instrument_key")
#                 if key:
#                     trading_keys.append(key)

#             # Add ATM options
#             if current_price > 0:
#                 option_keys = self._get_atm_options(symbol, current_price, instruments)
#                 trading_keys.extend(option_keys)

#             processed_count += 1

#         logger.info(
#             f"📊 Generated {len(set(trading_keys))} trading instruments for {processed_count} stocks"
#         )
#         return list(set(trading_keys))

#     def _get_atm_options(
#         self, symbol: str, current_price: float, instruments: Dict
#     ) -> List[str]:
#         """Get option keys around ATM price."""
#         option_keys = []

#         # Calculate strike step
#         if current_price < 100:
#             strike_step = 5
#         elif current_price < 500:
#             strike_step = 10
#         elif current_price < 1000:
#             strike_step = 25
#         else:
#             strike_step = 50

#         atm_strike = round(current_price / strike_step) * strike_step

#         # Define range
#         if current_price < 500:
#             strike_range = 100
#         elif current_price < 2000:
#             strike_range = 200
#         else:
#             strike_range = 500

#         min_strike = atm_strike - strike_range
#         max_strike = atm_strike + strike_range

#         # Get options within range
#         for option_type in ["CE", "PE"]:
#             options = instruments.get(option_type, [])
#             for option in options:
#                 strike = option.get("strike_price", 0)
#                 if min_strike <= strike <= max_strike:
#                     key = option.get("instrument_key")
#                     if key:
#                         option_keys.append(key)

#         return option_keys

#     def get_stock_instruments(self, symbol: str) -> Optional[Dict]:
#         """Get all instruments for a stock symbol."""
#         if not self._initialized:
#             logger.warning("⚠️ Service not initialized")
#             return None
#         return self._stock_mappings.get(symbol.upper())

#     def get_primary_instrument_key(self, symbol: str) -> Optional[str]:
#         """Get primary instrument key for a stock."""
#         mapping = self.get_stock_instruments(symbol)
#         return mapping.get("primary_instrument_key") if mapping else None

#     def get_websocket_keys_for_stock(self, symbol: str) -> List[str]:
#         """Get WebSocket keys for a specific stock."""
#         mapping = self.get_stock_instruments(symbol)
#         return mapping.get("websocket_keys", []) if mapping else []

#     def is_initialized(self) -> bool:
#         """Check if service is initialized."""
#         return self._initialized

#     async def get_service_stats(self) -> ServiceStats:
#         """Get comprehensive service statistics."""
#         try:
#             redis_connected = (
#                 await self.redis_client.ping() if self.redis_client else False
#             )
#         except:
#             redis_connected = False

#         return ServiceStats(
#             initialized=self._initialized,
#             total_stocks_mapped=len(self._stock_mappings),
#             total_instrument_keys=len(self._instrument_key_map),
#             valid_instruments=len(self._valid_instruments),
#             websocket_keys=len(self._websocket_keys),
#             cache_available=redis_connected,
#             redis_connected=redis_connected,
#             last_update=(
#                 self._initialization_time.isoformat()
#                 if self._initialization_time
#                 else ""
#             ),
#         )

#     async def health_check(self) -> Dict[str, Any]:
#         """Comprehensive health check for monitoring."""
#         try:
#             stats = await self.get_service_stats()
#             status = "healthy" if stats.initialized else "degraded"

#             return {
#                 "status": status,
#                 "service_stats": asdict(stats),
#                 "timestamp": datetime.now().isoformat(),
#                 "version": "2.1.0",
#             }
#         except Exception as e:
#             return {
#                 "status": "unhealthy",
#                 "error": str(e),
#                 "timestamp": datetime.now().isoformat(),
#                 "version": "2.1.0",
#             }

#     async def clear_cache(self):
#         """Clear all cached data."""
#         try:
#             if self.redis_client:
#                 patterns = [
#                     "stock_mapping:*",
#                     "websocket_*",
#                     "reverse_*",
#                     "instrument_*",
#                 ]
#                 for pattern in patterns:
#                     keys = await self.redis_client.keys(pattern)
#                     if keys:
#                         await self.redis_client.delete(*keys)
#                 logger.info("🗑️ Cache cleared successfully")
#         except Exception as e:
#             logger.error(f"❌ Error clearing cache: {e}")


# class FastInstrumentRetrieval:
#     """Ultra-fast instrument data retrieval for trading operations."""

#     def __init__(self, service: OptimizedInstrumentService):
#         self.service = service

#     @performance_timer
#     def get_stock_instruments(self, symbol: str) -> Optional[Dict]:
#         """Get all instruments for a stock symbol (sync version)."""
#         return self.service.get_stock_instruments(symbol)

#     async def get_stock_instruments_async(self, symbol: str) -> Optional[Dict]:
#         """Get all instruments for a stock symbol (async version)."""
#         try:
#             if self.service._initialized:
#                 return self.service.get_stock_instruments(symbol)

#             # Try from cache if service not initialized
#             await self.service._ensure_cache_connection()
#             cache_key = f"stock_mapping:{symbol.upper()}"
#             cached = await self.service.redis_client.get(cache_key)
#             return json.loads(cached) if cached else None
#         except Exception as e:
#             logger.error(f"❌ Error getting instruments for {symbol}: {e}")
#             return None

#     def get_primary_instrument_key(self, symbol: str) -> Optional[str]:
#         """Get primary instrument key for a stock."""
#         return self.service.get_primary_instrument_key(symbol)

#     async def get_primary_instrument_key_async(self, symbol: str) -> Optional[str]:
#         """Get primary instrument key for a stock (async version)."""
#         mapping = await self.get_stock_instruments_async(symbol)
#         return mapping.get("primary_instrument_key") if mapping else None

#     def get_websocket_keys_for_stock(self, symbol: str) -> List[str]:
#         """Get WebSocket keys for a specific stock."""
#         return self.service.get_websocket_keys_for_stock(symbol)

#     async def get_websocket_keys_for_stock_async(self, symbol: str) -> List[str]:
#         """Get WebSocket keys for a specific stock (async version)."""
#         mapping = await self.get_stock_instruments_async(symbol)
#         return mapping.get("websocket_keys", []) if mapping else []

#     async def get_all_websocket_keys(self) -> List[str]:
#         """Get all WebSocket instrument keys."""
#         try:
#             if self.service._initialized:
#                 return self.service._websocket_keys

#             # Try from cache
#             await self.service._ensure_cache_connection()
#             cached = await self.service.redis_client.get("websocket_instrument_keys")
#             return json.loads(cached) if cached else []
#         except Exception as e:
#             logger.error(f"❌ Error getting WebSocket keys: {e}")
#             return []

#     async def get_stock_from_instrument_key(
#         self, instrument_key: str
#     ) -> Optional[Dict]:
#         """Get stock info from instrument key."""
#         try:
#             await self.service._ensure_cache_connection()
#             cached = await self.service.redis_client.get("reverse_instrument_mapping")
#             if cached:
#                 reverse_mapping = json.loads(cached)
#                 return reverse_mapping.get(instrument_key)
#         except Exception as e:
#             logger.error(f"❌ Error getting stock for {instrument_key}: {e}")
#         return None

#     def get_symbol_from_instrument_key(self, instrument_key: str) -> Optional[str]:
#         """Get symbol from instrument key (sync version)."""
#         try:
#             if self.service._initialized:
#                 instrument = self.service._instrument_key_map.get(instrument_key)
#                 if instrument:
#                     return instrument.get("tradingsymbol") or instrument.get(
#                         "underlying_symbol"
#                     )

#             # Fallback: parse from key format
#             if "|" in instrument_key:
#                 parts = instrument_key.split("|")
#                 if len(parts) >= 2:
#                     detail = parts[1]
#                     # For F&O, extract symbol before expiry/strike
#                     if "-" in detail:
#                         return detail.split("-")[0]
#                     return detail

#             return None
#         except Exception as e:
#             logger.debug(f"Error getting symbol from {instrument_key}: {e}")
#             return None

#     async def get_instrument_details(self, instrument_key: str) -> Optional[Dict]:
#         """Get detailed instrument information."""
#         try:
#             if self.service._initialized:
#                 return self.service._instrument_key_map.get(instrument_key)

#             # Try from cache
#             await self.service._ensure_cache_connection()
#             cached = await self.service.redis_client.get("instrument_key_map")
#             if cached:
#                 instrument_map = json.loads(cached)
#                 return instrument_map.get(instrument_key)
#         except Exception as e:
#             logger.error(
#                 f"❌ Error getting instrument details for {instrument_key}: {e}"
#             )
#         return None

#     async def is_valid_instrument(self, instrument_key: str) -> bool:
#         """Check if instrument key is valid for trading."""
#         try:
#             if self.service._initialized:
#                 return instrument_key in self.service._valid_instruments

#             # Try from cache
#             await self.service._ensure_cache_connection()
#             cached = await self.service.redis_client.get("valid_instruments")
#             if cached:
#                 valid_instruments = json.loads(cached)
#                 return instrument_key in valid_instruments
#         except Exception as e:
#             logger.error(f"❌ Error checking validity for {instrument_key}: {e}")
#         return False

#     async def search_instruments(self, query: str, limit: int = 50) -> List[Dict]:
#         """Search instruments by symbol or name."""
#         try:
#             if self.service._initialized:
#                 instrument_map = self.service._instrument_key_map
#             else:
#                 await self.service._ensure_cache_connection()
#                 cached = await self.service.redis_client.get("instrument_key_map")
#                 if not cached:
#                     return []
#                 instrument_map = json.loads(cached)

#             query_upper = query.upper()
#             results = []

#             for instr in instrument_map.values():
#                 search_fields = [
#                     instr.get("tradingsymbol", ""),
#                     instr.get("name", ""),
#                     instr.get("underlying_symbol", ""),
#                     instr.get("symbol", ""),
#                 ]

#                 if any(query_upper in field.upper() for field in search_fields):
#                     results.append(instr)
#                     if len(results) >= limit:
#                         break

#             return results
#         except Exception as e:
#             logger.error(f"❌ Error searching instruments: {e}")
#         return []


# # ========== FIXED SINGLETON PATTERN ==========

# # Global instance with proper initialization
# _instrument_service_instance = None
# _fast_retrieval_instance = None


# def get_instrument_service() -> OptimizedInstrumentService:
#     """Get the singleton instrument service instance."""
#     global _instrument_service_instance
#     if _instrument_service_instance is None:
#         _instrument_service_instance = OptimizedInstrumentService()
#     return _instrument_service_instance


# def get_fast_retrieval() -> FastInstrumentRetrieval:
#     """Get the singleton fast retrieval instance."""
#     global _fast_retrieval_instance
#     if _fast_retrieval_instance is None:
#         _fast_retrieval_instance = FastInstrumentRetrieval(get_instrument_service())
#     return _fast_retrieval_instance


# # ========== CONVENIENCE FUNCTIONS ==========


# async def initialize_instrument_system(**kwargs) -> InitializationResult:
#     """Initialize the instrument system."""
#     service = get_instrument_service()
#     return await service.initialize_instruments_system()


# def get_optimized_instruments() -> List[str]:
#     """Get all dashboard instruments."""
#     service = get_instrument_service()
#     return service.get_all_dashboard_instruments()


# def get_trading_instruments_for_selected_stocks(
#     selected_stocks: List[Dict],
# ) -> List[str]:
#     """Get trading instruments for selected stocks."""
#     service = get_instrument_service()
#     return service.get_trading_instruments_for_selected_stocks(selected_stocks)


# def get_stock_instruments(symbol: str) -> Optional[Dict]:
#     """Get instruments for a stock symbol."""
#     service = get_instrument_service()
#     return service.get_stock_instruments(symbol)


# async def get_stock_instruments_async(symbol: str) -> Optional[Dict]:
#     """Get instruments for a stock symbol (async version)."""
#     retrieval = get_fast_retrieval()
#     return await retrieval.get_stock_instruments_async(symbol)


# def get_primary_instrument_key(symbol: str) -> Optional[str]:
#     """Get primary instrument key for a stock."""
#     service = get_instrument_service()
#     return service.get_primary_instrument_key(symbol)


# async def get_primary_instrument_key_async(symbol: str) -> Optional[str]:
#     """Get primary instrument key for a stock (async version)."""
#     retrieval = get_fast_retrieval()
#     return await retrieval.get_primary_instrument_key_async(symbol)


# def get_websocket_keys_for_stock(symbol: str) -> List[str]:
#     """Get WebSocket keys for a specific stock."""
#     service = get_instrument_service()
#     return service.get_websocket_keys_for_stock(symbol)


# async def get_all_websocket_keys() -> List[str]:
#     """Get all WebSocket instrument keys."""
#     retrieval = get_fast_retrieval()
#     return await retrieval.get_all_websocket_keys()


# async def get_instrument_details(instrument_key: str) -> Optional[Dict]:
#     """Get detailed instrument information."""
#     retrieval = get_fast_retrieval()
#     return await retrieval.get_instrument_details(instrument_key)


# async def search_instruments(query: str, limit: int = 50) -> List[Dict]:
#     """Search instruments by symbol or name."""
#     retrieval = get_fast_retrieval()
#     return await retrieval.search_instruments(query, limit)


# async def is_valid_instrument(instrument_key: str) -> bool:
#     """Check if instrument key is valid for trading."""
#     retrieval = get_fast_retrieval()
#     return await retrieval.is_valid_instrument(instrument_key)


# async def health_check() -> Dict[str, Any]:
#     """Health check for monitoring."""
#     service = get_instrument_service()
#     return await service.health_check()


# async def get_service_stats() -> ServiceStats:
#     """Get service statistics."""
#     service = get_instrument_service()
#     return await service.get_service_stats()


# def is_initialized() -> bool:
#     """Check if service is initialized."""
#     service = get_instrument_service()
#     return service.is_initialized()


# async def clear_cache():
#     """Clear all cached data."""
#     service = get_instrument_service()
#     await service.clear_cache()


# # ========== BACKWARD COMPATIBILITY FUNCTIONS ==========


# def get_top_stocks_with_chain() -> List[Dict]:
#     """Get top stocks with option chain data (backward compatibility)."""
#     service = get_instrument_service()
#     if not service._initialized:
#         logger.warning("⚠️ Service not initialized")
#         return []

#     stocks = []
#     for symbol, mapping in service._stock_mappings.items():
#         if mapping["instruments"].get("EQ") or mapping["instruments"].get("INDEX"):
#             stocks.append(
#                 {
#                     "symbol": symbol,
#                     "name": mapping["name"],
#                     "exchange": mapping["exchange"],
#                     "primary_instrument_key": mapping["primary_instrument_key"],
#                     "instrument_count": mapping["instrument_count"],
#                 }
#             )
#     return stocks


# def get_top_stock_details() -> Dict[str, Any]:
#     """Get comprehensive top stock details (backward compatibility)."""
#     service = get_instrument_service()
#     if not service._initialized:
#         logger.warning("⚠️ Service not initialized")
#         return {"data": {}, "error": "Service not initialized"}

#     return {
#         "data": service._stock_mappings,
#         "metadata": {
#             "total_symbols": len(service._stock_mappings),
#             "total_instruments": len(service._instrument_key_map),
#             "timestamp": datetime.now().isoformat(),
#         },
#     }


# def get_spot_instrument_keys() -> List[str]:
#     """Get spot instrument keys (backward compatibility)."""
#     service = get_instrument_service()
#     return service.get_all_dashboard_instruments()


# # ========== PERFORMANCE TESTING ==========


# async def performance_test():
#     """Run comprehensive performance tests."""
#     logger.info("🧪 Starting enhanced performance tests...")

#     start_time = time.time()

#     # Test initialization
#     logger.info("🔧 Testing initialization...")
#     init_result = await initialize_instrument_system()
#     init_time = time.time() - start_time

#     if init_result.status != "success":
#         logger.error(f"❌ Initialization failed: {init_result.error}")
#         return {"error": "Initialization failed", "details": init_result.error}

#     # Test fast retrieval
#     logger.info("⚡ Testing fast retrieval...")
#     test_symbols = ["RELIANCE", "TCS", "INFY", "HDFC", "ICICIBANK"]
#     retrieval_start = time.time()

#     retrieval_results = {}
#     for symbol in test_symbols:
#         instruments = await get_stock_instruments_async(symbol)
#         primary_key = await get_primary_instrument_key_async(symbol)
#         retrieval_results[symbol] = {
#             "found": instruments is not None,
#             "has_primary_key": primary_key is not None,
#             "instrument_count": (
#                 instruments.get("instrument_count", 0) if instruments else 0
#             ),
#         }

#     retrieval_time = time.time() - retrieval_start

#     # Test WebSocket keys
#     logger.info("🔗 Testing WebSocket keys...")
#     ws_start = time.time()
#     ws_keys = await get_all_websocket_keys()
#     ws_time = time.time() - ws_start

#     # Test search functionality
#     logger.info("🔍 Testing search...")
#     search_start = time.time()
#     search_results = await search_instruments("RELIANCE", 10)
#     search_time = time.time() - search_start

#     # Test health check
#     logger.info("🏥 Testing health check...")
#     health_start = time.time()
#     health = await health_check()
#     health_time = time.time() - health_start

#     # Test backward compatibility
#     logger.info("🔄 Testing backward compatibility...")
#     compat_start = time.time()
#     top_stocks = get_top_stocks_with_chain()
#     top_details = get_top_stock_details()
#     spot_keys = get_spot_instrument_keys()
#     compat_time = time.time() - compat_start

#     total_time = time.time() - start_time

#     results = {
#         "status": "success",
#         "total_time": total_time,
#         "initialization_time": init_time,
#         "retrieval_time": retrieval_time,
#         "websocket_keys_time": ws_time,
#         "search_time": search_time,
#         "health_check_time": health_time,
#         "compatibility_time": compat_time,
#         "counts": {
#             "mapped_stocks": init_result.mapped_stocks,
#             "websocket_keys": len(ws_keys),
#             "search_results": len(search_results),
#             "top_stocks": len(top_stocks),
#             "spot_keys": len(spot_keys),
#         },
#         "retrieval_results": retrieval_results,
#         "health_status": health["status"],
#         "cache_type": "Redis" if REDIS_AVAILABLE else "In-Memory",
#     }

#     logger.info(f"🧪 Enhanced performance test completed in {total_time:.3f}s")
#     return results


# if __name__ == "__main__":
#     # Enhanced testing
#     async def main():
#         logger.info("🧪 Testing Enhanced Optimized Instrument Service")

#         # Run comprehensive performance test
#         results = await performance_test()

#         if "error" in results:
#             print(f"❌ Test failed: {results['error']}")
#             return

#         print(f"\n📊 Performance Test Results:")
#         print(f"   Total Time: {results['total_time']:.3f}s")
#         print(f"   Initialization: {results['initialization_time']:.3f}s")
#         print(f"   Cache Type: {results['cache_type']}")
#         print(f"   Mapped Stocks: {results['counts']['mapped_stocks']}")
#         print(f"   WebSocket Keys: {results['counts']['websocket_keys']}")
#         print(f"   Search Results: {results['counts']['search_results']}")
#         print(f"   Health Status: {results['health_status']}")

#         print(f"\n🔍 Stock Retrieval Test:")
#         for symbol, result in results["retrieval_results"].items():
#             status = "✅" if result["found"] else "❌"
#             print(f"   {symbol}: {status} (Instruments: {result['instrument_count']})")

#         print("\n✅ All tests completed successfully!")

#     asyncio.run(main())
