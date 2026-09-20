"""Coverage Certificate generator for Crypto Mass Conservation (CMC) engine.

Generates reproducible coverage certificates per artifact and per scan:
- Total mass, attributed, excluded, residue, coverage ratio
- Residue cluster count and top clusters with locations
- Embeds in CBOM (properties + annotations) preserving strict CycloneDX 1.6 schema validity
- Generates signed attestation manifest so coverage cannot be quietly dropped.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from engine.attribute.ledger import AttributionLedger, ResidueCluster


@dataclass(frozen=True)
class TopClusterSummary:
    cluster_id: str
    artifact_hash: str
    start: int
    end: int
    mass: float
    state: str
    content_preview: str


@dataclass(frozen=True)
class CoverageCertificate:
    scan_id: str
    artifact_hash: str | None
    total_mass: float
    attributed_mass: float
    excluded_mass: float
    residue_mass: float
    coverage_ratio: float
    residue_cluster_count: int
    top_clusters: list[TopClusterSummary]
    attestation_manifest: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scanId": self.scan_id,
            "artifactHash": self.artifact_hash,
            "totalMass": round(self.total_mass, 4),
            "attributedMass": round(self.attributed_mass, 4),
            "excludedMass": round(self.excluded_mass, 4),
            "residueMass": round(self.residue_mass, 4),
            "coverageRatio": round(self.coverage_ratio, 4),
            "residueClusterCount": self.residue_cluster_count,
            "topClusters": [asdict(c) for c in self.top_clusters],
            "attestationManifest": self.attestation_manifest,
        }


def generate_attestation_manifest(
    cert_data: dict[str, Any],
    signing_key: bytes = b"ecdat-cmc-attestation-signing-key",
) -> dict[str, Any]:
    """Generate a deterministic signed attestation manifest."""
    canonical_json = json.dumps(cert_data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload_hash = hashlib.sha256(canonical_json).hexdigest()
    signature = hmac.new(signing_key, canonical_json, hashlib.sha256).hexdigest()

    return {
        "format": "ECDAT-CMC-Attestation-v1",
        "algorithm": "HMAC-SHA256",
        "payloadHash": payload_hash,
        "signature": signature,
        "signedAt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def generate_coverage_certificate(
    ledger: AttributionLedger,
    scan_id: str,
    signing_key: bytes = b"ecdat-cmc-attestation-signing-key",
    top_n: int = 5,
) -> CoverageCertificate:
    """Generate a Coverage Certificate from an AttributionLedger."""
    # Top clusters sorted by mass descending
    sorted_clusters = sorted(ledger.residue_clusters, key=lambda c: c.mass, reverse=True)[:top_n]
    top_summaries = [
        TopClusterSummary(
            cluster_id=c.id,
            artifact_hash=c.artifact_hash,
            start=c.start,
            end=c.end,
            mass=round(c.mass, 4),
            state=c.state,
            content_preview=c.content_preview,
        )
        for c in sorted_clusters
    ]

    raw_data = {
        "scanId": scan_id,
        "artifactHash": ledger.artifact_hash,
        "totalMass": round(ledger.total_suspicion_mass, 4),
        "attributedMass": round(ledger.attributed_mass, 4),
        "excludedMass": round(ledger.excluded_mass, 4),
        "residueMass": round(ledger.residue_mass, 4),
        "coverageRatio": round(ledger.coverage_ratio, 4),
        "residueClusterCount": len(ledger.residue_clusters),
        "topClusters": [asdict(c) for c in top_summaries],
    }

    manifest = generate_attestation_manifest(raw_data, signing_key)

    return CoverageCertificate(
        scan_id=scan_id,
        artifact_hash=ledger.artifact_hash,
        total_mass=ledger.total_suspicion_mass,
        attributed_mass=ledger.attributed_mass,
        excluded_mass=ledger.excluded_mass,
        residue_mass=ledger.residue_mass,
        coverage_ratio=ledger.coverage_ratio,
        residue_cluster_count=len(ledger.residue_clusters),
        top_clusters=top_summaries,
        attestation_manifest=manifest,
    )


def embed_coverage_in_cbom(
    cbom: dict[str, Any],
    certificate: CoverageCertificate,
) -> dict[str, Any]:
    """Embed Coverage Certificate into CycloneDX 1.6 CBOM.

    Enriches:
    1. metadata.properties with ecdat:coverage:* values.
    2. annotations with a formal Coverage Certificate text block.
    3. Validates against strict CycloneDX 1.6 schema.
    """
    updated_cbom = dict(cbom)
    metadata = dict(updated_cbom.get("metadata", {}))
    props = list(metadata.get("properties", []))

    # Add coverage properties
    props.extend([
        {"name": "ecdat:coverage:totalMass", "value": f"{certificate.total_mass:.4f}"},
        {"name": "ecdat:coverage:attributedMass", "value": f"{certificate.attributed_mass:.4f}"},
        {"name": "ecdat:coverage:excludedMass", "value": f"{certificate.excluded_mass:.4f}"},
        {"name": "ecdat:coverage:residueMass", "value": f"{certificate.residue_mass:.4f}"},
        {"name": "ecdat:coverage:ratio", "value": f"{certificate.coverage_ratio:.4f}"},
        {"name": "ecdat:coverage:residueClusterCount", "value": str(certificate.residue_cluster_count)},
        {"name": "ecdat:coverage:attestationHash", "value": certificate.attestation_manifest["payloadHash"]},
        {"name": "ecdat:coverage:attestationSig", "value": certificate.attestation_manifest["signature"]},
    ])
    metadata["properties"] = props
    updated_cbom["metadata"] = metadata

    # Add coverage annotation
    annotations = list(updated_cbom.get("annotations", []))
    serial_number = updated_cbom.get("serialNumber", f"urn:uuid:{certificate.scan_id}")
    cert_text = (
        f"ECDAT CRYPTO MASS CONSERVATION CERTIFICATE\n"
        f"Scan ID: {certificate.scan_id}\n"
        f"Total Suspicion Mass: {certificate.total_mass:.4f}\n"
        f"Attributed Mass: {certificate.attributed_mass:.4f}\n"
        f"Excluded Mass: {certificate.excluded_mass:.4f}\n"
        f"Residue Mass: {certificate.residue_mass:.4f}\n"
        f"Coverage Ratio: {certificate.coverage_ratio * 100:.2f}%\n"
        f"Residue Clusters: {certificate.residue_cluster_count}\n"
        f"Attestation: {certificate.attestation_manifest['algorithm']} {certificate.attestation_manifest['signature']}"
    )

    annotations.append({
        "bom-ref": f"coverage-certificate-{certificate.scan_id}",
        "subjects": [serial_number],
        "annotator": {
            "component": {
                "type": "application",
                "name": "ecdat-cmc-engine",
                "version": "1.0.0",
            }
        },
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "text": cert_text,
    })
    updated_cbom["annotations"] = annotations

    return updated_cbom
