"""
Rate Limiting Module
Provides rate limiting for authentication endpoints using Redis or in-memory fallback.
"""

import time
import logging
from collections import defaultdict
from typing import Optional
from threading import Lock

from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter with sliding window.
    
    Note: For multi-instance production deployments, replace with Redis-based implementation.
    """

    def __init__(self):
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def _get_bucket_key(self, identifier: str, endpoint: str) -> str:
        return f"{endpoint}:{identifier}"

    def is_allowed(self, identifier: str, endpoint: str, max_attempts: int, window_minutes: int) -> tuple[bool, int]:
        """
        Check if request is allowed under rate limit.
        
        Returns:
            tuple: (allowed: bool, remaining_attempts: int)
        """
        if not settings.RATE_LIMIT_ENABLED or settings.TESTING:
            return True, max_attempts

        key = self._get_bucket_key(identifier, endpoint)
        now = time.time()
        window_seconds = window_minutes * 60

        with self._lock:
            # Remove expired entries
            self._buckets[key] = [ts for ts in self._buckets[key] if now - ts < window_seconds]
            
            current_count = len(self._buckets[key])
            remaining = max(0, max_attempts - current_count)
            
            if current_count >= max_attempts:
                return False, 0
            
            # Add current request
            self._buckets[key].append(now)
            return True, remaining - 1

    def get_remaining(self, identifier: str, endpoint: str, max_attempts: int, window_minutes: int) -> int:
        """Get remaining attempts without consuming one."""
        if not settings.RATE_LIMIT_ENABLED or settings.TESTING:
            return max_attempts

        key = self._get_bucket_key(identifier, endpoint)
        now = time.time()
        window_seconds = window_minutes * 60

        with self._lock:
            self._buckets[key] = [ts for ts in self._buckets[key] if now - ts < window_seconds]
            current_count = len(self._buckets[key])
            return max(0, max_attempts - current_count)

    def reset(self, identifier: str, endpoint: str) -> None:
        """Reset rate limit for an identifier and endpoint."""
        key = self._get_bucket_key(identifier, endpoint)
        with self._lock:
            if key in self._buckets:
                del self._buckets[key]


# Global rate limiter instance
rate_limiter = RateLimiter()


def check_rate_limit(
    identifier: str,
    endpoint: str,
    max_attempts: int,
    window_minutes: int,
) -> tuple[bool, int]:
    """Convenience function to check rate limit."""
    return rate_limiter.is_allowed(identifier, endpoint, max_attempts, window_minutes)