"""Tests for Phase 10 Sliding-Window Rate Limiting Middleware."""

from __future__ import annotations

from typing import TYPE_CHECKING

from api.rate_limiter import SlidingWindowRateLimiter

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_sliding_window_rate_limiter_unit() -> None:
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=2.0)
    key = "client_test_unit"

    # First 3 requests allowed
    allowed, rem, _ = limiter.is_allowed(key)
    assert allowed is True
    assert rem == 2

    allowed, rem, _ = limiter.is_allowed(key)
    assert allowed is True
    assert rem == 1

    allowed, rem, _ = limiter.is_allowed(key)
    assert allowed is True
    assert rem == 0

    # 4th request blocked
    allowed, rem, retry_after = limiter.is_allowed(key)
    assert allowed is False
    assert rem == 0
    assert retry_after >= 1


def test_rate_limiting_middleware_throttling(client: TestClient) -> None:
    # Use a unique client ID header to isolate this test
    client_id = "test_rate_limited_client_999"
    headers = {"X-Test-Client-Id": client_id}

    # Make 120 calls to a mutating route (or test until throttled)
    # The default max is 120, so after 120, the 121st call must return 429
    # We can hit a lightweight mutating endpoint like patch triage
    # or create a test client with lower limits, but let's test directly on client
    # Or even better, test the limiter attached to middleware
    for _ in range(120):
        resp = client.post("/api/v1/scans", json={"path": "engine"}, headers=headers)
        if resp.status_code == 429:
            break
        assert resp.status_code in (201, 400)
        assert "x-ratelimit-limit" in resp.headers

    # Next request must be throttled with 429
    throttled = client.post("/api/v1/scans", json={"path": "engine"}, headers=headers)
    assert throttled.status_code == 429
    assert "retry-after" in throttled.headers
    assert throttled.headers["x-ratelimit-remaining"] == "0"
    data = throttled.json()
    assert data["error"] == "TooManyRequests"
