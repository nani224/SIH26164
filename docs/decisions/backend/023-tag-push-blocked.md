# 023 — `v0.3.0-sih-finale` tag created locally, push to origin BLOCKED

## Status

BLOCKED (Finale G5, 2026-09-20). Not something this session can resolve
itself; documented here so a human can unblock it with one action, same
pattern as ADR 020's external-repo-proof blocker.

## Context

G5's final step: tag the merged release commit `v0.3.0-sih-finale` and
push the tag. The PR (`nani224/SIH26164#14`) merged cleanly to `main` at
`07215b6`, and `backend-ci` ran green on that commit
(run `35514786677`, `conclusion: success`).

The annotated tag was created locally against `origin/main`'s `07215b6`:
```
git tag -a v0.3.0-sih-finale -m "..." origin/main
```
Pushing it fails, consistently, with an authorization error (not a
network error):
```
$ git push origin v0.3.0-sih-finale
error: RPC failed; HTTP 403 curl 22 The requested URL returned error: 403
send-pack: unexpected disconnect while reading sideband packet
fatal: the remote end hung up unexpectedly
```
Retried twice more (per this repo's own "retry network errors with
backoff" instruction) with the identical result each time. Confirmed the
tag genuinely never reached the remote:
```
GET /repos/nani224/SIH26164/git/ref/tags/v0.3.0-sih-finale -> 404 Not Found
```

## Why this isn't a network flake

Every `git push origin <branch>` in this same session, on this same
remote, over this same connection, succeeded without incident (7 pushes
to `release/v0.3.0` across G2-G5, plus the earlier `feature/a1-backend`
and `main` pushes). The 403 is specific to a `refs/tags/*` push, not
general connectivity or credential validity -- a real 403 from GitHub
means the authenticated identity was recognized but denied that specific
action.

## Most likely root cause

GitHub's per-repository **tag protection rules** (Settings -> Tags,
separate from branch protection) can block ref creation under a matching
pattern (e.g. `v*`) for anyone other than an explicitly listed bypass
actor -- including a GitHub App installation token, which this session's
git credential is. This session has no visibility into the repo's actual
tag-protection configuration (that's an org/repo admin setting, not
something exposed via the GitHub App's own permission list the way
ADR 020's repository-creation limitation was), so this is the most
likely explanation based on the symptom (blocks specifically on
`refs/tags/*`, not `refs/heads/*`) rather than a confirmed root cause.

## What a human needs to do (either one unblocks this)

1. **Push the tag directly**, from a clone with a credential that has
   tag-push rights:
   ```
   git fetch origin main
   git tag -a v0.3.0-sih-finale -m "v0.3.0-sih-finale -- see CHANGELOG.md" origin/main
   git push origin v0.3.0-sih-finale
   ```
   (`origin/main` at the time of writing is `07215b6`, the exact commit
   PR #14 merged.)
2. **Or**, if a tag-protection rule is indeed the cause, adjust it
   (Settings -> Tags -> protection rules) to allow this session's GitHub
   App installation to create tags matching `v*`, then ask this session
   (or a continuation of it) to retry the push itself.

## Consequences

- `main` is fully up to date (`07215b6`), CI green, README/CHANGELOG/
  DEMO_SCRIPT all merged. Only the tag ref itself is missing from origin.
- Marked as a known, explicit gap in the finale report rather than
  claimed done on the strength of the local tag object alone -- the local
  tag is real but the release isn't reproducible/discoverable by anyone
  else until it's actually on the remote.
- If a human never does this, `v0.3.0-sih-finale` stays available locally
  in this session's working tree only, which is not equivalent to a
  pushed, shareable release tag.
