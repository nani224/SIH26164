"""Actor identity tracking on the audit chain for ECDAT API.

Phase: Production Hardening (M3).
Enforces X-ECDAT-Actor header on state-changing operations and propagates
to audit log records.
"""

from __future__ import annotations

import contextvars

from fastapi import HTTPException, Request

current_actor_var: contextvars.ContextVar[str] = contextvars.ContextVar("current_actor", default="system")


def get_current_actor() -> str:
    """Retrieve the current operator actor identity."""
    return current_actor_var.get()


def set_current_actor(actor: str) -> None:
    """Set the operator actor identity for the current request context."""
    current_actor_var.set(actor)


async def require_actor_on_write(request: Request) -> str:
    """FastAPI dependency enforcing X-ECDAT-Actor header on state-changing requests.

    Missing header on a write returns 400 with a clear message.
    Read requests (GET, HEAD, OPTIONS) do not require it.
    """
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        actor = request.headers.get("x-ecdat-actor")
        if not actor or not actor.strip():
            raise HTTPException(
                status_code=400,
                detail="X-ECDAT-Actor header is required for state-changing requests",
            )
        clean_actor = actor.strip()
        set_current_actor(clean_actor)
        return clean_actor
    return "system"
