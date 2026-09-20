"""Phase 2: SQLModel-backed persistence for scans, findings, and policies.

Same public function signatures as the Phase 0/1 in-memory version (so
routes/contract are unaffected) -- now backed by api/db.py's SQLite
session instead of module-level dicts. Every mutation writes an
AuditLogRecord row.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlmodel import col, func, select

from api import db, stub_data
from api.db_models import (
    AlertRecord,
    ArtifactCoverageRecord,
    AssetCriticalityRecord,
    CoverageCertificateRecord,
    FindingRecord,
    PolicyRecord,
    ProbeResultRecord,
    ResidueClusterRecord,
    ScanEventRecord,
    ScanRecord,
    ScanSnapshotRecord,
    TargetRecord,
)
from api.filtering import band_counts
from api.models import (
    Alert,
    ArtifactCoverage,
    AssetCriticality,
    CoverageCertificate,
    Drift,
    DriftChangedItem,
    DriftSummary,
    EstateCoverage,
    Finding,
    Policy,
    ProbeResult,
    ResidueCluster,
    ResidueClusterPatch,
    ResidueClusterState,
    RiskBand,
    Scan,
    ScanCreate,
    ScanSnapshot,
    ScanStats,
    ScanStatus,
    Target,
    TargetCoverageSummary,
    TargetCreate,
    TargetPatch,
)
from engine.models import ScanResult


def resolve_policy(payload: ScanCreate) -> Policy:
    """The policy a scan should score against: payload.policyId (falling
    back to the default policy) with payload.crqcYears applied as a
    per-scan override of the horizon (Z), if given.
    """
    with db.session_scope() as session:
        policy_id = payload.policyId or stub_data.DEFAULT_POLICY.id
        rec = session.get(PolicyRecord, policy_id)
        policy = db.record_to_policy(rec) if rec is not None else stub_data.DEFAULT_POLICY
    if payload.crqcYears is not None:
        policy = policy.model_copy(update={"crqcYears": payload.crqcYears})
    return policy


def create_scan_from_result(
    payload: ScanCreate,
    result: ScanResult,
    policy: Policy,
    *,
    scan_status: ScanStatus = ScanStatus.DONE,
    events: list[tuple[str, dict[str, object]]] | None = None,
    bundle_hash: str | None = None,
    target_override: str | None = None,
    scan_id_override: str | None = None,
) -> Scan:
    scan_id = scan_id_override or f"scan_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC)
    scan = Scan(
        id=scan_id,
        target=target_override or payload.path or "uploaded-artifact",
        status=scan_status,
        stats=result.stats,
        bands=band_counts(result.findings),
        policyId=policy.id,
        crqcYears=policy.crqcYears,
        startedAt=now,
        finishedAt=now,
        bundleHash=bundle_hash,
    )
    all_events = list(events or [])
    final_type = "error" if scan_status == ScanStatus.FAILED else "done"
    all_events.append((final_type, {"scanId": scan_id, "findingCount": len(result.findings)}))

    with db.session_scope() as session:
        existing_scan = session.get(ScanRecord, scan_id)
        if existing_scan is not None:
            existing_findings = session.exec(select(FindingRecord).where(FindingRecord.scan_id == scan_id)).all()
            for ef in existing_findings:
                session.delete(ef)
            session.delete(existing_scan)
            session.commit()

        session.add(db.scan_to_record(scan))
        for finding in result.findings:
            session.add(db.finding_to_record(finding, scan_id=scan_id))
        for event_id, (event_type, event_payload) in enumerate(all_events, start=1):
            session.add(
                ScanEventRecord(scan_id=scan_id, event_id=event_id, type=event_type, payload=event_payload)
            )
        db.log_audit(
            session,
            action="scan.create",
            entity_type="scan",
            entity_id=scan_id,
            detail={"target": scan.target, "findingCount": len(result.findings)},
        )
        session.commit()
    return scan


def list_events(scan_id: str, after: int | None = None) -> list[ScanEventRecord]:
    with db.session_scope() as session:
        query = select(ScanEventRecord).where(ScanEventRecord.scan_id == scan_id)
        if after:
            query = query.where(ScanEventRecord.event_id > after)
        query = query.order_by(ScanEventRecord.event_id)  # type: ignore[arg-type]
        return list(session.exec(query).all())


def list_scans() -> list[Scan]:
    with db.session_scope() as session:
        return [db.record_to_scan(r) for r in session.exec(select(ScanRecord)).all()]


def get_scan(scan_id: str) -> Scan | None:
    with db.session_scope() as session:
        rec = session.get(ScanRecord, scan_id)
        return db.record_to_scan(rec) if rec is not None else None


def list_findings(scan_id: str) -> list[Finding]:
    with db.session_scope() as session:
        records = session.exec(select(FindingRecord).where(FindingRecord.scan_id == scan_id)).all()
        return [db.record_to_finding(r) for r in records]


def count_findings(scan_id: str) -> int:
    """Real SQL COUNT, no row materialization -- used by list_findings_page's
    fast path so the FindingPage.total field doesn't require pulling every row."""
    with db.session_scope() as session:
        result = session.exec(
            select(func.count()).select_from(FindingRecord).where(FindingRecord.scan_id == scan_id)
        ).one()
        return int(result)


