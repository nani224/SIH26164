"""SSH endpoint probe adapter using ssh-audit and SSH handshake inspection.

Extracts:
- Active negotiated cryptographic primitives (kex, cipher, mac, host key)
- Complete list of server-supported SSH algorithms
Enforces in-code air-gap guardrail before initiating network connections.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from ssh_audit.auditconf import AuditConf  # type: ignore[import-untyped]
from ssh_audit.outputbuffer import OutputBuffer  # type: ignore[import-untyped]
from ssh_audit.ssh_audit import audit  # type: ignore[import-untyped]

from api.models import ProbeProtocol, ProbeResult
from probes.guard import validate_probe_destination

logger = logging.getLogger(__name__)


def probe_ssh(
    host: str,
    port: int,
    target_id: str,
    timeout: float = 5.0,
) -> ProbeResult:
    """Probe a live SSH service endpoint.

    Validates destination against the air-gap allowlist, connects to the SSH
    daemon, captures the server banner and algorithm lists, and extracts
    negotiated primitives vs. supported algorithms.

    Args:
        host: Target hostname or IP (must be allowed by DestinationGuard).
        port: Target port (typically 22 or 2222).
        target_id: ID of the Target record.
        timeout: Socket timeout in seconds.

    Returns:
        ProbeResult containing negotiated primitives and supported algorithms.
    """
    validate_probe_destination(host)

    aconf = AuditConf(host, port)
    aconf.batch = True
    aconf.json = True
    aconf.timeout = timeout
    # Crucial: target_list prevents ssh-audit from invoking sys.exit on error
    aconf.target_list = [f"{host}:{port}"]

    out = OutputBuffer()
    audit(out, aconf)
    raw_output = out.get_buffer().strip()

    negotiated: dict[str, Any] = {}
    supported: list[dict[str, Any]] = []

    try:
        data = json.loads(raw_output)
        banner = data.get("banner", {})
        raw_banner = banner.get("raw") if isinstance(banner, dict) else str(banner)

        # Supported algorithms by category
        kex_list = data.get("kex", [])
        enc_list = data.get("enc", [])
        mac_list = data.get("mac", [])
        key_list = data.get("key", [])

        for item in kex_list:
            name = item.get("algorithm") if isinstance(item, dict) else str(item)
            supported.append({"type": "kex", "algorithm": name})

        for item in enc_list:
            name = item.get("algorithm") if isinstance(item, dict) else str(item)
            supported.append({"type": "cipher", "algorithm": name})

        for item in mac_list:
            name = item.get("algorithm") if isinstance(item, dict) else str(item)
            supported.append({"type": "mac", "algorithm": name})

        for item in key_list:
            name = item.get("algorithm") if isinstance(item, dict) else str(item)
            supported.append({"type": "host_key", "algorithm": name})

        first_kex = kex_list[0].get("algorithm") if kex_list and isinstance(kex_list[0], dict) else (
            kex_list[0] if kex_list else None
        )
        first_enc = enc_list[0].get("algorithm") if enc_list and isinstance(enc_list[0], dict) else (
            enc_list[0] if enc_list else None
        )
        first_mac = mac_list[0].get("algorithm") if mac_list and isinstance(mac_list[0], dict) else (
            mac_list[0] if mac_list else None
        )
        first_key = key_list[0].get("algorithm") if key_list and isinstance(key_list[0], dict) else (
            key_list[0] if key_list else None
        )

        negotiated = {
            "banner": raw_banner,
            "kex": first_kex,
            "cipher": first_enc,
            "mac": first_mac,
            "hostKey": first_key,
        }
    except Exception as exc:
        logger.warning("Failed to parse ssh-audit output as JSON: %s. Output: %s", exc, raw_output[:200])
        # If connection failed or produced non-json, return error indication or raise
        if "[exception]" in raw_output or "cannot connect" in raw_output:
            raise ConnectionError(f"SSH probe connection failed: {raw_output}") from exc

    return ProbeResult(
        id=f"prb_{uuid4().hex[:12]}",
        targetId=target_id,
        host=host,
        port=port,
        protocol=ProbeProtocol.SSH,
        negotiated=negotiated,
        supported=supported,
        probedAt=datetime.now(UTC),
    )
