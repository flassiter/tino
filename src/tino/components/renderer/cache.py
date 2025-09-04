"""
Render caching system for performance optimization.

Provides intelligent caching of rendered markdown with invalidation strategies
and performance monitoring.
"""

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from tino.core.interfaces.renderer import RenderResult


@dataclass
class CacheEntry:
    """Represents a cached render result with metadata."""

    result: RenderResult
    timestamp: float
    access_count: int
    last_access: float
    content_hash: str
    file_path_hash: str | None = None


class RenderCache:
    """
    LRU cache for rendered markdown content with intelligent invalidation.

    Features:
    - LRU eviction policy
    - Content-based cache keys
    - Access statistics
    - Size limits
    - Time-based invalidation
    """

    def __init__(self, max_size: int = 100, max_age_seconds: float = 300.0) -> None:
        """
        Initialize the render cache.

        Args:
            max_size: Maximum number of entries to cache
            max_age_seconds: Maximum age of cache entries in seconds
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._max_age = max_age_seconds

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._invalidations = 0

    def get(
        self, content: str, file_path: str | None = None, theme: str = "dark"
    ) -> RenderResult | None:
        """
        Get cached render result if available and valid.

        Args:
            content: Markdown content
            file_path: Optional file path for context
            theme: Current theme

        Returns:
            Cached RenderResult if found, None otherwise
        """
        cache_key = self._generate_cache_key(content, file_path, theme)

        if cache_key not in self._cache:
            self._misses += 1
            return None

        entry = self._cache[cache_key]
        current_time = time.time()

        # Check if entry has expired
        if current_time - entry.timestamp > self._max_age:
            del self._cache[cache_key]
            self._invalidations += 1
            self._misses += 1
            return None

        # Update access statistics and move to end (LRU)
        entry.access_count += 1
        entry.last_access = current_time
        self._cache.move_to_end(cache_key)

        self._hits += 1

        # Mark result as cached
        cached_result = entry.result
        cached_result.cached = True

        return cached_result

    def put(
        self,
        content: str,
        result: RenderResult,
        file_path: str | None = None,
        theme: str = "dark",
    ) -> None:
        """
        Cache a render result.

        Args:
            content: Markdown content that was rendered
            result: Render result to cache
            file_path: Optional file path for context
            theme: Theme used for rendering
        """
        cache_key = self._generate_cache_key(content, file_path, theme)
        current_time = time.time()

        # Create cache entry
        entry = CacheEntry(
            result=result,
            timestamp=current_time,
            access_count=1,
            last_access=current_time,
            content_hash=self._hash_content(content),
            file_path_hash=self._hash_content(file_path) if file_path else None,
        )

        # Add to cache
        self._cache[cache_key] = entry

        # Enforce size limit
        self._evict_if_needed()

    def invalidate(
        self, content: str | None = None, file_path: str | None = None
    ) -> int:
        """
        Invalidate cache entries matching criteria.

        Args:
            content: If provided, invalidate entries with this content
            file_path: If provided, invalidate entries with this file path

        Returns:
            Number of entries invalidated
        """
        keys_to_remove = []

        content_hash = self._hash_content(content) if content else None
        file_hash = self._hash_content(file_path) if file_path else None

        for key, entry in self._cache.items():
            should_remove = False

            if content_hash and entry.content_hash == content_hash:
                should_remove = True
            elif file_hash and entry.file_path_hash == file_hash:
                should_remove = True
            elif content is None and file_path is None:
                # Invalidate all if no criteria specified
                should_remove = True

            if should_remove:
                keys_to_remove.append(key)

        # Remove invalidated entries
        for key in keys_to_remove:
            del self._cache[key]

        self._invalidations += len(keys_to_remove)
        return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cached entries."""
        count = len(self._cache)
        self._cache.clear()
        self._invalidations += count

    def cleanup_expired(self) -> int:
        """Remove expired cache entries."""
        current_time = time.time()
        keys_to_remove = []

        for key, entry in self._cache.items():
            if current_time - entry.timestamp > self._max_age:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]

        self._invalidations += len(keys_to_remove)
        return len(keys_to_remove)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_ratio = self._hits / total_requests if total_requests > 0 else 0.0

        # Calculate cache efficiency metrics
        if self._cache:
            total_access_count = sum(
                entry.access_count for entry in self._cache.values()
            )
            avg_access_count = total_access_count / len(self._cache)

            render_times = [
                entry.result.render_time_ms for entry in self._cache.values()
            ]
            avg_render_time = sum(render_times) / len(render_times)
        else:
            avg_access_count = 0.0
            avg_render_time = 0.0

        return {
            "cache_size": len(self._cache),
            "max_cache_size": self._max_size,
            "hit_ratio": hit_ratio,
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "invalidations": self._invalidations,
            "avg_access_count": avg_access_count,
            "avg_render_time_ms": avg_render_time,
            "cache_utilization": len(self._cache) / self._max_size,
        }

    def get_size_info(self) -> dict[str, int]:
        """Get cache size information."""
        return {
            "current_size": len(self._cache),
            "max_size": self._max_size,
            "available_slots": self._max_size - len(self._cache),
        }

    def resize(self, new_max_size: int) -> None:
        """
        Resize the cache to a new maximum size.

        Args:
            new_max_size: New maximum cache size
        """
        old_max_size = self._max_size
        self._max_size = new_max_size

        if new_max_size < old_max_size:
            # Need to evict entries if cache is now too large
            while len(self._cache) > new_max_size:
                self._evict_oldest()

    def get_most_accessed(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get the most frequently accessed cache entries.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of cache entry info dictionaries
        """
        entries = []

        for _key, entry in self._cache.items():
            entries.append(
                {
                    "content_hash": entry.content_hash[:8] + "...",
                    "access_count": entry.access_count,
                    "render_time_ms": entry.result.render_time_ms,
                    "age_seconds": time.time() - entry.timestamp,
                    "cached": entry.result.cached,
                }
            )

        # Sort by access count
        entries.sort(key=lambda x: x["access_count"], reverse=True)
        return entries[:limit]

    def _generate_cache_key(
        self, content: str, file_path: str | None = None, theme: str = "dark"
    ) -> str:
        """Generate a unique cache key for the given parameters."""
        key_components = [content, str(file_path), theme]
        key_string = "|".join(key_components)
        return hashlib.md5(key_string.encode("utf-8")).hexdigest()

    def _hash_content(self, content: str | None) -> str | None:
        """Generate a hash for content."""
        if content is None:
            return None
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def _evict_if_needed(self) -> None:
        """Evict entries if cache exceeds maximum size."""
        while len(self._cache) > self._max_size:
            self._evict_oldest()

    def _evict_oldest(self) -> None:
        """Evict the oldest (least recently used) entry."""
        if self._cache:
            self._cache.popitem(last=False)  # Remove first item (oldest)
            self._evictions += 1
