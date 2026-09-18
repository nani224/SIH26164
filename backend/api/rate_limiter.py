"""Sliding-window rate limiter middleware for ECDAT (Phase 10).

Provides deterministic in-memory sliding-window throttling for mutating and resource-intensive
endpoints (POST, PATCH, PUT, DELETE) to protect against DoS or resource exhaustion in air-gapped environments.
"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from typing import TYPE_CHECKING

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

if TYPE_CHECKING:
    pass


class SlidingWindowRateLimiter:
    """Thread-safe sliding window request counter."""

    def __init__(self, max_requests: int = 120, window_seconds: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def is_allowed(self, client_key: str, cost: int = 1) -> tuple[bool, int, int]:
        """Check if request is allowed.

        Returns: (allowed, remaining, retry_after)
        """
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            q = self._requests[client_key]
            # Prune timestamps older than window
            while q and q[0] < cutoff:
                q.popleft()

            current_count = len(q)
            if current_count + cost > self.max_requests:
                oldest = q[0] if q else now
                retry_after = max(1, int(oldest + self.window_seconds - now) + 1)
                return False, 0, retry_after

            for _ in range(cost):
                q.append(now)

            remaining = max(0, self.max_requests - len(q))
            return True, remaining, 0

    def reset(self) -> None:
        """Clear all client rate limiting buckets."""
        with self._lock:
            self._requests.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Starlette middleware applying sliding-window rate limiting on mutating API requests."""

    def __init__(
        self,
        app: object,
        *,
        max_requests: int | None = None,
        window_seconds: float = 60.0,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        env_limit = int(os.environ.get("ECDAT_RATE_LIMIT_MUTATING", "120"))
        limit = max_requests if max_requests is not None else env_limit
        self.limiter = SlidingWindowRateLimiter(max_requests=limit, window_seconds=window_seconds)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Check if disabled via environment
        if os.environ.get("ECDAT_RATE_LIMIT_DISABLED") == "1":
            return await call_next(request)

        # Only rate limit mutating methods on API paths
        if request.method in ("POST", "PATCH", "PUT", "DELETE") and request.url.path.startswith("/api/v1/"):
            client_ip = (
                request.headers.get("X-Test-Client-Id")
                or (request.client.host if request.client else "unknown_client")
            )
            key = f"{client_ip}:{request.method}:{request.url.path}"

            allowed, remaining, retry_after = self.limiter.is_allowed(key)
            if not allowed:
                headers = {
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.limiter.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                }
                return JSONResponse(
                    status_code=429,
                    content={"error": "TooManyRequests", "message": "Rate limit exceeded. Please retry later."},
                    headers=headers,
                )

            response: Response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(self.limiter.max_requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response

        return await call_next(request)
