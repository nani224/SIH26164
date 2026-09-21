"""Load test script for ECDAT Crypto Mass Conservation (CMC) endpoints (Milestone M7).

Benchmarks latency against a live server for:
- 10k findings scan
- Coverage certificate retrieval (budget: p95 < 150ms)
- Artifact coverage retrieval (budget: p95 < 150ms)
- Residue cluster queries (budget: p95 < 200ms)
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from typing import Any

import httpx

# Ensure backend root is in sys.path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from api import db, store, stub_data  # noqa: E402
from api.models import (  # noqa: E402
    ArtifactCoverage,
    CoverageCertificate,
    Finding,
    ResidueCluster,
    ResidueClusterState,
    ScanCreate,
    TargetCreate,
    TargetKind,
)
from engine.models import ScanResult  # noqa: E402


def seed_10k_data(scan_id: str = "scan_load_10k") -> str:
    """Seed 10,000 findings, coverage certificate, 500 artifacts, and 50 residue clusters."""
    print(f"[*] Initializing DB and seeding 10,000 findings for {scan_id}...")
    db.init_db()

    target = store.create_target(
        TargetCreate(
            name="Load Test Target",
            kind=TargetKind.REPO,
            uri="https://github.com/ecdat/load-test",
            policyId="policy_default",
            schedule="0 0 * * *",
        )
    )
    target_id = target.id

    now = datetime.now(UTC)

    print("[*] Generating 10,000 finding objects from base finding...")
    base_finding = stub_data.list_findings()[0]
    findings: list[Finding] = []
    for i in range(10_000):
        findings.append(
            base_finding.model_copy(
                update={
                    "id": f"f_load_{i:05d}",
                    "displayName": f"Finding {i}",
                }
            )
        )

    scan_create = ScanCreate(path="src/load_test_project")
    policy = store.resolve_policy(scan_create)
    scan_result = ScanResult(findings=findings)

    print("[*] Creating scan with 10,000 findings via create_scan_from_result...")
    store.create_scan_from_result(
        scan_create,
        scan_result,
        policy,
        scan_id_override=scan_id,
        target_override=target_id,
    )

    print("[*] Generating coverage certificate and 500 artifact coverages...")
    cert = CoverageCertificate(
        scanId=scan_id,
        artifactCount=500,
        totalMass=25000.0,
        attributedMass=23000.0,
        excludedMass=1000.0,
        residueMass=1000.0,
        coverageRatio=0.92,
        residueClusterCount=50,
        computedAt=now,
    )

    artifacts: list[ArtifactCoverage] = []
    for i in range(500):
        h = hashlib.sha256(f"art_{i}".encode()).hexdigest()
        artifacts.append(
            ArtifactCoverage(
                artifactHash=h,
                path=f"src/module_{i}/file.py",
                totalMass=50.0,
                attributed=46.0,
                excluded=2.0,
                residue=2.0,
                coverageRatio=0.92,
            )
        )

    print("[*] Generating 50 residue clusters...")
    clusters: list[ResidueCluster] = []
    for i in range(50):
        ch = hashlib.sha256(f"res_cluster_{i}".encode()).hexdigest()
        state = (
            ResidueClusterState.OPEN
            if i % 3 == 0
            else (ResidueClusterState.ACCEPTED if i % 3 == 1 else ResidueClusterState.EXCLUDED)
        )
        clusters.append(
            ResidueCluster(
                id=f"res_cluster_{i:03d}",
                contentHash=ch,
                signalTypes=["constant_pool", "entropy"],
                magnitude=20.0 + (i * 1.5),
                occurrences=[],
                state=state,
                justification="Known legacy crypto blob" if state != ResidueClusterState.OPEN else None,
                owner="crypto-team@ecdat.local" if state != ResidueClusterState.OPEN else None,
                firstSeen=now,
                lastSeen=now,
            )
        )

    store.save_coverage(
        scan_id,
        cert,
        artifacts,
        clusters,
        target_id=target_id,
    )
    print("[+] Seeding complete.")
    return scan_id


def calculate_percentiles(times_ms: list[float]) -> dict[str, float]:
    sorted_times = sorted(times_ms)
    n = len(sorted_times)

    def p(pct: float) -> float:
        idx = int(pct * n / 100.0)
        return sorted_times[min(idx, n - 1)]

    return {
        "min": round(sorted_times[0], 2),
        "p50": round(p(50), 2),
        "p90": round(p(90), 2),
        "p95": round(p(95), 2),
        "p99": round(p(99), 2),
        "max": round(sorted_times[-1], 2),
    }


def run_load_benchmarks(base_url: str, rounds: int = 50) -> bool:
    print("\n=======================================================")
    print("   ECDAT LOAD TEST SUITE (10k Findings + Coverage)    ")
    print("=======================================================")
    print(f"Base URL: {base_url} | Iterations per endpoint: {rounds}\n")

    endpoints = [
        ("GET /scans/{id}/coverage", "/api/v1/scans/scan_load_10k/coverage", 150.0),
        ("GET /scans/{id}/coverage/artifacts", "/api/v1/scans/scan_load_10k/coverage/artifacts", 150.0),
        ("GET /residue", "/api/v1/residue", 200.0),
        ("GET /residue?state=open", "/api/v1/residue?state=open", 200.0),
        ("GET /residue/{id}", "/api/v1/residue/res_cluster_001", 200.0),
    ]

    all_passed = True
    results: list[dict[str, Any]] = []

    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        # Warm up
        for _, path, _ in endpoints:
            r = client.get(path)
            assert r.status_code == 200, f"Warmup failed for {path}: {r.status_code} {r.text}"

        for name, path, budget_p95 in endpoints:
            latencies: list[float] = []
            for _ in range(rounds):
                t0 = time.perf_counter()
                r = client.get(path)
                t1 = time.perf_counter()
                assert r.status_code == 200, f"Request failed: {r.status_code}"
                latencies.append((t1 - t0) * 1000.0)

            stats = calculate_percentiles(latencies)
            passed = stats["p95"] <= budget_p95
            if not passed:
                all_passed = False

            results.append(
                {
                    "name": name,
                    "budget": budget_p95,
                    "stats": stats,
                    "passed": passed,
                }
            )

    header = (
        f"{'Endpoint':<36} | {'Budget (p95)':<12} | {'p50':<8} | "
        f"{'p90':<8} | {'p95':<8} | {'p99':<8} | {'Status'}"
    )
    print(header)
    print("-" * 95)
    for res in results:
        s = res["stats"]
        status_str = "PASS" if res["passed"] else "FAIL"
        row = (
            f"{res['name']:<36} | {res['budget']:<12.1f} | {s['p50']:<8.2f} | "
            f"{s['p90']:<8.2f} | {s['p95']:<8.2f} | {s['p99']:<8.2f} | {status_str}"
        )
        print(row)
    print("=" * 95)

    return all_passed


def main() -> None:
    port = 8025
    base_url = f"http://127.0.0.1:{port}"

    # 1. Seed data
    seed_10k_data()

    # 2. Boot server
    print(f"[*] Starting background uvicorn server on port {port}...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--port", str(port), "--host", "127.0.0.1"],
        cwd=BACKEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        # Wait for server to become healthy
        healthy = False
        for _ in range(30):
            try:
                r = httpx.get(f"{base_url}/api/v1/health", timeout=1.0)
                if r.status_code == 200:
                    healthy = True
                    break
            except Exception:
                time.sleep(0.3)

        if not healthy:
            print("[-] Error: Server failed to start or respond to health check.")
            sys.exit(1)

        print("[+] Server healthy. Running load benchmarks...")
        success = run_load_benchmarks(base_url, rounds=50)

        if not success:
            print("[-] Performance budget violation detected!")
            sys.exit(1)
        else:
            print("[+] All load benchmarks satisfied performance budgets.")

    finally:
        print("[*] Terminating uvicorn server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
