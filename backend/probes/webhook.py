"""Webhook dispatch adapter for alerts.

Isolated in probes/ to preserve strict air-gap boundaries in api/ and engine/.
Redacts webhook URLs in logs to prevent secret leakage (M5).
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


def redact_url(url: str) -> str:
    """Redact sensitive path, token, or query parameters from a webhook URL."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc
        if "@" in netloc:
            _, host = netloc.split("@", 1)
            netloc = f"***:***@{host}"
        path = parsed.path
        if path and len(path) > 1:
            parts = path.strip("/").split("/")
            if len(parts) > 1:
                path = "/" + "/".join([parts[0]] + ["***" for _ in parts[1:]])
            else:
                path = "/***"
        query = "?***" if parsed.query else ""
        return f"{parsed.scheme}://{netloc}{path}{query}"
    except Exception:
        return f"{url[:15]}...***" if len(url) > 15 else "***"


def send_alert_webhook(url: str, payload: dict[str, Any], timeout: float = 3.0) -> bool:
    """Send an alert payload to the configured webhook URL, redacting secrets in logs."""
    safe_url = redact_url(url)
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload)
            if resp.status_code >= 400:
                logger.warning("Webhook dispatch to %s returned %d", safe_url, resp.status_code)
                return False
            return True
    except Exception as exc:
        logger.warning("Failed to dispatch alert to webhook %s: %s", safe_url, exc)
        return False
