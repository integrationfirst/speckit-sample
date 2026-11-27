# speckit-sample

## Development

### Prerequisites

- **Node.js 22 LTS** (`>=22.12`). The repository has an `.nvmrc`, so with nvm you can run `nvm use`
  (or `nvm install` the first time).
- **npm** (ships with Node.js).

### One-time setup

Install the Chromium browser that the end-to-end tests use:

```bash
npx playwright install --with-deps chromium
```

On Linux, `--with-deps` installs system packages and may ask for `sudo`.

### Install

```bash
npm ci
```

`npm ci` installs the exact versions in the committed `package-lock.json`.

### Run locally

```bash
npm run dev                          # development server with hot reload; open the printed URL
npm run build && npm run preview     # production build served from dist/
```

### Checks

These five scripts are the quality gate. Every pull request must pass all of them.

| Script | Command | What it checks |
|--------|---------|----------------|
| `npm run typecheck` | `tsc --noEmit` | No type errors in `src/`, `tests/` and `*.config.ts` under strict TypeScript |
| `npm run lint` | `eslint . --max-warnings 0` | No ESLint errors or warnings (type-aware and React Hooks rules) |
| `npm run test:unit` | `vitest run` | All component tests in `src/**/*.test.{ts,tsx}` pass |
| `npm run test:e2e` | `playwright test` | All browser tests in `tests/e2e/` pass in Chromium, including a WCAG 2.1 AA accessibility scan with axe-core |
| `npm run build` | `vite build` | The production bundle builds into `dist/` |

Notes:

- Every script is non-interactive: none prompts for input or stays in watch mode, and each exits
  non-zero on failure.
- `test:e2e` builds the app and serves it itself on port **4173**. If that port is already in use, it
  fails fast instead of reusing the other server. Stop anything running on 4173 (for example a
  `npm run preview`) before running it.

### Stack

- [Vite](https://vite.dev/) for the dev server and build
- [React](https://react.dev/) with [TypeScript](https://www.typescriptlang.org/) in strict mode
- [Tailwind CSS v4](https://tailwindcss.com/) utilities; `src/index.css` is the only stylesheet
- [ESLint](https://eslint.org/) with typescript-eslint
- [Vitest](https://vitest.dev/) and [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/) for component tests
- [Playwright](https://playwright.dev/) and [axe-core](https://github.com/dequelabs/axe-core) for end-to-end and accessibility tests
