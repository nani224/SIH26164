from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from api.cbom import build_cbom
from api.stub_data import default_scan, list_findings

FIXTURES = Path(__file__).parent / "fixtures" / "cyclonedx"


def _validator() -> jsonschema.Draft7Validator:
    schema = json.loads((FIXTURES / "bom-1.6.schema.json").read_text())
    resolver = jsonschema.RefResolver(
        base_uri=(FIXTURES / "bom-1.6.schema.json").as_uri(), referrer=schema
    )
    return jsonschema.Draft7Validator(schema, resolver=resolver)


def test_stub_cbom_validates_against_cyclonedx_1_6_schema() -> None:
    cbom = build_cbom(default_scan(), list_findings())
    errors = list(_validator().iter_errors(cbom))
    assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors)


def test_cbom_has_a_component_per_finding() -> None:
    findings = list_findings()
    cbom = build_cbom(default_scan(), findings)
    assert len(cbom["components"]) == len(findings)
    assert all(c["type"] == "cryptographic-asset" for c in cbom["components"])


def test_private_key_finding_maps_to_related_crypto_material() -> None:
    cbom = build_cbom(default_scan(), list_findings())
    key_components = [c for c in cbom["components"] if c["bom-ref"] == "finding_002"]
    assert len(key_components) == 1
    assert key_components[0]["cryptoProperties"]["assetType"] == "related-crypto-material"
