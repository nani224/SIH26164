from fastapi import APIRouter

from api.models import PqcCatalogEntry
from api.stub_data import PQC_CATALOG

router = APIRouter()


@router.get("/catalog/pqc", response_model=list[PqcCatalogEntry])
async def get_pqc_catalog() -> list[PqcCatalogEntry]:
    return PQC_CATALOG
