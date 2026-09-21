"""Hardware Security Module (SoftHSM2 / PKCS#11) inventory endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from api.models import HsmInventory
from probes.hsm import get_hsm_inventory

router = APIRouter(tags=["hsm"])


@router.get("/hsm/inventory", response_model=HsmInventory)
def get_inventory() -> HsmInventory:
    """Enumerate PKCS#11 / SoftHSM2 cryptographic keys and slots."""
    return get_hsm_inventory()
