"""Webhook dispatch adapter for alerts.

Isolated in probes/ to preserve strict air-gap boundaries in api/ and engine/.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def send_alert_webhook(url: str, payload: dict[str, Any], timeout: float = 3.0) -> bool:
    """Send an alert payload to the configured webhook URL."""
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload)
            if resp.status_code >= 400:
                logger.warning("Webhook dispatch returned %d: %s", resp.status_code, resp.text)
                return False
            return True
    except Exception as exc:
        logger.warning("Failed to dispatch alert to webhook %s: %s", url, exc)
        return False
