"""Request size limit middleware for ECDAT API.

Phase: Production Hardening (M4).
Enforces HTTP-layer size limits:
- 1 MB cap on ordinary JSON endpoints (HTTP 413 Payload Too Large).
- Upload endpoints (/api/v1/scans/upload, /api/v1/criticality/import) bypass the 1MB cap
  and use their documented limits.
"""

from __future__ import annotations

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_JSON_REQUEST_BYTES = 1 * 1024 * 1024  # 1 MB cap for JSON endpoints
UPLOAD_PATHS = {
    "/api/v1/scans/upload",
    "/api/v1/criticality/import",
}


class RequestEntityTooLargeException(Exception):
    """Raised when streaming request body exceeds configured limit."""


class RequestSizeLimitMiddleware:
    """Middleware rejecting requests exceeding payload size limits with HTTP 413."""

    def __init__(self, app: ASGIApp, max_json_bytes: int = MAX_JSON_REQUEST_BYTES) -> None:
        self.app = app
        self.max_json_bytes = max_json_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        # Allow upload endpoints to handle their own large streaming limits
        if path in UPLOAD_PATHS:
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        content_length_header = headers.get("content-length")
        if content_length_header:
            try:
                content_length = int(content_length_header)
                if content_length > self.max_json_bytes:
                    response = JSONResponse(
                        status_code=413,
                        content={
                            "error": "PayloadTooLarge",
                            "message": f"Request body exceeds maximum allowed size of {self.max_json_bytes} bytes",
                        },
                    )
                    await response(scope, receive, send)
                    return
            except ValueError:
                pass

        bytes_received = 0

        async def limited_receive() -> Message:
            nonlocal bytes_received
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                bytes_received += len(body)
                if bytes_received > self.max_json_bytes:
                    raise RequestEntityTooLargeException()
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestEntityTooLargeException:
            response = JSONResponse(
                status_code=413,
                content={
                    "error": "PayloadTooLarge",
                    "message": f"Request body exceeds maximum allowed size of {self.max_json_bytes} bytes",
                },
            )
            await response(scope, receive, send)
