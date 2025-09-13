# 🔗 Kafka Integration Guide

## Overview

This guide explains how to integrate Kafka with your trading application components, including producers, consumers, and message handling patterns.

## Integration Architecture

```
┌─────────────────────────────────────────────────────────┐
│                Trading Application                       │
│                                                         │
│  ┌─────────────────┐    ┌─────────────────────────────┐ │
│  │ Market Data     │───▶│        Kafka Topics         │ │
│  │ Sources         │    │                             │ │
│  │                 │    │ • market_data.raw           │ │
│  │ • Upstox WS     │    │ • signals.breakout          │ │
│  │ • Angel One WS  │    │ • analytics.market          │ │
│  │ • Manual Events │    │ • ui.price_updates          │ │
│  └─────────────────┘    └─────────────────────────────┘ │
│                                    │                    │
│  ┌─────────────────────────────────┼──────────────────┐ │
│  │              Services           │                  │ │
│  │                                 ▼                  │ │
│  │ ┌─────────────────┐  ┌─────────────────┐          │ │
│  │ │ Strategy        │  │ Analytics       │          │ │
│  │ │ Engines         │  │ Engines         │          │ │
│  │ │                 │  │                 │          │ │
│  │ │ • Breakout      │  │ • Market        │          │ │
│  │ │ • Momentum      │  │ • Performance   │          │ │
│  │ │ • Gap Trading   │  │ • Risk          │          │ │
│  │ └─────────────────┘  └─────────────────┘          │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Getting Started

### 1. Kafka System Initialization

```python
# In your main application (app.py)
from services.simple_kafka_system import get_kafka_system

async def initialize_kafka():
    """Initialize Kafka system on application startup"""
    kafka_system = get_kafka_system()

    # Initialize the system
    success = await kafka_system.initialize()
    if success:
        # Start all consumers
        await kafka_system.start_system()
        logger.info("✅ Kafka system ready for trading operations")
        return kafka_system
    else:
        logger.warning("⚠️ Kafka initialization failed - continuing without Kafka")
        return None

# Usage in FastAPI lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    kafka_system = await initialize_kafka()
    app.state.kafka_system = kafka_system

    yield

    # Shutdown
    if kafka_system:
        await kafka_system.shutdown()
```

### 2. Publishing Market Data

```python
# In your WebSocket manager (centralized_ws_manager.py)
from services.simple_kafka_system import get_kafka_system

class CentralizedWSManager:
    def __init__(self):
        self.kafka_system = get_kafka_system()

    async def _stream_to_kafka(self, instrument_key: str, market_data: dict):
        """Stream market data to Kafka topics"""
        if not self.kafka_system:
            return  # Graceful degradation if Kafka unavailable

        # Prepare standardized message
        message = {
            "instrument_key": instrument_key,
            "timestamp": int(time.time() * 1000),
            "source": "centralized_ws_manager",
            "data": market_data,
            "processing_stage": "raw_ingestion"
        }

        # Publish to raw market data topic
        await self.kafka_system.publish_message(
            topic="trading.market_data.raw",
            message=message,
            key=instrument_key  # Partition by instrument
        )

        logger.debug(f"📤 Published market data for {instrument_key}")

    async def _process_live_feed(self, message: dict):
        """Process incoming WebSocket message"""
        try:
            feeds = message.get("feeds", {})

            for instrument_key, feed_data in feeds.items():
                # Process the feed data
                processed_data = self._extract_price_data(feed_data)

                # Stream to Kafka
                await self._stream_to_kafka(instrument_key, processed_data)

                # Also update local cache for immediate access
                await self._update_price_cache(instrument_key, processed_data)

        except Exception as e:
            logger.error(f"Error processing live feed: {e}")
```

### 3. Creating Strategy Consumer

```python
# Example: services/strategies/breakout_strategy_consumer.py
import asyncio
import json
from typing import Dict, Any
from services.simple_kafka_system import get_kafka_system
from services.enhanced_breakout_engine import EnhancedBreakoutEngine

