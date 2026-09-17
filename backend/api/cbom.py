"""Phase 0 stub CBOM (CycloneDX 1.6) builder.

Builds a structurally-correct CycloneDX 1.6 "cryptographic-asset" BOM from
the in-memory stub findings. Field names/enums here are taken directly from
the CycloneDX 1.6 JSON schema vendored at
tests/fixtures/cyclonedx/bom-1.6.schema.json (see TOOLBELT.md for the pinned
hash) — validated by tests/test_cbom.py. This is Phase 0 scaffolding: the
real engine (Phase 1+) will build these from actual detections, not stub
data.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from api.models import Finding, Scan

_PRIMITIVE_MAP: dict[str, str] = {
    "AES": "block-cipher",
    "ChaCha20": "stream-cipher",
    "3DES": "block-cipher",
    "DES": "block-cipher",
    "RC4": "stream-cipher",
    "Blowfish": "block-cipher",
    "MD5": "hash",
    "SHA-1": "hash",
    "SHA-2": "hash",
    "SHA-3": "hash",
    "HMAC": "mac",
    "ML-KEM": "kem",
    "DH": "key-agree",
    "ECDH": "key-agree",
    "X25519": "key-agree",
}
_SIGNATURE_FAMILIES = {"DSA", "ECDSA", "Ed25519", "ML-DSA", "SLH-DSA"}


def _primitive_for(finding: Finding) -> str:
    if finding.family is None:
        return "unknown"
    if finding.family == "RSA":
        return "signature" if finding.function in ("sign", "verify") else "pke"
    if finding.family in _SIGNATURE_FAMILIES:
        return "signature"
    if finding.family == "AES" and finding.mode in ("GCM", "CCM"):
        return "ae"
    return _PRIMITIVE_MAP.get(finding.family, "unknown")


def _asset_type_for(finding: Finding) -> str:
    if finding.kind == "certificate":
        return "certificate"
    if finding.kind == "key":
        return "related-crypto-material"
    if finding.kind == "protocol":
        return "protocol"
    return "algorithm"


def _crypto_properties_for(finding: Finding) -> dict[str, Any]:
    asset_type = _asset_type_for(finding)
    props: dict[str, Any] = {"assetType": asset_type}

    if asset_type == "algorithm" or asset_type == "protocol":
        algo_props: dict[str, Any] = {
            "primitive": _primitive_for(finding),
            "cryptoFunctions": [finding.function],
        }
        if finding.keySize is not None:
            algo_props["parameterSetIdentifier"] = str(finding.keySize)
        if finding.curve is not None:
            algo_props["curve"] = finding.curve
        if finding.mode is not None:
            algo_props["mode"] = finding.mode.lower()
        props["algorithmProperties"] = algo_props
    elif asset_type == "related-crypto-material":
        props["relatedCryptoMaterialProperties"] = {
            "type": "private-key" if finding.function in ("sign", "decrypt", "keyderive") else "key",
            "size": finding.keySize,
        }

    return props


def _evidence_for(finding: Finding) -> dict[str, Any]:
    occurrence: dict[str, Any] = {"location": finding.location.path, "symbol": finding.symbol}
    if finding.location.line is not None:
        occurrence["line"] = finding.location.line
    if finding.location.offset is not None:
        occurrence["offset"] = finding.location.offset
    return {"occurrences": [occurrence]}


def build_cbom(scan: Scan, findings: list[Finding]) -> dict[str, Any]:
    components = [
        {
            "type": "cryptographic-asset",
            "bom-ref": finding.id,
            "name": finding.displayName,
            "cryptoProperties": _crypto_properties_for(finding),
            "evidence": _evidence_for(finding),
        }
        for finding in findings
    ]

    return {
        "$schema": "http://cyclonedx.org/schema/bom-1.6.schema.json",
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, scan.id)}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tools": {
                "components": [
                    {"type": "application", "name": "ecdat", "version": "0.1.0-phase0"},
                ],
            },
            "properties": [
                {"name": "ecdat:phase", "value": "0-stub"},
                {"name": "ecdat:scanId", "value": scan.id},
            ],
        },
        "components": components,
    }
