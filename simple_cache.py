"""
Simple in-memory cache for database query results.
Reduces database hits for frequently accessed data.
"""
import time
import logging
from typing import Any, Callable, Optional, Dict

logger = logging.getLogger(__name__)


class SimpleCache:
    """Simple in-memory cache with TTL (time-to-live)."""
    
    def __init__(self):
        self.cache: Dict[str, tuple] = {}  # {key: (value, expiry_time)}
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if it exists and hasn't expired."""
        if key not in self.cache:
            self.misses += 1
            return None
        
        value, expiry = self.cache[key]
        if time.time() > expiry:
            # Expired
            del self.cache[key]
            self.misses += 1
            return None
        
        self.hits += 1
        return value
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """Set value in cache with TTL (default 5 minutes)."""
        expiry = time.time() + ttl
        self.cache[key] = (value, expiry)
    
    def get_or_fetch(self, key: str, fetch_fn: Callable, ttl: int = 300) -> Any:
        """Get from cache or fetch and cache if not found."""
        cached = self.get(key)
        if cached is not None:
            logger.debug(f"✅ Cache HIT: {key}")
            return cached
        
        logger.debug(f"❌ Cache MISS: {key} - fetching...")
        value = fetch_fn()
        self.set(key, value, ttl)
        return value
    
    def clear(self):
        """Clear all cache."""
        self.cache.clear()
    
    def stats(self) -> str:
        """Get cache statistics."""
        total = self.hits + self.misses
        if total == 0:
            return "No cache activity"
        hit_rate = (self.hits / total) * 100
        return f"Cache: {self.hits} hits, {self.misses} misses ({hit_rate:.1f}% hit rate)"


# Global cache instance
_cache = SimpleCache()


def get_cache() -> SimpleCache:
    """Get global cache instance."""
    return _cache
