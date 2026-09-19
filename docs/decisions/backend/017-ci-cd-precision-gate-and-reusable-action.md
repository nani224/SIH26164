# 017 — CI/CD: precision-floor gate, policy-as-code, reusable Action (M5)

## Status

Accepted (in progress — see Consequences for what remains)

## Context

Track CC M5's brief: make CI/CD the headline feature. Concretely: this
repo's own CI enforces the 0.95 precision floor (previously a norm this
session self-policed by hand, not something a green CI run actually
proved); a policy-as-code file consuming repos can copy and edit; a
reusable Action other repos can call to scan themselves and get a PR
comment with a findings table, using `GITHUB_TOKEN` directly (no
third-party comment action); and (separately, tracked but not yet done
— see Consequences) a real demonstration: a deliberately-vulnerable demo
repo with a PR that actually gets blocked by this Action.

## Decision

- **`backend/bench/check_precision_floor.py`**: imports both
  `bench/evaluate.py` (Layer A) and `bench/real_world/evaluate.py` (HOLD)
  and fails (exit 1) if either's precision drops below 0.95. Wired into
  `.github/workflows/backend-ci.yml` as a new step, after the existing
  contract-diff check. This is the same floor this session enforced by
  hand at every milestone (and which caught a real violation in M3) --
  now a green backend-ci run is itself the proof, not something that
  needs re-deriving from a PROGRESS.md entry.
- **`.ecdat-policy.yml`** (repo root): one YAML file serving two purposes
  -- the existing risk-formula `Policy` shape (`crqcYears`/`default`/
  `contexts`, identical to what `POST /policies` already accepts) *and*
  a `gate:` section (`failOnBand`, `precisionFloor`) that's CI-specific,
  not part of the risk formula. A consuming repo copies this file to its
  own root and edits it for its own environment.
- **`backend/bench/ci_scan.py`**: loads the policy file, runs
  `engine.scanner.scan()` against a target path (no running API/DB
  involved -- CI has nothing to talk to), writes a JSON findings file and
  a Markdown findings table, and exits non-zero if any finding is at or
  above `gate.failOnBand`. Verified end-to-end against a hand-written
  `rsa.generate_private_key(key_size=1024)` sample: correctly scores it
  critical (90.0, via the existing private-key floor) and exits 1.
- **`backend/bench/post_pr_comment.py`**: posts/updates a PR comment via
  raw `urllib.request` calls to the GitHub REST API, authenticated with
  `GITHUB_TOKEN` from the environment (never logged, never passed as a
  CLI arg). Idempotent -- finds its own previous comment via a hidden
  HTML marker and PATCHes it instead of accumulating a new comment per
  push. No third-party action (`peter-evans/create-or-update-comment`
  etc.) used, per the brief's explicit constraint.
- **`.github/actions/ecdat-scan/action.yml`**: a composite Action other
  repos' workflows can call. Since the scanner engine lives in *this*
  repo, the action's first step checks out `nani224/SIH26164` (sparse,
  `backend/` only) into a subdirectory, installs `uv`+Python+deps there,
  then runs `ci_scan.py` against the *calling* repo's already-checked-out
  workspace (`$GITHUB_WORKSPACE`), then `post_pr_comment.py`.
- **`.github/workflows/ecdat-scan-reusable.yml`**: a `workflow_call`
  wrapper so a consuming repo needs only one `uses:` line (plus its own
  checkout) rather than wiring the composite action directly.
- 11 new unit tests across the three new scripts
  (`test_check_precision_floor.py`, `test_ci_scan.py`,
  `test_post_pr_comment.py`), the PR-comment tests using a monkeypatched
  `_api_request` so no real network call is ever made from the test
  suite.

## Consequences

- `backend-ci.yml` now fails if this repo's own detection precision ever
  regresses below 0.95 on either corpus -- a real gate, not a rule
  someone has to remember to check by hand.
- The reusable Action and policy file are real, tested (locally, against
  a real hand-built vulnerable sample) infrastructure -- but **not yet
  proven against a real external repository and a real GitHub PR**,
  which is what the brief's "create a deliberately-vulnerable demo repo
  and open a REAL PR that gets REALLY BLOCKED" step is for. Creating a
  new external repository and opening a real PR under the user's GitHub
  identity is a visible, hard-to-reverse action outside this session's
  current repository scope (`nani224/SIH26164` only) -- flagged to the
  user rather than done unilaterally or silently skipped. If authorized
  and a target repository is provided, the remaining work is
  straightforward given everything above: add a workflow file calling
  `ecdat-scan-reusable.yml` to that repo, commit a file introducing an
  RSA-1024 key generation (or similar critical-band pattern), open a PR,
  and confirm the check fails for real.
- `.github/actions/ecdat-scan/action.yml`'s cross-repo checkout step
  (`repository: nani224/SIH26164`) has not been exercised inside an
  actual GitHub Actions runner -- verified for YAML syntax validity only
  (`yaml.safe_load`), not for actually running end-to-end on GitHub's
  infrastructure. The underlying script it calls (`ci_scan.py`) *has*
  been verified end-to-end locally.
