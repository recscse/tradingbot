import asyncio
import logging
from datetime import datetime
from threading import RLock
from typing import Dict, List
import numpy as np
from numba import njit


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
        price_data = np.concatenate(
            (
                buf["price"][pos : pos + filled],
                buf["price"][: max(0, filled - (self.history_len - pos))],
            )
        )
        volume_data = np.concatenate(
            (
                buf["volume"][pos : pos + filled],
                buf["volume"][: max(0, filled - (self.history_len - pos))],
            )
        )
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
                if price_arr is None:
                    continue

                if fast_volume_breakout_check(price_arr, volume_arr, self.min_volume):
                    signals.append(
                        BreakoutSignal(
                            instrument, "volume", price_arr[-1], volume_arr[-1]
                        )
                    )

                if fast_momentum_breakout_check(price_arr, self.momentum_threshold):
                    signals.append(
                        BreakoutSignal(
                            instrument, "momentum", price_arr[-1], volume_arr[-1]
                        )
                    )

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
        for sig in signals:
            data = sig.to_dict()
            try:
                await self.unified_manager.emit("breakout_signal", data)
            except Exception:
                try:
                    await self.centralized_manager.emit("breakout_signal", data)
                except Exception:
                    logging.warning(f"Failed to broadcast signal: {data}")

    # -----------------------------
    # Public Update Method
    # -----------------------------
    async def update_market_data(self, feed_batch: Dict[str, Dict[str, float]]):
        self._process_feed_batch(feed_batch)
        signals = self._detect_breakouts_vectorized()
        if signals:
            await self._broadcast_breakouts(signals)

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
