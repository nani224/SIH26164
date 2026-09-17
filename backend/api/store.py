"""In-memory Phase 0 state for scans and policies.

Not persisted across restarts — real persistence is Phase 2 (SQLModel).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from api import stub_data
from api.models import BandCounts, Policy, Scan, ScanCreate, ScanStats, ScanStatus

_SCANS: dict[str, Scan] = {}
_POLICIES: dict[str, Policy] = {}


def _seed() -> None:
    scan = stub_data.default_scan()
    _SCANS[scan.id] = scan
    _POLICIES[stub_data.DEFAULT_POLICY.id] = stub_data.DEFAULT_POLICY


_seed()


def create_scan(payload: ScanCreate) -> Scan:
    scan_id = f"scan_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC)
    policy_id = payload.policyId or stub_data.DEFAULT_POLICY.id
    policy = _POLICIES.get(policy_id, stub_data.DEFAULT_POLICY)
    scan = Scan(
        id=scan_id,
        target=payload.path or "uploaded-artifact",
        status=ScanStatus.DONE,
        stats=ScanStats(files=0, bytes=0, seconds=0.0, mbPerSec=0.0, errors=0, skippedPrefilter=0),
        bands=BandCounts(),
        policyId=policy.id,
        crqcYears=payload.crqcYears or policy.crqcYears,
        startedAt=now,
        finishedAt=now,
    )
    _SCANS[scan_id] = scan
    return scan


def list_scans() -> list[Scan]:
    return list(_SCANS.values())


def get_scan(scan_id: str) -> Scan | None:
    return _SCANS.get(scan_id)


def list_policies() -> list[Policy]:
    return list(_POLICIES.values())


def get_policy(policy_id: str) -> Policy | None:
    return _POLICIES.get(policy_id)


def put_policy(policy: Policy) -> Policy:
    _POLICIES[policy.id] = policy
    return policy
