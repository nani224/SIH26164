---
description: Run all mechanical gates for backend and frontend (lint/type/test), quiet output.
---

Run, and report only the summary line + any failures verbatim:

Backend (`cd backend`):
```
uv run ruff check .
uv run mypy --strict .
uv run pytest --cov -q
uv run python scripts/contract_diff.py
```

Frontend (`cd frontend`):
```
pnpm typecheck
pnpm lint
pnpm knip
pnpm test
pnpm build
```

Do not paste full passing output. For any failure, show the real error and the file:line.
