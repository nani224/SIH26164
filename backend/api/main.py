"""ECDAT backend — Phase 0 FastAPI skeleton.

Every route here returns in-memory stub data (see api/stub_data.py). There
is no real detection engine, persistence, auth, or CORS hardening yet --
those are later phases (see backend/PLAN.md). This app exists so the
frontend has a real, contract-shaped API to integrate against from day 1.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from api.routes import catalog, findings, health, policies, scans

structlog.configure(processors=[structlog.processors.JSONRenderer()])
log = structlog.get_logger("ecdat.api")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    log.info("ecdat_api_startup", phase="0")
    yield


app = FastAPI(
    title="ECDAT API",
    version="0.1.0-phase0",
    description="Enterprise Cryptographic Discovery & Analysis Tool (SIH26164) — Phase 0 contract skeleton.",
    lifespan=lifespan,
)

for router in (health.router, scans.router, findings.router, policies.router, catalog.router):
    app.include_router(router, prefix="/api/v1")


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    content = {"error": exc.__class__.__name__, "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content=content)
