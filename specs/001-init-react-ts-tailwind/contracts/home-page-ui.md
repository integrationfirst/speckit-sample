# Contract: Home page UI

**Source of authority**: Spec FR-010 to FR-016 and User Story 2; Constitution Principle IV.

This is the externally observable contract that the component test and the e2e test assert. Tests
query by role and text, never by class names or DOM structure.

## Document

- `<html lang="en">`; `<title>` is `speckit-sample`; there is a responsive viewport meta tag.
- The only stylesheet is `src/index.css` (Tailwind entry). There is no inline `<style>` and no other
  CSS file.

## Landmarks and content (accessibility tree)

| Order | Role | Element | Accessible content | Requirement |
|-------|------|---------|--------------------|-------------|
| 1 | `banner` | `<header>` (top-level, not nested in `main`) | Contains the text `speckit-sample` | FR-011, FR-014 |
| 2 | `main` | `<main>` | Contains exactly one `heading` with level 1, plus a short welcome paragraph | FR-012, FR-014 |
| 3 | `contentinfo` | `<footer>` (top-level) | Minimal text, e.g. `© speckit-sample` | FR-013, FR-014 |

- The whole page has exactly **one** level-1 heading. Any later headings must not skip levels.
- The page has no interactive elements. If any are added later, each must be reachable with Tab in
  DOM order and show a visible focus ring (`focus-visible:` utilities).

## Layout

- Mobile-first. At 320 px and 1280 px wide, all three landmarks and the `h1` and welcome text are
  visible, and `document.documentElement.scrollWidth <= window.innerWidth`.
- Text wraps instead of overflowing. At 200% browser zoom, content reflows without clipping.

## Visual accessibility

- Text contrast ≥ 4.5:1 (normal) and ≥ 3:1 (large). Planned palette: `slate-900` and `slate-600` on
  `white`.
- No animations or transitions.
- axe-core scan with tags `wcag2a`, `wcag2aa`, `wcag21a` and `wcag21aa` → 0 violations.
