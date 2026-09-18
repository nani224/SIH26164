"""SQLModel engine/session setup, seeding, and Pydantic<->record conversion.

`DATABASE_URL` is read once at import time (default `sqlite:///./ecdat.db`).
Tests override it by setting the env var *before* `api.db` is first
imported (see tests/conftest.py) so the whole test session shares one
in-memory SQLite database via StaticPool -- otherwise every `sqlite://`
connection would get its own separate empty database.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from api import stub_data
from api.db_models import AuditLogRecord, FindingRecord, PolicyRecord, ScanRecord
from api.models import (
    BandCounts,
    Context,
    ContextWithGlob,
    Finding,
    Location,
    Policy,
    Recommendation,
    Risk,
    RiskBand,
    Scan,
    ScanStats,
    Triage,
)

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./ecdat.db")

_is_memory = DATABASE_URL in ("sqlite://", "sqlite:///:memory:")
_engine_kwargs: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
if _is_memory:
    _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, **_engine_kwargs)


@contextmanager
def session_scope() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def log_audit(
    session: Session, *, action: str, entity_type: str, entity_id: str, detail: dict[str, Any] | None = None
) -> None:
    session.add(AuditLogRecord(action=action, entity_type=entity_type, entity_id=entity_id, detail=detail or {}))


# --- Finding <-> FindingRecord -------------------------------------------------

def finding_to_record(finding: Finding, scan_id: str) -> FindingRecord:
    risk = finding.risk
    rec = finding.recommendation
    return FindingRecord(
        id=finding.id,
        scan_id=scan_id,
        kind=finding.kind.value,
        surface=finding.surface.value,
        family=finding.family.value if finding.family else None,
        display_name=finding.displayName,
        key_size=finding.keySize,
        mode=finding.mode,
        curve=finding.curve,
        function=finding.function.value,
        location_path=finding.location.path,
        location_line=finding.location.line,
        location_offset=finding.location.offset,
        location_layer=finding.location.layer,
        symbol=finding.symbol,
        snippet=finding.snippet,
        source=finding.source.value,
        confidence=finding.confidence,
        risk_score=risk.score if risk else None,
        risk_band=risk.band.value if risk else None,
        risk_v=risk.V if risk else None,
        risk_f=risk.F if risk else None,
        risk_u=risk.U if risk else None,
        risk_e=risk.E if risk else None,
        risk_k=risk.K if risk else None,
        risk_x=risk.X if risk else None,
        risk_y=risk.Y if risk else None,
        risk_z=risk.Z if risk else None,
        risk_mosca_margin=risk.moscaMargin if risk else None,
        risk_reason=risk.reason if risk else None,
        risk_classically_broken=risk.classicallyBroken if risk else None,
        risk_hndl=risk.hndl if risk else None,
        risk_needs_review=risk.needsReview if risk else None,
        recommendation=rec.model_dump() if rec else None,
        triage_status=finding.triage.status.value,
        triage_note=finding.triage.note,
    )


def record_to_finding(rec: FindingRecord) -> Finding:
    risk = None
    if rec.risk_score is not None and rec.risk_band is not None:
        risk = Risk(
            score=rec.risk_score, band=RiskBand(rec.risk_band),
            V=rec.risk_v or 0.0, F=rec.risk_f or 0.0, U=rec.risk_u or 0.0,
            E=rec.risk_e or 0.0, K=rec.risk_k or 0.0, X=rec.risk_x or 0.0,
            Y=rec.risk_y or 0.0, Z=rec.risk_z or 0.0,
            moscaMargin=rec.risk_mosca_margin or 0.0, reason=rec.risk_reason or "",
            classicallyBroken=bool(rec.risk_classically_broken),
            hndl=bool(rec.risk_hndl), needsReview=bool(rec.risk_needs_review),
        )
    return Finding(
        id=rec.id, kind=rec.kind, surface=rec.surface, family=rec.family,  # type: ignore[arg-type]
        displayName=rec.display_name, keySize=rec.key_size, mode=rec.mode, curve=rec.curve,
        function=rec.function,  # type: ignore[arg-type]
        location=Location(
            path=rec.location_path, line=rec.location_line, offset=rec.location_offset, layer=rec.location_layer
        ),
        symbol=rec.symbol, snippet=rec.snippet, source=rec.source, confidence=rec.confidence,  # type: ignore[arg-type]
        risk=risk,
        recommendation=Recommendation.model_validate(rec.recommendation) if rec.recommendation else None,
        triage=Triage(status=rec.triage_status, note=rec.triage_note),  # type: ignore[arg-type]
    )


# --- Scan <-> ScanRecord --------------------------------------------------------

def scan_to_record(scan: Scan) -> ScanRecord:
    stats = scan.stats
    return ScanRecord(
        id=scan.id, target=scan.target, status=scan.status.value,
        files=stats.files if stats else None, bytes=stats.bytes if stats else None,
        seconds=stats.seconds if stats else None, mb_per_sec=stats.mbPerSec if stats else None,
        errors=stats.errors if stats else None, skipped_prefilter=stats.skippedPrefilter if stats else None,
        bands=scan.bands.model_dump(), policy_id=scan.policyId, crqc_years=scan.crqcYears,
        started_at=scan.startedAt, finished_at=scan.finishedAt,
        bundle_hash=scan.bundleHash,
    )


def _as_utc(dt: datetime | None) -> datetime | None:
    """SQLite drops tzinfo on round-trip; every stored timestamp is UTC by
    convention (always written via datetime.now(UTC)), so reattach it."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def record_to_scan(rec: ScanRecord) -> Scan:
    stats = None
    if rec.files is not None:
        stats = ScanStats(
            files=rec.files, bytes=rec.bytes or 0, seconds=rec.seconds or 0.0,
            mbPerSec=rec.mb_per_sec or 0.0, errors=rec.errors or 0, skippedPrefilter=rec.skipped_prefilter or 0,
        )
    return Scan(
        id=rec.id, target=rec.target, status=rec.status,  # type: ignore[arg-type]
        stats=stats, bands=BandCounts(**rec.bands), policyId=rec.policy_id, crqcYears=rec.crqc_years,
        startedAt=_as_utc(rec.started_at) or rec.started_at, finishedAt=_as_utc(rec.finished_at),
        bundleHash=rec.bundle_hash,
    )


# --- Policy <-> PolicyRecord -----------------------------------------------------

def policy_to_record(policy: Policy) -> PolicyRecord:
    return PolicyRecord(
        id=policy.id, name=policy.name, crqc_years=policy.crqcYears,
        default_context=policy.default.model_dump(),
        contexts=[c.model_dump() for c in policy.contexts],
    )


def record_to_policy(rec: PolicyRecord) -> Policy:
    return Policy(
        id=rec.id, name=rec.name, crqcYears=rec.crqc_years,
        default=Context.model_validate(rec.default_context),
        contexts=[ContextWithGlob.model_validate(c) for c in rec.contexts],
    )


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    with session_scope() as session:
        _seed_if_empty(session)


def _seed_if_empty(session: Session) -> None:
    if session.exec(select(ScanRecord).limit(1)).first() is not None:
        return
    session.add(policy_to_record(stub_data.DEFAULT_POLICY))
    scan = stub_data.default_scan()
    session.add(scan_to_record(scan))
    for finding in stub_data.list_findings():
        session.add(finding_to_record(finding, scan_id=scan.id))
    log_audit(session, action="db.seed", entity_type="database", entity_id="init", detail={"scanId": scan.id})
    session.commit()
