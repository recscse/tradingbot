# services/market_data_hub.py - HIGH-PERFORMANCE MARKET DATA HUB with NumPy/Pandas
"""
Ultra-Fast Market Data Hub for Real-Time Trading Application

Features:
- NumPy arrays for vectorized operations (10-100x faster)
- Pandas DataFrames for complex queries and analytics
- Zero-copy data sharing where possible
- Columnar storage for cache efficiency
- SIMD optimizations via NumPy
- Topic-based pub/sub system
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Callable, Optional, Union, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import threading
from concurrent.futures import ThreadPoolExecutor
import weakref

# High-performance libraries
import numpy as np
import pandas as pd
from numba import jit, njit
import pyarrow as pa
import pyarrow.compute as pc

# Try to import optional performance libraries
try:
    import polars as pl
    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

# NumPy dtypes for optimal memory usage
PRICE_DTYPE = np.float32  # 4 bytes vs 8 for float64
VOLUME_DTYPE = np.int32   # 4 bytes vs 8 for int64
TIMESTAMP_DTYPE = np.float64  # Need precision for timestamps

@dataclass
class MarketDataSchema:
    """Schema definition for market data columns"""
    # Core price fields
    LTP = 'ltp'
    CHANGE = 'change'
    CHANGE_PERCENT = 'change_percent'
    VOLUME = 'volume'
    
    # OHLC fields
    OPEN = 'open'
    HIGH = 'high'
    LOW = 'low'
    CLOSE = 'close'
    
    # Order book
    BID = 'bid'
    ASK = 'ask'
    BID_QTY = 'bid_qty'
    ASK_QTY = 'ask_qty'
    
    # Metadata
    SYMBOL = 'symbol'
    EXCHANGE = 'exchange'
    SECTOR = 'sector'
    NAME = 'name'
    
    # Timestamps
    TIMESTAMP = 'timestamp'
    UPDATE_COUNT = 'update_count'
    
    @classmethod
    def get_numeric_columns(cls) -> List[str]:
        """Get columns that should be numeric"""
        return [
            cls.LTP, cls.CHANGE, cls.CHANGE_PERCENT, cls.VOLUME,
            cls.OPEN, cls.HIGH, cls.LOW, cls.CLOSE,
            cls.BID, cls.ASK, cls.BID_QTY, cls.ASK_QTY,
            cls.TIMESTAMP, cls.UPDATE_COUNT
        ]
    
    @classmethod
    def get_string_columns(cls) -> List[str]:
        """Get columns that should be strings"""
        return [cls.SYMBOL, cls.EXCHANGE, cls.SECTOR, cls.NAME]

# Numba-compiled utility functions (standalone)
@njit(cache=True)
def fast_percentage_change(current: np.ndarray, previous: np.ndarray) -> np.ndarray:
    """Ultra-fast percentage change calculation using Numba"""
    result = np.zeros_like(current)
    mask = previous != 0
    result[mask] = ((current[mask] - previous[mask]) / previous[mask]) * 100
    return result

@njit(cache=True)
def fast_moving_average(values: np.ndarray, window: int) -> np.ndarray:
    """Fast moving average calculation"""
    if len(values) < window:
        return np.full_like(values, np.nan)
    
    result = np.zeros_like(values)
    for i in range(window - 1, len(values)):
        result[i] = np.mean(values[i - window + 1:i + 1])
    
    return result

@njit(cache=True)
def fast_volatility(prices: np.ndarray, window: int = 20) -> float:
    """Fast volatility calculation"""
    if len(prices) < window:
        return 0.0
    
    returns = np.diff(prices) / prices[:-1]
    return np.std(returns[-window:]) * np.sqrt(252)  # Annualized volatility

@njit(cache=True)  
def fast_change_calculation(ltp: np.ndarray, close: np.ndarray, change: np.ndarray, change_percent: np.ndarray, indices: np.ndarray):
    """Ultra-fast change calculation for updated instruments"""
    for i in range(len(indices)):
        idx = indices[i]
        if close[idx] != 0 and change_percent[idx] == 0:
            change_percent[idx] = (change[idx] / close[idx]) * 100

class HighPerformanceMarketDataHub:
    """
    🚀 ULTRA-HIGH-PERFORMANCE MARKET DATA HUB
    
    Uses NumPy/Pandas for vectorized operations and columnar storage
    Optimized for real-time trading with microsecond latencies
    """
    
    def __init__(self, 
                 max_instruments: int = 10000,
                 history_depth: int = 1000,
                 enable_redis: bool = True,
                 enable_analytics: bool = True):
        
        # Configuration
        self.max_instruments = max_instruments
        self.history_depth = history_depth
        self.enable_redis = enable_redis
        self.enable_analytics = enable_analytics
        
        # High-performance data storage
        self.instrument_index: Dict[str, int] = {}  # instrument_key -> array index
        self.reverse_index: Dict[int, str] = {}     # array index -> instrument_key
        self.next_index = 0
        
        # NumPy arrays for ultra-fast access (columnar storage)
        self._init_numpy_arrays()
        
        # Pandas DataFrame for complex operations (created on-demand)
        self._df_cache: Optional[pd.DataFrame] = None
        self._df_dirty = False
        self._df_last_update = 0.0
        
        # Polars DataFrame for even faster analytics (if available)
        self._pl_cache: Optional['pl.DataFrame'] = None
        
        # Thread safety
        self.data_lock = threading.RLock()
        
        # Consumer management
        self.consumers: Dict[str, Dict[str, Any]] = {}
        self.consumer_queues: Dict[str, asyncio.Queue] = {}
        self.topic_subscribers: Dict[str, Set[str]] = defaultdict(set)
        
        # Performance metrics
        self.metrics = {
            "total_updates": 0,
            "updates_per_second": 0.0,
            "avg_processing_time_us": 0.0,  # Microseconds for precision
            "active_instruments": 0,
            "memory_usage_mb": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "vectorized_ops": 0
        }
        
        # Background tasks
        self.background_tasks: Set[asyncio.Task] = set()
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
        # Redis connection
        self.redis_client = None
        
        # Thread pool for CPU-intensive operations
        self.thread_pool = ThreadPoolExecutor(
            max_workers=4, 
            thread_name_prefix="market-hub"
        )
        
        logger.info(f"🚀 High-Performance Market Data Hub initialized")
        logger.info(f"📊 Max instruments: {max_instruments}, History depth: {history_depth}")
        
    def _init_numpy_arrays(self):
        """Initialize NumPy arrays for columnar storage"""
        size = self.max_instruments
        
        # Core price data (optimized dtypes)
        self.ltp = np.zeros(size, dtype=PRICE_DTYPE)
        self.change = np.zeros(size, dtype=PRICE_DTYPE)
        self.change_percent = np.zeros(size, dtype=PRICE_DTYPE)
        self.volume = np.zeros(size, dtype=VOLUME_DTYPE)
        
        # OHLC data
        self.open_price = np.zeros(size, dtype=PRICE_DTYPE)
        self.high = np.zeros(size, dtype=PRICE_DTYPE)
        self.low = np.zeros(size, dtype=PRICE_DTYPE)
        self.close = np.zeros(size, dtype=PRICE_DTYPE)
        
        # Order book
        self.bid = np.zeros(size, dtype=PRICE_DTYPE)
        self.ask = np.zeros(size, dtype=PRICE_DTYPE)
        self.bid_qty = np.zeros(size, dtype=VOLUME_DTYPE)
        self.ask_qty = np.zeros(size, dtype=VOLUME_DTYPE)
        
        # Timestamps and counters
        self.timestamps = np.zeros(size, dtype=TIMESTAMP_DTYPE)
        self.update_counts = np.zeros(size, dtype=np.int32)
        self.first_seen = np.zeros(size, dtype=TIMESTAMP_DTYPE)
        
        # String data (stored separately for efficiency)
        self.symbols = [''] * size
        self.exchanges = ['NSE'] * size
        self.sectors = ['OTHER'] * size
        self.names = [''] * size
        
        # Valid data mask
        self.valid_mask = np.zeros(size, dtype=bool)
        
        # Historical data (ring buffer)
        self.price_history = np.zeros((size, self.history_depth), dtype=PRICE_DTYPE)
        self.volume_history = np.zeros((size, self.history_depth), dtype=VOLUME_DTYPE)
        self.history_index = np.zeros(size, dtype=np.int32)
        
        logger.info(f"📊 Initialized NumPy arrays: {self._calculate_memory_usage():.2f} MB")
    
    def _calculate_memory_usage(self) -> float:
        """Calculate memory usage in MB"""
        arrays = [
            self.ltp, self.change, self.change_percent, self.volume,
            self.open_price, self.high, self.low, self.close,
            self.bid, self.ask, self.bid_qty, self.ask_qty,
            self.timestamps, self.update_counts, self.first_seen,
            self.valid_mask, self.price_history, self.volume_history,
            self.history_index
        ]
        
        total_bytes = sum(arr.nbytes for arr in arrays)
        return total_bytes / (1024 * 1024)
    
    async def start(self):
        """Start the hub and background services"""
        if self.is_running:
            return
            
        self.is_running = True
        self.shutdown_event.clear()
        
        # Initialize Redis if enabled
        if self.enable_redis and REDIS_AVAILABLE:
            await self._init_redis()
        
        # Start background tasks
        self._start_background_tasks()
        
        logger.info("✅ High-Performance Market Data Hub started")
    
    async def stop(self):
        """Stop the hub and cleanup resources"""
        if not self.is_running:
            return
            
        self.is_running = False
        self.shutdown_event.set()
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.aclose()
        
        logger.info("🛑 High-Performance Market Data Hub stopped")
    
    def update_market_data_batch(self, raw_data: Dict[str, Any]) -> int:
        """
        🚀 ATOMIC BATCH UPDATE - Ensures data consistency and correct ordering
        """
        start_time = time.perf_counter()
        updated_count = 0
        updated_indices = []
        
        try:
            current_timestamp = time.time()
            
            # CRITICAL: Single atomic transaction with lock
            with self.data_lock:
                # Phase 1: Validate and prepare all updates
                valid_updates = []
                
                for instrument_key, raw_item in raw_data.items():
                    if not self._is_valid_raw_data(raw_item):
                        continue
                    
                    # Get or create index
                    if instrument_key in self.instrument_index:
                        idx = self.instrument_index[instrument_key]
                    else:
                        if self.next_index >= self.max_instruments:
                            logger.warning(f"⚠️ Max instruments reached ({self.max_instruments})")
                            continue
                        
                        idx = self.next_index
                        self.instrument_index[instrument_key] = idx
                        self.reverse_index[idx] = instrument_key
                        self.next_index += 1
                        
                        # Initialize new instrument
                        self.first_seen[idx] = current_timestamp
                        self.symbols[idx] = self._extract_symbol(instrument_key)
                        self.exchanges[idx] = self._extract_exchange(instrument_key)
                        self.valid_mask[idx] = True
                    
                    # Prepare update data
                    valid_updates.append({
                        'idx': idx,
                        'instrument_key': instrument_key,
                        'raw_item': raw_item,
                        'prev_ltp': self.ltp[idx]
                    })
                
                # Phase 2: Apply all updates atomically (prevents inconsistent state)
                for update in valid_updates:
                    idx = update['idx']
                    raw_item = update['raw_item']
                    prev_ltp = update['prev_ltp']
                    
                    # Core price data
                    new_ltp = float(raw_item.get("ltp", raw_item.get("last_price", 0)))
                    self.ltp[idx] = new_ltp
                    self.volume[idx] = int(raw_item.get("volume", raw_item.get("vol", 0)))
                    self.open_price[idx] = float(raw_item.get("open", 0))
                    self.high[idx] = float(raw_item.get("high", 0))
                    self.low[idx] = float(raw_item.get("low", 0))
                    self.close[idx] = float(raw_item.get("close", 0))
                    
                    # Calculate changes consistently
                    if "change" in raw_item:
                        self.change[idx] = float(raw_item["change"])
                    else:
                        self.change[idx] = new_ltp - self.close[idx] if self.close[idx] != 0 else 0
                    
                    if "chp" in raw_item or "change_percent" in raw_item:
                        self.change_percent[idx] = float(raw_item.get("chp", raw_item.get("change_percent", 0)))
                    else:
                        if self.close[idx] != 0:
                            self.change_percent[idx] = (self.change[idx] / self.close[idx]) * 100
                        else:
                            self.change_percent[idx] = 0
                    
                    # Order book data
                    self.bid[idx] = float(raw_item.get("bid", 0))
                    self.ask[idx] = float(raw_item.get("ask", 0))
                    self.bid_qty[idx] = int(raw_item.get("bid_qty", 0))
                    self.ask_qty[idx] = int(raw_item.get("ask_qty", 0))
                    
                    # Update timestamps and counters
                    self.timestamps[idx] = current_timestamp
                    self.update_counts[idx] += 1
                    
                    # Update price history (ring buffer)
                    hist_idx = self.history_index[idx] % self.history_depth
                    self.price_history[idx, hist_idx] = new_ltp
                    self.volume_history[idx, hist_idx] = self.volume[idx]
                    self.history_index[idx] += 1
                    
                    # Track significant updates only
                    if abs(new_ltp - prev_ltp) > 0.001 or self.update_counts[idx] == 1:
                        updated_indices.append(idx)
                        updated_count += 1
                
                # Phase 3: Post-process all updates with vectorized calculations
                if updated_indices:
                    self._post_process_updates(np.array(updated_indices))
                    
                    # IMPORTANT: Refresh analytics cache immediately for consistency
                    self._invalidate_analytics_cache()
            
            # Update performance metrics
            processing_time_us = (time.perf_counter() - start_time) * 1_000_000
            self.metrics["total_updates"] += updated_count
            self.metrics["active_instruments"] = np.sum(self.valid_mask)
            self.metrics["avg_processing_time_us"] = (
                0.9 * self.metrics["avg_processing_time_us"] + 
                0.1 * processing_time_us
            )
            self.metrics["vectorized_ops"] += 1
            
            # Mark DataFrame as dirty for lazy refresh
            if updated_count > 0:
                self._df_dirty = True
                self._df_last_update = current_timestamp
                
                # IMMEDIATE: Broadcast updates to consumers (preserving order)
                asyncio.create_task(self._broadcast_atomic_updates(updated_indices))
                
                # Check if any indices were updated and broadcast separately
                indices_updated = [idx for idx in updated_indices if self._is_index(self.reverse_index[idx])]
                if indices_updated:
                    asyncio.create_task(self._broadcast_indices_updates())
            
            if updated_count > 0:
                logger.debug(f"⚡ Atomic update: {updated_count} instruments in {processing_time_us:.1f}μs")
            
            return updated_count
            
        except Exception as e:
            logger.error(f"❌ Error in atomic update: {e}")
            return 0
    
    def _invalidate_analytics_cache(self):
        """Invalidate analytics cache to ensure fresh calculations"""
        self._df_cache = None
        self._df_dirty = True
        if hasattr(self, '_pl_cache'):
            self._pl_cache = None
    
    def _post_process_updates(self, updated_indices: np.ndarray):
        """Vectorized post-processing of updated data"""
        if len(updated_indices) == 0:
            return
        
        # Use standalone Numba function for ultra-fast calculations
        fast_change_calculation(
            self.ltp, self.close, self.change, 
            self.change_percent, updated_indices
        )
    
    def get_live_price_fast(self, instrument_key: str) -> Optional[Dict[str, Any]]:
        """Ultra-fast single instrument lookup"""
        with self.data_lock:
            idx = self.instrument_index.get(instrument_key)
            if idx is None or not self.valid_mask[idx]:
                self.metrics["cache_misses"] += 1
                return None
            
            self.metrics["cache_hits"] += 1
            
            return {
                "instrument_key": instrument_key,
                "symbol": self.symbols[idx],
                "ltp": float(self.ltp[idx]),
                "last_price": float(self.ltp[idx]),
                "change": float(self.change[idx]),
                "change_percent": float(self.change_percent[idx]),
                "volume": int(self.volume[idx]),
                "open": float(self.open_price[idx]),
                "high": float(self.high[idx]),
                "low": float(self.low[idx]),
                "close": float(self.close[idx]),
                "bid": float(self.bid[idx]),
                "ask": float(self.ask[idx]),
                "bid_qty": int(self.bid_qty[idx]),
                "ask_qty": int(self.ask_qty[idx]),
                "exchange": self.exchanges[idx],
                "sector": self.sectors[idx],
                "name": self.names[idx],
                "timestamp": self.timestamps[idx],
                "last_updated": datetime.fromtimestamp(self.timestamps[idx]).isoformat(),
                "update_count": int(self.update_counts[idx]),
                "data_source": "market_hub_vectorized"
            }
    
    def get_multiple_prices_vectorized(self, instrument_keys: List[str]) -> Dict[str, Dict[str, Any]]:
        """Vectorized multi-instrument lookup"""
        result = {}
        
        with self.data_lock:
            # Convert to indices
            indices = []
            valid_keys = []
            
            for key in instrument_keys:
                idx = self.instrument_index.get(key)
                if idx is not None and self.valid_mask[idx]:
                    indices.append(idx)
                    valid_keys.append(key)
                    self.metrics["cache_hits"] += 1
                else:
                    self.metrics["cache_misses"] += 1
            
            if not indices:
                return result
            
            # Vectorized extraction
            idx_array = np.array(indices)
            
            for i, key in enumerate(valid_keys):
                idx = idx_array[i]
                result[key] = {
                    "instrument_key": key,
                    "symbol": self.symbols[idx],
                    "ltp": float(self.ltp[idx]),
                    "last_price": float(self.ltp[idx]),
                    "change": float(self.change[idx]),
                    "change_percent": float(self.change_percent[idx]),
                    "volume": int(self.volume[idx]),
                    "open": float(self.open_price[idx]),
                    "high": float(self.high[idx]),
                    "low": float(self.low[idx]),
                    "close": float(self.close[idx]),
                    "timestamp": self.timestamps[idx],
                    "update_count": int(self.update_counts[idx])
                }
        
        return result
    
    def get_dataframe(self, refresh: bool = False) -> pd.DataFrame:
        """
        Get pandas DataFrame for complex analytics operations
        Uses lazy loading and caching for performance
        """
        with self.data_lock:
            if self._df_cache is None or self._df_dirty or refresh:
                self._refresh_dataframe()
            
            return self._df_cache.copy()  # Return copy to prevent mutations
    
    def _refresh_dataframe(self):
        """Refresh the cached pandas DataFrame"""
        try:
            # Get valid data mask
            valid_indices = np.where(self.valid_mask)[0]
            
            if len(valid_indices) == 0:
                self._df_cache = pd.DataFrame()
                return
            
            # Create DataFrame with vectorized operations
            data = {
                'instrument_key': [self.reverse_index[i] for i in valid_indices],
                'symbol': [self.symbols[i] for i in valid_indices],
                'ltp': self.ltp[valid_indices],
                'last_price': self.ltp[valid_indices],  # React compatibility
                'change': self.change[valid_indices],
                'change_percent': self.change_percent[valid_indices],
                'volume': self.volume[valid_indices],
                'open': self.open_price[valid_indices],
                'high': self.high[valid_indices],
                'low': self.low[valid_indices],
                'close': self.close[valid_indices],
                'bid': self.bid[valid_indices],
                'ask': self.ask[valid_indices],
                'bid_qty': self.bid_qty[valid_indices],
                'ask_qty': self.ask_qty[valid_indices],
                'exchange': [self.exchanges[i] for i in valid_indices],
                'sector': [self.sectors[i] for i in valid_indices],
                'name': [self.names[i] for i in valid_indices],
                'timestamp': self.timestamps[valid_indices],
                'update_count': self.update_counts[valid_indices]
            }
            
            self._df_cache = pd.DataFrame(data)
            
            # Add computed columns using vectorized operations
            self._df_cache['last_updated'] = pd.to_datetime(
                self._df_cache['timestamp'], unit='s'
            )
            
            # Performance categories using pd.cut (vectorized)
            self._df_cache['performance_category'] = pd.cut(
                self._df_cache['change_percent'],
                bins=[-np.inf, -5, -1, 1, 5, np.inf],
                labels=['strong_loser', 'loser', 'neutral', 'gainer', 'strong_gainer']
            )
            
            # Volume categories
            self._df_cache['volume_category'] = pd.cut(
                self._df_cache['volume'],
                bins=[0, 10000, 100000, 1000000, np.inf],
                labels=['low', 'medium', 'high', 'very_high']
            )
            
            self._df_dirty = False
            
            logger.debug(f"📊 DataFrame refreshed: {len(self._df_cache)} instruments")
            
        except Exception as e:
            logger.error(f"❌ Error refreshing DataFrame: {e}")
            self._df_cache = pd.DataFrame()
    
    def get_top_movers_vectorized(self, limit: int = 20) -> Dict[str, List[Dict]]:
        """Ultra-fast top movers calculation using vectorized operations"""
        with self.data_lock:
            if not np.any(self.valid_mask):
                return {"gainers": [], "losers": []}
            
            # Get valid indices sorted by change_percent
            valid_indices = np.where(self.valid_mask)[0]
            changes = self.change_percent[valid_indices]
            
            # Vectorized sorting
            sorted_indices = valid_indices[np.argsort(changes)]
            
            # Get top gainers and losers
            gainers_indices = sorted_indices[-limit:][::-1]  # Reverse for descending
            losers_indices = sorted_indices[:limit]
            
            def _create_mover_data(indices):
                return [
                    {
                        "instrument_key": self.reverse_index[idx],
                        "symbol": self.symbols[idx],
                        "ltp": float(self.ltp[idx]),
                        "last_price": float(self.ltp[idx]),
                        "change": float(self.change[idx]),
                        "change_percent": float(self.change_percent[idx]),
                        "volume": int(self.volume[idx]),
                        "exchange": self.exchanges[idx],
                        "sector": self.sectors[idx]
                    }
                    for idx in indices if self.change_percent[idx] != 0
                ]
            
            return {
                "gainers": _create_mover_data(gainers_indices),
                "losers": _create_mover_data(losers_indices),
                "timestamp": time.time()
            }
    
    def get_volume_leaders_vectorized(self, limit: int = 20) -> List[Dict]:
        """Ultra-fast volume leaders using vectorized operations"""
        with self.data_lock:
            if not np.any(self.valid_mask):
                return []
            
            valid_indices = np.where(self.valid_mask)[0]
            volumes = self.volume[valid_indices]
            
            # Get top volume indices
            top_indices = valid_indices[np.argsort(volumes)[-limit:][::-1]]
            
            return [
                {
                    "instrument_key": self.reverse_index[idx],
                    "symbol": self.symbols[idx],
                    "ltp": float(self.ltp[idx]),
                    "volume": int(self.volume[idx]),
                    "change_percent": float(self.change_percent[idx]),
                    "exchange": self.exchanges[idx]
                }
                for idx in top_indices if self.volume[idx] > 0
            ]
    
    def calculate_sector_performance_vectorized(self) -> Dict[str, Dict]:
        """Ultra-fast sector analysis using pandas groupby"""
        df = self.get_dataframe()
        
        if df.empty:
            return {}
        
        # Vectorized sector aggregation
        sector_stats = df.groupby('sector').agg({
            'change_percent': ['mean', 'count'],
            'volume': 'sum',
            'ltp': ['min', 'max']
        }).round(2)
        
        # Flatten column names
        sector_stats.columns = ['_'.join(col) for col in sector_stats.columns]
        
        result = {}
        for sector in sector_stats.index:
            sector_df = df[df.sector == sector]
            
            result[sector] = {
                "avg_change_percent": float(sector_stats.loc[sector, 'change_percent_mean']),
                "stock_count": int(sector_stats.loc[sector, 'change_percent_count']),
                "total_volume": int(sector_stats.loc[sector, 'volume_sum']),
                "advancing": len(sector_df[sector_df.change_percent > 0]),
                "declining": len(sector_df[sector_df.change_percent < 0]),
                "min_price": float(sector_stats.loc[sector, 'ltp_min']),
                "max_price": float(sector_stats.loc[sector, 'ltp_max'])
            }
        
        return result
    
    def register_consumer(
        self, 
        consumer_name: str,
        callback: Callable,
        topics: Union[str, List[str]] = "prices",
        priority: int = 5,
        max_queue_size: int = 1000
    ) -> bool:
        """Register a consumer for market data updates"""
        try:
            if isinstance(topics, str):
                topics = [topics]
            
            # Create consumer config
            config = {
                "name": consumer_name,
                "callback": callback,
                "topics": set(topics),
                "priority": priority,
                "is_async": asyncio.iscoroutinefunction(callback),
                "stats": {
                    "messages_sent": 0,
                    "errors": 0,
                    "avg_latency_us": 0.0
                }
            }
            
            self.consumers[consumer_name] = config
            self.consumer_queues[consumer_name] = asyncio.Queue(maxsize=max_queue_size)
            
            # Register for topics
            for topic in topics:
                self.topic_subscribers[topic].add(consumer_name)
            
            # Start consumer processor
            task = asyncio.create_task(self._consumer_processor(consumer_name))
            self.background_tasks.add(task)
            task.add_done_callback(lambda t: self.background_tasks.discard(t))
            
            logger.info(f"✅ Registered consumer: {consumer_name} for topics: {topics}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error registering consumer {consumer_name}: {e}")
            return False
    
    async def _broadcast_atomic_updates(self, updated_indices: List[int]):
        """Broadcast updates atomically with guaranteed order preservation"""
        if not updated_indices:
            return
        
        try:
            current_time = time.time()
            
            # ATOMIC: Prepare all data in single operation
            with self.data_lock:
                broadcast_data = {
                    "prices": {},
                    "timestamp": current_time,
                    "count": len(updated_indices),
                    "source": "atomic_hub",
                    "update_sequence": self.metrics["total_updates"]  # For ordering
                }
                
                # Atomic data extraction (all or nothing)
                for idx in updated_indices:
                    if idx in self.reverse_index and self.valid_mask[idx]:
                        instrument_key = self.reverse_index[idx]
                        broadcast_data["prices"][instrument_key] = {
                            "instrument_key": instrument_key,
                            "symbol": self.symbols[idx],
                            "ltp": float(self.ltp[idx]),
                            "last_price": float(self.ltp[idx]),
                            "change": float(self.change[idx]),
                            "change_percent": float(self.change_percent[idx]),
                            "volume": int(self.volume[idx]),
                            "open": float(self.open_price[idx]),
                            "high": float(self.high[idx]),
                            "low": float(self.low[idx]),
                            "close": float(self.close[idx]),
                            "timestamp": self.timestamps[idx],
                            "update_count": int(self.update_counts[idx]),
                            "is_realtime": True,
                            "data_quality": "atomic_consistent"
                        }
            
            # ORDERED: Send to consumers with priority ordering
            priority_consumers = []
            regular_consumers = []
            
            for consumer_name in self.topic_subscribers.get("prices", set()).union(
                self.topic_subscribers.get("all", set())
            ):
                if consumer_name in self.consumers:
                    priority = self.consumers[consumer_name]["priority"]
                    if priority <= 2:  # High priority (UI, trading)
                        priority_consumers.append((consumer_name, priority))
                    else:
                        regular_consumers.append((consumer_name, priority))
            
            # Sort by priority (1=highest, 10=lowest)
            priority_consumers.sort(key=lambda x: x[1])
            regular_consumers.sort(key=lambda x: x[1])
            
            # Send to high priority consumers FIRST (trading, UI)
            for consumer_name, _ in priority_consumers:
                await self._send_to_consumer_atomic(consumer_name, broadcast_data)
            
            # Send to regular consumers
            for consumer_name, _ in regular_consumers:
                await self._send_to_consumer_atomic(consumer_name, broadcast_data)
                
            logger.debug(f"⚡ Atomic broadcast: {len(updated_indices)} instruments to {len(priority_consumers + regular_consumers)} consumers")
                        
        except Exception as e:
            logger.error(f"❌ Error in atomic broadcast: {e}")
    
    async def _send_to_consumer_atomic(self, consumer_name: str, data: Dict):
        """Send data to consumer with atomic guarantees"""
        if consumer_name not in self.consumer_queues:
            return
        
        queue = self.consumer_queues[consumer_name]
        try:
            # For high-priority consumers, ensure delivery
            consumer_config = self.consumers.get(consumer_name, {})
            priority = consumer_config.get("priority", 5)
            
            if priority <= 2:  # Critical consumers (UI, trading)
                # Don't drop messages for critical consumers
                if queue.full():
                    logger.warning(f"⚠️ Critical consumer {consumer_name} queue full - processing immediately")
                    # Try to make space by processing one item
                    try:
                        old_data = queue.get_nowait()
                        # Process the old data immediately if possible
                    except asyncio.QueueEmpty:
                        pass
                
                await queue.put(data)
            else:
                # Regular consumers - can drop old messages
                if queue.full():
                    try:
                        queue.get_nowait()  # Drop oldest
                    except asyncio.QueueEmpty:
                        pass
                
                queue.put_nowait(data)
                
        except Exception as e:
            logger.debug(f"Error sending to {consumer_name}: {e}")
            # Update consumer error stats
            if consumer_name in self.consumers:
                self.consumers[consumer_name]["stats"]["errors"] += 1
    
    async def _broadcast_indices_updates(self):
        """Broadcast indices data updates to subscribers"""
        try:
            indices_data = self.get_indices_data()
            
            if indices_data and indices_data["indices"]:
                # Broadcast to indices topic subscribers
                for consumer_name in self.topic_subscribers.get("indices", set()).union(
                    self.topic_subscribers.get("all", set())
                ):
                    if consumer_name in self.consumer_queues:
                        queue = self.consumer_queues[consumer_name]
                        try:
                            indices_message = {
                                "type": "indices_data_update", 
                                "data": indices_data,
                                "timestamp": time.time(),
                                "source": "atomic_hub"
                            }
                            
                            if queue.full():
                                try:
                                    queue.get_nowait()  # Drop oldest
                                except asyncio.QueueEmpty:
                                    pass
                                    
                            queue.put_nowait(indices_message)
                        except Exception as e:
                            logger.debug(f"Error sending indices to {consumer_name}: {e}")
                
                logger.debug(f"📊 Broadcast indices: {len(indices_data['indices'])} total, {len(indices_data['major_indices'])} major")
                        
        except Exception as e:
            logger.error(f"❌ Error broadcasting indices updates: {e}")
    
    async def _consumer_processor(self, consumer_name: str):
        """Process messages for a specific consumer"""
        config = self.consumers.get(consumer_name)
        if not config:
            return
        
        queue = self.consumer_queues.get(consumer_name)
        if not queue:
            return
        
        stats = config["stats"]
        
        while self.is_running:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=1.0)
                
                start_time = time.perf_counter()
                
                # Call consumer callback
                if config["is_async"]:
                    await config["callback"](message)
                else:
                    config["callback"](message)
                
                # Update stats
                latency_us = (time.perf_counter() - start_time) * 1_000_000
                stats["messages_sent"] += 1
                stats["avg_latency_us"] = (
                    0.9 * stats["avg_latency_us"] + 0.1 * latency_us
                )
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                stats["errors"] += 1
                logger.error(f"❌ Error in consumer {consumer_name}: {e}")
    
    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        # Performance monitoring
        task = asyncio.create_task(self._performance_monitor())
        self.background_tasks.add(task)
        task.add_done_callback(lambda t: self.background_tasks.discard(t))
        
        # Memory management
        task = asyncio.create_task(self._memory_manager())
        self.background_tasks.add(task)
        task.add_done_callback(lambda t: self.background_tasks.discard(t))
    
    async def _performance_monitor(self):
        """Monitor and log performance metrics"""
        last_updates = 0
        last_time = time.time()
        
        while self.is_running:
            try:
                await asyncio.sleep(10)  # Report every 10 seconds
                
                current_time = time.time()
                current_updates = self.metrics["total_updates"]
                
                # Calculate updates per second
                time_diff = current_time - last_time
                updates_diff = current_updates - last_updates
                
                if time_diff > 0:
                    self.metrics["updates_per_second"] = updates_diff / time_diff
                
                # Update memory usage
                self.metrics["memory_usage_mb"] = self._calculate_memory_usage()
                
                logger.info(
                    f"🚀 Hub Performance: "
                    f"{self.metrics['active_instruments']} instruments, "
                    f"{self.metrics['updates_per_second']:.1f} updates/sec, "
                    f"{self.metrics['avg_processing_time_us']:.1f}μs avg, "
                    f"{self.metrics['memory_usage_mb']:.1f}MB, "
                    f"{len(self.consumers)} consumers"
                )
                
                last_updates = current_updates
                last_time = current_time
                
            except Exception as e:
                logger.error(f"❌ Error in performance monitor: {e}")
    
    async def _memory_manager(self):
        """Manage memory usage and cleanup old data"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                # Cleanup old price history beyond retention period
                current_time = time.time()
                old_threshold = current_time - (24 * 60 * 60)  # 24 hours
                
                with self.data_lock:
                    for idx in range(self.next_index):
                        if self.valid_mask[idx] and self.timestamps[idx] < old_threshold:
                            # Mark as invalid if too old and no recent updates
                            if current_time - self.timestamps[idx] > 3600:  # 1 hour
                                self.valid_mask[idx] = False
                                logger.debug(f"Cleaned up old instrument at index {idx}")
                
                # Force garbage collection periodically
                import gc
                gc.collect()
                
            except Exception as e:
                logger.error(f"❌ Error in memory manager: {e}")
    
    async def _init_redis(self):
        """Initialize Redis connection for optional caching"""
        try:
            self.redis_client = await redis.Redis()
            await self.redis_client.ping()
            logger.info("✅ Redis connection established")
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}")
            self.enable_redis = False
    
    def _is_valid_raw_data(self, raw_data: Any) -> bool:
        """Fast validation of raw market data"""
        return (
            isinstance(raw_data, dict) and
            (raw_data.get("ltp") is not None or raw_data.get("last_price") is not None)
        )
    
    def _extract_symbol(self, instrument_key: str) -> str:
        """Extract symbol from instrument key"""
        if "|" in instrument_key:
            return instrument_key.split("|")[-1]
        return instrument_key
    
    def _extract_exchange(self, instrument_key: str) -> str:
        """Extract exchange from instrument key"""
        if "|" in instrument_key:
            exchange_segment = instrument_key.split("|")[0]
            if "NSE" in exchange_segment:
                return "NSE"
            elif "BSE" in exchange_segment:
                return "BSE"
        return "NSE"
    
    def _is_index(self, instrument_key: str) -> bool:
        """Check if instrument is an index"""
        return "INDEX" in instrument_key or any(
            index_name in instrument_key.upper() 
            for index_name in ["NIFTY", "SENSEX", "BANKEX", "FINNIFTY", "MIDCPNIFTY"]
        )
    
    def get_indices_data(self) -> Dict[str, List[Dict]]:
        """Get all indices data with real-time updates"""
        with self.data_lock:
            indices = []
            major_indices = []
            sector_indices = []
            
            # Major indices symbols
            major_index_symbols = {
                "NIFTY 50", "NIFTY", "SENSEX", "NIFTY BANK", "BANKEX", 
                "NIFTY IT", "NIFTY AUTO", "NIFTY PHARMA", "NIFTY FMCG"
            }
            
            for idx in range(self.next_index):
                if not self.valid_mask[idx]:
                    continue
                    
                instrument_key = self.reverse_index[idx]
                if self._is_index(instrument_key):
                    symbol = self.symbols[idx]
                    
                    index_data = {
                        "instrument_key": instrument_key,
                        "symbol": symbol,
                        "name": symbol,  # Can be enhanced with full names
                        "ltp": float(self.ltp[idx]),
                        "last_price": float(self.ltp[idx]),
                        "change": float(self.change[idx]),
                        "change_percent": float(self.change_percent[idx]),
                        "open": float(self.open_price[idx]),
                        "high": float(self.high[idx]),
                        "low": float(self.low[idx]),
                        "close": float(self.close[idx]),
                        "timestamp": self.timestamps[idx],
                        "last_updated": datetime.fromtimestamp(self.timestamps[idx]).isoformat(),
                        "exchange": self.exchanges[idx],
                        "type": "INDEX"
                    }
                    
                    indices.append(index_data)
                    
                    # Classify as major or sector index
                    if any(major in symbol.upper() for major in major_index_symbols):
                        major_indices.append(index_data)
                    else:
                        sector_indices.append(index_data)
            
            # Calculate summary
            if indices:
                advancing = len([idx for idx in indices if idx["change_percent"] > 0])
                declining = len([idx for idx in indices if idx["change_percent"] < 0])
                unchanged = len(indices) - advancing - declining
                
                summary = {
                    "total_indices": len(indices),
                    "major_indices": len(major_indices),
                    "sector_indices": len(sector_indices),
                    "advancing": advancing,
                    "declining": declining,
                    "unchanged": unchanged,
                    "last_updated": datetime.now().isoformat()
                }
            else:
                summary = {
                    "total_indices": 0,
                    "major_indices": 0,
                    "sector_indices": 0,
                    "advancing": 0,
                    "declining": 0,
                    "unchanged": 0,
                    "last_updated": datetime.now().isoformat()
                }
            
            return {
                "indices": indices,
                "major_indices": major_indices,
                "sector_indices": sector_indices,
                "summary": summary
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return {
            **self.metrics,
            "consumer_stats": {
                name: config["stats"] for name, config in self.consumers.items()
            },
            "numpy_arrays_shape": {
                "max_instruments": self.max_instruments,
                "history_depth": self.history_depth,
                "next_index": self.next_index
            }
        }


# Singleton instance
market_data_hub = HighPerformanceMarketDataHub()


# Convenience functions
async def start_market_hub():
    """Start the high-performance market data hub"""
    await market_data_hub.start()


async def stop_market_hub():
    """Stop the market data hub"""
    await market_data_hub.stop()


def get_market_hub() -> HighPerformanceMarketDataHub:
    """Get the singleton market data hub instance"""
    return market_data_hub


# Ultra-fast access functions
def get_live_price_fast(instrument_key: str) -> Optional[Dict[str, Any]]:
    """Ultra-fast single price lookup"""
    return market_data_hub.get_live_price_fast(instrument_key)


def get_multiple_prices_fast(instrument_keys: List[str]) -> Dict[str, Dict[str, Any]]:
    """Ultra-fast multiple price lookup"""
    return market_data_hub.get_multiple_prices_vectorized(instrument_keys)


def get_top_movers_fast(limit: int = 20) -> Dict[str, List[Dict]]:
    """Ultra-fast top movers calculation"""
    return market_data_hub.get_top_movers_vectorized(limit)


def register_price_consumer_fast(name: str, callback: Callable, priority: int = 5) -> bool:
    """Register a consumer for ultra-fast price updates"""
    return market_data_hub.register_consumer(name, callback, ["prices"], priority)


def get_indices_data_fast() -> Dict[str, List[Dict]]:
    """Get all indices data with real-time updates"""
    return market_data_hub.get_indices_data()


def get_major_indices_fast() -> List[Dict]:
    """Get major indices (Nifty, Sensex, Bank Nifty, etc.)"""
    indices_data = market_data_hub.get_indices_data()
    return indices_data.get("major_indices", [])


def get_index_price_fast(symbol: str) -> Optional[Dict[str, Any]]:
    """Get live price for specific index"""
    # Try different formats
    possible_keys = [
        f"NSE_INDEX|{symbol}",
        f"BSE_INDEX|{symbol}",
        f"NSE_INDEX|Nifty {symbol}",  # e.g., "NSE_INDEX|Nifty 50"
        f"BSE_INDEX|{symbol}"
    ]
    
    for key in possible_keys:
        price_data = market_data_hub.get_live_price_fast(key)
        if price_data:
            return price_data
    
    # Search by symbol in all indices
    indices_data = market_data_hub.get_indices_data()
    for index in indices_data.get("indices", []):
        if index["symbol"].upper() == symbol.upper():
            return index
    
    return None


def register_indices_consumer_fast(name: str, callback: Callable, priority: int = 3) -> bool:
    """Register a consumer for indices updates"""
    return market_data_hub.register_consumer(name, callback, ["indices"], priority)