"""Universal CycloneDX 1.6 CBOM Benchmark Scorer.

Scores ANY tool's CycloneDX CBOM output against ground truth.
Measures:
1. Detection accuracy: True Positives, False Positives, False Negatives, Precision, Recall, F1.
2. Crypto Mass Conservation (CMC) metrics: Total Suspicion Mass, Attributed Mass, Excluded Mass,
   Residue Mass, and Coverage Ratio.

Usage:
  python bench/public/score.py --cbom <path-to-cbom.json> [--truth <path-to-truth.json>] [--json]
  python bench/public/score.py --all [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Ensure backend root is on sys.path
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from api.models import Context, Criticality, Exposure, Policy, Scan
from api.cbom import build_cbom
from engine.attribute import compute_ledger
from engine.certificate import embed_coverage_in_cbom, generate_coverage_certificate
from engine.scanner import scan

DEFAULT_TRUTH = _BACKEND_ROOT / "bench" / "truth.json"
FIXTURES_DIR = _BACKEND_ROOT / "bench" / "fixtures"


def _normalize_family(name: str, primitive: str = "") -> str:
    n = name.lower()
    p = primitive.lower()

    # 1. MAC takes precedence over hash
    if "hmac" in n:
        return "HMAC"

    # 2. Key agreement takes precedence over generic EC
    if p in ("key-agree", "kem") or any(k in n for k in ("ecdh", "diffie", "x25519", "keyagreement")):
        if "x25519" in n:
            return "X25519"
        if "ecdh" in n or "diffie" in n or "ec" in n:
            return "ECDH"
        if "dh" in n:
            return "DH"

    # 3. 3DES before DES
    if any(k in n for k in ("3des", "triple", "desede", "ede3", "des3")):
        return "3DES"

    # 4. Signatures / Asymmetric key operations
    if p in ("signature", "pke") or any(k in n for k in ("sign", "verify", "keygen", "key_gen")):
        if "rsa" in n:
            return "RSA"
        if "ecdsa" in n or "ec_paramgen" in n or "ec" in n:
            return "ECDSA"
        if "ed25519" in n:
            return "Ed25519"
        if "dsa" in n and "ecdsa" not in n:
            return "DSA"

    # 5. Symmetric ciphers
    if "chacha" in n:
        return "ChaCha20"
    if "aes" in n:
        return "AES"
    if "des" in n and not any(k in n for k in ("triple", "3des", "desede", "ede3", "des3")):
        return "DES"
    if "blowfish" in n:
        return "Blowfish"
    if "rc4" in n or "arc4" in n or "rc2" in n:
        return "RC4"
    if p in ("ae", "block-cipher", "stream-cipher"):
        return "AES"

    # 6. Hashes
    # SHA-384 is SHA-2, NOT SHA-3! Check sha384 first
    if any(k in n for k in (
        "sha384", "sha-384", "sum384", "sha512", "sha-512", "sum512",
        "sha256", "sha-256", "sum256", "sha224", "sha-224", "sum224", "sha2", "sha-2"
    )):
        return "SHA-2"
    if ("sha3" in n or "sha-3" in n or "sha3_" in n) and "sha384" not in n and "sha-384" not in n:
        return "SHA-3"
    if "sha1" in n or "sha-1" in n or "wc_shahash" in n or "wc_sha" in n:
        return "SHA-1"
    if "md5" in n:
        return "MD5"

    # 7. Fallback asymmetric
    if "rsa" in n:
        return "RSA"
    if "ecdsa" in n or "ec_paramgen" in n or "ec" in n:
        return "ECDSA"
    if "ed25519" in n:
        return "Ed25519"
    if "dsa" in n:
        return "DSA"

    return name


def extract_detections_from_cbom(cbom: dict[str, Any]) -> set[tuple[str, str, str, int]]:
    """Extract (path, family, function, line) tuples from any CycloneDX CBOM."""
    detections: set[tuple[str, str, str, int]] = set()

    components = cbom.get("components", [])
    for comp in components:
        raw_name = comp.get("name", "")
        crypto_props = comp.get("cryptoProperties", {})
        algo_props = crypto_props.get("algorithmProperties", {})
        primitive = algo_props.get("primitive", "")
        functions = algo_props.get("cryptoFunctions", [""])
        raw_fn = functions[0] if functions else ""
        fn = getattr(raw_fn, "value", str(raw_fn))

        family = _normalize_family(raw_name, primitive)

        # Extract occurrences
        evidence = comp.get("evidence", {})
        occurrences = evidence.get("occurrences", [])
        for occ in occurrences:
            loc = occ.get("location", "")
            filename = Path(loc).name if loc else ""
            line = occ.get("line", -1)
            if filename:
                detections.add((filename, family, fn, line))

    return detections


def extract_coverage_from_cbom(cbom: dict[str, Any]) -> dict[str, Any] | None:
    """Extract coverage certificate metrics from CycloneDX metadata.properties."""
    props = cbom.get("metadata", {}).get("properties", [])
    coverage: dict[str, Any] = {}
    prefix = "ecdat:coverage:"

    for prop in props:
        name = prop.get("name", "")
        if name.startswith(prefix):
            key = name[len(prefix) :]
            val = prop.get("value", "")
            try:
                if "." in val:
                    coverage[key] = float(val)
                else:
                    coverage[key] = int(val)
            except ValueError:
                coverage[key] = val

    return coverage if coverage else None


def load_truth(truth_path: Path) -> set[tuple[str, str, str, int]]:
    """Load ground truth tuples from truth.json."""
    data = json.loads(truth_path.read_text(encoding="utf-8"))
    truth_set: set[tuple[str, str, str, int]] = set()
    for filename, entries in data.items():
        for entry in entries:
            truth_set.add((filename, entry.get("family", ""), entry.get("function", ""), entry.get("line", -1)))
    return truth_set


def match_detections(
    truth: set[tuple[str, str, str, int]],
    detected: set[tuple[str, str, str, int]],
    line_tolerance: int = 0,
) -> tuple[set[tuple[str, str, str, int]], set[tuple[str, str, str, int]], set[tuple[str, str, str, int]]]:
    """Match detected findings against truth, allowing optional line tolerance."""
    tp: set[tuple[str, str, str, int]] = set()
    matched_det: set[tuple[str, str, str, int]] = set()

    for t_item in truth:
        t_file, t_fam, t_fn, t_line = t_item
        matched = False
        for d_item in detected:
            if d_item in matched_det:
                continue
            d_file, d_fam, d_fn, d_line = d_item
            if t_file != d_file:
                continue

            # Family match: exact, or one is empty/unknown, or case-insensitive
            fam_match = not t_fam or not d_fam or t_fam.lower() == d_fam.lower()
            # Function match: exact, or one is empty/unknown, or case-insensitive
            fn_match = (
                not t_fn or not d_fn
                or t_fn.lower() == d_fn.lower()
                or {t_fn.lower(), d_fn.lower()} <= {"", "unknown"}
            )

            if fam_match and fn_match:
                if abs(t_line - d_line) <= line_tolerance:
                    tp.add(t_item)
                    matched_det.add(d_item)
                    matched = True
                    break

    fp = detected - matched_det
    fn = truth - tp
    return tp, fp, fn


def score_cbom(
    cbom: dict[str, Any],
    truth: set[tuple[str, str, str, int]],
    line_tolerance: int = 0,
) -> dict[str, Any]:
    """Score a CycloneDX CBOM against truth."""
    detected = extract_detections_from_cbom(cbom)
    tp, fp, fn = match_detections(truth, detected, line_tolerance=line_tolerance)

    precision = len(tp) / len(detected) if detected else 1.0
    recall = len(tp) / len(truth) if truth else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    coverage = extract_coverage_from_cbom(cbom)

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "true_positives": len(tp),
        "false_positives": len(fp),
        "false_negatives": len(fn),
        "truth_count": len(truth),
        "detected_count": len(detected),
        "coverage": coverage,
    }


def run_benchmark_all() -> tuple[dict[str, Any], dict[str, Any]]:
    """Run full benchmark scan across fixtures and score the resulting CBOM."""
    policy = Policy(
        id="bench_policy",
        name="Bench evaluation policy",
        crqcYears=10,
        default=Context(
            exposure=Exposure.INTERNAL, criticality=Criticality.MEDIUM, shelfLifeYears=5, migrationYears=3
        ),
        contexts=[],
    )

    from api.stub_data import default_scan

    scan_result = scan(FIXTURES_DIR, policy)
    scan_obj = default_scan()
    scan_obj.target = str(FIXTURES_DIR)
    scan_obj.policyId = policy.id

    # Compute ledger & coverage certificate across fixtures
    import hashlib
    from engine.attribute import compute_ledger
    from engine.attribute.ledger import AttributionLedger
    from engine.extract import extract_all

    all_attributed_mass = 0.0
    all_excluded_mass = 0.0
    all_residue_mass = 0.0
    all_total_mass = 0.0
    all_attributed_spans = []
    all_excluded_spans = []
    all_residue_spans = []
    all_clusters = []
    all_exclusions = []

    for f_path in sorted(FIXTURES_DIR.rglob("*")):
        if f_path.is_file() and not any(part.startswith(".") for part in f_path.relative_to(FIXTURES_DIR).parts):
            try:
                content = f_path.read_bytes()
                f_hash = hashlib.sha256(content).hexdigest()
                f_finding_spans = [
                    s for f in scan_result.findings
                    for s in getattr(f, "spans", [])
                    if s.artifact_hash == f_hash
                ]
                f_suspicion_spans = extract_all(content, str(f_path), artifact_hash=f_hash)
                f_ledger = compute_ledger(content, f_finding_spans, f_suspicion_spans, artifact_hash=f_hash)

                all_total_mass += f_ledger.total_suspicion_mass
                all_attributed_mass += f_ledger.attributed_mass
                all_excluded_mass += f_ledger.excluded_mass
                all_residue_mass += f_ledger.residue_mass
                all_attributed_spans.extend(f_ledger.attributed_spans)
                all_excluded_spans.extend(f_ledger.excluded_spans)
                all_residue_spans.extend(f_ledger.residue_spans)
                all_clusters.extend(f_ledger.residue_clusters)
                all_exclusions.extend(f_ledger.exclusion_records)
            except Exception:
                pass

    agg_ratio = all_attributed_mass / all_total_mass if all_total_mass > 0 else 1.0
    agg_ledger = AttributionLedger(
        artifact_hash="corpus-aggregate",
        total_suspicion_mass=all_total_mass,
        attributed_mass=all_attributed_mass,
        excluded_mass=all_excluded_mass,
        residue_mass=all_residue_mass,
        coverage_ratio=agg_ratio,
        attributed_spans=all_attributed_spans,
        excluded_spans=all_excluded_spans,
        residue_spans=all_residue_spans,
        residue_clusters=all_clusters,
        exclusion_records=all_exclusions,
    )

    cert = generate_coverage_certificate(
        ledger=agg_ledger,
        scan_id="scan_bench",
    )
    base_cbom = build_cbom(scan_obj, scan_result.findings)
    enriched_cbom = embed_coverage_in_cbom(base_cbom, cert)

    truth = load_truth(DEFAULT_TRUTH)
    scores = score_cbom(enriched_cbom, truth)
    return scores, cert


def main() -> int:
    parser = argparse.ArgumentParser(description="Score CycloneDX 1.6 CBOM against ground truth.")
    parser.add_argument("--cbom", type=Path, help="Path to CycloneDX CBOM JSON file.")
    parser.add_argument("--truth", type=Path, default=DEFAULT_TRUTH, help="Path to truth.json.")
    parser.add_argument("--all", action="store_true", help="Run full benchmark scan and score CBOM.")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format.")
    parser.add_argument("--tolerance", type=int, default=0, help="Line matching tolerance (default 0).")

    args = parser.parse_args()

    if args.all:
        scores, cert = run_benchmark_all()
        if args.json:
            print(json.dumps({"scores": scores, "certificate": cert.to_dict()}, indent=2))
        else:
            print("=" * 60)
            print("ECDAT v1.0 — BENCHMARK EVALUATION & COVERAGE CERTIFICATE")
            print("=" * 60)
            print(f"Precision:        {scores['precision']:.4f}  (floor: 0.9500)")
            print(f"Recall:           {scores['recall']:.4f}")
            print(f"F1 Score:         {scores['f1']:.4f}")
            print(f"True Positives:   {scores['true_positives']}")
            print(f"False Positives:  {scores['false_positives']}")
            print(f"False Negatives:  {scores['false_negatives']}")
            print("-" * 60)
            if scores.get("coverage"):
                cov = scores["coverage"]
                total = cov.get("totalMass", cov.get("total_mass", 0.0))
                attr = cov.get("attributedMass", cov.get("attributed_mass", 0.0))
                excl = cov.get("excludedMass", cov.get("excluded_mass", 0.0))
                res = cov.get("residueMass", cov.get("residue_mass", 0.0))
                ratio = cov.get("ratio", 0.0)
                clusters = cov.get("residueClusterCount", cov.get("residue_clusters", 0))
                print("Crypto Mass Conservation (CMC) Certificate:")
                print(f"  Total Suspicion Mass: {total:.2f}")
                print(f"  Attributed Mass:      {attr:.2f}")
                print(f"  Excluded Mass:        {excl:.2f}")
                print(f"  Residue Mass:         {res:.2f}")
                print(f"  Coverage Ratio:       {ratio:.4f}")
                print(f"  Residue Clusters:     {clusters}")
            print("=" * 60)
        return 0

    if not args.cbom:
        parser.print_help()
        return 1

    if not args.cbom.exists():
        print(f"Error: CBOM file '{args.cbom}' does not exist.", file=sys.stderr)
        return 1

    truth = load_truth(args.truth)
    cbom_data = json.loads(args.cbom.read_text(encoding="utf-8"))
    scores = score_cbom(cbom_data, truth, line_tolerance=args.tolerance)

    if args.json:
        print(json.dumps(scores, indent=2))
    else:
        print(f"precision={scores['precision']} recall={scores['recall']} f1={scores['f1']}")
        print(f"truth={scores['truth_count']} detected={scores['detected_count']} tp={scores['true_positives']} fp={scores['false_positives']} fn={scores['false_negatives']}")
        if scores.get("coverage"):
            print("Coverage Certificate:", scores["coverage"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
