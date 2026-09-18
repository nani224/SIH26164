# ADR 002: API Contract Compliance, Live Re-Scoring, and Air-Gapped Typography

## Status
Accepted

## Context
A rigorous principal architectural audit flagged discrepancies in the initial prototype:
1. Static mock imports directly embedded in page views bypassing TanStack Query and HTTP client abstraction.
2. Client-side re-computation of Mosca risk scores in the frontend during $Z$-slider movement, diverging from the authoritative backend endpoint `POST /api/v1/scans/{id}/rescore`.
3. Incomplete MSW handlers causing HTTP requests to fail when bypassing mock data.
4. External CDN font references that violate air-gapped sovereign deployment requirements.
5. Incomplete type alignments between the auto-generated OpenAPI client and frontend components.

## Decisions

1. **Strict Typed API Client (`src/lib/api.ts`)**:
   - Centralized all OpenAPI endpoint calls into typed asynchronous functions conforming strictly to `contracts/openapi.yaml`.
   - Replaced all direct mock array references in screens (Overview, Inventory, Certificates, Mosca Matrix, Policy Editor, Scan Launcher, Remediation Plan, Graph) with TanStack Query `useQuery` and `useMutation`.

2. **Live Backend Re-Scoring for Mosca Matrix (`MoscaMatrixView.tsx`)**:
   - Completely excised client-side Mosca risk arithmetic ($V \times F \times U \times E \times K$) from `useMemo`.
   - Wired the $Z$-slider change handler to a debounced `useMutation` calling `POST /api/v1/scans/{id}/rescore`.
   - Matrix scatter plot and side drawer "Scenario Horizon Shifts" update exclusively from the authoritative response containing updated `bands` and `changedFindings`.
   - Preserved domain invariant: classically-broken assets (MD5, SHA-1) strictly maintain $U = 1.0$ and remain stationary across all $Z$ values.

3. **Complete MSW Contract Handlers (`src/mocks/handlers.ts`)**:
   - Implemented full MSW handlers matching all OpenAPI routes: `GET/POST /api/v1/scans`, `GET /api/v1/scans/{id}`, `GET /api/v1/scans/{id}/findings`, `POST /api/v1/scans/{id}/rescore`, `GET /api/v1/scans/{id}/graph`, `GET /api/v1/scans/{id}/cbom`, `GET /api/v1/scans/{id}/plan`, and Policy CRUD (`/api/v1/policies`, `/api/v1/policies/{id}`).
   - Enabled instant bypass via `NEXT_PUBLIC_ENABLE_MSW=false` in `src/components/MswProvider.tsx` for zero-friction integration with Claude's live backend.

4. **Air-Gapped Self-Hosted Typography**:
   - Packaged Latin WOFF2 font files for `IBM Plex Sans Condensed` (weights 400, 600, 700) and `JetBrains Mono` (weights 400, 600, 700) into `public/fonts/`.
   - Configured `next/font/local` in `src/app/layout.tsx` injecting CSS variables `--font-sans` and `--font-mono`.
   - Guaranteed zero runtime outbound requests to external CDNs, meeting air-gapped defense facility standards.

5. **Visible `[Proposed]` Tagging for Spec Extensions**:
   - Flagged features without active OpenAPI endpoints (Executive PDF reports, Hardware Security Module discovery, Cloud KMS discovery) with explicit `[Proposed]` badges in the UI.
   - Formalized RFC-001, RFC-002, and RFC-003 in `contracts/PROPOSALS.md`.

## Consequences
- 100% compliance with `contracts/openapi.yaml`.
- Clean separation between frontend visualization and backend cryptographic scoring.
- Passing all automated quality gates: TypeScript (`tsc --noEmit`), ESLint (`eslint .`), Knip, Vitest unit tests, and Playwright E2E browser tests.
