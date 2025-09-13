# 🚀 Complete Kafka Setup Guide

## 📋 Overview

This comprehensive guide provides detailed setup instructions for Apache Kafka in various environments, specifically optimized for the trading application's requirements. The system uses Kafka for distributing live market data to multiple services efficiently.

## 🏠 Local Development Setup

### Prerequisites

1. **Python Dependencies**
   ```bash
   pip install aiokafka kafka-python
   ```

2. **Choose Your Kafka Approach** (in order of recommendation):
   - **🥇 Docker**: Easy, consistent
   - **🥈 KRaft Mode**: Modern, no Zookeeper
   - **🥉 Managed Kafka**: No local install needed
   - **❌ Traditional Zookeeper**: Deprecated, complex

### Option 1: Docker Setup (Recommended)

#### Step 1: Start Kafka
```bash
# Start Kafka and Zookeeper
docker-compose -f docker-compose.kafka.yml up -d

# Check if services are running
docker-compose -f docker-compose.kafka.yml ps
```

#### Step 2: Create Topics
```bash
# Create all required topics
python setup_kafka_topics.py
```

#### Step 3: Start Your Application
```bash
# Start the trading application
python app.py
```

**Expected Output:**
```
🚀 Initializing Kafka System...
✅ Kafka system initialized successfully
🚀 Kafka consumers started successfully
```

#### Step 4: Monitor (Optional)
- **Kafka UI**: http://localhost:8080 (see topics, messages, consumers)
- **Application logs**: Watch for Kafka streaming messages

### Option 2: KRaft Mode (Modern, No Zookeeper)

**Recommended for learning and custom configurations**

#### Step 1: Start Kafka in KRaft Mode
```bash
# Quick start with automated script
start_kafka_kraft.bat

# Or manual setup:
cd kafka\kafka_2.13-4.1.0

# Generate cluster ID (first time only)
bin\windows\kafka-storage.bat random-uuid > cluster_id.txt
set /p CLUSTER_ID=<cluster_id.txt

# Format storage
bin\windows\kafka-storage.bat format -t %CLUSTER_ID% -c config\kraft\server.properties

# Start Kafka server
bin\windows\kafka-server-start.bat config\kraft\server.properties
```

#### Step 2: Create Topics & Start App
```bash
# Create topics
python setup_kafka_topics.py

# Start application
python app.py
```

**Expected Output:**
```
🚀 Kafka KRaft mode started
✅ Cluster ID generated: abc123-def456-ghi789
✅ Storage formatted successfully
✅ Kafka server ready on localhost:9092
🎯 No Zookeeper dependency!
```

### Option 3: Traditional Setup (Deprecated)

**⚠️ Not recommended - shown for reference only**

1. Download Kafka from https://kafka.apache.org/downloads
2. Start Zookeeper: `bin/zookeeper-server-start.sh config/zookeeper.properties`
3. Start Kafka: `bin/kafka-server-start.sh config/server.properties`
4. Create topics: `python setup_kafka_topics.py`

## 🌐 Production Deployment (Cloud/Render)

### Environment Variables

Set these in your deployment environment:

```bash
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=your-kafka-cluster:9092
KAFKA_CLIENT_ID=trading_app_prod

# Optional Performance Tuning
KAFKA_PRODUCER_LINGER_MS=0
KAFKA_PRODUCER_BATCH_SIZE=1
KAFKA_CONSUMER_FETCH_MAX_WAIT_MS=1
```

### Managed Kafka Services

#### Option 1: Upstash (Recommended - FREE Tier)
1. Create account at https://upstash.com
2. Create Kafka cluster (FREE tier available)
3. Get connection details:
```bash
KAFKA_BOOTSTRAP_SERVERS=tops-stingray-12345-us1-kafka.upstash.io:9092
KAFKA_SASL_USERNAME=dG9wcy1zdGluZ3JheS0xMjM0NSQ...
KAFKA_SASL_PASSWORD=your-password
KAFKA_SASL_MECHANISM=SCRAM-SHA-256
KAFKA_SECURITY_PROTOCOL=SASL_SSL
```

#### Option 2: CloudKarafka (Alternative)
1. Create account at https://cloudkarafka.com
2. Free tier: 25MB storage
3. Get connection details from dashboard

#### Option 3: Confluent Cloud (Premium)
1. Create account at https://confluent.cloud
2. Basic cluster: $1/hour when running
3. Get bootstrap servers and API keys

### Render.com Deployment

#### render.yaml Configuration
```yaml
services:
  - type: web
    name: trading-app
    env: python
    plan: starter
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python app.py"
    envVars:
      - key: KAFKA_BOOTSTRAP_SERVERS
        value: your-kafka-endpoint:9092
      - key: DATABASE_URL
        fromDatabase:
          name: trading-db
          property: connectionString
```

## 🔧 System Architecture

### Data Flow
```
Upstox WebSocket → CentralizedWSManager → Producer → Kafka Topics
                                                        ↓
Multiple Services ← Consumers ← Kafka Topics ← Memory Bridge
```

### Kafka Topics

