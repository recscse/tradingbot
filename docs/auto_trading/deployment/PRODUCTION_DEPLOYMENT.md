# Production Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Auto Trading System in production environments. It covers infrastructure requirements, security configurations, monitoring setup, and operational procedures for maintaining a robust HFT trading platform.

## Infrastructure Requirements

### System Specifications

#### Minimum Requirements

| Component | CPU | Memory | Storage | Network |
|-----------|-----|--------|---------|---------|
| **Trading Engine** | 8 cores (3.0+ GHz) | 16 GB RAM | 200 GB SSD | 1 Gbps |
| **Kafka Cluster** | 4 cores per broker | 8 GB RAM | 500 GB SSD | 10 Gbps |
| **Database Server** | 4 cores | 8 GB RAM | 100 GB SSD | 1 Gbps |
| **Load Balancer** | 2 cores | 4 GB RAM | 50 GB SSD | 10 Gbps |

#### Recommended Production Setup

| Component | CPU | Memory | Storage | Network |
|-----------|-----|--------|---------|---------|
| **Trading Engine** | 16 cores (3.5+ GHz) | 64 GB RAM | 1 TB NVMe SSD | 10 Gbps |
| **Kafka Cluster** | 8 cores per broker | 32 GB RAM | 2 TB NVMe SSD | 10 Gbps |
| **Database Server** | 8 cores | 32 GB RAM | 500 GB NVMe SSD | 10 Gbps |
| **Redis Cache** | 4 cores | 16 GB RAM | 100 GB SSD | 10 Gbps |

### Network Architecture

```
                    ┌─────────────────────┐
                    │   Load Balancer     │
                    │   (HAProxy/Nginx)   │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
        ┌───────────▼──────────┐ ┌───────▼──────────┐
        │  Trading Engine 1    │ │  Trading Engine 2 │
        │  (Primary)           │ │  (Standby)        │
        └───────────┬──────────┘ └───────┬──────────┘
                    │                     │
        ┌───────────┴─────────────────────┴───────────┐
        │              Kafka Cluster                  │
        │  ┌─────────┐ ┌─────────┐ ┌─────────┐       │
        │  │Broker 1 │ │Broker 2 │ │Broker 3 │       │
        │  └─────────┘ └─────────┘ └─────────┘       │
        └─────────────┬───────────────────────────────┘
                      │
        ┌─────────────┴───────────────────────────────┐
        │           Data Layer                        │
        │  ┌──────────────┐    ┌──────────────┐      │
        │  │ PostgreSQL   │    │ Redis Cache  │      │
        │  │ (Primary)    │    │              │      │
        │  └──────────────┘    └──────────────┘      │
        │  ┌──────────────┐                          │
        │  │ PostgreSQL   │                          │
        │  │ (Replica)    │                          │
        │  └──────────────┘                          │
        └─────────────────────────────────────────────┘
```

## Pre-Deployment Checklist

### Environment Preparation

```bash
# 1. System Updates
sudo apt update && sudo apt upgrade -y

# 2. Install Required Packages
sudo apt install -y \
    python3.9 \
    python3.9-venv \
    python3-pip \
    postgresql-14 \
    redis-server \
    nginx \
    supervisor \
    htop \
    iotop \
    netstat-nat

# 3. Create Application User
sudo useradd -r -s /bin/false autotrading
sudo mkdir -p /opt/autotrading
sudo chown autotrading:autotrading /opt/autotrading

# 4. Configure System Limits
echo "autotrading soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "autotrading hard nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "autotrading soft nproc 32768" | sudo tee -a /etc/security/limits.conf
echo "autotrading hard nproc 32768" | sudo tee -a /etc/security/limits.conf
```

### Security Hardening

```bash
# 1. Firewall Configuration
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow specific services
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8000/tcp  # Application (internal)
sudo ufw allow 9092/tcp  # Kafka (internal)
sudo ufw allow 5432/tcp  # PostgreSQL (internal)
sudo ufw allow 6379/tcp  # Redis (internal)

# 2. SSH Hardening
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl reload ssh

# 3. Fail2Ban Installation
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## Application Deployment

### Code Deployment Script

```bash
#!/bin/bash
# deploy.sh - Production deployment script

