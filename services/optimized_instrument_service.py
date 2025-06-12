import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional
from pathlib import Path
import redis
from collections import defaultdict
import aiofiles

logger = logging.getLogger(__name__)


class OptimizedInstrumentService:
    """
    High-performance instrument service that builds and caches instrument keys
    for ultra-fast access during trading hours.
    """

    def __init__(self):
        self.redis_client = redis.Redis(
            host="localhost", port=6379, db=1, decode_responses=True
        )
        self.cache_ttl = 86400  # 24 hours
        self.batch_size = 1000

    async def initialize_instruments_system(self) -> Dict:
        """
        Complete instrument system initialization.
        Should be called during application startup or pre-market.
        """
        start_time = datetime.now()
        logger.info("🔧 Initializing instruments system...")

        try:
            # Step 1: Load and validate data files
            top_stocks, instruments = await self._load_data_files_async()

            # Step 2: Build optimized indexes
            indexes = await self._build_optimized_indexes(instruments)

            # Step 3: Generate instrument mappings for top stocks
            stock_mappings = await self._generate_stock_mappings(top_stocks, indexes)

            # Step 4: Cache everything for production use
            await self._cache_all_mappings(stock_mappings, indexes)

            # Step 5: Prepare WebSocket subscription lists
            ws_instruments = await self._prepare_websocket_instruments(stock_mappings)

            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            result = {
                "status": "success",
                "processing_time": processing_time,
                "total_stocks": len(top_stocks),
                "total_instruments": len(instruments),
                "mapped_stocks": len(stock_mappings),
                "websocket_instruments": len(ws_instruments),
                "cache_keys_created": await self._count_cache_keys(),
                "initialized_at": datetime.now().isoformat(),
            }

            logger.info(f"✅ Instruments system initialized in {processing_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"❌ Instruments initialization failed: {e}")
            raise

    async def _load_data_files_async(self) -> tuple[List[Dict], List[Dict]]:
        """Load data files asynchronously for better performance."""
        try:

            async def load_json_file(file_path: str):
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                    return json.loads(content)

            # Load both files concurrently
            top_stocks_task = load_json_file("data/top_stocks.json")
            instruments_task = load_json_file("data/upstox_instruments.json")

            top_stocks_data, instruments = await asyncio.gather(
                top_stocks_task, instruments_task
            )

            top_stocks = top_stocks_data.get("securities", [])

            logger.info(
                f"📂 Loaded {len(top_stocks)} stocks and {len(instruments)} instruments"
            )
            return top_stocks, instruments

        except Exception as e:
            logger.error(f"Error loading data files: {e}")
            raise

    async def _build_optimized_indexes(self, instruments: List[Dict]) -> Dict:
        """Build multiple indexes for ultra-fast lookups."""
        logger.info("🏗️ Building optimized indexes...")

        indexes = {
            "by_symbol": defaultdict(list),
            "by_exchange_symbol": defaultdict(list),
            "by_instrument_type": defaultdict(list),
            "by_underlying": defaultdict(list),
            "instrument_key_map": {},
            "valid_instruments": set(),
        }

        current_time = datetime.now()

        for instrument in instruments:
            try:
                # Validate instrument
                if not self._is_instrument_valid(instrument, current_time):
                    continue

                instrument_key = instrument.get("instrument_key")
                if not instrument_key:
                    continue

                # Add to valid instruments
                indexes["valid_instruments"].add(instrument_key)

                # Create instrument key mapping
                indexes["instrument_key_map"][instrument_key] = instrument

                # Index by multiple symbol fields
                symbol_fields = ["trading_symbol", "underlying_symbol", "name"]
                for field in symbol_fields:
                    symbol = instrument.get(field, "").strip().upper()
                    if symbol:
                        indexes["by_symbol"][symbol].append(instrument)

                # Index by exchange + symbol
                exchange = instrument.get("exchange", "").upper()
                for field in symbol_fields:
                    symbol = instrument.get(field, "").strip().upper()
                    if symbol and exchange:
                        key = f"{exchange}_{symbol}"
                        indexes["by_exchange_symbol"][key].append(instrument)

                # Index by instrument type
                instr_type = instrument.get("instrument_type", "").upper()
                if instr_type:
                    indexes["by_instrument_type"][instr_type].append(instrument)

                # Index by underlying symbol
                underlying = instrument.get("underlying_symbol", "").strip().upper()
                if underlying:
                    indexes["by_underlying"][underlying].append(instrument)

            except Exception as e:
                logger.warning(f"Error indexing instrument: {e}")
                continue

        logger.info(
            f"🏗️ Built indexes with {len(indexes['valid_instruments'])} valid instruments"
        )
        return indexes

    def _is_instrument_valid(self, instrument: Dict, current_time: datetime) -> bool:
        """Check if instrument is valid for trading."""
        # Check basic required fields
        if not instrument.get("instrument_key"):
            return False

        # Check expiry for derivatives
        expiry = instrument.get("expiry")
        if expiry:
            try:
                expiry_date = datetime.fromtimestamp(expiry / 1000)
                if expiry_date < current_time:
                    return False
            except (ValueError, TypeError):
                return False

        # Check if trading is allowed
        segment = instrument.get("segment", "")
        if "TEST" in segment.upper():
            return False

        return True

    async def _generate_stock_mappings(
        self, top_stocks: List[Dict], indexes: Dict
    ) -> Dict:
        """Generate comprehensive mappings for each stock."""
        logger.info(f"🎯 Generating mappings for {len(top_stocks)} stocks...")

        stock_mappings = {}

        for stock in top_stocks:
            try:
                symbol = stock.get("symbol", "").strip().upper()
                exchange = stock.get("exchange", "").strip().upper()
                name = stock.get("name", "")

                if not symbol or not exchange:
                    continue

                # Find all instruments for this stock
                instruments = self._find_stock_instruments(symbol, exchange, indexes)

                if instruments:
                    stock_mappings[symbol] = {
                        "symbol": symbol,
                        "name": name,
                        "exchange": exchange,
                        "instruments": instruments,
                        "primary_instrument_key": self._get_primary_instrument_key(
                            instruments
                        ),
                        "websocket_keys": self._get_websocket_keys(instruments),
                        "instrument_count": len(instruments),
                    }

            except Exception as e:
                logger.warning(f"Error mapping stock {symbol}: {e}")
                continue

        logger.info(f"🎯 Generated mappings for {len(stock_mappings)} stocks")
        return stock_mappings

    def _find_stock_instruments(
        self, symbol: str, exchange: str, indexes: Dict
    ) -> Dict:
        """Find all relevant instruments for a stock."""
        instruments = {"EQ": [], "INDEX": [], "FUT": [], "CE": [], "PE": []}

        # Search strategies
        search_keys = [
            f"{exchange}_{symbol}",
            symbol,
            symbol.replace("-", ""),  # Handle symbols like BAJAJ-AUTO
            symbol.replace("&", ""),  # Handle symbols like M&M
        ]

        # Add common variations
        if symbol == "CRUDEOIL":
            search_keys.extend(["CRUDEOILM", "CRUDE"])
        elif symbol == "GOLD":
            search_keys.extend(["GOLDM", "GOLD MINI"])

        # Search in indexes
        found_instruments = []
        for key in search_keys:
            found_instruments.extend(indexes["by_exchange_symbol"].get(key, []))
            found_instruments.extend(indexes["by_symbol"].get(key, []))

        # Remove duplicates
        unique_instruments = {
            instr["instrument_key"]: instr for instr in found_instruments
        }

        # Categorize instruments
        for instrument in unique_instruments.values():
            instr_type = instrument.get("instrument_type", "").upper()
            if instr_type in instruments:
                instruments[instr_type].append(instrument)

        return instruments

    def _get_primary_instrument_key(self, instruments: Dict) -> Optional[str]:
        """Get the primary instrument key (EQ or INDEX)."""
        for instr_type in ["EQ", "INDEX"]:
            if instruments.get(instr_type):
                return instruments[instr_type][0].get("instrument_key")
        return None

    def _get_websocket_keys(self, instruments: Dict) -> List[str]:
        """Get instrument keys suitable for WebSocket subscription."""
        keys = []

        # Always include EQ/INDEX
        for instr_type in ["EQ", "INDEX"]:
            for instr in instruments.get(instr_type, []):
                keys.append(instr.get("instrument_key"))

        # Include limited futures and options
        for instr in instruments.get("FUT", [])[:2]:  # Max 2 futures
            keys.append(instr.get("instrument_key"))

        # Include ATM options only
        for instr_type in ["CE", "PE"]:
            sorted_options = sorted(
                instruments.get(instr_type, []), key=lambda x: x.get("strike_price", 0)
            )
            for instr in sorted_options[:3]:  # Max 3 per type
                keys.append(instr.get("instrument_key"))

        return [key for key in keys if key]

    async def _cache_all_mappings(self, stock_mappings: Dict, indexes: Dict):
        """Cache all mappings for production use."""
        logger.info("💾 Caching all mappings...")

        try:
            # Cache stock mappings
            await self._cache_stock_mappings(stock_mappings)

            # Cache reverse mappings (instrument_key -> stock)
            await self._cache_reverse_mappings(stock_mappings)

            # Cache indexes for fast lookups
            await self._cache_indexes(indexes)

            # Cache WebSocket instrument lists
            await self._cache_websocket_lists(stock_mappings)

            logger.info("💾 All mappings cached successfully")

        except Exception as e:
            logger.error(f"Error caching mappings: {e}")
            raise

    async def _cache_stock_mappings(self, stock_mappings: Dict):
        """Cache individual stock mappings."""
        pipe = self.redis_client.pipeline()

        for symbol, mapping in stock_mappings.items():
            cache_key = f"stock_mapping:{symbol}"
            pipe.setex(cache_key, self.cache_ttl, json.dumps(mapping))

        await asyncio.get_event_loop().run_in_executor(None, pipe.execute)
        logger.info(f"💾 Cached {len(stock_mappings)} stock mappings")

    async def _cache_reverse_mappings(self, stock_mappings: Dict):
        """Cache reverse mappings for fast instrument_key -> stock lookups."""
        reverse_mapping = {}

        for symbol, mapping in stock_mappings.items():
            # Map all instrument keys to this stock
            for instr_type, instruments in mapping["instruments"].items():
                for instrument in instruments:
                    instrument_key = instrument.get("instrument_key")
                    if instrument_key:
                        reverse_mapping[instrument_key] = {
                            "symbol": symbol,
                            "name": mapping["name"],
                            "exchange": mapping["exchange"],
                            "instrument_type": instr_type,
                        }

        # Cache the complete reverse mapping
        cache_key = "reverse_instrument_mapping"
        self.redis_client.setex(cache_key, self.cache_ttl, json.dumps(reverse_mapping))

        logger.info(f"💾 Cached reverse mapping for {len(reverse_mapping)} instruments")

    async def _cache_indexes(self, indexes: Dict):
        """Cache indexes for fast searches."""
        # Cache instrument key map
        cache_key = "instrument_key_map"
        self.redis_client.setex(
            cache_key, self.cache_ttl, json.dumps(indexes["instrument_key_map"])
        )

        # Cache valid instruments set
        cache_key = "valid_instruments"
        self.redis_client.setex(
            cache_key, self.cache_ttl, json.dumps(list(indexes["valid_instruments"]))
        )

        logger.info("💾 Cached instrument indexes")

    async def _cache_websocket_lists(self, stock_mappings: Dict):
        """Cache WebSocket subscription lists."""
        # All WebSocket keys
        all_ws_keys = []
        for mapping in stock_mappings.values():
            all_ws_keys.extend(mapping["websocket_keys"])

        # Remove duplicates and cache
        unique_ws_keys = list(set(all_ws_keys))

        cache_key = "websocket_instrument_keys"
        self.redis_client.setex(cache_key, self.cache_ttl, json.dumps(unique_ws_keys))

        # Cache by categories
        categories = {"equity_keys": [], "futures_keys": [], "options_keys": []}

        for key in unique_ws_keys:
            if "_EQ|" in key or "_INDEX|" in key:
                categories["equity_keys"].append(key)
            elif "_FO|" in key and ("FUT" in key or "FUTURE" in key):
                categories["futures_keys"].append(key)
            elif "_FO|" in key and ("CE" in key or "PE" in key):
                categories["options_keys"].append(key)

        for category, keys in categories.items():
            cache_key = f"websocket_{category}"
            self.redis_client.setex(cache_key, self.cache_ttl, json.dumps(keys))

        logger.info(f"💾 Cached {len(unique_ws_keys)} WebSocket keys in categories")

    async def _prepare_websocket_instruments(self, stock_mappings: Dict) -> List[str]:
        """Prepare optimized WebSocket instrument list."""
        all_keys = []

        for mapping in stock_mappings.values():
            all_keys.extend(mapping["websocket_keys"])

        # Remove duplicates and limit for performance
        unique_keys = list(set(all_keys))

        # Limit to prevent WebSocket overload
        max_instruments = 1500  # Upstox limit
        if len(unique_keys) > max_instruments:
            # Prioritize EQ/INDEX instruments
            priority_keys = [k for k in unique_keys if "_EQ|" in k or "_INDEX|" in k]
            other_keys = [k for k in unique_keys if k not in priority_keys]

            remaining_slots = max_instruments - len(priority_keys)
            if remaining_slots > 0:
                unique_keys = priority_keys + other_keys[:remaining_slots]
            else:
                unique_keys = priority_keys[:max_instruments]

        logger.info(f"🔗 Prepared {len(unique_keys)} WebSocket instruments")
        return unique_keys

    async def _count_cache_keys(self) -> int:
        """Count created cache keys."""
        try:
            keys = self.redis_client.keys("stock_mapping:*")
            keys.extend(self.redis_client.keys("websocket_*"))
            keys.extend(self.redis_client.keys("reverse_*"))
            keys.extend(self.redis_client.keys("instrument_*"))
            return len(keys)
        except:
            return 0


# Fast retrieval functions for production use
class FastInstrumentRetrieval:
    """Ultra-fast instrument data retrieval for trading operations."""

    def __init__(self):
        self.redis_client = redis.Redis(
            host="localhost", port=6379, db=1, decode_responses=True
        )

    def get_stock_instruments(self, symbol: str) -> Optional[Dict]:
        """Get all instruments for a stock symbol."""
        try:
            cache_key = f"stock_mapping:{symbol.upper()}"
            cached = self.redis_client.get(cache_key)
            return json.loads(cached) if cached else None
        except Exception as e:
            logger.error(f"Error getting instruments for {symbol}: {e}")
            return None

    def get_primary_instrument_key(self, symbol: str) -> Optional[str]:
        """Get primary instrument key for a stock."""
        mapping = self.get_stock_instruments(symbol)
        return mapping.get("primary_instrument_key") if mapping else None

    def get_websocket_keys_for_stock(self, symbol: str) -> List[str]:
        """Get WebSocket keys for a specific stock."""
        mapping = self.get_stock_instruments(symbol)
        return mapping.get("websocket_keys", []) if mapping else []

    def get_all_websocket_keys(self) -> List[str]:
        """Get all WebSocket instrument keys."""
        try:
            cached = self.redis_client.get("websocket_instrument_keys")
            return json.loads(cached) if cached else []
        except Exception as e:
            logger.error(f"Error getting WebSocket keys: {e}")
            return []

    def get_stock_from_instrument_key(self, instrument_key: str) -> Optional[Dict]:
        """Get stock info from instrument key."""
        try:
            cached = self.redis_client.get("reverse_instrument_mapping")
            if cached:
                reverse_mapping = json.loads(cached)
                return reverse_mapping.get(instrument_key)
        except Exception as e:
            logger.error(f"Error getting stock for {instrument_key}: {e}")
        return None

    def get_instrument_details(self, instrument_key: str) -> Optional[Dict]:
        """Get detailed instrument information."""
        try:
            cached = self.redis_client.get("instrument_key_map")
            if cached:
                instrument_map = json.loads(cached)
                return instrument_map.get(instrument_key)
        except Exception as e:
            logger.error(f"Error getting instrument details for {instrument_key}: {e}")
        return None

    def is_valid_instrument(self, instrument_key: str) -> bool:
        """Check if instrument key is valid for trading."""
        try:
            cached = self.redis_client.get("valid_instruments")
            if cached:
                valid_instruments = json.loads(cached)
                return instrument_key in valid_instruments
        except Exception as e:
            logger.error(f"Error checking validity for {instrument_key}: {e}")
        return False


# Global instances for production use
instrument_service = OptimizedInstrumentService()
fast_retrieval = FastInstrumentRetrieval()
