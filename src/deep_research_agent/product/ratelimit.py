"""In-process token bucket rate limiting, keyed by (tenant_id, route)."""

from __future__ import annotations

import math
import threading
import time
from typing import Protocol


class RateLimiter(Protocol):
    """Rate limiting boundary; a check returns the retry delay in seconds or None."""

    def check(self, key: str, *, now: float | None = None) -> float | None: ...


class TokenBucketRateLimiter:
    """进程内令牌桶，按 key（tenant_id:route）维度独立计数，线程安全。

    无外部依赖；超出容量时返回建议的 Retry-After 秒数。
    """

    def __init__(
        self,
        *,
        capacity: int = 20,
        refill_rate: float = 5.0,
        max_keys: int = 10_000,
    ) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        if refill_rate <= 0:
            raise ValueError("refill_rate must be positive")
        if max_keys < 1:
            raise ValueError("max_keys must be at least 1")
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self.max_keys = max_keys
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, *, now: float | None = None) -> float | None:
        """消耗一个 token；允许返回 None，拒绝返回 Retry-After 秒数。"""
        if now is None:
            now = time.monotonic()
        with self._lock:
            if len(self._buckets) >= self.max_keys:
                self._buckets.clear()
            tokens, last_refill = self._buckets.get(key, (self.capacity, now))
            tokens = min(self.capacity, tokens + max(now - last_refill, 0.0) * self.refill_rate)
            if tokens >= 1.0:
                self._buckets[key] = (tokens - 1.0, now)
                return None
            self._buckets[key] = (tokens, now)
            wait = (1.0 - tokens) / self.refill_rate
            return max(math.ceil(wait), 1)


class NullRateLimiter:
    """零限流实现：测试/本地模式注入，从不拒绝请求。"""

    def check(self, key: str, *, now: float | None = None) -> float | None:
        del key, now
        return None


__all__ = ["NullRateLimiter", "RateLimiter", "TokenBucketRateLimiter"]
