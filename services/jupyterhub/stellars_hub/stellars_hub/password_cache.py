"""Temporary password cache for admin-created users."""

import time

_password_cache = {}
_CACHE_EXPIRY_SECONDS = 300  # 5 minutes


def cache_password(username, password):
    """Store a password in the cache with timestamp."""
    _password_cache[username] = (password, time.time())


def get_cached_password(username):
    """Get a password from cache if not expired."""
    if username in _password_cache:
        password, timestamp = _password_cache[username]
        if time.time() - timestamp < _CACHE_EXPIRY_SECONDS:
            return password
        else:
            del _password_cache[username]
    return None


def clear_cached_password(username):
    """Remove a password from cache."""
    _password_cache.pop(username, None)