set -e  # Exit on any error

# Configuration
APP_NAME="autotrading"
APP_USER="autotrading"
APP_DIR="/opt/autotrading"
REPO_URL="https://github.com/your-org/autotrading-system.git"
BRANCH="production"
BACKUP_DIR="/opt/backups"

echo "Starting production deployment..."

# 1. Create backup
echo "Creating backup..."
sudo -u $APP_USER mkdir -p $BACKUP_DIR
sudo -u $APP_USER tar -czf "$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).tar.gz" -C $APP_DIR . || true

# 2. Stop application services
echo "Stopping application services..."
sudo systemctl stop autotrading-app
sudo systemctl stop autotrading-worker
sudo systemctl stop autotrading-kafka-consumer

# 3. Update code
echo "Updating application code..."
cd $APP_DIR
sudo -u $APP_USER git fetch origin
sudo -u $APP_USER git checkout $BRANCH
sudo -u $APP_USER git pull origin $BRANCH

# 4. Install dependencies
echo "Installing dependencies..."
sudo -u $APP_USER python3 -m venv venv
sudo -u $APP_USER ./venv/bin/pip install -r requirements.txt

# 5. Run database migrations
echo "Running database migrations..."
sudo -u $APP_USER ./venv/bin/python -m alembic upgrade head

# 6. Compile static assets (if any)
echo "Compiling assets..."
sudo -u $APP_USER ./compile_assets.sh || true

# 7. Start services
echo "Starting application services..."
sudo systemctl start autotrading-app
sudo systemctl start autotrading-worker
sudo systemctl start autotrading-kafka-consumer

# 8. Health check
echo "Performing health check..."
sleep 10
curl -f http://localhost:8000/health || {
    echo "Health check failed!"
    exit 1
}

echo "Deployment completed successfully!"
```

### Environment Configuration

```bash
# /opt/autotrading/.env
# Production environment variables

# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://autotrading:${DB_PASSWORD}@localhost:5432/autotrading_prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=0

# Redis
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=${REDIS_PASSWORD}

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka1:9092,kafka2:9092,kafka3:9092
KAFKA_SECURITY_PROTOCOL=SSL
KAFKA_SSL_CAFILE=/opt/autotrading/certs/ca-cert
KAFKA_SSL_CERTFILE=/opt/autotrading/certs/client-cert
KAFKA_SSL_KEYFILE=/opt/autotrading/certs/client-key

# Broker APIs
UPSTOX_API_KEY=${UPSTOX_API_KEY}
UPSTOX_API_SECRET=${UPSTOX_API_SECRET}
UPSTOX_MOBILE=${UPSTOX_MOBILE}
UPSTOX_PIN=${UPSTOX_PIN}
UPSTOX_TOTP_KEY=${UPSTOX_TOTP_KEY}

