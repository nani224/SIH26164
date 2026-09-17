from fastapi import APIRouter, HTTPException

from api import store
from api.models import ErrorDetail, Policy

router = APIRouter()


@router.get("/policies", response_model=list[Policy])
async def list_policies() -> list[Policy]:
    return store.list_policies()


@router.put("/policies", response_model=Policy)
async def upsert_policy(policy: Policy) -> Policy:
    return store.put_policy(policy)


@router.get("/policies/{policy_id}", response_model=Policy, responses={404: {"model": ErrorDetail}})
async def get_policy(policy_id: str) -> Policy:
    policy = store.get_policy(policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="policy not found")
    return policy


@router.put("/policies/{policy_id}", response_model=Policy)
async def put_policy(policy_id: str, policy: Policy) -> Policy:
    if policy.id != policy_id:
        raise HTTPException(status_code=400, detail="policy id in body must match path")
    return store.put_policy(policy)
