"""ECDAT backend — FastAPI app.

Scans/findings/policies are persisted (SQLModel + SQLite, api/db.py) as of
Phase 2. There is still no real detection engine wired in (POST /scans
still returns stub-shaped data -- that's Phase 3), no auth, no CORS
hardening (Phase 10). See backend/PLAN.md.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from api import db
from api.rate_limiter import RateLimitMiddleware
from api.routes import catalog, findings, health, policies, scans

structlog.configure(processors=[structlog.processors.JSONRenderer()])
log = structlog.get_logger("ecdat.api")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    db.init_db()
    log.info("ecdat_api_startup", phase="2")
    yield


app = FastAPI(
    title="ECDAT API",
    version="0.2.0-phase2",
    description="Enterprise Cryptographic Discovery & Analysis Tool (SIH26164) — Phase 2 persistence.",
    lifespan=lifespan,
)

app.add_middleware(RateLimitMiddleware)

for router in (health.router, scans.router, findings.router, policies.router, catalog.router):
    app.include_router(router, prefix="/api/v1")


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    content = {"error": exc.__class__.__name__, "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content=content)
