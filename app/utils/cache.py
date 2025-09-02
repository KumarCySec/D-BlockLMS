"""
Caching utilities using Redis
"""
import json
import redis
from typing import Any, Optional, Dict, List
from datetime import timedelta
from flask import current_app
from functools import wraps


class CacheService:
    """Redis-based caching service"""
    
    _redis_client = None
    
    @classmethod
    def get_redis_client(cls):
        """Get Redis client instance"""
        if cls._redis_client is None:
            try:
                redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
                cls._redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                cls._redis_client.ping()
            except Exception as e:
                current_app.logger.warning(f"Redis connection failed: {e}")
                cls._redis_client = None
        
        return cls._redis_client
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if Redis is available"""
        try:
            client = cls.get_redis_client()
            return client is not None and client.ping()
        except:
            return False
    
    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            client = cls.get_redis_client()
            if client is None:
                return None
            
            value = client.get(key)
            if value is not None:
                return json.loads(value)
            return None
        except Exception as e:
            current_app.logger.warning(f"Cache get failed for key {key}: {e}")
            return None
    
    @classmethod
    def set(cls, key: str, value: Any, expire: int = 600) -> bool:
        """Set value in cache with expiration (default 10 minutes)"""
        try:
            client = cls.get_redis_client()
            if client is None:
                return False
            
            serialized_value = json.dumps(value, default=str)
            return client.setex(key, expire, serialized_value)
        except Exception as e:
            current_app.logger.warning(f"Cache set failed for key {key}: {e}")
            return False
    
    @classmethod
    def delete(cls, key: str) -> bool:
        """Delete key from cache"""
        try:
            client = cls.get_redis_client()
            if client is None:
                return False
            
            return bool(client.delete(key))
        except Exception as e:
            current_app.logger.warning(f"Cache delete failed for key {key}: {e}")
            return False
    
    @classmethod
    def delete_pattern(cls, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            client = cls.get_redis_client()
            if client is None:
                return 0
            
            keys = client.keys(pattern)
            if keys:
                return client.delete(*keys)
            return 0
        except Exception as e:
            current_app.logger.warning(f"Cache delete pattern failed for {pattern}: {e}")
            return 0
    
    @classmethod
    def clear_all(cls) -> bool:
        """Clear all cache (use with caution)"""
        try:
            client = cls.get_redis_client()
            if client is None:
                return False
            
            return client.flushdb()
        except Exception as e:
            current_app.logger.warning(f"Cache clear all failed: {e}")
            return False


def cached(key_prefix: str, expire: int = 600):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            cached_result = CacheService.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            CacheService.set(cache_key, result, expire)
            
            return result
        return wrapper
    return decorator


class FilterCache:
    """Specialized cache for filter options"""
    
    CACHE_KEYS = {
        'inventory_filters': 'filters:inventory',
        'donor_filters': 'filters:donors',
        'departments': 'filters:departments',
        'languages': 'filters:languages',
        'branches': 'filters:branches',
        'batches': 'filters:batches',
        'popular_searches': 'search:popular'
    }
    
    DEFAULT_EXPIRE = 600  # 10 minutes
    
    @classmethod
    def get_inventory_filters(cls) -> Optional[Dict]:
        """Get cached inventory filter options"""
        return CacheService.get(cls.CACHE_KEYS['inventory_filters'])
    
    @classmethod
    def set_inventory_filters(cls, filters: Dict) -> bool:
        """Cache inventory filter options"""
        return CacheService.set(
            cls.CACHE_KEYS['inventory_filters'], 
            filters, 
            cls.DEFAULT_EXPIRE
        )
    
    @classmethod
    def get_donor_filters(cls) -> Optional[Dict]:
        """Get cached donor filter options"""
        return CacheService.get(cls.CACHE_KEYS['donor_filters'])
    
    @classmethod
    def set_donor_filters(cls, filters: Dict) -> bool:
        """Cache donor filter options"""
        return CacheService.set(
            cls.CACHE_KEYS['donor_filters'], 
            filters, 
            cls.DEFAULT_EXPIRE
        )
    
    @classmethod
    def get_popular_searches(cls) -> Optional[Dict]:
        """Get cached popular searches"""
        return CacheService.get(cls.CACHE_KEYS['popular_searches'])
    
    @classmethod
    def set_popular_searches(cls, searches: Dict) -> bool:
        """Cache popular searches"""
        return CacheService.set(
            cls.CACHE_KEYS['popular_searches'], 
            searches, 
            cls.DEFAULT_EXPIRE
        )
    
    @classmethod
    def invalidate_inventory_cache(cls):
        """Invalidate inventory-related cache"""
        CacheService.delete(cls.CACHE_KEYS['inventory_filters'])
        CacheService.delete(cls.CACHE_KEYS['departments'])
        CacheService.delete(cls.CACHE_KEYS['languages'])
        CacheService.delete_pattern('search:*')
    
    @classmethod
    def invalidate_donor_cache(cls):
        """Invalidate donor-related cache"""
        CacheService.delete(cls.CACHE_KEYS['donor_filters'])
        CacheService.delete(cls.CACHE_KEYS['branches'])
        CacheService.delete(cls.CACHE_KEYS['batches'])
        CacheService.delete_pattern('search:*')
    
    @classmethod
    def invalidate_all(cls):
        """Invalidate all filter cache"""
        for key in cls.CACHE_KEYS.values():
            CacheService.delete(key)
        CacheService.delete_pattern('search:*')


# Cache invalidation helpers
def invalidate_inventory_cache():
    """Helper function to invalidate inventory cache"""
    FilterCache.invalidate_inventory_cache()


def invalidate_donor_cache():
    """Helper function to invalidate donor cache"""
    FilterCache.invalidate_donor_cache()