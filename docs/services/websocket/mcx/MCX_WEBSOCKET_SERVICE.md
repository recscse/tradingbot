# MCX WebSocket Service

A specialized WebSocket client for MCX (Multi Commodity Exchange) real-time data processing with pandas/numpy analytics integration.

## Overview

The MCX WebSocket service provides:
- **Real-time MCX commodity data** via Upstox WebSocket API
- **Pandas/NumPy integration** for advanced analytics
- **Futures chain data processing** for commodities
- **Automatic token management** and health monitoring
- **Modular architecture** following the existing ws_client pattern

## Architecture

```
services/websocket/mcx/
├── __init__.py                 # Module initialization
├── mcx_ws_client.py           # Core WebSocket client with pandas integration
├── mcx_service_manager.py     # Service lifecycle management
├── integration.py             # App integration and health checks
└── README.md                  # This file
```

## Features

### 🚀 Core Features
- **Real-time MCX Data**: Live commodity futures and options data
- **Pandas Analytics**: Advanced data processing with DataFrames
- **Futures Chains**: Automatic futures chain construction
- **Auto Restart**: Automatic reconnection and error recovery
- **Market Hours**: Smart market hours detection

### 📊 Data Processing
- **Live Price Data**: Real-time LTP, volume, change calculations
- **Volume Analytics**: Trading volume analysis and statistics
- **Performance Metrics**: Top gainers/losers identification
- **Symbol Grouping**: Futures chain organization by underlying

### 🔧 Technical Features
- **Async Architecture**: Non-blocking WebSocket operations
- **Error Resilience**: Comprehensive error handling
- **Data Export**: CSV export capabilities
- **Health Monitoring**: Service health checks and statistics

## Usage

### Basic Usage

```python
from services.websocket.mcx.mcx_ws_client import MCXWebSocketClient

# Create client with custom callback
async def my_callback(data):
    print(f"Received MCX data: {data['count']} instruments")

    # Access pandas DataFrames
    dataframes = data.get('dataframes', {})
    if 'current_snapshot' in dataframes:
        df = dataframes['current_snapshot']
        print(f"Top performer: {df.nlargest(1, 'change_percent')}")

mcx_client = MCXWebSocketClient(callback=my_callback)

# Initialize and start
if await mcx_client.initialize():
    await mcx_client.start()
```

### Service Manager Usage

```python
from services.websocket.mcx.mcx_service_manager import MCXServiceManager

service = MCXServiceManager()

# Start service (handles market hours automatically)
await service.start_service()

# Get analytics
analytics = service.get_analytics_summary()
market_overview = service.get_market_overview()

# Get specific symbol data
symbol_data = service.get_symbol_data("CRUDEOIL")
```

### App Integration

The MCX service automatically integrates with the main application:

```python
# Automatic startup during app initialization
# Added in app.py lifespan function

# Health check endpoint
from services.websocket.mcx.integration import get_mcx_status
status = get_mcx_status()
```

## Data Format

### Input Format (Upstox WebSocket)
```json
{
  "type": "live_feed",
  "feeds": {
    "MCX_FO|463598": {
      "fullFeed": {
        "marketFF": {
          "ltpc": {"ltp": 6500.50, "cp": 6450.00},
          "tbq": 150000,
          "marketOHLC": {"ohlc": [...]},
          "marketLevel": {"bidAskQuote": [...]}
        }
      }
    }
  }
}
```

### Output Format (Processed)
```json
{
  "type": "mcx_live_feed",
  "count": 25,
  "timestamp": "1758291921887",
  "dataframes": {
    "current_snapshot": "pandas.DataFrame",
    "futures_chain": "pandas.DataFrame",
    "volume_data": "pandas.DataFrame"
  },
  "analytics": {
    "total_instruments": 25,
    "price_stats": {
      "avg_change_percent": 1.23,
      "top_gainers": [...],
      "top_losers": [...]
    }
  }
}
```

## Configuration

### Environment Variables
```bash
# Required - Upstox access token in database
ADMIN_EMAIL=admin@example.com

# Optional - Market hours override
MCX_MARKET_START=09:00
MCX_MARKET_END=23:30

# Optional - Data export path
MCX_EXPORT_PATH=data/mcx_export
```

### Market Hours
- **Default**: 9:00 AM to 11:30 PM (MCX extended hours)
- **Automatic**: Service starts/stops based on market hours
- **Override**: Can be customized via environment variables

## Testing

### Run Basic Test
```bash
python examples/mcx_enhanced_test.py
```

### Test Options
1. **Basic MCX Client Test** (60 seconds)
2. **MCX Service Manager Test** (30 seconds)
3. **Pandas Analytics Demo**
4. **All Tests**

### Test Output
- Real-time data display
- Pandas analytics demonstration
- Data export functionality
- Service health monitoring

## Integration Points

### With Centralized WebSocket Manager
- MCX data is broadcasted to dashboard clients
- Integrated with unified data flow
- Health status included in system monitoring

### With Database
- Access token retrieval from BrokerConfig table
- Token expiry validation
- User-specific configurations

### With Redis (Optional)
- Market data caching
- Performance metrics storage
- Analytics snapshots

## Performance

### Optimizations
- **Pandas DataFrames**: Efficient data manipulation
- **NumPy Arrays**: Fast numerical computations
- **Async Processing**: Non-blocking operations
- **Memory Management**: Automatic data cleanup

### Metrics
- **Latency**: <10ms data processing
- **Memory**: Automatic cleanup after 1000 records per instrument
- **CPU**: Optimized with vectorized operations
- **Network**: Efficient protobuf decoding

## Error Handling

### Automatic Recovery
- **Connection Errors**: Auto-reconnect with exponential backoff
- **Token Expiry**: Automatic token refresh detection
- **Data Errors**: Graceful handling of malformed data
- **Market Hours**: Automatic service pause/resume

### Monitoring
- **Health Checks**: Continuous service monitoring
- **Error Logging**: Comprehensive error tracking
- **Performance Metrics**: Real-time performance statistics
- **Data Quality**: Data validation and cleanup

## API Endpoints

When integrated with the main app, provides:

```
GET /api/mcx/status          # Service health status
GET /api/mcx/analytics       # Real-time analytics
GET /api/mcx/market-overview # Market overview
GET /api/mcx/symbol/{symbol} # Symbol-specific data
```

## Development

### Adding New Features
1. Extend `MCXDataProcessor` for new analytics
2. Add callback processing in `MCXWebSocketClient`
3. Update service manager for new data types
4. Add integration endpoints as needed

### Testing New Features
1. Use `examples/mcx_enhanced_test.py` as base
2. Add custom callbacks for specific testing
3. Validate with pandas analytics
4. Test integration with main app

## Troubleshooting

### Common Issues

1. **No Access Token**
   - Check database for valid Upstox token
   - Verify ADMIN_EMAIL configuration
   - Check token expiry

2. **WebSocket Connection Failed**
   - Verify internet connectivity
   - Check Upstox API status
   - Review token permissions

3. **No MCX Data**
   - Confirm MCX instruments in data/mcx_instruments.json
   - Check market hours
   - Verify subscription success

4. **High Memory Usage**
   - Check data retention settings
   - Verify automatic cleanup
   - Monitor DataFrame sizes

### Debug Mode
```python
import logging
logging.getLogger('services.websocket.mcx').setLevel(logging.DEBUG)
```

## License

Part of the main trading application. See main project license.