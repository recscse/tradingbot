"""
Production-Grade Logging Configuration for Trading Application
Includes structured logging, error tracking, audit trails, and compliance logging
"""
import logging
import logging.handlers
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import os
from contextlib import contextmanager
import uuid

class TradingFormatter(logging.Formatter):
    """Custom formatter for trading application with structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Create structured log entry
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread_id': record.thread,
            'process_id': record.process,
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'broker'):
            log_entry['broker'] = record.broker
        if hasattr(record, 'trade_id'):
            log_entry['trade_id'] = record.trade_id
        if hasattr(record, 'order_id'):
            log_entry['order_id'] = record.order_id
        if hasattr(record, 'symbol'):
            log_entry['symbol'] = record.symbol
        if hasattr(record, 'amount'):
            log_entry['amount'] = record.amount
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
            
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
            
        return json.dumps(log_entry, ensure_ascii=False)

class AuditLogger:
    """Dedicated audit logger for compliance and regulatory requirements"""
    
    def __init__(self, log_dir: str = "logs/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create audit logger
        self.logger = logging.getLogger('audit')
        self.logger.setLevel(logging.INFO)
        
        # Remove default handlers to avoid duplication
        self.logger.handlers.clear()
        
        # File handler for audit logs (daily rotation)
        audit_handler = logging.handlers.TimedRotatingFileHandler(
            filename=self.log_dir / 'audit.log',
            when='midnight',
            interval=1,
            backupCount=365,  # Keep 1 year of audit logs
            encoding='utf-8'
        )
        audit_handler.setFormatter(TradingFormatter())
        self.logger.addHandler(audit_handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
        
    def log_trade_execution(self, user_id: str, broker: str, symbol: str, 
                          order_type: str, quantity: int, price: float, 
                          order_id: str, trade_id: Optional[str] = None):
        """Log trade execution for audit trail"""
        self.logger.info(
            f"TRADE_EXECUTED: {order_type} {quantity} {symbol} @ {price}",
            extra={
                'user_id': user_id,
                'broker': broker,
                'symbol': symbol,
                'order_type': order_type,
                'quantity': quantity,
                'price': price,
                'order_id': order_id,
                'trade_id': trade_id,
                'event_type': 'TRADE_EXECUTION'
            }
        )
    
    def log_login(self, user_id: str, ip_address: str, user_agent: str, success: bool):
        """Log user login attempts"""
        event = "LOGIN_SUCCESS" if success else "LOGIN_FAILED"
        self.logger.info(
            f"{event}: User {user_id} from {ip_address}",
            extra={
                'user_id': user_id,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'event_type': event
            }
        )
    
    def log_configuration_change(self, user_id: str, component: str, 
                                old_value: Any, new_value: Any):
        """Log configuration changes"""
        self.logger.info(
            f"CONFIG_CHANGE: {component} changed by {user_id}",
            extra={
                'user_id': user_id,
                'component': component,
                'old_value': str(old_value),
                'new_value': str(new_value),
                'event_type': 'CONFIG_CHANGE'
            }
        )
    
    def log_api_access(self, user_id: str, endpoint: str, method: str, 
                      status_code: int, request_id: str):
        """Log API access for security monitoring"""
        self.logger.info(
            f"API_ACCESS: {method} {endpoint} - {status_code}",
            extra={
                'user_id': user_id,
                'endpoint': endpoint,
                'method': method,
                'status_code': status_code,
                'request_id': request_id,
                'event_type': 'API_ACCESS'
            }
        )

class TradingLogger:
    """Main production logging setup for trading application"""
    
    def __init__(self, app_name: str = "TradingBot", log_level: str = "INFO"):
        self.app_name = app_name
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different log types
        (self.log_dir / "application").mkdir(exist_ok=True)
        (self.log_dir / "trading").mkdir(exist_ok=True)
        (self.log_dir / "errors").mkdir(exist_ok=True)
        (self.log_dir / "performance").mkdir(exist_ok=True)
        
        # Set up loggers
        self.setup_application_logger(log_level)
        self.setup_trading_logger()
        self.setup_error_logger()
        self.setup_performance_logger()
        
        # Initialize audit logger
        self.audit = AuditLogger()
        
    def setup_application_logger(self, log_level: str):
        """Set up main application logger"""
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, log_level.upper()))
        
        # Remove default handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            
        # Console handler for development
        if os.getenv('ENVIRONMENT') != 'production':
            console_handler = logging.StreamHandler(sys.stdout)
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        # File handler with rotation
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=self.log_dir / "application" / "app.log",
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        file_handler.setFormatter(TradingFormatter())
        logger.addHandler(file_handler)
        
    def setup_trading_logger(self):
        """Set up dedicated trading operations logger"""
        trading_logger = logging.getLogger('trading')
        trading_logger.setLevel(logging.INFO)
        
        # Trading operations log
        trading_handler = logging.handlers.TimedRotatingFileHandler(
            filename=self.log_dir / "trading" / "trading.log",
            when='midnight',
            interval=1,
            backupCount=90,  # Keep 3 months of trading logs
            encoding='utf-8'
        )
        trading_handler.setFormatter(TradingFormatter())
        trading_logger.addHandler(trading_handler)
        trading_logger.propagate = False
        
    def setup_error_logger(self):
        """Set up dedicated error logger with immediate notification"""
        error_logger = logging.getLogger('errors')
        error_logger.setLevel(logging.ERROR)
        
        # Error log file
        error_handler = logging.handlers.TimedRotatingFileHandler(
            filename=self.log_dir / "errors" / "errors.log",
            when='midnight',
            interval=1,
            backupCount=365,  # Keep 1 year of error logs
            encoding='utf-8'
        )
        error_handler.setFormatter(TradingFormatter())
        error_logger.addHandler(error_handler)
        
        # Email handler for critical errors (if configured)
        if os.getenv('SMTP_HOST') and os.getenv('ERROR_EMAIL_TO'):
            smtp_handler = logging.handlers.SMTPHandler(
                mailhost=(os.getenv('SMTP_HOST'), int(os.getenv('SMTP_PORT', '587'))),
                fromaddr=os.getenv('ERROR_EMAIL_FROM'),
                toaddrs=[os.getenv('ERROR_EMAIL_TO')],
                subject=f"[CRITICAL] {self.app_name} Error",
                credentials=(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD')),
                secure=()
            )
            smtp_handler.setLevel(logging.CRITICAL)
            error_logger.addHandler(smtp_handler)
            
        error_logger.propagate = False
        
    def setup_performance_logger(self):
        """Set up performance monitoring logger"""
        perf_logger = logging.getLogger('performance')
        perf_logger.setLevel(logging.INFO)
        
        perf_handler = logging.handlers.TimedRotatingFileHandler(
            filename=self.log_dir / "performance" / "performance.log",
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        perf_handler.setFormatter(TradingFormatter())
        perf_logger.addHandler(perf_handler)
        perf_logger.propagate = False

# Global logger instances
_trading_logger = None
_audit_logger = None

def get_trading_logger() -> TradingLogger:
    """Get or create the global trading logger instance"""
    global _trading_logger
    if _trading_logger is None:
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        _trading_logger = TradingLogger(log_level=log_level)
    return _trading_logger

def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger

@contextmanager
def log_execution_time(operation_name: str, logger_name: str = 'performance'):
    """Context manager to log operation execution time"""
    logger = logging.getLogger(logger_name)
    start_time = datetime.now()
    request_id = str(uuid.uuid4())
    
    try:
        logger.info(
            f"OPERATION_START: {operation_name}",
            extra={'operation': operation_name, 'request_id': request_id}
        )
        yield request_id
        
    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.error(
            f"OPERATION_FAILED: {operation_name} after {execution_time:.3f}s",
            extra={
                'operation': operation_name,
                'request_id': request_id,
                'execution_time': execution_time,
                'error': str(e)
            },
            exc_info=True
        )
        raise
        
    else:
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"OPERATION_COMPLETE: {operation_name} in {execution_time:.3f}s",
            extra={
                'operation': operation_name,
                'request_id': request_id,
                'execution_time': execution_time
            }
        )

# Initialize logging on import
get_trading_logger()