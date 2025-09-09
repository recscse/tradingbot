# WebSocket Feed Distribution Integration Guide

## Overview

This guide explains how to integrate the Upstox WebSocket client with the centralized manager to achieve non-blocking feed distribution to multiple services like premarket candle builder and breakout detection engine.

## Architecture

The new architecture solves blocking issues by using a centralized dispatch system:

```
Upstox WebSocket Client → centralized_manager.publish() → Non-blocking dispatch → Multiple Services
```

### Why This Architecture Avoids Blocking

1. **Non-blocking dispatch**: `centralized_manager.publish()` schedules callbacks via `asyncio.create_task()` instead of awaiting them
2. **Async/sync handling**: Sync callbacks run in a thread pool executor to avoid blocking the event loop
3. **Fast return**: The WebSocket receiver returns immediately after scheduling callbacks

## Integration Code Example

### 1. Upstox WebSocket Client Integration

```python
from services.centralized_ws_manager import centralized_manager
from services.upstox.ws_client import UpstoxWebSocketClient

# Initialize centralized manager
await centralized_manager.initialize()

# Create Upstox client with centralized callback
upstox_client = UpstoxWebSocketClient(
    # KEY CHANGE: Use centralized_manager.publish as callback
    callback=centralized_manager.publish,  # NON-BLOCKING
    
    instrument_keys=list(centralized_manager.all_instrument_keys),
    admin_token=centralized_manager.admin_token
)

# Start streaming - data flows non-blocking to all services
await upstox_client.connect_and_stream()
```

### 2. Service Registration (Premarket Candle Builder)

```python
from services.centralized_ws_manager import centralized_manager

# Register callback without priority parameter (FIXED)
success = await centralized_manager.register_callback(
    "price_update", 
    self._handle_direct_market_data
)

# The callback receives normalized data and doesn't block others
async def _handle_direct_market_data(self, callback_data: dict):
    # Feed normalization handles different formats
    market_feeds = normalize_feed_data(callback_data)
    
    # Process safely with defensive parsing
    for instrument_key, feed_data in market_feeds.items():
        price = safe_float(feed_data.get("ltp", 0))
        volume = safe_int(feed_data.get("volume", 0))
        # ... process without blocking other services
```

### 3. Service Registration (Enhanced Breakout Engine)

```python
from services.centralized_ws_manager import centralized_manager, register_market_data_callback

# Register with centralized manager
success = register_market_data_callback(self._process_centralized_data)

async def _process_centralized_data(self, data: Dict[str, Any]):
    # FIXED: Handle both dict and list feeds formats
    feeds_raw = data.get("data", data.get("feeds", []))
    
    # Convert dict to list to prevent slice errors
    if isinstance(feeds_raw, dict):
        feeds = list(feeds_raw.values())  # PREVENTS unhashable slice error
    elif isinstance(feeds_raw, list):
        feeds = feeds_raw
    else:
        feeds = []
    
    # Process in batches without blocking
    for i in range(0, len(feeds), batch_size):
        batch = feeds[i:i + batch_size]  # Now works correctly
        await self._process_feed_batch(batch)
```

## Backpressure Recommendations

### Adding Per-Consumer Queues (Optional)

If you need backpressure protection, you can add bounded queues:

```python
import asyncio
from collections import defaultdict

class EnhancedCentralizedManager(CentralizedWebSocketManager):
    def __init__(self):
        super().__init__()
        # Add per-consumer queues
        self.consumer_queues = defaultdict(lambda: asyncio.Queue(maxsize=1000))
        self.consumer_workers = {}
    
    async def register_callback_with_queue(self, event_type: str, callback, max_queue_size=1000):
        """Register callback with dedicated queue for backpressure protection"""
        queue = asyncio.Queue(maxsize=max_queue_size)
        self.consumer_queues[callback] = queue
        
        # Start worker for this consumer
        worker = asyncio.create_task(self._queue_worker(callback, queue))
        self.consumer_workers[callback] = worker
        
        # Register the queuing callback instead of direct callback
        await self.register_callback(event_type, lambda data: self._enqueue_data(callback, data))
    
    async def _enqueue_data(self, callback, data):
        """Enqueue data for consumer, drop if queue full"""
        queue = self.consumer_queues.get(callback)
        if queue:
            try:
                queue.put_nowait(data)
            except asyncio.QueueFull:
                logger.warning(f"Queue full for {callback.__name__}, dropping data")
    
    async def _queue_worker(self, callback, queue):
        """Worker that processes queued data for a consumer"""
        while True:
            try:
                data = await queue.get()
                await callback(data)
                queue.task_done()
            except Exception as e:
                logger.error(f"Error in queue worker for {callback.__name__}: {e}")
```

## Testing the Integration

### Run the Test Harness

```bash
# From the project root directory
cd C:\Work\P\app\tradingapp-main\tradingapp-main

# Run the test script
python scripts\test_feed_dispatch.py
```

The test harness verifies:
- ✅ Non-blocking dispatch (publish returns quickly)
- ✅ Multiple callback formats are supported
- ✅ Both async and sync callbacks work
- ✅ No data loss during dispatch
- ✅ Error handling works correctly

### Expected Output

```
🧪 Feed Dispatch Test Harness
===============================================
📡 Test 1: Publishing Dict-of-feeds (Upstox format)...
   ⏱️  Publish took 0.45ms
📡 Test 2: Publishing Nested data format...
   ⏱️  Publish took 0.32ms
📡 Test 3: Publishing List-of-feeds format...
   ⏱️  Publish took 0.28ms

📊 TEST RESULTS
==============================
✅ PASS - All tests successful!

✅ The centralized manager:
  • Accepts various feed formats
  • Dispatches to callbacks non-blocking
  • Handles both async and sync callbacks
  • Does not block the WebSocket receive loop
```

## Key Benefits

1. **No WebSocket Blocking**: The WebSocket receiver returns immediately after publishing
2. **Multiple Service Support**: Any number of services can register for feeds
3. **Format Flexibility**: Handles Upstox protobuf format, normalized format, and lists
4. **Error Isolation**: If one service fails, others continue receiving data
5. **Performance**: Sub-millisecond dispatch times with concurrent callback execution

## Troubleshooting

### Common Issues

1. **"TypeError: register_callback() got unexpected keyword 'priority'"**
   - **Fix**: Remove the `priority` parameter from callback registration

2. **"TypeError: unhashable type: 'slice'"**
   - **Fix**: Applied in enhanced_breakout_engine.py - converts dict feeds to list before slicing

3. **Slow WebSocket receiving**
   - **Fix**: Centralized manager now uses non-blocking dispatch via `asyncio.create_task()`

4. **Services not receiving data**
   - **Check**: Ensure services register callbacks during startup
   - **Check**: Verify centralized manager is initialized before service registration

### Debugging Tips

```python
# Enable debug logging
import logging
logging.getLogger("services.centralized_ws_manager").setLevel(logging.DEBUG)

# Check callback registration
print(f"Registered callbacks: {centralized_manager.callbacks}")

# Monitor performance metrics
print(f"Callbacks executed: {centralized_manager.performance_metrics['callbacks_executed']}")
```

## Production Considerations

- **Memory Management**: The non-blocking approach uses more memory due to task scheduling
- **Error Monitoring**: Set up alerts for callback failures
- **Performance Monitoring**: Track dispatch times and callback execution rates
- **Graceful Shutdown**: Ensure all background tasks are cancelled on shutdown

## Next Steps

1. Deploy the fixes to your development environment
2. Run the test harness to verify integration
3. Monitor WebSocket performance and callback execution
4. Consider adding per-consumer queues if backpressure becomes an issue