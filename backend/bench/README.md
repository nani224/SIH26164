# bench/ — ECDAT detection benchmarks (Track CC)

This is the handoff document for everything under `backend/bench/`: how
to run every benchmark, what each corpus is (and isn't), the blind-
labelling protocol that keeps the real-world numbers honest, current
measured numbers with their date, and where every documented false-
negative gap comes from. Everything below is reproducible from this file
alone — every command is copy-pasteable from `backend/`, and every number
was produced by running that exact command, not carried over from a prior
report.

## Quick start — run everything

```
cd backend
uv sync
uv run python bench/evaluate.py              # Layer A (starter fixtures)
uv run python bench/real_world/evaluate.py   # real_world (HOLD)
uv run python bench/check_precision_floor.py # CI gate: fails (exit 1) if either corpus < 0.95 precision
```

All three are plain Python scripts with no server, database, or network
dependency — they call `engine.scanner.scan()` (or the per-language
`engine/source_*.py` detectors it dispatches to) directly against files
on disk and compare the result to a hand-written `truth.json`.

## The two corpora — what each one is, and is not

| | `bench/fixtures/` (Layer A) | `bench/real_world/samples/` (HOLD) |
|---|---|---|
| What it is | Small, hand-written synthetic snippets, one or two per detection rule | Real, unmodified, third-party open-source files |
| Purpose | Regression floor: did a code change break an existing rule? | Honest accuracy signal: does the detector work on code it wasn't written to pass? |
| Expected precision/recall | 1.0/1.0 (files are written to exercise exactly the patterns that exist) | Whatever it actually measures — never adjusted to hit a number |
| Truth file | `bench/truth.json` | `bench/real_world/truth.json` |
| Eval script | `bench/evaluate.py` | `bench/real_world/evaluate.py` |
| Detail doc | this file | `bench/real_world/README.md` (provenance table + full numbered gap list) |

**Neither is the brief's full Loop B1 DEV/HOLD split** (>=150 labelled
usages across 3 unseen real projects, one Java, one Go, one C). As of
2026-09-20 (M7, Track CC), `bench/real_world/` has **56 usages across 14
files, 4 languages** — real progress (up from 32/9 the session before),
but still well short of 150. This is reported honestly here and in
`bench/real_world/README.md`'s own "What's still missing" section, not
rounded up.

One unrelated file lives alongside these: `bench/benchmark_corpus.tar.gz`
is a demo-data bundle for `scripts/demo_seed.py` (seeding the running API
with example scan data) — it has nothing to do with detection accuracy
and is not read by either `evaluate.py`.

## The blind-labelling protocol (why the real_world numbers can be trusted)

Every file in `bench/real_world/samples/` was added following this exact
order, every time, no exceptions:

1. **Source** a real, unseen (never previously read by anyone building
   this detector), permissively-licensed file (MIT/Apache-2.0/BSD/ISC —
   see `backend/CLAUDE.md`'s licence gate; LGPL/GPL may be *read* for
   research but never committed).
2. **Label blind.** A fresh `corpus-labeler` subagent (or, in an
   unassisted session, a human) reads the file end to end and records
   every crypto usage it can confidently identify — family, function,
   line — **with no access to this repo's detector or its output.**
   Ambiguous or dynamically-resolved usages (e.g. an algorithm name
   chosen by a runtime variable, not a literal) are explicitly *not*
   labelled, and are instead written up as a documented gap in
   `bench/real_world/README.md`'s gap list. Guessing a family to avoid an
   honest zero is never acceptable.
3. **Commit the labels alone**, in their own commit, separate from any
   detector code change. This is the step that makes the discipline real:
   once labels are committed, they are a historical fact, not something
   to revise after seeing what the detector does with them.
4. **Run the detector exactly once** (`bench/real_world/evaluate.py`) and
   record precision/recall/false-positive/false-negative lists exactly as
   printed.
5. **Never edit the labels to make that run's number look better.**
   If a "false positive" turns out to be a labelling-convention question
   rather than a detector defect (this happened once — see
   `docs/decisions/backend/019-m7-corpus-growth-and-aes-attribution.md`),
   the resolution is to document the root cause and fix the *convention*
   for the *next* file, never to retroactively edit an already-scored
   file's labels. Inspecting a miss and then relabelling to match is
   exactly what this discipline exists to prevent.

A **capability extension is not tuning** if it happens *before* step 2-4
above on the file that motivated it — i.e., you read a real file, notice
the detector has no rule for a pattern it uses, and add that rule *before*
that file is labelled or scored. This happened three times in M7 (Go
`crypto/dsa` sign/verify, Java `SecretKeyFactory`/PBKDF2) — see
`docs/decisions/backend/019-m7-corpus-growth-and-aes-attribution.md` for
the exact reasoning and why it's different from reacting to a run's
output.

