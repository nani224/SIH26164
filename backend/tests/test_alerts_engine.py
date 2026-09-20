"""Tests for Alerts Engine: trigger rules, webhook dispatching, and acknowledgment."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from api.alerts import rules
from api.alerts.dispatcher import dispatch_alert
from api.main import app
from api.models import (
    Alert,
    AlertType,
    CryptoFunction,
    Drift,
    DriftSummary,
    Finding,
    FindingKind,
    FindingSource,
    Location,
    ProbeProtocol,
    ProbeResult,
    Risk,
    RiskBand,
    Surface,
    Triage,
    TriageStatus,
)


def _make_dummy_finding(name: str, score: float, band: RiskBand) -> Finding:
    return Finding(
        id=f"fnd_{uuid4().hex[:8]}",
        kind=FindingKind.ALGORITHM,
        surface=Surface.SOURCE,
        family=None,
        displayName=name,
        function=CryptoFunction.ENCRYPT,
        location=Location(path="src/crypto.py", line=12, offset=0),
        symbol="RSA_2048",
        snippet="rsa.generate_private_key()",
        source=FindingSource.AST,
        confidence=1.0,
        risk=Risk(
            score=score,
            band=band,
            V=1.0,
            F=1.0,
            U=1.0,
            E=1.0,
            K=1.0,
            X=10.0,
            Y=5.0,
            Z=10.0,
            moscaMargin=-5.0,
            reason="Test risk",
            classicallyBroken=False,
            hndl=False,
            needsReview=False,
        ),
        triage=Triage(status=TriageStatus.OPEN),
    )


def test_rule_new_critical_finding() -> None:
    target_id = f"tgt_{uuid4().hex[:8]}"
    crit_finding = _make_dummy_finding("RSA-1024 Weak Key", score=85.0, band=RiskBand.CRITICAL)
    low_finding = _make_dummy_finding("AES-256", score=10.0, band=RiskBand.LOW)

    alerts = rules.check_new_critical_findings(target_id, [crit_finding, low_finding])
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.type == AlertType.NEW_CRITICAL
    assert alert.severity == RiskBand.CRITICAL
    assert alert.targetId == target_id
    assert alert.findingId == crit_finding.id
    assert "RSA-1024" in alert.message


def test_rule_cert_expiring() -> None:
    target_id = f"tgt_{uuid4().hex[:8]}"
    # Expiring in 10 days (< 30 days)
    expires_soon = (datetime.now(UTC) + timedelta(days=10)).isoformat()
    alert = rules.check_cert_expiring(target_id, expires_soon)
    assert alert is not None
    assert alert.type == AlertType.CERT_EXPIRING
    assert alert.severity == RiskBand.HIGH
    assert "expiring in 9" in alert.message or "expiring in 10" in alert.message

    # Expiring in 90 days (> 30 days) -> No alert
    expires_later = (datetime.now(UTC) + timedelta(days=90)).isoformat()
    alert_none = rules.check_cert_expiring(target_id, expires_later)
    assert alert_none is None


def test_rule_drift_alert() -> None:
    target_id = f"tgt_{uuid4().hex[:8]}"
    crit_finding = _make_dummy_finding("RSA-1024", score=80.0, band=RiskBand.CRITICAL)

    drift = Drift(
        targetId=target_id,
        fromSnapshotId="snp_base",
        toSnapshotId="snp_head",
        added=[crit_finding],
        resolved=[],
        changed=[],
        summary=DriftSummary(
            addedCount=1,
            resolvedCount=0,
            changedCount=0,
            netRiskDelta=45.0,
        ),
    )

    alerts = rules.check_drift_alerts(target_id, drift)
    assert len(alerts) >= 1
    assert any(a.type == AlertType.DRIFT for a in alerts)


def test_rule_probe_downgrade() -> None:
    target_id = f"tgt_{uuid4().hex[:8]}"

    # Insecure RC4 cipher negotiated
    insecure_probe = ProbeResult(
        id=f"prb_{uuid4().hex[:8]}",
        targetId=target_id,
        host="127.0.0.1",
        port=8443,
        protocol=ProbeProtocol.TLS,
        negotiated={"protocol": "TLSv1.0", "cipher": "RC4-MD5"},
        supported=[],
        probedAt=datetime.now(UTC),
    )
    alert = rules.check_probe_downgrade(target_id, insecure_probe)
    assert alert is not None
    assert alert.type == AlertType.PROBE_DOWNGRADE
    assert alert.severity == RiskBand.CRITICAL
    assert "insecure" in alert.message

    # Modern secure cipher -> No alert
    secure_probe = ProbeResult(
        id=f"prb_{uuid4().hex[:8]}",
        targetId=target_id,
        host="127.0.0.1",
        port=8443,
        protocol=ProbeProtocol.TLS,
        negotiated={"protocol": "TLSv1.3", "cipher": "TLS_AES_256_GCM_SHA384"},
        supported=[],
        probedAt=datetime.now(UTC),
    )
    assert rules.check_probe_downgrade(target_id, secure_probe) is None


def test_webhook_dispatch_payload(monkeypatch: Any) -> None:
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://mock.webhook.internal/alerts")

    alert = Alert(
        id=f"alt_{uuid4().hex[:8]}",
        type=AlertType.NEW_CRITICAL,
        targetId="tgt_webhook",
        severity=RiskBand.CRITICAL,
        message="Critical cipher found",
        createdAt=datetime.now(UTC),
        acknowledged=False,
    )

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_client.__enter__.return_value.post.return_value = mock_resp

    with patch("probes.webhook.httpx.Client", return_value=mock_client):
        saved = dispatch_alert(alert)
        assert saved.id == alert.id

        post_calls = mock_client.__enter__.return_value.post.call_args_list
        assert len(post_calls) == 1
        args, kwargs = post_calls[0]
        assert args[0] == "https://mock.webhook.internal/alerts"
        payload = kwargs["json"]
        assert "ECDAT CRITICAL ALERT" in payload["text"]
        assert payload["alert"]["id"] == alert.id


def test_alerts_api_acknowledgment_idempotency() -> None:
    client = TestClient(app)

    # 1. Create test alert via rule
    crit = _make_dummy_finding("Vulnerable 3DES", score=75.0, band=RiskBand.CRITICAL)
    alerts = rules.check_new_critical_findings("tgt_ack_test", [crit])
    assert len(alerts) >= 1
    alert_id = alerts[0].id

    # 2. List unacknowledged alerts
    res = client.get("/api/v1/alerts?acknowledged=false")
    assert res.status_code == 200
    unacked = [a["id"] for a in res.json()]
    assert alert_id in unacked

    # 3. Acknowledge alert
    ack_res = client.patch(f"/api/v1/alerts/{alert_id}/acknowledge")
    assert ack_res.status_code == 200
    ack_body = ack_res.json()
    assert ack_body["id"] == alert_id
    assert ack_body["acknowledged"] is True

    # 4. Idempotent re-acknowledgment
    ack_res2 = client.patch(f"/api/v1/alerts/{alert_id}/acknowledge")
    assert ack_res2.status_code == 200
    assert ack_res2.json()["acknowledged"] is True

    # 5. Check filter: now appears in acknowledged=true and not in acknowledged=false
    res_unack = client.get("/api/v1/alerts?acknowledged=false")
    assert alert_id not in [a["id"] for a in res_unack.json()]

    res_ack = client.get("/api/v1/alerts?acknowledged=true")
    assert alert_id in [a["id"] for a in res_ack.json()]

    # 6. Non-existent alert returns 404
    err_res = client.patch("/api/v1/alerts/nonexistent_alert_id/acknowledge")
    assert err_res.status_code == 404
