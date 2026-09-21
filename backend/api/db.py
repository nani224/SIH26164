"""SQLModel engine/session setup, seeding, and Pydantic<->record conversion.

`DATABASE_URL` is read once at import time (default `sqlite:///./ecdat.db`).
Tests override it by setting the env var *before* `api.db` is first
imported (see tests/conftest.py) so the whole test session shares one
in-memory SQLite database via StaticPool -- otherwise every `sqlite://`
connection would get its own separate empty database.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, col, create_engine, select, text

from api import stub_data
from api.db_models import (
    AlertRecord,
    ArtifactCoverageRecord,
    AssetCriticalityRecord,
    AuditLogRecord,
    CoverageCertificateRecord,
    FindingRecord,
    PolicyRecord,
    ProbeResultRecord,
    ResidueClusterRecord,
    ScanRecord,
    ScanSnapshotRecord,
    TargetRecord,
)
from api.models import (
    Alert,
    AlertType,
    ArtifactCoverage,
    AssetCriticality,
    AssetFacing,
    BandCounts,
    Context,
    ContextWithGlob,
    CoverageCertificate,
    Criticality,
    CriticalitySource,
    Finding,
    Location,
    Policy,
    ProbeProtocol,
    ProbeResult,
    Recommendation,
    ResidueCluster,
    ResidueClusterState,
    ResidueOccurrence,
    Risk,
    RiskBand,
    Scan,
    ScanSnapshot,
    ScanStats,
    Target,
    TargetKind,
    Triage,
)

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./ecdat.db")

_is_memory = DATABASE_URL in ("sqlite://", "sqlite:///:memory:")
_engine_kwargs: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
if _is_memory:
    _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, **_engine_kwargs)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    if "sqlite" in str(engine.url):
        cursor = dbapi_connection.cursor()
        with suppress(Exception):
            cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = OFF")
        cursor.execute("PRAGMA cache_size = -128000")
        cursor.execute("PRAGMA temp_store = MEMORY")
        with suppress(Exception):
            cursor.execute("PRAGMA mmap_size = 268435456")
        cursor.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def compute_audit_record_hash(
    *, action: str, entity_type: str, entity_id: str, detail: dict[str, Any], prev_hash: str
) -> str:
    detail_str = json.dumps(detail, sort_keys=True)
    payload = f"{action}|{entity_type}|{entity_id}|{detail_str}|{prev_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def log_audit(
    session: Session, *, action: str, entity_type: str, entity_id: str, detail: dict[str, Any] | None = None
) -> AuditLogRecord:
    last_rec = session.exec(select(AuditLogRecord).order_by(col(AuditLogRecord.id).desc())).first()
    prev_hash = last_rec.record_hash if (last_rec and last_rec.record_hash) else "0" * 64
    d = detail or {}
    rec_hash = compute_audit_record_hash(
        action=action, entity_type=entity_type, entity_id=entity_id, detail=d, prev_hash=prev_hash
    )
    rec = AuditLogRecord(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=d,
        prev_hash=prev_hash,
        record_hash=rec_hash,
    )
    session.add(rec)
    return rec


def verify_audit_log_integrity(session: Session) -> tuple[bool, str | None]:
    """Verify cryptographic hash-chaining of the entire audit log.

    Returns (True, None) if the chain is strictly intact.
    Returns (False, reason) if tampering, broken hash, or insertion is detected.
    """
    records = session.exec(select(AuditLogRecord).order_by(col(AuditLogRecord.id).asc())).all()
    if not records:
        return True, None

    expected_prev = "0" * 64
    for i, rec in enumerate(records):
        if rec.prev_hash != expected_prev:
            return (
                False,
                f"Broken chain at record id={rec.id} (index {i}): "
                f"prev_hash={rec.prev_hash} != expected {expected_prev}",
            )

        calc_hash = compute_audit_record_hash(
            action=rec.action,
            entity_type=rec.entity_type,
            entity_id=rec.entity_id,
            detail=rec.detail or {},
            prev_hash=rec.prev_hash,
        )
        if rec.record_hash != calc_hash:
            return (
                False,
                f"Tampered record at id={rec.id}: stored hash={rec.record_hash} != computed {calc_hash}",
            )

        expected_prev = rec.record_hash

    return True, None


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
        negotiated=finding.negotiated,
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
        negotiated=rec.negotiated,
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


# --- Target <-> TargetRecord -----------------------------------------------------

def target_to_record(target: Target) -> TargetRecord:
    return TargetRecord(
        id=target.id,
        name=target.name,
        kind=target.kind.value,
        uri=target.uri,
        policy_id=target.policyId,
        schedule=target.schedule,
        enabled=target.enabled,
        last_scan_id=target.lastScanId,
        last_scan_at=target.lastScanAt,
        created_at=target.createdAt,
    )


def record_to_target(rec: TargetRecord) -> Target:
    return Target(
        id=rec.id,
        name=rec.name,
        kind=TargetKind(rec.kind),
        uri=rec.uri,
        policyId=rec.policy_id,
        schedule=rec.schedule,
        enabled=rec.enabled,
        lastScanId=rec.last_scan_id,
        lastScanAt=_as_utc(rec.last_scan_at),
        createdAt=_as_utc(rec.created_at) or rec.created_at,
    )


# --- ScanSnapshot <-> ScanSnapshotRecord -----------------------------------------

def snapshot_to_record(snapshot: ScanSnapshot) -> ScanSnapshotRecord:
    return ScanSnapshotRecord(
        id=snapshot.id,
        target_id=snapshot.targetId,
        scan_id=snapshot.scanId,
        taken_at=snapshot.takenAt,
        bands=snapshot.bands,
        total_findings=snapshot.totalFindings,
        stats=snapshot.stats.model_dump(),
        coverage_ratio=snapshot.coverageRatio,
        residue_mass=snapshot.residueMass,
    )


def record_to_snapshot(rec: ScanSnapshotRecord) -> ScanSnapshot:
    return ScanSnapshot(
        id=rec.id,
        targetId=rec.target_id,
        scanId=rec.scan_id,
        takenAt=_as_utc(rec.taken_at) or rec.taken_at,
        bands=rec.bands,
        totalFindings=rec.total_findings,
        stats=ScanStats.model_validate(rec.stats),
        coverageRatio=rec.coverage_ratio,
        residueMass=rec.residue_mass,
    )


# --- Alert <-> AlertRecord -------------------------------------------------------

def alert_to_record(alert: Alert) -> AlertRecord:
    return AlertRecord(
        id=alert.id,
        type=alert.type.value,
        target_id=alert.targetId,
        finding_id=alert.findingId,
        severity=alert.severity.value,
        message=alert.message,
        created_at=alert.createdAt,
        acknowledged=alert.acknowledged,
    )


def record_to_alert(rec: AlertRecord) -> Alert:
    return Alert(
        id=rec.id,
        type=AlertType(rec.type),
        targetId=rec.target_id,
        findingId=rec.finding_id,
        severity=RiskBand(rec.severity),
        message=rec.message,
        createdAt=_as_utc(rec.created_at) or rec.created_at,
        acknowledged=rec.acknowledged,
    )


# --- ProbeResult <-> ProbeResultRecord -------------------------------------------

def probe_result_to_record(result: ProbeResult) -> ProbeResultRecord:
    return ProbeResultRecord(
        id=result.id,
        target_id=result.targetId,
        host=result.host,
        port=result.port,
        protocol=result.protocol.value,
        negotiated=result.negotiated,
        supported=result.supported,
        probed_at=result.probedAt,
    )


def record_to_probe_result(rec: ProbeResultRecord) -> ProbeResult:
    return ProbeResult(
        id=rec.id,
        targetId=rec.target_id,
        host=rec.host,
        port=rec.port,
        protocol=ProbeProtocol(rec.protocol),
        negotiated=rec.negotiated,
        supported=rec.supported,
        probedAt=_as_utc(rec.probed_at) or rec.probed_at,
    )


def record_to_coverage_certificate(rec: CoverageCertificateRecord) -> CoverageCertificate:
    return CoverageCertificate(
        scanId=rec.scan_id,
        artifactCount=rec.artifact_count,
        totalMass=rec.total_mass,
        attributedMass=rec.attributed_mass,
        excludedMass=rec.excluded_mass,
        residueMass=rec.residue_mass,
        coverageRatio=rec.coverage_ratio,
        residueClusterCount=rec.residue_cluster_count,
        computedAt=_as_utc(rec.computed_at) or rec.computed_at,
    )


def coverage_certificate_to_record(cert: CoverageCertificate | dict[str, Any]) -> CoverageCertificateRecord:
    if isinstance(cert, dict):
        cert = CoverageCertificate.model_validate(cert)
    return CoverageCertificateRecord(
        scan_id=cert.scanId,
        artifact_count=cert.artifactCount,
        total_mass=cert.totalMass,
        attributed_mass=cert.attributedMass,
        excluded_mass=cert.excludedMass,
        residue_mass=cert.residueMass,
        coverage_ratio=cert.coverageRatio,
        residue_cluster_count=cert.residueClusterCount,
        computed_at=cert.computedAt,
    )


def record_to_artifact_coverage(rec: ArtifactCoverageRecord) -> ArtifactCoverage:
    return ArtifactCoverage(
        artifactHash=rec.artifact_hash,
        path=rec.path,
        totalMass=rec.total_mass,
        attributed=rec.attributed,
        excluded=rec.excluded,
        residue=rec.residue,
        coverageRatio=rec.coverage_ratio,
    )


def artifact_coverage_to_record(cov: ArtifactCoverage, scan_id: str) -> ArtifactCoverageRecord:
    return ArtifactCoverageRecord(
        id=f"{scan_id}:{cov.artifactHash}",
        scan_id=scan_id,
        artifact_hash=cov.artifactHash,
        path=cov.path,
        total_mass=cov.totalMass,
        attributed=cov.attributed,
        excluded=cov.excluded,
        residue=cov.residue,
        coverage_ratio=cov.coverageRatio,
    )


def record_to_residue_cluster(rec: ResidueClusterRecord) -> ResidueCluster:
    occurrences = [
        ResidueOccurrence(
            artifactHash=occ.get("artifactHash", ""),
            path=occ.get("path", ""),
            range=occ.get("range", [0, 0]),
        )
        for occ in (rec.occurrences or [])
    ]
    return ResidueCluster(
        id=rec.id,
        contentHash=rec.content_hash,
        signalTypes=rec.signal_types or [],
        magnitude=rec.magnitude,
        occurrences=occurrences,
        state=ResidueClusterState(rec.state),
        justification=rec.justification,
        owner=rec.owner,
        firstSeen=_as_utc(rec.first_seen) or rec.first_seen,
        lastSeen=_as_utc(rec.last_seen) or rec.last_seen,
    )


def residue_cluster_to_record(cluster: ResidueCluster, target_id: str | None = None) -> ResidueClusterRecord:
    return ResidueClusterRecord(
        id=cluster.id,
        content_hash=cluster.contentHash,
        signal_types=cluster.signalTypes,
        magnitude=cluster.magnitude,
        occurrences=[occ.model_dump() for occ in cluster.occurrences],
        state=cluster.state.value if hasattr(cluster.state, "value") else str(cluster.state),
        justification=cluster.justification,
        owner=cluster.owner,
        target_id=target_id,
        first_seen=cluster.firstSeen,
        last_seen=cluster.lastSeen,
    )


def record_to_asset_criticality(rec: AssetCriticalityRecord) -> AssetCriticality:
    return AssetCriticality(
        targetId=rec.target_id,
        pathPattern=rec.path_pattern,
        criticality=Criticality(rec.criticality),
        businessOwner=rec.business_owner,
        dataClassification=rec.data_classification,
        facing=AssetFacing(rec.facing),
        source=CriticalitySource(rec.source),
    )


def asset_criticality_to_record(crit: AssetCriticality) -> AssetCriticalityRecord:
    rec_id = f"{crit.targetId}:{crit.pathPattern}"
    return AssetCriticalityRecord(
        id=rec_id,
        target_id=crit.targetId,
        path_pattern=crit.pathPattern,
        criticality=crit.criticality.value if hasattr(crit.criticality, "value") else str(crit.criticality),
        business_owner=crit.businessOwner,
        data_classification=crit.dataClassification,
        facing=crit.facing.value if hasattr(crit.facing, "value") else str(crit.facing),
        source=crit.source.value if hasattr(crit.source, "value") else str(crit.source),
    )


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    with engine.connect() as conn:
        with suppress(Exception):
            conn.execute(text("ALTER TABLE scans ADD COLUMN bundle_hash VARCHAR"))
            conn.commit()
        with suppress(Exception):
            conn.execute(text("ALTER TABLE findings ADD COLUMN negotiated BOOLEAN"))
            conn.commit()
        with suppress(Exception):
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_findings_rescore "
                    "ON findings (scan_id, risk_classically_broken)"
                )
            )
            conn.commit()
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
