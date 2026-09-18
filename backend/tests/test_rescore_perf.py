from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.db import session_scope
from api.db_models import FindingRecord, ScanRecord
from engine.risk import rescore


@dataclass(frozen=True)
class Archetype:
    display_name: str
    family: str
    kind: str
    surface: str
    function: str
    v: float
    f: float
    e: float
    k: float
    x: float
    y: float
    broken: bool


@pytest.fixture
def seeded_10k_scan(client: TestClient) -> str:
    scan_id = "scan_perf_10k"
    now = datetime.now(UTC)

    # 10,000 findings across 5 archetypes:
    # 1. 2,000 RSA-2048 (quantum-sensitive, changes with Z)
    # 2. 2,000 SHA-1 (classically-broken, U=1 invariant, NEVER changes with Z)
    # 3. 2,000 AES-128 (quantum-sensitive, changes with Z)
    # 4. 2,000 ML-KEM-768 (quantum-safe, changes with Z)
    # 5. 2,000 3DES (classically-broken, U=1 invariant, NEVER changes with Z)
    archetypes = [
        Archetype(
            display_name="RSA-2048",
            family="RSA",
            kind="algorithm",
            surface="source",
            function="encrypt",
            v=1.0,
            f=0.9,
            e=0.9,
            k=0.8,
            x=10.0,
            y=5.0,
            broken=False,
        ),
        Archetype(
            display_name="SHA-1",
            family="SHA-1",
            kind="algorithm",
            surface="source",
            function="digest",
            v=1.0,
            f=0.9,
            e=0.9,
            k=0.8,
            x=5.0,
            y=3.0,
            broken=True,
        ),
        Archetype(
            display_name="AES-128",
            family="AES",
            kind="algorithm",
            surface="source",
            function="encrypt",
            v=0.6,
            f=0.8,
            e=0.7,
            k=0.7,
            x=8.0,
            y=4.0,
            broken=False,
        ),
        Archetype(
            display_name="ML-KEM-768",
            family="ML-KEM",
            kind="algorithm",
            surface="source",
            function="keygen",
            v=0.1,
            f=0.2,
            e=0.3,
            k=0.3,
            x=3.0,
            y=2.0,
            broken=False,
        ),
        Archetype(
            display_name="3DES",
            family="3DES",
            kind="algorithm",
            surface="source",
            function="encrypt",
            v=1.0,
            f=0.8,
            e=0.8,
            k=0.8,
            x=5.0,
            y=2.0,
            broken=True,
        ),
    ]

    records: list[FindingRecord] = []
    initial_z = 10.0
    counter = 0

    for arch in archetypes:
        score, u, band = rescore(
            v=arch.v,
            f=arch.f,
            e=arch.e,
            k=arch.k,
            x=arch.x,
            y=arch.y,
            z=initial_z,
            classically_broken=arch.broken,
        )
        for i in range(2000):
            counter += 1
            f_id = f"finding_perf_{counter:05d}"
            records.append(
                FindingRecord(
                    id=f_id,
                    scan_id=scan_id,
                    kind=arch.kind,
                    surface=arch.surface,
                    family=arch.family,
                    display_name=arch.display_name,
                    key_size=None,
                    mode=None,
                    curve=None,
                    function=arch.function,
                    location_path=f"src/subsystem_{i % 50}/crypto.py",
                    location_line=i + 1,
                    location_offset=None,
                    location_layer=None,
                    symbol=f"CRYPTO_SYM_{counter}",
                    snippet="crypto_call()",
                    source="ast",
                    confidence=0.95,
                    risk_score=score,
                    risk_band=band,
                    risk_v=arch.v,
                    risk_f=arch.f,
                    risk_u=u,
                    risk_e=arch.e,
                    risk_k=arch.k,
                    risk_x=arch.x,
                    risk_y=arch.y,
                    risk_z=initial_z,
                    risk_mosca_margin=arch.x + arch.y - initial_z,
                    risk_reason="Performance test seeded finding",
                    risk_classically_broken=arch.broken,
                    risk_hndl=False,
                    risk_needs_review=False,
                    recommendation=None,
                    triage_status="open",
                    triage_note=None,
                )
            )

    with session_scope() as session:
        # Create scan record
        scan = ScanRecord(
            id=scan_id,
            status="done",
            target="/test/perf",
            policy_id="default",
            crqc_years=int(initial_z),
            started_at=now,
            finished_at=now,
            bands={},
        )
        session.merge(scan)
        # Bulk add 10,000 findings
        session.add_all(records)
        session.commit()

    return scan_id


def test_rescore_10000_findings_performance(client: TestClient, seeded_10k_scan: str) -> None:
    """Brief SLA: rescore 10,000 findings from stored factors in <200ms, no re-detection."""
    scan_id = seeded_10k_scan

    # Warm up TestClient / ASGI worker thread
    client.get(f"/api/v1/scans/{scan_id}")

    # Rescore with Z = 5 (lowering horizon increases urgency for quantum-sensitive assets)
    import gc
    gc.collect()
    gc.disable()
    try:
        start = time.perf_counter()
        resp = client.post(f"/api/v1/scans/{scan_id}/rescore", json={"crqcYears": 5})
        elapsed_sec = time.perf_counter() - start
    finally:
        gc.enable()

    assert resp.status_code == 200
    body: dict[str, Any] = resp.json()

    # 1. Performance SLA verification: < 200 ms
    print(f"\n[PERF RESULT] 10,000 findings rescore time: {elapsed_sec * 1000:.2f} ms")
    assert elapsed_sec < 0.200, f"Rescore took {elapsed_sec * 1000:.2f}ms, exceeding 200ms budget!"

    # 2. Mathematical invariant verification:
    # 4,000 findings are classically broken (2,000 SHA-1 + 2,000 3DES) and must NEVER change.
    # 6,000 findings are quantum sensitive (2,000 RSA-2048 + 2,000 AES-128 + 2,000 ML-KEM-768)
    # and their score must change when Z decreases from 10 to 5.
    changed = body["changed"]
    assert len(changed) == 6000

    changed_families = {c["family"] for c in changed}
    assert "SHA-1" not in changed_families, "Classically broken SHA-1 changed score on Z change!"
    assert "3DES" not in changed_families, "Classically broken 3DES changed score on Z change!"
    assert "RSA" in changed_families
    assert "AES" in changed_families
    assert "ML-KEM" in changed_families

    # 3. Verify total bands count sums to 10,000
    bands = body["bands"]
    total_in_bands = sum(bands.values())
    assert total_in_bands == 10000
