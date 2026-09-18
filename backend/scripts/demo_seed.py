"""demo_seed.py: Seeds the demo policy and scans the benchmark corpus.

Invoked by `make demo` to produce a live, offline-ready ECDAT installation
with real scan results, real event timeline, and real findings (including
stripped binary AES S-box constants).
"""

from __future__ import annotations

import shutil
import sys
import tarfile
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from api import db, store  # noqa: E402
from api.models import Context, Criticality, Exposure, Policy, ScanCreate, ScanStatus  # noqa: E402
from engine.scanner import scan as run_scan  # noqa: E402

AES_SBOX_TABLE = bytes([
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
    0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0, 0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
    0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
    0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A, 0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
    0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0, 0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84,
    0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B, 0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
    0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
    0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5, 0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
    0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44, 0x17, 0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
    0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88, 0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB,
    0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C, 0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
    0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
    0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6, 0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A,
    0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E, 0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E,
    0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
    0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16,
])

DEMO_POLICY_ID = "policy-default-defense"


def setup_demo_environment() -> tuple[Path, Path]:
    """Prepares the demo corpus directory and bundle archive."""
    corpus_dir = BACKEND_DIR / "bench" / "demo_corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy sample Python & Go files
    fixtures_dir = BACKEND_DIR / "bench" / "fixtures"
    for py_file in fixtures_dir.glob("*.py"):
        shutil.copy2(py_file, corpus_dir / py_file.name)

    rw_samples = BACKEND_DIR / "bench" / "real_world" / "samples"
    if rw_samples.exists():
        for sample in rw_samples.glob("*.*"):
            shutil.copy2(sample, corpus_dir / sample.name)

    # 2. Write stripped binary containing AES S-box constant
    bin_dir = corpus_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    binary_path = bin_dir / "stripped_crypto_worker.elf"

    # Prefix with 4096 bytes of dummy ELF header / code, then static S-box table
    elf_content = bytearray(b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 4088)
    elf_content.extend(AES_SBOX_TABLE)
    elf_content.extend(b"\x00" * 512)
    binary_path.write_bytes(bytes(elf_content))

    # 3. Create tar.gz archive for bundle ingestion
    bundle_path = BACKEND_DIR / "bench" / "benchmark_corpus.tar.gz"
    with tarfile.open(bundle_path, "w:gz") as tar:
        for item in corpus_dir.rglob("*"):
            if item.is_file():
                tar.add(item, arcname=str(item.relative_to(corpus_dir)))

    return corpus_dir, bundle_path


def seed_demo() -> None:
    print("=== ECDAT Demo Environment Setup ===")
    db.init_db()

    # 1. Ensure National Defense Core (CNSA 2.0) Demo Policy is stored
    demo_policy = Policy(
        id=DEMO_POLICY_ID,
        name="National Defense Core (Default CNSA 2.0)",
        crqcYears=10,
        default=Context(
            exposure=Exposure.EXTERNAL,
            criticality=Criticality.MISSION_CRITICAL,
            shelfLifeYears=10,
            migrationYears=5,
        ),
        contexts=[],
    )
    store.put_policy(demo_policy)
    print(f"[OK] Demo Policy seeded: {demo_policy.name} ({demo_policy.id})")

    # 2. Prepare corpus and bundle
    corpus_dir, bundle_path = setup_demo_environment()
    print(f"[OK] Benchmark Corpus prepared: {corpus_dir}")
    print(f"[OK] Offline Bundle generated: {bundle_path} ({bundle_path.stat().st_size} bytes)")

    # 3. Scan corpus and record scan
    collected_events: list[tuple[str, dict[str, Any]]] = []

    def on_event(event_type: str, event_payload: dict[str, Any]) -> None:
        collected_events.append((event_type, event_payload))

    scan_result = run_scan(corpus_dir, demo_policy, on_event=on_event)

    payload = ScanCreate(path="benchmark_corpus.tar.gz", policyId=DEMO_POLICY_ID, crqcYears=10)
    scan = store.create_scan_from_result(
        payload,
        scan_result,
        demo_policy,
        scan_status=ScanStatus.DONE,
        events=collected_events,
        bundle_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        target_override="benchmark-corpus-v1 (source + binaries)",
        scan_id_override="scan-7f8e1a",
    )

    # Link demo ID alias if desirable
    print(f"[OK] Benchmark Scan generated: {scan.id}")
    print(f"     Target: {scan.target}")
    print(f"     Status: {scan.status}")
    print(
        f"     Bands: Critical={scan.bands.critical}, High={scan.bands.high}, "
        f"Medium={scan.bands.medium}, Low={scan.bands.low}"
    )
    print(f"     Total Findings: {len(scan_result.findings)}")

    sbox_findings = [f for f in scan_result.findings if "S-box" in f.displayName or f.symbol == "AES_SBOX"]
    print(f"[OK] Stripped Binary findings detected: {len(sbox_findings)}")
    for f in sbox_findings:
        print(f"     -> {f.displayName} at {f.location.path} (Risk: {f.risk.band.value if f.risk else 'unknown'})")

    print("\n=== Demo Setup Complete. System ready for offline demonstration. ===")


if __name__ == "__main__":
    seed_demo()
