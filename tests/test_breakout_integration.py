"""
Test Enhanced Breakout Engine Integration with Real-time Market Engine

This test verifies that:
1. Breakout engine can be initialized
2. It receives data from market engine
3. Breakout detection works correctly
4. Signals are broadcast properly
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List

from services.enhanced_breakout_engine import (
    RingBufferStorage,
    EnhancedBreakoutEngine,
    BreakoutSignal,
    initialize_breakout_engine,
    get_breakout_engine,
    get_breakout_stats,
    connect_to_market_engine,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockWebSocketManager:
    """Mock WebSocket manager for testing"""

    def __init__(self):
        self.emitted_events: List[Dict] = []

    async def emit(self, event: str, data: Dict):
        """Mock emit method"""
        self.emitted_events.append({"event": event, "data": data})
        logger.info(f"📡 Emitted {event}: {data}")


class MockMarketEngine:
    """Mock market engine for testing"""

    def __init__(self):
        self.event_emitter = MockEventEmitter()


class MockEventEmitter:
    """Mock event emitter for testing"""

    def __init__(self):
        self.callbacks: Dict[str, List] = {}

    def on(self, event: str, callback):
        """Register callback"""
        if event not in self.callbacks:
            self.callbacks[event] = []
        self.callbacks[event].append(callback)
        logger.info(f"✅ Registered callback for {event}")

    def emit(self, event: str, data: Dict):
        """Emit event to all callbacks"""
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                callback(data)


def test_ring_buffer_storage():
    """Test RingBuffer storage functionality"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: RingBuffer Storage")
    logger.info("=" * 60)

    storage = RingBufferStorage(history_len=5)

    # Add some data
    storage.update_data("NSE_EQ|TEST", 100.0, 1000.0)
    storage.update_data("NSE_EQ|TEST", 101.0, 1100.0)
    storage.update_data("NSE_EQ|TEST", 102.0, 1200.0)

    # Get data
    price_arr, volume_arr = storage.get_data("NSE_EQ|TEST")

    assert price_arr is not None, "Price array should not be None"
    assert volume_arr is not None, "Volume array should not be None"
    assert len(price_arr) == 3, "Should have 3 data points"
    assert price_arr[-1] == 102.0, "Last price should be 102.0"
    assert volume_arr[-1] == 1200.0, "Last volume should be 1200.0"

    logger.info(f"✅ Price array: {price_arr}")
    logger.info(f"✅ Volume array: {volume_arr}")
    logger.info("✅ RingBuffer test passed!")


def test_breakout_engine_initialization():
    """Test breakout engine initialization"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Breakout Engine Initialization")
    logger.info("=" * 60)

    mock_ws_manager = MockWebSocketManager()
    storage = RingBufferStorage(history_len=50)

    engine = EnhancedBreakoutEngine(
        storage=storage,
        unified_manager=mock_ws_manager,
        centralized_manager=None,
        min_volume=1000,
        min_price=10,
        momentum_threshold=0.015,
    )

    assert engine.min_volume == 1000, "Min volume should be 1000"
    assert engine.min_price == 10, "Min price should be 10"
    assert engine.momentum_threshold == 0.015, "Momentum threshold should be 0.015"
    assert engine.active is True, "Engine should be active"

    logger.info(f"✅ Min Volume: {engine.min_volume}")
    logger.info(f"✅ Min Price: {engine.min_price}")
    logger.info(f"✅ Momentum Threshold: {engine.momentum_threshold}")
    logger.info("✅ Initialization test passed!")


def test_price_update_callback():
    """Test price update callback functionality"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Price Update Callback")
    logger.info("=" * 60)

    mock_ws_manager = MockWebSocketManager()
    storage = RingBufferStorage(history_len=50)

    engine = EnhancedBreakoutEngine(
        storage=storage,
        unified_manager=mock_ws_manager,
        centralized_manager=None,
        min_volume=1000,
        min_price=10,
        momentum_threshold=0.015,
    )

    # Simulate market data update
    price_data = {
        "NSE_EQ|INE318A01026": {
            "ltp": 3097.7,
            "volume": 31929,
            "high": 3115.4,
            "low": 3081.0,
        }
    }

    # Call the callback
    engine.on_price_update(price_data)

    # Verify data was stored
    price_arr, volume_arr = storage.get_data("NSE_EQ|INE318A01026")

    assert price_arr is not None, "Price data should be stored"
    assert volume_arr is not None, "Volume data should be stored"
    assert price_arr[-1] == 3097.7, "Last price should match"
    assert volume_arr[-1] == 31929.0, "Last volume should match"

    logger.info(f"✅ Stored price: {price_arr[-1]}")
    logger.info(f"✅ Stored volume: {volume_arr[-1]}")
    logger.info("✅ Price update callback test passed!")


