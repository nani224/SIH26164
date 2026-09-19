"""Alert endpoints: querying active/historical alerts and acknowledging them."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from api import store
from api.models import Alert

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=list[Alert])
def list_alerts(acknowledged: bool | None = Query(default=None)) -> list[Alert]:
    """List historical and active alerts, optionally filtered by acknowledgment status."""
    return store.list_alerts(acknowledged=acknowledged)


@router.patch("/alerts/{id}/acknowledge", response_model=Alert)
def acknowledge_alert(id: str) -> Alert:
    """Acknowledge an alert."""
    alert = store.acknowledge_alert(id)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {id} not found",
        )
    return alert