| Topic | Purpose | Partitions | Consumers |
|-------|---------|------------|-----------|
| `trading.market_data.raw` | Raw data from WebSocket | 3 | Memory Bridge |
| `trading.market_data.processed` | Processed market data | 3 | All services |
| `trading.signals.breakout` | Breakout signals | 2 | Trading engine |
| `trading.signals.gap` | Gap analysis | 2 | Gap detector |
| `trading.analytics.market` | Market analytics | 2 | Dashboard |
| `trading.system.events` | System events | 2 | Monitoring |
| `trading.ui.price_updates` | UI updates | 1 | Frontend |

### Services & Consumers

| Service | Consumer | Purpose |
|---------|----------|---------|
| **Instrument Registry** | `InstrumentRegistryConsumer` | Price cache updates |
| **Enhanced Breakout Engine** | `BreakoutEngineConsumer` | Pattern detection |
| **Market Analytics** | `MarketAnalyticsConsumer` | Real-time analysis |
| **Premarket Candle Builder** | `PremarketConsumer` | Candle building |

## 🚀 Testing & Verification

### Quick Health Check
```bash
# Check if Kafka is working
python -c "
import asyncio
from services.simple_kafka_system import get_kafka_system

async def test():
    system = get_kafka_system()
    status = system.get_system_status()
    print(f'Kafka System: {status}')

asyncio.run(test())
"
```

### Live Data Verification

1. **Start the app**: `python app.py`
2. **Check logs** for:
   ```
   🚀 Kafka streaming with optimizations
   📊 Consumer started: instrument_registry
   📊 Consumer started: breakout_engine
   ```
3. **Monitor Kafka UI**: http://localhost:8080 to see message flow

### Performance Monitoring

```bash
# Check consumer lag
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --describe --all-groups

# Monitor topics
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

## 🛠 Troubleshooting

### Common Issues

#### 1. "Failed to initialize Kafka Producer"
- **Cause**: Kafka not running or wrong connection parameters
- **Solution**:
  ```bash
  docker-compose -f docker-compose.kafka.yml ps
  python setup_kafka_topics.py
  ```

#### 2. "Kafka consumers failed to start"
- **Cause**: Topics don't exist or consumer group issues
- **Solution**:
  ```bash
  python setup_kafka_topics.py
  # Restart the app
  ```

#### 3. No market data in Kafka
- **Cause**: WebSocket not connected or Kafka streaming disabled
- **Check**: Look for "Kafka streaming" in logs
- **Solution**: Verify broker credentials and WebSocket connection

#### 4. High consumer lag
- **Cause**: Processing bottleneck or insufficient partitions
- **Solution**: Scale consumers or increase partitions

### Debug Commands

```bash
# View Kafka logs
docker-compose -f docker-compose.kafka.yml logs kafka

# List consumer groups
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list

# Read from topic (testing)
docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic trading.market_data.raw --from-beginning
```

## 📊 Production Monitoring

### Key Metrics to Monitor

1. **Producer Metrics**
   - Message send rate
   - Error rate
   - Latency

2. **Consumer Metrics**
   - Lag per partition
   - Processing rate
   - Error count

3. **System Health**
   - CPU/Memory usage
   - Network I/O
   - Disk space

### Alerting Setup

Monitor these conditions:
- Consumer lag > 1000 messages
- Error rate > 1%
- Processing latency > 100ms
- Any consumer down for > 30 seconds

## 🎯 Performance Tuning

### Producer Tuning
```bash
# Ultra-low latency (current settings)
KAFKA_PRODUCER_LINGER_MS=0
KAFKA_PRODUCER_BATCH_SIZE=1

# Higher throughput (if latency less critical)
KAFKA_PRODUCER_LINGER_MS=5
KAFKA_PRODUCER_BATCH_SIZE=100
```

### Consumer Tuning
```bash
# Low latency
KAFKA_CONSUMER_FETCH_MAX_WAIT_MS=1
KAFKA_CONSUMER_MAX_POLL_RECORDS=100

# High throughput
KAFKA_CONSUMER_FETCH_MAX_WAIT_MS=100
KAFKA_CONSUMER_MAX_POLL_RECORDS=1000
```

## 🚨 Emergency Procedures

### Complete Reset
```bash
# Stop everything
docker-compose -f docker-compose.kafka.yml down

# Remove all data
docker-compose -f docker-compose.kafka.yml down -v

# Start fresh
docker-compose -f docker-compose.kafka.yml up -d
python setup_kafka_topics.py
python app.py
```

### Fallback Mode (Without Kafka)
If Kafka is completely unavailable, the system will automatically fall back to the legacy WebSocket distribution system. Look for:
```
⚠️ Kafka system initialization failed - continuing without Kafka
```

---

## 🎉 Quick Start Summary

```bash
# 1. Start Kafka
docker-compose -f docker-compose.kafka.yml up -d

# 2. Setup topics
python setup_kafka_topics.py

# 3. Start app
python app.py

# 4. Monitor (optional)
# Visit http://localhost:8080 for Kafka UI
```

Your Kafka system should now be running with proper market data distribution! 🚀