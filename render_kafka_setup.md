# 🌐 Render Production Kafka Setup

## Option 1: Upstash Kafka (Recommended - FREE Tier Available)

### Step 1: Create Upstash Account
1. Go to https://upstash.com
2. Sign up with GitHub/Google
3. Create new Kafka cluster

### Step 2: Get Connection Details
1. In Upstash Console → Your Kafka cluster
2. Copy these values:
   - **Bootstrap Server**: `tops-stingray-12345-us1-kafka.upstash.io:9092`
   - **Username**: `dG9wcy1zdGluZ3JheS0xMjM0NSQ...`
   - **Password**: `your-password`

### Step 3: Configure Render Environment Variables

In your Render service settings, add:

```bash
# Kafka Configuration
HFT_KAFKA_BOOTSTRAP_SERVERS=tops-stingray-12345-us1-kafka.upstash.io:9092
KAFKA_SASL_USERNAME=dG9wcy1zdGluZ3JheS0xMjM0NSQ...
KAFKA_SASL_PASSWORD=your-password
KAFKA_SASL_MECHANISM=SCRAM-SHA-256
KAFKA_SECURITY_PROTOCOL=SASL_SSL

# Optional
HFT_KAFKA_CLIENT_ID=trading_app_prod
```

### Step 4: Update Producer Config (if using SASL)

The system will automatically use these environment variables.

---

## Option 2: CloudKarafka (Alternative)

1. Sign up at https://cloudkarafka.com
2. Create instance (FREE plan available)
3. Get connection details from console
4. Set environment variables in Render

---

## Option 3: Confluent Cloud (Premium)

1. Sign up at https://confluent.cloud  
2. Create Basic cluster ($1/hour when running)
3. Get bootstrap servers and API keys
4. Set environment variables in Render

---

## Environment Variables for Render

```bash
# Required
HFT_KAFKA_BOOTSTRAP_SERVERS=your-kafka-server:9092

# If using SASL (Upstash/CloudKarafka)
KAFKA_SASL_USERNAME=your-username
KAFKA_SASL_PASSWORD=your-password
KAFKA_SASL_MECHANISM=SCRAM-SHA-256
KAFKA_SECURITY_PROTOCOL=SASL_SSL

# Optional tuning
HFT_KAFKA_CLIENT_ID=trading_app_prod
HFT_KAFKA_PRODUCER_LINGER_MS=5
HFT_KAFKA_CONSUMER_FETCH_MAX_WAIT_MS=100
```

## Render.yaml Configuration

```yaml
services:
  - type: web
    name: trading-app
    env: python
    plan: starter
    region: oregon
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python app.py"
    envVars:
      # Database
      - key: DATABASE_URL
        fromDatabase:
          name: trading-postgres
          property: connectionString
      
      # Redis
      - key: REDIS_URL
        fromService:
          type: redis
          name: trading-redis
          property: connectionString
      
      # Kafka (Upstash example)
      - key: HFT_KAFKA_BOOTSTRAP_SERVERS
        value: tops-stingray-12345-us1-kafka.upstash.io:9092
      - key: KAFKA_SASL_USERNAME
        value: dG9wcy1zdGluZ3JheS0xMjM0NSQ...
      - key: KAFKA_SASL_PASSWORD
        value: your-password
      - key: KAFKA_SASL_MECHANISM
        value: SCRAM-SHA-256
      - key: KAFKA_SECURITY_PROTOCOL
        value: SASL_SSL

databases:
  - name: trading-postgres
    databaseName: trading_db
    user: trading_user
    plan: free

services:
  - type: redis
    name: trading-redis
    plan: free
    maxmemoryPolicy: allkeys-lru
```

## Cost Comparison

| Service | Free Tier | Paid Plans | Best For |
|---------|-----------|------------|----------|
| **Upstash** | 10K messages/day | $0.2 per 100K | Development/Small apps |
| **CloudKarafka** | 25MB storage | $9/month | Small production |
| **Confluent Cloud** | $0 (trial) | $1/hour | Enterprise |

## Recommended: Upstash for Your Use Case

- ✅ **FREE tier** perfect for development
- ✅ **Serverless** - pay only for usage
- ✅ **REST API** - works great with Render
- ✅ **Built-in monitoring**
- ✅ **Auto-scaling**