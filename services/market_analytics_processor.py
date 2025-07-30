# services/market_analytics_processor.py
import asyncio
import logging
from typing import Dict, List, Any, Optional, Set, Callable
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class MarketAnalyticsProcessor:
    """
    Efficient market analytics processor that subscribes to registry events
    and computes analytics only when needed
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        # Cache for computed analytics
        self.cache = {
            "top_gainers": [],
            "top_losers": [],
            "volume_leaders": [],
            "market_sentiment": {},
            "last_update": None,
        }

        # Flag to track if we need to recompute
        self.needs_update = {
            "top_gainers": True,
            "top_losers": True,
            "volume_leaders": True,
            "market_sentiment": True,
        }

        # Settings
        self.update_interval = 60  # seconds
        self.min_update_interval = 10  # seconds
        self.last_computation = {
            "top_gainers": None,
            "top_losers": None,
            "volume_leaders": None,
            "market_sentiment": None,
        }

        # Callback registration
        self.callbacks = {}
        self.background_tasks = set()

        # Initialize
        self._initialized = True
        self._connect_to_registry()
        logger.info("✅ Market analytics processor initialized")

    def _connect_to_registry(self):
        """Connect to instrument registry"""
        try:
            from services.instrument_registry import instrument_registry

            # Subscribe to registry events
            instrument_registry.subscribe("price_update", self._on_price_update)
            instrument_registry.subscribe("index_update", self._on_index_update)

            # Start background task for periodic computation
            # task = asyncio.create_task(self._periodic_computation())
            # self.background_tasks.add(task)
            # task.add_done_callback(lambda t: self.background_tasks.discard(t))

            logger.info("✅ Connected to instrument registry")

        except ImportError:
            logger.warning("⚠️ Instrument registry not available")
        except Exception as e:
            logger.warning(f"⚠️ Error connecting to registry: {e}")

    async def start_background_tasks(self):
        """Start background tasks in proper async context"""
        try:
            # Start background task for periodic computation
            task = asyncio.create_task(self._periodic_computation())
            self.background_tasks.add(task)
            task.add_done_callback(lambda t: self.background_tasks.discard(t))
            logger.info("✅ Analytics processor background tasks started")
        except Exception as e:
            logger.error(f"❌ Error starting background tasks: {e}")

    async def _on_price_update(self, data):
        """Handle price updates from registry"""
        # Mark data as needing update
        for key in self.needs_update:
            self.needs_update[key] = True

        # Always update market sentiment immediately as it's lightweight
        if self._should_compute("market_sentiment"):
            self.cache["market_sentiment"] = self._compute_market_sentiment()
            self.last_computation["market_sentiment"] = datetime.now()

            # Notify subscribers
            self._notify("market_sentiment", self.cache["market_sentiment"])

    async def _on_index_update(self, data):
        """Handle index updates"""
        # Update sentiment immediately for indices
        self.cache["market_sentiment"] = self._compute_market_sentiment()
        self.last_computation["market_sentiment"] = datetime.now()

        # Notify subscribers
        self._notify(
            "index_update",
            {
                "index_data": data.get("data", {}),
                "market_sentiment": self.cache["market_sentiment"],
            },
        )

    def _should_compute(self, key):
        """Determine if we should compute this analytics now"""
        if not self.needs_update[key]:
            return False

        last_time = self.last_computation[key]
        if last_time is None:
            return True

        # Don't compute too frequently
        time_since_last = (datetime.now() - last_time).total_seconds()
        return time_since_last >= self.min_update_interval

    async def _periodic_computation(self):
        """Periodically compute analytics"""
        while True:
            try:
                # Wait a bit to start
                await asyncio.sleep(5)

                # Compute each analytics if needed
                updates = {}

                if self.needs_update["top_gainers"] and self._should_compute(
                    "top_gainers"
                ):
                    self.cache["top_gainers"] = self._compute_top_gainers(20)
                    self.last_computation["top_gainers"] = datetime.now()
                    self.needs_update["top_gainers"] = False
                    updates["top_gainers"] = self.cache["top_gainers"]

                if self.needs_update["top_losers"] and self._should_compute(
                    "top_losers"
                ):
                    self.cache["top_losers"] = self._compute_top_losers(20)
                    self.last_computation["top_losers"] = datetime.now()
                    self.needs_update["top_losers"] = False
                    updates["top_losers"] = self.cache["top_losers"]

                if self.needs_update["volume_leaders"] and self._should_compute(
                    "volume_leaders"
                ):
                    self.cache["volume_leaders"] = self._compute_volume_leaders(20)
                    self.last_computation["volume_leaders"] = datetime.now()
                    self.needs_update["volume_leaders"] = False
                    updates["volume_leaders"] = self.cache["volume_leaders"]

                if self.needs_update["market_sentiment"] and self._should_compute(
                    "market_sentiment"
                ):
                    self.cache["market_sentiment"] = self._compute_market_sentiment()
                    self.last_computation["market_sentiment"] = datetime.now()
                    self.needs_update["market_sentiment"] = False
                    updates["market_sentiment"] = self.cache["market_sentiment"]

                # Update timestamp
                if updates:
                    self.cache["last_update"] = datetime.now().isoformat()
                    updates["last_update"] = self.cache["last_update"]

                    # Notify subscribers about full update
                    self._notify("analytics_update", updates)

                    logger.info(f"📊 Computed analytics: {', '.join(updates.keys())}")

                # Wait for next update
                await asyncio.sleep(self.update_interval)

            except Exception as e:
                logger.error(f"❌ Error in periodic computation: {e}")
                await asyncio.sleep(self.update_interval)

    def _compute_top_gainers(self, limit=20):
        """Compute top gainers"""
        try:
            from services.instrument_registry import instrument_registry

            # Get top gainers from registry
            return instrument_registry.get_top_gainers(limit)

        except Exception as e:
            logger.error(f"❌ Error computing top gainers: {e}")
            return []

    def _compute_top_losers(self, limit=20):
        """Compute top losers"""
        try:
            from services.instrument_registry import instrument_registry

            # Get top losers from registry
            return instrument_registry.get_top_losers(limit)

        except Exception as e:
            logger.error(f"❌ Error computing top losers: {e}")
            return []

    def _compute_volume_leaders(self, limit=20):
        """Compute volume leaders"""
        try:
            from services.instrument_registry import instrument_registry

            # Get all spot prices
            volume_data = []
            for symbol in instrument_registry._symbols_map:
                # Skip indices
                if symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]:
                    continue

                spot_data = instrument_registry.get_spot_price(symbol)
                if spot_data and spot_data.get("volume"):
                    volume_data.append(spot_data)

            # Sort by volume
            volume_data.sort(key=lambda x: x.get("volume", 0) or 0, reverse=True)
            return volume_data[:limit]

        except Exception as e:
            logger.error(f"❌ Error computing volume leaders: {e}")
            return []

    def _compute_market_sentiment(self):
        """Compute market sentiment"""
        try:
            from services.instrument_registry import instrument_registry

            # Get indices data
            nifty = instrument_registry.get_spot_price("NIFTY")
            banknifty = instrument_registry.get_spot_price("BANKNIFTY")

            # Get market breadth
            gainers_count = 0
            losers_count = 0
            unchanged_count = 0
            total_count = 0

            for symbol in instrument_registry._symbols_map:
                # Skip indices
                if symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]:
                    continue

                spot_data = instrument_registry.get_spot_price(symbol)
                if spot_data and spot_data.get("change_percent") is not None:
                    total_count += 1
                    change_raw = spot_data.get("change_percent", 0)
                    try:
                        change = float(change_raw)
                    except:
                        logger.warning(
                            f"Invalid change_percent value '{change_raw}' for symbol {symbol}, treating as 0."
                        )
                        change = 0.0

                    if change > 0:
                        gainers_count += 1
                    elif change < 0:
                        losers_count += 1
                    else:
                        unchanged_count += 1

            # Calculate advance-decline ratio
            adv_dec_ratio = (
                gainers_count / losers_count if losers_count > 0 else float("inf")
            )

            # Determine sentiment
            sentiment = "neutral"
            if adv_dec_ratio > 1.5:
                sentiment = "strongly_bullish"
            elif adv_dec_ratio > 1.1:
                sentiment = "bullish"
            elif adv_dec_ratio < 0.5:
                sentiment = "strongly_bearish"
            elif adv_dec_ratio < 0.9:
                sentiment = "bearish"

            return {
                "overall": sentiment,
                "breadth": {
                    "total": total_count,
                    "gainers": gainers_count,
                    "losers": losers_count,
                    "unchanged": unchanged_count,
                    "adv_dec_ratio": (
                        round(adv_dec_ratio, 2)
                        if adv_dec_ratio != float("inf")
                        else None
                    ),
                },
                "nifty": {
                    "price": nifty.get("last_price") if nifty else None,
                    "change": nifty.get("change") if nifty else None,
                    "change_percent": nifty.get("change_percent") if nifty else None,
                },
                "banknifty": {
                    "price": banknifty.get("last_price") if banknifty else None,
                    "change": banknifty.get("change") if banknifty else None,
                    "change_percent": (
                        banknifty.get("change_percent") if banknifty else None
                    ),
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Error computing market sentiment: {e}")
            return {"overall": "unknown", "error": str(e)}

    def register_callback(self, event: str, callback: Callable):
        """Register a callback for notifications"""
        if event not in self.callbacks:
            self.callbacks[event] = []
        self.callbacks[event].append(callback)
        return True

    def unregister_callback(self, event: str, callback: Callable):
        """Unregister a callback"""
        if event in self.callbacks and callback in self.callbacks[event]:
            self.callbacks[event].remove(callback)
            return True
        return False

    def _notify(self, event: str, data: Any):
        """Notify all subscribers for an event"""
        if event not in self.callbacks:
            return

        for callback in self.callbacks[event]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    task = asyncio.create_task(callback(data))
                    self.background_tasks.add(task)
                    task.add_done_callback(lambda t: self.background_tasks.discard(t))
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"❌ Error in callback for {event}: {e}")

    # PUBLIC API

    def get_top_gainers_losers(self, limit=10):
        """Get top gainers and losers"""
        return {
            "gainers": self.cache["top_gainers"][:limit],
            "losers": self.cache["top_losers"][:limit],
            "timestamp": datetime.now().isoformat(),
        }

    def get_volume_leaders(self, limit=10):
        """Get volume leaders"""
        return {
            "volume_leaders": self.cache["volume_leaders"][:limit],
            "timestamp": datetime.now().isoformat(),
        }

    def get_market_sentiment(self):
        """Get market sentiment"""
        return self.cache["market_sentiment"]

    def get_all_analytics(self):
        """Get all analytics data"""
        return {
            "top_gainers": self.cache["top_gainers"][:10],
            "top_losers": self.cache["top_losers"][:10],
            "volume_leaders": self.cache["volume_leaders"][:10],
            "market_sentiment": self.cache["market_sentiment"],
            "last_update": self.cache["last_update"],
            "timestamp": datetime.now().isoformat(),
        }


# Create singleton instance
market_analytics_processor = MarketAnalyticsProcessor()