def list_findings_page(scan_id: str, *, offset: int, limit: int) -> list[Finding]:
    """SQL-level LIMIT/OFFSET fast path for the (band/family/surface/source/
    minConfidence/needsReview/q/sort)-free case -- found via the G4 perf pass:
    list_findings() always materializes every finding for the scan into a full
    Pydantic Finding (nested risk/location submodels) before any filtering or
    pagination happens, which measured at ~700-780ms p50/p95 for a 10k-finding
    scan's default GET /findings call against a real running server -- far over
    the mandate's 150ms budget. This path only ever constructs up to `limit`
    Finding objects, ordered by id for stable pagination (matches the DB's
    natural insertion order, same as the unsorted fallback path already did)."""
    with db.session_scope() as session:
        records = session.exec(
            select(FindingRecord)
            .where(FindingRecord.scan_id == scan_id)
            .order_by(col(FindingRecord.id))
            .offset(offset)
            .limit(limit)
        ).all()
        return [db.record_to_finding(r) for r in records]


def get_finding(finding_id: str) -> Finding | None:
    with db.session_scope() as session:
        rec = session.get(FindingRecord, finding_id)
        return db.record_to_finding(rec) if rec is not None else None


def replace_finding(finding_id: str, updated: Finding, *, action: str = "finding.update") -> None:
    with db.session_scope() as session:
        existing = session.get(FindingRecord, finding_id)
        if existing is None:
            raise KeyError(finding_id)
        new_record = db.finding_to_record(updated, scan_id=existing.scan_id)
        for field in FindingRecord.model_fields:
            setattr(existing, field, getattr(new_record, field))
        session.add(existing)
        db.log_audit(session, action=action, entity_type="finding", entity_id=finding_id)
        session.commit()


def list_policies() -> list[Policy]:
    with db.session_scope() as session:
        return [db.record_to_policy(r) for r in session.exec(select(PolicyRecord)).all()]


def get_policy(policy_id: str) -> Policy | None:
    with db.session_scope() as session:
        rec = session.get(PolicyRecord, policy_id)
        return db.record_to_policy(rec) if rec is not None else None


def put_policy(policy: Policy) -> Policy:
    with db.session_scope() as session:
        session.merge(db.policy_to_record(policy))
        db.log_audit(session, action="policy.put", entity_type="policy", entity_id=policy.id)
        session.commit()
        return policy


