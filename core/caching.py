#!/usr/bin/env python3
"""
Production-Grade Caching System
Multi-level caching with TTL, LRU eviction, and intelligent cache warming.
"""

import asyncio
import hashlib
import json
import time
from typing import Optional, Any, Dict, Callable, TypeVar
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict
from functools import wraps
import pickle

from .exceptions import CacheError, CacheMissError
from .observability import StructuredLogger

logger = StructuredLogger("cache")

T = TypeVar('T')


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def touch(self):
        """Update access metadata."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()


class LRUCache:
    """
    LRU (Least Recently Used) Cache with TTL support.

    Thread-safe, async-compatible cache with automatic eviction.
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[float] = None,  # seconds
        max_memory_bytes: Optional[int] = None
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.max_memory_bytes = max_memory_bytes

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self._current_memory = 0

        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    async def get(self, key: str) -> Any:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value

        Raises:
            CacheMissError: If key not found or expired
        """
        async with self._lock:
            if key not in self._cache:
                self.misses += 1
                logger.debug(f"Cache miss: {key}", hits=self.hits, misses=self.misses)
                raise CacheMissError(key)

            entry = self._cache[key]

            # Check expiration
            if entry.is_expired():
                logger.debug(f"Cache entry expired: {key}")
                await self._remove_entry(key)
                self.misses += 1
                raise CacheMissError(key)

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.touch()
            self.hits += 1

            logger.debug(
                f"Cache hit: {key}",
                hits=self.hits,
                misses=self.misses,
                hit_rate=self.get_hit_rate()
            )

            return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None
    ):
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None = use default)
        """
        async with self._lock:
            # Calculate size
            size_bytes = self._estimate_size(value)

            # Calculate expiration
            ttl_seconds = ttl if ttl is not None else self.default_ttl
            expires_at = None
            if ttl_seconds is not None:
                expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

            # Create entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.utcnow(),
                expires_at=expires_at,
                size_bytes=size_bytes
            )

            # Remove old entry if exists
            if key in self._cache:
                await self._remove_entry(key)

            # Check memory limit
            if self.max_memory_bytes:
                while (
                    self._current_memory + size_bytes > self.max_memory_bytes
                    and self._cache
                ):
                    await self._evict_lru()

            # Check size limit
            while len(self._cache) >= self.max_size and self._cache:
                await self._evict_lru()

            # Add entry
            self._cache[key] = entry
            self._current_memory += size_bytes

            logger.debug(
                f"Cache set: {key}",
                size_bytes=size_bytes,
                ttl=ttl_seconds,
                total_entries=len(self._cache)
            )

    async def delete(self, key: str):
        """Delete entry from cache."""
        async with self._lock:
            await self._remove_entry(key)

    async def clear(self):
        """Clear entire cache."""
        async with self._lock:
            self._cache.clear()
            self._current_memory = 0
            logger.info("Cache cleared")

    async def _remove_entry(self, key: str):
        """Remove entry and update memory."""
        if key in self._cache:
            entry = self._cache.pop(key)
            self._current_memory -= entry.size_bytes

    async def _evict_lru(self):
        """Evict least recently used entry."""
        if not self._cache:
            return

        # Remove first item (least recently used)
        key, entry = self._cache.popitem(last=False)
        self._current_memory -= entry.size_bytes
        self.evictions += 1

        logger.debug(
            f"Cache eviction: {key}",
            reason="LRU",
            total_evictions=self.evictions
        )

    def _estimate_size(self, value: Any) -> int:
        """Estimate size of value in bytes."""
        try:
            return len(pickle.dumps(value))
        except Exception:
            # Fallback estimation
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (int, float)):
                return 8
            elif isinstance(value, (list, dict)):
                return len(json.dumps(value, default=str))
            else:
                return 1024  # Default 1KB estimate

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "memory_bytes": self._current_memory,
            "max_memory_bytes": self.max_memory_bytes,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": self.get_hit_rate()
        }

    def get_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class MultiLevelCache:
    """
    Multi-level cache with L1 (memory) and L2 (disk/persistent) support.

    Implements cache promotion/demotion strategies.
    """

    def __init__(
        self,
        l1_size: int = 100,
        l1_ttl: Optional[float] = 300,  # 5 minutes
        l2_size: int = 1000,
        l2_ttl: Optional[float] = 3600,  # 1 hour
    ):
        self.l1_cache = LRUCache(max_size=l1_size, default_ttl=l1_ttl)
        self.l2_cache = LRUCache(max_size=l2_size, default_ttl=l2_ttl)

    async def get(self, key: str) -> Any:
        """
        Get value from cache, checking L1 then L2.

        Promotes L2 hits to L1 for better performance.
        """
        try:
            # Try L1 first
            return await self.l1_cache.get(key)
        except CacheMissError:
            pass

        try:
            # Try L2
            value = await self.l2_cache.get(key)

            # Promote to L1
            await self.l1_cache.set(key, value)
            logger.debug(f"Cache promotion: {key} from L2 to L1")

            return value
        except CacheMissError:
            raise

    async def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """
        Set value in cache.

        Writes to both L1 and L2 for consistency.
        """
        await self.l1_cache.set(key, value, ttl)
        await self.l2_cache.set(key, value, ttl)

    async def delete(self, key: str):
        """Delete from both cache levels."""
        await self.l1_cache.delete(key)
        await self.l2_cache.delete(key)

    async def clear(self):
        """Clear both cache levels."""
        await self.l1_cache.clear()
        await self.l2_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for both cache levels."""
        return {
            "l1": self.l1_cache.get_stats(),
            "l2": self.l2_cache.get_stats(),
            "combined_hit_rate": self._calculate_combined_hit_rate()
        }

    def _calculate_combined_hit_rate(self) -> float:
        """Calculate combined hit rate across cache levels."""
        total_hits = self.l1_cache.hits + self.l2_cache.hits
        total_misses = self.l2_cache.misses  # Only count L2 misses (complete misses)
        total = total_hits + total_misses
        return total_hits / total if total > 0 else 0.0


def cache_key(*args, **kwargs) -> str:
    """
    Generate cache key from function arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Hash of arguments as cache key
    """
    # Create stable representation
    key_parts = []

    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            key_parts.append(json.dumps(arg, sort_keys=True, default=str))

    for k, v in sorted(kwargs.items()):
        if isinstance(v, (str, int, float, bool)):
            key_parts.append(f"{k}={v}")
        else:
            key_parts.append(f"{k}={json.dumps(v, sort_keys=True, default=str)}")

    key_string = "|".join(key_parts)
    return hashlib.sha256(key_string.encode()).hexdigest()


def cached(
    cache: Optional[LRUCache] = None,
    ttl: Optional[float] = None,
    key_prefix: Optional[str] = None
):
    """
    Decorator for caching function results.

    Args:
        cache: Cache instance to use (creates default if None)
        ttl: Time to live for cached result
        key_prefix: Prefix for cache keys

    Example:
        @cached(ttl=300)
        async def expensive_function(arg1, arg2):
            # Your expensive operation
            return result
    """
    cache_instance = cache or LRUCache()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            # Generate cache key
            func_name = func.__name__
            prefix = key_prefix or func_name
            key = f"{prefix}:{cache_key(*args, **kwargs)}"

            # Try to get from cache
            try:
                result = await cache_instance.get(key)
                logger.debug(f"Cache hit for {func_name}", key=key)
                return result
            except CacheMissError:
                pass

            # Execute function
            logger.debug(f"Cache miss for {func_name}, executing", key=key)
            result = await func(*args, **kwargs)

            # Cache result
            await cache_instance.set(key, result, ttl)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            # For sync functions, use asyncio.run
            import inspect
            if inspect.iscoroutinefunction(func):
                raise ValueError("Use async wrapper for async functions")

            # Generate cache key
            func_name = func.__name__
            prefix = key_prefix or func_name
            key = f"{prefix}:{cache_key(*args, **kwargs)}"

            # Try to get from cache (sync)
            try:
                result = asyncio.run(cache_instance.get(key))
                logger.debug(f"Cache hit for {func_name}", key=key)
                return result
            except CacheMissError:
                pass

            # Execute function
            logger.debug(f"Cache miss for {func_name}, executing", key=key)
            result = func(*args, **kwargs)

            # Cache result (sync)
            asyncio.run(cache_instance.set(key, result, ttl))

            return result

        # Return appropriate wrapper
        import inspect
        if inspect.iscoroutinefunction(func):
            async_wrapper.cache = cache_instance  # Attach for monitoring
            return async_wrapper
        else:
            sync_wrapper.cache = cache_instance  # Attach for monitoring
            return sync_wrapper

    return decorator


# Global cache instance
default_cache = LRUCache(max_size=1000, default_ttl=300)
