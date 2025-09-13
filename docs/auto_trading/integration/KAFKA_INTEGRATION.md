# Kafka Integration Guide

## Overview

This guide provides comprehensive instructions for integrating and configuring Apache Kafka within the Auto Trading System. Kafka serves as the central nervous system for high-frequency data processing, real-time analytics, and inter-component communication.

## Architecture Overview

### Kafka Ecosystem Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Kafka Ecosystem                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   HFT Producer  │  │  HFT Consumer   │  │ Analytics Bridge│  │
│  │                 │  │                 │  │                 │  │
│  │ • Market Data   │  │ • Position Mon  │  │ • SSE Streaming │  │
│  │ • Trade Events  │  │ • Risk Manager  │  │ • UI Updates    │  │
│  │ • System Events │  │ • Strategy Exec │  │ • Notifications │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Kafka Topics                               │
├─────────────────┬───────────────────┬───────────────────────────┤
│ Market Data     │ Analytics         │ System Events             │
│                 │                   │                           │
│ • hft.market_data│ • hft.analytics  │ • hft.trading.signals     │
│ • hft.price_updates│ • hft.features │ • hft.trading.executions  │
│ • hft.trades    │ • hft.stock_selection│ • hft.system.alerts    │
└─────────────────┴───────────────────┴───────────────────────────┘
```

## Topic Structure and Configuration

### Core Topic Definitions

| Topic Name | Purpose | Partitions | Retention | Key Schema |
|------------|---------|------------|-----------|------------|
| `hft.market_data` | Raw market data from brokers | 10 | 1 hour | instrument_key |
| `hft.analytics.market_data` | Processed market analytics | 5 | 4 hours | instrument_key |
| `hft.analytics.features` | Calculated technical features | 3 | 8 hours | instrument_key |
| `hft.trading.signals` | Generated trading signals | 5 | 24 hours | user_session |
| `hft.trading.executions` | Trade execution results | 3 | 7 days | user_id |
| `hft.trading.positions` | Position updates | 3 | 7 days | position_id |
| `hft.trading.pnl_updates` | PnL calculation results | 2 | 7 days | session_id |
| `hft.trading.risk_events` | Risk alerts and events | 1 | 7 days | user_id |
| `hft.ui.price_updates` | UI-specific price updates | 2 | 30 minutes | channel_id |
| `hft.system.health` | System health metrics | 1 | 24 hours | component |

### Topic Configuration

```python
# Kafka topic configurations
KAFKA_TOPICS_CONFIG = {
    "hft.market_data": {
        "num_partitions": 10,
        "replication_factor": 3,
        "config": {
            "retention.ms": 3600000,  # 1 hour
            "cleanup.policy": "delete",
            "compression.type": "lz4",
            "min.insync.replicas": 2,
            "unclean.leader.election.enable": False
        }
    },
    "hft.analytics.market_data": {
        "num_partitions": 5,
        "replication_factor": 3,
        "config": {
            "retention.ms": 14400000,  # 4 hours
            "cleanup.policy": "delete",
            "compression.type": "lz4",
            "segment.ms": 600000  # 10 minutes
        }
    },
    "hft.trading.signals": {
        "num_partitions": 5,
        "replication_factor": 3,
        "config": {
            "retention.ms": 86400000,  # 24 hours
            "cleanup.policy": "delete",
            "compression.type": "snappy"
        }
    }
}
```

## HFT Producer Configuration

### High-Performance Producer Setup

```python
from services.hft.hft_producer import HFTProducer

