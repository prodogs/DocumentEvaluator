"""
Cache Module

Provides caching functionality with Redis backend and fallback to in-memory cache.
"""

import json
import pickle
import time
import hashlib
from functools import wraps
from typing import Any, Optional, Callable, Union, Dict
from datetime import timedelta

import redis
from flask import current_app
from app.core.logger import get_logger, get_performance_logger

logger = get_logger(__name__)
perf_logger = get_performance_logger('cache')


class CacheManager:
    """Manages caching with Redis or in-memory fallback"""
    
    def __init__(self, redis_url: Optional[str] = None, default_timeout: int = 300):
        self.redis_url = redis_url
        self.default_timeout = default_timeout
        self.redis_client = None
        self.memory_cache = {}  # Fallback cache
        self._connect()
    
    def _connect(self):
        """Connect to Redis if available"""
        if self.redis_url:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=False,  # We'll handle encoding/decoding
                    socket_keepalive=True,
                    socket_keepalive_options={
                        1: 1,  # TCP_KEEPIDLE
                        2: 1,  # TCP_KEEPINTVL
                        3: 3,  # TCP_KEEPCNT
                    }
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Connected to Redis cache")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Using in-memory cache.")
                self.redis_client = None
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            # Try JSON first (more portable)
            return json.dumps(value).encode('utf-8')
        except (TypeError, ValueError):
            # Fall back to pickle for complex objects
            return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        if not data:
            return None
        
        try:
            # Try JSON first
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            return pickle.loads(data)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        start_time = time.time()
        
        try:
            if self.redis_client:
                data = self.redis_client.get(key)
                value = self._deserialize(data) if data else None
            else:
                # In-memory fallback
                entry = self.memory_cache.get(key)
                if entry and (entry['expires'] == 0 or entry['expires'] > time.time()):
                    value = entry['value']
                else:
                    value = None
                    if key in self.memory_cache:
                        del self.memory_cache[key]
            
            duration = time.time() - start_time
            perf_logger.log_operation(
                'cache_get',
                duration,
                success=value is not None,
                metadata={'key': key, 'hit': value is not None}
            )
            
            return value
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Set value in cache"""
        start_time = time.time()
        timeout = timeout or self.default_timeout
        
        try:
            if self.redis_client:
                data = self._serialize(value)
                if timeout > 0:
                    success = self.redis_client.setex(key, timeout, data)
                else:
                    success = self.redis_client.set(key, data)
            else:
                # In-memory fallback
                self.memory_cache[key] = {
                    'value': value,
                    'expires': time.time() + timeout if timeout > 0 else 0
                }
                success = True
            
            duration = time.time() - start_time
            perf_logger.log_operation(
                'cache_set',
                duration,
                success=success,
                metadata={'key': key, 'timeout': timeout}
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            if self.redis_client:
                return bool(self.redis_client.delete(key))
            else:
                if key in self.memory_cache:
                    del self.memory_cache[key]
                    return True
                return False
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def clear(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries matching pattern"""
        count = 0
        
        try:
            if self.redis_client:
                if pattern:
                    # Clear matching keys
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        count = self.redis_client.delete(*keys)
                else:
                    # Clear all
                    self.redis_client.flushdb()
                    count = -1  # Unknown count
            else:
                if pattern:
                    # Clear matching keys from memory cache
                    import fnmatch
                    keys_to_delete = [
                        k for k in self.memory_cache.keys()
                        if fnmatch.fnmatch(k, pattern)
                    ]
                    for key in keys_to_delete:
                        del self.memory_cache[key]
                        count += 1
                else:
                    # Clear all
                    count = len(self.memory_cache)
                    self.memory_cache.clear()
            
            logger.info(f"Cleared {count} cache entries")
            return count
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0
    
    def get_many(self, keys: list) -> Dict[str, Any]:
        """Get multiple values from cache"""
        result = {}
        
        try:
            if self.redis_client:
                # Get all values in one operation
                values = self.redis_client.mget(keys)
                for key, data in zip(keys, values):
                    if data:
                        result[key] = self._deserialize(data)
            else:
                # In-memory fallback
                for key in keys:
                    value = self.get(key)
                    if value is not None:
                        result[key] = value
            
            return result
            
        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return {}
    
    def set_many(self, mapping: Dict[str, Any], timeout: Optional[int] = None) -> bool:
        """Set multiple values in cache"""
        timeout = timeout or self.default_timeout
        
        try:
            if self.redis_client:
                # Use pipeline for atomic operation
                pipe = self.redis_client.pipeline()
                for key, value in mapping.items():
                    data = self._serialize(value)
                    if timeout > 0:
                        pipe.setex(key, timeout, data)
                    else:
                        pipe.set(key, data)
                pipe.execute()
            else:
                # In-memory fallback
                for key, value in mapping.items():
                    self.set(key, value, timeout)
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False
    
    def increment(self, key: str, delta: int = 1) -> Optional[int]:
        """Increment a counter in cache"""
        try:
            if self.redis_client:
                return self.redis_client.incr(key, delta)
            else:
                # In-memory fallback
                current = self.get(key) or 0
                new_value = current + delta
                self.set(key, new_value)
                return new_value
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None


