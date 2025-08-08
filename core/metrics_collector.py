"""
Production Metrics Collection System
Collects and exposes metrics for Prometheus monitoring
"""
import time
import asyncio
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from collections import defaultdict, deque
import threading
from contextlib import contextmanager
import json
import os
from prometheus_client import Counter, Histogram, Gauge, Summary, Info, start_http_server, REGISTRY
import redis
from sqlalchemy import text
from database.database import get_db

logger = logging.getLogger('metrics')

class TradingMetrics:
    """Trading-specific metrics collector"""
    
    def __init__(self):
        # Trading metrics
        self.trades_executed = Counter('trades_executed_total', 'Total trades executed', ['broker', 'symbol', 'order_type'])
        self.order_execution_time = Histogram('order_execution_seconds', 'Order execution time', ['broker'])
        self.order_execution_failures = Counter('order_execution_failures_total', 'Order execution failures', ['broker', 'error_type'])
        
        # Portfolio metrics
        self.portfolio_value = Gauge('portfolio_value_inr', 'Total portfolio value in INR', ['user_id'])
        self.portfolio_unrealized_pnl = Gauge('portfolio_unrealized_pnl', 'Unrealized P&L', ['user_id'])
        self.daily_realized_pnl = Gauge('daily_realized_pnl', 'Daily realized P&L', ['user_id'])
        
        # Position metrics
        self.position_count = Gauge('active_positions_count', 'Number of active positions', ['user_id', 'broker'])
        self.position_value = Gauge('position_value_inr', 'Position value in INR', ['user_id', 'symbol'])
        
        # Risk metrics
        self.margin_utilization = Gauge('margin_utilization_percentage', 'Margin utilization percentage', ['user_id', 'broker'])
        self.risk_exposure = Gauge('risk_exposure_inr', 'Total risk exposure in INR', ['user_id'])
        
        # Market data metrics
        self.market_data_lag = Histogram('market_data_lag_seconds', 'Market data latency', ['source'])
        self.price_updates = Counter('price_updates_total', 'Price updates received', ['symbol', 'source'])
        
    def record_trade_execution(self, broker: str, symbol: str, order_type: str, execution_time: float):
        """Record trade execution"""
        self.trades_executed.labels(broker=broker, symbol=symbol, order_type=order_type).inc()
        self.order_execution_time.labels(broker=broker).observe(execution_time)
        
    def record_order_failure(self, broker: str, error_type: str):
        """Record order execution failure"""
        self.order_execution_failures.labels(broker=broker, error_type=error_type).inc()
        
    def update_portfolio_metrics(self, user_id: str, value: float, unrealized_pnl: float, daily_pnl: float):
        """Update portfolio metrics"""
        self.portfolio_value.labels(user_id=user_id).set(value)
        self.portfolio_unrealized_pnl.labels(user_id=user_id).set(unrealized_pnl)
        self.daily_realized_pnl.labels(user_id=user_id).set(daily_pnl)
        
    def update_position_metrics(self, user_id: str, broker: str, symbol: str, position_count: int, position_value: float):
        """Update position metrics"""
        self.position_count.labels(user_id=user_id, broker=broker).set(position_count)
        self.position_value.labels(user_id=user_id, symbol=symbol).set(position_value)

