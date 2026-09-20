.PHONY: help demo demo-down demo-seed dev test benchmark clean compose-up compose-down

help:
	@echo "ECDAT — Enterprise Cryptographic Discovery & Analysis Tool"
	@echo "Available commands:"
	@echo "  make demo          - Full real stack via Docker Compose (api+web+weak-TLS+registry)"
	@echo "  make demo-down     - Stops the demo stack"
	@echo "  make demo-seed     - Seeds demo policy & benchmark corpus into a local SQLite file, no Docker"
	@echo "  make dev           - Runs backend and frontend development servers"
	@echo "  make test          - Runs all backend and frontend test suites"
	@echo "  make benchmark     - Runs ECDAT benchmark evaluation and Crypto Mass Conservation certificate"
	@echo "  make compose-up    - Starts all services via Docker Compose (base profile only)"
	@echo "  make compose-down  - Stops Docker Compose services"
	@echo "  make clean         - Cleans temporary artifacts and caches"

# Brings up api+web+demo-weak-tls+demo-registry (the `demo` compose profile,
# see docker-compose.yml) -- the whole real stack from a clean state, no
# stub/mock data. NOTE (docs/decisions/backend/021-g2-real-stack-verification.md):
# building `api`/`web` needs the internet access `--build` implies; a
# TLS-intercepting sandbox without container-level CA trust (this repo's own
# CI dev sandbox included) will fail the build step specifically -- not a
# defect in this target, see that ADR for the documented workaround.
demo:
	docker compose --profile demo up --build -d
	@echo "Demo stack starting: web on http://localhost:3000, api on http://localhost:8000"
	@echo "Weak-TLS probe target: localhost:8443  |  local registry: localhost:5000"

demo-down:
	docker compose --profile demo down

# Seeds a local SQLite file with real scan results (no Docker, no running
# server) -- the fast, dependency-light path used to produce this repo's own
# bench/demo evidence when a full Docker build isn't available.
demo-seed:
	uv run --directory backend python scripts/demo_seed.py

dev:
	@echo "Starting backend and frontend..."
	uv run --directory backend uvicorn api.main:app --reload --port 8000 & pnpm --dir frontend dev

test:
	uv run --directory backend pytest
	pnpm --dir frontend test:unit

benchmark:
	uv run --directory backend python bench/public/score.py --all

compose-up:
	docker compose up --build -d

compose-down:
	docker compose down

clean:
	python -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ['backend/.pytest_cache', 'backend/.ruff_cache', 'backend/.mypy_cache', 'frontend/.next']]"
