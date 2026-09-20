# 020 — M8a: external-repo proof of the reusable Action — BLOCKED, needs human repo creation

## Status

BLOCKED (Track CC, 2026-09-20). Not something this session can resolve
itself; documented here so a human can unblock it with one action.

## Context

`.github/workflows/ecdat-scan-reusable.yml` and
`.github/actions/ecdat-scan/action.yml` (M5, Track CC) let any *other*
GitHub repository call ECDAT's scan-and-gate as a single reusable
workflow. So far this has only ever been proven **inside** this same repo
(`nani224/SIH26164`'s own `demo/vulnerable-app/` + `demo-vulnerable-check.yml`,
PRs #8-#10) — a real, working proof, but not evidence that an *external*
consuming repository can actually call in via the cross-repo
`uses: nani224/SIH26164/.github/workflows/ecdat-scan-reusable.yml@main`
form.

M8a asks for that missing proof: either get a real external repo wired up
and a real blocked PR opened there, or document the exact blocker and the
one instruction needed to clear it.

## Why this session cannot do it itself

Confirmed earlier this same engagement (before M6): the GitHub App
integration this session authenticates through cannot create new
repositories via the GitHub API — this returns a 403 regardless of the
app's configured repository access ("All repositories" was already
selected; there is no "Administration" permission offered in the app's
own permission list at all). This is architectural, not a scope/permission
setting a retry or a different call shape can work around — GitHub Apps
generally cannot call `POST /user/repos` or `POST /orgs/{org}/repos` on a
person's behalf; only a user-authenticated (OAuth/PAT) client or a human
using the UI can create a repository. This session only has GitHub App
(MCP `github` server) access, scoped to `nani224/SIH26164` besides.

## What a human needs to do (exact, one-time)

1. **Create one new, empty, public GitHub repository** under any account
   or org the human controls (any name — e.g. `ecdat-external-proof`).
   Public matters only so the resulting PR/Action run is inspectable
   without extra access grants; a private repo the human later grants
   this session access to would also work.
2. **Add exactly one file** to that repo's default branch,
   `.github/workflows/ecdat-check.yml`:
   ```yaml
   name: ecdat-check
   on:
     pull_request:
   jobs:
     ecdat:
       permissions:
         contents: read
         pull-requests: write
       uses: nani224/SIH26164/.github/workflows/ecdat-scan-reusable.yml@main
       with:
         scan-path: .
       secrets:
         github-token: ${{ secrets.GITHUB_TOKEN }}
   ```
   This is the literal cross-repo form already documented in this repo's
   own `.github/workflows/ecdat-scan-reusable.yml` header comment — no
   new snippet was written for this doc, it's copied verbatim from there
   so the two can never drift.
3. **Add one deliberately weak crypto file** to that repo (e.g. an
   RSA-1024 keygen, mirroring `demo/vulnerable-app/` in this repo) and
   **open a PR** in the new repo introducing it.
4. **Tell this session (or whoever continues this work) the new repo's
   name/URL**, and grant this session's GitHub access to it (adding it to
   the session's repo scope) so the resulting Action run and PR can be
   inspected and reported on, the same way PRs #8-#10 were verified in
   this repo.

Once that repo exists and access is granted, the remaining work (open the
PR, watch the check run, confirm the real block, report the result) is
exactly the same mechanical process already proven twice in this repo
(PR #8 for the M5 in-repo demo, PR #9/#10 for the permissions-fix
iteration) and needs no further design.

## Consequences

- Marked `[BLOCKED - needs human repo creation]` in `PLAN.md`'s M8 entry
  and `PROGRESS.md`'s M8 dated entry, per the mandate's own instruction
  for this exact situation, rather than left vague or silently skipped.
- M8b (proving the precision-floor gate itself fails red) does **not**
  depend on this and was completed independently this same session — see
  the M8 PROGRESS.md entry for that evidence.
- If a human never provides a repo, this stays honestly BLOCKED rather
  than being marked done on the strength of the in-repo demo alone, which
  is a real but narrower proof (same-repo `uses: ./...` local reference,
  not the cross-repo `owner/repo/...@ref` form this ADR is about).