class BreakoutStrategyConsumer:
    def __init__(self):
        self.kafka_system = get_kafka_system()
        self.breakout_engine = EnhancedBreakoutEngine()
        self.is_running = False

    async def start_consuming(self):
        """Start consuming market data for breakout analysis"""
        if not self.kafka_system:
            logger.warning("Kafka system not available - breakout consumer disabled")
            return

        self.is_running = True
        logger.info("🚀 Starting breakout strategy consumer")

        # Start consumer for market data
        await self.kafka_system.start_consumer(
            consumer_name="breakout_strategy",
            topics=["trading.market_data.raw"],
            message_handler=self._handle_market_data,
            consumer_config={
                "auto_offset_reset": "latest",
                "group_id": "breakout_strategy_group"
            }
        )

    async def _handle_market_data(self, message: Dict[str, Any], context: Dict[str, Any]):
        """Handle incoming market data for breakout analysis"""
        try:
            # Extract data from message
            instrument_key = message.get("instrument_key")
            market_data = message.get("data", {})
            timestamp = message.get("timestamp")

            # Analyze for breakout patterns
            signals = await self.breakout_engine.analyze_for_breakouts(
                instrument_key=instrument_key,
                market_data=market_data,
                timestamp=timestamp
            )

            # Publish any signals found
            for signal in signals:
                await self._publish_breakout_signal(signal)

        except Exception as e:
            logger.error(f"Error in breakout analysis: {e}")

    async def _publish_breakout_signal(self, signal: Dict[str, Any]):
        """Publish breakout signal to trading signals topic"""
        signal_message = {
            "signal_id": f"breakout_{signal['symbol']}_{int(time.time())}",
            "strategy_type": "breakout",
            "timestamp": int(time.time() * 1000),
            "signal_data": signal,
            "confidence": signal.get("confidence", 0.7),
            "action": signal.get("action", "HOLD")
        }

        await self.kafka_system.publish_message(
            topic="trading.signals.breakout",
            message=signal_message,
            key=signal["symbol"]
        )

        logger.info(f"📊 Published breakout signal: {signal['symbol']} - {signal['action']}")

    async def stop_consuming(self):
        """Stop the consumer gracefully"""
        self.is_running = False
        logger.info("🛑 Stopping breakout strategy consumer")
```

### 4. Creating Analytics Consumer

```python
# Example: services/analytics/market_analytics_consumer.py
class MarketAnalyticsConsumer:
    def __init__(self):
        self.kafka_system = get_kafka_system()
        self.analytics_engine = EnhancedMarketAnalytics()

    async def start_consuming(self):
        """Start consuming for market analytics"""
        await self.kafka_system.start_consumer(
            consumer_name="market_analytics",
            topics=["trading.market_data.raw"],
            message_handler=self._handle_analytics_processing,
            consumer_config={
                "auto_offset_reset": "latest",
                "group_id": "market_analytics_group"
            }
        )

    async def _handle_analytics_processing(self, message: Dict[str, Any], context: Dict[str, Any]):
        """Process market data for analytics"""
        try:
            # Extract market data
            instrument_key = message.get("instrument_key")
            market_data = message.get("data", {})

            # Calculate analytics metrics
            analytics_data = await self.analytics_engine.calculate_market_metrics(
                instrument_key=instrument_key,
                market_data=market_data
            )

            # Publish analytics results
            await self._publish_analytics_update(analytics_data)

        except Exception as e:
            logger.error(f"Error in analytics processing: {e}")

    async def _publish_analytics_update(self, analytics_data: Dict[str, Any]):
        """Publish analytics update"""
        analytics_message = {
            "update_type": "market_analytics",
            "timestamp": int(time.time() * 1000),
            "data": analytics_data
        }

        await self.kafka_system.publish_message(
            topic="trading.analytics.market",
            message=analytics_message,
            key="market_wide"
        )
