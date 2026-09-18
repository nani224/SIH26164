"""Tests for Phase 8 PQC Catalog and Agility Metrics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from api.models import CryptoFunction, Family, FindingKind, FindingSource, Surface
from engine.models import Detection
from engine.recommend import recommend

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_catalog_endpoint_returns_nist_standardized_pqc(client: TestClient) -> None:
    resp = client.get("/api/v1/catalog/pqc")
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) == 9

    names = {e["displayName"] for e in entries}
    assert "ML-KEM-512" in names
    assert "ML-KEM-768" in names
    assert "ML-KEM-1024" in names
    assert "ML-DSA-44" in names
    assert "ML-DSA-65" in names
    assert "ML-DSA-87" in names
    assert "SLH-DSA-SHA2-128s" in names

    ml_kem_768 = next(e for e in entries if e["displayName"] == "ML-KEM-768")
    assert ml_kem_768["standard"] == "FIPS 203"
    assert ml_kem_768["securityCategory"] == 3
    assert ml_kem_768["publicKeyBytes"] == 1184
    assert ml_kem_768["ciphertextOrSignatureBytes"] == 1088


def test_recommendation_agility_cost_deltas_rsa_2048() -> None:
    d = Detection(
        kind=FindingKind.ALGORITHM,
        surface=Surface.SOURCE,
        family=Family.RSA,
        display_name="RSA keygen",
        function=CryptoFunction.KEYGEN,
        symbol="rsa.generate_private_key",
        confidence=0.9,
        key_size=2048,
        path="test.py",
        line=1,
        snippet="test",
        source=FindingSource.AST,
    )
    rec = recommend(d)
    assert rec is not None
    assert rec.target == "ML-KEM-768"
    assert rec.cost.pkBytesDelta == 1184 - 256
    assert rec.cost.wireBytesDelta == 1088 - 256
    assert rec.cost.opMsDelta == round(0.05 - 0.01, 4)


def test_recommendation_agility_cost_deltas_rsa_4096_upgrades_to_level_5() -> None:
    d = Detection(
        kind=FindingKind.ALGORITHM,
        surface=Surface.SOURCE,
        family=Family.RSA,
        display_name="RSA-4096 keygen",
        function=CryptoFunction.KEYGEN,
        symbol="rsa.generate_private_key",
        confidence=0.9,
        key_size=4096,
        path="test.py",
        line=1,
        snippet="test",
        source=FindingSource.AST,
    )
    rec = recommend(d)
    assert rec is not None
    assert rec.target == "ML-KEM-1024"  # Level 5
    assert rec.cost.pkBytesDelta == 1568 - 512
    assert rec.cost.wireBytesDelta == 1568 - 512


def test_recommendation_agility_cost_deltas_signatures() -> None:
    d = Detection(
        kind=FindingKind.ALGORITHM,
        surface=Surface.SOURCE,
        family=Family.ECDSA,
        display_name="ECDSA signature",
        function=CryptoFunction.SIGN,
        symbol="ecdsa.sign",
        confidence=0.9,
        curve="P256",
        path="test.py",
        line=1,
        snippet="test",
        source=FindingSource.AST,
    )
    rec = recommend(d)
    assert rec is not None
    assert rec.target == "ML-DSA-65"
    assert rec.cost.pkBytesDelta == 1952 - 64
    assert rec.cost.wireBytesDelta == 3309 - 64
