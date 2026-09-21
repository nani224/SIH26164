"""Integration tests for live probe adapters, air-gap destination guard,
and findings reconciliation.
"""

from __future__ import annotations

import http.server
import socket
import ssl
import tempfile
import threading
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient

from api import db, store
from api.db_models import FindingRecord, TargetRecord
from api.main import app
from api.models import (
    CryptoFunction,
    FindingKind,
    FindingSource,
    ProbeProtocol,
    ProbeResult,
    Surface,
    TargetCreate,
    TargetKind,
    TriageStatus,
)
from probes.guard import SecurityException, is_allowed_host, validate_probe_destination
from probes.reconciler import extract_negotiated_tokens, reconcile_probe_findings
from probes.ssh import probe_ssh
from probes.tls import probe_tls


def _generate_test_cert(cert_path: str, key_path: str) -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(days=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=30))
        .sign(key, hashes.SHA256())
    )
    with open(key_path, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))


@pytest.fixture(scope="module")
def tls_server() -> Generator[tuple[str, int], None, None]:
    """Spins up a lightweight in-process HTTPS server with a valid self-signed cert."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cert_file = f"{tmpdir}/cert.pem"
        key_file = f"{tmpdir}/key.pem"
        _generate_test_cert(cert_file, key_file)

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args: object) -> None:
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), QuietHandler)
        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_ctx.load_cert_chain(certfile=cert_file, keyfile=key_file)
        server.socket = ssl_ctx.wrap_socket(server.socket, server_side=True)
        port = server.server_address[1]

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield ("127.0.0.1", port)
        finally:
            server.shutdown()
            server.server_close()


def test_destination_guard_allows_safe_destinations() -> None:
    for host in (
        "localhost",
        "127.0.0.1",
        "::1",
        "test-target-legacy-tls",
        "test-target-modern-tls",
        "test-target-legacy-ssh",
    ):
        assert is_allowed_host(host) is True
        validate_probe_destination(host)


def test_destination_guard_rejects_external() -> None:
    for forbidden in ("google.com", "8.8.8.8", "example.com", "1.1.1.1", "api.github.com"):
        assert is_allowed_host(forbidden) is False
        with pytest.raises(SecurityException, match="air-gap policy"):
            validate_probe_destination(forbidden)


def test_tls_probe_live_endpoint(tls_server: tuple[str, int]) -> None:
    host, port = tls_server
    target_id = f"tgt_{uuid4().hex[:8]}"

    result = probe_tls(host=host, port=port, target_id=target_id)
    assert result.targetId == target_id
    assert result.protocol == ProbeProtocol.TLS
    assert result.host == host
    assert result.port == port

    # Semantic distinction invariant: negotiated is a single configuration dict,
    # while supported is a list of candidate cipher suites
    assert isinstance(result.negotiated, dict)
    assert isinstance(result.supported, list)
    assert not isinstance(result.supported, dict)

    assert "cipher" in result.negotiated
    assert "protocol" in result.negotiated
    assert len(result.supported) >= 1


def test_ssh_probe_airgap_and_connection_error() -> None:
    # Air-gap rejection
    with pytest.raises(SecurityException):
        probe_ssh(host="evil.external.host", port=22, target_id="tgt_err")

    # Connection error on closed port
    s = socket.socket()
    s.bind(("", 0))
    free_port = s.getsockname()[1]
    s.close()

    with pytest.raises(ConnectionError):
        probe_ssh(host="127.0.0.1", port=free_port, target_id="tgt_err")


def test_negotiated_token_extraction() -> None:
    negotiated = {
        "protocol": "TLSv1.3",
        "cipher": "TLS_AES_256_GCM_SHA384",
        "kex": "curve25519-sha256",
    }
    tokens = extract_negotiated_tokens(negotiated)
    assert "tlsaes256gcmsha384" in tokens
    assert "aes" in tokens
    assert "256" in tokens
    assert "gcm" in tokens
    assert "curve25519sha256" in tokens


def test_probe_reconciler_updates_findings() -> None:
    scan_id = f"scn_probe_{uuid4().hex[:8]}"
    target_id = f"tgt_probe_{uuid4().hex[:8]}"

    # Setup target and finding
    with db.session_scope() as session:
        target = TargetRecord(
            id=target_id,
            name="Probe Test Target",
            kind="endpoint",
            uri="https://127.0.0.1:8443",
            policy_id="pol_default",
            schedule="0 0 * * *",
            last_scan_id=scan_id,
        )
        session.add(target)

        finding = FindingRecord(
            id=f"fnd_{uuid4().hex[:8]}",
            scan_id=scan_id,
            kind=FindingKind.ALGORITHM.value,
            surface=Surface.CONFIG.value,
            family="AES",
            display_name="AES-256-GCM in TLS",
            symbol="TLS_AES_256_GCM_SHA384",
            snippet="ssl_ciphers TLS_AES_256_GCM_SHA384;",
            function=CryptoFunction.ENCRYPT.value,
            location_path="config/tls.conf",
            location_line=10,
            location_offset=0,
            source=FindingSource.CONFIG_PARSER.value,
            confidence=1.0,
            triage_status=TriageStatus.OPEN.value,
            negotiated=None,
        )
        session.add(finding)
        session.commit()
        f_id = finding.id

    # Create ProbeResult that matched the cipher
    probe_result = ProbeResult(
        id=f"prb_{uuid4().hex[:8]}",
        targetId=target_id,
        host="127.0.0.1",
        port=8443,
        protocol=ProbeProtocol.TLS,
        negotiated={"protocol": "TLSv1.3", "cipher": "TLS_AES_256_GCM_SHA384"},
        supported=[{"protocol": "TLSv1.3", "cipher": "TLS_AES_256_GCM_SHA384"}],
        probedAt=datetime.now(UTC),
    )

    reconciled = reconcile_probe_findings(target_id, probe_result)
    assert reconciled >= 1

    # Verify finding.negotiated was updated to True
    with db.session_scope() as session:
        updated = session.get(FindingRecord, f_id)
        assert updated is not None
        assert updated.negotiated is True


def test_probes_api_endpoints(tls_server: tuple[str, int]) -> None:
    client = TestClient(app)
    host, port = tls_server

    # 1. External target rejected via 400
    res = client.post(
        "/api/v1/probes/tls",
        json={"targetId": "tgt_ext", "host": "google.com", "port": 443},
    )
    assert res.status_code == 400
    assert "air-gap" in res.json()["message"]

    # 2. Localhost probe succeeds
    target = store.create_target(
        TargetCreate(
            name="Local TLS",
            kind=TargetKind.ENDPOINT,
            uri=f"https://{host}:{port}",
            policyId="pol_default",
            schedule="0 0 * * *",
        )
    )

    res = client.post(
        "/api/v1/probes/tls",
        json={"targetId": target.id, "host": host, "port": port},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["targetId"] == target.id
    assert body["protocol"] == "tls"
    assert "cipher" in body["negotiated"]

    # 3. List probe results
    res_list = client.get(f"/api/v1/probes?targetId={target.id}")
    assert res_list.status_code == 200
    results = res_list.json()
    assert len(results) >= 1
    assert results[0]["id"] == body["id"]
