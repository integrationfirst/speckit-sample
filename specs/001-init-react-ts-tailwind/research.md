# Research: Initialize Project with React, TypeScript and Tailwind CSS

**Feature**: `001-init-react-ts-tailwind` | **Date**: 2026-11-27 | **Plan**: [plan.md](./plan.md)

The stack is fixed by the issue and the constitution. This research covers how to configure it so
that the five scripts are strict, non-interactive and reliable. There were no open NEEDS
CLARIFICATION items. Exact package versions are the latest stable releases at implementation time,
recorded in `package-lock.json`.

## R-1 Node.js version

- **Decision**: Node.js 22 LTS. `.nvmrc` = `22`, `package.json` `engines.node` = `>=22.12`.
- **Rationale**: Node.js 22 is an LTS line and is the version installed in the current dev
  environment. 22.12 is the minimum that current Vite releases support on the 22 line. Newer LTS
  lines (24 and later) also satisfy the range.
- **Alternatives considered**: Pinning Node 24 LTS. This was rejected for now because it would force
  contributors and agents to upgrade from the installed Node 22 with no benefit for this feature.
  Revisit before Node 22 reaches end of life (April 2027).

## R-2 Scaffolding method

- **Decision**: Write the scaffold files by hand, following the shape of the official Vite
  `react-ts` template, then `npm install` the listed packages to create the lock file.
- **Rationale**: `npm create vite` prompts when the target directory is not empty, and the root
  already holds `README.md`, `.specify/`, `.claude/` and `specs/`. Writing the files by hand avoids
  prompts (constitution III), skips template extras that YAGNI rules out (`App.css`, demo counter,
  logos, `eslint-plugin-react-refresh`), and fits the single-`tsconfig` decision (R-3).
- **Alternatives considered**: Running `create-vite` in a temporary directory and copying files
  over. This was rejected because it brings in demo code that must then be deleted, and the result
  is the same.

## R-3 TypeScript configuration and `typecheck`

- **Decision**: One `tsconfig.json` with `strict: true` plus `noUncheckedIndexedAccess`,
  `noImplicitOverride`, `noFallthroughCasesInSwitch`, `noUnusedLocals`, `noUnusedParameters`,
  `exactOptionalPropertyTypes`, `verbatimModuleSyntax`, `noEmit: true`, `jsx: "react-jsx"`,
  `moduleResolution: "bundler"`, `types: ["vite/client", "node"]`. `include` covers `src`, `tests`
  and the `*.config.ts` files. Script: `"typecheck": "tsc --noEmit"`.
- **Rationale**: The constitution names `tsc --noEmit` literally. A single config makes that command
  check everything: app, tests and config files (FR-005, "all source code"). The extra flags are the
  "strictest mode" that FR-005 asks for, beyond `strict`.
- **Alternatives considered**: The Vite template's project references (`tsconfig.app.json` +
  `tsconfig.node.json` with `tsc -b`). This was rejected because plain `tsc --noEmit` on the root
  config checks nothing when the root has `files: []`, so the literal constitution command would
  silently pass. Mixing DOM and Node types in one config is an acceptable trade-off for a project
  this size.

## R-4 Linting

- **Decision**: ESLint 9 flat config (`eslint.config.js`) using `@eslint/js` recommended,
  `typescript-eslint` `strictTypeChecked` + `stylisticTypeChecked` with
  `parserOptions.projectService: true`, and `eslint-plugin-react-hooks` recommended rules. Globals
  from the `globals` package (browser for `src`, node for config files). Ignore `dist`,
  `playwright-report` and `test-results`. Script: `"lint": "eslint . --max-warnings 0"`.
- **Rationale**: Type-aware rules plus hooks rules satisfy FR-006 and the constitution's stack
  section. `--max-warnings 0` keeps warnings from piling up. `strictTypeChecked` includes
  `no-explicit-any`, which backs up Principle I.
- **Alternatives considered**: `recommendedTypeChecked` only. This was rejected because the stricter
  preset costs nothing on an empty codebase and is much harder to adopt later. Biome was rejected
  because the constitution names ESLint.

## R-5 Tailwind CSS integration

- **Decision**: Tailwind CSS v4 with the `@tailwindcss/vite` plugin. The single stylesheet is
  `src/index.css`, which contains `@import "tailwindcss";` and is imported once from `src/main.tsx`.
  No `tailwind.config.js` and no PostCSS config.
- **Rationale**: v4's Vite plugin is the zero-config path. Content detection is automatic, so there
  is no config file to maintain. One entry file satisfies FR-010 and constitution IV.
- **Alternatives considered**: Tailwind v3 with PostCSS and `tailwind.config.js`. This was rejected
  because it is legacy and needs more files.

## R-6 Unit and component testing

