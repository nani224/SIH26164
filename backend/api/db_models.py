"""SQLModel table definitions (Phase 2 persistence).

Filterable/sortable fields (everything api/filtering.py operates on, plus
every raw risk factor per the brief's "all raw risk factors stored") are
flattened into real columns. Nested, non-filtered structures
(Recommendation, Policy.default/contexts, ScanStats-as-a-unit) are stored
as JSON columns -- normalizing them into more tables isn't earning its
keep yet at this scale.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ScanRecord(SQLModel, table=True):
    __tablename__ = "scans"

    id: str = Field(primary_key=True)
    target: str
    status: str
    files: int | None = None
    bytes: int | None = None
    seconds: float | None = None
    mb_per_sec: float | None = None
    errors: int | None = None
    skipped_prefilter: int | None = None
    bands: dict[str, int] = Field(default_factory=dict, sa_column=Column(JSON))
    policy_id: str
    crqc_years: int
    started_at: datetime
    finished_at: datetime | None = None
    bundle_hash: str | None = None


class FindingRecord(SQLModel, table=True):
    __tablename__ = "findings"

    id: str = Field(primary_key=True)
    scan_id: str = Field(index=True)
    kind: str
    surface: str
    family: str | None = None
    display_name: str
    key_size: int | None = None
    mode: str | None = None
    curve: str | None = None
    function: str
    location_path: str
    location_line: int | None = None
    location_offset: int | None = None
    location_layer: str | None = None
    symbol: str
    snippet: str
    source: str
    confidence: float

    # Raw risk factors -- stored individually per the brief ("all raw risk
    # factors stored"), not just the final score, so rescoring/audit can
    # work from them directly.
    risk_score: float | None = None
    risk_band: str | None = None
    risk_v: float | None = None
    risk_f: float | None = None
    risk_u: float | None = None
    risk_e: float | None = None
    risk_k: float | None = None
    risk_x: float | None = None
    risk_y: float | None = None
    risk_z: float | None = None
    risk_mosca_margin: float | None = None
    risk_reason: str | None = None
    risk_classically_broken: bool | None = None
    risk_hndl: bool | None = None
    risk_needs_review: bool | None = None

    recommendation: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    triage_status: str = "open"
    triage_note: str | None = None
    negotiated: bool | None = None


class PolicyRecord(SQLModel, table=True):
    __tablename__ = "policies"

    id: str = Field(primary_key=True)
    name: str
    crqc_years: int
    default_context: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    contexts: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))


class AuditLogRecord(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=_utcnow)
    actor: str = Field(default="system")
    action: str
    entity_type: str
    entity_id: str
    detail: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    prev_hash: str = Field(default="0" * 64)
    record_hash: str = Field(default="")


class ScanEventRecord(SQLModel, table=True):
    """Phase 4: the real, replayable event log for a scan's WS stream.

    event_id is sequential *within* a scan (starts at 1), separate from
    the global autoincrement `id` -- it's what clients pass back via the
    `after` query param to resume.
    """

    __tablename__ = "scan_events"

    id: int | None = Field(default=None, primary_key=True)
    scan_id: str = Field(index=True)
    event_id: int
    type: str
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_utcnow)


class TargetRecord(SQLModel, table=True):
    __tablename__ = "targets"

    id: str = Field(primary_key=True)
    name: str
    kind: str  # repo, path, endpoint
    uri: str
    policy_id: str
    schedule: str
    enabled: bool = True
    last_scan_id: str | None = None
    last_scan_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class ScanSnapshotRecord(SQLModel, table=True):
    __tablename__ = "scan_snapshots"

    id: str = Field(primary_key=True)
    target_id: str = Field(index=True)
    scan_id: str = Field(index=True)
    taken_at: datetime = Field(default_factory=_utcnow)
    bands: dict[str, int] = Field(default_factory=dict, sa_column=Column(JSON))
    total_findings: int = 0
    stats: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    coverage_ratio: float | None = None
    residue_mass: float | None = None


class AlertRecord(SQLModel, table=True):
    __tablename__ = "alerts"

    id: str = Field(primary_key=True)
    type: str  # new-critical, cert-expiring, drift, probe-downgrade, residue-rise
    target_id: str = Field(index=True)
    finding_id: str | None = None
    severity: str  # critical, high, medium, low
    message: str
    created_at: datetime = Field(default_factory=_utcnow)
    acknowledged: bool = False


class ProbeResultRecord(SQLModel, table=True):
    __tablename__ = "probe_results"

    id: str = Field(primary_key=True)
    target_id: str = Field(index=True)
    host: str
    port: int
    protocol: str  # tls, ssh
    negotiated: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    supported: list[Any] = Field(default_factory=list, sa_column=Column(JSON))
    probed_at: datetime = Field(default_factory=_utcnow)


class CoverageCertificateRecord(SQLModel, table=True):
    __tablename__ = "coverage_certificates"

    scan_id: str = Field(primary_key=True)
    artifact_count: int
    total_mass: float
    attributed_mass: float
    excluded_mass: float
    residue_mass: float
    coverage_ratio: float
    residue_cluster_count: int
    computed_at: datetime = Field(default_factory=_utcnow)


class ArtifactCoverageRecord(SQLModel, table=True):
    __tablename__ = "artifact_coverages"

    id: str = Field(primary_key=True)
    scan_id: str = Field(index=True)
    artifact_hash: str = Field(index=True)
    path: str
    total_mass: float
    attributed: float
    excluded: float
    residue: float
    coverage_ratio: float


class ResidueClusterRecord(SQLModel, table=True):
    __tablename__ = "residue_clusters"

    id: str = Field(primary_key=True)
    content_hash: str = Field(index=True)
    signal_types: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    magnitude: float
    occurrences: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    state: str = "open"  # open, promoted, excluded, accepted
    justification: str | None = None
    owner: str | None = None
    target_id: str | None = Field(default=None, index=True)
    first_seen: datetime = Field(default_factory=_utcnow)
    last_seen: datetime = Field(default_factory=_utcnow)


class AssetCriticalityRecord(SQLModel, table=True):
    __tablename__ = "asset_criticalities"

    id: str = Field(primary_key=True)
    target_id: str = Field(index=True)
    path_pattern: str
    criticality: str
    business_owner: str
    data_classification: str
    facing: str  # internal, external
    source: str  # manual, import
    created_at: datetime = Field(default_factory=_utcnow)


