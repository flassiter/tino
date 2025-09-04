"""
Tests for RenderCache component.

Tests caching behavior, LRU eviction, invalidation, and performance.
"""

import time

import pytest

from tino.components.renderer.cache import RenderCache
from tino.core.interfaces.renderer import Heading, RenderResult, ValidationIssue


class TestRenderCache:
    """Test suite for RenderCache."""

    @pytest.fixture
    def cache(self):
        """Create a RenderCache instance for testing."""
        return RenderCache(max_size=5, max_age_seconds=1.0)

    @pytest.fixture
    def sample_render_result(self):
        """Create a sample render result for testing."""
        return RenderResult(
            html="<h1>Test</h1>",
            outline=[Heading(level=1, text="Test", id="test", line_number=1)],
            issues=[],
            render_time_ms=10.0,
            cached=False,
        )

    def test_cache_initialization(self, cache):
        """Test cache initialization with correct parameters."""
        assert cache._max_size == 5
        assert cache._max_age == 1.0
        assert len(cache._cache) == 0

        stats = cache.get_stats()
        assert stats["cache_size"] == 0
        assert stats["max_cache_size"] == 5
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_basic_put_and_get(self, cache, sample_render_result):
        """Test basic cache put and get operations."""
        content = "# Test Heading"

        # Initially should not be cached
        result = cache.get(content)
        assert result is None

        stats = cache.get_stats()
        assert stats["misses"] == 1

        # Put in cache
        cache.put(content, sample_render_result)

        # Should now be cached
        cached_result = cache.get(content)
        assert cached_result is not None
        assert cached_result.html == sample_render_result.html
        assert cached_result.cached is True

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["cache_size"] == 1

    def test_cache_key_generation(self, cache, sample_render_result):
        """Test that cache keys are generated correctly for different contexts."""
        content = "# Test"

        # Same content, no file path
        cache.put(content, sample_render_result, theme="dark")
        result1 = cache.get(content, theme="dark")
        assert result1 is not None

        # Same content, different theme - should be cache miss
        result2 = cache.get(content, theme="light")
        assert result2 is None

        # Same content, same theme, different file path - should be cache miss
        result3 = cache.get(content, file_path="/test/file.md", theme="dark")
        assert result3 is None

    def test_lru_eviction(self, cache, sample_render_result):
        """Test LRU eviction when cache exceeds max size."""
        # Fill cache to max size
        for i in range(5):
            content = f"# Test {i}"
            cache.put(content, sample_render_result)

        assert cache.get_size_info()["current_size"] == 5

        # Access first item to make it most recently used
        first_result = cache.get("# Test 0")
        assert first_result is not None

        # Add one more item - should evict least recently used
        cache.put("# Test 5", sample_render_result)

        # Cache should still be at max size
        assert cache.get_size_info()["current_size"] == 5

        # First item should still be there (was accessed)
        assert cache.get("# Test 0") is not None

        # Second item should be evicted (least recently used)
        assert cache.get("# Test 1") is None

        stats = cache.get_stats()
        assert stats["evictions"] >= 1

    def test_age_based_expiration(self, sample_render_result):
        """Test that cache entries expire based on age."""
        # Create cache with very short expiration
        cache = RenderCache(max_size=10, max_age_seconds=0.1)

        content = "# Test"
        cache.put(content, sample_render_result)

        # Should be cached immediately
        result = cache.get(content)
        assert result is not None

        # Wait for expiration
        time.sleep(0.15)

        # Should be expired now
        result = cache.get(content)
        assert result is None

        stats = cache.get_stats()
        assert stats["invalidations"] >= 1

    def test_cache_invalidation(self, cache, sample_render_result):
        """Test manual cache invalidation."""
        # Add several items
        contents = ["# Test 1", "# Test 2", "# Test 3"]
        for content in contents:
            cache.put(content, sample_render_result)

        assert cache.get_size_info()["current_size"] == 3

        # Invalidate specific content
        invalidated = cache.invalidate(content="# Test 1")
        assert invalidated == 1
        assert cache.get("# Test 1") is None
        assert cache.get("# Test 2") is not None

        # Invalidate all
        invalidated = cache.invalidate()
        assert invalidated == 2  # Remaining items
        assert cache.get_size_info()["current_size"] == 0

    def test_cache_cleanup_expired(self, sample_render_result):
        """Test cleanup of expired entries."""
        cache = RenderCache(max_size=10, max_age_seconds=0.1)

        # Add items
        for i in range(5):
            cache.put(f"# Test {i}", sample_render_result)

        assert cache.get_size_info()["current_size"] == 5

        # Wait for expiration
        time.sleep(0.15)

        # Cleanup expired entries
        cleaned = cache.cleanup_expired()
        assert cleaned == 5
        assert cache.get_size_info()["current_size"] == 0

    def test_cache_resize(self, cache, sample_render_result):
        """Test resizing cache capacity."""
        # Fill cache
        for i in range(5):
            cache.put(f"# Test {i}", sample_render_result)

        assert cache.get_size_info()["current_size"] == 5

        # Resize to smaller capacity
        cache.resize(3)

        # Should evict oldest entries
        size_info = cache.get_size_info()
        assert size_info["max_size"] == 3
        assert size_info["current_size"] == 3

        # Resize to larger capacity
        cache.resize(10)
        assert cache.get_size_info()["max_size"] == 10
        assert cache.get_size_info()["current_size"] == 3  # Existing items preserved

    def test_access_count_tracking(self, cache, sample_render_result):
        """Test that access counts are tracked correctly."""
        content = "# Test"
        cache.put(content, sample_render_result)

        # Access multiple times
        for _ in range(5):
            cache.get(content)

        # Check access statistics
        most_accessed = cache.get_most_accessed(limit=1)
        assert len(most_accessed) == 1
        assert most_accessed[0]["access_count"] == 6  # 1 put + 5 gets

    def test_cache_statistics(self, cache, sample_render_result):
        """Test comprehensive cache statistics."""
        # Perform various operations
        cache.put("# Test 1", sample_render_result)
        cache.put("# Test 2", sample_render_result)

        cache.get("# Test 1")  # Hit
        cache.get("# Test 1")  # Hit
        cache.get("# Test 3")  # Miss
        cache.get("# Missing")  # Miss

        stats = cache.get_stats()

        assert stats["cache_size"] == 2
        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["hit_ratio"] == 0.5  # 2 hits out of 4 total requests
        assert stats["cache_utilization"] == 0.4  # 2 out of 5 max size

    def test_most_accessed_entries(self, cache, sample_render_result):
        """Test retrieval of most accessed cache entries."""
        # Add entries with different access patterns
        contents = ["# Test A", "# Test B", "# Test C"]

        for content in contents:
            cache.put(content, sample_render_result)

        # Access with different frequencies
        for _ in range(5):
            cache.get("# Test A")  # 5 additional accesses

        for _ in range(2):
            cache.get("# Test B")  # 2 additional accesses

        # # Test C accessed only once (during put)

        most_accessed = cache.get_most_accessed(limit=3)

        assert len(most_accessed) == 3

        # Should be sorted by access count (descending)
        assert most_accessed[0]["access_count"] == 6  # Test A: 1 put + 5 gets
        assert most_accessed[1]["access_count"] == 3  # Test B: 1 put + 2 gets
        assert most_accessed[2]["access_count"] == 1  # Test C: 1 put only

    def test_cache_clear(self, cache, sample_render_result):
        """Test clearing all cache entries."""
        # Fill cache
        for i in range(3):
            cache.put(f"# Test {i}", sample_render_result)

        assert cache.get_size_info()["current_size"] == 3

        # Clear cache
        cache.clear()

        assert cache.get_size_info()["current_size"] == 0

        # All entries should be gone
        for i in range(3):
            assert cache.get(f"# Test {i}") is None

        stats = cache.get_stats()
        assert stats["invalidations"] >= 3

    def test_concurrent_access(self, cache, sample_render_result):
        """Test cache behavior under concurrent access."""
        import threading

        content = "# Concurrent Test"
        cache.put(content, sample_render_result)

        results = []
        errors = []

        def access_cache():
            try:
                for _ in range(10):
                    result = cache.get(content)
                    results.append(result is not None)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=access_cache)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        assert all(results), "Some cache accesses failed"
        assert len(results) == 50  # 5 threads * 10 accesses each

    def test_memory_efficiency(self, sample_render_result):
        """Test cache memory usage with large number of entries."""
        # Create cache with reasonable size limit
        cache = RenderCache(max_size=1000)

        # Add many entries
        for i in range(500):
            content = f"# Test Content {i}\n\nSome content here."
            cache.put(content, sample_render_result)

        # Cache should not exceed max size
        assert cache.get_size_info()["current_size"] == 500

        # Add more to trigger eviction
        for i in range(500, 1100):
            content = f"# Test Content {i}"
            cache.put(content, sample_render_result)

        # Should stay at max size
        assert cache.get_size_info()["current_size"] == 1000

        stats = cache.get_stats()
        assert stats["evictions"] > 0

    def test_cache_with_different_result_types(self, cache):
        """Test caching with different types of render results."""
        # Result with outline
        result_with_outline = RenderResult(
            html="<h1>Title</h1><h2>Section</h2>",
            outline=[
                Heading(level=1, text="Title", id="title", line_number=1),
                Heading(level=2, text="Section", id="section", line_number=3),
            ],
            issues=[],
            render_time_ms=15.0,
            cached=False,
        )

        # Result with issues
        result_with_issues = RenderResult(
            html="<h1>Title</h1>",
            outline=[],
            issues=[
                ValidationIssue(
                    type="broken_link",
                    message="Link not found",
                    line_number=5,
                    column=10,
                    severity="error",
                )
            ],
            render_time_ms=20.0,
            cached=False,
        )

        # Cache both
        cache.put("# Content 1", result_with_outline)
        cache.put("# Content 2", result_with_issues)

        # Retrieve and verify
        cached1 = cache.get("# Content 1")
        assert cached1 is not None
        assert len(cached1.outline) == 2
        assert len(cached1.issues) == 0

        cached2 = cache.get("# Content 2")
        assert cached2 is not None
        assert len(cached2.outline) == 0
        assert len(cached2.issues) == 1
        assert cached2.issues[0].type == "broken_link"

    def test_cache_performance(self, sample_render_result):
        """Test cache operation performance."""
        import time

        cache = RenderCache(max_size=1000)

        # Measure put performance
        start_time = time.perf_counter()
        for i in range(1000):
            cache.put(f"# Content {i}", sample_render_result)
        put_time = time.perf_counter() - start_time

        # Measure get performance
        start_time = time.perf_counter()
        for i in range(1000):
            cache.get(f"# Content {i}")
        get_time = time.perf_counter() - start_time

        # Should be reasonably fast
        assert put_time < 1.0, f"Put operations too slow: {put_time:.3f}s"
        assert get_time < 0.5, f"Get operations too slow: {get_time:.3f}s"

        # Cache operations should be much faster than typical rendering
        avg_put_time = put_time / 1000 * 1000  # Convert to ms
        avg_get_time = get_time / 1000 * 1000  # Convert to ms

        assert avg_put_time < 1.0, f"Average put time too slow: {avg_put_time:.3f}ms"
        assert avg_get_time < 0.1, f"Average get time too slow: {avg_get_time:.3f}ms"
