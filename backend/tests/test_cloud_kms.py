"""Tests for M6 — AWS KMS Cloud Key Discovery via LocalStack (PS clause i).

Verifies:
1. Enumerate keys with algorithm, size, creation date, rotation age, policy compliance.
2. Join to findings by identityId where public key is available.
3. Clean degradation when LocalStack is unreachable (empty keys + roadmap note).
4. Roadmap note is visible in API response.
5. In-code air-gap destination guard blocks non-allowlisted endpoints.
"""

from __future__ import annotations

import hashlib
import sys
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.models import (
    CryptoFunction,
    Finding,
    FindingKind,
    FindingSource,
    Location,
    Surface,
    Triage,
    TriageStatus,
)
from probes.cloud_kms import discover_cloud_keys, join_cloud_keys_to_findings
from probes.guard import SecurityException, validate_probe_destination

client = TestClient(app)


def test_cloud_keys_endpoint_degrades_cleanly_when_unreachable() -> None:
    """Unreachable LocalStack degrades cleanly without 500 error, returning roadmap note."""
    with patch.dict("os.environ", {"LOCALSTACK_ENDPOINT_URL": "http://localhost:59999"}):
        resp = client.get("/api/v1/cloud/keys")
        assert resp.status_code == 200
        body = resp.json()
        assert body["keys"] == []
        assert "[Roadmap]" in body["roadmap"]
        assert "AWS KMS via LocalStack" in body["roadmap"]
        assert "Azure Key Vault" in body["roadmap"]


def test_cloud_keys_unsupported_provider_returns_empty() -> None:
    """Non-AWS provider returns empty list and roadmap note."""
    resp = client.get("/api/v1/cloud/keys?provider=azure")
    assert resp.status_code == 200
    body = resp.json()
    assert body["keys"] == []
    assert "[Roadmap]" in body["roadmap"]


def test_cloud_kms_airgap_destination_guard() -> None:
    """Attempting to probe external/non-allowlisted endpoint is rejected by guard."""
    with patch.dict("os.environ", {"LOCALSTACK_ENDPOINT_URL": "https://kms.us-east-1.amazonaws.com"}):
        # discover_cloud_keys should log and degrade cleanly to []
        records = discover_cloud_keys()
        assert records == []

    with pytest.raises(SecurityException, match="air-gap policy"):
        validate_probe_destination("kms.us-east-1.amazonaws.com")


