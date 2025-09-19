# WebSocket Services Documentation

This directory contains documentation for all WebSocket-related services in the trading application.

## Overview

The WebSocket services provide real-time market data processing, streaming, and analytics capabilities. The architecture is designed to handle high-frequency data with low latency and comprehensive error handling.

## Service Architecture

```
WebSocket Services
├── MCX Service           # MCX commodity data processing
├── Centralized Manager   # Unified WebSocket management
├── Unified Manager       # Multi-broker data aggregation
└── Upstox Client        # Upstox-specific WebSocket client
```

## Available Services

### 🏗️ Core Services

#### 1. **MCX WebSocket Service** (`mcx/`)
- **Purpose**: Real-time MCX commodity data processing
- **Features**: Pandas/NumPy analytics, futures chains, volume analysis
- **Documentation**: [MCX Service Guide](mcx/MCX_WEBSOCKET_SERVICE.md)
- **Data Format**: [MCX Data Format](mcx/MCX_DATA_FORMAT.md)

#### 2. **Centralized WebSocket Manager**
- **Purpose**: Single admin WebSocket connection for all instruments
- **Features**: Unified data management, broadcasting, health monitoring
- **Location**: `services/centralized_ws_manager.py`

#### 3. **Unified WebSocket Manager**
- **Purpose**: Multi-broker data aggregation and streaming
- **Features**: Real-time data broadcasting, client management
- **Location**: `services/unified_websocket_manager.py`

#### 4. **Upstox WebSocket Client**
- **Purpose**: Upstox-specific WebSocket connection handling
- **Features**: Protobuf decoding, connection management, retry logic
- **Location**: `services/upstox/ws_client.py`

## Data Flow Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Broker APIs   │    │  WebSocket       │    │   Analytics     │
│                 │    │  Services        │    │   Engine        │
│ • Upstox        │───▶│                  │───▶│                 │
│ • Angel One     │    │ • MCX Service    │    │ • Real-time     │
│ • Dhan          │    │ • Centralized    │    │ • Historical    │
│ • Zerodha       │    │ • Unified        │    │ • Predictive    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Frontend      │
                       │   Clients       │
                       │                 │
                       │ • Dashboard     │
                       │ • Trading UI    │
                       │ • Mobile App    │
                       └─────────────────┘
```

## Service Integration

### Automatic Startup
All WebSocket services are automatically integrated into the main application startup sequence:

```python
# In app.py lifespan function
async def lifespan(app: FastAPI):
    # ... other services

    # Step 8: Centralized WebSocket
    await centralized_manager.initialize()

    # Step 16: MCX WebSocket Service
    await initialize_mcx_service()

    yield

    # Shutdown
    await centralized_manager.stop()
    await stop_mcx_service()
```

### Health Monitoring
Each service provides health check endpoints:

```python
GET /api/health/websocket    # Overall WebSocket health
GET /api/health/mcx          # MCX service health
GET /api/health/centralized  # Centralized manager health
```

## Development Guidelines

### Adding New WebSocket Services

1. **Create Service Directory**
   ```bash
   mkdir services/websocket/{service_name}
   ```

2. **Implement Core Components**
   - `{service}_ws_client.py` - WebSocket client implementation
   - `{service}_service_manager.py` - Service lifecycle management
   - `integration.py` - App integration functions

3. **Add Documentation**
   - `README.md` - Service overview and usage
   - `{SERVICE}_DATA_FORMAT.md` - Data format specification

4. **Integrate with App**
   - Add startup logic in `app.py`
   - Add health checks
   - Add API endpoints if needed

### Coding Standards

#### WebSocket Client Pattern
```python
class CustomWebSocketClient:
    def __init__(self, callback=None):
        self.callback = callback
        self.is_running = False

    async def initialize(self) -> bool:
        # Setup and validation
        pass

    async def start(self) -> bool:
        # Start WebSocket connection
        pass

    async def stop(self):
        # Clean shutdown
        pass
```

#### Service Manager Pattern
```python
class CustomServiceManager:
    def __init__(self):
        self.client = None
        self.is_running = False

    async def start_service(self) -> bool:
        # Initialize and start client
        pass

    async def stop_service(self):
        # Clean shutdown
        pass

    def get_service_status(self) -> Dict:
        # Return health status
        pass
```

### Error Handling
- Use comprehensive try/catch blocks
- Implement exponential backoff for retries
- Log errors with context for debugging
- Graceful degradation for non-critical failures

### Performance Optimization
- Use async/await for non-blocking operations
- Implement connection pooling where applicable
- Cache frequently accessed data
- Use pandas/numpy for data processing efficiency

## Configuration

### Environment Variables
```bash
# WebSocket Configuration
WS_RECONNECT_INTERVAL=30
WS_MAX_RETRIES=5
WS_TIMEOUT=120

# MCX Specific
MCX_MARKET_START=09:00
MCX_MARKET_END=23:30
MCX_EXPORT_PATH=data/mcx_export

# Health Monitoring
HEALTH_CHECK_INTERVAL=60
PERFORMANCE_LOG_INTERVAL=300
```

### Database Configuration
WebSocket services require broker configurations in the database:

```sql
-- BrokerConfig table
SELECT * FROM broker_configs
WHERE broker = 'upstox'
AND user_email = 'admin@example.com';
```

## Monitoring & Observability

### Metrics Collection
- Connection uptime and stability
- Message processing rates
- Error rates and types
- Memory and CPU usage
- Data quality metrics

### Logging
```python
# Standard logging format
logger.info("🚀 Service started successfully")
logger.warning("⚠️ Connection retry attempt")
logger.error("❌ Service failed to initialize")
```

### Performance Monitoring
- Real-time latency tracking
- Memory usage optimization
- Connection health scoring
- Data freshness validation

## Troubleshooting

### Common Issues

#### 1. Connection Failures
```
Error: WebSocket connection failed
Solution: Check network, broker API status, token validity
```

#### 2. Data Processing Errors
```
Error: NoneType comparison errors
Solution: Implement proper null checking, data validation
```

#### 3. Memory Leaks
```
Error: Increasing memory usage
Solution: Implement data cleanup, limit cache sizes
```

#### 4. Token Expiry
```
Error: Authentication failed
Solution: Implement automatic token refresh
```

### Debug Mode
Enable detailed logging for troubleshooting:

```python
import logging
logging.getLogger('services.websocket').setLevel(logging.DEBUG)
```

## Future Enhancements

### Planned Features
- [ ] Multi-exchange WebSocket aggregation
- [ ] Advanced machine learning analytics
- [ ] Real-time option chain processing
- [ ] Cross-commodity arbitrage detection
- [ ] Enhanced mobile WebSocket support

### Performance Improvements
- [ ] WebSocket connection pooling
- [ ] Advanced caching strategies
- [ ] GPU-accelerated analytics
- [ ] Distributed processing support

## Resources

### External Documentation
- [Upstox WebSocket API](https://upstox.com/developer/api/websocket-api/)
- [WebSocket RFC 6455](https://tools.ietf.org/html/rfc6455)
- [FastAPI WebSocket Guide](https://fastapi.tiangolo.com/advanced/websockets/)

### Internal Links
- [System Architecture](../../architecture/)
- [Data Flow Analysis](../../data-flow/)
- [Integration Patterns](../../integration/)

---

For specific service documentation, see the individual service folders and their respective README files.