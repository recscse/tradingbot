"""
Advanced Security Manager for Production Trading Application
Implements comprehensive security measures for fintech applications
"""
import hashlib
import secrets
import hmac
import base64
import logging
import asyncio
import ipaddress
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import jwt
import bcrypt
import pyotp
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import redis
import json
import os
from functools import wraps
import time
import geoip2.database
import geoip2.errors
from collections import defaultdict
from threading import Lock
import re

logger = logging.getLogger('security')

class SecurityEventType(Enum):
    """Security event types"""
    LOGIN_ATTEMPT = "LOGIN_ATTEMPT"
    LOGIN_SUCCESS = "LOGIN_SUCCESS" 
    LOGIN_FAILURE = "LOGIN_FAILURE"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    TOKEN_MANIPULATION = "TOKEN_MANIPULATION"
    BRUTE_FORCE_ATTEMPT = "BRUTE_FORCE_ATTEMPT"
    GEOLOCATION_ANOMALY = "GEOLOCATION_ANOMALY"
    DEVICE_ANOMALY = "DEVICE_ANOMALY"
    API_ABUSE = "API_ABUSE"
    INJECTION_ATTEMPT = "INJECTION_ATTEMPT"

class ThreatLevel(Enum):
    """Threat severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class SecurityEvent:
    """Security event record"""
    id: str
    event_type: SecurityEventType
    threat_level: ThreatLevel
    timestamp: datetime
    user_id: Optional[str]
    ip_address: str
    user_agent: str
    details: Dict[str, Any]
    action_taken: str
    blocked: bool = False

class EncryptionManager:
    """Handles encryption/decryption of sensitive data"""
    
    def __init__(self):
        self.master_key = self._get_or_generate_master_key()
        self.fernet = Fernet(self.master_key)
        
    def _get_or_generate_master_key(self) -> bytes:
        """Get existing master key or generate new one"""
        key_env = os.getenv('ENCRYPTION_MASTER_KEY')
        if key_env:
            return key_env.encode()
            
        # Generate new key if not provided
        key = Fernet.generate_key()
        logger.warning("Generated new encryption key. Set ENCRYPTION_MASTER_KEY environment variable!")
        return key
        
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        if not data:
            return data
        return self.fernet.encrypt(data.encode()).decode()
        
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not encrypted_data:
            return encrypted_data
        return self.fernet.decrypt(encrypted_data.encode()).decode()
        
    def encrypt_dict(self, data: Dict[str, Any], sensitive_keys: List[str]) -> Dict[str, Any]:
        """Encrypt sensitive keys in dictionary"""
        result = data.copy()
        for key in sensitive_keys:
            if key in result and result[key]:
                result[key] = self.encrypt(str(result[key]))
        return result
        
    def decrypt_dict(self, data: Dict[str, Any], sensitive_keys: List[str]) -> Dict[str, Any]:
        """Decrypt sensitive keys in dictionary"""
        result = data.copy()
        for key in sensitive_keys:
            if key in result and result[key]:
                result[key] = self.decrypt(result[key])
        return result

class RateLimiter:
    """Rate limiting for API endpoints and user actions"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.local_store = defaultdict(list)  # Fallback for no Redis
        self.lock = Lock()
        
        # Rate limit configurations
        self.limits = {
            'login': {'requests': 5, 'window': 300},  # 5 attempts per 5 minutes
            'api_general': {'requests': 60, 'window': 60},  # 60 requests per minute
            'trading': {'requests': 10, 'window': 60},  # 10 trades per minute
            'sensitive_ops': {'requests': 3, 'window': 300},  # 3 sensitive operations per 5 minutes
        }
        
    def is_allowed(self, identifier: str, limit_type: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is within rate limits"""
        if limit_type not in self.limits:
            return True, {}
            
        config = self.limits[limit_type]
        now = time.time()
        window_start = now - config['window']
        
        if self.redis_client:
            return self._check_redis_rate_limit(identifier, limit_type, now, window_start, config)
        else:
            return self._check_local_rate_limit(identifier, limit_type, now, window_start, config)
            
    def _check_redis_rate_limit(self, identifier: str, limit_type: str, now: float, 
                               window_start: float, config: Dict) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit using Redis"""
        key = f"rate_limit:{limit_type}:{identifier}"
        
        try:
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcount(key, window_start, now)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, config['window'])
            results = pipe.execute()
            
            current_requests = results[1]
            allowed = current_requests < config['requests']
            
            return allowed, {
                'current_requests': current_requests,
                'limit': config['requests'],
                'window': config['window'],
                'reset_time': now + config['window']
            }
            
        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}")
            return True, {}  # Allow on Redis errors
            
    def _check_local_rate_limit(self, identifier: str, limit_type: str, now: float,
                               window_start: float, config: Dict) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit using local memory"""
        with self.lock:
            key = f"{limit_type}:{identifier}"
            requests = self.local_store[key]
            
            # Clean old requests
            requests[:] = [req_time for req_time in requests if req_time > window_start]
            
            current_requests = len(requests)
            allowed = current_requests < config['requests']
            
            if allowed:
                requests.append(now)
                
            return allowed, {
                'current_requests': current_requests,
                'limit': config['requests'],
                'window': config['window'],
                'reset_time': now + config['window']
            }

class GeolocationAnalyzer:
    """Analyzes geolocation patterns for security"""
    
    def __init__(self):
        self.geoip_db_path = os.getenv('GEOIP_DB_PATH', 'data/GeoLite2-City.mmdb')
        self.reader = None
        
        try:
            if os.path.exists(self.geoip_db_path):
                self.reader = geoip2.database.Reader(self.geoip_db_path)
                logger.info("GeoIP database loaded successfully")
            else:
                logger.warning("GeoIP database not found. Geolocation analysis disabled.")
        except Exception as e:
            logger.error(f"Failed to load GeoIP database: {e}")
            
    def get_location_info(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Get location information for IP address"""
        if not self.reader:
            return None
            
        try:
            response = self.reader.city(ip_address)
            return {
                'country': response.country.name,
                'country_code': response.country.iso_code,
                'city': response.city.name,
                'latitude': float(response.location.latitude) if response.location.latitude else None,
                'longitude': float(response.location.longitude) if response.location.longitude else None,
                'timezone': response.location.time_zone,
                'accuracy_radius': response.location.accuracy_radius
            }
        except geoip2.errors.AddressNotFoundError:
            logger.debug(f"IP address not found in GeoIP database: {ip_address}")
            return None
        except Exception as e:
            logger.error(f"GeoIP lookup error: {e}")
            return None
            
    def is_location_anomaly(self, user_id: str, current_ip: str, 
                           previous_locations: List[Dict[str, Any]]) -> bool:
        """Detect location anomalies"""
        if not self.reader or not previous_locations:
            return False
            
        current_location = self.get_location_info(current_ip)
        if not current_location:
            return False
            
        # Check if country changed
        previous_countries = {loc.get('country_code') for loc in previous_locations}
        if current_location['country_code'] not in previous_countries:
            logger.warning(f"Country change detected for user {user_id}: {current_location['country']}")
            return True
            
        # Check distance (simplified - would use proper geospatial calculation)
        # This is a basic implementation
        for prev_loc in previous_locations[-3:]:  # Check last 3 locations
            if (prev_loc.get('latitude') and prev_loc.get('longitude') and
                current_location.get('latitude') and current_location.get('longitude')):
                
                # Simple distance check (would use haversine formula in production)
                lat_diff = abs(current_location['latitude'] - prev_loc['latitude'])
                lon_diff = abs(current_location['longitude'] - prev_loc['longitude'])
                
                # If difference is more than ~1000km (very rough approximation)
                if lat_diff > 10 or lon_diff > 10:
                    logger.warning(f"Large distance change detected for user {user_id}")
                    return True
                    
        return False

