.PHONY: help demo dev test clean compose-up compose-down

help:
	@echo "ECDAT — Enterprise Cryptographic Discovery & Analysis Tool"
	@echo "Available commands:"
	@echo "  make demo          - Seeds demo policy & benchmark corpus, runs offline"
	@echo "  make dev           - Runs backend and frontend development servers"
	@echo "  make test          - Runs all backend and frontend test suites"
	@echo "  make compose-up    - Starts all services via Docker Compose"
	@echo "  make compose-down  - Stops Docker Compose services"
	@echo "  make clean         - Cleans temporary artifacts and caches"

demo:
	uv run --directory backend python scripts/demo_seed.py

dev:
	@echo "Starting backend and frontend..."
	uv run --directory backend uvicorn api.main:app --reload --port 8000 & pnpm --dir frontend dev

test:
	uv run --directory backend pytest
	pnpm --dir frontend test:unit

compose-up:
	docker compose up --build -d

compose-down:
	docker compose down

clean:
	python -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ['backend/.pytest_cache', 'backend/.ruff_cache', 'backend/.mypy_cache', 'frontend/.next']]"
