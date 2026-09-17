from fastapi import APIRouter, HTTPException

from api import stub_data
from api.models import ErrorDetail, Finding, Triage, TriagePatch

router = APIRouter()


@router.patch(
    "/findings/{finding_id}/triage",
    response_model=Finding,
    responses={404: {"model": ErrorDetail}},
)
async def patch_triage(finding_id: str, patch: TriagePatch) -> Finding:
    finding = stub_data.get_finding(finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="finding not found")
    updated = finding.model_copy(update={"triage": Triage(status=patch.status, note=patch.note)})
    stub_data.replace_finding(finding_id, updated)
    return updated
