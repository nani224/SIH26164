# 017 — CI/CD: precision-floor gate, policy-as-code, reusable Action (M5)

## Status

Accepted — real blocked PR demonstrated: https://github.com/nani224/SIH26164/pull/9

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
  someone has to remember to check by hand. Proven for real on GitHub's
  own runner (not just locally) in PR #8: https://github.com/nani224/SIH26164/pull/8
  (backend-ci `success`, including the new precision-floor step) -- the
  first time this session's entire M0-M5 work was validated by GitHub's
  Actions infrastructure rather than only local `uv run` commands.
- **The real-blocked-PR demonstration is done**:
  https://github.com/nani224/SIH26164/pull/9 introduces
  `demo/vulnerable-app/legacy_auth.py` (a 1024-bit RSA keygen) and is
  genuinely blocked -- the `ecdat-demo / scan` check reports `failure`
  (exit 1), the PR's `mergeable_state` is `unstable`, and
  `post_pr_comment.py` posted a real findings-table comment
  (https://github.com/nani224/SIH26164/pull/9#issuecomment-5746916900)
  via `GITHUB_TOKEN`, all on GitHub's actual infrastructure -- not a
  local simulation. Not a separate external repository, as the brief
  originally envisioned: repo creation via the GitHub App integration is
  403-blocked (`Resource not accessible by integration` -- GitHub Apps
  generally cannot create repositories via the API at all, independent of
  which permissions are granted; confirmed by retrying after the user
  checked the app's permission page), and the user, once informed,
  redirected this to a same-repo demo instead (`demo/vulnerable-app/` +
  `.github/workflows/demo-vulnerable-check.yml`, calling the *same*
  reusable workflow an external repo would call via
  `nani224/SIH26164/.github/workflows/ecdat-scan-reusable.yml@main`,
  just referenced locally as `./.github/workflows/ecdat-scan-reusable.yml`
  since this workflow lives in the same repo it's demonstrating).
- **Real bug caught and fixed by this exact demonstration, not before
  it**: the first run of `demo-vulnerable-check.yml` (on PR #8, then
  again on PR #9) failed with `startup_failure` --
  `"The nested job 'scan' is requesting 'pull-requests: write', but is
  only allowed 'pull-requests: none'"` -- because the calling workflow
  didn't declare `permissions:`, so it defaulted to read-only and
  couldn't grant what `ecdat-scan-reusable.yml`'s job requests. Fixed by
  adding explicit `permissions: {contents: read, pull-requests: write}`
  to the calling job. This is exactly the value of actually running the
  thing on real infrastructure instead of stopping at "the YAML parses
  and the underlying script works locally" -- a composite-Action
  permission-propagation bug like this has no local equivalent to catch
  it against.
- `.github/actions/ecdat-scan/action.yml`'s cross-repo checkout step
  (`repository: nani224/SIH26164`) is now proven on real GitHub Actions
  infrastructure (PR #9's run: real checkout of this repo's `backend/`,
  real `uv sync`, real scan, real exit code, real PR comment) -- no
  longer YAML-syntax-validated only.