```

## Integration Patterns

### 1. Producer Pattern
```python
class KafkaProducer:
    def __init__(self, topic: str):
        self.kafka_system = get_kafka_system()
        self.topic = topic

    async def publish(self, data: dict, key: str = None):
        """Publish data to Kafka topic"""
        if not self.kafka_system:
            return False

        message = {
            "timestamp": int(time.time() * 1000),
            "data": data,
            "source": self.__class__.__name__
        }

        success = await self.kafka_system.publish_message(
            topic=self.topic,
            message=message,
            key=key
        )

        return success
```

### 2. Consumer Pattern
```python
class KafkaConsumer:
    def __init__(self, topics: List[str], group_id: str):
        self.kafka_system = get_kafka_system()
        self.topics = topics
        self.group_id = group_id

    async def start(self, handler_function):
        """Start consuming messages"""
        if not self.kafka_system:
            logger.warning(f"Kafka not available - {self.group_id} consumer disabled")
            return

        await self.kafka_system.start_consumer(
            consumer_name=self.group_id,
            topics=self.topics,
            message_handler=handler_function,
            consumer_config={
                "group_id": self.group_id,
                "auto_offset_reset": "latest"
            }
        )
```

### 3. Request-Response Pattern
```python
class KafkaRequestResponse:
    def __init__(self):
        self.kafka_system = get_kafka_system()
        self.response_handlers = {}

    async def send_request(self, request_topic: str, response_topic: str, data: dict):
        """Send request and wait for response"""
        correlation_id = str(uuid.uuid4())

        # Set up response handler
        future = asyncio.Future()
        self.response_handlers[correlation_id] = future

        # Send request
        request_message = {
            "correlation_id": correlation_id,
            "response_topic": response_topic,
            "data": data,
            "timestamp": int(time.time() * 1000)
        }

        await self.kafka_system.publish_message(
            topic=request_topic,
            message=request_message,
            key=correlation_id
        )

        # Wait for response (with timeout)
        try:
            response = await asyncio.wait_for(future, timeout=30.0)
            return response
        except asyncio.TimeoutError:
            logger.error(f"Request timeout for correlation_id: {correlation_id}")
            return None
        finally:
            self.response_handlers.pop(correlation_id, None)