class OptimizedHFTProducer(HFTProducer):
    """
    High-performance Kafka producer optimized for HFT systems.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize HFT producer with optimized settings.
        
        Args:
            config: Producer configuration dictionary
        """
        # Merge with HFT-optimized defaults
        hft_config = {
            # Performance optimizations
            "batch.size": 65536,              # 64KB batch size
            "linger.ms": 1,                   # Minimal batching delay
            "compression.type": "lz4",        # Fast compression
            "buffer.memory": 134217728,       # 128MB buffer
            
            # Reliability settings
            "acks": "1",                      # Wait for leader acknowledgment
            "retries": 3,                     # Retry failed sends
            "retry.backoff.ms": 100,          # Quick retry backoff
            "max.in.flight.requests.per.connection": 5,
            
            # Timeout settings
            "request.timeout.ms": 5000,       # 5 second timeout
            "delivery.timeout.ms": 10000,     # 10 second delivery timeout
            
            # Serialization
            "key.serializer": "org.apache.kafka.common.serialization.StringSerializer",
            "value.serializer": "org.apache.kafka.common.serialization.StringSerializer",
            
            **config
        }
        
        super().__init__(hft_config)
        self._metrics = ProducerMetrics()
    
    async def produce_market_data(
        self, 
        instrument_key: str, 
        market_data: Dict[str, Any]
    ) -> None:
        """
        Produce market data with optimized routing.
        
        Args:
            instrument_key: Instrument identifier for partitioning
            market_data: Market data payload
        """
        start_time = time.perf_counter()
        
        try:
            # Add metadata
            enriched_data = {
                **market_data,
                "producer_timestamp": datetime.now().isoformat(),
                "instrument_key": instrument_key
            }
            
            # Produce to market data topic
            await self.produce_message(
                topic="hft.market_data",
                key=instrument_key,
                message=enriched_data
            )
            
            # Track metrics
            processing_time = (time.perf_counter() - start_time) * 1000
            self._metrics.record_market_data_sent(processing_time)
            
        except Exception as e:
            logger.error(f"Failed to produce market data for {instrument_key}: {e}")
            self._metrics.record_error("market_data_production")
            raise
    
    async def produce_trading_signal(
        self,
        user_id: int,
        session_id: str,
        signal_data: Dict[str, Any]
    ) -> None:
        """
        Produce trading signal with user-based partitioning.
        
        Args:
            user_id: User identifier
            session_id: Trading session ID
            signal_data: Signal payload
        """
        try:
            # Create partition key for consistent routing
            partition_key = f"user_{user_id}_session_{session_id}"
            
            # Enrich signal data
            enriched_signal = {
                **signal_data,
                "user_id": user_id,
                "session_id": session_id,
                "signal_timestamp": datetime.now().isoformat()
            }
            
            # Produce to signals topic
            await self.produce_message(
                topic="hft.trading.signals",
                key=partition_key,
                message=enriched_signal
            )
            
            self._metrics.record_signal_sent()
            
        except Exception as e:
            logger.error(f"Failed to produce trading signal for user {user_id}: {e}")
            self._metrics.record_error("signal_production")
            raise
```

## HFT Consumer Configuration

### Optimized Consumer Implementation

```python
from services.hft.base_hft_consumer import BaseHFTConsumer

