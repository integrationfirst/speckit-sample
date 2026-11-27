# Contract: npm scripts (tooling contract)

**Source of authority**: Constitution Principle III, spec FR-003, FR-004, FR-005, FR-006, FR-007, FR-008 and FR-009.

The issue-flow test gate calls these scripts by name. Renaming or removing one is a constitution
amendment.

## Gate scripts

| Script | Command | Passes when | Fails (non-zero exit) when | Must not |
|--------|---------|-------------|----------------------------|----------|
| `typecheck` | `tsc --noEmit` | 0 type errors across `src/`, `tests/` and `*.config.ts` under strict settings | Any type error | Emit files |
| `lint` | `eslint . --max-warnings 0` | 0 errors and 0 warnings with type-aware + react-hooks rules | Any error or warning | Auto-fix files |
| `test:unit` | `vitest run` | All `src/**/*.test.{ts,tsx}` pass (at least 1 home page test) | Any failing test, or no tests found | Enter watch mode |
| `test:e2e` | `playwright test` | All `tests/e2e/**` specs pass in Chromium against a server the test starts itself, including the axe WCAG 2.1 AA scan | Any failing test, port 4173 already in use, browsers not installed, or build failure | Prompt, reuse a stray server, or open an HTML report or browser window |
| `build` | `vite build` | Production bundle written to `dist/` | Any build or compile error | Prompt |

## Non-gate helper scripts

| Script | Command | Purpose |
|--------|---------|---------|
| `dev` | `vite` | Local development server (interactive; never run by the gate) |
| `preview` | `vite preview` | Serve `dist/`; used by the Playwright `webServer` and for local checks |

## Install contract

- `package-lock.json` is committed. Automation uses `npm ci` (FR-002).
- `engines.node`: `>=22.12`. `.nvmrc`: `22`.
- One-time setup for e2e: `npx playwright install --with-deps chromium`.
