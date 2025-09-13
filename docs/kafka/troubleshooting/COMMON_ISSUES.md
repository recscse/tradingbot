# 🔧 Kafka Troubleshooting Guide

## 🚨 Common Issues & Solutions

### 1. Connection Issues

#### "Connection refused to localhost:9092"
**Symptoms:**
- Application fails to start
- "Failed to initialize Kafka Producer" error
- No Kafka services visible in docker ps

**Solutions:**
```bash
# Check if Kafka is running
netstat -an | findstr :9092

# If using Docker
docker-compose -f docker-compose.kafka.yml ps
docker-compose -f docker-compose.kafka.yml up -d

# If using local Kafka
# Make sure you started both Zookeeper and Kafka
bin\windows\zookeeper-server-start.bat config\zookeeper.properties
bin\windows\kafka-server-start.bat config\server.properties

# If using KRaft mode
start_kafka_kraft.bat
```

#### "Bootstrap server not configured"
**Symptoms:**
- "No bootstrap servers configured" error
- Kafka system fails initialization

**Solutions:**
```bash
# Check environment variables
echo %KAFKA_BOOTSTRAP_SERVERS%

# Set in .env file
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# For managed Kafka
KAFKA_BOOTSTRAP_SERVERS=your-server.upstash.io:9092
```

### 2. Authentication Issues

#### "SASL authentication failed"
**Symptoms:**
- "Authentication failed" in logs
- Connection timeout errors with managed Kafka

**Solutions:**
```bash
# Verify credentials in .env
KAFKA_SASL_USERNAME=your-username
KAFKA_SASL_PASSWORD=your-password
KAFKA_SASL_MECHANISM=SCRAM-SHA-256
KAFKA_SECURITY_PROTOCOL=SASL_SSL

# Check managed Kafka dashboard for correct credentials
# Ensure no extra spaces or special characters in credentials
```

#### "SSL handshake failed"
**Symptoms:**
- SSL/TLS connection errors
- Timeout during connection establishment

**Solutions:**
```bash
# Verify security protocol
KAFKA_SECURITY_PROTOCOL=SASL_SSL

# Check if your firewall blocks SSL connections
# Test connection manually:
telnet your-kafka-server.com 9092
```

### 3. Topic Issues

#### "Topic does not exist"
**Symptoms:**
- "Topic 'trading.market_data.raw' does not exist" error
- Consumer fails to start

**Solutions:**
```bash
# Create all topics
python setup_kafka_topics.py

# Check existing topics
bin\windows\kafka-topics.bat --bootstrap-server localhost:9092 --list

# For managed Kafka, check via their console
```

#### "Topic already exists"
**Symptoms:**
- "Topic already exists" warning during topic creation
- Application continues to work fine

**Solutions:**
```bash
# This is usually not an issue - topics are idempotent
# If you need to recreate topics:
bin\windows\kafka-topics.bat --bootstrap-server localhost:9092 --delete --topic topic-name
python setup_kafka_topics.py
```

### 4. Consumer Issues

#### "Consumer group rebalancing"
**Symptoms:**
- Frequent rebalancing messages in logs
- Delayed message processing
- Consumer lag increasing

**Solutions:**
```bash
# Check consumer group status
bin\windows\kafka-consumer-groups.bat --bootstrap-server localhost:9092 --describe --group your-group-id

# Increase session timeout
KAFKA_CONSUMER_SESSION_TIMEOUT_MS=30000
KAFKA_CONSUMER_HEARTBEAT_INTERVAL_MS=10000

# Reduce max poll records if processing is slow
KAFKA_CONSUMER_MAX_POLL_RECORDS=100
```

#### "Consumer lag too high"
**Symptoms:**
- High lag shown in monitoring
- Old messages being processed
- Real-time updates delayed

**Solutions:**
```bash
# Check consumer lag
bin\windows\kafka-consumer-groups.bat --bootstrap-server localhost:9092 --describe --all-groups

# Solutions:
1. Increase number of consumers (if you have multiple partitions)
2. Optimize message processing speed
3. Increase partition count for better parallelism
4. Check if consumer is stuck or crashed
```

### 5. Producer Issues

#### "Producer timeout"
**Symptoms:**
- "Failed to send message" errors
- Messages not appearing in topics

**Solutions:**
```bash
# Check producer configuration
KAFKA_PRODUCER_REQUEST_TIMEOUT_MS=30000
KAFKA_PRODUCER_LINGER_MS=0
KAFKA_PRODUCER_BATCH_SIZE=16384

# Test producer manually
bin\windows\kafka-console-producer.bat --bootstrap-server localhost:9092 --topic test
```

#### "Message too large"
**Symptoms:**
- "Message size too large" error
- Large market data payloads failing

**Solutions:**
```bash
# Increase message size limits
KAFKA_PRODUCER_MAX_REQUEST_SIZE=10485760
KAFKA_CONSUMER_FETCH_MAX_BYTES=10485760

# Or compress messages
KAFKA_PRODUCER_COMPRESSION_TYPE=gzip
```

### 6. Docker Issues

#### "Docker container won't start"
**Symptoms:**
- Docker compose fails to start Kafka
- Container exits immediately