class SecurityAnalyzer:
    """Analyzes patterns for security threats"""
    
    def __init__(self):
        self.suspicious_patterns = {
            'sql_injection': [
                r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC)\b)",
                r"(\b(UNION|AND|OR)\s+\d+\s*=\s*\d+)",
                r"('|\"|;|--|\/\*|\*\/)"
            ],
            'xss_attempt': [
                r"(<script|<iframe|<object|<embed|<applet)",
                r"(javascript:|data:text\/html|vbscript:)",
                r"(onload|onerror|onclick|onmouseover)\s*="
            ],
            'path_traversal': [
                r"(\.\./|\.\.\\|%2e%2e%2f|%2e%2e%5c)",
                r"(/etc/passwd|/windows/system32)"
            ]
        }
        
    def analyze_request_for_threats(self, request_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze request for security threats"""
        threats = []
        
        # Convert all request data to string for analysis
        request_str = json.dumps(request_data).lower()
        
        for threat_type, patterns in self.suspicious_patterns.items():
            for pattern in patterns:
                if re.search(pattern, request_str, re.IGNORECASE):
                    threats.append({
                        'type': threat_type,
                        'pattern': pattern,
                        'severity': 'HIGH'
                    })
                    break
                    
        return threats
        
    def analyze_user_behavior(self, user_id: str, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user behavior patterns"""
        if not actions:
            return {'anomaly_score': 0, 'patterns': []}
            
        analysis = {
            'anomaly_score': 0,
            'patterns': [],
            'recommendations': []
        }
        
        # Analyze action frequency
        action_times = [action.get('timestamp') for action in actions if action.get('timestamp')]
        if len(action_times) > 10:  # Need sufficient data
            # Calculate time intervals
            intervals = []
            for i in range(1, len(action_times)):
                if isinstance(action_times[i], datetime) and isinstance(action_times[i-1], datetime):
                    interval = (action_times[i] - action_times[i-1]).total_seconds()
                    intervals.append(interval)
                    
            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                
                # Check for bot-like behavior (very regular intervals)
                if len(set(int(interval) for interval in intervals[-10:])) < 3:
                    analysis['anomaly_score'] += 30
                    analysis['patterns'].append('bot_like_regular_intervals')
                    
                # Check for rapid-fire actions
                rapid_actions = sum(1 for interval in intervals if interval < 1)
                if rapid_actions > len(intervals) * 0.5:
                    analysis['anomaly_score'] += 40
                    analysis['patterns'].append('rapid_fire_actions')
                    
        # Analyze action types
        action_types = [action.get('type') for action in actions]
        unique_actions = set(action_types)
        
        # Check for automated patterns
        if len(unique_actions) < len(action_types) * 0.1:  # Very repetitive
            analysis['anomaly_score'] += 20
            analysis['patterns'].append('repetitive_actions')
            
        return analysis

class TokenManager:
    """Manages JWT tokens with enhanced security"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.algorithm = 'HS256'
        self.token_blacklist = set()  # In production, use Redis
        
    def create_token(self, user_id: str, permissions: List[str], 
                    expires_delta: Optional[timedelta] = None, 
                    additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """Create JWT token with enhanced claims"""
        if expires_delta is None:
            expires_delta = timedelta(hours=24)
            
        now = datetime.utcnow()
        claims = {
            'sub': user_id,
            'iat': now,
            'exp': now + expires_delta,
            'permissions': permissions,
            'jti': secrets.token_urlsafe(32),  # Unique token ID
            'token_type': 'access'
        }
        
        if additional_claims:
            claims.update(additional_claims)
            
        return jwt.encode(claims, self.secret_key, algorithm=self.algorithm)
        
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            # Check if token is blacklisted
            if token in self.token_blacklist:
                logger.warning("Blacklisted token used")
                return None
                
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Additional validation
            if payload.get('token_type') != 'access':
                logger.warning("Invalid token type")
                return None
                
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.debug("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
            
    def blacklist_token(self, token: str):
        """Add token to blacklist"""
        self.token_blacklist.add(token)
        
    def create_refresh_token(self, user_id: str) -> str:
        """Create refresh token"""
        claims = {
            'sub': user_id,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(days=7),
            'jti': secrets.token_urlsafe(32),
            'token_type': 'refresh'
        }
        
        return jwt.encode(claims, self.secret_key, algorithm=self.algorithm)

class SecurityManager:
    """Main security management class"""
    
    def __init__(self):
        self.encryption = EncryptionManager()
        self.rate_limiter = RateLimiter(self._get_redis_client())
        self.geolocation = GeolocationAnalyzer()
        self.analyzer = SecurityAnalyzer()
        self.token_manager = TokenManager(os.getenv('JWT_SECRET_KEY'))
        
        # Security configuration
        self.max_login_attempts = int(os.getenv('MAX_LOGIN_ATTEMPTS', '5'))
        self.lockout_duration = int(os.getenv('LOCKOUT_DURATION_MINUTES', '30'))
        self.password_min_length = int(os.getenv('PASSWORD_MIN_LENGTH', '12'))
        
        # Event storage
        self.security_events: List[SecurityEvent] = []
        self.blocked_ips: Dict[str, datetime] = {}
        
    def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client for rate limiting"""
        try:
            if os.getenv('REDIS_ENABLED', 'true').lower() == 'true':
                return redis.Redis(
                    host=os.getenv('REDIS_HOST', 'localhost'),
                    port=int(os.getenv('REDIS_PORT', '6379')),
                    db=int(os.getenv('REDIS_DB', '0')),
                    password=os.getenv('REDIS_PASSWORD'),
                    decode_responses=True
                )
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
        return None
        
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """Validate password strength"""
        issues = []
        score = 0
        
        if len(password) < self.password_min_length:
            issues.append(f"Password must be at least {self.password_min_length} characters")
        else:
            score += 20
            
        if not re.search(r'[A-Z]', password):
            issues.append("Password must contain uppercase letters")
        else:
            score += 20
            
        if not re.search(r'[a-z]', password):
            issues.append("Password must contain lowercase letters")
        else:
            score += 20
            
        if not re.search(r'\d', password):
            issues.append("Password must contain numbers")
        else:
            score += 20
            
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>?]', password):
            issues.append("Password must contain special characters")
        else:
            score += 20
            
        # Check for common patterns
        if re.search(r'(\w)\1{2,}', password):  # Repeated characters
            issues.append("Password should not contain repeated characters")
            score -= 10
            
        if re.search(r'(123|abc|password|admin)', password.lower()):
            issues.append("Password should not contain common patterns")
            score -= 20
            
        strength = 'WEAK'
        if score >= 80:
            strength = 'STRONG'
        elif score >= 60:
            strength = 'MEDIUM'
            
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'score': max(0, score),
            'strength': strength
        }
        
    async def authenticate_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive request authentication and security analysis"""
        ip_address = request_data.get('ip_address', '')
        user_agent = request_data.get('user_agent', '')
        token = request_data.get('token')
        user_id = request_data.get('user_id')
        
        result = {
            'authenticated': False,
            'user_id': None,
            'permissions': [],
            'security_warnings': [],
            'blocked': False
        }
        
        # Check if IP is blocked
        if ip_address in self.blocked_ips:
            if datetime.utcnow() < self.blocked_ips[ip_address]:
                result['blocked'] = True
                result['security_warnings'].append('IP address is temporarily blocked')
                return result
            else:
                del self.blocked_ips[ip_address]
                
        # Rate limiting check
        allowed, rate_info = self.rate_limiter.is_allowed(ip_address, 'api_general')
        if not allowed:
            result['security_warnings'].append('Rate limit exceeded')
            await self._log_security_event(
                SecurityEventType.RATE_LIMIT_EXCEEDED,
                ThreatLevel.MEDIUM,
                user_id, ip_address, user_agent,
                {'rate_limit_info': rate_info}
            )
            
        # Analyze request for threats
        threats = self.analyzer.analyze_request_for_threats(request_data)
        if threats:
            result['security_warnings'].extend([f"Potential {t['type']} detected" for t in threats])
            await self._log_security_event(
                SecurityEventType.INJECTION_ATTEMPT,
                ThreatLevel.HIGH,
                user_id, ip_address, user_agent,
                {'threats': threats}
            )
            
        # Token validation
        if token:
            token_data = self.token_manager.verify_token(token)
            if token_data:
                result['authenticated'] = True
                result['user_id'] = token_data.get('sub')
                result['permissions'] = token_data.get('permissions', [])
            else:
                result['security_warnings'].append('Invalid or expired token')
                await self._log_security_event(
                    SecurityEventType.TOKEN_MANIPULATION,
                    ThreatLevel.MEDIUM,
                    user_id, ip_address, user_agent,
                    {'token_validation': 'failed'}
                )
                
        return result
        
    async def _log_security_event(self, event_type: SecurityEventType, threat_level: ThreatLevel,
                                 user_id: Optional[str], ip_address: str, user_agent: str,
                                 details: Dict[str, Any]):
        """Log security event"""
        event = SecurityEvent(
            id=secrets.token_urlsafe(16),
            event_type=event_type,
            threat_level=threat_level,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            action_taken='logged'
        )
        
        self.security_events.append(event)
        
        # Log to file/database in production
        logger.warning(f"Security event: {event_type.value} - {threat_level.value} - IP: {ip_address}")
        
        # Take action for high-severity events
        if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            await self._handle_high_severity_event(event)
            
    async def _handle_high_severity_event(self, event: SecurityEvent):
        """Handle high-severity security events"""
        if event.threat_level == ThreatLevel.CRITICAL:
            # Block IP for critical threats
            self.blocked_ips[event.ip_address] = datetime.utcnow() + timedelta(minutes=self.lockout_duration)
            event.action_taken = 'ip_blocked'
            event.blocked = True
            
        # In production, send alerts to security team
        logger.critical(f"HIGH SEVERITY SECURITY EVENT: {event.event_type.value} from {event.ip_address}")

# Global security manager instance
_security_manager = None

def get_security_manager() -> SecurityManager:
    """Get or create the global security manager instance"""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This would integrate with your actual request context
            # For now, just a placeholder
            logger.info(f"Permission check: {permission} required")
            return await func(*args, **kwargs)
        return wrapper
    return decorator