class OptimizedHFTConsumer(BaseHFTConsumer):
    """
    High-performance Kafka consumer with batch processing.
    """
    
    def __init__(
        self, 
        topics: List[str], 
        consumer_group: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize optimized HFT consumer.
        
        Args:
            topics: List of topics to consume
            consumer_group: Consumer group ID
            config: Additional consumer configuration
        """
        # HFT-optimized consumer config
        hft_config = {
            # Performance settings
            "fetch.min.bytes": 1024,          # Minimum fetch size
            "fetch.max.wait.ms": 10,          # Low latency fetch
            "max.poll.records": 1000,         # Batch processing size
            "max.poll.interval.ms": 30000,    # 30 second poll interval
            
            # Memory and network optimization
            "receive.buffer.bytes": 262144,   # 256KB receive buffer
            "send.buffer.bytes": 131072,      # 128KB send buffer
            "fetch.max.bytes": 10485760,      # 10MB max fetch
            
            # Offset management
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,      # Manual offset management
            
            # Session and heartbeat
            "session.timeout.ms": 10000,      # 10 second session timeout
            "heartbeat.interval.ms": 3000,    # 3 second heartbeat
            
            # Deserialization
            "key.deserializer": "org.apache.kafka.common.serialization.StringDeserializer",
            "value.deserializer": "org.apache.kafka.common.serialization.StringDeserializer",
            
            **(config or {})
        }
        
        super().__init__(topics, consumer_group, hft_config)
        self._metrics = ConsumerMetrics()
        self._processing_queue = asyncio.Queue(maxsize=10000)
    
    async def process_messages(self, messages: List[Dict[str, Any]]) -> None:
        """
        Process messages with batch optimization.
        
        Args:
            messages: List of messages to process
        """
        if not messages:
            return
        
        start_time = time.perf_counter()
        
        try:
            # Group messages by type for efficient processing
            grouped_messages = self._group_messages_by_type(messages)
            
            # Process each group concurrently
            processing_tasks = []
            for message_type, message_group in grouped_messages.items():
                task = asyncio.create_task(
                    self._process_message_group(message_type, message_group)
                )
                processing_tasks.append(task)
            
            # Wait for all processing to complete
            await asyncio.gather(*processing_tasks)
            
            # Track metrics
            processing_time = (time.perf_counter() - start_time) * 1000
            self._metrics.record_batch_processed(len(messages), processing_time)
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            self._metrics.record_processing_error(len(messages))
            raise
    
    def _group_messages_by_type(
        self, 
        messages: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group messages by type for efficient batch processing"""
        grouped = {}
        
        for message in messages:
            message_type = self._determine_message_type(message)
            if message_type not in grouped:
                grouped[message_type] = []
            grouped[message_type].append(message)
        
        return grouped
    
    async def _process_message_group(
        self, 
        message_type: str, 
        messages: List[Dict[str, Any]]
    ) -> None:
        """Process a group of messages of the same type"""
        try:
            if message_type == "market_data":
                await self._process_market_data_batch(messages)
            elif message_type == "trading_signal":
                await self._process_trading_signals_batch(messages)
            elif message_type == "position_update":
                await self._process_position_updates_batch(messages)
            else:
                # Handle unknown message types
                await self._process_generic_messages(messages)
                
        except Exception as e:
            logger.error(f"Failed to process {message_type} group: {e}")
            raise
```

## Analytics Integration

### Real-Time Analytics Engine Integration

```python
class KafkaAnalyticsIntegration:
    """
    Integration layer between Kafka and analytics services.
    """
    
    def __init__(
        self, 
        kafka_config: Dict[str, Any],
        analytics_config: Dict[str, Any]
    ):
        """
        Initialize Kafka-Analytics integration.
        
        Args:
            kafka_config: Kafka connection configuration
            analytics_config: Analytics engine configuration
        """
        self.kafka_config = kafka_config
        self.analytics_config = analytics_config
        
        # Initialize components
        self._producer = OptimizedHFTProducer(kafka_config)
        self._analytics_consumer = None
        self._features_producer = None
        
        # Analytics engines
        self._analytics_engine = None
        self._stock_selector = None
        self._sse_bridge = None
    
    async def initialize(self) -> None:
        """Initialize all integration components"""
        try:
            # Initialize producer
            await self._producer.initialize()
            
            # Initialize analytics consumer
            self._analytics_consumer = OptimizedHFTConsumer(
                topics=["hft.analytics.market_data"],
                consumer_group="analytics_engine_group",
                config=self.kafka_config
            )
            
            # Initialize features producer
            self._features_producer = OptimizedHFTProducer(self.kafka_config)
            await self._features_producer.initialize()
            
            # Initialize analytics engines
            from services.analytics.real_time_analytics_engine import RealTimeAnalyticsEngine
            from services.stock_selection.real_time_stock_selector import RealTimeStockSelector
            from services.analytics.kafka_sse_bridge import KafkaSSEBridge
            
            self._analytics_engine = RealTimeAnalyticsEngine(
                ["hft.analytics.market_data"],
                "analytics_engine_group"
            )
            
            self._stock_selector = RealTimeStockSelector(
                ["hft.analytics.features"],
                "stock_selector_group"
            )
            
            self._sse_bridge = KafkaSSEBridge(
                ["hft.ui.price_updates", "hft.trading.signals"],
                "sse_bridge_group"
            )
            
            logger.info("Kafka analytics integration initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kafka analytics integration: {e}")
            raise
    
    async def start_analytics_pipeline(self) -> None:
        """Start the complete analytics pipeline"""
        try:
            # Start analytics engine
            analytics_task = asyncio.create_task(
                self._analytics_engine.start_consuming()
            )
            
            # Start stock selector
            selector_task = asyncio.create_task(
                self._stock_selector.start_consuming()
            )
            
            # Start SSE bridge
            sse_task = asyncio.create_task(
                self._sse_bridge.start_consuming()
            )
            
            # Monitor tasks
            await asyncio.gather(
                analytics_task,
                selector_task, 
                sse_task,
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"Analytics pipeline failed: {e}")
            raise
    
    async def publish_market_analytics(
        self, 
        analytics_data: Dict[str, Any]
    ) -> None:
        """
        Publish calculated analytics to appropriate topics.
        
        Args:
            analytics_data: Calculated analytics results
        """
        try:
            # Publish features to features topic
            if "features" in analytics_data:
                await self._features_producer.produce_message(
                    topic="hft.analytics.features",
                    key=analytics_data.get("instrument_key"),
                    message=analytics_data["features"]
                )
            
            # Publish UI updates
            if "ui_updates" in analytics_data:
                await self._producer.produce_message(
                    topic="hft.ui.price_updates",
                    key=analytics_data.get("channel_id", "general"),
                    message=analytics_data["ui_updates"]
                )
            
            # Publish stock selection results
            if "selected_stocks" in analytics_data:
                await self._producer.produce_message(
                    topic="hft.trading.stock_selection",
                    key=f"selection_{datetime.now().strftime('%Y%m%d_%H%M')}",
                    message=analytics_data["selected_stocks"]
                )
            
        except Exception as e:
            logger.error(f"Failed to publish analytics: {e}")
            raise
```

## Performance Optimization

### Producer Optimization Strategies

```python
class HighPerformanceKafkaProducer:
    """
    Ultra-high-performance Kafka producer for HFT systems.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with performance-optimized settings"""
        self.config = {
            # Ultra-low latency settings
            "linger.ms": 0,                   # No batching delay
            "batch.size": 131072,             # 128KB batches
            "buffer.memory": 268435456,       # 256MB buffer
            "compression.type": "lz4",        # Fastest compression
            
            # Connection optimization
            "max.in.flight.requests.per.connection": 1,  # Strict ordering
            "tcp.nodelay": True,              # Disable Nagle's algorithm
            "socket.send.buffer.bytes": 1048576,  # 1MB send buffer
            
            # Minimal acknowledgment for speed
            "acks": "0",                      # No wait for acknowledgment
            "retries": 0,                     # No retries for maximum speed
            
            **config
        }
        
        self._producer = None
        self._send_queue = asyncio.Queue(maxsize=100000)
        self._metrics = PerformanceMetrics()
    
    async def ultra_fast_send(
        self, 
        topic: str, 
        key: str, 
        message: Dict[str, Any]
    ) -> None:
        """
        Ultra-fast message sending with minimal overhead.
        
        Args:
            topic: Kafka topic
            key: Message key
            message: Message payload
        """
        # Pre-serialize for speed
        serialized_message = json.dumps(message, separators=(',', ':'))
        
        # Direct send without async/await overhead
        try:
            self._producer.produce(
                topic=topic,
                key=key,
                value=serialized_message,
                callback=self._delivery_callback
            )
            
            # Flush immediately for ultra-low latency
            self._producer.flush(timeout=0.001)  # 1ms flush timeout
            
        except Exception as e:
            # Minimal error handling for speed
            self._metrics.record_error()
```

### Consumer Optimization Strategies

```python
class HighPerformanceKafkaConsumer:
    """
    Ultra-high-performance Kafka consumer with batch processing.
    """
    
    def __init__(self, topics: List[str], consumer_group: str):
        """Initialize with performance-optimized settings"""
        self.config = {
            # High-throughput settings
            "max.poll.records": 10000,        # Large batch sizes
            "fetch.min.bytes": 10240,         # 10KB minimum fetch
            "fetch.max.wait.ms": 1,           # 1ms maximum wait
            "receive.buffer.bytes": 2097152,  # 2MB receive buffer
            
            # Memory optimization
            "max.partition.fetch.bytes": 10485760,  # 10MB per partition
            "session.timeout.ms": 30000,     # 30 second timeout
            "heartbeat.interval.ms": 10000,   # 10 second heartbeat
            
            # Offset management for performance
            "enable.auto.commit": False,      # Manual commits for control
            "auto.offset.reset": "latest"
        }
        
        self._consumer = None
        self._processing_pool = ThreadPoolExecutor(max_workers=8)
        self._metrics = ConsumerPerformanceMetrics()
    
    async def high_speed_consume(self) -> None:
        """High-speed message consumption with parallel processing"""
        while True:
            try:
                # Poll for messages with minimal timeout
                messages = self._consumer.poll(timeout_ms=1)
                
                if messages:
                    # Process messages in parallel
                    await self._parallel_process_messages(messages)
                    
                    # Commit offsets asynchronously
                    self._consumer.commit_async()
                
                # Yield control briefly
                await asyncio.sleep(0.001)  # 1ms yield
                
            except Exception as e:
                logger.error(f"High-speed consumption error: {e}")
                await asyncio.sleep(0.01)  # Brief pause on error
```

## Monitoring and Metrics

### Kafka Performance Monitoring

```python
class KafkaPerformanceMonitor:
    """
    Comprehensive Kafka performance monitoring system.
    """
    
    def __init__(self):
        """Initialize monitoring system"""
        self.metrics = {
            "producer": {
                "messages_sent": 0,
                "bytes_sent": 0,
                "send_errors": 0,
                "average_latency_ms": 0.0,
                "throughput_msg_per_sec": 0.0
            },
            "consumer": {
                "messages_consumed": 0,
                "bytes_consumed": 0,
                "processing_errors": 0,
                "average_processing_time_ms": 0.0,
                "lag_ms": 0.0
            },
            "system": {
                "active_producers": 0,
                "active_consumers": 0,
                "topic_health": {},
                "broker_connectivity": True
            }
        }
        
        self._start_time = time.time()
        self._latency_samples = []
        self._throughput_samples = []
    
    def record_producer_metrics(
        self, 
        messages_sent: int, 
        bytes_sent: int, 
        latency_ms: float
    ) -> None:
        """Record producer performance metrics"""
        self.metrics["producer"]["messages_sent"] += messages_sent
        self.metrics["producer"]["bytes_sent"] += bytes_sent
        
        # Update latency
        self._latency_samples.append(latency_ms)
        if len(self._latency_samples) > 1000:
            self._latency_samples = self._latency_samples[-1000:]
        
        self.metrics["producer"]["average_latency_ms"] = (
            sum(self._latency_samples) / len(self._latency_samples)
        )
        
        # Calculate throughput
        elapsed_time = time.time() - self._start_time
        if elapsed_time > 0:
            self.metrics["producer"]["throughput_msg_per_sec"] = (
                self.metrics["producer"]["messages_sent"] / elapsed_time
            )
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": time.time() - self._start_time,
            "metrics": self.metrics,
            "health_status": self._assess_system_health(),
            "recommendations": self._generate_recommendations()
        }
    
    def _assess_system_health(self) -> Dict[str, Any]:
        """Assess overall system health"""
        health = {
            "status": "healthy",
            "issues": []
        }
        
        # Check latency
        avg_latency = self.metrics["producer"]["average_latency_ms"]
        if avg_latency > 100:  # > 100ms is concerning
            health["issues"].append(f"High producer latency: {avg_latency:.2f}ms")
            health["status"] = "degraded"
        
        # Check error rates
        total_sent = self.metrics["producer"]["messages_sent"]
        send_errors = self.metrics["producer"]["send_errors"]
        if total_sent > 0 and (send_errors / total_sent) > 0.01:  # > 1% error rate
            error_rate = (send_errors / total_sent) * 100
            health["issues"].append(f"High error rate: {error_rate:.2f}%")
            health["status"] = "unhealthy"
        
        return health