# Security
JWT_SECRET_KEY=${JWT_SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# Monitoring
SENTRY_DSN=${SENTRY_DSN}
PROMETHEUS_PORT=8001

# Performance
WORKERS=8
WORKER_CLASS=uvicorn.workers.UvicornWorker
WORKER_CONNECTIONS=1000
KEEPALIVE=2
MAX_REQUESTS=1000
MAX_REQUESTS_JITTER=50

# Rate Limiting
RATE_LIMIT_PER_MINUTE=1000
RATE_LIMIT_BURST=100
```

## Service Configuration

### Systemd Service Files

#### Main Application Service

```ini
# /etc/systemd/system/autotrading-app.service
[Unit]
Description=Auto Trading System Main Application
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=notify
User=autotrading
Group=autotrading
WorkingDirectory=/opt/autotrading
Environment=PATH=/opt/autotrading/venv/bin
EnvironmentFile=/opt/autotrading/.env
ExecStart=/opt/autotrading/venv/bin/gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 8 \
    --worker-class uvicorn.workers.UvicornWorker \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --timeout 30 \
    --keepalive 2 \
    --preload \
    --access-logfile /var/log/autotrading/access.log \
    --error-logfile /var/log/autotrading/error.log \
    --log-level info \
    app:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/autotrading /var/log/autotrading /tmp

# Resource limits
LimitNOFILE=65536
LimitNPROC=32768
MemoryMax=8G
CPUQuota=800%

[Install]
WantedBy=multi-user.target
```

#### Kafka Consumer Service

```ini
# /etc/systemd/system/autotrading-kafka-consumer.service
[Unit]
Description=Auto Trading Kafka Consumer
After=network.target kafka.service
Requires=kafka.service

[Service]
Type=simple
User=autotrading
Group=autotrading
WorkingDirectory=/opt/autotrading
Environment=PATH=/opt/autotrading/venv/bin
EnvironmentFile=/opt/autotrading/.env
ExecStart=/opt/autotrading/venv/bin/python -m services.hft.kafka_consumer_manager
Restart=always
RestartSec=5
TimeoutStopSec=10

# Resource limits
LimitNOFILE=65536
MemoryMax=4G
CPUQuota=400%

[Install]
WantedBy=multi-user.target
```

#### Background Worker Service

```ini
# /etc/systemd/system/autotrading-worker.service
[Unit]
Description=Auto Trading Background Worker
After=network.target redis.service
Requires=redis.service

[Service]
Type=simple
User=autotrading
Group=autotrading
WorkingDirectory=/opt/autotrading
Environment=PATH=/opt/autotrading/venv/bin
EnvironmentFile=/opt/autotrading/.env
ExecStart=/opt/autotrading/venv/bin/python -m workers.background_worker
Restart=always
RestartSec=5

# Resource limits
LimitNOFILE=65536
MemoryMax=2G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
```

### Nginx Configuration

```nginx
# /etc/nginx/sites-available/autotrading
upstream app_servers {
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8001 max_fails=3 fail_timeout=30s backup;
    
    keepalive 32;
}

# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
limit_req_zone $binary_remote_addr zone=websocket:10m rate=50r/m;

server {
    listen 80;
    server_name autotrading.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name autotrading.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/autotrading.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/autotrading.yourdomain.com/privkey.pem;
    ssl_session_timeout 1d;
    ssl_session_cache shared:MozTLS:10m;
    ssl_session_tickets off;
    
    # Modern SSL configuration
    ssl_protocols TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # Main application
    location / {
        proxy_pass http://app_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Rate limiting for API endpoints
        limit_req zone=api burst=20 nodelay;
    }
    
    # WebSocket endpoints
    location /ws/ {
        proxy_pass http://app_servers;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket specific timeouts
        proxy_connect_timeout 7s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Rate limiting for WebSocket connections
        limit_req zone=websocket burst=10 nodelay;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://app_servers;
        access_log off;
    }
    
    # Static files (if any)
    location /static/ {
        alias /opt/autotrading/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Metrics endpoint (restrict access)
    location /metrics {
        proxy_pass http://app_servers;
        allow 10.0.0.0/8;
        allow 192.168.0.0/16;
        deny all;
    }
}
```

## Database Setup

### PostgreSQL Configuration

```bash
# Install PostgreSQL 14
sudo apt install -y postgresql-14 postgresql-contrib-14

# Configure PostgreSQL
sudo -u postgres createuser --interactive autotrading
sudo -u postgres createdb autotrading_prod -O autotrading

# Set password
sudo -u postgres psql -c "ALTER USER autotrading PASSWORD 'your_secure_password';"
```

#### PostgreSQL Tuning

```sql
-- /etc/postgresql/14/main/postgresql.conf optimizations

# Memory settings
shared_buffers = 4GB                    # 25% of total RAM
effective_cache_size = 12GB             # 75% of total RAM
work_mem = 64MB                         # Per operation
maintenance_work_mem = 512MB

# Connection settings
max_connections = 200
superuser_reserved_connections = 3

# WAL settings
wal_buffers = 64MB
checkpoint_completion_target = 0.9
wal_compression = on

# Query planner
default_statistics_target = 100
random_page_cost = 1.1                  # For SSD storage
effective_io_concurrency = 200          # For SSD storage

# Logging
log_min_duration_statement = 1000       # Log slow queries
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on

# Performance monitoring
track_activities = on
track_counts = on
track_io_timing = on
track_functions = all
```

### Database Backup Strategy

```bash
#!/bin/bash
# /opt/autotrading/scripts/backup_database.sh

BACKUP_DIR="/opt/backups/database"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="autotrading_prod"
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Create database backup
pg_dump -h localhost -U autotrading -d $DB_NAME \
    --no-password --clean --create --if-exists \
    --format=custom --compress=9 \
    > "$BACKUP_DIR/autotrading_${DATE}.backup"

# Create SQL dump for disaster recovery
pg_dump -h localhost -U autotrading -d $DB_NAME \
    --no-password --clean --create --if-exists \
    --format=plain \
    > "$BACKUP_DIR/autotrading_${DATE}.sql"

# Compress SQL dump
gzip "$BACKUP_DIR/autotrading_${DATE}.sql"

# Remove old backups
find $BACKUP_DIR -name "autotrading_*.backup" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "autotrading_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Database backup completed: $BACKUP_DIR/autotrading_${DATE}.backup"
```

## Monitoring and Logging

### Logging Configuration

```python
# logging_config.py
import logging.config

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '{asctime} {levelname} {name} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'detailed',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'json',
            'filename': '/var/log/autotrading/application.log',
            'maxBytes': 100*1024*1024,  # 100MB
            'backupCount': 10,
            'encoding': 'utf-8'
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'json',
            'filename': '/var/log/autotrading/error.log',
            'maxBytes': 50*1024*1024,   # 50MB
            'backupCount': 5,
            'encoding': 'utf-8'
        },
        'trading_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'json',
            'filename': '/var/log/autotrading/trading.log',
            'maxBytes': 200*1024*1024,  # 200MB
            'backupCount': 20,
            'encoding': 'utf-8'
        }
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False
        },
        'autotrading': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False
        },
        'trading': {
            'handlers': ['trading_file', 'console'],
            'level': 'INFO',
            'propagate': False
        },
        'uvicorn': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False
        }
    }
}
```

### Health Check Endpoint

```python
# health.py - Comprehensive health checking
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import asyncio
import time
import psutil

