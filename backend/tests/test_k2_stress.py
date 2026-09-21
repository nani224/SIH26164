"""CMC K2 Specificity Stress Test against real-world benign codebases.

Evaluates K2 specificity against real, permissively-licensed benign C codebases:
1. miniz (richgel999/miniz, MIT): Single-file zlib/deflate/inflate with Adler-32, CRC-32, Huffman tables.
2. cJSON (DaveGamble/cJSON, MIT): Ultralightweight ANSI C JSON parser with unicode surrogate bitshifts and lookup logic.

Total corpus size exceeds 150,000 bytes across real-world production C code.
Defined floor: benign residue ratio <= 5.0% (0.05).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from engine import source_c
from engine.attribute import compute_ledger
from engine.extract import extract_all
from engine.models import Span

BENIGN_CORPUS_DIR = Path(__file__).parent.parent / "bench" / "fixtures" / "benign_corpus"
BENIGN_RESIDUE_FLOOR_RATIO = 0.05


def test_k2_specificity_real_world_benign_corpus() -> None:
    """K2 Specificity: Real benign codebases with tables/bitshifts produce residue <= 5.0%."""
    benign_files = sorted(list(BENIGN_CORPUS_DIR.glob("*.c")) + list(BENIGN_CORPUS_DIR.glob("*.h")))
    assert len(benign_files) >= 2, f"Expected benign corpus files in {BENIGN_CORPUS_DIR}, found {len(benign_files)}"

    total_benign_bytes = 0
    total_benign_residue_mass = 0.0
    file_results: list[dict[str, object]] = []

    for file_path in benign_files:
        content = file_path.read_bytes()
        artifact_hash = hashlib.sha256(content).hexdigest()
        file_size = len(content)
        total_benign_bytes += file_size

        finding_spans: list[Span] = [
            s for d in source_c.detect_code(content, file_path.name, artifact_hash) for s in d.spans
        ]
        suspicion_spans = extract_all(content, file_path.name, artifact_hash)
        ledger = compute_ledger(content, finding_spans, suspicion_spans, artifact_hash)

        total_benign_residue_mass += ledger.residue_mass
        file_ratio = (ledger.residue_mass / file_size) if file_size > 0 else 0.0

        file_results.append({
            "file": file_path.name,
            "bytes": file_size,
            "findings": len(finding_spans),
            "suspicion_spans": len(suspicion_spans),
            "residue_mass": ledger.residue_mass,
            "residue_ratio": file_ratio,
        })

    aggregate_residue_ratio = (
        total_benign_residue_mass / total_benign_bytes if total_benign_bytes > 0 else 0.0
    )

    print(f"\n{'='*60}")
    print(f"[K2 REAL-WORLD STRESS TEST] Total Benign Bytes: {total_benign_bytes:,}")
    print(f"[K2 REAL-WORLD STRESS TEST] Total Benign Residue Mass: {total_benign_residue_mass:,.1f}")
    print(f"[K2 REAL-WORLD STRESS TEST] Aggregate Residue Ratio: {aggregate_residue_ratio * 100:.3f}%")
    print(f"[K2 REAL-WORLD STRESS TEST] Defined K2 Floor: {BENIGN_RESIDUE_FLOOR_RATIO * 100:.1f}%")
    for r in file_results:
        mass = r["residue_mass"]
        pct = float(r["residue_ratio"]) * 100  # type: ignore[arg-type]
        print(f"  - {r['file']}: {r['bytes']:,} bytes, {mass} residue mass ({pct:.2f}%)")
    print(f"{'='*60}\n")

    assert aggregate_residue_ratio <= BENIGN_RESIDUE_FLOOR_RATIO, (
        f"K2 Specificity stress test failed: aggregate residue {aggregate_residue_ratio * 100:.3f}% "
        f"exceeds floor {BENIGN_RESIDUE_FLOOR_RATIO * 100:.1f}%"
    )
