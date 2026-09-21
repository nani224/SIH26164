# Benchmark

How detection accuracy is measured, the current real numbers, and where
they fall short of the original brief — stated honestly rather than
rounded up, per the root `CLAUDE.md`'s "honest numbers only" rule.

## The two corpora

### Starter fixtures (`backend/bench/fixtures/`)

Small, hand-written synthetic files covering every detection rule —
Python, Java, Go, C/C++. Not real-world code; exists to catch obvious
regressions fast in CI.

```bash
cd backend
uv run python bench/evaluate.py
```

**Result (2026-09-20)**: `precision=1.0 recall=1.0 f1=1.0` — 27 files, 64
labelled usages. `backend/tests/test_bench_evaluate.py` fails the build
if this regresses.

### Real-world HOLD (`backend/bench/real_world/`)

Real, unseen third-party source files (Django, PyJWT, Spring Security,
`golang.org/x/crypto`, etc.) — genuinely representative code, not
fixtures written to exercise a specific rule.

```bash
cd backend
uv run python bench/real_world/evaluate.py
```

**Result (2026-09-20)**: `precision=0.9583 recall=0.8214 f1=0.8846` — 14
files, 4 languages, 56 labelled usages (tp=46, detected=48).

Per-language breakdown:

| Language | Truth | Detected | TP | Precision | Recall |
| :--- | ---: | ---: | ---: | ---: | ---: |
| C | 5 | 5 | 5 | 1.0000 | 1.0000 |
| Java | 2 | 2 | 2 | 1.0000 | 1.0000 |
| Python | 25 | 20 | 20 | 1.0000 | 0.8000 |
| Go | 24 | 21 | 19 | 0.9048 | 0.7917 |

Go's 0.9048 precision (2 false positives, both AES misattributions in
`x_crypto_ssh_keys.go`) is the one language below the aggregate;
`backend/bench/real_world/README.md` itemizes every false positive and
false negative with a root cause.

## Honest gaps

- **This is not the brief's Loop B1 DEV/HOLD corpus.** The brief asked
  for 150+ labelled usages across 3 unseen real projects; the real-world
  HOLD set here is 56 usages across 14 files. Real, hand-labelled, and
  honestly short — not silently rounded up to look closer to the target.
- **The starter-fixture 1.000/1.000 is not a claim about real-world
  accuracy.** It's a regression floor on synthetic code written to
  exercise known rules; it will always score near-perfect by
  construction. The real-world HOLD number is the one that means
  something about production code.
- Precision floor enforcement (CI, 0.95) only runs against the
  **fixtures** corpus today, not the real-world HOLD set — see
  `bench/check_precision_floor.py`.

## Protocol: label before running

For any HOLD/DEV corpus addition, the root `CLAUDE.md` requires: read
the source and write the truth-table labels **first**, commit the labels
alone in their own commit, only then run the detector. This is the one
thing standing between a real accuracy number and unconsciously
tuning-on-HOLD. `docs/decisions/backend/009-corpus-growth-and-aes-attribution.md`
documents a real case where this discipline mattered: a labelling
convention question (attribute a call to the function it's syntactically
inside of, vs. what it dispatches to) was resolved by NOT retroactively
"fixing" the labels once the detector's real behavior was seen, to avoid
laundering a rule change through the corpus.

## Licence gate

Only MIT/Apache-2.0/BSD/ISC-licensed source is committed into
`backend/bench/`. Reading an LGPL/GPL project from a scratch path to
hand-label against the detector is fine and is not "vendoring" — but
its source is never committed to this repo.

## CI enforcement

`.github/workflows/backend-ci.yml` runs `bench/check_precision_floor.py`
on every push touching `backend/**`. A rule that raises recall but drops
fixture precision below 0.95 fails the build — see
[ADR 020](decisions/backend/020-ci-cd-precision-gate.md) for the real
blocked-PR proof of this gate (PR #12) and
[ADR 021](decisions/backend/021-external-repo-proof-blocked.md) for the
one part of that story (an external consuming repo calling the reusable
Action) still blocked on a one-time human action.