## Current measured numbers (2026-09-20, M7-M8 Track CC)

```
$ uv run python bench/evaluate.py
precision=1.0 recall=1.0 f1=1.0
truth=64 detected=64 tp=64
```

Layer A: 27 files, 64 labelled usages, all 4 languages (Python, Java, Go,
C/C++). 1.0/1.0 is expected by construction (these fixtures exist to
exercise exactly the patterns implemented) — not evidence of general
accuracy. Grew from 15 (Python-only, 2026-09-17) -> 40 (+Java, M1,
2026-09-19) -> 56 (+C/C++, M2, 2026-09-19) -> 62 (+Go sign/verify, M7,
2026-09-20) -> 64 (+Java SecretKeyFactory, M7, 2026-09-20).

```
$ uv run python bench/real_world/evaluate.py
precision=0.9583 recall=0.8214 f1=0.8846
truth=56 detected=48 tp=46
```

Real_world (HOLD): 14 real, unseen, permissively-licensed files, 4
languages, 56 labelled usages. Precision 0.9583 (above the CI floor of
0.95; the 2 "false positives" are a labelling-convention finding, not a
code defect — see ADR 019). Recall 0.8214 (46/56) — down from the prior
session's 0.875 purely because the corpus grew faster than detector
coverage; every usage found before this session is still found. Grew from
25/2-language (pre-M1) -> 32/9-file/4-language (M6, 2026-09-19) ->
56/14-file/4-language (M7, 2026-09-20).

```
$ uv run python bench/check_precision_floor.py
Layer A (bench/fixtures): precision=1.0 (floor 0.95) -- PASS
real_world (HOLD): precision=0.9583 (floor 0.95) -- PASS

Precision floor (0.95) satisfied on both corpora.
```

This script is wired into `.github/workflows/backend-ci.yml` and fails
the build (exit 1) if either corpus drops below 0.95. It was proven to
actually do this on GitHub's real infrastructure, not just locally: M8b
deliberately broke precision on a throwaway branch and confirmed a real
`failure` conclusion on the `backend-ci` job (PR #12, closed unmerged,
change reverted) — see `backend/PROGRESS.md`'s 2026-09-20 M8 entry for
the full real command/log output of both the local break and the GitHub
Actions failure.

## Documented false-negative gap clusters (as of 2026-09-20)

The real_world corpus currently has 10 false negatives, all previously
identified and none silently ignored. Full detail (exact lines, exact
reasoning per case) lives in `bench/real_world/README.md`'s numbered gap
list; the categories are:

1. **Project-specific type aliases** (pyjwt's `AllowedECKeys`) — resolving
   it would mean hardcoding one library's internal naming, not a
   generalizable rule. 1 instance.
2. **Local-variable dataflow for `.verify()`/`.sign()`** — the receiver's
   type comes from a runtime-computed local variable, not a typed
   parameter (ADR 016 only resolves the parameter case). 1 pyjwt instance.
3. **Generic `cipher.Stream`/`cipher.BlockMode` interface (Go)** — the
   concrete cipher (`aes.NewCipher`) is constructed several calls before
   the actual `XORKeyStream`/`CryptBlocks` operation, behind a generic
   interface parameter. 5 instances across 2 files
   (`gorilla_securecookie.go`, `x_crypto_ssh_keys.go`).
4. **No Python PBKDF2 API coverage** — `hashlib.pbkdf2_hmac(...)` and
   Django's own `pbkdf2()` wrapper have no detection rule at all (unlike
   Java, which gained `SecretKeyFactory` coverage this session). 2
   instances.
5. **Attribute-bound hash resolution** — `self.digest(...)` reads a hash
   function back off an instance attribute set elsewhere in the class;
   needs attribute-to-class-body dataflow, a different mechanism than the
   existing parameter-type-annotation resolution. 1 instance.

None of these are fixed reactively from seeing them in a HOLD run — per
the blind-labelling protocol above, a real detector improvement for any
of these would need to be developed and proven on *new*, not-yet-labelled
material, the same way the M7 capability extensions were.

## Where the design decisions live

Every non-trivial engine design decision has an ADR in
`docs/decisions/backend/`, numbered in the order it happened:
013 (Java engine), 014 (C/C++ engine), 015 (OpenSSL EVP context linkage —
a real precision bug this corpus caught and fixed), 016 (Python
parameter-type-annotation resolution), 017 (CI/CD precision gate +
reusable Action), 018 (Go bare-function-reference), 019 (M7 corpus growth
+ the AES-attribution labelling-convention finding), 020 (M8a's blocked
external-repo proof, with the exact human instruction to unblock it).
