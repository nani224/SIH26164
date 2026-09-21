# Install

Two supported paths. Native is what this project's own verification
passes have actually run end-to-end; Docker is correct for a normal
deployment host but has a known limitation in network-restricted
sandboxes (see below).

## Prerequisites

- **Python 3.12** with [`uv`](https://docs.astral.sh/uv/)
- **Node.js 20+** with `pnpm`
- **Docker Compose v2** (optional, for the containerized path)

## Option 1 — Native (no Docker)

```bash
# Backend
cd backend
uv sync
uv run python scripts/demo_seed.py      # seeds a real scan into a local SQLite file
uv run uvicorn api.main:app --port 8000

# Frontend (separate shell)
cd frontend
pnpm install
# MSW must be off at BUILD time -- Next.js inlines NEXT_PUBLIC_* vars, not at runtime
NODE_ENV=production NEXT_PUBLIC_ENABLE_MSW=false NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 pnpm build
pnpm start
```

Open `http://localhost:3000`. API + interactive docs at
`http://localhost:8000/docs`.

For local development instead of a production build, `pnpm dev` runs
against MSW mocks by default (no backend needed) — see
[`OPERATIONS.md`](OPERATIONS.md) for the MSW-on vs. MSW-off distinction.

## Option 2 — Docker Compose

```bash
make demo          # docker compose --profile demo up --build -d
```

Brings up `api` (FastAPI), `web` (Next.js, MSW off), a weak-TLS demo
probe target (`localhost:8443`), and a local container registry
(`localhost:5000`).

```bash
make demo-down      # stop the stack
```

### Known limitation: image builds behind a restricted network

`docker build` for `api`/`web` needs ordinary internet access (pulling
`ghcr.io/astral-sh/uv`, `pypi.org`, `registry.npmjs.org`, etc.). Inside a
TLS-intercepting sandbox without container-level CA trust — confirmed in
this project's own v0.3 finale verification pass — the build fails
specifically at those fetch steps:

```
target api: failed to solve: ghcr.io/astral-sh/uv:0.6.14: failed to resolve
  source metadata ... Forbidden
target web: RUN corepack enable && corepack prepare pnpm@latest --activate:
  did not complete successfully: exit code: 1
```

This is **not** a defect in `docker-compose.yml`/`Dockerfile` — both are
correct for a host with normal internet access. It's a property of the
sandbox this project's own CI/agent verification runs in. See
[ADR 022](decisions/backend/022-real-stack-verification.md) for the exact
workaround (mounting a trusted CA bundle, or building with
`--network host`) and why it isn't baked into the committed compose
file. If `make demo`'s build step fails with an error like the above,
use Option 1 (native) instead — every number in this project's own
[`README.md`](../README.md) came from that path.

## Air-gap / offline verification

No runtime network calls outside `backend/probes/`'s guarded, allowlisted
surface (see [`ARCHITECTURE.md`](ARCHITECTURE.md)). The one build-time
download the backend needs — the CycloneDX 1.6 JSON schema, for CBOM
validation tests — is vendored at `backend/tests/fixtures/cyclonedx/`
with its hash recorded in
[`docs/engineering/backend/TOOLBELT.md`](engineering/backend/TOOLBELT.md);
`uv sync` plus the vendored fixtures is enough to run every backend gate
with no network access. Verify with:

```bash
cd backend
uv run pytest tests/test_airgap.py
uv run python scripts/verify_airgap.py
```

## Local test-target containers (weak-TLS, HSM)

`docker-compose.test.yml` brings up isolated mock targets used by the
probe adapter tests (`backend/tests/test_probes_adapters.py`) — a
weak-cipher TLS container distinct from the demo one, referenced from
`docker-compose.yml`. SoftHSM2 itself is **not** containerized in this
repo's compose files; either install `softhsm2`/`opensc` on the host and
run `backend/probes/hsm.py`'s default library-path resolution, or add it
to `backend/Dockerfile`'s runtime stage yourself (documented, not yet
wired in — see [ADR 022](decisions/backend/022-real-stack-verification.md)).
