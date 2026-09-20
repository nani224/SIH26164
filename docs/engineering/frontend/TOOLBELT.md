# Toolbelt Registry

| Package / Library | Version | License | Purpose / Justification |
|---|---|---|---|
| `next` | ^15.2.0 | MIT | Core framework (App Router, static exports, Server & Client components) |
| `react` / `react-dom` | ^19.0.0 | MIT | UI library |
| `tailwindcss` | ^4.0.0 | MIT | Utility-first CSS using modern CSS-first `@theme` syntax |
| `@tailwindcss/postcss` | ^4.0.0 | MIT | PostCSS integration for Tailwind v4 |
| `framer-motion` | ^12.0.0 | MIT | Smooth spring animations for score/counter updates and drawer slides |
| `@tanstack/react-query`| ^5.66.0 | MIT | Asynchronous server state caching, background refetches, mutation management |
| `@tanstack/react-virtual`| ^3.13.0| MIT | 60 fps virtualization for 10,000+ row cryptographic finding tables |
| `zustand` | ^5.0.0 | MIT | Client scenario state (CRQC $Z$ horizon, active filter presets) |
| `openapi-typescript` | ^7.6.0 | MIT | Deterministic type generation from `contracts/openapi.yaml` |
| `msw` | ^2.7.0 | MIT | Mock Service Worker for local offline API simulation matching contract |
| `lucide-react` | ^0.475.0 | MIT | Accessible technical iconography |
| `clsx` / `tailwind-merge` | ^2.1.0 | MIT | Dynamic className joining without specificity conflicts |
| `d3` / `d3-scale` | ^7.9.0 | ISC | Scientific chart scales and coordinate transformations for Mosca Matrix |

## Reusable Quality Gate & Verification Commands

| Command | Target Scope | Purpose |
|---|---|---|
| `pnpm typecheck` | `frontend/` | TypeScript strict static analysis (0 errors required) |
| `pnpm lint` | `frontend/` | ESLint configuration validation (0 warnings/errors required) |
| `pnpm knip` | `frontend/` | Dead code, unused export, and unreferenced dependency detection |
| `pnpm vitest run` | `frontend/` | Component-level Unit & jsdom accessibility test execution |
| `pnpm playwright test` | `frontend/` | Real-browser multi-viewport E2E, Axe WCAG AA, and integration suite |
| `pnpm build` | `frontend/` | Production Next.js App Router static compilation and budget validation |
| `pnpm codegen:api` | `frontend/` | Regenerate `src/types/api.generated.ts` from `contracts/openapi.yaml` |

