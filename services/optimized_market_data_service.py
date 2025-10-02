"""
Optimized Market Data Service
Pre-populated structured store for ultra-fast analytics

This service maintains a complete instrument database with:
- Static metadata (symbol, name, sector, instrument_key)
- Live calculated fields (change%, volume, value)
- Efficient O(1) updates from live feed
- Fast analytics without looping
"""

import logging
import time
import heapq
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from decimal import Decimal
import json
import asyncio
from dataclasses import dataclass, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class InstrumentData:
    """Complete instrument data structure"""

    # Static metadata (populated once)
    instrument_key: str
    symbol: str
    name: str
    sector: str
    exchange: str
    instrument_type: str
    isin: Optional[str] = None
    lot_size: Optional[int] = None

    # Live price data (updated from feed)
    ltp: float = 0.0
    open_price: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    previous_close: float = 0.0

    # Volume and trading data
    volume: int = 0
    total_traded_value: int = 0  # vtt
    avg_traded_price: float = 0.0  # atp

    # Calculated fields (auto-computed)
    change: float = 0.0
    change_percent: float = 0.0
    value_crores: float = 0.0  # Value (₹ Cr.) = vtt * atp / 1e7

    # Market microstructure
    bid_price: float = 0.0
    ask_price: float = 0.0
    bid_qty: int = 0
    ask_qty: int = 0

    # Timestamps
    last_updated: str = ""
    last_trade_time: str = ""

    # Analytics flags
    is_active: bool = True
    is_fno: bool = False
    has_derivatives: bool = False

    def calculate_derived_fields(self):
        """Calculate change%, value etc. efficiently"""
        if self.previous_close > 0:
            self.change = self.ltp - self.previous_close
            self.change_percent = (self.change / self.previous_close) * 100

        if self.total_traded_value > 0 and self.avg_traded_price > 0:
            self.value_crores = (self.total_traded_value * self.avg_traded_price) / 1e7


