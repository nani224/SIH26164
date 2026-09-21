"""Alert trigger rules for ECDAT continuous operation.

Rules:
1. New critical finding detected (score >= 60.0 or band == critical).
2. Certificate expiring in < 30 days.
3. Drift alert on added critical findings or significant net risk increase.
4. Probe detects downgrade or insecure primitive negotiated.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from uuid import uuid4

from api.alerts.dispatcher import dispatch_alert
from api.models import (
    Alert,
    AlertType,
    Drift,
    Finding,
    ProbeResult,
    RiskBand,
    Scan,
    ScanSnapshot,
    Target,
)


def evaluate_scan_alerts(
    target: Target,
    scan: Scan,
    snapshot: ScanSnapshot,
    findings: list[Finding],
) -> list[Alert]:
    """Evaluate scan alerts: new critical findings and expiring certificates."""
    alerts: list[Alert] = []
    alerts.extend(check_new_critical_findings(target.id, findings))
    return alerts

INSECURE_CIPHER_PATTERNS = re.compile(
    r"(rc4|3des|des|md5|null|export|anon|cbc|group1|ssh-rsa|arcfour)",
    re.IGNORECASE,
)
INSECURE_PROTOCOLS = {"sslv2", "sslv3", "tlsv1.0", "tlsv1.1", "tls 1.0", "tls 1.1"}


def check_new_critical_findings(target_id: str, findings: list[Finding]) -> list[Alert]:
    """Trigger alerts for new critical findings in a scan."""
    alerts: list[Alert] = []
    for f in findings:
        score = f.risk.score if f.risk else 0.0
        band = f.risk.band if f.risk else None
        if band == RiskBand.CRITICAL or score >= 60.0:
            alert = Alert(
                id=f"alt_{uuid4().hex[:12]}",
                type=AlertType.NEW_CRITICAL,
                targetId=target_id,
                findingId=f.id,
                severity=RiskBand.CRITICAL,
                message=(
                    f"Critical cryptographic finding detected: {f.displayName} "
                    f"(score: {score:.1f}) in {f.location.path}"
                ),
                createdAt=datetime.now(UTC),
                acknowledged=False,
            )
            dispatch_alert(alert)
            alerts.append(alert)
    return alerts


def check_cert_expiring(
    target_id: str,
    not_after: str | datetime | None,
    finding_id: str | None = None,
) -> Alert | None:
    """Trigger alert if a certificate expires in less than 30 days."""
    if not not_after:
        return None

    expiry_dt: datetime | None = None
    if isinstance(not_after, datetime):
        expiry_dt = not_after if not_after.tzinfo is not None else not_after.replace(tzinfo=UTC)
    elif isinstance(not_after, str):
        try:
            expiry_dt = parsedate_to_datetime(not_after)
            if expiry_dt.tzinfo is None:
                expiry_dt = expiry_dt.replace(tzinfo=UTC)
        except Exception:
            try:
                expiry_dt = datetime.fromisoformat(not_after)
                if expiry_dt.tzinfo is None:
                    expiry_dt = expiry_dt.replace(tzinfo=UTC)
            except Exception:
                return None

    if expiry_dt is None:
        return None

    now = datetime.now(UTC)
    delta_days = (expiry_dt - now).total_seconds() / 86400.0

    if delta_days < 30.0:
        alert = Alert(
            id=f"alt_{uuid4().hex[:12]}",
            type=AlertType.CERT_EXPIRING,
            targetId=target_id,
            findingId=finding_id,
            severity=RiskBand.HIGH if delta_days > 7 else RiskBand.CRITICAL,
            message=f"Certificate expiring in {int(max(0, delta_days))} days (expires at {expiry_dt.isoformat()})",
            createdAt=now,
            acknowledged=False,
        )
        return dispatch_alert(alert)
    return None


def check_drift_alerts(target_id: str, drift: Drift) -> list[Alert]:
    """Trigger alert if snapshot drift introduces new critical findings or increases risk."""
    alerts: list[Alert] = []
    now = datetime.now(UTC)

    # 1. New critical finding introduced in drift
    for added_finding in drift.added:
        score = added_finding.risk.score if added_finding.risk else 0.0
        band = added_finding.risk.band if added_finding.risk else None
        if band == RiskBand.CRITICAL or score >= 60.0:
            alert = Alert(
                id=f"alt_{uuid4().hex[:12]}",
                type=AlertType.DRIFT,
                targetId=target_id,
                findingId=added_finding.id,
                severity=RiskBand.CRITICAL,
                message=(
                    f"Drift introduced critical finding: {added_finding.displayName} "
                    f"in {added_finding.location.path}"
                ),
                createdAt=now,
                acknowledged=False,
            )
            dispatch_alert(alert)
            alerts.append(alert)

    # 2. Overall risk regression (netRiskDelta > 0)
    if drift.summary.netRiskDelta > 0 and not alerts:
        severity = RiskBand.CRITICAL if drift.summary.netRiskDelta >= 20.0 else RiskBand.HIGH
        alert = Alert(
            id=f"alt_{uuid4().hex[:12]}",
            type=AlertType.DRIFT,
            targetId=target_id,
            findingId=None,
            severity=severity,
            message=(
                f"Cryptographic risk regression: net risk score increased by "
                f"+{drift.summary.netRiskDelta:.1f} ({drift.summary.addedCount} added, "
                f"{drift.summary.resolvedCount} resolved)"
            ),
            createdAt=now,
            acknowledged=False,
        )
        dispatch_alert(alert)
        alerts.append(alert)

    return alerts


def check_probe_downgrade(target_id: str, probe_result: ProbeResult) -> Alert | None:
    """Trigger alert if a probe negotiates an insecure or downgraded algorithm."""
    negotiated: dict[str, Any] = probe_result.negotiated or {}
    proto = str(negotiated.get("protocol", "")).lower()
    cipher = str(negotiated.get("cipher", "")).lower()
    kex = str(negotiated.get("kex", "")).lower()

    is_insecure = False
    details = []

    if proto in INSECURE_PROTOCOLS:
        is_insecure = True
        details.append(f"insecure protocol {proto.upper()}")

    if INSECURE_CIPHER_PATTERNS.search(cipher):
        is_insecure = True
        details.append(f"insecure cipher {cipher}")

    if INSECURE_CIPHER_PATTERNS.search(kex):
        is_insecure = True
        details.append(f"insecure key exchange {kex}")

    if is_insecure:
        detail_str = ", ".join(details)
        alert = Alert(
            id=f"alt_{uuid4().hex[:12]}",
            type=AlertType.PROBE_DOWNGRADE,
            targetId=target_id,
            findingId=None,
            severity=RiskBand.CRITICAL,
            message=(
                f"Probe detected insecure/downgraded primitive on "
                f"{probe_result.host}:{probe_result.port}: {detail_str}"
            ),
            createdAt=datetime.now(UTC),
            acknowledged=False,
        )
        return dispatch_alert(alert)

    return None


def check_residue_rise(
    target_id: str,
    from_residue_mass: float | None,
    to_residue_mass: float | None,
    threshold: float = 10.0,
) -> Alert | None:
    """Trigger alert if residue mass rises by more than the configured threshold between snapshots.

    That means new unexplained cryptographic evidence mass appeared in the estate.
    """
    if from_residue_mass is None or to_residue_mass is None:
        return None

    delta = to_residue_mass - from_residue_mass
    if delta > threshold:
        alert = Alert(
            id=f"alt_{uuid4().hex[:12]}",
            type=AlertType.RESIDUE_RISE,
            targetId=target_id,
            findingId=None,
            severity=RiskBand.HIGH if delta < 50.0 else RiskBand.CRITICAL,
            message=(
                f"Residue crypto mass increased significantly by +{delta:.1f} "
                f"(from {from_residue_mass:.1f} to {to_residue_mass:.1f}), exceeding threshold {threshold:.1f}. "
                "New unexplained cryptographic suspicion appeared."
            ),
            createdAt=datetime.now(UTC),
            acknowledged=False,
        )
        return dispatch_alert(alert)
    return None