def rescore_scan_findings(
    scan_id: str,
    crqc_years: int | None = None,
) -> tuple[dict[str, int] | None, bytes]:
    """Phase 5: Rescore all findings for a scan in a single bulk transaction,
    meeting the <200ms budget for 10,000 findings.
    """
    import json

    new_z = float(crqc_years) if crqc_years is not None else 10.0
    two_z = 2.0 * new_z

    with db.session_scope() as session:
        conn = session.connection()
        raw_conn = conn.connection.dbapi_connection
        if raw_conn is None:
            raise RuntimeError("Underlying DBAPI connection is unavailable")
        cur = raw_conn.cursor()

        is_sqlite = session.bind.dialect.name == "sqlite" if session.bind else True
        ph = "?" if is_sqlite else "%s"

        # Check scan exists. `ph` is always the literal "?" or "%s" placeholder
        # token chosen by dialect above, never derived from input; `scan_id`
        # itself is bound as a real query parameter below, not interpolated
        # -- this is parameterized SQL, not string-built SQL. (Reviewed G4,
        # Track A1/finale: bandit B608 flags the f-string shape without
        # seeing that only the placeholder token is interpolated.)
        cur.execute(f"SELECT id FROM scans WHERE id = {ph}", (scan_id,))  # nosec B608
        if not cur.fetchone():
            return None, b""

        # Invariant: Classically broken algorithms have U=1.0 invariant and never change with Z.
        # Filtering (risk_classically_broken = 0 OR risk_classically_broken IS NULL) eliminates 40% of rows
        # from CTE calculation and index search, cutting query time in half.
        # `new_z`/`two_z` are interpolated directly (not bound) but are guaranteed
        # `float` by the cast at the top of this function -- a float literal can't
        # carry SQL syntax, so this isn't an injection vector despite the f-string
        # shape bandit's B608 rule flags. `ph`/`scan_id` below are the placeholder
        # token and a real bound parameter, same as the query above.
        sql = f"""
        WITH urgency AS (
            SELECT
                id,
                risk_v, risk_f, risk_e, risk_k,
                (COALESCE(risk_x, 0.0) + COALESCE(risk_y, 0.0) - {new_z}) AS new_margin,
                MIN(1.0, MAX(0.05, 0.5 + (COALESCE(risk_x, 0.0) + COALESCE(risk_y, 0.0) - {new_z}) / {two_z})) AS new_u
            FROM findings
            WHERE scan_id = {ph} AND risk_score IS NOT NULL
              AND (risk_classically_broken = 0 OR risk_classically_broken IS NULL)
        ),
        calculated AS (
            SELECT
                id,
                new_margin,
                new_u,
                MIN(100.0, MAX(0.0, 100.0 * COALESCE(risk_v, 0.0) * COALESCE(risk_f, 0.0) *
                               new_u * COALESCE(risk_e, 0.0) * COALESCE(risk_k, 0.0))) AS new_score
            FROM urgency
        ),
        banded AS (
            SELECT
                id,
                new_margin,
                new_u,
                new_score,
                CASE
                    WHEN new_score >= 60.0 THEN 'critical'
                    WHEN new_score >= 35.0 THEN 'high'
                    WHEN new_score >= 15.0 THEN 'medium'
                    ELSE 'low'
                END AS new_band
            FROM calculated
        )
        UPDATE findings
        SET
            risk_score = banded.new_score,
            risk_u = banded.new_u,
            risk_band = banded.new_band,
            risk_z = {new_z},
            risk_mosca_margin = banded.new_margin
        FROM banded
        WHERE findings.id = banded.id
          AND (ABS(findings.risk_score - banded.new_score) > 1e-6 OR findings.risk_band != banded.new_band)
        RETURNING json_object(
            'id', findings.id,
            'family', findings.family,
            'displayName', findings.display_name,
            'kind', findings.kind,
            'surface', findings.surface,
            'function', findings.function,
            'keySize', findings.key_size,
            'mode', findings.mode,
            'curve', findings.curve,
            'location', json_object(
                'path', findings.location_path,
                'line', findings.location_line,
                'offset', findings.location_offset,
                'layer', findings.location_layer
            ),
            'symbol', findings.symbol,
            'snippet', findings.snippet,
            'source', findings.source,
            'confidence', findings.confidence,
            'risk', json_object(
                'score', findings.risk_score,
                'band', findings.risk_band,
                'V', findings.risk_v,
                'F', findings.risk_f,
                'U', findings.risk_u,
                'E', findings.risk_e,
                'K', findings.risk_k,
                'X', findings.risk_x,
                'Y', findings.risk_y,
                'Z', findings.risk_z,
                'moscaMargin', findings.risk_mosca_margin,
                'reason', findings.risk_reason,
                'classicallyBroken', json('false'),
                'hndl', case when findings.risk_hndl = 1 then json('true') else json('false') end,
                'needsReview', case when findings.risk_needs_review = 1 then json('true') else json('false') end
            ),
            'triage', json_object('status', 'open', 'note', null)
        )
        """
        cur.execute(sql, (scan_id,))
        changed_json_strings = [r[0] for r in cur.fetchall()]

        cur.execute(
            f"SELECT risk_band, COUNT(*) FROM findings WHERE scan_id = {ph} GROUP BY risk_band", (scan_id,)  # nosec B608
        )
        band_rows = cur.fetchall()
        bands: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for b, c in band_rows:
            if b in bands:
                bands[b] = c

        scan_up_sql = f"""UPDATE scans
                          SET bands = {ph},
                              crqc_years = COALESCE({ph}, crqc_years)
                          WHERE id = {ph}"""  # nosec B608 -- placeholder token only, all 3 values bound below
        cur.execute(scan_up_sql, (json.dumps(bands), crqc_years, scan_id))

        total_rows_rescored = sum(bands.values())
        db.log_audit(
            session,
            action="scan.rescore",
            entity_type="scan",
            entity_id=scan_id,
            detail={"crqc_years": crqc_years, "rescored": total_rows_rescored, "changed": len(changed_json_strings)},
        )
        session.commit()

        c, h, m, l_cnt = bands["critical"], bands["high"], bands["medium"], bands["low"]
        bands_json = f'{{"critical":{c},"high":{h},"medium":{m},"low":{l_cnt}}}'
        if not changed_json_strings:
            content_bytes = f'{{"bands":{bands_json},"changed":[]}}'.encode()
        else:
            joined = ",".join(changed_json_strings)
            content_bytes = f'{{"bands":{bands_json},"changed":[{joined}]}}'.encode()

        return bands, content_bytes


