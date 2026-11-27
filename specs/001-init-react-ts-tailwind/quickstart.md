# Quickstart & Validation: Initialize Project with React, TypeScript and Tailwind CSS

**Feature**: `001-init-react-ts-tailwind` | **Contracts**: [npm-scripts](./contracts/npm-scripts.md), [home-page-ui](./contracts/home-page-ui.md)

## Prerequisites

- Node.js 22 LTS (`>=22.12`; `nvm use` reads `.nvmrc`) and npm.
- One-time setup: `npx playwright install --with-deps chromium` (on Linux, `--with-deps` may need sudo).

## V1: Gate run (US1-AS1, US1-AS2; SC-001, SC-002)

From a clean checkout at the repository root:

```bash
npm ci
npm run typecheck   # expect: exits 0, no output errors
npm run lint        # expect: exits 0, no problems reported
npm run test:unit   # expect: "Test Files  1 passed", exits 0, returns to prompt (no watch)
npm run test:e2e    # expect: builds, starts preview on :4173, all tests pass in chromium, exits 0
npm run build       # expect: dist/index.html and hashed assets written, exits 0
```

Check that `echo $?` prints `0` after each command and that no command waits for input.

## V2: Failure path (US1-AS3; manual negative check)

Run each check below on a throwaway branch or with `git stash` afterwards, and confirm a **non-zero**
exit for each:

| Plant | Command | Expected |
|-------|---------|----------|
| `const n: number = "x";` in `src/App.tsx` | `npm run typecheck` | Exit ≠ 0, TS2322 reported |
| `const x: any = 1; console.log(x);` in `src/App.tsx` | `npm run lint` | Exit ≠ 0, `@typescript-eslint/no-explicit-any` reported |
| Change the expected heading text in `src/App.test.tsx` | `npm run test:unit` | Exit ≠ 0, 1 failed |
| Remove the `<footer>` from the page | `npm run test:e2e` | Exit ≠ 0, landmark assertion fails |
| Start `npm run preview -- --port 4173` in another terminal, then run e2e | `npm run test:e2e` | Fails fast with a port-in-use error, does not hang |

Revert all plants afterwards.

## V3: Home page behaviour (US2; SC-003, SC-004)

The automated tests cover this in `npm run test:unit` and `npm run test:e2e`. For a quick manual
look:

```bash
npm run dev         # open the printed local URL
```

- Use DevTools device mode at 320 px and at 1280 px. The header (`speckit-sample`), the `h1` with the
  welcome message, and the footer are visible, and there is no horizontal scrollbar.
- Zoom to 200%. The text reflows and nothing is clipped.
- Press Tab. Focus is not trapped on the page (there are no interactive elements).

## V4: README check (US3; SC-006)

Following only the README on a fresh clone, a new contributor can install, start the dev server, run
all four check commands, and build within 15 minutes (not counting downloads). Confirm that the
README states the Node version and the Playwright browser install step.

## Done

The feature is validated when V1 is fully green, every V2 plant fails as expected, and V3 and V4 are
confirmed.