```

## Configuration Examples

### Development Environment

```python
# Development Kafka configuration
DEVELOPMENT_KAFKA_CONFIG = {
    "bootstrap.servers": "localhost:9092",
    "client.id": "auto_trading_dev",
    
    # Relaxed settings for development
    "acks": "1",
    "retries": 3,
    "linger.ms": 10,
    "batch.size": 16384,
    "buffer.memory": 33554432,
    
    # Development-friendly settings
    "compression.type": "none",
    "max.in.flight.requests.per.connection": 5,
    "request.timeout.ms": 30000,
    "delivery.timeout.ms": 120000,
    
    # Security (if needed)
    "security.protocol": "PLAINTEXT"
}
```

### Production Environment

```python
# Production Kafka configuration
PRODUCTION_KAFKA_CONFIG = {
    "bootstrap.servers": "kafka1:9092,kafka2:9092,kafka3:9092",
    "client.id": "auto_trading_prod",
    
    # High-performance production settings
    "acks": "1",                              # Balance between performance and durability
    "retries": 2147483647,                    # Infinite retries
    "linger.ms": 1,                           # Minimal batching delay
    "batch.size": 65536,                      # 64KB batches
    "buffer.memory": 134217728,               # 128MB buffer
    
    # Compression for network efficiency
    "compression.type": "lz4",
    
    # Connection optimization
    "max.in.flight.requests.per.connection": 5,
    "request.timeout.ms": 10000,
    "delivery.timeout.ms": 30000,
    
    # Security
    "security.protocol": "SSL",
    "ssl.truststore.location": "/path/to/truststore.jks",
    "ssl.truststore.password": "${SSL_TRUSTSTORE_PASSWORD}",
    "ssl.keystore.location": "/path/to/keystore.jks",
    "ssl.keystore.password": "${SSL_KEYSTORE_PASSWORD}",
    
    # Monitoring
    "metric.reporters": "io.confluent.metrics.reporter.ConfluentMetricsReporter",
    "confluent.metrics.reporter.bootstrap.servers": "kafka1:9092,kafka2:9092,kafka3:9092"
}
```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. High Latency Issues

```python
# Diagnosis and solution for high latency
async def diagnose_latency_issues():
    """Diagnose and resolve Kafka latency issues"""
    
    # Check producer configuration
    producer_issues = []
    
    if producer_config.get("linger.ms", 0) > 5:
        producer_issues.append("linger.ms too high for HFT")
    
    if producer_config.get("batch.size", 0) > 131072:
        producer_issues.append("batch.size may be too large")
    
    if producer_config.get("compression.type") not in ["lz4", "none"]:
        producer_issues.append("compression type not optimized for speed")
    
    # Recommended fixes
    optimized_config = {
        "linger.ms": 1,
        "batch.size": 65536,
        "compression.type": "lz4",
        "acks": "1"
    }
    
    return {
        "issues": producer_issues,
        "recommended_config": optimized_config
    }
