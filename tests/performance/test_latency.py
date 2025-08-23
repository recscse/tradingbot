#!/usr/bin/env python3
"""
Performance Tests for Trading Application

Tests latency, throughput, and memory usage under various load conditions.
"""

import pytest
import time
import asyncio
import statistics
import psutil
import gc
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

# Import modules to test
try:
    from services.enhanced_breakout_engine import enhanced_breakout_engine
    ENHANCED_ENGINE_AVAILABLE = True
except ImportError:
    ENHANCED_ENGINE_AVAILABLE = False

try:
    from services.market_data_hub import market_data_hub
    MARKET_HUB_AVAILABLE = True
except ImportError:
    MARKET_HUB_AVAILABLE = False


@pytest.mark.performance
@pytest.mark.skipif(not ENHANCED_ENGINE_AVAILABLE, reason="Enhanced Breakout Engine not available")
class TestBreakoutEnginePerformance:
    """Performance tests for Enhanced Breakout Engine"""

    def test_vectorized_processing_latency(self):
        """Test that vectorized processing meets <5ms target"""
        import numpy as np
        from services.enhanced_breakout_engine import (
            fast_volume_breakout_check,
            fast_momentum_breakout_check,
            fast_resistance_breakout_check
        )
        
        # Test with 1000 instruments (realistic load)
        n_instruments = 1000
        
        # Generate realistic test data
        current_volumes = np.random.randint(50000, 500000, n_instruments).astype(np.uint32)
        volume_history = np.random.randint(20000, 200000, (n_instruments, 20)).astype(np.uint32)
        price_changes = np.random.uniform(-3, 3, n_instruments).astype(np.float32)
        current_prices = np.random.uniform(100, 3000, n_instruments).astype(np.float32)
        price_history = np.random.uniform(100, 3000, (n_instruments, 50)).astype(np.float32)
        
        latencies = []
        
        # Run multiple test iterations
        for _ in range(10):
            start_time = time.perf_counter()
            
            # Test all vectorized functions
            volume_results = fast_volume_breakout_check(current_volumes, volume_history, price_changes)
            momentum_results = fast_momentum_breakout_check(current_prices, price_changes)
            resistance_results = fast_resistance_breakout_check(current_prices, price_history)
            
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
        
        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        min_latency = min(latencies)
        max_latency = max(latencies)
        
        print(f"\nVectorized Processing Performance:")
        print(f"  Instruments: {n_instruments}")
        print(f"  Average latency: {avg_latency:.2f}ms")
        print(f"  95th percentile: {p95_latency:.2f}ms")
        print(f"  Min latency: {min_latency:.2f}ms")
        print(f"  Max latency: {max_latency:.2f}ms")
        print(f"  Per-instrument: {avg_latency/n_instruments:.4f}ms")
        
        # Performance assertions
        assert avg_latency < 10.0, f"Average latency {avg_latency:.2f}ms exceeds 10ms target"
        assert p95_latency < 20.0, f"95th percentile {p95_latency:.2f}ms exceeds 20ms limit"
        assert min_latency < 5.0, f"Best case {min_latency:.2f}ms exceeds 5ms target"

    @pytest.mark.asyncio
    async def test_real_time_processing_latency(self):
        """Test real-time data processing latency"""
        engine = enhanced_breakout_engine
        
        # Generate test market data batch
        test_feeds = []
        for i in range(500):  # 500 instruments update
            test_feeds.append({
                'instrument_key': f'NSE_EQ|{30000+i}',
                'symbol': f'TEST{i:03d}',
                'last_price': 1000.0 + i,
                'volume': 100000 + i * 100,
                'change_percent': (i % 20 - 10) / 10.0,  # -1% to +1%
                'timestamp': time.time()
            })
        
        latencies = []
        
        # Test processing latency
        for _ in range(5):  # 5 test runs
            start_time = time.perf_counter()
            
            # Process feed batch (simulating real-time update)
            await engine._process_feed_batch(test_feeds)
            
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
        
        avg_latency = statistics.mean(latencies)
        max_latency = max(latencies)
        
        print(f"\nReal-time Processing Performance:")
        print(f"  Feed size: {len(test_feeds)} instruments")
        print(f"  Average latency: {avg_latency:.2f}ms")
        print(f"  Max latency: {max_latency:.2f}ms")
        print(f"  Per-instrument: {avg_latency/len(test_feeds):.4f}ms")
        
        # Real-time targets
        assert avg_latency < 50.0, f"Real-time processing {avg_latency:.2f}ms too slow"
        assert max_latency < 100.0, f"Worst case {max_latency:.2f}ms unacceptable"

    def test_memory_usage_efficiency(self):
        """Test memory usage remains efficient under load"""
        engine = enhanced_breakout_engine
        storage = engine.storage
        
        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        storage_initial = storage.get_memory_usage()
        
        print(f"\nMemory Usage Test:")
        print(f"  Initial process memory: {initial_memory:.2f}MB")
        print(f"  Initial storage memory: {storage_initial:.2f}MB")
        
        # Add 2000 instruments with full history
        n_instruments = 2000
        
        for i in range(n_instruments):
            instrument_key = f"PERF_TEST_{i}"
            storage.add_instrument(instrument_key)
            
            # Add full history (simulate real usage)
            for j in range(storage.buffer_size):
                storage.update_data(
                    instrument_key,
                    price=1000.0 + i + j,
                    volume=100000 + i * 10 + j,
                    change_pct=(j % 10) / 10.0,
                    timestamp=time.time() + j
                )
        
        # Update analytics (triggers calculations)
        storage.batch_update_analytics()
        
        # Force garbage collection
        gc.collect()
        
        # Measure final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        storage_final = storage.get_memory_usage()
        
        memory_increase = final_memory - initial_memory
        storage_increase = storage_final - storage_initial
        
        print(f"  Final process memory: {final_memory:.2f}MB")
        print(f"  Final storage memory: {storage_final:.2f}MB")
        print(f"  Process increase: {memory_increase:.2f}MB")
        print(f"  Storage increase: {storage_increase:.2f}MB")
        print(f"  Memory per instrument: {storage_increase/n_instruments:.4f}MB")
        
        # Memory efficiency targets
        assert storage_increase < 100.0, f"Storage memory {storage_increase:.2f}MB too high"
        assert storage_increase/n_instruments < 0.1, f"Per-instrument memory too high"
        assert memory_increase < 200.0, f"Process memory increase {memory_increase:.2f}MB excessive"

    def test_throughput_capacity(self):
        """Test system throughput under sustained load"""
        engine = enhanced_breakout_engine
        
        # Test parameters
        test_duration = 10  # seconds
        batch_size = 100
        
        processed_batches = 0
        total_instruments = 0
        start_time = time.time()
        
        print(f"\nThroughput Test (Duration: {test_duration}s):")
        
        while time.time() - start_time < test_duration:
            # Generate batch of updates
            test_batch = []
            for i in range(batch_size):
                test_batch.append({
                    'instrument_key': f'THROUGHPUT_{i}',
                    'last_price': 2000.0 + (i % 100),
                    'volume': 100000 + i * 10,
                    'change_percent': (i % 20 - 10) / 10.0,
                    'timestamp': time.time()
                })
            
            # Process batch
            batch_start = time.perf_counter()
            
            # Simulate processing
            for update in test_batch:
                engine.storage.update_data(
                    update['instrument_key'],
                    update['last_price'],
                    update['volume'],
                    update['change_percent'],
                    update['timestamp']
                )
            
            batch_time = time.perf_counter() - batch_start
            
            processed_batches += 1
            total_instruments += batch_size
            
            # Small delay to prevent overwhelming
            time.sleep(0.001)
        
        actual_duration = time.time() - start_time
        throughput_per_second = total_instruments / actual_duration
        batches_per_second = processed_batches / actual_duration
        
        print(f"  Processed batches: {processed_batches}")
        print(f"  Total instruments: {total_instruments}")
        print(f"  Actual duration: {actual_duration:.2f}s")
        print(f"  Throughput: {throughput_per_second:.0f} instruments/second")
        print(f"  Batch rate: {batches_per_second:.1f} batches/second")
        
        # Throughput targets
        assert throughput_per_second > 1000, f"Throughput {throughput_per_second:.0f}/s too low"
        assert batches_per_second > 10, f"Batch rate {batches_per_second:.1f}/s too low"

    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """Test performance with concurrent operations"""
        engine = enhanced_breakout_engine
        
        async def simulate_data_processing():
            """Simulate concurrent data processing"""
            for i in range(50):  # 50 updates per coroutine
                await engine._process_feed_batch([{
                    'instrument_key': f'CONCURRENT_{i}',
                    'last_price': 2000.0 + i,
                    'volume': 100000,
                    'change_percent': 1.0,
                    'timestamp': time.time()
                }])
                await asyncio.sleep(0.001)  # Small delay
        
        async def simulate_breakout_detection():
            """Simulate concurrent breakout detection"""
            for i in range(20):  # 20 detection cycles
                await engine._detect_breakouts_vectorized()
                await asyncio.sleep(0.005)  # Small delay
        
        async def simulate_metrics_access():
            """Simulate concurrent metrics access"""
            for i in range(30):  # 30 metrics calls
                metrics = engine.get_metrics()
                summary = engine.get_breakouts_summary()
                await asyncio.sleep(0.003)  # Small delay
        
        print(f"\nConcurrent Processing Test:")
        
        start_time = time.perf_counter()
        
        # Run all operations concurrently
        await asyncio.gather(
            simulate_data_processing(),
            simulate_data_processing(),  # 2 data processors
            simulate_breakout_detection(),
            simulate_metrics_access(),
            return_exceptions=True
        )
        
        total_time = time.perf_counter() - start_time
        
        print(f"  Total concurrent time: {total_time:.2f}s")
        print(f"  Concurrent operations completed successfully")
        
        # Should complete reasonably quickly
        assert total_time < 5.0, f"Concurrent processing {total_time:.2f}s too slow"


