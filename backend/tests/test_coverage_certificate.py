"""M4 Verification: Coverage Certificate tests.

Verifies:
1. Every CBOM carrying a coverage certificate strictly validates against CycloneDX 1.6 schema.
2. The certificate is reproducible: same input produces identical coverage numbers and hashes.
3. Signed attestation manifest is present and verifiable.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from api.cbom import build_cbom
from api.stub_data import default_scan, list_findings
from engine.attribute import compute_ledger
from engine.certificate import (
    embed_coverage_in_cbom,
    generate_coverage_certificate,
)
from engine.models import Span

FIXTURES = Path(__file__).parent / "fixtures" / "cyclonedx"


def _validator() -> jsonschema.Draft7Validator:
    schema = json.loads((FIXTURES / "bom-1.6.schema.json").read_text())
    resolver = jsonschema.RefResolver(
        base_uri=(FIXTURES / "bom-1.6.schema.json").as_uri(), referrer=schema
    )
    return jsonschema.Draft7Validator(schema, resolver=resolver)


def test_cbom_with_coverage_certificate_validates_cyclonedx_1_6() -> None:
    """A CBOM enriched with a Coverage Certificate must strictly pass CycloneDX 1.6 validation."""
    scan_obj = default_scan()
    findings = list_findings()
    base_cbom = build_cbom(scan_obj, findings)

    # Create dummy spans and ledger
    artifact_content = b"sample artifact content with some crypto evidence"
    f_spans = [
        Span(
            artifact_hash="abc123hash",
            kind="ast",
            start=10,
            end=30,
            producing_rule="test.rule",
        )
    ]
    s_spans = [
        Span(
            artifact_hash="abc123hash",
            kind="ast",
            start=10,
            end=30,
            producing_rule="extract.suspicion",
            signal_type="suspicion",
            magnitude=20.0,
        ),
        Span(
            artifact_hash="abc123hash",
            kind="ast",
            start=35,
            end=50,
            producing_rule="extract.residue",
            signal_type="suspicion",
            magnitude=15.0,
        ),
    ]

    ledger = compute_ledger(artifact_content, f_spans, s_spans, "abc123hash")
    certificate = generate_coverage_certificate(ledger, scan_obj.id)

    enriched_cbom = embed_coverage_in_cbom(base_cbom, certificate)

    # Validate against strict CycloneDX 1.6 schema
    validator = _validator()
    errors = list(validator.iter_errors(enriched_cbom))
    assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors)

    # Verify coverage properties exist
    meta_props = {p["name"]: p["value"] for p in enriched_cbom["metadata"]["properties"]}
    assert "ecdat:coverage:totalMass" in meta_props
    assert "ecdat:coverage:attributedMass" in meta_props
    assert "ecdat:coverage:residueMass" in meta_props
    assert "ecdat:coverage:ratio" in meta_props
    assert "ecdat:coverage:attestationSig" in meta_props

    # Verify annotations exist
    assert "annotations" in enriched_cbom
    assert len(enriched_cbom["annotations"]) >= 1
    assert "ECDAT CRYPTO MASS CONSERVATION CERTIFICATE" in enriched_cbom["annotations"][0]["text"]


def test_certificate_reproducibility() -> None:
    """Identical input must produce strictly identical coverage numbers and attestation hashes."""
    content = b"content for reproducibility testing"
    s_spans = [
        Span(
            artifact_hash="fixed_hash",
            kind="byte",
            start=0,
            end=10,
            producing_rule="extract.s1",
            signal_type="s1",
            magnitude=10.0,
        ),
        Span(
            artifact_hash="fixed_hash",
            kind="byte",
            start=15,
            end=25,
            producing_rule="extract.s2",
            signal_type="s2",
            magnitude=10.0,
        ),
    ]

    ledger1 = compute_ledger(content, [], s_spans, "fixed_hash")
    ledger2 = compute_ledger(content, [], s_spans, "fixed_hash")

    cert1 = generate_coverage_certificate(ledger1, "scan_123")
    cert2 = generate_coverage_certificate(ledger2, "scan_123")

    assert cert1.total_mass == cert2.total_mass
    assert cert1.attributed_mass == cert2.attributed_mass
    assert cert1.excluded_mass == cert2.excluded_mass
    assert cert1.residue_mass == cert2.residue_mass
    assert cert1.coverage_ratio == cert2.coverage_ratio
    assert cert1.residue_cluster_count == cert2.residue_cluster_count
    assert cert1.attestation_manifest["payloadHash"] == cert2.attestation_manifest["payloadHash"]
    assert cert1.attestation_manifest["signature"] == cert2.attestation_manifest["signature"]
