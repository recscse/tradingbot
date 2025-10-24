import asyncio
import logging
from datetime import datetime
from threading import RLock
from typing import Dict, List, Optional
import numpy as np
from numba import njit


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# -----------------------------
# Breakout Signal Definition
# -----------------------------
class BreakoutSignal:
    def __init__(
        self,
        instrument: str,
        type_: str,
        price: float,
        volume: float,
        timestamp: datetime = None,
    ):
        self.instrument = instrument
        self.type = type_
        self.price = price
        self.volume = volume
        self.timestamp = timestamp or datetime.now()

    def to_dict(self):
        return {
            "instrument": self.instrument,
            "type": self.type,
            "price": self.price,
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat(),
        }


# -----------------------------
# Vectorized Breakout Functions
# -----------------------------
@njit
def fast_volume_breakout_check(price_arr, volume_arr, volume_threshold):
    return volume_arr[-1] > volume_threshold


@njit
def fast_momentum_breakout_check(price_arr, threshold):
    return price_arr[-1] > price_arr[-2] * (1 + threshold)


@njit
def fast_resistance_breakout_check(price_arr, resistance_level):
    return price_arr[-1] > resistance_level


@njit
def fast_volatility_calculation(price_arr):
    return np.std(price_arr)


# -----------------------------
# Ring Buffer for Instrument Data
# -----------------------------
class RingBufferStorage:
    def __init__(self, history_len: int = 50):
        self.history_len = history_len
        self.storage: Dict[str, Dict[str, np.ndarray]] = {}

    def update_data(self, instrument: str, price: float, volume: float):
        if instrument not in self.storage:
            self.storage[instrument] = {
                "price": np.zeros(self.history_len, dtype=np.float64),
                "volume": np.zeros(self.history_len, dtype=np.float64),
                "pos": 0,
                "filled": 0,
            }

        buf = self.storage[instrument]
        pos = buf["pos"]
        buf["price"][pos] = price
        buf["volume"][pos] = volume
        buf["pos"] = (pos + 1) % self.history_len
        buf["filled"] = min(buf["filled"] + 1, self.history_len)

    def get_data(self, instrument: str):
        if instrument not in self.storage or self.storage[instrument]["filled"] == 0:
            return None, None
        buf = self.storage[instrument]
        filled = buf["filled"]
        pos = buf["pos"]

        # Get data in correct order (oldest to newest)
        if filled < self.history_len:
            # Buffer not full yet, just return filled portion
            price_data = buf["price"][:filled]
            volume_data = buf["volume"][:filled]
        else:
            # Buffer is full, need to handle wrap-around
            price_data = np.concatenate((buf["price"][pos:], buf["price"][:pos]))
            volume_data = np.concatenate((buf["volume"][pos:], buf["volume"][:pos]))

        return price_data, volume_data


