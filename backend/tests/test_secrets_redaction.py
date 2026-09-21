"""M5 Verification: Secrets audit & redaction tests.

Proves:
1. Webhook URLs configured via environment never appear in full in any log line.
2. Sensitive path segments/tokens in webhook URLs are redacted in logs.
3. No API response echoes the auth token or webhook URL.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from probes.webhook import redact_url, send_alert_webhook


def test_redact_url_masks_webhook_secrets() -> None:
    """redact_url must mask secret tokens and queries from webhook URLs."""
    raw_slack = "https://hooks.slack.com/services/T12345678/B12345678/SECRET_SLACK_TOKEN_9999"
    redacted_slack = redact_url(raw_slack)
    assert "SECRET_SLACK_TOKEN_9999" not in redacted_slack
    assert "https://hooks.slack.com/services/***" in redacted_slack

    raw_discord = "https://discord.com/api/webhooks/1234567890/SECRET_DISCORD_TOKEN?token=secret123"
    redacted_discord = redact_url(raw_discord)
    assert "SECRET_DISCORD_TOKEN" not in redacted_discord
    assert "secret123" not in redacted_discord
    assert "?***" in redacted_discord


def test_webhook_dispatch_logs_redact_url_on_failure(caplog: pytest.LogCaptureFixture) -> None:
    """When a webhook dispatch fails, the full webhook URL must never appear in the logs."""
    secret_token = "SUPER_SECRET_WEBHOOK_CREDENTIAL_987654321"
    webhook_url = f"https://hooks.example.org/webhook/v1/{secret_token}?auth={secret_token}"

    with caplog.at_level(logging.WARNING), patch("httpx.Client.post", side_effect=Exception("Connection refused")):
        success = send_alert_webhook(webhook_url, {"text": "Test alert"})
        assert success is False

    # Check that the secret token is completely absent from all captured log lines
    assert secret_token not in caplog.text
    assert webhook_url not in caplog.text
    # Verify redacted URL was logged
    assert "hooks.example.org" in caplog.text
    assert "***" in caplog.text


def test_api_responses_never_echo_auth_token_or_webhook(monkeypatch: pytest.MonkeyPatch) -> None:
    """API responses must not echo back the auth token or webhook credentials."""
    secret_token = "TOP_SECRET_AUTH_TOKEN_7777777"
    monkeypatch.setenv("ECDAT_API_TOKEN", secret_token)
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://hooks.internal.net/secret-hook-888")

    client = TestClient(app, headers={"Authorization": f"Bearer {secret_token}", "X-ECDAT-Actor": "test-operator"})

    endpoints = [
        "/api/v1/health",
        "/api/v1/alerts",
        "/api/v1/catalog/pqc",
        "/api/v1/targets",
        "/api/v1/policies",
    ]

    for ep in endpoints:
        resp = client.get(ep, headers={"Authorization": f"Bearer {secret_token}", "X-ECDAT-Actor": "test-operator"})
        assert secret_token not in resp.text, f"Secret token leaked in response from {ep}"
        assert "secret-hook-888" not in resp.text, f"Webhook secret leaked in response from {ep}"
