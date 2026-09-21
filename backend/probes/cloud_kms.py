from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import structlog

from api.models import CloudKeyRecord
from probes.guard import validate_probe_destination

if TYPE_CHECKING:
    from api.models import Finding

log = structlog.get_logger("ecdat.probes.cloud_kms")


def discover_cloud_keys(provider: str | None = None) -> list[CloudKeyRecord]:
    """Discover cryptographic keys from AWS KMS via LocalStack.

    If provider is specified and not 'aws', returns an empty list.
    Degrades cleanly if LocalStack endpoint is unreachable.
    """
    if provider is not None and provider.lower() not in ("aws", "localstack"):
        return []

    endpoint_url = os.environ.get("LOCALSTACK_ENDPOINT_URL", "http://localhost:4566")
    region_name = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

    # Air-gap destination validation
    try:
        host = urlparse(endpoint_url).hostname or "localhost"
        validate_probe_destination(host)
    except Exception as exc:
        log.warning("cloud_kms_probe_destination_rejected", endpoint=endpoint_url, error=str(exc))
        return []

    records: list[CloudKeyRecord] = []

    try:
        import boto3  # type: ignore[import-not-found]
        from botocore.config import Config  # type: ignore[import-not-found]

        client = boto3.client(
            "kms",
            endpoint_url=endpoint_url,
            region_name=region_name,
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "test"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
            config=Config(connect_timeout=1, read_timeout=2, retries={"max_attempts": 1}),
        )

        resp = client.list_keys(Limit=100)
        for k in resp.get("Keys", []):
            key_id = k.get("KeyId", "")
            try:
                desc = client.describe_key(KeyId=key_id).get("KeyMetadata", {})
                spec = desc.get("KeySpec") or desc.get("CustomerMasterKeySpec", "SYMMETRIC_DEFAULT")
                created = desc.get("CreationDate", datetime.now(UTC))
                age_days = (
                    max(0, (datetime.now(UTC) - created).days)
                    if isinstance(created, datetime)
                    else 0
                )

                if "SYMMETRIC" in spec:
                    algo = "AES-GCM"
                    key_size = 256
                elif "RSA" in spec:
                    algo = "RSA"
                    parts = spec.split("_")
                    key_size = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 2048
                elif "ECC" in spec:
                    algo = "ECDSA"
                    if "384" in spec:
                        key_size = 384
                    elif "521" in spec:
                        key_size = 521
                    else:
                        key_size = 256
                elif "HMAC" in spec:
                    algo = "HMAC"
                    parts = spec.split("_")
                    key_size = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 256
                else:
                    algo = spec
                    key_size = 256

                identity_id = desc.get("Arn")
                # When public key material is available, fingerprint it into identityId
                try:
                    pub_resp = client.get_public_key(KeyId=key_id)
                    pub_bytes = pub_resp.get("PublicKey")
                    if pub_bytes:
                        identity_id = f"sha256:{hashlib.sha256(pub_bytes).hexdigest()}"
                except Exception:
                    pass

                records.append(
                    CloudKeyRecord(
                        provider="aws",
                        keyId=key_id,
                        algorithm=algo,
                        keySize=key_size,
                        rotationAgeDays=age_days,
                        policyCompliant=age_days <= 90,
                        identityId=identity_id,
                    )
                )
            except Exception as exc:
                log.debug("kms_describe_key_failed", key_id=key_id, error=str(exc))

    except Exception as exc:
        log.info("localstack_kms_unavailable_clean_degrade", endpoint=endpoint_url, error=str(exc))

    return records


def join_cloud_keys_to_findings(
    keys: list[CloudKeyRecord],
    findings: list[Finding],
) -> list[tuple[CloudKeyRecord, Finding]]:
    """Join discovered cloud keys to static/runtime findings by identityId or keyId.

    Matches:
    1. Exact match on identityId (e.g. public key sha256 or ARN).
    2. KeyId substring match against finding's symbol, location path, or snippet.
    """
    matches: list[tuple[CloudKeyRecord, Finding]] = []
    for k in keys:
        for f in findings:
            fields = (
                f.symbol or "",
                (f.location.path if f.location else "") or "",
                f.snippet or "",
            )
            matched = bool(
                (k.identityId and any(k.identityId in field for field in fields))
                or (k.keyId and any(k.keyId in field for field in fields))
            )

            if matched:
                matches.append((k, f))
    return matches
