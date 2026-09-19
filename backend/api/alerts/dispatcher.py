"""Alert notification dispatcher.

Persists alerts to the database and dispatches notifications to configured
webhooks (Slack/Discord format) when `ALERT_WEBHOOK_URL` is set in the
environment.
"""

from __future__ import annotations

import logging
import os

from api import store
from api.models import Alert
from probes.webhook import send_alert_webhook

logger = logging.getLogger(__name__)


def dispatch_alert(alert: Alert) -> Alert:
    """Save alert to the persistent database and forward to webhook if configured.

    Args:
        alert: The Alert instance to dispatch.

    Returns:
        The persisted Alert instance.
    """
    # 1. Database persistence
    saved = store.create_alert(alert)

    # 2. Webhook dispatch if configured
    webhook_url = os.environ.get("ALERT_WEBHOOK_URL", "").strip()
    if webhook_url:
        payload = {
            "text": f"🚨 *[ECDAT {alert.severity.value.upper()} ALERT]* {alert.message}",
            "content": f"🚨 **[ECDAT {alert.severity.value.upper()} ALERT]** {alert.message}",
            "alert": {
                "id": alert.id,
                "type": alert.type.value,
                "targetId": alert.targetId,
                "findingId": alert.findingId,
                "severity": alert.severity.value,
                "message": alert.message,
                "createdAt": alert.createdAt.isoformat(),
            },
        }
        send_alert_webhook(webhook_url, payload)

    return saved
