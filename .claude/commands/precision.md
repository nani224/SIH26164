---
description: Fast loop check during rule-author work -- Layer A synthetic + real-world benchmark numbers only, no full gate suite.
---

Run, in `backend/`:
```
uv run python bench/evaluate.py
uv run python bench/real_world/evaluate.py
```
Report only: precision/recall/f1 for each, and whether precision >= 0.95 on whichever
corpus is the current target (state which). If either script errors, show the real error.
Do not run ruff/mypy/pytest here -- that's `/gates`.
