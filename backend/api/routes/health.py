from datetime import UTC, datetime

from fastapi import APIRouter

from api.models import HealthStatus

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def health() -> HealthStatus:
    return HealthStatus(status="ok", version="0.1.0-phase0", time=datetime.now(UTC))