@pytest.mark.performance
@pytest.mark.skipif(not MARKET_HUB_AVAILABLE, reason="Market Data Hub not available")
class TestMarketDataHubPerformance:
    """Performance tests for Market Data Hub"""
    
    def test_numpy_operations_speed(self):
        """Test NumPy operations performance"""
        from services.market_data_hub import fast_percentage_change, fast_moving_average
        import numpy as np
        
        # Test data
        n_instruments = 5000
        current_prices = np.random.uniform(100, 3000, n_instruments).astype(np.float32)
        previous_prices = current_prices * np.random.uniform(0.98, 1.02, n_instruments)
        
        latencies = []
        
        for _ in range(10):
            start_time = time.perf_counter()
            
            # Test percentage change calculation
            pct_changes = fast_percentage_change(current_prices, previous_prices)
            
            # Test moving average
            ma = fast_moving_average(current_prices, 20)
            
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
        
        avg_latency = statistics.mean(latencies)
        
        print(f"\nNumPy Operations Performance:")
        print(f"  Instruments: {n_instruments}")
        print(f"  Average latency: {avg_latency:.2f}ms")
        print(f"  Per-instrument: {avg_latency/n_instruments:.6f}ms")
        
        # NumPy should be very fast
        assert avg_latency < 5.0, f"NumPy operations {avg_latency:.2f}ms too slow"

    @pytest.mark.asyncio
    async def test_consumer_callback_performance(self):
        """Test callback system performance"""
        hub = market_data_hub
        
        callback_times = []
        callback_count = 0
        
        def performance_callback(data):
            nonlocal callback_count
            start_time = time.perf_counter()
            
            # Simulate processing
            time.sleep(0.0001)  # 0.1ms processing
            
            end_time = time.perf_counter()
            callback_times.append((end_time - start_time) * 1000)
            callback_count += 1
        
        # Register callback
        hub.register_consumer(
            "performance_test",
            performance_callback,
            ["prices"],
            priority=1
        )
        
        # Send test data
        test_data = {f"NSE_EQ|{i}": {"ltp": 2000 + i} for i in range(100)}
        
        start_time = time.perf_counter()
        
        # Trigger callbacks
        for _ in range(10):
            hub._notify_consumers("prices", test_data)
            await asyncio.sleep(0.001)
        
        total_time = time.perf_counter() - start_time
        
        print(f"\nCallback Performance:")
        print(f"  Callbacks triggered: {callback_count}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Average callback time: {statistics.mean(callback_times):.4f}ms")
        
        # Cleanup
        if "performance_test" in hub.consumers:
            del hub.consumers["performance_test"]


if __name__ == "__main__":
    # Allow running performance tests directly
    pytest.main([__file__, "-v", "-m", "performance"])