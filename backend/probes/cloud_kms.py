from __future__ import annotations

import os
from datetime import UTC, datetime

import structlog

from api.models import CloudKeyRecord

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
                spec = desc.get("CustomerMasterKeySpec", "SYMMETRIC_DEFAULT")
                created = desc.get("CreationDate", datetime.now(UTC))
                age_days = (
                    max(0, (datetime.now(UTC) - created).days)
                    if isinstance(created, datetime)
                    else 0
                )


                algo = "AES-GCM" if "SYMMETRIC" in spec else spec
                key_size = 256 if "SYMMETRIC" in spec else 2048

                records.append(
                    CloudKeyRecord(
                        provider="aws",
                        keyId=key_id,
                        algorithm=algo,
                        keySize=key_size,
                        rotationAgeDays=age_days,
                        policyCompliant=age_days <= 90,
                        identityId=desc.get("Arn"),
                    )
                )
            except Exception as exc:
                log.debug("kms_describe_key_failed", key_id=key_id, error=str(exc))

    except Exception as exc:
        log.info("localstack_kms_unavailable_clean_degrade", endpoint=endpoint_url, error=str(exc))

    return records
