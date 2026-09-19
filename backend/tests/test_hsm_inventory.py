"""Tests for SoftHSM2 PKCS#11 inventory probe and air-gapped container registry scanning."""

from __future__ import annotations

import io
import tarfile
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.models import FindingKind, Surface
from probes.guard import SecurityException
from probes.hsm import get_hsm_inventory
from probes.registry import scan_layer_tar, validate_registry_endpoint


def test_hsm_inventory_fallback_on_missing_lib() -> None:
    inventory = get_hsm_inventory(lib_path="/nonexistent/path/to/softhsm2.so")
    assert inventory.slots == []


def test_hsm_inventory_with_pkcs11_mock() -> None:
    from pkcs11 import Attribute, KeyType

    def mock_lookup(attr: Any) -> Any:
        if attr == Attribute.KEY_TYPE:
            return KeyType.RSA
        if attr == Attribute.LABEL:
            return "prod-signing-key"
        if attr == Attribute.MODULUS_BITS:
            return 2048
        return None

    mock_obj = MagicMock()
    mock_obj.__getitem__.side_effect = mock_lookup

    mock_session = MagicMock()
    mock_session.__enter__.return_value.get_objects.return_value = [mock_obj]

    mock_token = MagicMock()
    mock_token.label = "Production Token"
    mock_token.open.return_value = mock_session

    mock_slot = MagicMock()
    mock_slot.slot_id = 1
    mock_slot.get_token.return_value = mock_token

    mock_lib = MagicMock()
    mock_lib.get_slots.return_value = [mock_slot]

    with patch("pkcs11.lib", return_value=mock_lib), patch("os.path.isfile", return_value=True):
        inventory = get_hsm_inventory(lib_path="mock_softhsm2.dll")
        assert len(inventory.slots) == 1
        slot = inventory.slots[0]
        assert slot.slot == 1
        assert slot.label == "Production Token"
        assert len(slot.keys) == 1
        assert slot.keys[0].label == "prod-signing-key"
        assert slot.keys[0].size == 2048


def test_registry_airgap_validation() -> None:
    # Allowed local endpoints
    validate_registry_endpoint("http://localhost:5000")
    validate_registry_endpoint("http://127.0.0.1:5000")

    # Rejected public registries
    with pytest.raises(SecurityException, match="air-gap policy"):
        validate_registry_endpoint("https://registry-1.docker.io")

    with pytest.raises(SecurityException, match="air-gap policy"):
        validate_registry_endpoint("https://quay.io")

    with pytest.raises(SecurityException, match="air-gap policy"):
        validate_registry_endpoint("https://ghcr.io")


def test_scan_layer_tar_extracts_crypto_assets() -> None:
    # Build synthetic in-memory tarball containing crypto files
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        cert_data = b"-----BEGIN CERTIFICATE-----\nMIIC...TEST\n-----END CERTIFICATE-----\n"
        cert_info = tarfile.TarInfo(name="etc/ssl/certs/server.crt")
        cert_info.size = len(cert_data)
        tar.addfile(cert_info, io.BytesIO(cert_data))

        key_data = b"-----BEGIN RSA PRIVATE KEY-----\nMIIE...SECRET\n-----END RSA PRIVATE KEY-----\n"
        key_info = tarfile.TarInfo(name="etc/ssl/private/server.key")
        key_info.size = len(key_data)
        tar.addfile(key_info, io.BytesIO(key_data))

    tar_bytes = buf.getvalue()
    findings = scan_layer_tar(tar_bytes, "myapp:v1")

    assert len(findings) == 2
    for f in findings:
        assert f.surface == Surface.IMAGE
        assert f.kind in (FindingKind.CERTIFICATE, FindingKind.KEY)
        assert "myapp:v1:etc/ssl" in f.location.path


def test_hsm_api_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/api/v1/hsm/inventory")
    assert resp.status_code == 200
    body = resp.json()
    assert "slots" in body
    assert isinstance(body["slots"], list)
