@echo off
REM ECDAT Windows Command Dispatcher

IF "%1"=="" GOTO help
IF "%1"=="help" GOTO help
IF "%1"=="demo" GOTO demo
IF "%1"=="test" GOTO test
IF "%1"=="dev" GOTO dev
IF "%1"=="compose-up" GOTO compose_up
IF "%1"=="compose-down" GOTO compose_down
IF "%1"=="clean" GOTO clean

:help
echo ECDAT - Enterprise Cryptographic Discovery ^& Analysis Tool
echo Available commands:
echo   make demo          - Seeds demo policy and benchmark corpus
echo   make test          - Runs all backend and frontend test suites
echo   make dev           - Starts development servers
echo   make compose-up    - Starts Docker Compose services
echo   make compose-down  - Stops Docker Compose services
GOTO end

:demo
echo Seeding demo policy and benchmark corpus...
uv run --directory backend python scripts/demo_seed.py
GOTO end

:test
echo Running backend tests...
uv run --directory backend pytest
echo Running frontend unit tests...
pnpm --dir frontend test:unit
GOTO end

:dev
echo Starting backend...
start "ECDAT Backend" uv run --directory backend uvicorn api.main:app --reload --port 8000
echo Starting frontend...
start "ECDAT Frontend" pnpm --dir frontend dev
GOTO end

:compose_up
docker compose up --build -d
GOTO end

:compose_down
docker compose down
GOTO end

:clean
echo Cleaning cache directories...
rmdir /s /q backend\.pytest_cache 2>nul
rmdir /s /q backend\.ruff_cache 2>nul
rmdir /s /q backend\.mypy_cache 2>nul
rmdir /s /q frontend\.next 2>nul
echo Done.
GOTO end

:end
