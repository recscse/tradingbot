# 🚀 HFT Kafka System - Complete Architecture & Implementation Guide

## Table of Contents
1. [System Overview](#system-overview)
2. [Data Flow Architecture](#data-flow-architecture)
3. [Topic Architecture & Design](#topic-architecture--design)
4. [Service Components](#service-components)
5. [Implementation Details](#implementation-details)
6. [Consumer Processing Logic](#consumer-processing-logic)
7. [Error Handling & Resilience](#error-handling--resilience)
8. [Performance Optimizations](#performance-optimizations)
9. [Monitoring & Observability](#monitoring--observability)

---

## System Overview

The HFT (High-Frequency Trading) Kafka system is designed for ultra-low latency market data distribution with sub-millisecond performance targets. It follows an event-driven architecture with clear separation of concerns.

### Core Principles
- **Single Source of Truth**: Raw market data flows through one entry point
- **Event-Driven Processing**: All components communicate via Kafka events
- **Zero-Copy Optimizations**: Minimal data transformations
- **Fault Tolerance**: Graceful degradation and recovery mechanisms
- **Scalable Architecture**: Horizontal scaling through partitions

### System Components
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│  Kafka Cluster   │───▶│   HFT Services  │
│                 │    │                  │    │                 │
│ • Upstox WS     │    │ • Raw Data       │    │ • Analytics     │
│ • Angel One WS  │    │ • Shared Memory  │    │ • Breakouts     │
│ • Dhan WS       │    │ • Strategy Feeds │    │ • Execution     │
│ • Zerodha WS    │    │ • UI Updates     │    │ • Monitoring    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

---

## Data Flow Architecture

### Phase 1: Data Ingestion (Priority 0 - Critical)
```
WebSocket Sources ──┐
                    │
Upstox WS Feed ─────┼──▶ CentralizedWSManager ──▶ hft.raw.market_data
                    │         (Single Entry)              (Topic)
Angel One WS ───────┘              │
                                   ▼
                            Data Validation
                            Format Standardization
                            Timestamp Enrichment
```

**Implementation**: `services/centralized_ws_manager.py`
```python
async def _hft_kafka_stream(self, instrument_key: str, live_feed_data: dict):
    """
    Single entry point for all market data - publishes to Kafka
    """
    standardized_data = {
        "instrument_key": instrument_key,
        "timestamp": int(time.time() * 1000),
        "source": "centralized_ws_manager",
        "data": live_feed_data,
        "processing_stage": "raw_ingestion"
    }
    
    await self.hft_system.publish_to_topic(
        "hft.raw.market_data", 
        standardized_data
    )
```

### Phase 2: Memory Bridge (Priority 1 - Critical)
```
hft.raw.market_data ──▶ MemoryBridge ──▶ hft.shared_memory.feed
        │                    │                     │
        ▼                    ▼                     ▼
   Raw Validation      Data Enrichment      Shared Memory
   Rate Limiting       Price Calculations    Distribution
   Duplicate Check     Volume Analysis       Load Balancing
```

**Consumer Group**: `hft_memory_bridge`
**Partitions**: 1 (sequential processing for data integrity)
**Retention**: 1 hour (30 minutes for recovery)

### Phase 3: Service Distribution (Priority 2-4)
```
hft.shared_memory.feed ──┬──▶ InstrumentRegistry ──▶ Price Tracking
                         │
                         ├──▶ BreakoutEngine ──▶ Strategy Signals
                         │
                         ├──▶ AnalyticsEngine ──▶ Market Analytics
                         │
                         ├──▶ PremarketBuilder ──▶ Candle Data
                         │
                         └──▶ ExecutionEngine ──▶ Trade Orders
```

### Phase 4: UI Broadcasting (Priority 5)
```
Service Outputs ──▶ UnifiedWebSocketManager ──▶ React Frontend
                           │
                           ├──▶ hft.ui.price_updates
                           ├──▶ Real-time Charts
                           ├──▶ Dashboard Updates
                           └──▶ Alert Notifications
```

---

## Topic Architecture & Design

### Topic Hierarchy
```
hft.
├── raw.
│   └── market_data              # Raw WebSocket data (Priority 0)
├── shared_memory.
│   └── feed                     # Processed shared data (Priority 1)
├── analytics.
│   └── market_data              # Analytics pipeline (Priority 2)
├── strategy.
│   ├── breakout                 # Breakout signals (Priority 3)
│   ├── momentum                 # Momentum signals (Priority 3)
│   ├── gap_trading              # Gap trading signals (Priority 3)
│   └── fibonacci                # Fibonacci signals (Priority 3)
├── execution.
│   └── signals                  # Trading execution (Priority 4)
├── ui.
│   └── price_updates            # UI updates (Priority 5)
└── premarket.
    └── candles                  # Premarket data (Specialized)
```

### Topic Configuration Details

#### Critical Topics (Priority 0-1)
```python
# hft.raw.market_data
{
    "partitions": 1,              # Sequential processing
    "replication_factor": 3,      # High availability
    "retention_ms": 3600000,      # 1 hour retention
    "segment_ms": 300000,         # 5-minute segments
    "min_in_sync_replicas": 2,    # Consistency guarantee
    "cleanup_policy": "delete"    # Time-based cleanup
}

# hft.shared_memory.feed  
{
    "partitions": 8,              # Parallel processing
    "replication_factor": 3,      # High availability
    "retention_ms": 1800000,      # 30 minutes retention
    "segment_ms": 180000,         # 3-minute segments
    "consumer_groups": [
        "instrument_registry_group",
        "breakout_engine_group", 
        "premarket_candle_group"
    ]
}
```

#### High-Performance Topics (Priority 2-3)
```python
# Strategy Topics
{
    "partitions": 4,              # Strategy parallelism
    "replication_factor": 2,      # Balance availability/performance
    "retention_ms": 3600000,      # 1 hour for analysis
    "segment_ms": 300000          # 5-minute segments
}

# Analytics Topic
{
    "partitions": 16,             # High concurrency
    "replication_factor": 2,      # Performance optimized
    "retention_ms": 7200000       # 2 hours for calculations
}
```

### Data Formats by Topic

#### hft.raw.market_data Format
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
                            "ltq": "1",
                            "cp": 3095.1
                        },
                        "marketLevel": {
                            "bidAskQuote": [...]
                        },
                        "marketOHLC": {
                            "ohlc": [...]
                        }
                    }
                }
            }
        }
    },
    "processing_stage": "raw_ingestion",
    "correlation_id": "uuid-12345"
}
```

#### hft.shared_memory.feed Format
```json
{
    "instrument_key": "NSE_EQ|INE318A01026",
    "timestamp": 1757308567467,
    "source": "memory_bridge",
    "processed_data": {
        "symbol": "RELIANCE",
        "exchange": "NSE",
        "ltp": 3097.7,
        "change": 2.6,
        "change_percent": 0.084,
        "volume": 31929,
        "high": 3115.4,
        "low": 3081.0,
        "open": 3094.0,
        "previous_close": 3095.1,
        "bid_price": 3097.4,
        "ask_price": 3097.9,
        "bid_quantity": 1,
        "ask_quantity": 2,
        "atp": 3096.11,
        "total_buy_qty": 49001,
        "total_sell_qty": 45374
    },
    "technical_indicators": {
        "sma_20": 3089.5,
        "ema_12": 3091.2,
        "rsi": 62.3,
        "macd": 5.4
    },
    "processing_stage": "enriched_memory",
    "correlation_id": "uuid-12345"
}
```

---

## Service Components

### 1. Centralized WebSocket Manager
**File**: `services/centralized_ws_manager.py`

**Responsibilities**:
- Single entry point for all WebSocket data
- Data validation and standardization  
- Kafka publishing to `hft.raw.market_data`
- Connection management and reconnection

**Key Methods**:
```python
async def _hft_kafka_stream(self, instrument_key: str, live_feed_data: dict)
async def _process_live_feed(self, message: dict)
async def _handle_connection_error(self, error: Exception)
```

**Configuration**:
- Ultra-low latency producer settings
- Zero-copy data handling
- Async event processing

### 2. HFT System Core
**File**: `services/hft/core.py`

**Responsibilities**:
- Kafka producer/consumer management
- Topic creation and configuration
- Consumer group coordination
- System health monitoring

**Key Components**:
```python
class HFTKafkaCore:
    async def initialize_system(self) -> bool
    async def start_system(self) -> bool
    async def publish_to_topic(self, topic: str, data: dict)
    async def create_consumer(self, topic: str, group_id: str)
```

### 3. Memory Bridge Service
**File**: `services/hft/memory_bridge.py`

**Responsibilities**:
- Consume from `hft.raw.market_data`
- Data enrichment and validation
- Technical indicator calculations
- Publish to `hft.shared_memory.feed`

**Processing Pipeline**:
```python
async def process_raw_data(self, raw_data: dict) -> dict:
    # 1. Validate data format
    validated_data = await self._validate_market_data(raw_data)
    
    # 2. Extract and standardize
    standardized = await self._standardize_format(validated_data)
    
    # 3. Calculate technical indicators
    enriched = await self._calculate_indicators(standardized)
    
    # 4. Publish to shared memory feed
    await self._publish_to_shared_feed(enriched)
```

### 4. Instrument Registry Service
**File**: `services/instrument_registry.py`

**Responsibilities**:
- Real-time price tracking
- Instrument metadata management
- Price history maintenance
- Alert trigger detection

**Consumer Configuration**:
```python
{
    "group_id": "instrument_registry_group",
    "topics": ["hft.shared_memory.feed"],
    "auto_offset_reset": "latest",
    "enable_auto_commit": True
}
```

### 5. Enhanced Breakout Engine
**File**: `services/enhanced_breakout_engine.py`

**Responsibilities**:
- Breakout pattern detection
- Strategy signal generation
- Risk assessment
- Alert notifications

**Processing Logic**:
```python
async def process_market_update(self, data: dict):
    # 1. Check for breakout patterns
    breakout_signals = await self._detect_breakouts(data)
    
    # 2. Validate signals against risk parameters
    validated_signals = await self._validate_signals(breakout_signals)
    
    # 3. Publish to strategy topic
    for signal in validated_signals:
        await self._publish_strategy_signal(signal)
```

### 6. Unified WebSocket Manager
**File**: `services/unified_websocket_manager.py`

**Responsibilities**:
- Frontend WebSocket connections
- Real-time data broadcasting
- Event subscription management
- Client connection handling

---

## Implementation Details

### Kafka Producer Configuration
```python
# Ultra-low latency settings
producer_config = {
    "linger_ms": 0,                    # Send immediately
    "max_batch_size": 1,               # Single message batches  
    "acks": 1,                         # Leader acknowledgment only
    "compression_type": "none",        # No compression overhead
    "request_timeout_ms": 100,         # 100ms timeout
}

# SASL Authentication (Production)
if KAFKA_SASL_USERNAME:
    producer_config.update({
        "security_protocol": "SASL_SSL",
        "sasl_mechanism": "SCRAM-SHA-256", 
        "sasl_plain_username": KAFKA_SASL_USERNAME,
        "sasl_plain_password": KAFKA_SASL_PASSWORD,
    })
```

### Consumer Configuration
```python
# High-throughput consumer settings
consumer_config = {
    "fetch_min_bytes": 1,              # Fetch immediately
    "fetch_max_wait_ms": 1,            # 1ms wait maximum
    "max_poll_records": 1000,          # Batch processing
    "session_timeout_ms": 10000,       # 10s session timeout
    "heartbeat_interval_ms": 3000,     # 3s heartbeat
    "auto_offset_reset": "latest",     # Start from latest
    "enable_auto_commit": True,        # Auto commit for speed
    "auto_commit_interval_ms": 1000,   # 1s commit interval
}
```

### Topic Creation Logic
```python
async def create_hft_topics(self):
    """Create all HFT topics with optimized configurations"""
    topic_manager = get_topic_manager()
    admin_client = AIOKafkaAdminClient(
        bootstrap_servers=self.bootstrap_servers,
        **self.auth_config
    )
    
    try:
        # Get topic configurations
        topic_configs = topic_manager.get_topic_creation_configs()
        
        # Create topics in parallel
        tasks = []
        for config in topic_configs:
            task = self._create_single_topic(admin_client, config)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is not False)
        logger.info(f"✅ Created {success_count}/{len(topic_configs)} HFT topics")
        
    finally:
        await admin_client.close()
```

---

## Consumer Processing Logic

### 1. Memory Bridge Consumer
```python
class MemoryBridgeConsumer:
    async def start_consuming(self):
        consumer = AIOKafkaConsumer(
            "hft.raw.market_data",
            bootstrap_servers=self.bootstrap_servers,
            group_id="hft_memory_bridge",
            **self.consumer_config
        )
        
        await consumer.start()
        try:
            async for message in consumer:
                await self._process_message(message)
        finally:
            await consumer.stop()
    
    async def _process_message(self, message):
        try:
            # Parse message
            raw_data = json.loads(message.value.decode('utf-8'))
            
            # Process data
            processed_data = await self._enrich_market_data(raw_data)
            
            # Publish to shared feed
            await self._publish_to_shared_feed(processed_data)
            
        except Exception as e:
            logger.error(f"Memory bridge processing error: {e}")
```

### 2. Service Consumer Pattern
```python
class ServiceConsumer:
    def __init__(self, service_name: str, topics: List[str]):
        self.service_name = service_name
        self.topics = topics
        self.group_id = f"{service_name}_group"
        
    async def start_consuming(self):
        consumer = AIOKafkaConsumer(
            *self.topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            **self.consumer_config
        )
        
        await consumer.start()
        try:
            async for message in consumer:
                await self._route_message(message)
        finally:
            await consumer.stop()
    
    async def _route_message(self, message):
        topic = message.topic
        handler = self._get_handler(topic)
        if handler:
            await handler(message)
```

### 3. Error Handling in Consumers
```python
async def _process_with_retry(self, message, max_retries=3):
    """Process message with retry logic"""
    for attempt in range(max_retries):
        try:
            await self._process_message(message)
            return
        except RetryableError as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise
        except NonRetryableError:
            logger.error(f"Non-retryable error processing message: {message}")
            return  # Skip message
```

This comprehensive architecture ensures ultra-low latency, high reliability, and scalable market data processing for your HFT trading system.