class SystemMetrics:
    """System-level metrics collector"""
    
    def __init__(self):
        # System metrics
        self.cpu_usage = Gauge('cpu_usage_percentage', 'CPU usage percentage')
        self.memory_usage = Gauge('memory_usage_bytes', 'Memory usage in bytes')
        self.memory_usage_percentage = Gauge('memory_usage_percentage', 'Memory usage percentage')
        self.disk_usage = Gauge('disk_usage_bytes', 'Disk usage in bytes', ['path'])
        
        # Application metrics
        self.active_connections = Gauge('active_connections_count', 'Active WebSocket connections')
        self.http_requests = Counter('http_requests_total', 'HTTP requests', ['method', 'endpoint', 'status'])
        self.http_request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
        
        # Database metrics
        self.db_connections = Gauge('database_connections_active', 'Active database connections')
        self.db_query_duration = Histogram('database_query_duration_seconds', 'Database query duration', ['query_type'])
        self.db_query_errors = Counter('database_query_errors_total', 'Database query errors', ['error_type'])
        
        # Redis metrics
        self.redis_connections = Gauge('redis_connections_active', 'Active Redis connections')
        self.redis_operations = Counter('redis_operations_total', 'Redis operations', ['operation'])
        self.cache_hits = Counter('cache_hits_total', 'Cache hits', ['cache_type'])
        self.cache_misses = Counter('cache_misses_total', 'Cache misses', ['cache_type'])
        
        # WebSocket metrics
        self.websocket_connections = Gauge('websocket_connections_active', 'Active WebSocket connections', ['type'])
        self.websocket_messages = Counter('websocket_messages_total', 'WebSocket messages', ['direction', 'type'])
        self.websocket_reconnections = Counter('websocket_reconnections_total', 'WebSocket reconnections', ['reason'])
        
    def update_system_metrics(self):
        """Update system-level metrics"""
        # CPU usage
        cpu_percent = psutil.cpu_percent()
        self.cpu_usage.set(cpu_percent)
        
        # Memory usage
        memory = psutil.virtual_memory()
        self.memory_usage.set(memory.used)
        self.memory_usage_percentage.set(memory.percent)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        self.disk_usage.labels(path='/').set(disk.used)
        
    def record_http_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request metrics"""
        self.http_requests.labels(method=method, endpoint=endpoint, status=str(status)).inc()
        self.http_request_duration.labels(method=method, endpoint=endpoint).observe(duration)

class BrokerMetrics:
    """Broker-specific metrics"""
    
    def __init__(self):
        # Connection metrics
        self.broker_connection_status = Gauge('broker_connection_status', 'Broker connection status (1=connected)', ['broker'])
        self.broker_token_expiry = Gauge('broker_token_expiry_timestamp', 'Token expiry timestamp', ['broker'])
        
        # API metrics
        self.broker_api_requests = Counter('broker_api_requests_total', 'Broker API requests', ['broker', 'endpoint'])
        self.broker_api_request_duration = Histogram('broker_api_request_duration_seconds', 'Broker API request duration', ['broker'])
        self.broker_api_errors = Counter('broker_api_errors_total', 'Broker API errors', ['broker', 'error_type'])
        
        # Rate limiting
        self.broker_rate_limit_hits = Counter('broker_rate_limit_hits_total', 'Rate limit hits', ['broker'])
        self.broker_requests_remaining = Gauge('broker_requests_remaining', 'Remaining API requests', ['broker'])
        
    def update_connection_status(self, broker: str, connected: bool):
        """Update broker connection status"""
        self.broker_connection_status.labels(broker=broker).set(1 if connected else 0)
        
    def record_api_request(self, broker: str, endpoint: str, duration: float, success: bool, error_type: str = None):
        """Record broker API request"""
        self.broker_api_requests.labels(broker=broker, endpoint=endpoint).inc()
        self.broker_api_request_duration.labels(broker=broker).observe(duration)
        
        if not success and error_type:
            self.broker_api_errors.labels(broker=broker, error_type=error_type).inc()

class MarketAnalyticsMetrics:
    """Market analytics and AI metrics"""
    
    def __init__(self):
        # Market data metrics
        self.stock_volume_ratio = Gauge('stock_volume_ratio', 'Current volume vs average ratio', ['symbol'])
        self.stock_price_change = Gauge('stock_price_change_percentage', 'Stock price change percentage', ['symbol'])
        self.market_sentiment = Gauge('market_sentiment_score', 'Market sentiment score', ['index'])
        
        # AI/ML metrics
        self.model_predictions = Counter('model_predictions_total', 'ML model predictions', ['model_name', 'prediction_type'])
        self.model_accuracy = Gauge('model_accuracy_percentage', 'Model accuracy percentage', ['model_name'])
        self.model_inference_time = Histogram('model_inference_duration_seconds', 'Model inference time', ['model_name'])
        
        # Trading signals
        self.trading_signals = Counter('trading_signals_total', 'Trading signals generated', ['signal_type', 'symbol'])
        self.signal_accuracy = Gauge('signal_accuracy_percentage', 'Signal accuracy percentage', ['signal_type'])
        
    def record_market_data(self, symbol: str, volume_ratio: float, price_change: float):
        """Record market data metrics"""
        self.stock_volume_ratio.labels(symbol=symbol).set(volume_ratio)
        self.stock_price_change.labels(symbol=symbol).set(price_change)

class ComplianceMetrics:
    """Compliance and regulatory metrics"""
    
    def __init__(self):
        self.compliance_events = Counter('compliance_events_total', 'Compliance events', ['event_type', 'risk_level'])
        self.regulatory_reports = Counter('regulatory_reports_total', 'Regulatory reports generated', ['report_type'])
        self.audit_log_entries = Counter('audit_log_entries_total', 'Audit log entries', ['event_type'])
        
    def record_compliance_event(self, event_type: str, risk_level: str):
        """Record compliance event"""
        self.compliance_events.labels(event_type=event_type, risk_level=risk_level).inc()

class MetricsCollector:
    """Main metrics collector orchestrator"""
    
    def __init__(self, port: int = 9090):
        self.port = port
        self.trading_metrics = TradingMetrics()
        self.system_metrics = SystemMetrics()
        self.broker_metrics = BrokerMetrics()
        self.market_metrics = MarketAnalyticsMetrics()
        self.compliance_metrics = ComplianceMetrics()
        
        # Performance tracking
        self.request_times = defaultdict(lambda: deque(maxlen=1000))
        self.error_counts = defaultdict(int)
        
        # Start metrics server
        self.start_metrics_server()
        
        # Start background collection
        self.collection_task = None
        self.running = False
        
    def start_metrics_server(self):
        """Start Prometheus metrics HTTP server"""
        try:
            start_http_server(self.port)
            logger.info(f"Metrics server started on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
            
    def start_collection(self):
        """Start background metrics collection"""
        if not self.running:
            self.running = True
            self.collection_task = asyncio.create_task(self._collection_loop())
            logger.info("Background metrics collection started")
            
    async def stop_collection(self):
        """Stop background metrics collection"""
        self.running = False
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
        logger.info("Background metrics collection stopped")
        
    async def _collection_loop(self):
        """Background metrics collection loop"""
        while self.running:
            try:
                # Update system metrics every 30 seconds
                self.system_metrics.update_system_metrics()
                
                # Update database metrics
                await self._collect_database_metrics()
                
                # Update broker metrics
                await self._collect_broker_metrics()
                
                # Wait before next collection
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(5)  # Short wait before retry
                
    async def _collect_database_metrics(self):
        """Collect database-specific metrics"""
        try:
            async with get_db() as db:
                # Check active connections
                result = await db.execute(text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"))
                active_connections = result.scalar()
                self.system_metrics.db_connections.set(active_connections)
                
        except Exception as e:
            logger.error(f"Error collecting database metrics: {e}")
            
    async def _collect_broker_metrics(self):
        """Collect broker-specific metrics"""
        try:
            # This would integrate with actual broker connection status
            # For now, just update with dummy data to show structure
            brokers = ['upstox', 'angel_one', 'dhan', 'zerodha', 'fyers']
            
            for broker in brokers:
                # In production, check actual connection status
                self.broker_metrics.update_connection_status(broker, True)
                
        except Exception as e:
            logger.error(f"Error collecting broker metrics: {e}")

    @contextmanager
    def time_operation(self, operation_name: str):
        """Context manager to time operations"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.request_times[operation_name].append(duration)
            
    def record_error(self, error_type: str):
        """Record error occurrence"""
        self.error_counts[error_type] += 1
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        summary = {
            'request_times': {},
            'error_counts': dict(self.error_counts),
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'disk_total': psutil.disk_usage('/').total
            }
        }
        
        for operation, times in self.request_times.items():
            if times:
                summary['request_times'][operation] = {
                    'count': len(times),
                    'avg': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times),
                    'recent_avg': sum(list(times)[-10:]) / min(len(times), 10)
                }
                
        return summary
        
    async def export_metrics_snapshot(self, filepath: str = None):
        """Export current metrics snapshot"""
        if filepath is None:
            filepath = f"metrics_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'performance_summary': self.get_performance_summary(),
            'system_metrics': {
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.virtual_memory()._asdict(),
                'disk_usage': psutil.disk_usage('/')._asdict()
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(snapshot, f, indent=2)
            
        logger.info(f"Metrics snapshot exported to {filepath}")

# Global metrics collector instance
_metrics_collector = None

def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        port = int(os.getenv('PROMETHEUS_PORT', '9090'))
        _metrics_collector = MetricsCollector(port=port)
    return _metrics_collector

def init_metrics_collection():
    """Initialize metrics collection"""
    collector = get_metrics_collector()
    collector.start_collection()
    return collector

# Initialize on import if enabled
if os.getenv('PROMETHEUS_ENABLED', 'true').lower() == 'true':
    get_metrics_collector()