```

#### 2. Consumer Lag Issues

```python
# Monitor and resolve consumer lag
async def resolve_consumer_lag():
    """Monitor and resolve consumer lag issues"""
    
    # Check consumer configuration
    lag_solutions = []
    
    # Increase batch processing
    if consumer_config.get("max.poll.records", 0) < 1000:
        lag_solutions.append("Increase max.poll.records to 1000+")
    
    # Optimize fetch settings
    if consumer_config.get("fetch.min.bytes", 0) < 1024:
        lag_solutions.append("Increase fetch.min.bytes for better throughput")
    
    # Parallel processing recommendation
    lag_solutions.append("Implement parallel message processing")
    
    return lag_solutions
```

#### 3. Connection Issues

```python
# Resolve Kafka connection problems
async def resolve_connection_issues():
    """Diagnose and resolve Kafka connection issues"""
    
    connection_checks = {
        "broker_connectivity": await check_broker_connectivity(),
        "dns_resolution": await check_dns_resolution(),
        "port_accessibility": await check_port_accessibility(),
        "ssl_configuration": await validate_ssl_config(),
        "authentication": await validate_authentication()
    }
    
    failed_checks = [
        check for check, result in connection_checks.items() 
        if not result
    ]
    
    return {
        "status": "healthy" if not failed_checks else "unhealthy",
        "failed_checks": failed_checks,
        "recommendations": generate_connection_recommendations(failed_checks)
    }
```

This Kafka Integration Guide provides comprehensive instructions for implementing high-performance Kafka integration within the Auto Trading System, ensuring optimal data flow and system performance.