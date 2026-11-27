# Data Model: Initialize Project with React, TypeScript and Tailwind CSS

**Feature**: `001-init-react-ts-tailwind` | **Date**: 2026-11-27

## Entities

None. Per the spec ("Key Entities: Not applicable"), this feature does not create, store, fetch or
exchange any data. There is no state, persistence or API (FR-018).

## Static content

The home page renders fixed copy. It is defined inline in the components and is not modelled as data:

| Item | Location | Value / rule |
|------|----------|--------------|
| App name | `SiteHeader` (also the document `<title>`) | `speckit-sample` (FR-011) |
| Top-level heading | `App` → `<main>` | Exactly one `h1`, e.g. "Welcome to speckit-sample" (FR-012) |
| Welcome message | `App` → `<main>` | One short sentence saying that the app is the foundation for upcoming features. The wording is not a requirement |
| Footer line | `SiteFooter` | Minimal, e.g. "© speckit-sample". No links |

## State transitions

None. The page has no interactive elements and no component state.