router = APIRouter()

class HealthChecker:
    """Comprehensive system health checker"""
    
    def __init__(self):
        self.checks = {
            'database': self._check_database,
            'redis': self._check_redis,
            'kafka': self._check_kafka,
            'disk_space': self._check_disk_space,
            'memory': self._check_memory,
            'cpu': self._check_cpu,
            'external_apis': self._check_external_apis,
            'websocket': self._check_websocket_health
        }
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {}
        overall_healthy = True
        
        for check_name, check_func in self.checks.items():
            try:
                start_time = time.time()
                result = await check_func()
                end_time = time.time()
                
                results[check_name] = {
                    'status': 'healthy' if result['healthy'] else 'unhealthy',
                    'details': result.get('details', {}),
                    'response_time_ms': round((end_time - start_time) * 1000, 2)
                }
                
                if not result['healthy']:
                    overall_healthy = False
                    
            except Exception as e:
                results[check_name] = {
                    'status': 'error',
                    'error': str(e),
                    'response_time_ms': 0
                }
                overall_healthy = False
        
        return {
            'status': 'healthy' if overall_healthy else 'unhealthy',
            'timestamp': time.time(),
            'checks': results,
            'system_info': {
                'uptime': time.time() - psutil.boot_time(),
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'disk_usage': psutil.disk_usage('/').percent
            }
        }
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            from database.database import get_database
            db = await get_database()
            
            # Test query
            start_time = time.time()
            await db.fetch_one("SELECT 1")
            query_time = (time.time() - start_time) * 1000
            
            # Get connection pool stats
            pool_stats = {
                'pool_size': db._pool.size if hasattr(db, '_pool') else 0,
                'checked_in': db._pool.checked_in_connections if hasattr(db, '_pool') else 0,
                'checked_out': db._pool.checked_out_connections if hasattr(db, '_pool') else 0
            }
            
            return {
                'healthy': query_time < 1000,  # < 1 second
                'details': {
                    'query_time_ms': round(query_time, 2),
                    'pool_stats': pool_stats
                }
            }
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance"""
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0)
            
            start_time = time.time()
            r.ping()
            ping_time = (time.time() - start_time) * 1000
            
            # Get Redis info
            info = r.info()
            
            return {
                'healthy': ping_time < 100,  # < 100ms
                'details': {
                    'ping_time_ms': round(ping_time, 2),
                    'connected_clients': info.get('connected_clients', 0),
                    'memory_usage': info.get('used_memory_human', 'Unknown'),
                    'uptime': info.get('uptime_in_seconds', 0)
                }
            }
        except Exception as e:
            return {'healthy': False, 'error': str(e)}

@router.get('/health')
async def health_check():
    """Comprehensive health check endpoint"""
    checker = HealthChecker()
    health_status = await checker.run_all_checks()
    
    if health_status['status'] == 'unhealthy':
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status

@router.get('/health/quick')
async def quick_health_check():
    """Quick health check for load balancer"""
    return {'status': 'healthy', 'timestamp': time.time()}
```

## Backup and Recovery

### Automated Backup Script

```bash
#!/bin/bash
# /opt/autotrading/scripts/full_backup.sh

set -e

BACKUP_ROOT="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/full_backup_$DATE"
RETENTION_DAYS=7

echo "Starting full system backup..."

# Create backup directory
mkdir -p $BACKUP_DIR

# 1. Database backup
echo "Backing up database..."
pg_dump -h localhost -U autotrading -d autotrading_prod \
    --no-password --clean --create \
    --format=custom --compress=9 \
    > "$BACKUP_DIR/database.backup"

# 2. Application files backup
echo "Backing up application files..."
tar -czf "$BACKUP_DIR/application.tar.gz" \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    -C /opt/autotrading .

# 3. Configuration backup
echo "Backing up configuration..."
cp /opt/autotrading/.env "$BACKUP_DIR/env_file"
tar -czf "$BACKUP_DIR/configs.tar.gz" \
    /etc/nginx/sites-available/autotrading \
    /etc/systemd/system/autotrading-*.service \
    /etc/supervisor/conf.d/autotrading-*.conf

# 4. Log files backup (recent)
echo "Backing up recent logs..."
tar -czf "$BACKUP_DIR/logs.tar.gz" \
    --newer-mtime="7 days ago" \
    /var/log/autotrading/

# 5. Create backup manifest
echo "Creating backup manifest..."
cat > "$BACKUP_DIR/manifest.txt" << EOF
Backup Date: $(date)
Database Size: $(ls -lh $BACKUP_DIR/database.backup | awk '{print $5}')
Application Size: $(ls -lh $BACKUP_DIR/application.tar.gz | awk '{print $5}')
Configs Size: $(ls -lh $BACKUP_DIR/configs.tar.gz | awk '{print $5}')
Logs Size: $(ls -lh $BACKUP_DIR/logs.tar.gz | awk '{print $5}')
Total Size: $(du -sh $BACKUP_DIR | awk '{print $1}')
EOF

# 6. Cleanup old backups
echo "Cleaning up old backups..."
find $BACKUP_ROOT -name "full_backup_*" -type d -mtime +$RETENTION_DAYS -exec rm -rf {} \;

# 7. Upload to cloud storage (optional)
if [ -n "$AWS_S3_BUCKET" ]; then
    echo "Uploading to S3..."
    aws s3 sync $BACKUP_DIR s3://$AWS_S3_BUCKET/backups/$(basename $BACKUP_DIR)/
fi

echo "Full backup completed: $BACKUP_DIR"
```

### Disaster Recovery Procedure

```bash
#!/bin/bash
# /opt/autotrading/scripts/disaster_recovery.sh

set -e

BACKUP_DIR="$1"
if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: $0 <backup_directory>"
    exit 1
fi

echo "Starting disaster recovery from: $BACKUP_DIR"

# 1. Stop all services
echo "Stopping services..."
systemctl stop autotrading-app
systemctl stop autotrading-worker
systemctl stop autotrading-kafka-consumer

# 2. Restore database
echo "Restoring database..."
sudo -u postgres dropdb autotrading_prod --if-exists
sudo -u postgres createdb autotrading_prod -O autotrading
pg_restore -h localhost -U autotrading -d autotrading_prod \
    --no-password --clean --create \
    "$BACKUP_DIR/database.backup"

# 3. Restore application files
echo "Restoring application files..."
cd /opt/autotrading
rm -rf app/ services/ database/ router/ models/ brokers/ core/
tar -xzf "$BACKUP_DIR/application.tar.gz"
chown -R autotrading:autotrading /opt/autotrading

# 4. Restore configuration
echo "Restoring configuration..."
cp "$BACKUP_DIR/env_file" .env
tar -xzf "$BACKUP_DIR/configs.tar.gz" -C /

# 5. Reinstall dependencies
echo "Reinstalling dependencies..."
sudo -u autotrading python3 -m venv venv
sudo -u autotrading ./venv/bin/pip install -r requirements.txt

# 6. Restart services
echo "Starting services..."
systemctl daemon-reload
systemctl start autotrading-app
systemctl start autotrading-worker
systemctl start autotrading-kafka-consumer

# 7. Verify recovery
echo "Verifying recovery..."
sleep 10
curl -f http://localhost:8000/health || {
    echo "Recovery verification failed!"
    exit 1
}

echo "Disaster recovery completed successfully!"
```

## Monitoring Setup

### Prometheus Configuration

```yaml
# /etc/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "/etc/prometheus/rules/*.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - "localhost:9093"

scrape_configs:
  - job_name: 'autotrading-app'
    static_configs:
      - targets: ['localhost:8001']
    scrape_interval: 5s
    metrics_path: /metrics
    
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
    
  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['localhost:9187']
    
  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['localhost:9121']
    
  - job_name: 'kafka-exporter'
    static_configs:
      - targets: ['localhost:9308']
```

### Alert Rules

```yaml
# /etc/prometheus/rules/autotrading.yml
groups:
  - name: autotrading_alerts
    rules:
      - alert: ApplicationDown
        expr: up{job="autotrading-app"} == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "Auto Trading Application is down"
          
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          
      - alert: DatabaseConnectionFailure
        expr: postgres_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection failure"
          
      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage detected"
          
      - alert: TradingLatencyHigh
        expr: trading_operation_duration_seconds{quantile="0.95"} > 1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Trading operation latency is high"
```

## Performance Optimization

### System Tuning

```bash
# /etc/sysctl.d/99-autotrading.conf
# Network optimizations
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_rmem = 4096 65536 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216

# File descriptor limits
fs.file-max = 2097152

# Virtual memory
vm.swappiness = 1
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5

# Apply settings
sudo sysctl --system
```

### Application Performance Tuning

```python
# performance_config.py
import uvloop
import asyncio

# Use uvloop for better async performance
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# Gunicorn configuration
bind = "0.0.0.0:8000"
workers = 8
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2
preload_app = True

# Worker process settings
worker_tmp_dir = "/dev/shm"  # Use shared memory for temp files
tmp_upload_dir = "/dev/shm"

# Logging
accesslog = "/var/log/autotrading/access.log"
errorlog = "/var/log/autotrading/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
```

This comprehensive production deployment guide ensures a robust, secure, and high-performance deployment of the Auto Trading System with proper monitoring, backup, and recovery procedures.