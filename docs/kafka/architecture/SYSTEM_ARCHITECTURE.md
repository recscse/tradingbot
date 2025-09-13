# 🏗️ Kafka System Architecture

## Overview

The trading application uses Apache Kafka as the central nervous system for distributing real-time market data and trading signals across multiple services. This architecture ensures low-latency, high-throughput, and fault-tolerant processing of financial data.

## High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│  Kafka Cluster   │───▶│   Trading       │
│                 │    │                  │    │   Services      │
│ • Upstox WS     │    │ • Market Data    │    │ • Analytics     │
│ • Angel One WS  │    │ • Trading Signals│    │ • Strategy      │
│ • Dhan WS       │    │ • UI Updates     │    │ • Execution     │
│ • Manual Events │    │ • System Events  │    │ • Monitoring    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Data Flow Architecture

### Phase 1: Data Ingestion (Critical Path)

**Entry Point**: `services/centralized_ws_manager.py`

```
WebSocket Sources ──┐
                    │
Upstox Live Feed ───┼──▶ CentralizedWSManager ──▶ kafka.trading.market_data.raw
                    │         (Validation &              (Topic)
Angel One Feed ─────┘         Standardization)
```

**Key Features**:
- Single entry point for all market data
- Data validation and format standardization
- Timestamp enrichment with processing metadata
- Error handling with graceful degradation

### Phase 2: Data Processing & Distribution

```
kafka.trading.market_data.raw ──┬──▶ InstrumentRegistry ──▶ Price Updates
                                 │
                                 ├──▶ BreakoutEngine ──▶ Trading Signals
                                 │
                                 ├──▶ MarketAnalytics ──▶ Sentiment Data
                                 │
                                 ├──▶ PremarketBuilder ──▶ OHLC Data
                                 │
                                 └──▶ UIBroadcaster ──▶ Frontend Updates
```

### Phase 3: Signal Generation & Execution

```
Trading Signals ──┬──▶ kafka.trading.signals.breakout
                  │
                  ├──▶ kafka.trading.signals.gap
                  │
                  ├──▶ kafka.trading.signals.momentum
                  │
                  └──▶ ExecutionEngine ──▶ Broker APIs
```

## Topic Architecture

### Core Topics Structure

```
kafka.trading.
├── market_data.
│   ├── raw                     # Raw WebSocket data (Priority 0)
│   └── processed               # Standardized market data
├── signals.
│   ├── breakout               # Breakout detection signals
│   ├── gap                    # Gap up/down signals
│   ├── momentum              # Momentum strategy signals
│   └── fibonacci             # Fibonacci retracement signals
├── analytics.
│   ├── market                # Market sentiment & analytics
│   └── performance           # Trading performance metrics
├── ui.
│   ├── price_updates         # Real-time price updates
│   └── alerts               # Alert notifications
└── system.
    └── events               # System monitoring events
```

### Topic Configuration

#### Critical Path Topics
```yaml
market_data.raw:
  partitions: 1              # Sequential processing for data integrity
  replication_factor: 3      # High availability
  retention_ms: 3600000      # 1 hour retention
  cleanup_policy: delete     # Time-based cleanup

market_data.processed:
  partitions: 8              # Parallel processing
  replication_factor: 3      # High availability
  retention_ms: 1800000      # 30 minutes retention
```

#### Signal Topics
```yaml
signals.*:
  partitions: 4              # Strategy parallelism
  replication_factor: 2      # Balance availability/performance
  retention_ms: 3600000      # 1 hour for analysis
```

#### UI Topics
```yaml
ui.*:
  partitions: 2              # Simple distribution
  replication_factor: 2      # Standard availability
  retention_ms: 300000       # 5 minutes (ephemeral)
```

## Service Integration

### 1. Centralized WebSocket Manager
**File**: `services/centralized_ws_manager.py`

**Role**: Single entry point for all market data
- Receives WebSocket data from multiple brokers
- Validates and standardizes data format
- Publishes to `kafka.trading.market_data.raw`
- Handles connection failures and reconnection

**Key Method**:
```python
async def _kafka_stream_market_data(self, instrument_key: str, data: dict):
    """Stream market data to Kafka with standardization"""
    standardized_data = {
        "instrument_key": instrument_key,
        "timestamp": int(time.time() * 1000),
        "source": "centralized_ws_manager",
        "data": data,
        "processing_stage": "raw_ingestion"
    }

    await self.kafka_system.publish_message(
        topic="kafka.trading.market_data.raw",
        message=standardized_data,
        key=instrument_key
    )
```

### 2. Instrument Registry Service
**File**: `services/instrument_registry.py`

**Role**: Real-time price tracking and caching
- Consumes from `kafka.trading.market_data.raw`
- Maintains live price cache for all instruments
- Triggers price alerts and notifications
- Publishes to `kafka.ui.price_updates`

**Consumer Configuration**:
```python
consumer_config = {
    "group_id": "instrument_registry_group",
    "topics": ["kafka.trading.market_data.raw"],
    "auto_offset_reset": "latest"
}
```

