"""Functional tests for password_cache.py - TTL cache operations."""

from unittest.mock import patch

from stellars_hub.password_cache import cache_password, get_cached_password, clear_cached_password


class TestPasswordCache:
    def test_cache_then_get(self, clean_password_cache):
        """Cached password can be retrieved."""
        cache_password("alice", "secret123")
        assert get_cached_password("alice") == "secret123"

    def test_get_nonexistent_returns_none(self, clean_password_cache):
        """Getting uncached username returns None."""
        assert get_cached_password("nobody") is None

    def test_expired_returns_none(self, clean_password_cache):
        """Expired entry returns None."""
        cache_password("bob", "pass456")

        with patch("stellars_hub.password_cache.time") as mock_time:
            # First call is cache_password's time.time(), already done above
            # Simulate 301 seconds later (> 300s TTL)
            mock_time.time.return_value = 9999999999.0

            from stellars_hub.password_cache import _password_cache
            # Overwrite timestamp to a known value
            _password_cache["bob"] = ("pass456", 1000.0)
            mock_time.time.return_value = 1301.0  # 301s after cache time

            assert get_cached_password("bob") is None

    def test_clear_removes_entry(self, clean_password_cache):
        """Clearing removes the entry."""
        cache_password("carol", "pass789")
        clear_cached_password("carol")
        assert get_cached_password("carol") is None

    def test_overwrite_replaces_value(self, clean_password_cache):
        """Caching same username overwrites previous value."""
        cache_password("dave", "old_pass")
        cache_password("dave", "new_pass")
        assert get_cached_password("dave") == "new_pass"
