# Implementation Plan: Initialize Project with React, TypeScript and Tailwind CSS

**Branch**: `001-init-react-ts-tailwind` | **Date**: 2026-11-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-init-react-ts-tailwind/spec.md`

## Summary

Scaffold a single Vite + React + TypeScript (strict) web app at the repository root, styled only through
one Tailwind CSS entry file, with the five constitution scripts (`typecheck`, `lint`, `test:unit`,
`test:e2e`, `build`) running non-interactively. Deliver a minimal, accessible, mobile-first home page
(header with the app name, main area with one `h1` and a welcome message, and a footer), covered by a
Vitest + React Testing Library component test and a Playwright suite that checks the page at 320 px and
1280 px and runs an axe-core WCAG 2.1 AA scan. Document setup and commands in the README.

## Technical Context

**Language/Version**: TypeScript 5.x (strict and extra strictness flags), on Node.js 22 LTS (`>=22.12`; `.nvmrc` = `22`)

**Primary Dependencies**: Runtime: `react`, `react-dom` (19.x). Build-time: `vite`, `@vitejs/plugin-react`, `tailwindcss` + `@tailwindcss/vite` (v4)

**Storage**: N/A

**Testing**: Vitest + jsdom + React Testing Library + `@testing-library/jest-dom` (unit and component); Playwright (Chromium) + `@axe-core/playwright` (end-to-end and accessibility)

**Target Platform**: Current evergreen browsers (desktop and mobile); static build output (`dist/`)

**Project Type**: Single-page web app (frontend only, single project at the repository root)

**Performance Goals**: No specific targets for this feature. The static page builds to a small bundle; full local check run under the 15-minute onboarding budget (SC-006)

**Constraints**: Every script is non-interactive and exits non-zero on failure (no watch mode, no prompts, no HTML report auto-open); no horizontal scroll from 320 px; WCAG 2.1 AA; no routing, state management, network calls, auth or deployment config (FR-018)

**Scale/Scope**: 1 page, 3 small components, ~1 unit test file, ~1 end-to-end spec file

All Technical Context items are resolved; see [research.md](./research.md) for the decisions and alternatives.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status (pre-research) | Status (post-design) |
|-----------|------|-----------------------|----------------------|
| I. Type Safety | `strict: true`; no `any`; `npm run typecheck` = `tsc --noEmit`, zero errors | PASS: a single `tsconfig.json` with `strict` covers `src/`, `tests/` and config files | PASS |
| II. Test-First | Tests written and seen failing before implementation; Vitest + RTL with role/text queries; Playwright for e2e + a11y; each acceptance scenario maps to a test | PASS with one justified deviation (see Complexity Tracking): US1 and US3 scenarios are about tooling and docs, so some are verified by the gate run itself or by a documented manual check | PASS (traceability below) |
| III. Tooling Contract | Exactly `typecheck`, `lint`, `test:unit`, `test:e2e`, `build`; non-interactive; non-zero on failure | PASS: see [contracts/npm-scripts.md](./contracts/npm-scripts.md). Helper scripts `dev` and `preview` are added for running the app locally and do not affect the gate (see research R-10) | PASS |
| IV. Accessible, Responsive UI | Semantic landmarks, heading order, WCAG 2.1 AA, Tailwind-only styling with one entry file, mobile-first from 320 px, axe scan per Playwright-covered page | PASS: see [contracts/home-page-ui.md](./contracts/home-page-ui.md) | PASS |
| V. Simplicity | Small components; runtime dependencies justified; no global state; YAGNI | PASS: runtime dependencies are only `react` and `react-dom` (required by the stack). No router, store or CSS other than the Tailwind entry file | PASS |
| Stack & Constraints | Node LTS + npm + committed lock file, `npm ci`; Vite; ESLint with TS + Hooks rules; no secrets | PASS | PASS |

**Runtime dependency justification (Principle V)**: `react` and `react-dom` are the UI runtime fixed by
the constitution and do not replace anything. Everything else is a dev dependency (build, lint, test).

### Acceptance-scenario traceability (SC-005)

| Scenario | Verified by |
|----------|-------------|
| US1-AS1 clean install + build | Gate run: `npm ci && npm run build` (quickstart V1) |
| US1-AS2 four check commands pass non-interactively | Gate run: `npm run typecheck`, `lint`, `test:unit`, `test:e2e` (quickstart V1) |
| US1-AS3 failing check → non-zero exit | Documented manual negative check (quickstart V2) |
| US2-AS1 320 px: all content visible, no horizontal scroll | `tests/e2e/home.spec.ts`: "mobile 320px" |
| US2-AS2 1280 px: all content visible | `tests/e2e/home.spec.ts`: "desktop 1280px" |
| US2-AS3 landmarks + exactly one `h1` | `src/App.test.tsx` (roles `banner`, `main`, `contentinfo`, one level-1 heading); also asserted in e2e |
| US2-AS4 zero axe WCAG 2.1 AA violations | `tests/e2e/home.spec.ts`: "has no WCAG 2.1 AA violations" |
| US2-AS5 keyboard order and visible focus | `tests/e2e/home.spec.ts`: "no focus trap": Tab from the page does not get stuck; the page has no interactive elements (spec assumption) |
| US3-AS1/AS2 README completeness | Documented manual check (quickstart V4) |

## Project Structure

### Documentation (this feature)

```text
specs/001-init-react-ts-tailwind/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (no data entities; states why)
├── quickstart.md        # Phase 1 output: validation guide
├── contracts/
│   ├── npm-scripts.md   # Tooling contract: the five gate scripts
│   └── home-page-ui.md  # UI contract: landmarks, content, layout, a11y
├── checklists/
│   └── requirements.md  # From /speckit-specify
└── tasks.md             # Phase 2 output (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
.
├── index.html                 # Vite HTML entry: lang="en", title, viewport meta
├── package.json               # Scripts contract; engines.node >=22.12
├── package-lock.json          # Committed; `npm ci` in automation
├── .nvmrc                     # 22
├── .gitignore                 # node_modules, dist, test-results, playwright-report
├── tsconfig.json              # Single strict config: src, tests, *.config.ts
├── vite.config.ts             # React + Tailwind plugins; Vitest `test` block (jsdom, src/**/*.test.tsx)
├── eslint.config.js           # Flat config: typescript-eslint strictTypeChecked + react-hooks
├── playwright.config.ts       # Chromium, webServer = build + preview on strict port, list reporter
├── README.md                  # Adds "Development" section (FR-017)
├── src/
│   ├── main.tsx               # createRoot + StrictMode, imports index.css
│   ├── index.css              # The only stylesheet: @import "tailwindcss";
│   ├── App.tsx                # Page layout: SiteHeader, <main> with h1 + welcome, SiteFooter
│   ├── App.test.tsx           # Component test: landmarks, app name, h1, welcome text
│   ├── components/
│   │   ├── SiteHeader.tsx     # <header> with the app name
│   │   └── SiteFooter.tsx     # <footer> with a copyright line
│   └── test/
│       └── setup.ts           # @testing-library/jest-dom/vitest matchers, RTL cleanup
└── tests/
    └── e2e/
        └── home.spec.ts       # Viewports, landmarks, axe scan, no focus trap
```

**Structure Decision**: Single frontend project at the repository root (FR-001). Component and unit
tests are colocated with the source (`src/**/*.test.tsx`) so Vitest includes only them. Playwright
specs live in `tests/e2e/` so the two runners never pick up each other's files. There is no
`backend/`, router or `pages/` directory because they are out of scope (FR-018).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle II: US1-AS3 (failing check → non-zero exit) and US3 (README) are verified by a documented manual check, not an automated test | These scenarios are about the tooling itself and about prose. The gate already proves the success path automatically on every story | A meta-test that plants errors and runs `tsc`/ESLint/Vitest as child processes would add slow, brittle test infrastructure that YAGNI (Principle V) argues against. Spec SC-005 explicitly allows a documented manual check |