- **Decision**: Vitest configured in the `test` block of `vite.config.ts` (`environment: "jsdom"`,
  `include: ["src/**/*.test.{ts,tsx}"]`, `setupFiles: ["src/test/setup.ts"]`, `globals: false`).
  The setup file imports `@testing-library/jest-dom/vitest` and registers RTL `cleanup` in
  `afterEach`. Tests import `describe`/`it`/`expect` from `vitest` explicitly. Script:
  `"test:unit": "vitest run"`.
- **Rationale**: `vitest run` never enters watch mode (FR-004). The explicit `include` keeps
  Playwright specs out. With `globals: false` there is no global-types setup, and
  `@testing-library/react` does not auto-clean without globals, so the setup file calls `cleanup`.
  Queries use roles and text (Principle II).
- **Alternatives considered**: `happy-dom`. It is faster, but jsdom is the RTL reference environment
  and speed does not matter at this size. A separate `vitest.config.ts` was rejected as an extra
  file with no benefit.

## R-7 End-to-end testing and accessibility scan

- **Decision**: Playwright with one `chromium` project. `webServer.command` =
  `npm run build && npm run preview -- --port 4173 --strictPort`, `url` = `http://localhost:4173`,
  `reuseExistingServer: false`, `timeout: 120_000`. `reporter: "list"`, `forbidOnly: !!process.env.CI`,
  `retries: process.env.CI ? 1 : 0`. Accessibility uses `@axe-core/playwright` with tags
  `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`. Script: `"test:e2e": "playwright test"`.
- **Rationale**:
  - Testing the production build via `vite preview` checks what ships (FR-008: the test starts the
    app itself).
  - `--strictPort` together with `reuseExistingServer: false` makes the "port already in use" edge
    case fail fast with a clear error instead of silently testing another server.
  - The `list` reporter never opens a browser window. The default `html` reporter opens one on
    failure, which would hang a non-interactive run.
  - If browsers are missing, Playwright exits with an error that names `npx playwright install`.
    It does not hang (edge case). The README documents `npx playwright install --with-deps chromium`
    as a one-time step.
- **Alternatives considered**: Testing against the dev server (`vite`). This was rejected because
  it is less faithful to production. `pa11y` or Lighthouse were rejected because axe-core is the de
  facto standard and integrates natively with Playwright. Multi-browser projects are out of scope
  per the spec assumptions.

## R-8 Responsive and visibility checks in e2e

- **Decision**: For each viewport (320×640 and 1280×800), assert that the `banner`, `main` (with the
  `h1` and the welcome text) and `contentinfo` landmarks are visible, and that
  `document.documentElement.scrollWidth <= window.innerWidth` (no horizontal scroll).
- **Rationale**: These directly encode US2-AS1/AS2 and SC-004 with cheap DOM assertions. No
  screenshot baselines are needed.
- **Alternatives considered**: Visual regression snapshots. This was rejected because snapshots are
  brittle across OS font rendering and add nothing to the acceptance criteria.

## R-9 Home page design for WCAG 2.1 AA

- **Decision**: Body text `text-slate-900` on `bg-white` (about 17:1) and muted text
  `text-slate-600` (about 7.5:1). There are no low-contrast grays (`slate-400` and lighter) for
  text. Layout is mobile-first: `min-h-dvh flex flex-col`, content in `max-w-3xl mx-auto px-4`,
  with `sm:`/`lg:` increases for padding and type size only. `break-words` on headings guards
  against overflow at 320 px. The header shows the app name as a text element, not a heading. The
  single `h1` sits in `<main>`. `index.html` sets `lang="en"`, `<title>speckit-sample</title>` and
  the viewport meta. There are no animations, so reduced motion is respected by default.
- **Rationale**: This meets FR-011–FR-016 with plain utilities. Putting the `h1` in `<main>` meets
  FR-012 and the "exactly one top-level heading" scenario. Using `rem`-based Tailwind sizes means
  200% zoom reflows instead of clipping.
- **Alternatives considered**: An `h1` in the header for the app name. This was rejected because
  FR-012 puts the top-level heading in the main area.

## R-10 Additional non-gate scripts

- **Decision**: Add `"dev": "vite"` and `"preview": "vite preview"` besides the five gate scripts.
- **Rationale**: US3 requires contributors to run the app locally, and the Playwright `webServer`
  needs `preview`. The constitution says the five gate scripts must exist exactly as named and must
  not be renamed or removed. Helper scripts that the gate does not run do not conflict with that.
  This reading is recorded in the plan's Constitution Check so reviewers can confirm it.
- **Alternatives considered**: Calling `npx vite` directly in the README and the Playwright config.
  This was rejected because it is less discoverable and goes against conventional npm usage.