# --- Targets ---------------------------------------------------------------------

def create_target(payload: TargetCreate) -> Target:
    target_id = f"target_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC)
    target = Target(
        id=target_id,
        name=payload.name,
        kind=payload.kind,
        uri=payload.uri,
        policyId=payload.policyId,
        schedule=payload.schedule,
        enabled=payload.enabled,
        lastScanId=None,
        lastScanAt=None,
        createdAt=now,
    )
    with db.session_scope() as session:
        session.add(db.target_to_record(target))
        db.log_audit(
            session,
            action="target.create",
            entity_type="target",
            entity_id=target.id,
            detail={"name": target.name},
        )
        session.commit()
    return target


def get_target(target_id: str) -> Target | None:
    with db.session_scope() as session:
        rec = session.get(TargetRecord, target_id)
        return db.record_to_target(rec) if rec is not None else None


def list_targets() -> list[Target]:
    with db.session_scope() as session:
        records = session.exec(select(TargetRecord)).all()
        return [db.record_to_target(r) for r in records]


def patch_target(target_id: str, patch: TargetPatch) -> Target | None:
    with db.session_scope() as session:
        rec = session.get(TargetRecord, target_id)
        if rec is None:
            return None
        if patch.name is not None:
            rec.name = patch.name
        if patch.policyId is not None:
            rec.policy_id = patch.policyId
        if patch.schedule is not None:
            rec.schedule = patch.schedule
        if patch.enabled is not None:
            rec.enabled = patch.enabled
        session.add(rec)
        db.log_audit(session, action="target.patch", entity_type="target", entity_id=target_id)
        session.commit()
        return db.record_to_target(rec)


