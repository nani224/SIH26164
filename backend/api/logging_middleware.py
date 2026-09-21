"""Structured request logging middleware for ECDAT API."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

log = structlog.get_logger("ecdat.api.http")


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        actor = request.headers.get("X-ECDAT-Actor") or "anonymous"
        path = request.url.path
        method = request.method

        start_time = time.perf_counter()
        log.info("request_started", method=method, path=path, actor=actor)

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            status_code = response.status_code

            if status_code >= 400:
                log.warning(
                    "request_failed",
                    method=method,
                    path=path,
                    actor=actor,
                    status_code=status_code,
                    duration_ms=duration_ms,
                )
            else:
                log.info(
                    "request_completed",
                    method=method,
                    path=path,
                    actor=actor,
                    status_code=status_code,
                    duration_ms=duration_ms,
                )
            return response
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            log.error(
                "request_error",
                method=method,
                path=path,
                actor=actor,
                error=str(exc),
                duration_ms=duration_ms,
            )
            raise
