"""Probe endpoints for live network cryptographic auditing (TLS and SSH)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from api import store
from api.models import ProbeRequest, ProbeResult
from probes.guard import SecurityException
from probes.reconciler import reconcile_probe_findings
from probes.ssh import probe_ssh
from probes.tls import probe_tls

router = APIRouter(tags=["probes"])


@router.post("/probes/tls", response_model=ProbeResult)
def probe_tls_endpoint(payload: ProbeRequest) -> ProbeResult:
    """Probe a TLS endpoint, record result, and reconcile findings."""
    try:
        result = probe_tls(host=payload.host, port=payload.port, target_id=payload.targetId)
    except SecurityException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"TLS probe failed: {exc}") from exc

    saved = store.create_probe_result(result)
    reconcile_probe_findings(payload.targetId, saved)
    # Check alert rules
    try:
        from api.alerts import rules as alert_rules
        alert_rules.check_probe_downgrade(payload.targetId, saved)
        alert_rules.check_cert_expiring(payload.targetId, saved.negotiated.get("certNotAfter"))
    except Exception:
        pass
    return saved


@router.post("/probes/ssh", response_model=ProbeResult)
def probe_ssh_endpoint(payload: ProbeRequest) -> ProbeResult:
    """Probe an SSH endpoint, record result, and reconcile findings."""
    try:
        result = probe_ssh(host=payload.host, port=payload.port, target_id=payload.targetId)
    except SecurityException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"SSH probe failed: {exc}") from exc

    saved = store.create_probe_result(result)
    reconcile_probe_findings(payload.targetId, saved)
    # Check alert rules
    try:
        from api.alerts import rules as alert_rules
        alert_rules.check_probe_downgrade(payload.targetId, saved)
    except Exception:
        pass
    return saved


@router.get("/probes", response_model=list[ProbeResult])
def list_probes(targetId: str | None = Query(default=None)) -> list[ProbeResult]:
    """List historical probe results, optionally filtered by target ID."""
    return store.list_probe_results(target_id=targetId)
