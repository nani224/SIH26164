"""Cloud KMS cryptographic key discovery endpoints (PS clause i)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from api.models import CloudKeyRecord, CloudKeysResponse
from probes.cloud_kms import discover_cloud_keys

router = APIRouter(tags=["cloud"])


ROADMAP_NOTE = (
    "[Roadmap] AWS KMS via LocalStack is actively supported in v1.0. "
    "Azure Key Vault and GCP Cloud HSM are scheduled for v1.1."
)


@router.get("/cloud/keys", response_model=CloudKeysResponse)
def list_cloud_keys(provider: str | None = Query(default=None)) -> CloudKeysResponse:  # noqa: B008
    """Discover cryptographic keys from cloud providers (AWS KMS via LocalStack)."""
    keys: list[CloudKeyRecord] = discover_cloud_keys(provider=provider)
    return CloudKeysResponse(
        keys=keys,
        roadmap=ROADMAP_NOTE,
    )