### 3. Enhanced Breakout Engine
**File**: `services/enhanced_breakout_engine.py`

**Role**: Technical analysis and signal generation
- Consumes market data for breakout pattern detection
- Applies technical analysis algorithms
- Publishes signals to `kafka.trading.signals.breakout`
- Integrates with risk management systems

### 4. Market Analytics Service
**File**: `services/enhanced_market_analytics.py`

**Role**: Real-time market analysis
- Processes market data for sentiment analysis
- Calculates market-wide metrics (top movers, volume analysis)
- Publishes to `kafka.trading.analytics.market`
- Provides dashboard data for UI

## Message Formats

### Raw Market Data Format
```json
{
    "instrument_key": "NSE_EQ|INE318A01026",
    "timestamp": 1757308567467,
    "source": "centralized_ws_manager",
    "data": {
        "type": "live_feed",
        "feeds": {
            "NSE_EQ|INE318A01026": {
                "fullFeed": {
                    "marketFF": {
                        "ltpc": {
                            "ltp": 3097.7,
                            "ltt": "1757308567467",
                            "cp": 3095.1
                        }
                    }
                }
            }
        }
    },
    "processing_stage": "raw_ingestion",
    "correlation_id": "uuid-generated"
}
```

### Trading Signal Format
```json
{
    "signal_id": "breakout_RELIANCE_20250114_093456",
    "instrument_key": "NSE_EQ|INE318A01026",
    "symbol": "RELIANCE",
    "strategy_type": "breakout",
    "action": "BUY",
    "timestamp": 1757308567467,
    "price_data": {
        "current_price": 3097.7,
        "breakout_level": 3095.0,
        "stop_loss": 3080.0,
        "target": 3120.0
    },
    "confidence": 0.85,
    "risk_reward": 2.5,
    "metadata": {
        "pattern_type": "ascending_triangle",
        "volume_confirmation": true,
        "timeframe": "5min"
    }
}
```

### UI Update Format
```json
{
    "update_type": "price_update",
    "instrument_key": "NSE_EQ|INE318A01026",
    "symbol": "RELIANCE",
    "data": {
        "ltp": 3097.7,
        "change": 2.6,
        "change_percent": 0.084,
        "volume": 31929
    },
    "timestamp": 1757308567467,
    "channel": "live_prices"
}
```

## Performance Specifications

### Latency Targets
- **Market Data Ingestion**: < 1ms
- **Signal Generation**: < 100ms
- **UI Updates**: < 500ms
- **End-to-End Processing**: < 1 second

### Throughput Requirements
- **Market Data**: 1000+ messages/second
- **Signal Processing**: 100 signals/second
- **UI Updates**: 50 updates/second per client
- **Concurrent Users**: 100+ simultaneous connections

### Resource Requirements
- **Memory**: 1GB for 5000 instruments
- **CPU**: 4 cores recommended for production
- **Network**: Low-latency connection to brokers
- **Storage**: 10GB for daily trading data

## Error Handling & Resilience

### Circuit Breakers
- **Connection Failures**: Automatic reconnection with exponential backoff
- **Processing Errors**: Dead letter queues for failed messages
- **Resource Limits**: Graceful degradation under high load
- **Data Quality**: Validation failures logged and skipped

### Monitoring & Health Checks
- **Consumer Lag Monitoring**: Real-time lag tracking per consumer group
- **Error Rate Tracking**: Percentage of failed messages per topic
- **Throughput Monitoring**: Messages per second per topic
- **System Health**: CPU, memory, and disk usage monitoring

### Failover Mechanisms
- **Multi-Broker Setup**: 3+ Kafka brokers for high availability
- **Replication**: All critical topics replicated across brokers
- **Graceful Degradation**: System continues operating with reduced functionality
- **Backup Systems**: Fallback to direct WebSocket distribution if Kafka fails

## Security Considerations

### Data Protection
- **SASL/SSL**: Encrypted communication for production deployments
- **API Keys**: Secure handling of broker credentials
- **Data Masking**: Sensitive information not logged in plain text
- **Access Control**: Topic-level permissions for different services

### Compliance
- **Audit Trails**: All trading signals and decisions logged
- **Data Retention**: Configurable retention policies per topic
- **Regulatory Requirements**: SEBI compliance for Indian markets
- **Risk Management**: Built-in safeguards and circuit breakers

## Deployment Architecture

### Local Development
```yaml
Kafka Setup:
  - Docker Compose with Zookeeper
  - Single broker configuration
  - Local topics with minimal replication
  - Kafka UI for monitoring

Application Services:
  - All services in single Python process
  - Shared Kafka system instance
  - In-memory caching fallback
```

### Production Deployment
```yaml
Managed Kafka:
  - Upstash/Confluent Cloud for managed Kafka
  - Multi-region replication
  - Professional monitoring and alerting
  - Automatic scaling and maintenance

Application Scaling:
  - Multiple service instances
  - Load balancing across consumers
  - Redis for distributed caching
  - Horizontal scaling per service type
```

This architecture provides a robust, scalable foundation for high-frequency trading operations while maintaining flexibility for future enhancements and integrations.