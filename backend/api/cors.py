"""CORS configuration for ECDAT API.

Phase: Production Hardening (M2).
Replaces insecure wildcard allow_origins=["*"] + allow_credentials=True with explicit origins.
"""

from __future__ import annotations

import os

DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def get_cors_origins() -> list[str]:
    """Retrieve allowed CORS origins from environment or default to local frontend URLs.

    Configurable via ECDAT_CORS_ORIGINS (comma-separated list of origins).
    """
    raw = os.getenv("ECDAT_CORS_ORIGINS", "").strip()
    if not raw:
        return list(DEFAULT_CORS_ORIGINS)
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or list(DEFAULT_CORS_ORIGINS)