# -----------------------------
# Enhanced Breakout Engine
# -----------------------------
class EnhancedBreakoutEngine:
    def __init__(
        self,
        storage: RingBufferStorage,
        unified_manager,
        centralized_manager,
        min_volume: float = 1000,
        min_price: float = 1,
        momentum_threshold: float = 0.01,
    ):
        self.storage = storage
        self.unified_manager = unified_manager
        self.centralized_manager = centralized_manager
        self.min_volume = min_volume
        self.min_price = min_price
        self.momentum_threshold = momentum_threshold

        self.data_lock = RLock()
        self.active = True

    # -----------------------------
    # Feed Processing
    # -----------------------------
    def _process_single_update(self, instrument: str, price: float, volume: float):
        if price < self.min_price or volume < self.min_volume:
            return
        with self.data_lock:
            self.storage.update_data(instrument, price, volume)

    def _process_feed_batch(self, feed_batch: Dict[str, Dict[str, float]]):
        for instrument, data in feed_batch.items():
            self._process_single_update(instrument, data["price"], data["volume"])

    # -----------------------------
    # Breakout Detection
    # -----------------------------
    def _detect_breakouts_vectorized(self) -> List[BreakoutSignal]:
        signals = []
        with self.data_lock:
            for instrument in self.storage.storage.keys():
                price_arr, volume_arr = self.storage.get_data(instrument)
                if price_arr is None or len(price_arr) < 2:
                    continue

                # Volume breakout check
                if fast_volume_breakout_check(price_arr, volume_arr, self.min_volume):
                    signals.append(
                        BreakoutSignal(
                            instrument, "volume", price_arr[-1], volume_arr[-1]
                        )
                    )

                # Momentum breakout check (needs at least 2 data points)
                if len(price_arr) >= 2:
                    if fast_momentum_breakout_check(price_arr, self.momentum_threshold):
                        signals.append(
                            BreakoutSignal(
                                instrument, "momentum", price_arr[-1], volume_arr[-1]
                            )
                        )

                # Resistance breakout check (needs at least 2 data points)
                if len(price_arr) >= 2:
                    resistance_level = np.max(price_arr[:-1])
                    if fast_resistance_breakout_check(price_arr, resistance_level):
                        signals.append(
                            BreakoutSignal(
                                instrument, "resistance", price_arr[-1], volume_arr[-1]
                            )
                        )

        return signals

    # -----------------------------
    # Broadcast
    # -----------------------------
    async def _broadcast_breakouts(self, signals: List[BreakoutSignal]):
        """
        Broadcast breakout signals to connected clients.

        Uses the realtime market engine's event emitter to broadcast breakout signals.
        This ensures signals are sent through the unified WebSocket system to all
        subscribed clients.

        Args:
            signals: List of BreakoutSignal objects to broadcast
        """
        for sig in signals:
            data = sig.to_dict()
            try:
                # Get market engine and emit through its event system
                from services.realtime_market_engine import get_market_engine

                engine = get_market_engine()
                if engine and hasattr(engine, "event_emitter"):
                    # Emit through market engine's event emitter
                    # This will trigger the on_breakout_signal listener in unified_websocket_routes
                    engine.event_emitter.emit("breakout_signal", data)
                    logger.debug(
                        f"Emitted breakout signal via market engine: {data['instrument']} "
                        f"(type: {data['type']}, price: {data['price']})"
                    )
                else:
                    logger.warning(
                        "Market engine not available or missing event_emitter - breakout signal not sent"
                    )
            except Exception as e:
                logger.error(f"Failed to broadcast breakout signal for {data.get('instrument', 'unknown')}: {e}")
                import traceback
                logger.debug(traceback.format_exc())

    # -----------------------------
    # Public Update Method
    # -----------------------------
    async def update_market_data(self, feed_batch: Dict[str, Dict[str, float]]):
        """
        Update market data and detect breakouts.

        Args:
            feed_batch: Dictionary of instrument_key to market data
                Format: {
                    instrument_key: {
                        "ltp": float,
                        "volume": int,
                        ...
                    }
                }
        """
        self._process_feed_batch(feed_batch)
        signals = self._detect_breakouts_vectorized()
        if signals:
            await self._broadcast_breakouts(signals)

    def on_price_update(self, price_data: Dict[str, Dict[str, any]]):
        """
        Synchronous callback for realtime market engine price updates.

        This method is called by the realtime_market_engine event emitter
        when new price data is available. It converts the data format and
        processes it for breakout detection.

        Args:
            price_data: Dictionary of instrument_key to price data from market engine
                Format: {
                    instrument_key: {
                        "ltp": float,
                        "volume": int,
                        "high": float,
                        "low": float,
                        ...
                    }
                }
        """
        try:
            # Convert market engine format to breakout engine format
            feed_batch = {}
            for instrument_key, data in price_data.items():
                if isinstance(data, dict):
                    feed_batch[instrument_key] = {
                        "price": float(data.get("ltp", 0)),
                        "volume": float(data.get("volume", 0)),
                    }

            # Process data (synchronous version)
            if feed_batch:
                self._process_feed_batch(feed_batch)

                # Detect breakouts
                signals = self._detect_breakouts_vectorized()

                # Schedule async broadcast if signals found
                if signals:
                    import asyncio

                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(self._broadcast_breakouts(signals))
                        else:
                            asyncio.run(self._broadcast_breakouts(signals))
                    except RuntimeError:
                        # If no event loop, log warning
                        logger.warning(
                            f"Cannot broadcast {len(signals)} breakout signals - no event loop"
                        )

        except Exception as e:
            logger.error(f"Error in price update callback: {e}")
            import traceback

            logger.error(traceback.format_exc())

    # -----------------------------
    # Async Loops
    # -----------------------------
    async def run_engine(self, feed_generator, update_interval: float = 0.1):
        while self.active:
            feed_batch = await feed_generator()
            await self.update_market_data(feed_batch)
            await asyncio.sleep(update_interval)

    def stop(self):
        self.active = False


