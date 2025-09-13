# 📋 Kafka Setup - Redirected to New Documentation

## 🎯 **New Organized Documentation Location**

This file has been moved to the new organized Kafka documentation structure.

**Please use the new location:**

📁 **Main Index**: [`docs/kafka/README.md`](docs/kafka/README.md)

## 🚀 **Updated Documentation Links**

- **🏃‍♂️ Quick Start**: [`docs/kafka/setup/QUICK_START.md`](docs/kafka/setup/QUICK_START.md) - 5-minute setup
- **📖 Complete Setup**: [`docs/kafka/setup/COMPLETE_SETUP.md`](docs/kafka/setup/COMPLETE_SETUP.md) - Detailed guide (replaces this file)
- **☁️ Production Setup**: [`docs/kafka/setup/MANAGED_SETUP.md`](docs/kafka/setup/MANAGED_SETUP.md) - Cloud deployment
- **🏗️ System Architecture**: [`docs/kafka/architecture/SYSTEM_ARCHITECTURE.md`](docs/kafka/architecture/SYSTEM_ARCHITECTURE.md) - How everything fits together
- **🔧 Troubleshooting**: [`docs/kafka/troubleshooting/COMMON_ISSUES.md`](docs/kafka/troubleshooting/COMMON_ISSUES.md) - Fix common problems

---

**This content has been improved and moved to the new documentation structure above.**

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

### Option 1: Super Easy Docker Setup (Recommended)

#### Step 1: Start Kafka
```bash
# Start Kafka and Zookeeper
docker-compose -f docker-compose.kafka.yml up -d

# Check if services are running
docker-compose -f docker-compose.kafka.yml ps
```

#### Step 2: Create Topics
```bash
# Create all required HFT topics
python setup_kafka_topics.py
```

#### Step 3: Start Your Application
```bash
# Start the trading application
python app.py
```

**Expected Output:**
```
🚀 Initializing HFT Kafka System...
✅ HFT Kafka system initialized successfully
🚀 HFT Kafka consumers started successfully
```

#### Step 4: Monitor (Optional)
- **Kafka UI**: http://localhost:8080 (see topics, messages, consumers)
- **Application logs**: Watch for HFT streaming messages

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
# Create HFT topics
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

## 🌐 Production Deployment (Render/Cloud)

### Environment Variables

Set these in your deployment environment:

```bash
# Kafka Configuration
HFT_KAFKA_BOOTSTRAP_SERVERS=your-kafka-cluster:9092
HFT_KAFKA_CLIENT_ID=hft_trading_prod

# Optional Performance Tuning
HFT_KAFKA_PRODUCER_LINGER_MS=0
HFT_KAFKA_PRODUCER_BATCH_SIZE=1
HFT_KAFKA_CONSUMER_FETCH_MAX_WAIT_MS=1
```

### Managed Kafka Services

#### Option 1: Confluent Cloud (Recommended)
1. Create account at https://confluent.cloud
2. Create Kafka cluster
3. Get bootstrap servers URL
4. Set environment variable: `HFT_KAFKA_BOOTSTRAP_SERVERS=pkc-xxxxx.region.provider.confluent.cloud:9092`

#### Option 2: AWS MSK (Amazon Managed Streaming for Apache Kafka)
1. Create MSK cluster in AWS Console
2. Get bootstrap servers endpoint
3. Configure security groups for access

#### Option 3: Upstash Kafka (Serverless)
1. Create account at https://upstash.com
2. Create Kafka database
3. Use REST endpoint as bootstrap server

### Render.com Deployment

#### render.yaml (Add this service)
```yaml
services:
  - type: web
    name: trading-app
    env: python
    plan: starter
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python app.py"
    envVars:
      - key: HFT_KAFKA_BOOTSTRAP_SERVERS
        value: your-kafka-endpoint:9092
      - key: DATABASE_URL
        fromDatabase:
          name: trading-db
          property: connectionString
```

## 🔧 System Architecture

### Data Flow

```
Upstox WebSocket → CentralizedWSManager → HFT Producer → Kafka Topics
                                                            ↓
Multiple Services ← HFT Consumers ← Kafka Topics ← Memory Bridge
```

### Kafka Topics

| Topic | Purpose | Partitions | Consumers |
|-------|---------|------------|-----------|
| `hft.raw.market_data` | Raw data from Upstox | 3 | Memory Bridge |
| `hft.shared_memory.feed` | Processed market data | 3 | All services |
| `hft.strategy.breakout` | Breakout signals | 2 | Trading engine |
| `hft.strategy.gap_trading` | Gap analysis | 2 | Gap detector |
| `hft.analytics.market_data` | Market analytics | 2 | Dashboard |
| `hft.execution.signals` | Trading signals | 2 | Order management |
| `hft.ui.price_updates` | UI updates | 1 | Frontend |

### Services & Consumers

| Service | Consumer | Purpose |
|---------|----------|---------|
| **Instrument Registry** | `HFTInstrumentRegistryConsumer` | Price cache updates |
| **Breakout Engine** | `HFTBreakoutEngineConsumer` | Pattern detection |
| **Market Analytics** | `HFTMarketAnalyticsConsumer` | Real-time analysis |
| **Premarket Builder** | `HFTPremarketConsumer` | Candle building |

## 🚀 Testing & Verification

### Quick Health Check
```bash
# Check if Kafka is working
python -c "
import asyncio
from services.hft.integration import get_hft_system

async def test():
    system = get_hft_system()
    status = system.get_system_status()
    print(f'HFT System: {status}')

asyncio.run(test())
"
```

### Live Data Verification

1. **Start the app**: `python app.py`
2. **Check logs** for:
   ```
   🚀 HFT Kafka streaming with zero-copy optimizations
   📊 HFT Consumer started: instrument_registry  
   📊 HFT Consumer started: breakout_engine
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

#### 1. "Failed to initialize HFT Kafka Producer"
- **Cause**: Kafka not running or wrong connection parameters  
- **Solution**: 
  ```bash
  docker-compose -f docker-compose.kafka.yml ps
  python setup_kafka_topics.py
  ```

#### 2. "HFT Kafka consumers failed to start"  
- **Cause**: Topics don't exist or consumer group issues
- **Solution**:
  ```bash
  python setup_kafka_topics.py
  # Restart the app
  ```

#### 3. No market data in Kafka
- **Cause**: WebSocket not connected or HFT streaming disabled
- **Check**: Look for "HFT Kafka streaming" in logs
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
docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic hft.raw.market_data --from-beginning
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
HFT_KAFKA_PRODUCER_LINGER_MS=0
HFT_KAFKA_PRODUCER_BATCH_SIZE=1

# Higher throughput (if latency less critical)  
HFT_KAFKA_PRODUCER_LINGER_MS=5
HFT_KAFKA_PRODUCER_BATCH_SIZE=100
```

### Consumer Tuning
```bash
# Low latency
HFT_KAFKA_CONSUMER_FETCH_MAX_WAIT_MS=1
HFT_KAFKA_CONSUMER_MAX_POLL_RECORDS=100

# High throughput
HFT_KAFKA_CONSUMER_FETCH_MAX_WAIT_MS=100  
HFT_KAFKA_CONSUMER_MAX_POLL_RECORDS=1000
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
⚠️ HFT Kafka system initialization failed - continuing without HFT
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

Your HFT Kafka system should now be running with proper live feed distribution! 🚀