**Solutions:**
```bash
# Check Docker logs
docker-compose -f docker-compose.kafka.yml logs

# Check Docker resources
docker system df
docker system prune  # If disk space is low

# Restart Docker Desktop
# Check if port 9092 is already in use
netstat -an | findstr :9092
```

#### "Kafka UI not accessible"
**Symptoms:**
- Cannot access http://localhost:8080
- UI shows "No clusters configured"

**Solutions:**
```bash
# Check if Kafka UI container is running
docker-compose -f docker-compose.kafka.yml ps

# Check if Kafka is accessible from UI container
docker exec kafka-ui ping kafka

# Restart the entire stack
docker-compose -f docker-compose.kafka.yml down
docker-compose -f docker-compose.kafka.yml up -d
```

## 🔍 Debugging Commands

### Check System Status
```bash
# Check if Kafka is running
netstat -an | findstr :9092

# List all topics
bin\windows\kafka-topics.bat --bootstrap-server localhost:9092 --list

# Check consumer groups
bin\windows\kafka-consumer-groups.bat --bootstrap-server localhost:9092 --list

# View topic details
bin\windows\kafka-topics.bat --bootstrap-server localhost:9092 --describe --topic trading.market_data.raw
```

### Monitor Message Flow
```bash
# Read messages from topic
bin\windows\kafka-console-consumer.bat --bootstrap-server localhost:9092 --topic trading.market_data.raw --from-beginning

# Send test message
bin\windows\kafka-console-producer.bat --bootstrap-server localhost:9092 --topic test

# Monitor with Python
python monitor_kafka_topics.py
```

### Check Application Integration
```bash
# Test Kafka system
python -c "
from services.simple_kafka_system import get_kafka_system
system = get_kafka_system()
print('System available:', system is not None)
"

# Check topic creation
python setup_kafka_topics.py

# Test full integration
python test_kafka_working.py
```

## 📊 Performance Issues

### High Latency
**Symptoms:**
- Slow message processing
- UI updates delayed
- Trading signals arriving late

**Solutions:**
```bash
# Optimize producer settings for low latency
KAFKA_PRODUCER_LINGER_MS=0
KAFKA_PRODUCER_BATCH_SIZE=1
KAFKA_PRODUCER_ACKS=1

# Optimize consumer settings
KAFKA_CONSUMER_FETCH_MAX_WAIT_MS=1
KAFKA_CONSUMER_FETCH_MIN_BYTES=1

# Use local Kafka for development
# Use SSD storage for Kafka data directory
```

### High Memory Usage
**Symptoms:**
- Kafka broker using excessive memory
- System becomes unresponsive

**Solutions:**
```bash
# Reduce Kafka heap size in Docker
KAFKA_HEAP_OPTS=-Xms256m -Xmx512m

# Reduce retention time
KAFKA_LOG_RETENTION_MS=3600000  # 1 hour

# Increase cleanup frequency
KAFKA_LOG_CLEANUP_INTERVAL_MS=60000  # 1 minute
```

## 🚑 Emergency Procedures

### Complete System Reset
```bash
# Stop everything
docker-compose -f docker-compose.kafka.yml down

# Remove all data (WARNING: This deletes all messages)
docker-compose -f docker-compose.kafka.yml down -v
docker volume prune -f

# Start fresh
docker-compose -f docker-compose.kafka.yml up -d
python setup_kafka_topics.py
python app.py
```

### Fallback Mode
If Kafka is completely unavailable:
```bash
# The application will automatically fall back to direct WebSocket distribution
# Look for this message in logs:
"⚠️ Kafka system initialization failed - continuing without Kafka"

# To force fallback mode:
# Remove KAFKA_BOOTSTRAP_SERVERS from environment
# Or set KAFKA_ENABLED=false in .env
```

### Data Recovery
```bash
# If you need to recover messages:
# 1. Check if retention period hasn't expired
# 2. Use kafka-dump-log to examine segments
# 3. Reset consumer group offset to earlier position

# Reset consumer group offset
bin\windows\kafka-consumer-groups.bat --bootstrap-server localhost:9092 --group your-group --reset-offsets --to-earliest --topic your-topic --execute
```

## 📞 Getting Help

### Log Analysis
When reporting issues, include:
```bash
# Application logs
tail -n 100 app.log

# Docker logs
docker-compose -f docker-compose.kafka.yml logs --tail=100

# System information
docker --version
python --version
echo %KAFKA_BOOTSTRAP_SERVERS%
```

### Useful Information for Support
- Operating System (Windows/Linux/Mac)
- Kafka setup method (Docker/Local/Managed)
- Error messages (complete stack trace)
- Configuration files (.env contents, excluding sensitive data)
- Recent changes made to the system

### Health Check Script
```python
# save as kafka_health_check.py
import asyncio
from services.simple_kafka_system import get_kafka_system

async def health_check():
    try:
        system = get_kafka_system()
        if system:
            print("✅ Kafka system initialized")
            # Add more checks here
            print("✅ All checks passed")
        else:
            print("❌ Kafka system not available")
    except Exception as e:
        print(f"❌ Health check failed: {e}")

if __name__ == "__main__":
    asyncio.run(health_check())
```

Remember: Most Kafka issues are related to configuration or connectivity. Always check the basics first: is Kafka running, are credentials correct, do topics exist?