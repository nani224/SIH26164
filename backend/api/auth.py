"""Authentication & Authorization dependencies for ECDAT API.

Phase: Production Hardening (M1).
Enforces single shared bearer token via ECDAT_API_TOKEN.
"""

from __future__ import annotations

import hmac
import os
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Security scheme for OpenAPI schema generation
security_scheme = HTTPBearer(
    scheme_name="bearerAuth",
    description="Single shared bearer token configured via ECDAT_API_TOKEN.",
    auto_error=False,
)


def is_dev_mode() -> bool:
    """Check if the backend is running in development or test mode."""
    return (
        os.getenv("ECDAT_DEV_MODE") == "1"
        or os.getenv("TESTING") == "1"
        or "PYTEST_CURRENT_TEST" in os.environ
    )


def get_expected_token() -> str:
    """Retrieve the expected bearer token from environment.

    In production mode, raises RuntimeError if ECDAT_API_TOKEN is unset or empty.
    In dev/test mode, falls back to a documented dev token if ECDAT_API_TOKEN is unset.
    """
    token = os.getenv("ECDAT_API_TOKEN", "").strip()
    if not token:
        if is_dev_mode():
            return "ecdat-dev-insecure-token"
        raise RuntimeError(
            "ECDAT_API_TOKEN environment variable must be set in production. "
            "(To run in development mode, set ECDAT_DEV_MODE=1)"
        )
    return token


async def verify_bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(security_scheme)],
) -> str:
    """Verify that the incoming request has a valid Bearer token.

    Missing or invalid token returns 401 Unauthorized with no details leaked.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expected = get_expected_token()
    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(credentials.credentials.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials
