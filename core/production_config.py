"""
Production Configuration Management
Handles environment-specific settings and configuration validation
"""
import os
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass
import json
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: str
    pool_size: int = 20
    max_overflow: int = 30
    pool_timeout: int = 30
    pool_recycle: int = 3600
    
    def validate(self) -> List[str]:
        """Validate database configuration"""
        errors = []
        
        if not self.url:
            errors.append("DATABASE_URL is required")
            return errors
            
        try:
            parsed = urlparse(self.url)
            if parsed.scheme not in ['postgresql', 'postgresql+psycopg2', 'sqlite']:
                errors.append(f"Unsupported database scheme: {parsed.scheme}")
        except Exception as e:
            errors.append(f"Invalid database URL: {e}")
            
        return errors

@dataclass
class RedisConfig:
    """Redis configuration"""
    enabled: bool = True
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    connection_pool_size: int = 50
    
    def validate(self) -> List[str]:
        """Validate Redis configuration"""
        errors = []
        
        if self.enabled:
            if not self.host:
                errors.append("REDIS_HOST is required when Redis is enabled")
            if not isinstance(self.port, int) or not (1 <= self.port <= 65535):
                errors.append("REDIS_PORT must be a valid port number")
                
        return errors

@dataclass
class SecurityConfig:
    """Security configuration"""
    jwt_secret_key: str
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    cors_origins: List[str] = None
    allowed_hosts: List[str] = None
    secret_key: str = None
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = []
        if self.allowed_hosts is None:
            self.allowed_hosts = []
    
    def validate(self) -> List[str]:
        """Validate security configuration"""
        errors = []
        
        if not self.jwt_secret_key:
            errors.append("JWT_SECRET_KEY is required")
        elif len(self.jwt_secret_key) < 32:
            errors.append("JWT_SECRET_KEY must be at least 32 characters long")
            
        if not self.secret_key:
            errors.append("SECRET_KEY is required")
            
        return errors

