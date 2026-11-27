---

description: "Task list for 001-init-react-ts-tailwind"
---

# Tasks: Initialize Project with React, TypeScript and Tailwind CSS

**Input**: Design documents from `specs/001-init-react-ts-tailwind/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/npm-scripts.md, contracts/home-page-ui.md, quickstart.md

**Tests**: Included. Constitution Principle II (Test-First, non-negotiable) requires tests written and
seen failing before the implementation they cover, and every acceptance scenario mapped to a test or a
documented manual check (spec SC-005, plan "Acceptance-scenario traceability").

**Organization**: Tasks are grouped by user story. Per constitution Principle III, the first user story
of the first feature scaffolds the project, so Phase 1 (Setup) and Phase 2 (Foundational) ship in the
**same pull request as User Story 1**. Each story is one pull request stacked on the previous one.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

Single project at the repository root (plan.md "Project Structure"): app code in `src/`, component
tests colocated as `src/**/*.test.tsx`, Playwright specs in `tests/e2e/`.

**Data model**: `data-model.md` defines no entities and no constrained fields, so no field citations
apply. Its "Static content" table is the source for page copy (app name, `h1`, welcome message, footer
line).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package manifest, Node version pin, ignore rules and the committed lock file

- [X] T001 Create `package.json` at the repository root: `"name": "speckit-sample"`, `"private": true`, `"type": "module"`, `"engines": { "node": ">=22.12" }`, and the scripts exactly as listed in contracts/npm-scripts.md (gate scripts `typecheck`, `lint`, `test:unit`, `test:e2e`, `build`, plus helpers `dev`, `preview`) in package.json
- [X] T002 [P] Create `.nvmrc` containing `22` (research R-1) in .nvmrc
- [X] T003 [P] Create `.gitignore` ignoring `node_modules/`, `dist/`, `test-results/`, `playwright-report/`, `blob-report/` and `*.log` in .gitignore
- [X] T004 Install dependencies with `npm install` to create package-lock.json: runtime `react`, `react-dom` (19.x); dev `typescript`, `@types/react`, `@types/react-dom`, `@types/node`, `vite`, `@vitejs/plugin-react`, `tailwindcss`, `@tailwindcss/vite`, `eslint`, `@eslint/js`, `typescript-eslint`, `eslint-plugin-react-hooks`, `globals`, `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/dom`, `@testing-library/jest-dom`, `@playwright/test`, `@axe-core/playwright` (depends on T001; no other runtime dependencies, plan Principle V justification) in package-lock.json

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: TypeScript, Vite, Tailwind and Vitest wiring that every story's code and tests rely on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 [P] Create the single strict `tsconfig.json` per research R-3: `strict`, `noUncheckedIndexedAccess`, `noImplicitOverride`, `noFallthroughCasesInSwitch`, `noUnusedLocals`, `noUnusedParameters`, `exactOptionalPropertyTypes`, `verbatimModuleSyntax`, `noEmit`, `jsx: "react-jsx"`, `module: "ESNext"`, `target: "ES2022"`, `lib: ["ES2022", "DOM", "DOM.Iterable"]`, `moduleResolution: "bundler"`, `skipLibCheck`, `types: ["vite/client", "node"]`; `include` covers `src`, `tests` and `*.config.ts` in tsconfig.json
- [X] T006 [P] Create the Vite HTML entry per contracts/home-page-ui.md "Document": `<html lang="en">`, `<meta charset="UTF-8">`, `<meta name="viewport" content="width=device-width, initial-scale=1.0">`, `<title>speckit-sample</title>`, `<div id="root"></div>` and `<script type="module" src="/src/main.tsx"></script>` in index.html
- [X] T007 [P] Create the only stylesheet containing exactly `@import "tailwindcss";` (research R-5, FR-010) in src/index.css
- [X] T008 [P] Create the Vitest setup file that imports `@testing-library/jest-dom/vitest` and registers `cleanup` from `@testing-library/react` in `afterEach` (imported from `vitest`) (research R-6) in src/test/setup.ts
- [X] T009 Create `vite.config.ts` using `defineConfig` from `vitest/config` with plugins `react()` and `tailwindcss()`, and a `test` block: `environment: "jsdom"`, `include: ["src/**/*.test.{ts,tsx}"]`, `setupFiles: ["src/test/setup.ts"]`, `globals: false` (research R-5, R-6; depends on T008) in vite.config.ts

**Checkpoint**: Foundation ready. User Story 1 can begin.

---

## Phase 3: User Story 1 - Working project foundation with quality gates (Priority: P1) 🎯 MVP

**Goal**: A clean checkout installs from the lock file and all five gate scripts run non-interactively,
pass, and exit non-zero on failure, with at least one real test in each suite.

**Independent Test**: On a clean checkout run `npm ci`, then `npm run typecheck`, `lint`, `test:unit`,
`test:e2e`, `build`; each exits 0 without prompting. Plant a type error, a lint error and a failing test
and confirm the matching command exits non-zero (quickstart.md V1 and V2).

### Tooling configuration for User Story 1

- [X] T010 [P] [US1] Create the ESLint 9 flat config per research R-4: `@eslint/js` recommended, `typescript-eslint` `strictTypeChecked` + `stylisticTypeChecked` with `parserOptions.projectService: true` and `tsconfigRootDir: import.meta.dirname`, `eslint-plugin-react-hooks` recommended rules for `**/*.{ts,tsx}`, `globals.browser` for `src/**` and `globals.node` for config files, ignores `dist`, `playwright-report`, `test-results`; disable type-checked rules for `eslint.config.js` itself if needed (`tseslint.configs.disableTypeChecked`) in eslint.config.js
- [X] T011 [P] [US1] Create the Playwright config per research R-7: `testDir: "tests/e2e"`, one `chromium` project (`devices["Desktop Chrome"]`), `use.baseURL: "http://localhost:4173"`, `reporter: "list"`, `forbidOnly: !!process.env.CI`, `retries: process.env.CI ? 1 : 0`, `webServer: { command: "npm run build && npm run preview -- --port 4173 --strictPort", url: "http://localhost:4173", reuseExistingServer: false, timeout: 120_000 }` in playwright.config.ts

### Tests for User Story 1 (write first, confirm they FAIL) ⚠️

- [X] T012 [P] [US1] Write the smoke component test: import `describe`/`it`/`expect` from `vitest`, render `<App />` from `./App`, and assert `screen.getByRole("heading", { level: 1, name: /speckit-sample/ })` is in the document. Run `npm run test:unit` and confirm it fails because `src/App.tsx` does not exist yet, in src/App.test.tsx
- [X] T013 [US1] Write the e2e smoke test: `test("home page loads and has no WCAG 2.1 AA violations")` navigates to `/`, expects `page` to have title `speckit-sample`, then runs `new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze()` and expects `violations` to equal `[]` (FR-008). Install Chromium once with `npx playwright install --with-deps chromium`, run `npm run test:e2e` and confirm it fails (build fails without `src/main.tsx`) (depends on T011) in tests/e2e/home.spec.ts

### Implementation for User Story 1

- [X] T014 [US1] Create a minimal `App` function component (named export) that renders `<main>` containing one `<h1>` with the heading text from data-model.md "Static content" (e.g. "Welcome to speckit-sample"); no other markup yet, so US2 owns the full layout. Run `npm run test:unit` and confirm T012 passes, in src/App.tsx
- [X] T015 [US1] Create the entry point: `import "./index.css"`, look up `document.getElementById("root")`, throw an `Error` if it is `null` (no non-null assertion, Principle I), then `createRoot(root).render(<StrictMode><App /></StrictMode>)` in src/main.tsx
- [ ] T016 [US1] Run the gate per quickstart.md V1 from the repository root: `npm ci`, `npm run typecheck`, `npm run lint`, `npm run test:unit`, `npm run test:e2e`, `npm run build`. Fix any errors in the files above until every command exits 0, no command waits for input or enters watch mode, and `dist/index.html` is produced (US1-AS1, US1-AS2; SC-001, SC-002). Commit package-lock.json
- [ ] T017 [US1] Perform the manual negative checks from quickstart.md V2 that apply at this stage (type error → `typecheck`, `any` → `lint`, changed heading expectation → `test:unit`, port 4173 already in use → `test:e2e` fails fast), confirm each exits non-zero, revert every plant, and record the results in the US1 pull request description (US1-AS3; documented manual check allowed by plan Complexity Tracking) per specs/001-init-react-ts-tailwind/quickstart.md

**Checkpoint**: User Story 1 is complete and independently verifiable. All five scripts are green; this is the MVP and the first pull request (includes Phases 1 and 2).

---

## Phase 4: User Story 2 - Accessible, responsive home page (Priority: P2)

**Goal**: The home page shows a header with the app name, a main area with one `h1` and a welcome
message, and a footer; it is mobile-first from 320 px, uses semantic landmarks, has no focus trap, and
passes an axe WCAG 2.1 AA scan (contracts/home-page-ui.md).

**Independent Test**: `npm run test:unit` and `npm run test:e2e` pass with the US2 assertions; manually,
the page at 320 px and 1280 px shows all three landmarks with no horizontal scroll and reflows at 200%
zoom (quickstart.md V3).

### Tests for User Story 2 (write first, confirm they FAIL) ⚠️

- [X] T018 [P] [US2] Extend the component test per contracts/home-page-ui.md "Landmarks and content", querying by role and text only: `banner` contains the text `speckit-sample`; `main` contains exactly one level-1 heading and the welcome paragraph text; `contentinfo` is present; the whole render has exactly one `heading` with `level: 1` (US2-AS3). Keep the US1 smoke assertion. Run `npm run test:unit` and confirm the new assertions fail, in src/App.test.tsx
- [X] T019 [P] [US2] Extend the e2e spec per research R-8 and the plan traceability table, using these test names: "mobile 320px" and "desktop 1280px" (`page.setViewportSize` 320×640 and 1280×800; assert `getByRole("banner")` with text `speckit-sample`, `getByRole("main")` with the level-1 heading and welcome text, and `getByRole("contentinfo")` are visible, and `document.documentElement.scrollWidth <= window.innerWidth`) (US2-AS1, US2-AS2, SC-004); rename the axe test to "has no WCAG 2.1 AA violations" (US2-AS4, SC-003); add "no focus trap": press `Tab` several times from the page and assert focus never stays on one element inside the page and the document still has exactly one level-1 heading (US2-AS5). Run `npm run test:e2e` and confirm the new tests fail, in tests/e2e/home.spec.ts

### Implementation for User Story 2

- [X] T020 [P] [US2] Create `SiteHeader` (named export): a top-level `<header>` showing the app name `speckit-sample` as a text element, not a heading (research R-9), styled with Tailwind utilities only (`text-slate-900`, padding inside `max-w-3xl mx-auto px-4`, `sm:`/`lg:` increases only), in src/components/SiteHeader.tsx
- [X] T021 [P] [US2] Create `SiteFooter` (named export): a top-level `<footer>` with the footer line from data-model.md "Static content" (e.g. "© speckit-sample"), no links, muted `text-slate-600` on white, same container utilities, in src/components/SiteFooter.tsx
- [X] T022 [US2] Update `App` to the full layout per research R-9 and contracts/home-page-ui.md: root `min-h-dvh flex flex-col bg-white text-slate-900`; `<SiteHeader />`; `<main className="flex-1 ...">` with the single `h1` (`break-words`) and one short welcome sentence from data-model.md "Static content"; `<SiteFooter />`. No animations or transitions, no colors lighter than `slate-600` for text, no interactive elements (depends on T020, T021) in src/App.tsx
- [X] T023 [US2] Run `npm run typecheck`, `npm run lint`, `npm run test:unit` and `npm run test:e2e`; fix until all exit 0. Then do the manual look from quickstart.md V3 (320 px, 1280 px, 200% zoom, Tab) and the deferred V2 plant "remove the `<footer>`" → `test:e2e` exits non-zero; revert. Record results in the US2 pull request description per specs/001-init-react-ts-tailwind/quickstart.md

**Checkpoint**: User Stories 1 and 2 both work; the gate is green with the full home page.

---

## Phase 5: User Story 3 - Contributor onboarding documentation (Priority: P3)

**Goal**: A new contributor can install, run, test and build the app using only the README.

**Independent Test**: Follow the README from top to bottom on a fresh clone with Node 22 installed and
complete install, dev server, the four check commands and the build in under 15 minutes, not counting
downloads (quickstart.md V4, SC-006).

### Implementation for User Story 3

- [X] T024 [US3] Add a "Development" section to the README below the existing title (FR-017), covering: prerequisites (Node.js 22 LTS `>=22.12`, `nvm use` reads `.nvmrc`, npm); one-time Playwright setup `npx playwright install --with-deps chromium` (note that `--with-deps` may need sudo on Linux); install with `npm ci`; run locally with `npm run dev` and `npm run build && npm run preview`; a table of the five gate scripts with their commands and what each checks (from contracts/npm-scripts.md); notes that every script is non-interactive, that `test:e2e` builds and serves the app itself on port 4173 and fails fast if that port is in use; and the stack (Vite, React, TypeScript strict, Tailwind CSS v4 with `src/index.css` as the only stylesheet, ESLint, Vitest + React Testing Library, Playwright + axe-core) in README.md
- [X] T025 [US3] Perform the README check from quickstart.md V4: on a fresh clone, follow only README.md and confirm install, dev server, `typecheck`, `lint`, `test:unit`, `test:e2e` and `build` all work and that the Node version and Playwright browser install step are stated (US3-AS1, US3-AS2); fix gaps in README.md and record the result in the US3 pull request description per specs/001-init-react-ts-tailwind/quickstart.md

**Checkpoint**: All user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Scope and constraint checks across all stories, then the full validation run

- [X] T026 [P] Audit scope and constraints: `dependencies` in package.json contain only `react` and `react-dom` (Principle V); `src/index.css` is the only `.css` file and no inline `<style>` exists (FR-010); no router, store, `fetch`, auth or deployment config exists (FR-018); no `any` and no non-null assertions in `src/`, `tests/` or config files (Principle I). Fix any finding in the offending file, starting from package.json
- [X] T027 Run the full validation in specs/001-init-react-ts-tailwind/quickstart.md from a clean state (`rm -rf node_modules dist test-results playwright-report`, then V1 through V4) and confirm every V1 command exits 0 and every V2 plant fails as expected

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies. T004 depends on T001.
- **Foundational (Phase 2)**: Depends on Setup (needs installed packages). T009 depends on T008.
- **User Story 1 (Phase 3)**: Depends on Foundational. Ships in one PR together with Phases 1 and 2.
- **User Story 2 (Phase 4)**: Depends on US1 (needs the working gate, `App`, `main.tsx` and both test files). Stacked PR.
- **User Story 3 (Phase 5)**: Technically depends only on US1 (the commands it documents). Delivered after US2 as a stacked PR so the README describes the final state.
- **Polish (Phase 6)**: Depends on all stories.

### User Story Dependencies

```text
Setup ─► Foundational ─► US1 (P1, MVP) ─┬─► US2 (P2) ─┐
                                        └─► US3 (P3) ─┴─► Polish
```

### Within Each User Story

- Tooling config (T010, T011) before the tests that need it.
- Tests are written and seen failing before implementation (T012/T013 before T014/T015; T018/T019 before T020–T022).
- Components (T020, T021) before the page that composes them (T022).
- Gate run last in each story (T016, T023, T025).

### Parallel Opportunities

- Phase 1: T002 and T003 alongside T001.
- Phase 2: T005, T006, T007 and T008 in parallel; then T009.
- US1: T010, T011 and T012 in parallel; T013 after T011.
- US2: T018 and T019 in parallel; then T020 and T021 in parallel.
- US3 can be written in parallel with US2 by a second contributor (different file: README.md).
- Polish: T026 alongside final README review.

---

## Parallel Example: User Story 1

```bash
# After Phase 2, launch together:
Task: "Create the ESLint 9 flat config in eslint.config.js"
Task: "Create the Playwright config in playwright.config.ts"
Task: "Write the smoke component test in src/App.test.tsx"
# Then:
Task: "Write the e2e smoke test in tests/e2e/home.spec.ts"
```

## Parallel Example: User Story 2

```bash
# Tests first, together:
Task: "Extend the component test in src/App.test.tsx"
Task: "Extend the e2e spec in tests/e2e/home.spec.ts"
# Then components, together:
Task: "Create SiteHeader in src/components/SiteHeader.tsx"
Task: "Create SiteFooter in src/components/SiteFooter.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational).
2. Complete Phase 3 (US1): tooling config, failing smoke tests, minimal `App`, entry point.
3. **STOP and VALIDATE**: quickstart.md V1 green and V2 plants fail (T016, T017).
4. Open the first PR. The issue-flow gate can now run on every later story.

### Incremental Delivery

1. Setup + Foundational + US1 → gate green → PR 1 (MVP).
2. US2 → full accessible home page, gate green → PR 2 stacked on PR 1.
3. US3 → README Development section → PR 3 stacked on PR 2.
4. Polish → final audit and full quickstart run before the last PR is approved.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks.
- Tests query by role, label or text, never by class names or DOM structure (Principle II, contracts/home-page-ui.md).
- Styling is Tailwind utilities only; never add a second stylesheet.
- Commit after each task or logical group; stop at any checkpoint to validate the story independently.
