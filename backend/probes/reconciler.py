"""Probe Reconciler.

Correlates live network probe observations (negotiated ciphers, key exchanges,
certificates, and protocols) with static code/inventory findings.
When a finding matches an algorithm actually observed in an active network
handshake, its `negotiated` attribute is set to True.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlmodel import select

from api import db
from api.db_models import FindingRecord, TargetRecord
from api.models import ProbeResult

logger = logging.getLogger(__name__)


def _normalize_token(val: str) -> str:
    """Normalize a cryptographic identifier for fuzzy comparison.

    Strips hyphens, underscores, slashes, spaces, and lowercases.
    e.g. 'TLS_RSA_WITH_AES_128_CBC_SHA' -> 'tlsrsawithaes128cbcsha'
    """
    return re.sub(r"[^a-zA-Z0-9]", "", val).lower()


def extract_negotiated_tokens(negotiated: dict[str, Any]) -> set[str]:
    """Extract a set of normalized tokens from the negotiated dictionary."""
    tokens: set[str] = set()
    for _key, val in negotiated.items():
        if val is None:
            continue
        str_val = str(val)
        tokens.add(_normalize_token(str_val))
        # Split compound identifiers like TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
        parts = re.split(r"[-_/\s]+", str_val)
        for p in parts:
            if len(p) >= 2:
                tokens.add(_normalize_token(p))
    return tokens


def reconcile_probe_findings(target_id: str, probe_result: ProbeResult) -> int:
    """Reconcile probe results with existing findings for the target.

    Finds all findings associated with the target's latest scan and sets
    `finding.negotiated = True` if the finding corresponds to any primitive
    actually negotiated in the handshake.

    Args:
        target_id: Target identifier.
        probe_result: The ProbeResult with negotiated parameters.

    Returns:
        Number of findings marked as negotiated.
    """
    negotiated_tokens = extract_negotiated_tokens(probe_result.negotiated)
    if not negotiated_tokens:
        return 0

    reconciled_count = 0

    with db.session_scope() as session:
        target = session.get(TargetRecord, target_id)
        if not target or not target.last_scan_id:
            # Fallback: find findings associated with target ID directly
            findings_stmt = select(FindingRecord).where(FindingRecord.scan_id == target_id)
            findings = session.exec(findings_stmt).all()
        else:
            findings_stmt = select(FindingRecord).where(FindingRecord.scan_id == target.last_scan_id)
            findings = session.exec(findings_stmt).all()

        for finding in findings:
            finding_tokens = {
                _normalize_token(finding.symbol or ""),
                _normalize_token(finding.display_name or ""),
                _normalize_token(finding.family or ""),
                _normalize_token(finding.mode or ""),
                _normalize_token(finding.curve or ""),
            }
            finding_tokens.discard("")

            # Match if any token is directly in negotiated_tokens or contains/contained by a token
            matched = False
            for ft in finding_tokens:
                if len(ft) < 3:
                    continue
                if ft in negotiated_tokens:
                    matched = True
                    break
                for nt in negotiated_tokens:
                    if len(nt) >= 4 and (ft in nt or nt in ft):
                        matched = True
                        break
                if matched:
                    break

            if matched and finding.negotiated is not True:
                finding.negotiated = True
                session.add(finding)
                reconciled_count += 1

        if reconciled_count > 0:
            db.log_audit(
                session,
                action="probe.reconcile",
                entity_type="target",
                entity_id=target_id,
                detail={"reconciledCount": reconciled_count, "probeId": probe_result.id},
            )
            session.commit()

    logger.info(
        "Reconciled %d findings for target %s from probe %s",
        reconciled_count,
        target_id,
        probe_result.id,
    )
    return reconciled_count