def test_cloud_kms_enumerates_real_key_records_with_boto3_mock() -> None:
    """Simulates real LocalStack KMS returning symmetric and asymmetric keys."""
    mock_boto3 = MagicMock()
    mock_kms_client = MagicMock()
    mock_boto3.client.return_value = mock_kms_client

    # Key 1: Symmetric AES-256 key, created 20 days ago (compliant <= 90 days)
    created_sym = datetime.now(UTC) - timedelta(days=20)
    # Key 2: Asymmetric RSA-2048 key, created 100 days ago (non-compliant > 90 days)
    created_rsa = datetime.now(UTC) - timedelta(days=100)
    pub_key_bytes = b"fake-rsa-public-key-der-bytes-12345"
    expected_rsa_fingerprint = f"sha256:{hashlib.sha256(pub_key_bytes).hexdigest()}"

    mock_kms_client.list_keys.return_value = {
        "Keys": [
            {"KeyId": "key-sym-001", "KeyArn": "arn:aws:kms:us-east-1:000000000000:key/key-sym-001"},
            {"KeyId": "key-rsa-002", "KeyArn": "arn:aws:kms:us-east-1:000000000000:key/key-rsa-002"},
        ]
    }

    def mock_describe_key(KeyId: str) -> dict[str, Any]:
        if KeyId == "key-sym-001":
            return {
                "KeyMetadata": {
                    "KeyId": "key-sym-001",
                    "Arn": "arn:aws:kms:us-east-1:000000000000:key/key-sym-001",
                    "KeySpec": "SYMMETRIC_DEFAULT",
                    "CreationDate": created_sym,
                }
            }
        elif KeyId == "key-rsa-002":
            return {
                "KeyMetadata": {
                    "KeyId": "key-rsa-002",
                    "Arn": "arn:aws:kms:us-east-1:000000000000:key/key-rsa-002",
                    "KeySpec": "RSA_2048",
                    "CreationDate": created_rsa,
                }
            }
        return {}

    def mock_get_public_key(KeyId: str) -> dict[str, Any]:
        if KeyId == "key-rsa-002":
            return {"PublicKey": pub_key_bytes}
        raise Exception("Not an asymmetric key")

    mock_kms_client.describe_key.side_effect = mock_describe_key
    mock_kms_client.get_public_key.side_effect = mock_get_public_key

    with patch.dict(sys.modules, {"boto3": mock_boto3, "botocore.config": MagicMock()}):
        keys = discover_cloud_keys()

        assert len(keys) == 2

        # Verify symmetric key
        k_sym = keys[0]
        assert k_sym.provider == "aws"
        assert k_sym.keyId == "key-sym-001"
        assert k_sym.algorithm == "AES-GCM"
        assert k_sym.keySize == 256
        assert k_sym.rotationAgeDays == 20
        assert k_sym.policyCompliant is True
        assert k_sym.identityId == "arn:aws:kms:us-east-1:000000000000:key/key-sym-001"

        # Verify asymmetric RSA key
        k_rsa = keys[1]
        assert k_rsa.provider == "aws"
        assert k_rsa.keyId == "key-rsa-002"
        assert k_rsa.algorithm == "RSA"
        assert k_rsa.keySize == 2048
        assert k_rsa.rotationAgeDays == 100
        assert k_rsa.policyCompliant is False
        assert k_rsa.identityId == expected_rsa_fingerprint

        # Test joining to findings by identityId and keyId
        finding1 = Finding(
            id="find_kms_01",
            kind=FindingKind.KEY,
            surface=Surface.SOURCE,
            family=None,
            displayName="AWS KMS RSA Key Reference",
            function=CryptoFunction.ENCRYPT,
            location=Location(path="src/kms_client.py", line=42),
            symbol=f"kms:{expected_rsa_fingerprint}",
            snippet="kms.get_public_key(KeyId=...)",
            source=FindingSource.AST,
            confidence=1.0,
            triage=Triage(status=TriageStatus.OPEN),
        )

        finding2 = Finding(
            id="find_kms_02",
            kind=FindingKind.KEY,
            surface=Surface.SOURCE,
            family=None,
            displayName="AWS KMS Symmetric Key",
            function=CryptoFunction.ENCRYPT,
            location=Location(path="config/keys.json", line=10),
            symbol="key-sym-001",
            snippet='"kms_key_id": "key-sym-001"',
            source=FindingSource.AST,
            confidence=1.0,
            triage=Triage(status=TriageStatus.OPEN),
        )

        matches = join_cloud_keys_to_findings(keys, [finding1, finding2])
        assert len(matches) == 2
        # First match is k_sym with finding2
        assert matches[0][0].keyId == "key-sym-001"
        assert matches[0][1].id == "find_kms_02"
        # Second match is k_rsa with finding1
        assert matches[1][0].keyId == "key-rsa-002"
        assert matches[1][1].id == "find_kms_01"


def test_api_endpoint_with_mocked_keys() -> None:
    """Verifies GET /api/v1/cloud/keys serializes real records according to contract."""
    from api.models import CloudKeyRecord

    fake_records = [
        CloudKeyRecord(
            provider="aws",
            keyId="arn:aws:kms:us-east-1:123456789012:key/mrk-1234",
            algorithm="AES-GCM",
            keySize=256,
            rotationAgeDays=45,
            policyCompliant=True,
            identityId="arn:aws:kms:us-east-1:123456789012:key/mrk-1234",
        )
    ]

    with patch("api.routes.cloud.discover_cloud_keys", return_value=fake_records):
        resp = client.get("/api/v1/cloud/keys")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["keys"]) == 1
        k = body["keys"][0]
        assert k["provider"] == "aws"
        assert k["keyId"] == "arn:aws:kms:us-east-1:123456789012:key/mrk-1234"
        assert k["algorithm"] == "AES-GCM"
        assert k["keySize"] == 256
        assert k["rotationAgeDays"] == 45
        assert k["policyCompliant"] is True
        assert "[Roadmap]" in body["roadmap"]
