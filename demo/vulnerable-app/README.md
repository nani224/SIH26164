# ecdat demo: vulnerable-app

Placeholder for a Track CC (M5) CI/CD demonstration: a follow-up PR adds
a Python file to this directory that generates a 1024-bit RSA key, and
`.github/workflows/demo-vulnerable-check.yml` (which scans this
directory on every PR touching it, via the same reusable workflow an
external repo would call) blocks that PR for real -- the finding scores
critical (90.0) under `.ecdat-policy.yml`'s `gate.failOnBand: critical`,
via the risk formula's existing "unencrypted private key outside a test
path -> score >= 90" rule (root `CLAUDE.md`).

Nothing in this directory is meant to be used as real code -- it exists
only to be scanned.
