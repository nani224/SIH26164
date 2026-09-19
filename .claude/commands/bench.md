---
description: Run all backend benchmark/evaluation scripts and report real precision/recall/F1 numbers, compared against README/PROGRESS.md claims.
---

In `backend/`, find and run every script under `bench/` that computes precision/recall/F1
or runs hostile-input tests (e.g. `bench/evaluate.py`, `bench/real_world/evaluate.py`, any
`realworld_sample.py`, any `hostile_tests.py`). Print the real numbers for each. Then grep
`README.md` and `backend/PROGRESS.md` for any quoted precision/recall/F1 claim and state,
for each, whether the real number just measured matches, and if not, by how much and what
you did about the discrepancy (fixed the claim, or flagged it as a real regression).