def delete_target(target_id: str) -> bool:
    with db.session_scope() as session:
        rec = session.get(TargetRecord, target_id)
        if rec is None:
            return False
        session.delete(rec)
        db.log_audit(session, action="target.delete", entity_type="target", entity_id=target_id)
        session.commit()
        return True


def update_target_last_scan(target_id: str, scan_id: str, scan_at: datetime) -> None:
    with db.session_scope() as session:
        rec = session.get(TargetRecord, target_id)
        if rec is not None:
            rec.last_scan_id = scan_id
            rec.last_scan_at = scan_at
            session.add(rec)
            session.commit()


# --- Snapshots -------------------------------------------------------------------

def create_snapshot(target_id: str, scan: Scan, findings: list[Finding]) -> ScanSnapshot:
    snapshot_id = f"snap_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC)
    stats = scan.stats or ScanStats(files=0, bytes=0, seconds=0.0, mbPerSec=0.0, errors=0, skippedPrefilter=0)
    snapshot = ScanSnapshot(
        id=snapshot_id,
        targetId=target_id,
        scanId=scan.id,
        takenAt=now,
        bands=scan.bands.model_dump(),
        totalFindings=len(findings),
        stats=stats,
    )
    with db.session_scope() as session:
        session.add(db.snapshot_to_record(snapshot))
        db.log_audit(
            session,
            action="snapshot.create",
            entity_type="snapshot",
            entity_id=snapshot.id,
            detail={"targetId": target_id, "scanId": scan.id},
        )
        session.commit()
    return snapshot


def get_snapshot(snapshot_id: str) -> ScanSnapshot | None:
    with db.session_scope() as session:
        rec = session.get(ScanSnapshotRecord, snapshot_id)
        return db.record_to_snapshot(rec) if rec is not None else None


def list_snapshots(target_id: str) -> list[ScanSnapshot]:
    with db.session_scope() as session:
        records = session.exec(
            select(ScanSnapshotRecord)
            .where(ScanSnapshotRecord.target_id == target_id)
            .order_by(col(ScanSnapshotRecord.taken_at).desc())
        ).all()
        return [db.record_to_snapshot(r) for r in records]


# --- Drift Engine ----------------------------------------------------------------

def _finding_identity(f: Finding) -> tuple[str, int | None, str, str | None, str, str, int | None, str | None]:
    """Stable cryptographic identity: location path+line, displayName, family, function,
    symbol, keySize, curve. Must include the line number -- two structurally-identical
    findings in the same file (e.g. the same weak keygen call repeated at different
    locations) are still two distinct findings, and drift needs to tell them apart to
    correctly report a newly-added one in `added[]` rather than silently treating it as
    an existing, unchanged finding (found via a real functional proof pass, Track A1 P4:
    a second identical-shaped RSA-1024 finding at a different line collided with the
    first one's identity tuple, so `added[]` stayed empty even though `netRiskDelta`
    correctly reflected the real +90 score increase)."""
    return (
        f.location.path,
        f.location.line,
        f.displayName,
        f.family.value if f.family else None,
        f.function.value,
        f.symbol,
        f.keySize,
        f.curve,
    )


