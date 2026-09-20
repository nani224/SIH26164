"""Debt-closure loop for Crypto Mass Conservation (CMC) engine.

CLI: ecdat debt list|show|promote|exclude|accept
- list: list all residue clusters
- show: inspect a residue cluster with its preview, mass, and spans
- promote: scaffold a rule stub with fixture, mark state as promoted-to-rule
- exclude: require written justification and owner, mark state as excluded
- accept: record why residue is tolerated, mark state as accepted

Closed clusters are keyed by content hash in a persistent debt store
so they never resurface and carry across estates.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEBT_STORE_PATH = Path(__file__).parent / "debt_store.json"
RULES_DIR = Path(__file__).parent
FIXTURES_DIR = Path(__file__).parent.parent / "bench" / "fixtures"


@dataclass
class ClosedClusterRecord:
    cluster_id: str
    state: str  # "promoted-to-rule" | "excluded" | "accepted"
    owner: str | None = None
    justification: str | None = None
    rule_file: str | None = None
    fixture_file: str | None = None


def load_debt_store(store_path: Path = DEBT_STORE_PATH) -> dict[str, ClosedClusterRecord]:
    if not store_path.exists():
        return {}
    try:
        data = json.loads(store_path.read_text(encoding="utf-8"))
        return {
            cid: ClosedClusterRecord(
                cluster_id=cid,
                state=rec.get("state", "open"),
                owner=rec.get("owner"),
                justification=rec.get("justification"),
                rule_file=rec.get("rule_file"),
                fixture_file=rec.get("fixture_file"),
            )
            for cid, rec in data.items()
        }
    except (json.JSONDecodeError, OSError):
        return {}


def save_debt_store(
    records: dict[str, ClosedClusterRecord], store_path: Path = DEBT_STORE_PATH
) -> None:
    data = {cid: asdict(rec) for cid, rec in records.items()}
    store_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_clusters(
    clusters: list[Any], store_path: Path = DEBT_STORE_PATH
) -> list[dict[str, Any]]:
    debt_store = load_debt_store(store_path)
    result = []
    for c in clusters:
        cid = c.id if hasattr(c, "id") else c.get("id")
        rec = debt_store.get(cid)
        state = rec.state if rec else getattr(c, "state", "open")
        owner = rec.owner if rec else getattr(c, "owner", None)
        item = {
            "id": cid,
            "artifact_hash": getattr(c, "artifact_hash", c.get("artifact_hash", "") if isinstance(c, dict) else ""),
            "start": getattr(c, "start", c.get("start", 0) if isinstance(c, dict) else 0),
            "end": getattr(c, "end", c.get("end", 0) if isinstance(c, dict) else 0),
            "mass": getattr(c, "mass", c.get("mass", 0.0) if isinstance(c, dict) else 0.0),
            "state": state,
            "owner": owner,
            "preview": getattr(c, "content_preview", c.get("content_preview", "") if isinstance(c, dict) else ""),
        }
        result.append(item)
    return result


def show_cluster(
    cluster_id: str, clusters: list[Any], store_path: Path = DEBT_STORE_PATH
) -> dict[str, Any] | None:
    debt_store = load_debt_store(store_path)
    matching = [c for c in clusters if (getattr(c, "id", None) or (c.get("id") if isinstance(c, dict) else None)) == cluster_id]
    if not matching:
        return None
    c = matching[0]
    rec = debt_store.get(cluster_id)
    return {
        "id": cluster_id,
        "artifact_hash": getattr(c, "artifact_hash", c.get("artifact_hash", "") if isinstance(c, dict) else ""),
        "start": getattr(c, "start", c.get("start", 0) if isinstance(c, dict) else 0),
        "end": getattr(c, "end", c.get("end", 0) if isinstance(c, dict) else 0),
        "mass": getattr(c, "mass", c.get("mass", 0.0) if isinstance(c, dict) else 0.0),
        "state": rec.state if rec else getattr(c, "state", "open"),
        "owner": rec.owner if rec else getattr(c, "owner", None),
        "justification": rec.justification if rec else getattr(c, "justification", None),
        "rule_file": rec.rule_file if rec else None,
        "fixture_file": rec.fixture_file if rec else None,
        "preview": getattr(c, "content_preview", c.get("content_preview", "") if isinstance(c, dict) else ""),
    }


def promote_cluster(
    cluster_id: str,
    cluster_slice: bytes,
    artifact_ext: str = ".py",
    store_path: Path = DEBT_STORE_PATH,
) -> ClosedClusterRecord:
    """Scaffold a rule stub with its fixture for a residue cluster."""
    debt_store = load_debt_store(store_path)

    short_id = cluster_id[:12]
    fixture_name = f"fixture_promoted_{short_id}{artifact_ext}"
    fixture_path = FIXTURES_DIR / fixture_name
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    fixture_path.write_bytes(cluster_slice)

    rule_name = f"promoted_{short_id}.py"
    rule_path = RULES_DIR / rule_name
    rule_content = f'''"""Auto-scaffolded rule for promoted residue cluster {cluster_id}.
