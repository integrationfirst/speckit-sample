# speckit-sample Constitution

## Core Principles

### I. Type Safety

- All source code MUST be TypeScript compiled with `"strict": true`.
- `any` MUST NOT be used unless a comment on the same line states why no precise type is possible;
  prefer `unknown` plus narrowing.
- `npm run typecheck` (`tsc --noEmit`) MUST pass with zero errors before a story is considered done.

Rationale: type errors are the cheapest defects to catch, and the automated gate runs before any
human review.

### II. Test-First (NON-NEGOTIABLE)

- Tests MUST be written before the implementation they cover, MUST be seen to fail, and only then
  MAY the implementation make them pass (red → green → refactor).
- Unit and component tests use Vitest with React Testing Library (`npm run test:unit` =
  `vitest run`); tests query by role, label or text, not by implementation details.
- UI and end-to-end behaviour, including automated accessibility checks, use Playwright
  (`npm run test:e2e` = `playwright test`).
- Every acceptance scenario in a spec MUST map to at least one automated test.
- Bug fixes MUST start with a test that reproduces the bug.

Rationale: the issue-to-pr workflow loops back to fixing until the suites pass, so the tests are
the definition of done.

### III. Tooling Contract

- `package.json` MUST define exactly these scripts, which the issue-flow test gate runs:
  `typecheck`, `lint` (ESLint, zero errors), `test:unit`, `test:e2e` and `build`.
- The first User Story of the first feature MUST scaffold the project (Vite + React + TypeScript +
  Tailwind CSS) with all five scripts working, even if some suites start with a single smoke test.
- Scripts MUST run non-interactively and exit non-zero on failure; no watch mode in these scripts.
- Renaming or removing one of these scripts is a constitution amendment.

Rationale: the workflow gate calls these commands by name; a missing script fails every story.

### IV. Accessible, Responsive UI

- Markup MUST be semantic HTML (landmarks, headings in order, real buttons and links, labelled form
  controls) and meet WCAG 2.1 AA, including keyboard operability, visible focus and color contrast.
- Styling MUST use Tailwind CSS utility classes; the only stylesheet is the Tailwind entry file.
  Shared styles are expressed as components, not custom CSS.
- Layouts MUST be mobile-first and work from 320 px wide upward.
- Playwright suites MUST include an automated accessibility scan of each page they cover.

Rationale: accessibility and responsiveness are cheaper built in than retrofitted, and automated
checks keep them from regressing.

### V. Simplicity

- Components MUST be small and focused on one responsibility; extract when a component mixes
  data fetching, state and presentation.
- A new runtime dependency MUST be justified in the plan (what it replaces and why).
- Local component state is the default; global state (context or a store) MUST NOT be introduced
  until at least two distant components need the same state.
- YAGNI: build only what the current story's acceptance criteria require.

Rationale: small, dependency-light code is easier for both agents and reviewers to verify.

## Technology Stack & Constraints

- Runtime and tooling: Node.js LTS with npm (`package-lock.json` committed; `npm ci` in automation).
- Build: Vite. UI: React with function components and hooks. Language: TypeScript (strict).
- Styling: Tailwind CSS. Testing: Vitest, React Testing Library, Playwright.
- Linting: ESLint with TypeScript and React Hooks rules; formatting is not a review topic.
- No secrets, tokens or credentials in the repository; configuration comes from environment
  variables documented in the README.

## Development Workflow & Quality Gates

- Work starts from a GitHub issue labelled `coding-agent` and flows through the issue-to-pr
  workflow: spec (product owner, business analyst, solution architect) → plan (team lead) →
  tasks (team lead) → implementation per User Story → automated tests → QA (QA lead) → pull request.
- Each User Story is delivered as one pull request; stories stack on the previous story's branch.
- A pull request MUST NOT be opened until `typecheck`, `lint`, `test:unit` and `test:e2e` pass.
- Failing tests, QA rejections and PR change requests loop back to the fix step; a passing story
  needs QA approval again after any code change.

## Governance

- This constitution supersedes other practices in this repository; plans MUST include a
  Constitution Check and justify any deviation.
- Changes reach `main` only through pull requests approved by a team lead; nobody approves their own
  pull request.
- Amendments are made by pull request that updates this file and bumps the version using semantic
  versioning: MAJOR for removing or redefining a principle, MINOR for a new principle or materially
  expanded guidance, PATCH for clarifications.
- Reviewers MUST check compliance with these principles on every pull request.

**Version**: 1.0.0 | **Ratified**: 2026-11-27 | **Last Amended**: 2026-11-27