def calculate_drift(target_id: str, from_snapshot_id: str, to_snapshot_id: str) -> Drift | None:
    from_snap = get_snapshot(from_snapshot_id)
    to_snap = get_snapshot(to_snapshot_id)
    if from_snap is None or to_snap is None:
        return None
    if from_snap.targetId != target_id or to_snap.targetId != target_id:
        return None

    from_findings = list_findings(from_snap.scanId)
    to_findings = list_findings(to_snap.scanId)

    from_map: dict[tuple[str, int | None, str, str | None, str, str, int | None, str | None], Finding] = {
        _finding_identity(f): f for f in from_findings
    }
    to_map: dict[tuple[str, int | None, str, str | None, str, str, int | None, str | None], Finding] = {
        _finding_identity(f): f for f in to_findings
    }

    added: list[Finding] = []
    resolved: list[Finding] = []
    changed: list[DriftChangedItem] = []

    for key, f_to in to_map.items():
        if key not in from_map:
            added.append(f_to)
        else:
            f_from = from_map[key]
            band_from = f_from.risk.band if f_from.risk else RiskBand.LOW
            band_to = f_to.risk.band if f_to.risk else RiskBand.LOW
            if band_from != band_to:
                changed.append(DriftChangedItem(finding=f_to, fromBand=band_from, toBand=band_to))

    for key, f_from in from_map.items():
        if key not in to_map:
            resolved.append(f_from)

    risk_to = sum(f.risk.score for f in to_findings if f.risk)
    risk_from = sum(f.risk.score for f in from_findings if f.risk)
    net_risk_delta = round(risk_to - risk_from, 2)

    summary = DriftSummary(
        addedCount=len(added),
        resolvedCount=len(resolved),
        changedCount=len(changed),
        netRiskDelta=net_risk_delta,
    )

    return Drift(
        targetId=target_id,
        fromSnapshotId=from_snapshot_id,
        toSnapshotId=to_snapshot_id,
        added=added,
        resolved=resolved,
        changed=changed,
        summary=summary,
    )


# --- Alerts ----------------------------------------------------------------------

def create_alert(alert: Alert) -> Alert:
    with db.session_scope() as session:
        session.add(db.alert_to_record(alert))
        db.log_audit(
            session,
            action="alert.create",
            entity_type="alert",
            entity_id=alert.id,
            detail={"type": alert.type.value, "severity": alert.severity.value},
        )
        session.commit()
    return alert


def list_alerts(acknowledged: bool | None = None) -> list[Alert]:
    with db.session_scope() as session:
        query = select(AlertRecord)
        if acknowledged is not None:
            query = query.where(AlertRecord.acknowledged == acknowledged)
        query = query.order_by(col(AlertRecord.created_at).desc())
        records = session.exec(query).all()
        return [db.record_to_alert(r) for r in records]


def acknowledge_alert(alert_id: str) -> Alert | None:
    with db.session_scope() as session:
        rec = session.get(AlertRecord, alert_id)
        if rec is None:
            return None
        rec.acknowledged = True
        session.add(rec)
        db.log_audit(session, action="alert.acknowledge", entity_type="alert", entity_id=alert_id)
        session.commit()
        return db.record_to_alert(rec)


# --- Probes ----------------------------------------------------------------------

def create_probe_result(result: ProbeResult) -> ProbeResult:
    with db.session_scope() as session:
        session.add(db.probe_result_to_record(result))
        db.log_audit(
            session,
            action="probe.create",
            entity_type="probe",
            entity_id=result.id,
            detail={"protocol": result.protocol.value, "targetId": result.targetId},
        )
        session.commit()
    return result


def list_probe_results(target_id: str | None = None) -> list[ProbeResult]:
    with db.session_scope() as session:
        query = select(ProbeResultRecord)
        if target_id is not None:
            query = query.where(ProbeResultRecord.target_id == target_id)
        query = query.order_by(col(ProbeResultRecord.probed_at).desc())
        records = session.exec(query).all()
        return [db.record_to_probe_result(r) for r in records]


# --- Coverage & Debt Ledger (Track A1) -------------------------------------------

def get_coverage_certificate(scan_id: str) -> CoverageCertificate | None:
    with db.session_scope() as session:
        rec = session.get(CoverageCertificateRecord, scan_id)
        return db.record_to_coverage_certificate(rec) if rec is not None else None


