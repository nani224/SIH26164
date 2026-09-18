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
    action: str
    entity_type: str
    entity_id: str
    detail: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
