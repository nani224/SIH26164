"""ECDAT backend — FastAPI app.

Scans/findings/policies are persisted (SQLModel + SQLite, api/db.py) as of
Phase 2. There is still no real detection engine wired in (POST /scans
still returns stub-shaped data -- that's Phase 3), no auth, no CORS
hardening (Phase 10). See docs/engineering/backend/PLAN.md.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import db
from api.rate_limiter import RateLimitMiddleware
from api.routes import (
    alerts,
    audit,
    catalog,
    cloud,
    coverage,
    criticality,
    estate,
    findings,
    health,
    hsm,
    policies,
    probes,
    residue,
    scans,
    targets,
)

structlog.configure(processors=[structlog.processors.JSONRenderer()])
log = structlog.get_logger("ecdat.api")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    db.init_db()
    try:
        from scheduler.engine import shutdown_scheduler, start_scheduler
        start_scheduler()
    except Exception as exc:
        log.warning("scheduler_startup_failed", error=str(exc))
    log.info("ecdat_api_startup", phase="v1.0")
    try:
        yield
    finally:
        try:
            from scheduler.engine import shutdown_scheduler
            shutdown_scheduler()
        except Exception:
            pass


app = FastAPI(
    title="ECDAT API",
    version="1.0.0",
    description="Enterprise Cryptographic Discovery & Analysis Tool (SIH26164) — v1.0 Crypto Mass Conservation (CMC).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

for router in (
    health.router, scans.router, findings.router, policies.router,
    catalog.router, targets.router, probes.router, alerts.router,
    hsm.router, audit.router, estate.router,
    coverage.router, residue.router, criticality.router, cloud.router,
):
    app.include_router(router, prefix="/api/v1")



@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    content = {"error": exc.__class__.__name__, "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content=content)