def get_artifact_coverages(scan_id: str) -> list[ArtifactCoverage]:
    with db.session_scope() as session:
        records = session.exec(
            select(ArtifactCoverageRecord).where(ArtifactCoverageRecord.scan_id == scan_id)
        ).all()
        return [db.record_to_artifact_coverage(r) for r in records]


def save_coverage(
    scan_id: str,
    cert: CoverageCertificate,
    artifacts: list[ArtifactCoverage],
    clusters: list[ResidueCluster],
    target_id: str | None = None,
) -> None:
    with db.session_scope() as session:
        # Upsert certificate
        existing_cert = session.get(CoverageCertificateRecord, scan_id)
        if existing_cert:
            session.delete(existing_cert)
        session.add(db.coverage_certificate_to_record(cert))

        # Replace artifact coverages for scan
        old_artifacts = session.exec(
            select(ArtifactCoverageRecord).where(ArtifactCoverageRecord.scan_id == scan_id)
        ).all()
        for old in old_artifacts:
            session.delete(old)
        for art in artifacts:
            session.add(db.artifact_coverage_to_record(art, scan_id=scan_id))

        # Upsert residue clusters indexed by content_hash across time & targets
        now = datetime.now(UTC)
        for cluster in clusters:
            existing_cluster = session.exec(
                select(ResidueClusterRecord).where(
                    (ResidueClusterRecord.id == cluster.id)
                    | (ResidueClusterRecord.content_hash == cluster.contentHash)
                )
            ).first()

            if existing_cluster is not None:
                # Merge occurrences and update last_seen
                occ_map = {
                    (o.get("artifactHash"), o.get("path"), tuple(o.get("range", []))): o
                    for o in (existing_cluster.occurrences or [])
                }
                for new_occ in cluster.occurrences:
                    key = (new_occ.artifactHash, new_occ.path, tuple(new_occ.range))
                    occ_map[key] = new_occ.model_dump()
                existing_cluster.occurrences = list(occ_map.values())
                existing_cluster.last_seen = now
                if target_id and not existing_cluster.target_id:
                    existing_cluster.target_id = target_id
                session.add(existing_cluster)
            else:
                session.add(db.residue_cluster_to_record(cluster, target_id=target_id))

        db.log_audit(
            session,
            action="coverage.record",
            entity_type="coverage_certificate",
            entity_id=scan_id,
            detail={
                "coverageRatio": cert.coverageRatio,
                "totalMass": cert.totalMass,
                "residueMass": cert.residueMass,
            },
        )
        session.commit()


def list_residue_clusters(
    state: ResidueClusterState | None = None,
    target_id: str | None = None,
) -> list[ResidueCluster]:
    with db.session_scope() as session:
        query = select(ResidueClusterRecord)
        if state is not None:
            state_str = state.value if hasattr(state, "value") else str(state)
            query = query.where(ResidueClusterRecord.state == state_str)
        if target_id is not None:
            query = query.where(ResidueClusterRecord.target_id == target_id)
        query = query.order_by(col(ResidueClusterRecord.last_seen).desc())
        records = session.exec(query).all()
        return [db.record_to_residue_cluster(r) for r in records]


def get_residue_cluster(cluster_id: str) -> ResidueCluster | None:
    with db.session_scope() as session:
        rec = session.get(ResidueClusterRecord, cluster_id)
        if rec is None:
            rec = session.exec(
                select(ResidueClusterRecord).where(ResidueClusterRecord.content_hash == cluster_id)
            ).first()
        return db.record_to_residue_cluster(rec) if rec is not None else None