# Global cache instance
cache = None


def init_cache(app=None):
    """Initialize cache with Flask app"""
    global cache
    
    if app:
        redis_url = app.config.get('REDIS_URL')
        default_timeout = app.config.get('CACHE_DEFAULT_TIMEOUT', 300)
    else:
        from app.core.config import get_config
        config = get_config()
        redis_url = config.REDIS_URL
        default_timeout = config.CACHE_DEFAULT_TIMEOUT
    
    cache = CacheManager(redis_url, default_timeout)
    return cache


# Decorator for caching function results
def cached(timeout: Optional[int] = None, key_prefix: Optional[str] = None,
          unless: Optional[Callable] = None):
    """Cache decorator for functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if caching should be skipped
            if unless and unless():
                return func(*args, **kwargs)
            
            # Generate cache key
            if key_prefix:
                cache_key = key_prefix
            else:
                cache_key = f"{func.__module__}.{func.__name__}"
            
            # Add args and kwargs to key
            if args:
                args_key = hashlib.md5(str(args).encode()).hexdigest()
                cache_key += f":{args_key}"
            if kwargs:
                kwargs_key = hashlib.md5(str(sorted(kwargs.items())).encode()).hexdigest()
                cache_key += f":{kwargs_key}"
            
            # Try to get from cache
            if cache:
                cached_value = cache.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cached_value
            
            # Call function and cache result
            result = func(*args, **kwargs)
            
            if cache and result is not None:
                cache.set(cache_key, result, timeout)
                logger.debug(f"Cached result for {func.__name__}")
            
            return result
        
        # Add method to clear this function's cache
        def clear_cache():
            if cache and key_prefix:
                cache.clear(f"{key_prefix}*")
            elif cache:
                cache.clear(f"{func.__module__}.{func.__name__}*")
        
        wrapper.clear_cache = clear_cache
        return wrapper
    
    return decorator


# Specialized cache decorators
def cache_result(timeout: Union[int, timedelta] = 300):
    """Cache function result with timeout"""
    if isinstance(timeout, timedelta):
        timeout = int(timeout.total_seconds())
    
    return cached(timeout=timeout)


def cache_key_func(make_key: Callable):
    """Cache with custom key function"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = make_key(*args, **kwargs)
            
            if cache:
                cached_value = cache.get(cache_key)
                if cached_value is not None:
                    return cached_value
            
            result = func(*args, **kwargs)
            
            if cache and result is not None:
                cache.set(cache_key, result)
            
            return result
        
        return wrapper
    return decorator


# Cache utilities
def invalidate_pattern(pattern: str):
    """Invalidate all cache entries matching pattern"""
    if cache:
        count = cache.clear(pattern)
        logger.info(f"Invalidated {count} cache entries matching {pattern}")


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    if not cache:
        return {'status': 'disabled'}
    
    stats = {
        'status': 'redis' if cache.redis_client else 'memory',
        'connected': cache.redis_client is not None
    }
    
    try:
        if cache.redis_client:
            info = cache.redis_client.info()
            stats.update({
                'used_memory': info.get('used_memory_human', 'N/A'),
                'connected_clients': info.get('connected_clients', 0),
                'total_commands': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': round(
                    info.get('keyspace_hits', 0) / 
                    max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1) * 100,
                    2
                )
            })
        else:
            stats.update({
                'keys': len(cache.memory_cache),
                'memory_warning': 'Using in-memory cache (not persistent)'
            })
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        stats['error'] = str(e)
    
    return stats