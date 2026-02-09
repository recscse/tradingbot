import os
import json
import logging
import redis
from typing import Optional, Any
from redis.exceptions import ConnectionError, RedisError

logger = logging.getLogger(__name__)

class TradingSafeRedisManager:
    """Redis manager specifically designed for trading applications with graceful fallbacks"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.is_connected = False
        self.fallback_cache = {}
        self._initialize_redis()

    def _initialize_redis(self):
        """Initialize Redis connection with comprehensive error handling"""
        redis_enabled = os.getenv("REDIS_ENABLED", "true").lower() == "true"

        if not redis_enabled:
            logger.info("🔧 Redis disabled via REDIS_ENABLED environment variable")
            return

        try:
            self.redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                db=int(os.getenv("REDIS_DB", 0)),
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=False,
                health_check_interval=30,
            )

            # Test connection
            self.redis_client.ping()
            self.is_connected = True
            logger.info("✅ Redis connected successfully for trading system")

        except ConnectionError:
            logger.warning(
                "⚠️ Redis connection failed - trading system will use fallback cache"
            )
            self.redis_client = None
            self.is_connected = False
        except Exception as e:
            logger.error(f"❌ Redis initialization error: {e} - using fallback cache")
            self.redis_client = None
            self.is_connected = False

    def get(self, key: str, default: Any = None) -> Any:
        """Get value with fallback to in-memory cache for critical trading data"""
        if self.is_connected and self.redis_client:
            try:
                result = self.redis_client.get(key)
                if result is None:
                    return self.fallback_cache.get(key, default)

                try:
                    parsed_result = json.loads(result)
                    if any(
                        critical in key
                        for critical in [
                            "live_price",
                            "selected_stocks",
                            "trading_data",
                        ]
                    ):
                        self.fallback_cache[key] = parsed_result
                    return parsed_result
                except (json.JSONDecodeError, TypeError):
                    if any(
                        critical in key
                        for critical in [
                            "live_price",
                            "selected_stocks",
                            "trading_data",
                        ]
                    ):
                        self.fallback_cache[key] = result
                    return result

            except RedisError as e:
                logger.warning(f"Redis GET error for key '{key}': {e} - using fallback")
                return self.fallback_cache.get(key, default)

        return self.fallback_cache.get(key, default)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value with fallback storage for critical data"""
        success = False

        if self.is_connected and self.redis_client:
            try:
                if isinstance(value, (dict, list)):
                    serialized_value = json.dumps(value)
                else:
                    serialized_value = value

                result = self.redis_client.set(key, serialized_value, ex=ttl)
                success = bool(result)

            except RedisError as e:
                logger.warning(f"Redis SET error for key '{key}': {e}")
                success = False

        # Always update fallback cache for critical trading data
        if any(
            critical in key
            for critical in [
                "live_price",
                "selected_stocks",
                "trading_data",
                "market_status",
            ]
        ):
            self.fallback_cache[key] = value
            if not success:
                logger.debug(f"Stored '{key}' in fallback cache")

        return success

    def delete(self, *keys: str) -> int:
        """Delete keys with fallback cache cleanup"""
        deleted_count = 0

        if self.is_connected and self.redis_client:
            try:
                deleted_count = self.redis_client.delete(*keys)
            except RedisError as e:
                logger.warning(f"Redis DELETE error: {e}")

        for key in keys:
            if key in self.fallback_cache:
                del self.fallback_cache[key]
                deleted_count += 1

        return deleted_count

    def exists(self, key: str) -> bool:
        """Check existence in Redis or fallback cache"""
        if self.is_connected and self.redis_client:
            try:
                return bool(self.redis_client.exists(key))
            except RedisError:
                pass

        return key in self.fallback_cache

    def keys(self, pattern: str = "*") -> list:
        """Get keys with fallback support"""
        redis_keys = []

        if self.is_connected and self.redis_client:
            try:
                redis_keys = self.redis_client.keys(pattern)
            except RedisError as e:
                logger.warning(f"Redis KEYS error: {e}")

        import fnmatch

        fallback_keys = [
            key for key in self.fallback_cache.keys() if fnmatch.fnmatch(key, pattern)
        ]

        all_keys = list(set(redis_keys + fallback_keys))
        return all_keys

    def health_check(self) -> dict:
        """Comprehensive health check for trading system"""
        if not self.redis_client:
            return {
                "status": "fallback_mode",
                "message": "Redis disabled - using in-memory fallback cache",
                "fallback_cache_size": len(self.fallback_cache),
            }

        try:
            self.redis_client.ping()
            self.is_connected = True
            return {
                "status": "healthy",
                "message": "Redis connection is working",
                "fallback_cache_size": len(self.fallback_cache),
            }
        except Exception as e:
            self.is_connected = False
            return {
                "status": "degraded",
                "message": f"Redis connection failed: {str(e)} - using fallback",
                "fallback_cache_size": len(self.fallback_cache),
            }

    def get_trading_cache_stats(self) -> dict:
        """Get statistics specific to trading data caching"""
        stats = {
            "redis_connected": self.is_connected,
            "fallback_cache_size": len(self.fallback_cache),
            "critical_data_cached": 0,
            "cache_mode": "redis" if self.is_connected else "fallback",
        }

        critical_keys = [
            "live_price",
            "selected_stocks",
            "trading_data",
            "market_status",
        ]
        stats["critical_data_cached"] = len(
            [
                key
                for key in self.fallback_cache.keys()
                if any(critical in key for critical in critical_keys)
            ]
        )

        return stats
