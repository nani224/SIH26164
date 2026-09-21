# ecdat demo: vulnerable-app

A Track CC (M5) CI/CD demonstration: a fixture file generates a
1024-bit RSA key, and `.github/workflows/demo-vulnerable-check.yml`
(which scans this directory on every PR touching it, via the same
reusable workflow an external repo would call) blocks a PR introducing
it for real -- the finding scores critical (90.0) under
`.ecdat-policy.yml`'s `gate.failOnBand: critical`, via the risk formula's
existing "unencrypted private key outside a test path -> score >= 90"
rule (root `CLAUDE.md`). Originally proven in PR #9 (2026-09-19).

Nothing in this directory is meant to be used as real code -- it exists
only to be scanned.

## Why the fixture file isn't on `main`

It's a genuine positive: any PR touching `demo/vulnerable-app/**` that
includes it gets blocked by `demo-vulnerable-check.yml`, on purpose. That
means it can never *merge* into `main` through the normal PR flow without
someone deliberately overriding the gate -- and if it somehow did land on
`main`, it would sit there as a live tripwire, blocking every future PR
that touches this directory for an unrelated reason (a README edit, a new
fixture) with the same critical finding, every time.

So the fixture lives on its own branch instead, refreshed to track
`main` as needed: **`demo/vulnerable-app-fixture`** (originally proven
from `demo/vulnerable-rsa1024`, PR #9). To re-run the demo:

```bash
git fetch origin demo/vulnerable-app-fixture
git checkout -b demo/refresh-$(date +%s) origin/demo/vulnerable-app-fixture
git push -u origin HEAD
# open a PR from this branch to main -- demo-vulnerable-check.yml blocks it.
# close the PR without merging once you've shown the block; delete the branch.
```

Or, to see the effect without opening a real PR, just read
`legacy_auth.py` on that branch and the `demo-vulnerable-check.yml`
workflow definition side by side -- the mechanism is exactly the same
one an external consuming repository's own PRs would go through via
`uses: nani224/SIH26164/.github/workflows/ecdat-scan-reusable.yml@main`.