class OptimizedMarketDataService:
    """
    Ultra-fast market data service with pre-populated instruments
    """

    def __init__(self):
        # Core data store - O(1) access by instrument_key
        self.instruments: Dict[str, InstrumentData] = {}

        # Add missing attributes for compatibility
        self._live_prices: Dict[str, Dict[str, Any]] = {}  # For backward compatibility
        self._instruments: Dict[str, InstrumentData] = {}  # Alias to self.instruments

        # Fast lookup indices
        self.symbol_to_key: Dict[str, str] = {}
        self.sector_instruments: Dict[str, List[str]] = defaultdict(list)
        self.fno_instruments: List[str] = []
        self.active_instruments: List[str] = []
        self.index_instruments: List[str] = []  # NEW: Separate indices from stocks

        # 🚀 METADATA INTEGRATION: Load once, use everywhere for ultra-fast real-time analytics
        self.enhanced_sector_mapping: Dict[str, Any] = {}
        self.symbol_to_sector_mapping: Dict[str, str] = {}
        self.isin_to_symbol_mapping: Dict[str, str] = {}  # NEW: ISIN → Symbol mapping
        self.isin_to_sector_mapping: Dict[str, str] = {}  # NEW: ISIN → Sector mapping
        self.fno_symbols_set: Set[str] = set()
        self.metadata_loaded = False

        # 🚀 ULTRA-FAST REAL-TIME ANALYTICS ENGINE
        # Binary heaps for O(log n) updates, O(1) top access
        self.analytics_heaps = {
            "gainers": [],  # [(-change_percent, stock_key)] - max heap
            "losers": [],  # [(-abs(change_percent), stock_key)] - max heap for biggest losses
            "volume": [],  # [(-volume, stock_key)] - max heap
            "value": [],  # [(-value_crores, stock_key)] - max heap
            "boosters": [],  # [(-volume_surge, stock_key)] - max heap for volume surge
            "movers": [],  # [(-abs(change_percent), stock_key)] - max heap for biggest movers
        }

        # READY-TO-SEND: Top 20 lists (always maintained, UI-ready)
        self.real_time_lists = {
            "top_gainers": [],  # Always top 20 gainers
            "top_losers": [],  # Always top 20 losers
            "volume_leaders": [],  # Always top 20 by volume
            "value_leaders": [],  # Always top 20 by value
            "intraday_boosters": [],  # Always top 20 by volume surge
            "biggest_movers": [],  # Always top 20 biggest price movers
            "new_highs": [],  # Always top 20 near day high
            "new_lows": [],  # Always top 20 near day low
        }

        # Track which lists need UI updates
        self.lists_needing_update: Set[str] = set()

        # Performance tracking
        self.heap_operations = 0
        self.last_ui_update = 0
        self.ui_update_interval = 0.1  # Send UI updates every 100ms

        # Pre-sorted lists for analytics (LEGACY - keep for backward compatibility)
        self.sorted_by_change: List[str] = []  # instrument_keys sorted by change%
        self.sorted_by_volume: List[str] = []  # instrument_keys sorted by volume
        self.sorted_by_value: List[str] = []  # instrument_keys sorted by value

        # Advance/Decline tracking
        self.advancing_stocks: List[str] = []  # stocks with positive change
        self.declining_stocks: List[str] = []  # stocks with negative change
        self.unchanged_stocks: List[str] = []  # stocks with no change
        self.new_highs: List[str] = []  # stocks at/near day high
        self.new_lows: List[str] = []  # stocks at/near day low

        # Update tracking - OPTIMIZED for real-time
        self.last_sort_update = 0
        self.sort_interval = 0.1  # Update every 100ms for real-time feel
        self.update_count = 0

        # Statistics
        self.stats = {
            "total_instruments": 0,
            "active_instruments": 0,
            "last_update": None,
            "updates_per_second": 0,
            "calculation_time_ms": 0,
        }

        logger.info("🚀 Optimized Market Data Service initialized")

    async def initialize_instruments(self):
        """Initialize all instruments with static metadata"""
        start_time = time.time()

        try:
            # 🚀 STEP 1: Load metadata once for ultra-fast real-time lookups
            await self._load_metadata()

            # Load from existing services
            await self._load_spot_instruments()
            await self._load_fno_instruments()
            await self._load_indices()

            # Build lookup indices
            self._build_indices()

            # 🚀 Initialize real-time analytics heaps
            self._initialize_analytics_heaps()

            initialization_time = (time.time() - start_time) * 1000
            logger.info(
                f"✅ Initialized {len(self.instruments)} instruments in {initialization_time:.2f}ms"
            )
            logger.info(
                f"📊 Metadata loaded: {len(self.symbol_to_sector_mapping)} sectors, {len(self.fno_symbols_set)} F&O stocks"
            )

            # Update stats
            self.stats["total_instruments"] = len(self.instruments)
            self.stats["active_instruments"] = len(self.active_instruments)

        except Exception as e:
            logger.error(f"❌ Error initializing instruments: {e}")

    async def _load_metadata(self):
        """🚀 Load all metadata once for ultra-fast real-time operations"""
        try:
            logger.info("🚀 Loading enhanced sector mapping and F&O metadata...")

            # Load enhanced sector mapping
            with open(
                "config/enhanced_sector_mapping.json", "r", encoding="utf-8"
            ) as f:
                self.enhanced_sector_mapping = json.load(f)

            # Extract symbol to sector mapping for O(1) lookups
            self.symbol_to_sector_mapping = self.enhanced_sector_mapping.get(
                "symbol_to_sector_mapping", {}
            )

            # 🚀 Create ISIN-to-symbol and ISIN-to-sector mappings for spot instruments
            for sector_code, sector_info in self.enhanced_sector_mapping.get(
                "sectors", {}
            ).items():
                for stock in sector_info.get("stocks", []):
                    symbol = stock.get("symbol")
                    isin = stock.get("isin")
                    if symbol and isin:
                        self.isin_to_symbol_mapping[isin] = symbol
                        self.isin_to_sector_mapping[isin] = sector_info.get(
                            "display_name", sector_code
                        )

            # Load F&O stock list
            try:
                with open("data/fno_stock_list.json", "r", encoding="utf-8") as f:
                    fno_data = json.load(f)

                # Extract F&O symbols into a set for O(1) lookups
                for security in fno_data.get("securities", []):
                    symbol = security.get("symbol")
                    if symbol:
                        self.fno_symbols_set.add(symbol.upper())

            except FileNotFoundError:
                logger.warning(
                    "F&O stock list not found, using enhanced sector mapping F&O data"
                )
                # Use enhanced sector mapping as fallback for F&O classification
                for sector_info in self.enhanced_sector_mapping.get(
                    "sectors", {}
                ).values():
                    for stock in sector_info.get("stocks", []):
                        symbol = stock.get("symbol")
                        if symbol and stock.get(
                            "lot_size"
                        ):  # If lot_size exists, it's F&O
                            self.fno_symbols_set.add(symbol.upper())

            self.metadata_loaded = True
            logger.info(
                f"✅ Metadata loaded: {len(self.symbol_to_sector_mapping)} symbol sectors, {len(self.isin_to_sector_mapping)} ISIN sectors, {len(self.fno_symbols_set)} F&O stocks"
            )

        except Exception as e:
            logger.error(f"❌ Error loading metadata: {e}")
            self.metadata_loaded = False

    async def _load_spot_instruments(self):
        """Load spot instruments from existing service"""
        try:
            from services.instrument_refresh_service import get_spot_only_instruments

            spot_instruments = get_spot_only_instruments()
            logger.info(f"📊 Loading {len(spot_instruments)} spot instruments")

            for instr in spot_instruments:
                try:
                    # 🚀 Use preloaded metadata for ultra-fast real-time operations
                    symbol = instr[
                        "symbol"
                    ].upper()  # This is actually ISIN for spot instruments
                    sector = self._get_sector_from_metadata(symbol)

                    # Check if F&O by both ISIN and actual symbol
                    actual_symbol = self.isin_to_symbol_mapping.get(symbol, symbol)
                    is_fno = (
                        actual_symbol in self.fno_symbols_set
                        or symbol in self.fno_symbols_set
                    )

                    instrument_data = InstrumentData(
                        instrument_key=instr["instrument_key"],
                        symbol=instr["symbol"],
                        name=instr.get("name", instr["symbol"]),
                        sector=sector,
                        exchange=instr.get("exchange", "NSE"),
                        instrument_type=instr.get("instrument_type", "EQ"),
                        isin=instr.get("isin"),
                        is_active=True,
                        is_fno=is_fno,
                        has_derivatives=is_fno,
                    )

                    self.instruments[instrument_data.instrument_key] = instrument_data
                    self.active_instruments.append(instrument_data.instrument_key)

                except Exception as e:
                    logger.debug(f"Error processing spot instrument: {e}")

        except Exception as e:
            logger.warning(f"Could not load spot instruments: {e}")

    async def _load_fno_instruments(self):
        """🚀 Load F&O instruments using preloaded metadata - ultra-fast operation"""
        try:
            if not self.metadata_loaded:
                logger.warning("Metadata not loaded, skipping F&O instruments")
                return

            fno_count = 0
            # Use preloaded enhanced sector mapping for ultra-fast processing
            for sector_info in self.enhanced_sector_mapping.get("sectors", {}).values():
                for stock in sector_info.get("stocks", []):
                    try:
                        # Create instrument key for F&O stock
                        symbol = stock.get("symbol")
                        isin = stock.get("isin")

                        if not symbol or not isin:
                            continue

                        instrument_key = f"NSE_EQ|{isin}"

                        if instrument_key in self.instruments:
                            # Update existing instrument with F&O metadata (already marked during initialization)
                            self.instruments[instrument_key].lot_size = stock.get(
                                "lot_size"
                            )
                            self.fno_instruments.append(instrument_key)
                            fno_count += 1

                    except Exception as e:
                        logger.debug(f"Error processing F&O instrument: {e}")

            logger.info(f"📊 Loaded {fno_count} F&O instruments with lot sizes")

        except Exception as e:
            logger.warning(f"Could not load F&O instruments: {e}")

    async def _load_indices(self):
        """
        Load market indices - matches _load_index_keys from instrument_refresh_service
        Consistent key format across all services
        """
        indices = [
            # Core Indices (Highest Priority)
            {"key": "NSE_INDEX|Nifty 50", "symbol": "NIFTY", "name": "Nifty 50"},
            {
                "key": "NSE_INDEX|Nifty Bank",
                "symbol": "BANKNIFTY",
                "name": "Nifty Bank",
            },
            {
                "key": "NSE_INDEX|Fin Nifty",
                "symbol": "FINNIFTY",
                "name": "Nifty Financial Services",
            },
            {"key": "BSE_INDEX|SENSEX", "symbol": "SENSEX", "name": "BSE Sensex"},
            # Major Sectoral Indices
            {
                "key": "NSE_INDEX|Nifty Auto",
                "symbol": "Nifty Auto",
                "name": "Nifty Auto",
            },
            {"key": "NSE_INDEX|Nifty IT", "symbol": "CNXIT", "name": "Nifty IT"},
            {
                "key": "NSE_INDEX|Nifty Pharma",
                "symbol": "CNXPHARMA",
                "name": "Nifty Pharma",
            },
            {"key": "NSE_INDEX|Nifty FMCG", "symbol": "CNXFMCG", "name": "Nifty FMCG"},
            {
                "key": "NSE_INDEX|Nifty Metal",
                "symbol": "CNXMETAL",
                "name": "Nifty Metal",
            },
            {
                "key": "NSE_INDEX|Nifty Realty",
                "symbol": "CNXREALTY",
                "name": "Nifty Realty",
            },
            {
                "key": "NSE_INDEX|Nifty Media",
                "symbol": "CNXMEDIA",
                "name": "Nifty Media",
            },
            {
                "key": "NSE_INDEX|Nifty PSU Bank",
                "symbol": "CNXPSUBANK",
                "name": "Nifty PSU Bank",
            },
            {
                "key": "NSE_INDEX|Nifty Private Bank",
                "symbol": "NIFTYPVTBANK",
                "name": "Nifty Private Bank",
            },
            {
                "key": "NSE_INDEX|NIFTY OIL AND GAS",
                "symbol": "CNXOILGAS",
                "name": "Nifty Oil and Gas",
            },
            {
                "key": "NSE_INDEX|Nifty Consumer Durables",
                "symbol": "CNXCONSUMER",
                "name": "Nifty Consumer Durables",
            },
            {
                "key": "NSE_INDEX|Nifty Healthcare Index",
                "symbol": "CNXHEALTHCARE",
                "name": "Nifty Healthcare Index",
            },
        ]

        for index in indices:
            try:
                # Determine exchange from key (BSE or NSE)
                exchange = "BSE" if index["key"].startswith("BSE_") else "NSE"

                instrument_data = InstrumentData(
                    instrument_key=index["key"],
                    symbol=index["symbol"],
                    name=index["name"],
                    sector="INDEX",
                    exchange=exchange,
                    instrument_type="INDEX",
                    is_active=True,
                )

                self.instruments[instrument_data.instrument_key] = instrument_data
                self.active_instruments.append(instrument_data.instrument_key)
                self.index_instruments.append(instrument_data.instrument_key)

            except Exception as e:
                logger.debug(f"Error loading index {index}: {e}")

        logger.info(
            f"📊 Loaded {len(self.index_instruments)} market indices (16 total including sectoral indices)"
        )

    def _get_sector_from_metadata(self, symbol: str) -> str:
        """🚀 Ultra-fast sector lookup using preloaded metadata - O(1) operation"""
        if not self.metadata_loaded:
            return "OTHER"

        try:
            symbol_upper = symbol.upper()

            # Try direct symbol lookup first
            sector_code = self.symbol_to_sector_mapping.get(symbol_upper)
            if sector_code:
                sectors = self.enhanced_sector_mapping.get("sectors", {})
                sector_info = sectors.get(sector_code, {})
                return sector_info.get("display_name", sector_code)

            # 🚀 NEW: Try ISIN lookup (for spot instruments)
            sector_name = self.isin_to_sector_mapping.get(symbol_upper)
            if sector_name:
                return sector_name

            return "OTHER"

        except Exception:
            return "OTHER"

    def _get_sector_for_symbol(self, symbol: str) -> str:
        """Legacy method - kept for backward compatibility"""
        return self._get_sector_from_metadata(symbol)

    def _build_indices(self):
        """Build fast lookup indices"""
        self.symbol_to_key.clear()
        self.sector_instruments.clear()

        for key, instrument in self.instruments.items():
            # Symbol lookup
            self.symbol_to_key[instrument.symbol] = key

            # Sector grouping
            self.sector_instruments[instrument.sector].append(key)

    def _initialize_analytics_heaps(self):
        """🚀 Initialize all analytics heaps with predefined stocks"""
        start_time = time.perf_counter()

        try:
            logger.info("🚀 Initializing real-time analytics heaps...")

            # Initialize all heaps with current instrument data
            for instrument_key, instrument in self.instruments.items():
                # Skip indices for stock analytics
                if instrument.instrument_type == "INDEX":
                    continue

                # Add to all heaps with current values (or 0 if no data yet)
                change_percent = instrument.change_percent
                volume = instrument.volume
                value_crores = instrument.value_crores

                # Gainers heap (positive change only)
                if change_percent > 0:
                    heapq.heappush(
                        self.analytics_heaps["gainers"],
                        (-change_percent, instrument_key),
                    )

                # Losers heap (negative change only, by magnitude)
                if change_percent < 0:
                    heapq.heappush(
                        self.analytics_heaps["losers"],
                        (-abs(change_percent), instrument_key),
                    )

                # Volume heap (all stocks)
                heapq.heappush(
                    self.analytics_heaps["volume"], (-volume, instrument_key)
                )

                # Value heap (all stocks)
                heapq.heappush(
                    self.analytics_heaps["value"], (-value_crores, instrument_key)
                )

                # Movers heap (all stocks with any change)
                if change_percent != 0:
                    heapq.heappush(
                        self.analytics_heaps["movers"],
                        (-abs(change_percent), instrument_key),
                    )

            # Build initial top 20 lists
            self._rebuild_all_top_lists()

            init_time = (time.perf_counter() - start_time) * 1000
            logger.info(f"✅ Analytics heaps initialized in {init_time:.2f}ms")
            logger.info(
                f"📊 Ready for real-time processing of {len(self.instruments)} instruments"
            )

        except Exception as e:
            logger.error(f"❌ Error initializing analytics heaps: {e}")

    def _rebuild_all_top_lists(self):
        """Rebuild all top 20 lists from heaps"""
        try:
            # Rebuild each list
            self._rebuild_top_list("gainers", "top_gainers")
            self._rebuild_top_list("losers", "top_losers")
            self._rebuild_top_list("volume", "volume_leaders")
            self._rebuild_top_list("value", "value_leaders")
            self._rebuild_top_list("movers", "biggest_movers")

            # Special lists
            self._rebuild_new_highs_lows()

        except Exception as e:
            logger.error(f"❌ Error rebuilding top lists: {e}")

    def _rebuild_top_list(self, heap_name: str, list_name: str):
        """Rebuild top 20 list from heap - O(20)"""
        try:
            heap = self.analytics_heaps[heap_name]
            top_20 = []
            seen = set()
            temp_heap = []

            # Extract top 20 unique stocks
            while heap and len(top_20) < 20:
                value, stock_key = heapq.heappop(heap)
                temp_heap.append((value, stock_key))

                if stock_key not in seen and stock_key in self.instruments:
                    seen.add(stock_key)
                    instrument = self.instruments[stock_key]

                    # Skip if no meaningful data
                    actual_value = -value
                    if heap_name in ["volume", "value"] and actual_value <= 0:
                        continue
                    if heap_name in ["gainers", "losers"] and actual_value == 0:
                        continue

                    position = len(top_20) + 1
                    top_20.append(
                        {
                            "position": position,
                            "symbol": instrument.symbol,
                            "name": instrument.name,
                            "key": stock_key,
                            "value": actual_value,
                            "ltp": instrument.ltp,
                            "change_percent": instrument.change_percent,
                            "volume": instrument.volume,
                            "value_crores": instrument.value_crores,
                            "sector": instrument.sector,
                        }
                    )

            # Restore heap
            for item in temp_heap:
                heapq.heappush(heap, item)

            # Update list
            self.real_time_lists[list_name] = top_20

        except Exception as e:
            logger.error(f"❌ Error rebuilding {list_name}: {e}")

    def _rebuild_new_highs_lows(self):
        """Rebuild new highs and lows lists"""
        try:
            new_highs = []
            new_lows = []

            for instrument_key, instrument in self.instruments.items():
                if instrument.instrument_type == "INDEX" or instrument.ltp <= 0:
                    continue

                # Near day high (within 0.5%)
                if instrument.high > 0 and (instrument.ltp / instrument.high) >= 0.995:
                    new_highs.append(
                        {
                            "symbol": instrument.symbol,
                            "key": instrument_key,
                            "ltp": instrument.ltp,
                            "high": instrument.high,
                            "proximity": (instrument.ltp / instrument.high) * 100,
                            "change_percent": instrument.change_percent,
                        }
                    )

                # Near day low (within 0.5%)
                if instrument.low > 0 and (instrument.ltp / instrument.low) <= 1.005:
                    new_lows.append(
                        {
                            "symbol": instrument.symbol,
                            "key": instrument_key,
                            "ltp": instrument.ltp,
                            "low": instrument.low,
                            "proximity": (instrument.ltp / instrument.low) * 100,
                            "change_percent": instrument.change_percent,
                        }
                    )

            # Sort and limit to top 20
            new_highs.sort(key=lambda x: x["proximity"], reverse=True)
            new_lows.sort(key=lambda x: x["proximity"])

            self.real_time_lists["new_highs"] = new_highs[:20]
            self.real_time_lists["new_lows"] = new_lows[:20]

        except Exception as e:
            logger.error(f"❌ Error rebuilding new highs/lows: {e}")

    def update_live_data(
        self, live_feed_data: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        🚀 ULTRA-FAST: Real-time update with instant analytics refresh
        Only updates instruments that exist in our store

        Returns:
            Dict[str, Dict[str, Any]]: Updated instrument data for WebSocket broadcasting
        """
        start_time = time.perf_counter()
        updated_count = 0
        analytics_updates_needed = set()
        updated_instruments = set()  # Track instruments with updated prices

        try:
            for instrument_key, feed_data in live_feed_data.items():
                if instrument_key in self.instruments:
                    instrument = self.instruments[instrument_key]

                    # Store old values for analytics comparison
                    old_change_percent = instrument.change_percent
                    old_volume = instrument.volume
                    old_value_crores = instrument.value_crores

                    # Update live data fields
                    if "ltp" in feed_data:
                        instrument.ltp = float(feed_data["ltp"])
                    if "high" in feed_data:
                        instrument.high = float(feed_data["high"])
                    if "low" in feed_data:
                        instrument.low = float(feed_data["low"])
                    if "open" in feed_data:
                        instrument.open_price = float(feed_data["open"])
                    if "cp" in feed_data:
                        instrument.previous_close = float(feed_data["cp"])
                    if "volume" in feed_data:
                        instrument.volume = int(feed_data["volume"])
                    if "vtt" in feed_data:
                        instrument.total_traded_value = int(feed_data["vtt"])
                    if "atp" in feed_data:
                        instrument.avg_traded_price = float(feed_data["atp"])

                    # Calculate derived fields
                    instrument.calculate_derived_fields()
                    instrument.last_updated = datetime.now().isoformat()

                    # Track this instrument as updated for price broadcasting
                    updated_instruments.add(instrument_key)

                    # 🚀 REAL-TIME ANALYTICS: Update heaps if values changed
                    if instrument.instrument_type != "INDEX":  # Skip indices
                        if old_change_percent != instrument.change_percent:
                            self._update_analytics_heaps_for_change(
                                instrument_key,
                                old_change_percent,
                                instrument.change_percent,
                            )
                            analytics_updates_needed.update(
                                ["gainers", "losers", "movers"]
                            )

                        if old_volume != instrument.volume:
                            self._update_analytics_heaps_for_volume(
                                instrument_key, old_volume, instrument.volume
                            )
                            analytics_updates_needed.add("volume")

                        if old_value_crores != instrument.value_crores:
                            self._update_analytics_heaps_for_value(
                                instrument_key,
                                old_value_crores,
                                instrument.value_crores,
                            )
                            analytics_updates_needed.add("value")

                    updated_count += 1

            # 🚀 REBUILD CHANGED ANALYTICS LISTS (only what changed)
            if analytics_updates_needed:
                for update_type in analytics_updates_needed:
                    if update_type == "gainers":
                        self._rebuild_top_list("gainers", "top_gainers")
                    elif update_type == "losers":
                        self._rebuild_top_list("losers", "top_losers")
                    elif update_type == "volume":
                        self._rebuild_top_list("volume", "volume_leaders")
                    elif update_type == "value":
                        self._rebuild_top_list("value", "value_leaders")
                    elif update_type == "movers":
                        self._rebuild_top_list("movers", "biggest_movers")

                # Always update new highs/lows if any price changed
                if any(
                    x in analytics_updates_needed
                    for x in ["gainers", "losers", "movers"]
                ):
                    self._rebuild_new_highs_lows()

                # Mark for UI update
                self.lists_needing_update.update(analytics_updates_needed)

            # 🚀 SEND UI UPDATES (if interval reached)
            current_time = time.time()

            # Always broadcast individual price updates immediately for all updated instruments
            if updated_instruments:
                self._broadcast_live_price_updates(updated_instruments)

            # Broadcast analytics updates if interval reached
            if (
                current_time - self.last_ui_update > self.ui_update_interval
                and self.lists_needing_update
            ):
                self._broadcast_analytics_updates()
                self.lists_needing_update.clear()
                self.last_ui_update = current_time

            # Update legacy sorting if needed (for backward compatibility)
            if current_time - self.last_sort_update > self.sort_interval:
                self._update_sorted_lists()
                self.last_sort_update = current_time

            # Update statistics
            self.update_count += 1
            calculation_time = (time.perf_counter() - start_time) * 1000
            self.stats["calculation_time_ms"] = calculation_time
            self.stats["last_update"] = datetime.now().isoformat()
            self.heap_operations += len(analytics_updates_needed)

            if updated_count > 0:
                logger.debug(
                    f"⚡ Updated {updated_count} instruments, {len(analytics_updates_needed)} analytics in {calculation_time:.2f}ms"
                )

            # 🚀 NEW: Return updated instruments data for unified WebSocket manager
            price_changes = {}
            for instrument_key in updated_instruments:
                if instrument_key in self.instruments:
                    instrument = self.instruments[instrument_key]
                    price_changes[instrument_key] = {
                        "symbol": instrument.symbol,
                        "name": instrument.name,
                        "ltp": instrument.ltp,
                        "change_percent": instrument.change_percent,
                        "volume": instrument.volume,
                        "instrument_key": instrument_key,
                        "sector": instrument.sector,
                        "last_updated": datetime.now().isoformat(),
                    }

            return price_changes

        except Exception as e:
            logger.error(f"❌ Error updating live data: {e}")
            return {}

    def _update_analytics_heaps_for_change(
        self, stock_key: str, old_change: float, new_change: float
    ):
        """Update gainers/losers/movers heaps for price change"""
        try:
            # Add new values to heaps (lazy cleanup approach)
            if new_change > 0:
                heapq.heappush(
                    self.analytics_heaps["gainers"], (-new_change, stock_key)
                )
            if new_change < 0:
                heapq.heappush(
                    self.analytics_heaps["losers"], (-abs(new_change), stock_key)
                )
            if new_change != 0:
                heapq.heappush(
                    self.analytics_heaps["movers"], (-abs(new_change), stock_key)
                )

        except Exception as e:
            logger.error(f"❌ Error updating change heaps: {e}")

    def _update_analytics_heaps_for_volume(
        self, stock_key: str, old_volume: int, new_volume: int
    ):
        """Update volume heap"""
        try:
            heapq.heappush(self.analytics_heaps["volume"], (-new_volume, stock_key))
        except Exception as e:
            logger.error(f"❌ Error updating volume heap: {e}")

    def _update_analytics_heaps_for_value(
        self, stock_key: str, old_value: float, new_value: float
    ):
        """Update value heap"""
        try:
            heapq.heappush(self.analytics_heaps["value"], (-new_value, stock_key))
        except Exception as e:
            logger.error(f"❌ Error updating value heap: {e}")

    def _broadcast_analytics_updates(self):
        """Broadcast real-time analytics updates to UI"""
        try:
            # Prepare UI update with only changed lists
            analytics_update = {
                "type": "real_time_analytics",
                "timestamp": datetime.now().isoformat(),
                "lists": {},
            }

            # Add changed lists
            if "gainers" in self.lists_needing_update:
                analytics_update["lists"]["top_gainers"] = self.real_time_lists[
                    "top_gainers"
                ]
            if "losers" in self.lists_needing_update:
                analytics_update["lists"]["top_losers"] = self.real_time_lists[
                    "top_losers"
                ]
            if "volume" in self.lists_needing_update:
                analytics_update["lists"]["volume_leaders"] = self.real_time_lists[
                    "volume_leaders"
                ]
            if "value" in self.lists_needing_update:
                analytics_update["lists"]["value_leaders"] = self.real_time_lists[
                    "value_leaders"
                ]
            if "movers" in self.lists_needing_update:
                analytics_update["lists"]["biggest_movers"] = self.real_time_lists[
                    "biggest_movers"
                ]

            # Always include new highs/lows if any price changed
            if any(
                x in self.lists_needing_update for x in ["gainers", "losers", "movers"]
            ):
                analytics_update["lists"]["new_highs"] = self.real_time_lists[
                    "new_highs"
                ]
                analytics_update["lists"]["new_lows"] = self.real_time_lists["new_lows"]

            # Broadcast via unified WebSocket manager
            try:
                from services.unified_websocket_manager import (
                    emit_real_time_analytics_update,
                )

                emit_real_time_analytics_update(analytics_update)
            except ImportError:
                logger.debug("Unified WebSocket manager not available for broadcasting")

        except Exception as e:
            logger.error(f"❌ Error broadcasting analytics updates: {e}")

    def _broadcast_live_price_updates(self, updated_instruments: Set[str]):
        """Broadcast individual live price updates for changed instruments"""
        try:
            if not updated_instruments:
                return

            # Get live prices for only the updated instruments
            live_prices = {}
            for instrument_key in updated_instruments:
                if instrument_key in self.instruments:
                    instrument = self.instruments[instrument_key]
                    if instrument.ltp > 0:
                        live_prices[instrument_key] = {
                            "symbol": instrument.symbol,
                            "name": instrument.name,
                            "instrument_key": instrument_key,
                            "ltp": instrument.ltp,
                            "last_price": instrument.ltp,
                            "change": instrument.change,
                            "change_percent": instrument.change_percent,
                            "volume": instrument.volume,
                            "high": instrument.high,
                            "low": instrument.low,
                            "open": getattr(instrument, "open", instrument.open_price),
                            "close": getattr(
                                instrument, "close", instrument.previous_close
                            ),
                            "sector": instrument.sector,
                            "instrument_type": instrument.instrument_type,
                            "exchange": instrument.exchange,
                            "timestamp": datetime.now().isoformat(),
                        }

            if live_prices:
                # 🚀 ENABLED: Send price_update events for UI compatibility
                try:
                    from services.unified_websocket_manager import unified_manager

                    unified_manager.emit_event("price_update", live_prices, priority=1)
                    logger.debug(
                        f"🚀 Broadcasted live prices for {len(live_prices)} instruments"
                    )
                except ImportError:
                    logger.debug(
                        "Unified WebSocket manager not available for price broadcasting"
                    )

        except Exception as e:
            logger.error(f"❌ Error broadcasting live price updates: {e}")

    def _update_sorted_lists(self):
        """Update pre-sorted lists for fast analytics with proper separation of indices and stocks"""
        try:
            # 🚀 CRITICAL FIX: Separate indices from stocks for proper sorting
            stock_keys = []
            index_keys = []

            for key in self.active_instruments:
                if self.instruments[key].ltp > 0:
                    if self.instruments[key].instrument_type == "INDEX":
                        index_keys.append(key)
                    else:
                        stock_keys.append(key)

            # Sort stocks only (exclude indices from stock analytics)
            self.sorted_by_change = sorted(
                stock_keys,  # Only stocks, not indices
                key=lambda k: self.instruments[k].change_percent,
                reverse=True,  # Highest change% first (gainers at top)
            )

            self.sorted_by_volume = sorted(
                stock_keys,  # Only stocks, not indices
                key=lambda k: self.instruments[k].volume,
                reverse=True,  # Highest volume first
            )

            self.sorted_by_value = sorted(
                stock_keys,  # Only stocks, not indices
                key=lambda k: self.instruments[k].value_crores,
                reverse=True,  # Highest value first
            )

            # Update advance/decline lists (stocks only)
            self._update_advance_decline_lists(stock_keys)

            logger.debug(
                f"⚡ Updated sorted lists: {len(stock_keys)} stocks, {len(index_keys)} indices"
            )

        except Exception as e:
            logger.error(f"❌ Error updating sorted lists: {e}")

    def _update_advance_decline_lists(self, active_keys: List[str]):
        """Update advance/decline tracking lists"""
        try:
            self.advancing_stocks.clear()
            self.declining_stocks.clear()
            self.unchanged_stocks.clear()
            self.new_highs.clear()
            self.new_lows.clear()

            for key in active_keys:
                instrument = self.instruments[key]

                # Advance/Decline classification
                if instrument.change_percent > 0:
                    self.advancing_stocks.append(key)
                elif instrument.change_percent < 0:
                    self.declining_stocks.append(key)
                else:
                    self.unchanged_stocks.append(key)

                # New highs/lows detection (within 1% of day high/low)
                if instrument.ltp > 0 and instrument.high > 0:
                    # Near day high (within 0.5%)
                    if (instrument.ltp / instrument.high) >= 0.995:
                        self.new_highs.append(key)

                    # Near day low (within 0.5%)
                    if (
                        instrument.low > 0
                        and (instrument.ltp / instrument.low) <= 1.005
                    ):
                        self.new_lows.append(key)

            # 🚀 CRITICAL: Sort advance/decline lists with consistent order
            # Advancing stocks: Highest change% first (best gainers at top)
            self.advancing_stocks.sort(
                key=lambda k: self.instruments[k].change_percent, reverse=True
            )
            # Declining stocks: Worst declines first (biggest losers at top)
            self.declining_stocks.sort(key=lambda k: self.instruments[k].change_percent)

            # Sort new highs/lows by their proximity to highs/lows
            self.new_highs.sort(
                key=lambda k: (
                    self.instruments[k].ltp / self.instruments[k].high
                    if self.instruments[k].high > 0
                    else 0
                ),
                reverse=True,
            )
            self.new_lows.sort(
                key=lambda k: (
                    self.instruments[k].ltp / self.instruments[k].low
                    if self.instruments[k].low > 0
                    else 0
                )
            )

        except Exception as e:
            logger.error(f"❌ Error updating advance/decline lists: {e}")

    # Fast Analytics Methods

    def get_top_gainers(self, limit: int = 20) -> List[Dict[str, Any]]:
        """🚀 REAL-TIME: Get top gainers - O(1) from pre-maintained list"""
        try:
            # Return real-time list (always top 20, instantly updated)
            return self.real_time_lists["top_gainers"][:limit]
        except Exception as e:
            logger.error(f"Error getting real-time top gainers: {e}")
            # Fallback to legacy method
            try:
                gainer_keys = [
                    k
                    for k in self.sorted_by_change[: limit * 2]
                    if self.instruments[k].change_percent > 0
                ][:limit]
                return [asdict(self.instruments[key]) for key in gainer_keys]
            except Exception as fallback_error:
                logger.error(f"Fallback method also failed: {fallback_error}")
                return []

    def get_top_losers(self, limit: int = 20) -> List[Dict[str, Any]]:
        """🚀 REAL-TIME: Get top losers - O(1) from pre-maintained list"""
        try:
            # Return real-time list (always top 20, instantly updated)
            return self.real_time_lists["top_losers"][:limit]
        except Exception as e:
            logger.error(f"Error getting real-time top losers: {e}")
            # Fallback to legacy method
            try:
                loser_keys = [
                    k
                    for k in reversed(self.sorted_by_change[-limit * 2 :])
                    if self.instruments[k].change_percent < 0
                ][:limit]
                return [asdict(self.instruments[key]) for key in loser_keys]
            except Exception as fallback_error:
                logger.error(f"Fallback method also failed: {fallback_error}")
                return []

    def get_volume_leaders(self, limit: int = 20) -> List[Dict[str, Any]]:
        """🚀 REAL-TIME: Get volume leaders - O(1) from pre-maintained list"""
        try:
            return self.real_time_lists["volume_leaders"][:limit]
        except Exception as e:
            logger.error(f"Error getting real-time volume leaders: {e}")
            # Fallback to legacy method
            try:
                return [
                    asdict(self.instruments[key])
                    for key in self.sorted_by_volume[:limit]
                ]
            except Exception as fallback_error:
                logger.error(f"Fallback method also failed: {fallback_error}")
                return []

    def get_value_leaders(self, limit: int = 20) -> List[Dict[str, Any]]:
        """🚀 REAL-TIME: Get value leaders - O(1) from pre-maintained list"""
        try:
            return self.real_time_lists["value_leaders"][:limit]
        except Exception as e:
            logger.error(f"Error getting real-time value leaders: {e}")
            # Fallback to legacy method
            try:
                return [
                    asdict(self.instruments[key])
                    for key in self.sorted_by_value[:limit]
                ]
            except Exception as fallback_error:
                logger.error(f"Fallback method also failed: {fallback_error}")
                return []

    # 🚀 NEW REAL-TIME ANALYTICS METHODS

    def get_biggest_movers(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get biggest price movers (positive or negative) - Real-time"""
        try:
            return self.real_time_lists["biggest_movers"][:limit]
        except Exception as e:
            logger.error(f"Error getting biggest movers: {e}")
            return []

    def get_new_highs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get stocks near day high - Real-time"""
        try:
            return self.real_time_lists["new_highs"][:limit]
        except Exception as e:
            logger.error(f"Error getting new highs: {e}")
            return []

    def get_new_lows(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get stocks near day low - Real-time"""
        try:
            return self.real_time_lists["new_lows"][:limit]
        except Exception as e:
            logger.error(f"Error getting new lows: {e}")
            return []

    def get_intraday_boosters(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get stocks with highest volume surge - Real-time"""
        try:
            return self.real_time_lists["intraday_boosters"][:limit]
        except Exception as e:
            logger.error(f"Error getting intraday boosters: {e}")
            return []

    def get_all_real_time_analytics(self) -> Dict[str, Any]:
        """Get all real-time analytics in one call - Ultra-fast"""
        try:
            return {
                "top_gainers": self.real_time_lists["top_gainers"],
                "top_losers": self.real_time_lists["top_losers"],
                "volume_leaders": self.real_time_lists["volume_leaders"],
                "value_leaders": self.real_time_lists["value_leaders"],
                "biggest_movers": self.real_time_lists["biggest_movers"],
                "new_highs": self.real_time_lists["new_highs"],
                "new_lows": self.real_time_lists["new_lows"],
                "intraday_boosters": self.real_time_lists["intraday_boosters"],
                "timestamp": datetime.now().isoformat(),
                "total_operations": self.heap_operations,
                "update_count": self.update_count,
            }
        except Exception as e:
            logger.error(f"Error getting all real-time analytics: {e}")
            return {}

    def get_sector_performance(self) -> Dict[str, Any]:
        """Get sector-wise performance - O(sectors) not O(stocks)"""
        try:
            sector_stats = {}

            for sector, instrument_keys in self.sector_instruments.items():
                if not instrument_keys:
                    continue

                sector_instruments = [
                    self.instruments[key]
                    for key in instrument_keys
                    if self.instruments[key].ltp > 0
                ]

                if not sector_instruments:
                    continue

                total_change = sum(inst.change_percent for inst in sector_instruments)
                advancing = len(
                    [inst for inst in sector_instruments if inst.change_percent > 0]
                )
                declining = len(
                    [inst for inst in sector_instruments if inst.change_percent < 0]
                )

                sector_stats[sector] = {
                    "avg_change_percent": total_change / len(sector_instruments),
                    "advancing": advancing,
                    "declining": declining,
                    "total_stocks": len(sector_instruments),
                    "strength_score": (
                        (advancing - declining) / len(sector_instruments)
                    )
                    * 100,
                }

            return sector_stats

        except Exception as e:
            logger.error(f"Error calculating sector performance: {e}")
            return {}

    def get_market_summary(self) -> Dict[str, Any]:
        """Get market summary - O(1) from pre-calculated data"""
        try:
            active_instruments = [
                inst
                for inst in self.instruments.values()
                if inst.is_active and inst.ltp > 0
            ]

            if not active_instruments:
                return {"error": "No active instruments"}

            advancing = len(
                [inst for inst in active_instruments if inst.change_percent > 0]
            )
            declining = len(
                [inst for inst in active_instruments if inst.change_percent < 0]
            )
            unchanged = len(active_instruments) - advancing - declining

            total_volume = sum(inst.volume for inst in active_instruments)
            total_value = sum(inst.value_crores for inst in active_instruments)

            return {
                "total_stocks": len(active_instruments),
                "advancing": advancing,
                "declining": declining,
                "unchanged": unchanged,
                "advance_decline_ratio": (
                    advancing / declining if declining > 0 else float("inf")
                ),
                "market_breadth_percent": (
                    (advancing - declining) / len(active_instruments)
                )
                * 100,
                "total_volume": total_volume,
                "total_value_crores": total_value,
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error calculating market summary: {e}")
            return {"error": str(e)}

    def get_fno_stocks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get F&O stocks for trading - O(fno_count) not O(all_stocks)"""
        try:
            fno_data = []
            for key in self.fno_instruments:
                if key in self.instruments:
                    instrument = self.instruments[key]
                    if instrument.ltp > 0:
                        fno_data.append(asdict(instrument))

            # Sort by volume for trading relevance
            fno_data.sort(key=lambda x: x["volume"], reverse=True)
            return fno_data[:limit]

        except Exception as e:
            logger.error(f"Error getting F&O stocks: {e}")
            return []

    def get_indices_data(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get indices data separately - O(1) from pre-tracked indices"""
        try:
            indices_data = []
            for key in self.index_instruments:
                if key in self.instruments and self.instruments[key].ltp > 0:
                    indices_data.append(asdict(self.instruments[key]))

            # Sort indices by change percentage (consistent with stocks)
            indices_data.sort(key=lambda x: x["change_percent"], reverse=True)
            return indices_data[:limit]

        except Exception as e:
            logger.error(f"Error getting indices data: {e}")
            return []

    def get_instrument_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get instrument by symbol - O(1) lookup"""
        key = self.symbol_to_key.get(symbol.upper())
        if key and key in self.instruments:
            return asdict(self.instruments[key])
        return None

    def get_all_live_prices(self) -> Dict[str, Dict[str, Any]]:
        """Get all live prices for ALL instruments - for broadcasting to UI"""
        try:
            live_prices = {}
            for key, instrument in self.instruments.items():
                if instrument.ltp > 0:  # Only include instruments with valid prices
                    live_prices[key] = {
                        "symbol": instrument.symbol,
                        "name": instrument.name,
                        "instrument_key": key,
                        "ltp": instrument.ltp,
                        "last_price": instrument.ltp,
                        "change": instrument.change,
                        "change_percent": instrument.change_percent,
                        "volume": instrument.volume,
                        "high": instrument.high,
                        "low": instrument.low,
                        "open": getattr(instrument, "open_price", 0),
                        "close": getattr(instrument, "previous_close", 0),
                        "sector": instrument.sector,
                        "instrument_type": instrument.instrument_type,
                        "exchange": instrument.exchange,
                        "timestamp": datetime.now().isoformat(),
                        "last_updated": datetime.now().timestamp() * 1000,
                    }
            return live_prices
        except Exception as e:
            logger.error(f"Error getting all live prices: {e}")
            return {}

    def get_updated_instruments(
        self, since_timestamp: float = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get instruments that have been updated since a specific timestamp - for efficient updates"""
        try:
            if since_timestamp is None:
                # Return all instruments if no timestamp provided
                return self.get_all_live_prices()

            updated_prices = {}
            for key, instrument in self.instruments.items():
                # Check if instrument was updated recently (within last few seconds)
                if instrument.ltp > 0 and hasattr(instrument, "last_updated"):
                    if (
                        instrument.last_updated
                        and instrument.last_updated > since_timestamp
                    ):
                        updated_prices[key] = {
                            "symbol": instrument.symbol,
                            "name": instrument.name,
                            "instrument_key": key,
                            "ltp": instrument.ltp,
                            "last_price": instrument.ltp,
                            "change": instrument.change,
                            "change_percent": instrument.change_percent,
                            "volume": instrument.volume,
                            "high": instrument.high,
                            "low": instrument.low,
                            "open": getattr(instrument, "open", instrument.open_price),
                            "close": getattr(
                                instrument, "close", instrument.previous_close
                            ),
                            "sector": instrument.sector,
                            "instrument_type": instrument.instrument_type,
                            "exchange": instrument.exchange,
                            "timestamp": datetime.now().isoformat(),
                            "last_updated": instrument.last_updated,
                        }
            return updated_prices
        except Exception as e:
            logger.error(f"Error getting updated instruments: {e}")
            return {}

    def get_sector_stocks(self, sector: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get stocks grouped by sector - O(sectors) not O(stocks) with consistent sorting"""
        try:
            if sector:
                # Get specific sector
                sector = sector.upper()
                if sector in self.sector_instruments:
                    instrument_keys = self.sector_instruments[sector]
                    stocks = [
                        asdict(self.instruments[key])
                        for key in instrument_keys
                        if key in self.instruments
                        and self.instruments[key].ltp > 0
                        and self.instruments[key].instrument_type != "INDEX"
                    ]
                    # 🚀 CRITICAL: Maintain consistent sorting - highest change% first
                    stocks.sort(key=lambda x: x["change_percent"], reverse=True)
                    return {sector: stocks}
                return {}
            else:
                # Get all sectors
                result = {}
                for sector_name, instrument_keys in self.sector_instruments.items():
                    stocks = [
                        asdict(self.instruments[key])
                        for key in instrument_keys
                        if key in self.instruments
                        and self.instruments[key].ltp > 0
                        and self.instruments[key].instrument_type != "INDEX"
                    ]
                    if stocks:  # Only include sectors with active stocks
                        # 🚀 CRITICAL: Maintain consistent sorting - highest change% first (gainers at top)
                        stocks.sort(key=lambda x: x["change_percent"], reverse=True)
                        result[sector_name] = stocks

                return result

        except Exception as e:
            logger.error(f"Error getting sector stocks: {e}")
            return {}

    def get_sector_leaders(
        self, limit_per_sector: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get top performers from each sector - ultra-fast"""
        try:
            sector_leaders = {}

            for sector_name, instrument_keys in self.sector_instruments.items():
                sector_stocks = [
                    self.instruments[key]
                    for key in instrument_keys
                    if key in self.instruments
                    and self.instruments[key].ltp > 0
                    and self.instruments[key].change_percent > 0
                ]

                if sector_stocks:
                    # Get top performers in this sector
                    top_performers = sorted(
                        sector_stocks, key=lambda x: x.change_percent, reverse=True
                    )[:limit_per_sector]
                    sector_leaders[sector_name] = [
                        asdict(stock) for stock in top_performers
                    ]

            return sector_leaders

        except Exception as e:
            logger.error(f"Error getting sector leaders: {e}")
            return {}

    def get_advance_decline_analysis(self) -> Dict[str, Any]:
        """Get comprehensive advance/decline analysis - O(1) from pre-sorted lists"""
        try:
            total_stocks = (
                len(self.advancing_stocks)
                + len(self.declining_stocks)
                + len(self.unchanged_stocks)
            )

            if total_stocks == 0:
                return {"error": "No active stocks for advance/decline analysis"}

            # Basic advance/decline metrics
            advancing_count = len(self.advancing_stocks)
            declining_count = len(self.declining_stocks)
            unchanged_count = len(self.unchanged_stocks)

            # Calculate ratios
            advance_decline_ratio = (
                advancing_count / declining_count
                if declining_count > 0
                else float("inf")
            )
            market_breadth_percent = (
                (advancing_count - declining_count) / total_stocks
            ) * 100

            # New highs/lows
            new_highs_count = len(self.new_highs)
            new_lows_count = len(self.new_lows)
            high_low_ratio = (
                new_highs_count / new_lows_count if new_lows_count > 0 else float("inf")
            )

            # Momentum analysis
            strong_advances = len(
                [
                    key
                    for key in self.advancing_stocks
                    if self.instruments[key].change_percent > 3
                ]
            )
            strong_declines = len(
                [
                    key
                    for key in self.declining_stocks
                    if self.instruments[key].change_percent < -3
                ]
            )

            # Market strength assessment
            if advance_decline_ratio > 2.0:
                market_strength = "very_strong"
            elif advance_decline_ratio > 1.5:
                market_strength = "strong"
            elif advance_decline_ratio > 0.8:
                market_strength = "neutral"
            elif advance_decline_ratio > 0.5:
                market_strength = "weak"
            else:
                market_strength = "very_weak"

            return {
                # Basic counts
                "total_stocks": total_stocks,
                "advancing": advancing_count,
                "declining": declining_count,
                "unchanged": unchanged_count,
                # Ratios and percentages
                "advance_decline_ratio": round(advance_decline_ratio, 2),
                "market_breadth_percent": round(market_breadth_percent, 2),
                "advancing_percent": round((advancing_count / total_stocks) * 100, 2),
                "declining_percent": round((declining_count / total_stocks) * 100, 2),
                # New highs/lows
                "new_highs": new_highs_count,
                "new_lows": new_lows_count,
                "high_low_ratio": (
                    round(high_low_ratio, 2)
                    if high_low_ratio != float("inf")
                    else "unlimited"
                ),
                # Momentum analysis
                "strong_advances": strong_advances,
                "strong_declines": strong_declines,
                "momentum_ratio": (
                    round(strong_advances / strong_declines, 2)
                    if strong_declines > 0
                    else float("inf")
                ),
                # Overall assessment
                "market_strength": market_strength,
                "market_sentiment": (
                    "bullish"
                    if market_breadth_percent > 10
                    else "bearish" if market_breadth_percent < -10 else "neutral"
                ),
                # Participation rates
                "advance_participation": round(
                    (advancing_count / total_stocks) * 100, 1
                ),
                "decline_participation": round(
                    (declining_count / total_stocks) * 100, 1
                ),
                "high_momentum_participation": round(
                    ((strong_advances + strong_declines) / total_stocks) * 100, 1
                ),
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error calculating advance/decline analysis: {e}")
            return {"error": str(e)}

    def get_advancing_stocks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get advancing stocks - O(1) from pre-sorted list"""
        try:
            return [
                asdict(self.instruments[key]) for key in self.advancing_stocks[:limit]
            ]
        except Exception as e:
            logger.error(f"Error getting advancing stocks: {e}")
            return []

    def get_declining_stocks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get declining stocks - O(1) from pre-sorted list"""
        try:
            return [
                asdict(self.instruments[key]) for key in self.declining_stocks[:limit]
            ]
        except Exception as e:
            logger.error(f"Error getting declining stocks: {e}")
            return []

    def get_market_breadth(self) -> Dict[str, Any]:
        """Get market breadth analysis - O(1) from pre-calculated advance/decline data"""
        try:
            # Use advance/decline analysis for market breadth
            advance_decline_data = self.get_advance_decline_analysis()

            if "error" in advance_decline_data:
                return advance_decline_data

            # Enhanced breadth metrics
            total_stocks = advance_decline_data["total_stocks"]
            advancing = advance_decline_data["advancing"]
            declining = advance_decline_data["declining"]

            # Volume-weighted breadth (stocks with significant volume)
            high_volume_advancing = len(
                [
                    key
                    for key in self.advancing_stocks
                    if self.instruments[key].volume > 100000
                ]
            )
            high_volume_declining = len(
                [
                    key
                    for key in self.declining_stocks
                    if self.instruments[key].volume > 100000
                ]
            )

            return {
                **advance_decline_data,
                "volume_weighted_breadth": {
                    "high_volume_advancing": high_volume_advancing,
                    "high_volume_declining": high_volume_declining,
                    "volume_weighted_ratio": (
                        round(high_volume_advancing / high_volume_declining, 2)
                        if high_volume_declining > 0
                        else float("inf")
                    ),
                },
                "breadth_indicators": {
                    "strong_breadth": advancing > total_stocks * 0.6,
                    "weak_breadth": declining > total_stocks * 0.6,
                    "neutral_breadth": abs(advancing - declining) < total_stocks * 0.1,
                },
            }

        except Exception as e:
            logger.error(f"Error calculating market breadth: {e}")
            return {"error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics"""
        stocks_with_data = len(
            [
                k
                for k in self.instruments
                if self.instruments[k].ltp > 0
                and self.instruments[k].instrument_type != "INDEX"
            ]
        )
        indices_with_data = len(
            [
                k
                for k in self.index_instruments
                if k in self.instruments and self.instruments[k].ltp > 0
            ]
        )

        return {
            **self.stats,
            "update_count": self.update_count,
            "total_instruments": len(self.instruments),
            "stocks_with_data": stocks_with_data,
            "indices_with_data": indices_with_data,
            "sectors_count": len(self.sector_instruments),
            "fno_instruments_count": len(self.fno_instruments),
            "index_instruments_count": len(self.index_instruments),
            # Analytics statistics
            "advancing_stocks": len(self.advancing_stocks),
            "declining_stocks": len(self.declining_stocks),
            "unchanged_stocks": len(self.unchanged_stocks),
            "new_highs": len(self.new_highs),
            "new_lows": len(self.new_lows),
            # Sorting statistics
            "sorted_by_change_count": len(self.sorted_by_change),
            "sorted_by_volume_count": len(self.sorted_by_volume),
            "sorted_by_value_count": len(self.sorted_by_value),
        }

    def get_gap_analysis(self) -> Dict[str, Any]:
        """Get gap up/down analysis for stocks"""
        try:
            gap_ups = []
            gap_downs = []

            for instrument_key, data in self._live_prices.items():
                if not isinstance(data, dict):
                    continue

                open_price = data.get("open", 0)
                close_price = data.get(
                    "cp", data.get("previous_close", 0)
                )  # cp = closing price (previous)
                symbol = data.get("symbol", "")

                if open_price > 0 and close_price > 0:
                    gap_percent = ((open_price - close_price) / close_price) * 100

                    stock_info = {
                        "symbol": symbol,
                        "instrument_key": instrument_key,
                        "open": open_price,
                        "previous_close": close_price,
                        "gap_percent": round(gap_percent, 2),
                        "current_price": data.get(
                            "ltp", data.get("last_price", open_price)
                        ),
                        "volume": data.get("volume", 0),
                        "sector": self._get_sector_for_symbol(symbol),
                    }

                    # Gap up criteria: > 1% gap up
                    if gap_percent > 1.0:
                        gap_ups.append(stock_info)

                    # Gap down criteria: > 1% gap down
                    elif gap_percent < -1.0:
                        gap_downs.append(stock_info)

            # Sort by gap percentage
            gap_ups.sort(key=lambda x: x["gap_percent"], reverse=True)
            gap_downs.sort(key=lambda x: x["gap_percent"])

            return {
                "gap_up": gap_ups[:20],  # Top 20 gap ups
                "gap_down": gap_downs[:20],  # Top 20 gap downs
                "summary": {
                    "total_gap_ups": len(gap_ups),
                    "total_gap_downs": len(gap_downs),
                    "avg_gap_up": (
                        round(
                            sum(stock["gap_percent"] for stock in gap_ups)
                            / len(gap_ups),
                            2,
                        )
                        if gap_ups
                        else 0
                    ),
                    "avg_gap_down": (
                        round(
                            sum(stock["gap_percent"] for stock in gap_downs)
                            / len(gap_downs),
                            2,
                        )
                        if gap_downs
                        else 0
                    ),
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Error calculating gap analysis: {e}")
            return {
                "gap_up": [],
                "gap_down": [],
                "summary": {
                    "total_gap_ups": 0,
                    "total_gap_downs": 0,
                    "avg_gap_up": 0,
                    "avg_gap_down": 0,
                },
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def get_breakout_analysis(self) -> Dict[str, Any]:
        """Get breakout/breakdown analysis based on price movements"""
        try:
            breakouts = []
            breakdowns = []

            for instrument_key, data in self._live_prices.items():
                if not isinstance(data, dict):
                    continue

                current_price = data.get("ltp", data.get("last_price", 0))
                high = data.get("high", 0)
                low = data.get("low", 0)
                open_price = data.get("open", 0)
                volume = data.get("volume", 0)
                change_percent = data.get("change_percent", 0)

                if current_price <= 0 or high <= 0 or low <= 0 or open_price <= 0:
                    continue

                symbol = data.get("symbol", "")

                # Calculate price position within the day's range
                day_range = high - low
                if day_range > 0:
                    position_in_range = (current_price - low) / day_range * 100
                else:
                    position_in_range = 50  # Default to middle if no range

                stock_info = {
                    "symbol": symbol,
                    "instrument_key": instrument_key,
                    "current_price": current_price,
                    "high": high,
                    "low": low,
                    "open": open_price,
                    "change_percent": round(change_percent, 2),
                    "volume": volume,
                    "position_in_range": round(position_in_range, 2),
                    "sector": self._get_sector_for_symbol(symbol),
                }

                # Breakout criteria:
                # 1. Price near day's high (>90% of range)
                # 2. Positive change (>1%)
                if position_in_range > 90 and change_percent > 1.0:
                    breakouts.append(stock_info)

                # Breakdown criteria:
                # 1. Price near day's low (<10% of range)
                # 2. Negative change (<-1%)
                elif position_in_range < 10 and change_percent < -1.0:
                    breakdowns.append(stock_info)

            # Sort by strength of breakout/breakdown
            breakouts.sort(key=lambda x: x["change_percent"], reverse=True)
            breakdowns.sort(key=lambda x: x["change_percent"])

            return {
                "breakouts": breakouts[:20],  # Top 20 breakouts
                "breakdowns": breakdowns[:20],  # Top 20 breakdowns
                "summary": {
                    "total_breakouts": len(breakouts),
                    "total_breakdowns": len(breakdowns),
                    "avg_breakout_strength": (
                        round(
                            sum(stock["change_percent"] for stock in breakouts)
                            / len(breakouts),
                            2,
                        )
                        if breakouts
                        else 0
                    ),
                    "avg_breakdown_strength": (
                        round(
                            sum(stock["change_percent"] for stock in breakdowns)
                            / len(breakdowns),
                            2,
                        )
                        if breakdowns
                        else 0
                    ),
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Error calculating breakout analysis: {e}")
            return {
                "breakouts": [],
                "breakdowns": [],
                "summary": {
                    "total_breakouts": 0,
                    "total_breakdowns": 0,
                    "avg_breakout_strength": 0,
                    "avg_breakdown_strength": 0,
                },
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def get_market_sentiment(self) -> Dict[str, Any]:
        """Calculate market sentiment based on advance/decline and market breadth"""
        try:
            # Get advance decline analysis
            advance_decline = self.get_advance_decline_analysis()

            if "error" in advance_decline:
                return {
                    "sentiment": "unknown",
                    "confidence": 0,
                    "metrics": {
                        "market_breadth_percent": 0,
                        "advance_decline_ratio": 0,
                        "advancing": 0,
                        "declining": 0,
                        "total_stocks": 0,
                    },
                    "error": "No market data available",
                    "timestamp": datetime.now().isoformat(),
                }

            # Extract metrics
            advancing = advance_decline.get("advancing", 0)
            declining = advance_decline.get("declining", 0)
            total_stocks = advance_decline.get("total_stocks", 0)
            ad_ratio = advance_decline.get("advance_decline_ratio", 1)
            ad_percentage = advance_decline.get("ad_percentage", 0)

            # Calculate market breadth percentage
            if total_stocks > 0:
                market_breadth_percent = ((advancing - declining) / total_stocks) * 100
            else:
                market_breadth_percent = 0

            # Determine sentiment based on multiple factors
            if ad_percentage > 15 and ad_ratio > 2.0:
                sentiment = "very_bullish"
                confidence = min(95, abs(ad_percentage) * 4)
            elif ad_percentage > 5 and ad_ratio > 1.3:
                sentiment = "bullish"
                confidence = min(85, abs(ad_percentage) * 5)
            elif ad_percentage < -15 and ad_ratio < 0.5:
                sentiment = "very_bearish"
                confidence = min(95, abs(ad_percentage) * 4)
            elif ad_percentage < -5 and ad_ratio < 0.8:
                sentiment = "bearish"
                confidence = min(85, abs(ad_percentage) * 5)
            else:
                sentiment = "neutral"
                confidence = 50 + abs(ad_percentage)

            return {
                "sentiment": sentiment,
                "confidence": round(confidence, 1),
                "metrics": {
                    "market_breadth_percent": round(market_breadth_percent, 2),
                    "advance_decline_ratio": round(ad_ratio, 2),
                    "advancing": advancing,
                    "declining": declining,
                    "total_stocks": total_stocks,
                    "ad_percentage": round(ad_percentage, 2),
                },
                "market_breadth": advance_decline.get("market_breadth", "neutral"),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error calculating market sentiment: {e}")
            return {
                "sentiment": "unknown",
                "confidence": 0,
                "metrics": {
                    "market_breadth_percent": 0,
                    "advance_decline_ratio": 0,
                    "advancing": 0,
                    "declining": 0,
                    "total_stocks": 0,
                },
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    # Removed complex list tracking method - keeping it simple


# Create singleton instance
optimized_market_service = OptimizedMarketDataService()