Generated by ecdat debt promote.
"""

from __future__ import annotations

import hashlib
from engine.models import Detection, Span
from api.models import FindingKind, Surface, Family, CryptoFunction, FindingSource

_CLUSTER_HASH = "{cluster_id}"
_CLUSTER_BYTES = {repr(cluster_slice)}


def detect_promoted_cluster(source: bytes, path: str = "<source>", artifact_hash: str | None = None) -> list[Detection]:
    if artifact_hash is None:
        artifact_hash = hashlib.sha256(source).hexdigest()
    detections: list[Detection] = []
    if _CLUSTER_BYTES in source:
        offset = source.find(_CLUSTER_BYTES)
        span = Span(
            artifact_hash=artifact_hash,
            kind="ast" if path.endswith((".py", ".go", ".java", ".c")) else "byte",
            start=offset,
            end=offset + len(_CLUSTER_BYTES),
            producing_rule="promoted_rule.{short_id}",
        )
        detections.append(
            Detection(
                kind=FindingKind.ALGORITHM,
                surface=Surface.SOURCE if path.endswith((".py", ".go", ".java", ".c")) else Surface.BINARY,
                family=Family.AES,
                display_name=f"Promoted Rule {short_id}",
                function=CryptoFunction.ENCRYPT,
                path=path,
                line=None,
                symbol="promoted_cluster",
                snippet=f"Promoted residue cluster {short_id}",
                source=FindingSource.AST if path.endswith((".py", ".go", ".java", ".c")) else FindingSource.BINARY_CONSTANT,
                confidence=0.96,
                spans=[span],
            )
        )
    return detections
'''
    rule_path.write_text(rule_content, encoding="utf-8")

    record = ClosedClusterRecord(
        cluster_id=cluster_id,
        state="promoted-to-rule",
        owner="engine-promoter",
        justification=f"Promoted to dedicated detection rule {rule_name}",
        rule_file=str(rule_path.relative_to(RULES_DIR.parent)),
        fixture_file=str(fixture_path.relative_to(RULES_DIR.parent)),
    )
    debt_store[cluster_id] = record
    save_debt_store(debt_store, store_path)
    return record


def exclude_cluster(
    cluster_id: str,
    justification: str,
    owner: str,
    store_path: Path = DEBT_STORE_PATH,
) -> ClosedClusterRecord:
    """Exclude a residue cluster with a written justification and owner."""
    if not justification or not justification.strip():
        raise ValueError("Excluding a cluster requires a non-empty written justification.")
    if not owner or not owner.strip():
        raise ValueError("Excluding a cluster requires a non-empty owner.")

    debt_store = load_debt_store(store_path)
    record = ClosedClusterRecord(
        cluster_id=cluster_id,
        state="excluded",
        owner=owner.strip(),
        justification=justification.strip(),
    )
    debt_store[cluster_id] = record
    save_debt_store(debt_store, store_path)
    return record


def accept_cluster(
    cluster_id: str,
    justification: str,
    owner: str,
    store_path: Path = DEBT_STORE_PATH,
) -> ClosedClusterRecord:
    """Accept a residue cluster with a written justification of why it is tolerated."""
    if not justification or not justification.strip():
        raise ValueError("Accepting a cluster requires a non-empty written justification.")
    if not owner or not owner.strip():
        raise ValueError("Accepting a cluster requires a non-empty owner.")

    debt_store = load_debt_store(store_path)
    record = ClosedClusterRecord(
        cluster_id=cluster_id,
        state="accepted",
        owner=owner.strip(),
        justification=justification.strip(),
    )
    debt_store[cluster_id] = record
    save_debt_store(debt_store, store_path)
    return record


def cli_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ecdat", description="ECDAT CLI - Crypto Mass Conservation")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    debt_parser = subparsers.add_parser("debt", help="Manage cryptographic residue debt clusters")
    debt_sub = debt_parser.add_subparsers(dest="debt_action", required=True)

    # list
    debt_sub.add_parser("list", help="List all residue clusters")

    # show
    show_p = debt_sub.add_parser("show", help="Show cluster details")
    show_p.add_argument("cluster_id", help="SHA-256 cluster ID")

    # promote
    promote_p = debt_sub.add_parser("promote", help="Promote cluster to a detection rule stub")
    promote_p.add_argument("cluster_id", help="SHA-256 cluster ID")

    # exclude
    exclude_p = debt_sub.add_parser("exclude", help="Exclude cluster with written justification and owner")
    exclude_p.add_argument("cluster_id", help="SHA-256 cluster ID")
    exclude_p.add_argument("--reason", required=True, help="Written justification")
    exclude_p.add_argument("--owner", required=True, help="Owner responsible for exclusion")

    # accept
    accept_p = debt_sub.add_parser("accept", help="Accept cluster with tolerated reason")
    accept_p.add_argument("cluster_id", help="SHA-256 cluster ID")
    accept_p.add_argument("--reason", required=True, help="Written explanation")
    accept_p.add_argument("--owner", required=True, help="Owner responsible for acceptance")

    args = parser.parse_args(argv)

    if args.subcommand == "debt":
        debt_store = load_debt_store()
        if args.debt_action == "list":
            if not debt_store:
                print("No recorded debt clusters in store.")
                return 0
            print(f"{'CLUSTER ID':<16} {'STATE':<16} {'OWNER':<15} {'JUSTIFICATION'}")
            print("-" * 75)
            for cid, rec in debt_store.items():
                print(f"{cid[:14]:<16} {rec.state:<16} {str(rec.owner):<15} {str(rec.justification)[:25]}")
            return 0

        elif args.debt_action == "show":
            rec = debt_store.get(args.cluster_id)
            if not rec:
                print(f"Cluster {args.cluster_id} not found.")
                return 1
            print(json.dumps(asdict(rec), indent=2))
            return 0

        elif args.debt_action == "exclude":
            rec = exclude_cluster(args.cluster_id, args.reason, args.owner)
            print(f"Excluded cluster {args.cluster_id}. Justification: {args.reason}")
            return 0

        elif args.debt_action == "accept":
            rec = accept_cluster(args.cluster_id, args.reason, args.owner)
            print(f"Accepted cluster {args.cluster_id}. Tolerated reason: {args.reason}")
            return 0

    return 0


if __name__ == "__main__":
    sys.exit(cli_main())
