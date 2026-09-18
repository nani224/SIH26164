# Backend Dockerfile — ECDAT Offline Air-gapped API
FROM python:3.12-slim AS builder

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ECDAT_AIRGAP=1

# Install uv for fast, reliable, reproducible dependency installation
COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /bin/uv

# Copy dependency specifications
COPY pyproject.toml uv.lock ./

# Install dependencies into virtual environment
RUN uv sync --frozen --no-dev --no-install-project

# Copy backend application source
COPY api ./api
COPY engine ./engine
COPY bench ./bench
COPY scripts ./scripts
COPY README.md ./

# Final runtime image
FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ECDAT_AIRGAP=1 \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder /app/.venv /app/.venv
COPY api ./api
COPY engine ./engine
COPY bench ./bench
COPY scripts ./scripts

# Run database initialization and demo seed
RUN python scripts/demo_seed.py

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