@dataclass
class BrokerConfig:
    """Broker API configuration"""
    upstox_api_key: Optional[str] = None
    upstox_api_secret: Optional[str] = None
    upstox_mobile: Optional[str] = None
    upstox_pin: Optional[str] = None
    upstox_totp_key: Optional[str] = None
    
    angel_one_api_key: Optional[str] = None
    angel_one_client_id: Optional[str] = None
    angel_one_password: Optional[str] = None
    angel_one_totp_key: Optional[str] = None
    
    dhan_client_id: Optional[str] = None
    dhan_access_token: Optional[str] = None
    
    zerodha_api_key: Optional[str] = None
    zerodha_api_secret: Optional[str] = None
    zerodha_user_id: Optional[str] = None
    zerodha_password: Optional[str] = None
    zerodha_pin: Optional[str] = None
    
    fyers_app_id: Optional[str] = None
    fyers_secret_key: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate broker configuration"""
        errors = []
        
        # Check that at least one broker is configured
        brokers_configured = 0
        
        if self.upstox_api_key and self.upstox_api_secret:
            brokers_configured += 1
            if not self.upstox_mobile or not self.upstox_pin:
                errors.append("UPSTOX_MOBILE and UPSTOX_PIN required for automation")
                
        if self.angel_one_api_key and self.angel_one_client_id:
            brokers_configured += 1
            
        if self.dhan_client_id and self.dhan_access_token:
            brokers_configured += 1
            
        if self.zerodha_api_key and self.zerodha_api_secret:
            brokers_configured += 1
            
        if self.fyers_app_id and self.fyers_secret_key:
            brokers_configured += 1
            
        if brokers_configured == 0:
            errors.append("At least one broker must be configured")
            
        return errors

@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration"""
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    sentry_dsn: Optional[str] = None
    datadog_api_key: Optional[str] = None
    newrelic_license_key: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate monitoring configuration"""
        errors = []
        
        if self.prometheus_enabled:
            if not isinstance(self.prometheus_port, int) or not (1024 <= self.prometheus_port <= 65535):
                errors.append("PROMETHEUS_PORT must be a valid port number (1024-65535)")
                
        return errors

@dataclass
class TradingConfig:
    """Trading-specific configuration"""
    max_position_size: int = 100000
    max_daily_loss: int = 50000
    max_order_value: int = 1000000
    stop_loss_percentage: float = 5.0
    take_profit_percentage: float = 10.0
    market_data_refresh_interval: int = 1000
    
    def validate(self) -> List[str]:
        """Validate trading configuration"""
        errors = []
        
        if self.max_position_size <= 0:
            errors.append("MAX_POSITION_SIZE must be positive")
            
        if self.max_daily_loss <= 0:
            errors.append("MAX_DAILY_LOSS must be positive")
            
        if self.stop_loss_percentage <= 0 or self.stop_loss_percentage > 100:
            errors.append("STOP_LOSS_PERCENTAGE must be between 0 and 100")
            
        return errors

class ProductionConfig:
    """Main production configuration class"""
    
    def __init__(self):
        self.environment = os.getenv('ENVIRONMENT', 'production')
        self.app_name = os.getenv('APP_NAME', 'TradingBot')
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # Load configuration sections
        self.database = self._load_database_config()
        self.redis = self._load_redis_config()
        self.security = self._load_security_config()
        self.brokers = self._load_broker_config()
        self.monitoring = self._load_monitoring_config()
        self.trading = self._load_trading_config()
        
        # Performance settings
        self.max_memory_mb = int(os.getenv('MAX_MEMORY_MB', '450'))
        self.worker_timeout = int(os.getenv('WORKER_TIMEOUT', '120'))
        self.max_requests = int(os.getenv('MAX_REQUESTS', '1000'))
        
        # Feature flags
        self.feature_flags = self._load_feature_flags()
        
        # Validate configuration
        self.validation_errors = self._validate_all()
        
    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration"""
        return DatabaseConfig(
            url=os.getenv('DATABASE_URL'),
            pool_size=int(os.getenv('DATABASE_POOL_SIZE', '20')),
            max_overflow=int(os.getenv('DATABASE_MAX_OVERFLOW', '30')),
            pool_timeout=int(os.getenv('DATABASE_POOL_TIMEOUT', '30')),
            pool_recycle=int(os.getenv('DATABASE_POOL_RECYCLE', '3600'))
        )
        
    def _load_redis_config(self) -> RedisConfig:
        """Load Redis configuration"""
        return RedisConfig(
            enabled=os.getenv('REDIS_ENABLED', 'true').lower() == 'true',
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            password=os.getenv('REDIS_PASSWORD'),
            ssl=os.getenv('REDIS_SSL', 'false').lower() == 'true',
            connection_pool_size=int(os.getenv('REDIS_CONNECTION_POOL_SIZE', '50'))
        )
        
    def _load_security_config(self) -> SecurityConfig:
        """Load security configuration"""
        cors_origins = os.getenv('CORS_ORIGINS', '').split(',') if os.getenv('CORS_ORIGINS') else []
        allowed_hosts = os.getenv('ALLOWED_HOSTS', '').split(',') if os.getenv('ALLOWED_HOSTS') else []
        
        return SecurityConfig(
            jwt_secret_key=os.getenv('JWT_SECRET_KEY'),
            jwt_access_token_expire_minutes=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '30')),
            jwt_refresh_token_expire_days=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRE_DAYS', '7')),
            cors_origins=[origin.strip() for origin in cors_origins if origin.strip()],
            allowed_hosts=[host.strip() for host in allowed_hosts if host.strip()],
            secret_key=os.getenv('SECRET_KEY')
        )
        
    def _load_broker_config(self) -> BrokerConfig:
        """Load broker configuration"""
        return BrokerConfig(
            upstox_api_key=os.getenv('UPSTOX_API_KEY'),
            upstox_api_secret=os.getenv('UPSTOX_API_SECRET'),
            upstox_mobile=os.getenv('UPSTOX_MOBILE'),
            upstox_pin=os.getenv('UPSTOX_PIN'),
            upstox_totp_key=os.getenv('UPSTOX_TOTP_KEY'),
            
            angel_one_api_key=os.getenv('ANGEL_ONE_API_KEY'),
            angel_one_client_id=os.getenv('ANGEL_ONE_CLIENT_ID'),
            angel_one_password=os.getenv('ANGEL_ONE_PASSWORD'),
            angel_one_totp_key=os.getenv('ANGEL_ONE_TOTP_KEY'),
            
            dhan_client_id=os.getenv('DHAN_CLIENT_ID'),
            dhan_access_token=os.getenv('DHAN_ACCESS_TOKEN'),
            
            zerodha_api_key=os.getenv('ZERODHA_API_KEY'),
            zerodha_api_secret=os.getenv('ZERODHA_API_SECRET'),
            zerodha_user_id=os.getenv('ZERODHA_USER_ID'),
            zerodha_password=os.getenv('ZERODHA_PASSWORD'),
            zerodha_pin=os.getenv('ZERODHA_PIN'),
            
            fyers_app_id=os.getenv('FYERS_APP_ID'),
            fyers_secret_key=os.getenv('FYERS_SECRET_KEY')
        )
        
    def _load_monitoring_config(self) -> MonitoringConfig:
        """Load monitoring configuration"""
        return MonitoringConfig(
            prometheus_enabled=os.getenv('PROMETHEUS_ENABLED', 'true').lower() == 'true',
            prometheus_port=int(os.getenv('PROMETHEUS_PORT', '9090')),
            sentry_dsn=os.getenv('SENTRY_DSN'),
            datadog_api_key=os.getenv('DATADOG_API_KEY'),
            newrelic_license_key=os.getenv('NEWRELIC_LICENSE_KEY')
        )
        
    def _load_trading_config(self) -> TradingConfig:
        """Load trading configuration"""
        return TradingConfig(
            max_position_size=int(os.getenv('MAX_POSITION_SIZE', '100000')),
            max_daily_loss=int(os.getenv('MAX_DAILY_LOSS', '50000')),
            max_order_value=int(os.getenv('MAX_ORDER_VALUE', '1000000')),
            stop_loss_percentage=float(os.getenv('STOP_LOSS_PERCENTAGE', '5.0')),
            take_profit_percentage=float(os.getenv('TAKE_PROFIT_PERCENTAGE', '10.0')),
            market_data_refresh_interval=int(os.getenv('MARKET_DATA_REFRESH_INTERVAL', '1000'))
        )
        
    def _load_feature_flags(self) -> Dict[str, bool]:
        """Load feature flags"""
        return {
            'paper_trading': os.getenv('ENABLE_PAPER_TRADING', 'true').lower() == 'true',
            'ai_trading': os.getenv('ENABLE_AI_TRADING', 'true').lower() == 'true',
            'backtesting': os.getenv('ENABLE_BACKTESTING', 'true').lower() == 'true',
            'options_trading': os.getenv('ENABLE_OPTIONS_TRADING', 'true').lower() == 'true',
            'margin_trading': os.getenv('ENABLE_MARGIN_TRADING', 'false').lower() == 'true',
            'crypto_trading': os.getenv('ENABLE_CRYPTO_TRADING', 'false').lower() == 'true'
        }
        
    def _validate_all(self) -> List[str]:
        """Validate all configuration sections"""
        errors = []
        
        errors.extend(self.database.validate())
        errors.extend(self.redis.validate())
        errors.extend(self.security.validate())
        errors.extend(self.brokers.validate())
        errors.extend(self.monitoring.validate())
        errors.extend(self.trading.validate())
        
        return errors
        
    def is_valid(self) -> bool:
        """Check if configuration is valid"""
        return len(self.validation_errors) == 0
        
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get validation summary"""
        return {
            'valid': self.is_valid(),
            'errors': self.validation_errors,
            'error_count': len(self.validation_errors),
            'environment': self.environment,
            'app_name': self.app_name
        }
        
    def save_validation_report(self, filepath: str = 'config_validation.json'):
        """Save configuration validation report"""
        report = {
            'timestamp': str(os.times()),
            'environment': self.environment,
            'validation': self.get_validation_summary(),
            'feature_flags': self.feature_flags,
            'performance_settings': {
                'max_memory_mb': self.max_memory_mb,
                'worker_timeout': self.worker_timeout,
                'max_requests': self.max_requests
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Configuration validation report saved to {filepath}")

# Global configuration instance
_config = None

def get_config() -> ProductionConfig:
    """Get or create the global configuration instance"""
    global _config
    if _config is None:
        _config = ProductionConfig()
        
        # Log configuration status
        if not _config.is_valid():
            logger.error("Configuration validation failed:")
            for error in _config.validation_errors:
                logger.error(f"  - {error}")
        else:
            logger.info("Configuration validation passed")
            
    return _config

def validate_production_config() -> bool:
    """Validate production configuration and exit if invalid"""
    config = get_config()
    
    if not config.is_valid():
        logger.critical("FATAL: Production configuration is invalid!")
        logger.critical("Errors found:")
        for error in config.validation_errors:
            logger.critical(f"  - {error}")
        logger.critical("Please fix configuration errors before starting the application")
        return False
        
    logger.info("✅ Production configuration is valid")
    return True

# Initialize configuration on import
if __name__ != "__main__":
    get_config()