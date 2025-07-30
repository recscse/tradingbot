# services/market_data_queue.py - COMPLETE FILE WITH MISSING FUNCTIONS

import asyncio
import json
import logging
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Deque
import numpy as np
from dataclasses import dataclass
import redis

from services.unified_market_data import market_data_processor


logger = logging.getLogger(__name__)


@dataclass
class TickData:
    """Individual tick data structure - ONLY IN MEMORY"""

    instrument_key: str
    symbol: str
    ltp: float
    ltq: int
    change: float
    change_percent: float
    volume: int
    timestamp: datetime
    exchange: str

    def to_dict(self):
        return {
            "instrument_key": self.instrument_key,
            "symbol": self.symbol,
            "ltp": self.ltp,
            "ltq": self.ltq,
            "change": self.change,
            "change_percent": self.change_percent,
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat(),
            "exchange": self.exchange,
        }


class MarketDataQueueService:
    """
    Optimized queue service - NO DATABASE TICK STORAGE
    Only stores aggregated summaries and snapshots
    """

    def __init__(self, max_queue_size: int = 50000, max_history_per_symbol: int = 500):
        # MEMORY-ONLY storage for ticks
        self.live_data: Dict[str, TickData] = {}
        self.tick_history: Dict[str, Deque[TickData]] = defaultdict(
            lambda: deque(maxlen=max_history_per_symbol)
        )

        # Aggregated data for database
        self.daily_summaries: Dict[str, Dict] = {}
        self.hourly_snapshots: Dict[str, Dict] = {}

        # Performance tracking
        self.processed_ticks = 0
        self.start_time = datetime.now()
        self.last_update = None
        self.last_db_save = None

        # Thread safety
        self.data_lock = threading.RLock()

        # Redis for fast access and persistence
        try:
            self.redis_client = redis.Redis(
                host="localhost",
                port=6379,
                db=0,
                decode_responses=True,
                socket_timeout=2,
            )
            self.redis_client.ping()
            self.redis_available = True
            logger.info("✅ Redis connected for market data caching")
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
            self.redis_available = False

        # Sector mapping
        self.sector_mapping = self._load_sector_mapping()

        # Background tasks
        self._start_background_tasks()

        logger.info("✅ Market Data Queue Service initialized (No DB tick storage)")

    def _start_background_tasks(self):
        """Start background tasks for maintenance"""

        # Save summaries every 5 minutes
        def periodic_save():
            while True:
                try:
                    threading.Event().wait(300)  # 5 minutes
                    asyncio.run(self._save_periodic_summaries())
                except Exception as e:
                    logger.error(f"Background save error: {e}")

        # Cleanup old data every hour
        def periodic_cleanup():
            while True:
                try:
                    threading.Event().wait(3600)  # 1 hour
                    self._cleanup_old_data()
                except Exception as e:
                    logger.error(f"Background cleanup error: {e}")

        # Start background threads
        save_thread = threading.Thread(target=periodic_save, daemon=True)
        cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)

        save_thread.start()
        cleanup_thread.start()

        logger.info("✅ Background tasks started")

    def _load_sector_mapping(self) -> Dict[str, str]:
        """Load sector mapping for stocks"""
        return {
            # Banking & Financial Services
            "HDFCBANK": "BANKING",
            "ICICIBANK": "BANKING",
            "SBIN": "BANKING",
            "AXISBANK": "BANKING",
            "KOTAKBANK": "BANKING",
            "INDUSINDBK": "BANKING",
            "BAJFINANCE": "FINANCIAL_SERVICES",
            "BAJAJFINSV": "FINANCIAL_SERVICES",
            # IT Services
            "TCS": "IT",
            "INFY": "IT",
            "HCLTECH": "IT",
            "WIPRO": "IT",
            "TECHM": "IT",
            "LTIM": "IT",
            # Oil & Gas
            "RELIANCE": "OIL_GAS",
            "ONGC": "OIL_GAS",
            "BPCL": "OIL_GAS",
            "IOC": "OIL_GAS",
            # Auto
            "MARUTI": "AUTO",
            "TATAMOTORS": "AUTO",
            "M&M": "AUTO",
            "BAJAJ-AUTO": "AUTO",
            "EICHERMOT": "AUTO",
            "HEROMOTOCO": "AUTO",
            "TVSMOTOR": "AUTO",
            # Pharmaceuticals
            "SUNPHARMA": "PHARMA",
            "DRREDDY": "PHARMA",
            "CIPLA": "PHARMA",
            "DIVISLAB": "PHARMA",
            "LUPIN": "PHARMA",
            "APOLLOHOSP": "PHARMA",
            # FMCG
            "HINDUNILVR": "FMCG",
            "ITC": "FMCG",
            "NESTLEIND": "FMCG",
            "BRITANNIA": "FMCG",
            "ASIANPAINT": "FMCG",
            "TITAN": "FMCG",
            # Metals
            "TATASTEEL": "METALS",
            "JSWSTEEL": "METALS",
            "HINDALCO": "METALS",
            "VEDL": "METALS",
            "COALINDIA": "METALS",
            # Infrastructure
            "LT": "INFRASTRUCTURE",
            "NTPC": "POWER",
            "POWERGRID": "POWER",
            "TATAPOWER": "POWER",
            # Indices
            "NIFTY": "INDEX",
            "BANKNIFTY": "INDEX",
            "FINNIFTY": "INDEX",
            "SENSEX": "INDEX",
            "MIDCPNIFTY": "INDEX",
        }

    def process_tick(self, instrument_key: str, data: Dict[str, Any]) -> bool:
        """Process incoming tick - IMPROVED with unified processing"""
        try:
            with self.data_lock:
                # Use unified symbol extraction
                symbol = self._extract_symbol(instrument_key)
                if not symbol:
                    return False

                # Validate required fields
                if not all(key in data for key in ["ltp", "change_percent"]):
                    logger.warning(f"Missing required fields for {instrument_key}")
                    return False

                # Create tick data with better error handling
                try:
                    tick = TickData(
                        instrument_key=instrument_key,
                        symbol=symbol,
                        ltp=float(data.get("ltp", 0)),
                        ltq=int(data.get("ltq", 0)),
                        change=float(data.get("change", 0)),
                        change_percent=float(data.get("change_percent", 0)),
                        volume=int(data.get("volume", 0)),
                        timestamp=datetime.now(),
                        exchange=self._extract_exchange(instrument_key),
                    )
                except (ValueError, TypeError) as e:
                    logger.error(f"Error creating TickData for {instrument_key}: {e}")
                    return False

                # Validate tick data
                if not self._validate_tick(tick):
                    return False

                # Store in memory only
                self.live_data[instrument_key] = tick
                self.tick_history[instrument_key].append(tick)

                # Update daily summary
                self._update_daily_summary(symbol, tick)

                # Update counters
                self.processed_ticks += 1
                self.last_update = datetime.now()

                # Cache in Redis
                if self.redis_available:
                    self._cache_latest_price(instrument_key, tick)

                return True

        except Exception as e:
            logger.error(f"Error processing tick for {instrument_key}: {e}")
            return False

    def _extract_symbol(self, instrument_key: str) -> Optional[str]:
        """Use unified symbol extraction"""
        return market_data_processor.extract_symbol_from_key(instrument_key)

    def _extract_exchange(self, instrument_key: str) -> str:
        """Extract exchange from instrument key"""
        if instrument_key.startswith("NSE"):
            return "NSE"
        elif instrument_key.startswith("BSE"):
            return "BSE"
        elif instrument_key.startswith("MCX"):
            return "MCX"
        return "UNKNOWN"

    def _update_daily_summary(self, symbol: str, tick: TickData):
        """Update daily summary for database storage"""
        try:
            if symbol not in self.daily_summaries:
                # Initialize summary
                self.daily_summaries[symbol] = {
                    "symbol": symbol,
                    "instrument_key": tick.instrument_key,
                    "open_price": tick.ltp,
                    "high_price": tick.ltp,
                    "low_price": tick.ltp,
                    "close_price": tick.ltp,
                    "volume": tick.volume,
                    "total_trades": 1,
                    "avg_price": tick.ltp,
                    "change_percent": tick.change_percent,
                    "sector": self.sector_mapping.get(symbol, "OTHER"),
                    "exchange": tick.exchange,
                }
            else:
                # Update existing summary
                summary = self.daily_summaries[symbol]
                summary["high_price"] = max(summary["high_price"], tick.ltp)
                summary["low_price"] = min(summary["low_price"], tick.ltp)
                summary["close_price"] = tick.ltp  # Latest price
                summary["volume"] = tick.volume  # Latest volume
                summary["total_trades"] += 1
                summary["change_percent"] = tick.change_percent

                # Update moving average
                total_trades = summary["total_trades"]
                summary["avg_price"] = (
                    summary["avg_price"] * (total_trades - 1) + tick.ltp
                ) / total_trades

        except Exception as e:
            logger.error(f"Error updating daily summary for {symbol}: {e}")

    def _cache_latest_price(self, instrument_key: str, tick: TickData):
        """Cache only the latest price in Redis - not all ticks"""
        try:
            # Store latest price with 1 hour TTL
            price_data = {
                "symbol": tick.symbol,
                "ltp": tick.ltp,
                "change_percent": tick.change_percent,
                "volume": tick.volume,
                "timestamp": tick.timestamp.isoformat(),
            }

            self.redis_client.setex(
                f"latest_price:{instrument_key}",
                3600,  # 1 hour TTL
                json.dumps(price_data),
            )

            # Also store in a hash for quick symbol lookup
            self.redis_client.hset("live_prices", tick.symbol, json.dumps(price_data))
            self.redis_client.expire("live_prices", 3600)

        except Exception as e:
            logger.warning(f"Failed to cache price in Redis: {e}")

    async def _save_periodic_summaries(self):
        """Save aggregated summaries to database (not individual ticks)"""
        try:
            if not self.daily_summaries:
                return

            logger.info(f"💾 Saving {len(self.daily_summaries)} daily summaries...")

            # For now, just log the summaries (you can add actual DB saving later)
            # This prevents the database overload while keeping the analytics working

            self.last_db_save = datetime.now()
            logger.info("✅ Daily summaries processed (no DB writes)")

        except Exception as e:
            logger.error(f"❌ Error saving periodic summaries: {e}")

    def _cleanup_old_data(self):
        """Cleanup old in-memory data to prevent memory issues"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=2)

            with self.data_lock:
                # Clean up old ticks from history (keep only recent)
                for symbol in list(self.tick_history.keys()):
                    history = self.tick_history[symbol]
                    # Keep only ticks from last 2 hours
                    recent_ticks = deque(
                        [tick for tick in history if tick.timestamp > cutoff_time],
                        maxlen=500,
                    )
                    self.tick_history[symbol] = recent_ticks

                    # Remove empty histories
                    if not recent_ticks:
                        del self.tick_history[symbol]

                logger.info("✅ Cleaned up old in-memory tick data")

        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")

    def get_top_gainers(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get top gainers from memory data"""
        return self._get_top_movers_data(True, limit)

    def get_top_losers(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get top losers from memory data"""
        return self._get_top_movers_data(False, limit)

    def _get_top_movers_data(self, gainers: bool, limit: int) -> List[Dict[str, Any]]:
        """Get top movers data from memory"""
        with self.data_lock:
            movers = []
            for tick in self.live_data.values():
                if gainers and tick.change_percent > 0:
                    movers.append(self._tick_to_dict(tick))
                elif not gainers and tick.change_percent < 0:
                    movers.append(self._tick_to_dict(tick))

            # Sort appropriately
            movers.sort(key=lambda x: x["change_percent"], reverse=gainers)
            return movers[:limit]

    def _tick_to_dict(self, tick: TickData) -> Dict[str, Any]:
        """Convert tick to dictionary for API response"""
        return {
            "symbol": tick.symbol,
            "instrument_key": tick.instrument_key,
            "ltp": tick.ltp,
            "change": tick.change,
            "change_percent": tick.change_percent,
            "volume": tick.volume,
            "sector": self.sector_mapping.get(tick.symbol, "OTHER"),
            "exchange": tick.exchange,
            "timestamp": tick.timestamp.isoformat(),
        }

    def get_volume_leaders(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get volume leaders with volume ratio calculation"""
        with self.data_lock:
            volume_leaders = []

            for tick in self.live_data.values():
                if tick.volume > 0:
                    # Calculate average volume (simplified)
                    avg_volume = self._get_average_volume(tick.symbol)
                    volume_ratio = tick.volume / avg_volume if avg_volume > 0 else 1.0

                    volume_leaders.append(
                        {
                            "symbol": tick.symbol,
                            "instrument_key": tick.instrument_key,
                            "ltp": tick.ltp,
                            "change_percent": tick.change_percent,
                            "current_volume": tick.volume,
                            "average_volume": avg_volume,
                            "volume_ratio": volume_ratio,
                            "sector": self.sector_mapping.get(tick.symbol, "OTHER"),
                            "exchange": tick.exchange,
                            "timestamp": tick.timestamp.isoformat(),
                        }
                    )

            # Sort by volume
            volume_leaders.sort(key=lambda x: x["current_volume"], reverse=True)
            return volume_leaders[:limit]

    def _get_average_volume(self, symbol: str) -> int:
        """Get average volume for a symbol (simplified)"""
        history = list(self.tick_history.get(symbol, []))
        if len(history) < 10:
            return 100000  # Default average volume

        volumes = [tick.volume for tick in history if tick.volume > 0]
        return int(np.mean(volumes)) if volumes else 100000

    def get_market_sentiment(self) -> Dict[str, Any]:
        """Calculate market sentiment"""
        with self.data_lock:
            if not self.live_data:
                return {}

            gainers = sum(
                1 for tick in self.live_data.values() if tick.change_percent > 0
            )
            losers = sum(
                1 for tick in self.live_data.values() if tick.change_percent < 0
            )
            unchanged = sum(
                1 for tick in self.live_data.values() if tick.change_percent == 0
            )
            total = len(self.live_data)

            # Calculate sector sentiment
            sector_sentiment = defaultdict(
                lambda: {"gainers": 0, "losers": 0, "total": 0}
            )

            for tick in self.live_data.values():
                sector = self.sector_mapping.get(tick.symbol, "OTHER")
                sector_sentiment[sector]["total"] += 1
                if tick.change_percent > 0:
                    sector_sentiment[sector]["gainers"] += 1
                elif tick.change_percent < 0:
                    sector_sentiment[sector]["losers"] += 1

            # Calculate volume sentiment
            total_volume = sum(tick.volume for tick in self.live_data.values())
            volume_weighted_change = sum(
                tick.change_percent * tick.volume
                for tick in self.live_data.values()
                if tick.volume > 0
            )

            avg_change = np.mean(
                [tick.change_percent for tick in self.live_data.values()]
            )

            return {
                "overall": {
                    "total_stocks": total,
                    "gainers": gainers,
                    "losers": losers,
                    "unchanged": unchanged,
                    "gainer_percentage": (gainers / total * 100) if total > 0 else 0,
                    "loser_percentage": (losers / total * 100) if total > 0 else 0,
                    "avg_change": round(avg_change, 2),
                    "sentiment": (
                        "BULLISH"
                        if gainers > losers
                        else "BEARISH" if losers > gainers else "NEUTRAL"
                    ),
                },
                "sector_sentiment": dict(sector_sentiment),
                "volume_sentiment": {
                    "total_volume": total_volume,
                    "volume_weighted_change": (
                        round(volume_weighted_change / total_volume, 2)
                        if total_volume > 0
                        else 0
                    ),
                    "high_volume_gainers": len(
                        [
                            tick
                            for tick in self.live_data.values()
                            if tick.change_percent > 2
                            and tick.volume
                            > self._get_average_volume(tick.symbol) * 1.5
                        ]
                    ),
                },
                "timestamp": datetime.now().isoformat(),
            }

    def get_sector_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get sector-wise performance"""
        with self.data_lock:
            sector_data = defaultdict(
                lambda: {
                    "stocks": [],
                    "avg_change": 0,
                    "total_volume": 0,
                    "gainers": 0,
                    "losers": 0,
                }
            )

            for tick in self.live_data.values():
                sector = self.sector_mapping.get(tick.symbol, "OTHER")

                sector_data[sector]["stocks"].append(
                    {
                        "symbol": tick.symbol,
                        "change_percent": tick.change_percent,
                        "volume": tick.volume,
                        "ltp": tick.ltp,
                    }
                )

                sector_data[sector]["total_volume"] += tick.volume

                if tick.change_percent > 0:
                    sector_data[sector]["gainers"] += 1
                elif tick.change_percent < 0:
                    sector_data[sector]["losers"] += 1

            # Calculate averages
            for sector, data in sector_data.items():
                if data["stocks"]:
                    data["avg_change"] = np.mean(
                        [s["change_percent"] for s in data["stocks"]]
                    )
                    data["stock_count"] = len(data["stocks"])

            return dict(sector_data)

    def get_live_market_data(self) -> Dict[str, Any]:
        """Get all live market data"""
        with self.data_lock:
            return {
                instrument_key: tick.to_dict()
                for instrument_key, tick in self.live_data.items()
            }

    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        with self.data_lock:
            uptime = (datetime.now() - self.start_time).total_seconds()

            return {
                "processed_ticks": self.processed_ticks,
                "active_instruments": len(self.live_data),
                "uptime_seconds": uptime,
                "ticks_per_second": self.processed_ticks / uptime if uptime > 0 else 0,
                "last_update": (
                    self.last_update.isoformat() if self.last_update else None
                ),
                "last_db_save": (
                    self.last_db_save.isoformat() if self.last_db_save else None
                ),
                "redis_available": self.redis_available,
                "memory_usage": {
                    "live_data_size": len(self.live_data),
                    "history_size": sum(
                        len(hist) for hist in self.tick_history.values()
                    ),
                    "daily_summaries": len(self.daily_summaries),
                },
                "storage_strategy": "memory_only_with_periodic_summaries",
            }

    def _validate_tick(self, tick: TickData) -> bool:
        """Validate tick data is reasonable"""
        # Price validation
        if tick.ltp <= 0 or tick.ltp > 500000:
            logger.warning(f"Invalid LTP for {tick.symbol}: {tick.ltp}")
            return False

        # Change percentage validation
        if abs(tick.change_percent) > 20:
            logger.warning(f"Extreme change% for {tick.symbol}: {tick.change_percent}%")
            return False

        # Volume validation
        if tick.volume < 0:
            logger.warning(f"Invalid volume for {tick.symbol}: {tick.volume}")
            return False


# Global instance management
_queue_service_instance = None
_queue_lock = threading.Lock()


def get_market_queue_service() -> MarketDataQueueService:
    """Get singleton instance of market queue service"""
    global _queue_service_instance

    with _queue_lock:
        if _queue_service_instance is None:
            _queue_service_instance = MarketDataQueueService()
        return _queue_service_instance


def initialize_queue_service() -> MarketDataQueueService:
    """Initialize the queue service and return instance"""
    logger.info("🔧 Initializing Market Data Queue Service...")
    service = get_market_queue_service()
    logger.info("✅ Market Data Queue Service initialized successfully")
    return service


# Alternative function names for backward compatibility
def get_optimized_queue_service() -> MarketDataQueueService:
    """Alias for get_market_queue_service"""
    return get_market_queue_service()


def init_queue_service() -> MarketDataQueueService:
    """Alias for initialize_queue_service"""
    return initialize_queue_service()
