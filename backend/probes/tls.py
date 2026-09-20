"""TLS endpoint probe adapter using sslyze and direct TLS socket handshake.

Extracts:
- Active negotiated cipher suite and protocol version
- Peer certificate expiration and algorithm details
- Complete list of server-supported cipher suites
Enforces in-code air-gap guardrail before initiating network connections.
"""

from __future__ import annotations

import socket
import ssl
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sslyze import (  # type: ignore[attr-defined]
    ScanCommand,
    Scanner,
    ServerNetworkLocation,
    ServerScanRequest,
    ServerScanStatusEnum,
)

from api.models import ProbeProtocol, ProbeResult
from probes.guard import validate_probe_destination


def probe_tls(
    host: str,
    port: int,
    target_id: str,
    timeout: float = 5.0,
) -> ProbeResult:
    """Probe a live TLS service endpoint.

    Validates destination against the air-gap allowlist, initiates a TLS
    handshake to capture negotiated parameters, and runs sslyze to enumerate
    supported cipher suites.

    Args:
        host: Target hostname or IP (must be allowed by DestinationGuard).
        port: Target port (e.g. 443, 8443).
        target_id: ID of the Target record.
        timeout: Socket timeout in seconds.

    Returns:
        ProbeResult with negotiated cipher details and supported suites list.
    """
    validate_probe_destination(host)

    negotiated: dict[str, Any] = {}
    supported: list[dict[str, Any]] = []

    # 1. Direct TLS handshake for exact negotiated parameters
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw_sock.settimeout(timeout)
    with raw_sock:
        raw_sock.connect((host, port))
        with ctx.wrap_socket(raw_sock, server_hostname=host) as tls_sock:
            version = tls_sock.version() or "UNKNOWN"
            cipher_info = tls_sock.cipher()
            cipher_name = cipher_info[0] if cipher_info else "UNKNOWN"
            secret_bits = cipher_info[2] if cipher_info else None

            peer_cert = tls_sock.getpeercert() or {}
            not_after = peer_cert.get("notAfter")
            cert_subject = str(peer_cert.get("subject", ""))
            cert_issuer = str(peer_cert.get("issuer", ""))

            if not not_after:
                try:
                    der_cert = tls_sock.getpeercert(binary_form=True)
                    if der_cert:
                        from cryptography import x509
                        parsed = x509.load_der_x509_certificate(der_cert)
                        not_after = parsed.not_valid_after_utc.isoformat()
                        cert_subject = parsed.subject.rfc4514_string()
                        cert_issuer = parsed.issuer.rfc4514_string()
                except Exception:
                    pass

            negotiated = {
                "protocol": version,
                "cipher": cipher_name,
                "secretBits": secret_bits,
                "certSubject": cert_subject,
                "certIssuer": cert_issuer,
                "certNotAfter": not_after,
            }
            # Initial supported entry from the active handshake
            supported.append({
                "protocol": version,
                "cipher": cipher_name,
                "accepted": True,
            })

    # 2. Enumerate supported cipher suites via sslyze
    try:
        location = ServerNetworkLocation(hostname=host, port=port)
        request = ServerScanRequest(
            server_location=location,
            scan_commands={
                ScanCommand.TLS_1_0_CIPHER_SUITES,
                ScanCommand.TLS_1_1_CIPHER_SUITES,
                ScanCommand.TLS_1_2_CIPHER_SUITES,
                ScanCommand.TLS_1_3_CIPHER_SUITES,
            },
        )
        scanner = Scanner()
        scanner.queue_scans([request])
        for result in scanner.get_results():
            if (
                getattr(result, "scan_status", None) == ServerScanStatusEnum.COMPLETED
                and result.scan_result is not None
            ):
                scan_res = result.scan_result
                for attempt in (
                    scan_res.tls_1_0_cipher_suites,
                    scan_res.tls_1_1_cipher_suites,
                    scan_res.tls_1_2_cipher_suites,
                    scan_res.tls_1_3_cipher_suites,
                ):
                    res_obj = getattr(attempt, "result", None)
                    if res_obj and hasattr(res_obj, "accepted_cipher_suites"):
                        for accepted in res_obj.accepted_cipher_suites:
                            suite_name = getattr(accepted.cipher_suite, "name", str(accepted.cipher_suite))
                            tls_ver = getattr(accepted.cipher_suite, "openssl_name", "TLS")
                            suite_dict = {
                                "protocol": tls_ver,
                                "cipher": suite_name,
                                "accepted": True,
                            }
                            if suite_dict not in supported:
                                supported.append(suite_dict)
    except Exception:
        # If sslyze scan commands fail or timeout, the handshake result is preserved
        pass

    return ProbeResult(
        id=f"prb_{uuid4().hex[:12]}",
        targetId=target_id,
        host=host,
        port=port,
        protocol=ProbeProtocol.TLS,
        negotiated=negotiated,
        supported=supported,
        probedAt=datetime.now(UTC),
    )