# -----------------------------
# Singleton Instance Management
# -----------------------------
_breakout_engine_instance: Optional[EnhancedBreakoutEngine] = None


def get_breakout_engine() -> Optional[EnhancedBreakoutEngine]:
    """
    Get the global breakout engine instance.

    Returns:
        EnhancedBreakoutEngine instance or None if not initialized
    """
    return _breakout_engine_instance


def initialize_breakout_engine(
    unified_manager=None,
    centralized_manager=None,
    min_volume: float = 1000,
    min_price: float = 1,
    momentum_threshold: float = 0.01,
    history_len: int = 50,
) -> EnhancedBreakoutEngine:
    """
    Initialize the global breakout engine instance.

    Args:
        unified_manager: Unified WebSocket manager for broadcasting
        centralized_manager: Centralized WebSocket manager for broadcasting
        min_volume: Minimum volume threshold for breakout detection
        min_price: Minimum price threshold for instrument filtering
        momentum_threshold: Momentum breakout threshold (default 1%)
        history_len: Number of historical data points to maintain

    Returns:
        Initialized EnhancedBreakoutEngine instance
    """
    global _breakout_engine_instance

    if _breakout_engine_instance is not None:
        logger.info("Breakout engine already initialized, returning existing instance")
        return _breakout_engine_instance

    # Create storage
    storage = RingBufferStorage(history_len=history_len)

    # Create engine instance
    _breakout_engine_instance = EnhancedBreakoutEngine(
        storage=storage,
        unified_manager=unified_manager,
        centralized_manager=centralized_manager,
        min_volume=min_volume,
        min_price=min_price,
        momentum_threshold=momentum_threshold,
    )

    logger.info(
        f"✅ Enhanced Breakout Engine initialized with {history_len} history length"
    )
    return _breakout_engine_instance


def connect_to_market_engine():
    """
    Connect the breakout engine to the realtime market engine.

    This function registers the breakout engine as a listener for
    price updates from the realtime market engine.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        from services.realtime_market_engine import get_market_engine

        market_engine = get_market_engine()
        breakout_engine = get_breakout_engine()

        if not breakout_engine:
            logger.error(
                "Breakout engine not initialized - call initialize_breakout_engine() first"
            )
            return False

        if not market_engine:
            logger.error("Realtime market engine not available")
            return False

        # Register callback for price updates
        market_engine.event_emitter.on("price_update", breakout_engine.on_price_update)

        logger.info("✅ Breakout engine connected to realtime market engine")
        logger.info("📊 Breakout detection will run on every price update")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to connect breakout engine to market engine: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


def get_breakout_stats() -> Dict[str, any]:
    """
    Get breakout engine statistics.

    Returns:
        Dictionary with breakout engine stats
    """
    engine = get_breakout_engine()
    if not engine:
        return {"initialized": False, "error": "Breakout engine not initialized"}

    try:
        return {
            "initialized": True,
            "active": engine.active,
            "instruments_tracked": len(engine.storage.storage),
            "min_volume": engine.min_volume,
            "min_price": engine.min_price,
            "momentum_threshold": engine.momentum_threshold,
        }
    except Exception as e:
        return {"initialized": True, "error": str(e)}