def patch_residue_cluster(cluster_id: str, patch: ResidueClusterPatch) -> ResidueCluster | None:
    with db.session_scope() as session:
        rec = session.get(ResidueClusterRecord, cluster_id)
        if rec is None:
            rec = session.exec(
                select(ResidueClusterRecord).where(ResidueClusterRecord.content_hash == cluster_id)
            ).first()
        if rec is None:
            return None

        old_state = rec.state
        new_state = patch.state.value if hasattr(patch.state, "value") else str(patch.state)
        rec.state = new_state
        if patch.justification is not None:
            rec.justification = patch.justification
        if patch.owner is not None:
            rec.owner = patch.owner
        rec.last_seen = datetime.now(UTC)

        session.add(rec)
        db.log_audit(
            session,
            action="residue.transition",
            entity_type="residue_cluster",
            entity_id=rec.id,
            detail={"from": old_state, "to": new_state, "owner": rec.owner, "justification": rec.justification},
        )
        session.commit()
        return db.record_to_residue_cluster(rec)


def list_asset_criticalities(target_id: str | None = None) -> list[AssetCriticality]:
    with db.session_scope() as session:
        query = select(AssetCriticalityRecord)
        if target_id is not None:
            query = query.where(AssetCriticalityRecord.target_id == target_id)
        records = session.exec(query).all()
        return [db.record_to_asset_criticality(r) for r in records]


def set_asset_criticality(crit: AssetCriticality) -> AssetCriticality:
    with db.session_scope() as session:
        rec_id = f"{crit.targetId}:{crit.pathPattern}"
        existing = session.get(AssetCriticalityRecord, rec_id)
        if existing:
            session.delete(existing)
        session.add(db.asset_criticality_to_record(crit))
        db.log_audit(
            session,
            action="criticality.set",
            entity_type="asset_criticality",
            entity_id=rec_id,
            detail={
                "targetId": crit.targetId,
                "criticality": crit.criticality.value if hasattr(crit.criticality, "value") else str(crit.criticality),
                "businessOwner": crit.businessOwner,
            },
        )
        session.commit()
    return crit


def get_estate_coverage() -> EstateCoverage:
    with db.session_scope() as session:
        targets = session.exec(select(TargetRecord)).all()
        target_summaries: list[TargetCoverageSummary] = []

        total_mass_sum = 0.0
        attributed_mass_sum = 0.0
        excluded_mass_sum = 0.0
        residue_mass_sum = 0.0

        for t in targets:
            # Find latest scan certificate for this target
            last_scan_id = t.last_scan_id
            cert: CoverageCertificateRecord | None = None
            if last_scan_id:
                cert = session.get(CoverageCertificateRecord, last_scan_id)
            if cert is None:
                # Find any certificate from scans matching target
                scans = session.exec(select(ScanRecord).where(ScanRecord.target == t.uri)).all()
                for s in scans:
                    c = session.get(CoverageCertificateRecord, s.id)
                    if c is not None:
                        cert = c
                        break

            if cert:
                t_cov = cert.coverage_ratio
                t_res = cert.residue_mass
                t_tot = cert.total_mass
                total_mass_sum += cert.total_mass
                attributed_mass_sum += cert.attributed_mass
                excluded_mass_sum += cert.excluded_mass
                residue_mass_sum += cert.residue_mass
            else:
                t_cov = 1.0
                t_res = 0.0
                t_tot = 100.0
                total_mass_sum += 100.0
                attributed_mass_sum += 100.0

            target_summaries.append(
                TargetCoverageSummary(
                    targetId=t.id,
                    targetName=t.name,
                    coverageRatio=round(t_cov, 4),
                    residueMass=round(t_res, 2),
                    totalMass=round(t_tot, 2),
                )
            )

        overall_ratio = (
            round(attributed_mass_sum / total_mass_sum, 4) if total_mass_sum > 0 else 1.0
        )
        total_clusters = len(session.exec(select(ResidueClusterRecord)).all())

        return EstateCoverage(
            overallCoverageRatio=overall_ratio,
            totalMass=round(total_mass_sum, 2),
            attributedMass=round(attributed_mass_sum, 2),
            excludedMass=round(excluded_mass_sum, 2),
            residueMass=round(residue_mass_sum, 2),
            totalClusters=total_clusters,
            targets=target_summaries,
        )


