"""Local container registry scanner.

Strictly restricted to localhost:5000 (air-gap enforced).
Extracts and inspects cryptographic artifacts (certificates, private keys,
and TLS configurations) embedded in container layers.
"""

from __future__ import annotations

import io
import logging
import tarfile
from urllib.parse import urlparse
from uuid import uuid4

import httpx

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
from probes.guard import SecurityException

logger = logging.getLogger(__name__)

ALLOWED_REGISTRY_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def validate_registry_endpoint(registry_url: str) -> None:
    """Validate that the registry endpoint is strictly a local registry."""
    parsed = urlparse(registry_url)
    host = parsed.hostname or ""
    if not host or host.lower() not in ALLOWED_REGISTRY_HOSTS:
        raise SecurityException(
            f"Registry endpoint '{registry_url}' is prohibited: air-gap policy strictly restricts "
            f"container registry scanning to localhost (e.g. localhost:5000)."
        )


def scan_layer_tar(tar_bytes: bytes, image_ref: str) -> list[Finding]:
    """Scan a container layer tarball for cryptographic assets."""
    findings: list[Finding] = []
    try:
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:*") as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue

                name_lower = member.name.lower()
                # Check for cryptographic assets
                if (
                    name_lower.endswith((".pem", ".crt", ".key", ".cer", ".p12", ".pfx"))
                    or "id_rsa" in name_lower
                    or "id_ecdsa" in name_lower
                    or "id_ed25519" in name_lower
                ):
                    f_extract = tar.extractfile(member)
                    snippet = ""
                    if f_extract:
                        header = f_extract.read(256)
                        snippet = header.decode("utf-8", errors="replace").strip()

                    findings.append(
                        Finding(
                            id=f"fnd_img_{uuid4().hex[:8]}",
                            kind=FindingKind.KEY if "key" in name_lower else FindingKind.CERTIFICATE,
                            surface=Surface.IMAGE,
                            family=None,
                            displayName=f"Container crypto asset: {member.name}",
                            function=CryptoFunction.ENCRYPT,
                            location=Location(path=f"{image_ref}:{member.name}", line=1, offset=0),
                            symbol=member.name,
                            snippet=snippet[:100],
                            source=FindingSource.PEM_PARSER,
                            confidence=0.95,
                            triage=Triage(status=TriageStatus.OPEN),
                        )
                    )
    except Exception as exc:
        logger.warning("Error inspecting layer tar for %s: %s", image_ref, exc)

    return findings


def scan_local_registry_image(
    image_name: str,
    tag: str = "latest",
    registry_url: str = "http://localhost:5000",
) -> list[Finding]:
    """Scan an image from the local Docker registry.

    Validates air-gap policy, fetches the image manifest, and inspects layers.
    """
    validate_registry_endpoint(registry_url)

    manifest_url = f"{registry_url}/v2/{image_name}/manifests/{tag}"
    findings: list[Finding] = []

    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(
                manifest_url,
                headers={"Accept": "application/vnd.docker.distribution.manifest.v2+json"},
            )
            if resp.status_code != 200:
                logger.info("Manifest not found or registry unavailable at %s: %d", manifest_url, resp.status_code)
                return []

            data = resp.json()
            layers = data.get("layers", [])
            for layer in layers:
                digest = layer.get("digest")
                if not digest:
                    continue
                layer_url = f"{registry_url}/v2/{image_name}/blobs/{digest}"
                blob_resp = client.get(layer_url)
                if blob_resp.status_code == 200:
                    findings.extend(scan_layer_tar(blob_resp.content, f"{image_name}:{tag}"))

    except Exception as exc:
        logger.warning("Registry scan failed for %s:%s at %s: %s", image_name, tag, registry_url, exc)

    return findings
