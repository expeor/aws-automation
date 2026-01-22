"""
core/data/inventory/cache.py - TTL-based Resource Cache

Provides in-memory caching with optional file persistence for resource data.
"""

from __future__ import annotations

import fnmatch
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from threading import RLock
from typing import Any


@dataclass
class CacheConfig:
    """Cache configuration"""

    ttl_minutes: int = 30
    cache_dir: Path | None = None
    enable_file_cache: bool = False

    def __post_init__(self):
        if self.cache_dir is None:
            self.cache_dir = Path("temp/inventory")


@dataclass
class CacheEntry:
    """Single cache entry with metadata"""

    data: Any
    created_at: datetime
    ttl_minutes: int
    key: str = ""

    @property
    def expires_at(self) -> datetime:
        return self.created_at + timedelta(minutes=self.ttl_minutes)

    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.created_at).total_seconds()


class ResourceCache:
    """TTL-based cache for resource data

    Provides thread-safe caching with optional file persistence.
    Keys typically follow the format: "{resource_type}:{account_id}:{region}"

    Example:
        cache = ResourceCache(ttl_minutes=30)

        # Store data
        cache.set("ec2:123456789012:us-east-1", instances)

        # Retrieve data (returns None if expired)
        data = cache.get("ec2:123456789012:us-east-1")

        # Force refresh
        cache.invalidate("ec2:*")  # Invalidate all EC2 entries
    """

    def __init__(
        self,
        ttl_minutes: int = 30,
        config: CacheConfig | None = None,
    ):
        """Initialize cache

        Args:
            ttl_minutes: Default TTL in minutes
            config: Optional CacheConfig for advanced settings
        """
        self._config = config or CacheConfig(ttl_minutes=ttl_minutes)
        self._cache: dict[str, CacheEntry] = {}
        self._lock = RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """Get cached data if not expired

        Args:
            key: Cache key (e.g., "ec2:123456789012:us-east-1")

        Returns:
            Cached data or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired:
                del self._cache[key]
                self._misses += 1
                return None

            self._hits += 1
            return entry.data

    def set(
        self,
        key: str,
        data: Any,
        ttl_minutes: int | None = None,
    ) -> None:
        """Store data in cache

        Args:
            key: Cache key
            data: Data to cache
            ttl_minutes: Optional custom TTL (uses default if not specified)
        """
        with self._lock:
            self._cache[key] = CacheEntry(
                key=key,
                data=data,
                created_at=datetime.now(),
                ttl_minutes=ttl_minutes or self._config.ttl_minutes,
            )

    def invalidate(self, pattern: str = "*") -> int:
        """Invalidate cache entries matching pattern

        Args:
            pattern: Glob pattern for keys to invalidate (default: all)

        Returns:
            Number of entries invalidated
        """
        with self._lock:
            if pattern == "*":
                count = len(self._cache)
                self._cache.clear()
                return count

            keys_to_delete = [
                key for key in self._cache.keys() if fnmatch.fnmatch(key, pattern)
            ]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)

    def has(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        return self.get(key) is not None

    def keys(self, pattern: str = "*") -> list[str]:
        """Get all cache keys matching pattern"""
        with self._lock:
            if pattern == "*":
                return list(self._cache.keys())
            return [key for key in self._cache.keys() if fnmatch.fnmatch(key, pattern)]

    def get_or_compute(
        self,
        key: str,
        compute_fn: callable,
        ttl_minutes: int | None = None,
        force_refresh: bool = False,
    ) -> Any:
        """Get cached value or compute and cache it

        Args:
            key: Cache key
            compute_fn: Function to compute value if not cached
            ttl_minutes: Optional custom TTL
            force_refresh: If True, ignore cache and recompute

        Returns:
            Cached or computed value
        """
        if not force_refresh:
            cached = self.get(key)
            if cached is not None:
                return cached

        data = compute_fn()
        self.set(key, data, ttl_minutes)
        return data

    @property
    def stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._hits + self._misses
            return {
                "entries": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total_requests if total_requests > 0 else 0.0,
                "ttl_minutes": self._config.ttl_minutes,
            }

    def clear_expired(self) -> int:
        """Remove expired entries

        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() if entry.is_expired
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    def save_to_file(self, filepath: Path | None = None) -> None:
        """Save cache to file (JSON format, for debugging/persistence)"""
        if filepath is None:
            if self._config.cache_dir:
                filepath = self._config.cache_dir / "inventory_cache.json"
            else:
                return

        with self._lock:
            os.makedirs(filepath.parent, exist_ok=True)

            serializable = {}
            for key, entry in self._cache.items():
                if not entry.is_expired:
                    # Only serialize simple types
                    try:
                        serializable[key] = {
                            "created_at": entry.created_at.isoformat(),
                            "ttl_minutes": entry.ttl_minutes,
                            "data_type": type(entry.data).__name__,
                            "data_count": len(entry.data) if hasattr(entry.data, "__len__") else 1,
                        }
                    except (TypeError, AttributeError):
                        pass

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=2, ensure_ascii=False)

    def __repr__(self) -> str:
        stats = self.stats
        return (
            f"ResourceCache(entries={stats['entries']}, "
            f"hit_rate={stats['hit_rate']:.1%}, "
            f"ttl={stats['ttl_minutes']}min)"
        )


# Global cache instance (optional, for sharing across collectors)
_global_cache: ResourceCache | None = None


def get_global_cache(ttl_minutes: int = 30) -> ResourceCache:
    """Get or create global cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = ResourceCache(ttl_minutes=ttl_minutes)
    return _global_cache


def clear_global_cache() -> None:
    """Clear global cache"""
    global _global_cache
    if _global_cache is not None:
        _global_cache.invalidate()