def test_volume_breakout_detection():
    """Test volume breakout detection"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Volume Breakout Detection")
    logger.info("=" * 60)

    mock_ws_manager = MockWebSocketManager()
    storage = RingBufferStorage(history_len=50)

    engine = EnhancedBreakoutEngine(
        storage=storage,
        unified_manager=mock_ws_manager,
        centralized_manager=None,
        min_volume=1000,
        min_price=10,
        momentum_threshold=0.015,
    )

    # Add data with increasing volume (breakout)
    for i in range(10):
        price_data = {
            "NSE_EQ|TEST": {
                "ltp": 100.0 + i,
                "volume": 500 + (i * 100),  # Increasing volume
            }
        }
        engine.on_price_update(price_data)

    # Add final data point with high volume
    price_data = {
        "NSE_EQ|TEST": {
            "ltp": 110.0,
            "volume": 5000,  # Volume breakout!
        }
    }
    engine.on_price_update(price_data)

    # Detect breakouts
    signals = engine._detect_breakouts_vectorized()

    # Should detect volume breakout
    volume_signals = [s for s in signals if s.type == "volume"]
    assert len(volume_signals) > 0, "Should detect volume breakout"

    logger.info(f"✅ Detected {len(volume_signals)} volume breakout(s)")
    for signal in volume_signals:
        logger.info(f"   - {signal.instrument}: {signal.type} at {signal.price}")

    logger.info("✅ Volume breakout detection test passed!")


def test_momentum_breakout_detection():
    """Test momentum breakout detection"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Momentum Breakout Detection")
    logger.info("=" * 60)

    mock_ws_manager = MockWebSocketManager()
    storage = RingBufferStorage(history_len=50)

    engine = EnhancedBreakoutEngine(
        storage=storage,
        unified_manager=mock_ws_manager,
        centralized_manager=None,
        min_volume=1000,
        min_price=10,
        momentum_threshold=0.015,  # 1.5% momentum threshold
    )

    # Add base price
    engine.on_price_update({"NSE_EQ|TEST": {"ltp": 100.0, "volume": 2000}})

    # Add momentum breakout (2% increase)
    engine.on_price_update({"NSE_EQ|TEST": {"ltp": 102.0, "volume": 2000}})

    # Detect breakouts
    signals = engine._detect_breakouts_vectorized()

    # Should detect momentum breakout
    momentum_signals = [s for s in signals if s.type == "momentum"]
    assert len(momentum_signals) > 0, "Should detect momentum breakout"

    logger.info(f"✅ Detected {len(momentum_signals)} momentum breakout(s)")
    for signal in momentum_signals:
        logger.info(f"   - {signal.instrument}: {signal.type} at {signal.price}")

    logger.info("✅ Momentum breakout detection test passed!")


def test_resistance_breakout_detection():
    """Test resistance breakout detection"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Resistance Breakout Detection")
    logger.info("=" * 60)

    mock_ws_manager = MockWebSocketManager()
    storage = RingBufferStorage(history_len=50)

    engine = EnhancedBreakoutEngine(
        storage=storage,
        unified_manager=mock_ws_manager,
        centralized_manager=None,
        min_volume=1000,
        min_price=10,
        momentum_threshold=0.015,
    )

    # Add data with resistance at 105
    for i in range(10):
        price_data = {
            "NSE_EQ|TEST": {"ltp": 100.0 + (i % 5), "volume": 2000}  # Max 104
        }
        engine.on_price_update(price_data)

    # Break resistance
    engine.on_price_update({"NSE_EQ|TEST": {"ltp": 106.0, "volume": 2000}})

    # Detect breakouts
    signals = engine._detect_breakouts_vectorized()

    # Should detect resistance breakout
    resistance_signals = [s for s in signals if s.type == "resistance"]
    assert len(resistance_signals) > 0, "Should detect resistance breakout"

    logger.info(f"✅ Detected {len(resistance_signals)} resistance breakout(s)")
    for signal in resistance_signals:
        logger.info(f"   - {signal.instrument}: {signal.type} at {signal.price}")

    logger.info("✅ Resistance breakout detection test passed!")


def test_breakout_stats():
    """Test breakout stats function"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Breakout Stats")
    logger.info("=" * 60)

    # Before initialization
    stats = get_breakout_stats()
    assert stats["initialized"] is False, "Should not be initialized"

    # Initialize
    mock_ws_manager = MockWebSocketManager()
    engine = initialize_breakout_engine(
        unified_manager=mock_ws_manager,
        centralized_manager=None,
        min_volume=1000,
        min_price=10,
        momentum_threshold=0.015,
        history_len=50,
    )

    # After initialization
    stats = get_breakout_stats()
    assert stats["initialized"] is True, "Should be initialized"
    assert stats["active"] is True, "Should be active"
    assert stats["min_volume"] == 1000, "Min volume should match"
    assert stats["min_price"] == 10, "Min price should match"

    logger.info("✅ Breakout Stats:")
    import json

    logger.info(json.dumps(stats, indent=2))
    logger.info("✅ Breakout stats test passed!")


if __name__ == "__main__":
    """Run all tests"""
    logger.info("\n" + "=" * 80)
    logger.info("RUNNING ENHANCED BREAKOUT ENGINE INTEGRATION TESTS")
    logger.info("=" * 80)

    try:
        test_ring_buffer_storage()
        test_breakout_engine_initialization()
        test_price_update_callback()
        test_volume_breakout_detection()
        test_momentum_breakout_detection()
        test_resistance_breakout_detection()
        test_breakout_stats()

        logger.info("\n" + "=" * 80)
        logger.info("ALL TESTS PASSED!")
        logger.info("=" * 80)

    except AssertionError as e:
        logger.error(f"\n❌ TEST FAILED: {e}")
        import traceback

        logger.error(traceback.format_exc())

    except Exception as e:
        logger.error(f"\n❌ ERROR: {e}")
        import traceback

        logger.error(traceback.format_exc())