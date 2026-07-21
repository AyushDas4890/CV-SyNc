# Multi-page CV template preview — design

## Problem

`frontend/public/template-previews/<id>.png` is a single PNG per template, rendered via `pdftoppm -f 1 -l 1` (page 1 only). If a template's sample content spans more than one page, pages 2+ are invisible in both the grid thumbnail and the click-to-preview modal — user picks a template blind to its full layout. Flagged as an open item in `kb/07-decisions.md`.

## Decision

Render all pages per template, pre-generated as static files (not on-demand server rendering — no new backend service needed, matches the existing static-PNG pattern). Modal shows all pages stacked, scrollable. Grid card gets a small page-count badge.

## Components

### 1. Render script (new): `scripts/render-template-previews.sh`

- For each `cv-templates/<id>/`, compile with the correct engine (xelatex for `deedy`, `plushcv`, `awesome-cv` — fontspec-based; pdflatex otherwise), per the compile notes in `kb/06-build-plan.md`.
- `pdftoppm -png -r 150` with **no** `-f`/`-l` limit — renders every page.
- Output naming: page 1 → `<id>.png` (unchanged, preserves existing references), page 2 → `<id>-p2.png`, page 3 → `<id>-p3.png`, etc.
- Also emit `frontend/public/template-previews/manifest.json`: `{ "<id>": <pageCount>, ... }` for all 8 templates.
- This script does not exist today — the current 8 PNGs were produced by hand-run commands in a prior sandbox session (per KB history). Committing the script closes that gap so re-rendering isn't tribal knowledge.

### 2. Frontend: `frontend/src/pages/TemplatePage.jsx`

- On mount, alongside the existing `api.me()` call, `fetch("/template-previews/manifest.json")` once, store result in state as `{id: pageCount}`.
- **Fallback:** if the manifest fails to load, or a given template id is absent from it, treat `pageCount` as `1` — falls back to exactly today's single-image behavior. No hard failure, no loading spinner gating the page.
- **Grid card:** unchanged `<img src="/template-previews/<id>.png">`. Add a small corner badge (e.g. `3p`) only when `pageCount > 1`. No badge for single-page templates.
- **Modal body:** replace the single `<img>` with a map over `1..pageCount`, rendering `<id>.png`, `<id>-p2.png`, ... stacked vertically, each full width. `modal-box` gets a `max-height` + `overflow-y: auto` so long stacks scroll instead of overflowing the viewport.
- Manifest fetch uses plain `fetch()`, not the `api.js` wrapper — this is a static public asset, not an authenticated backend call, so the session-cookie machinery in `api.js` is unnecessary indirection.

## Out of scope

- No backend/API changes — writer service and template selection wiring (07-decisions OPEN item: "what happens after template select") are untouched by this.
- No change to which templates need which engine — that's existing compile knowledge in `06-build-plan.md`, the script just applies it without the `-f 1 -l 1` restriction.

## Self-review

- Placeholders: none — every piece (script, naming, manifest, fallback, UI) is fully specified.
- Consistency: naming scheme (`<id>.png` = page 1) matches current `TemplatePage.jsx` references exactly, so no code path breaks for the 1-page templates.
- Scope: single feature, one script + one component change — no decomposition needed.
- Ambiguity: page-count badge threshold (`>1`) and fallback value (`1`) stated explicitly to avoid a second reading.
