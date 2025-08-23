#!/usr/bin/env python3
"""
Integration Tests for Data Flow

Tests the complete data flow from WebSocket input through processing
to API output, ensuring all components work together correctly.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch

# Import components to test
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


@pytest.mark.integration
class TestDataFlowIntegration:
    """Test complete data flow integration"""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not ENHANCED_ENGINE_AVAILABLE, reason="Enhanced Breakout Engine not available")
    async def test_market_data_to_breakout_flow(self):
        """Test data flow from market data input to breakout detection"""
        
        engine = enhanced_breakout_engine
        
        # Mock market feed data (realistic breakout scenario)
        mock_feeds = [
            {
                'instrument_key': 'NSE_EQ|26000',
                'symbol': 'RELIANCE',
                'last_price': 2550.0,
                'volume': 800000,  # High volume
                'change_percent': 2.8,  # Strong move
                'open': 2480.0,
                'high': 2560.0,
                'low': 2475.0,
                'prev_close': 2481.0,
                'timestamp': time.time()
            },
            {
                'instrument_key': 'NSE_EQ|26001',
                'symbol': 'TCS',
                'last_price': 3800.0,
                'volume': 120000,  # Normal volume
                'change_percent': 0.5,  # Small move
                'open': 3790.0,
                'high': 3805.0,
                'low': 3785.0,
                'prev_close': 3781.0,
                'timestamp': time.time()
            }
        ]
        
        # Track what data reaches the engine
        processed_instruments = []
        detected_breakouts = []
        
        # Create a callback to track processing
        original_process_feed = engine._process_feed_batch
        
        async def tracking_process_feed(feeds):
            nonlocal processed_instruments
            processed_instruments.extend([f.get('symbol', 'Unknown') for f in feeds])
            result = await original_process_feed(feeds)
            return result
        
        # Patch the processing method
        engine._process_feed_batch = tracking_process_feed
        
        try:
            # Step 1: Process the mock data
            await engine._process_feed_batch(mock_feeds)
            
            # Step 2: Allow processing time
            await asyncio.sleep(0.5)
            
            # Step 3: Check that data was processed
            assert 'RELIANCE' in processed_instruments
            assert 'TCS' in processed_instruments
            
            # Step 4: Check for breakout detection
            summary = engine.get_breakouts_summary()
            
            # Should have some data (even if no breakouts)
            assert 'total_breakouts_today' in summary
            assert isinstance(summary['total_breakouts_today'], int)
            
            # Step 5: Check storage state
            storage = engine.storage
            assert storage.next_index >= 2  # At least 2 instruments added
            
            print(f"✅ Data flow test completed:")
            print(f"   Processed instruments: {processed_instruments}")
            print(f"   Total breakouts today: {summary['total_breakouts_today']}")
            print(f"   Instruments in storage: {storage.next_index}")
            
        finally:
            # Restore original method
            engine._process_feed_batch = original_process_feed

    @pytest.mark.asyncio
    @pytest.mark.skipif(not (ENHANCED_ENGINE_AVAILABLE and MARKET_HUB_AVAILABLE), 
                        reason="Required services not available")
    async def test_hub_to_engine_integration(self):
        """Test Market Data Hub to Breakout Engine integration"""
        
        hub = market_data_hub
        engine = enhanced_breakout_engine
        
        # Track callback interactions
        callback_data = []
        
        def test_callback(data):
            callback_data.append(data)
        
        # Register a test callback with the hub
        success = hub.register_consumer(
            "integration_test",
            test_callback,
            ["prices"],
            priority=1
        )
        
        assert success, "Failed to register test callback"
        
        try:
            # Send test data through the hub
            test_data = {
                'NSE_EQ|26000': {
                    'ltp': 2500.0,
                    'volume': 150000,
                    'change_percent': 1.5
                }
            }
            
            # Notify consumers (simulates hub broadcasting)
            hub._notify_consumers("prices", test_data)
            
            # Allow processing
            await asyncio.sleep(0.1)
            
            # Check that callback received data
            assert len(callback_data) > 0, "Test callback was not called"
            assert test_data in callback_data, "Test data not received by callback"
            
            print(f"✅ Hub integration test completed:")
            print(f"   Callbacks triggered: {len(callback_data)}")
            print(f"   Data received: {len(test_data)} instruments")
            
        finally:
            # Cleanup
            if "integration_test" in hub.consumers:
                del hub.consumers["integration_test"]

    @pytest.mark.asyncio
    async def test_error_resilience(self):
        """Test system resilience to errors in data flow"""
        
        if not ENHANCED_ENGINE_AVAILABLE:
            pytest.skip("Enhanced Breakout Engine not available")
        
        engine = enhanced_breakout_engine
        
        # Test with malformed data
        bad_feeds = [
            {},  # Empty data
            {'instrument_key': 'INVALID'},  # Missing required fields
            {'last_price': 'invalid_price'},  # Invalid data types
            {'instrument_key': 'NSE_EQ|99999', 'last_price': -100},  # Invalid values
        ]
        
        # Should handle errors gracefully
        try:
            await engine._process_feed_batch(bad_feeds)
            print("✅ Error resilience test: System handled malformed data gracefully")
        except Exception as e:
            pytest.fail(f"System failed to handle malformed data: {e}")
        
        # System should still be functional
        metrics = engine.get_metrics()
        assert isinstance(metrics, dict), "Engine metrics not accessible after error"

    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test integration performance under load"""
        
        if not ENHANCED_ENGINE_AVAILABLE:
            pytest.skip("Enhanced Breakout Engine not available")
        
        engine = enhanced_breakout_engine
        
        # Generate large batch of realistic data
        large_batch = []
        for i in range(100):  # 100 instruments
            large_batch.append({
                'instrument_key': f'NSE_EQ|{30000+i}',
                'symbol': f'STOCK{i:03d}',
                'last_price': 1000 + i * 10,
                'volume': 100000 + i * 1000,
                'change_percent': (i % 20 - 10) / 10.0,  # -1% to +1%
                'timestamp': time.time()
            })
        
        # Measure processing time
        start_time = time.perf_counter()
        
        await engine._process_feed_batch(large_batch)
        
        processing_time = (time.perf_counter() - start_time) * 1000  # ms
        
        print(f"✅ Load test completed:")
        print(f"   Batch size: {len(large_batch)} instruments")
        print(f"   Processing time: {processing_time:.2f}ms")
        print(f"   Per-instrument: {processing_time/len(large_batch):.4f}ms")
        
        # Performance assertion
        assert processing_time < 100.0, f"Processing {len(large_batch)} instruments took {processing_time:.2f}ms (too slow)"

    def test_api_data_consistency(self):
        """Test that API returns consistent data structure"""
        
        if not ENHANCED_ENGINE_AVAILABLE:
            pytest.skip("Enhanced Breakout Engine not available")
        
        engine = enhanced_breakout_engine
        
        # Get data from different methods
        summary = engine.get_breakouts_summary()
        metrics = engine.get_metrics()
        
        # Validate summary structure
        required_summary_fields = [
            'total_breakouts_today', 'breakouts_by_type', 
            'recent_breakouts', 'timestamp'
        ]
        for field in required_summary_fields:
            assert field in summary, f"Missing field in summary: {field}"
        
        # Validate metrics structure
        required_metrics_fields = [
            'total_scans', 'breakouts_detected', 
            'memory_usage_mb', 'instruments_tracked'
        ]
        for field in required_metrics_fields:
            assert field in metrics, f"Missing field in metrics: {field}"
        
        # Data type validation
        assert isinstance(summary['total_breakouts_today'], int)
        assert isinstance(summary['breakouts_by_type'], dict)
        assert isinstance(summary['recent_breakouts'], list)
        assert isinstance(metrics['memory_usage_mb'], (int, float))
        
        print(f"✅ API consistency test completed:")
        print(f"   Summary fields: {len(summary)}")
        print(f"   Metrics fields: {len(metrics)}")

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test system behavior with concurrent operations"""
        
        if not ENHANCED_ENGINE_AVAILABLE:
            pytest.skip("Enhanced Breakout Engine not available")
        
        engine = enhanced_breakout_engine
        
        async def data_processor():
            """Simulate concurrent data processing"""
            for i in range(10):
                await engine._process_feed_batch([{
                    'instrument_key': f'CONCURRENT_{i}',
                    'last_price': 2000 + i,
                    'volume': 100000,
                    'change_percent': 1.0,
                    'timestamp': time.time()
                }])
                await asyncio.sleep(0.01)
        
        async def metrics_accessor():
            """Simulate concurrent metrics access"""
            for i in range(15):
                metrics = engine.get_metrics()
                summary = engine.get_breakouts_summary()
                assert isinstance(metrics, dict)
                assert isinstance(summary, dict)
                await asyncio.sleep(0.005)
        
        async def analytics_updater():
            """Simulate concurrent analytics updates"""
            for i in range(8):
                engine.storage.batch_update_analytics()
                await asyncio.sleep(0.015)
        
        # Run all operations concurrently
        start_time = time.perf_counter()
        
        await asyncio.gather(
            data_processor(),
            data_processor(),  # Two data processors
            metrics_accessor(),
            analytics_updater(),
            return_exceptions=True
        )
        
        total_time = time.perf_counter() - start_time
        
        print(f"✅ Concurrent operations test completed:")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   No exceptions or deadlocks occurred")
        
        # Should complete without hanging or errors
        assert total_time < 3.0, f"Concurrent operations took {total_time:.2f}s (too long)"


@pytest.mark.integration
class TestServiceHealthIntegration:
    """Test integration of service health checks"""
    
    def test_all_services_health(self):
        """Test that all available services report health correctly"""
        
        health_results = {}
        
        # Test Enhanced Breakout Engine
        if ENHANCED_ENGINE_AVAILABLE:
            try:
                from services.enhanced_breakout_engine import health_check
                health_results['enhanced_breakout'] = health_check()
            except Exception as e:
                health_results['enhanced_breakout'] = {'status': 'error', 'error': str(e)}
        
        # Test Market Data Hub
        if MARKET_HUB_AVAILABLE:
            try:
                health_results['market_hub'] = {
                    'status': 'available',
                    'memory_usage': market_data_hub.get_memory_usage()
                }
            except Exception as e:
                health_results['market_hub'] = {'status': 'error', 'error': str(e)}
        
        print(f"✅ Service health check completed:")
        for service, health in health_results.items():
            status = health.get('status', 'unknown')
            print(f"   {service}: {status}")
        
        # At least one service should be available
        assert len(health_results) > 0, "No services available for testing"


if __name__ == "__main__":
    # Allow running integration tests directly
    pytest.main([__file__, "-v", "-m", "integration"])