```

## Service Integration Examples

### 1. Order Execution Service
```python
# services/execution/kafka_order_executor.py
class KafkaOrderExecutor:
    def __init__(self):
        self.kafka_system = get_kafka_system()
        self.broker_manager = BrokerManager()

    async def start(self):
        """Start consuming trading signals"""
        # Subscribe to all signal topics
        signal_topics = [
            "trading.signals.breakout",
            "trading.signals.momentum",
            "trading.signals.gap"
        ]

        await self.kafka_system.start_consumer(
            consumer_name="order_executor",
            topics=signal_topics,
            message_handler=self._handle_trading_signal,
            consumer_config={
                "group_id": "order_execution_group",
                "auto_offset_reset": "latest"
            }
        )

    async def _handle_trading_signal(self, message: Dict[str, Any], context: Dict[str, Any]):
        """Process trading signal and execute order"""
        try:
            signal_data = message.get("signal_data", {})
            action = signal_data.get("action")
            symbol = signal_data.get("symbol")

            if action in ["BUY", "SELL"]:
                # Execute order through broker
                order_result = await self._execute_order(signal_data)

                # Publish execution result
                await self._publish_execution_result(order_result)

        except Exception as e:
            logger.error(f"Order execution error: {e}")

    async def _execute_order(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute order via broker API"""
        # Implementation depends on your broker integration
        return await self.broker_manager.place_order(signal_data)

    async def _publish_execution_result(self, result: Dict[str, Any]):
        """Publish order execution result"""
        await self.kafka_system.publish_message(
            topic="trading.execution.results",
            message=result,
            key=result.get("symbol")
        )
```

### 2. Risk Management Service
```python
# services/risk/kafka_risk_monitor.py
class KafkaRiskMonitor:
    def __init__(self):
        self.kafka_system = get_kafka_system()
        self.risk_limits = self._load_risk_limits()

    async def start(self):
        """Start monitoring all trading activities"""
        risk_topics = [
            "trading.execution.results",
            "trading.signals.*",  # All signal topics
            "trading.analytics.market"
        ]

        await self.kafka_system.start_consumer(
            consumer_name="risk_monitor",
            topics=risk_topics,
            message_handler=self._handle_risk_event,
            consumer_config={
                "group_id": "risk_monitoring_group"
            }
        )

    async def _handle_risk_event(self, message: Dict[str, Any], context: Dict[str, Any]):
        """Evaluate risk for each trading event"""
        topic = context.get("topic", "")

        if "execution.results" in topic:
            await self._check_execution_risk(message)
        elif "signals" in topic:
            await self._check_signal_risk(message)
        elif "analytics.market" in topic:
            await self._check_market_risk(message)

    async def _check_execution_risk(self, message: Dict[str, Any]):
        """Check risk after order execution"""
        # Implement position size, exposure, P&L checks
        risk_violation = self._evaluate_risk_metrics(message)

        if risk_violation:
            await self._publish_risk_alert(risk_violation)
```

## Message Format Standards

### 1. Market Data Message
```json
{
    "instrument_key": "NSE_EQ|INE318A01026",
    "timestamp": 1705123456789,
    "source": "centralized_ws_manager",
    "data": {
        "ltp": 3097.7,
        "change": 2.6,
        "volume": 31929,
        "high": 3115.4,
        "low": 3081.0
    },
    "processing_stage": "raw_ingestion",
    "correlation_id": "uuid-generated"
}
```

### 2. Trading Signal Message
```json
{
    "signal_id": "breakout_RELIANCE_1705123456",
    "strategy_type": "breakout",
    "action": "BUY",
    "symbol": "RELIANCE",
    "instrument_key": "NSE_EQ|INE318A01026",
    "timestamp": 1705123456789,
    "signal_data": {
        "entry_price": 3097.7,
        "stop_loss": 3080.0,
        "target": 3120.0,
        "quantity": 100
    },
    "confidence": 0.85,
    "risk_reward_ratio": 2.5
}
```

### 3. Analytics Update Message
```json
{
    "update_type": "market_analytics",
    "timestamp": 1705123456789,
    "data": {
        "market_sentiment": "bullish",
        "top_gainers": ["RELIANCE", "TCS", "HDFC"],
        "top_losers": ["WIPRO", "INFY"],
        "sector_performance": {
            "banking": 1.2,
            "it": -0.5,
            "energy": 2.1
        }
    },
    "calculation_period": "1h"
}
```

## Error Handling

### 1. Producer Error Handling
```python
async def publish_with_retry(self, topic: str, message: dict, key: str = None, max_retries: int = 3):
    """Publish message with retry logic"""
    for attempt in range(max_retries):
        try:
            success = await self.kafka_system.publish_message(topic, message, key)
            if success:
                return True
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                continue
            logger.error(f"Failed to publish after {max_retries} attempts: {e}")
            return False
    return False
```

### 2. Consumer Error Handling
```python
async def handle_message_with_error_handling(self, message: dict, context: dict):
    """Handle message with comprehensive error handling"""
    try:
        await self._process_message(message)
    except ValidationError as e:
        logger.error(f"Message validation failed: {e}")
        # Log but don't retry - bad data
    except NetworkError as e:
        logger.error(f"Network error processing message: {e}")
        # Could be retried later
        raise  # Re-raise for retry mechanism
    except Exception as e:
        logger.exception(f"Unexpected error processing message: {e}")
        # Log error but continue processing other messages
```

This integration guide provides the foundation for building robust, event-driven trading systems using Kafka as the central messaging backbone.