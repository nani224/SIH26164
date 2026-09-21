from datetime import UTC, datetime

from fastapi import APIRouter, Response, status
from sqlmodel import text

from api import db
from api.models import HealthStatus

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthStatus,
    responses={
        503: {
            "description": "Service Unavailable - Database unreachable",
            "model": HealthStatus,
        }
    },
)
def health(response: Response) -> HealthStatus:
    try:
        with db.session_scope() as session:
            session.execute(text("SELECT 1"))
        return HealthStatus(
            status="ok",
            version="1.0.1",
            engine_version="v1.0-cmc",
            rule_set_version="v1.0.1",
            database="connected",
            time=datetime.now(UTC),
        )
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthStatus(
            status="unavailable",
            version="1.0.1",
            engine_version="v1.0-cmc",
            rule_set_version="v1.0.1",
            database="disconnected",
            time=datetime.now(UTC),
        )
