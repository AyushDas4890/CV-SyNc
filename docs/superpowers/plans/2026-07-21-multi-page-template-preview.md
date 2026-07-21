# Multi-page CV Template Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render every page of each CV template's sample PDF (not just page 1) as static PNGs, and update the template picker UI to show all pages with a page-count badge.

**Architecture:** A new shell script compiles each of the 8 templates in `cv-templates/` and rasterizes every page via `pdftoppm`, writing `<id>.png` (page 1, unchanged name) plus `<id>-p2.png`, `<id>-p3.png`, ... and a `manifest.json` mapping id → page count. `TemplatePage.jsx` fetches the manifest once, shows a page-count badge on grid cards, and stacks all page images (scrollable) in the preview modal. No backend/API changes.

**Tech Stack:** bash, texlive (pdflatex/xelatex), poppler-utils (pdftoppm), React (existing `TemplatePage.jsx`).

**Spec:** `docs/superpowers/specs/2026-07-21-multi-page-template-preview-design.md`

**No automated test framework exists in `frontend/`** (no vitest/jest/testing-library in `package.json`). Adding one is a new dependency, which is out of scope without asking first — verification below is manual (visual + shell output) instead of unit tests.

---

### Task 1: Render script — single template, prove the approach

**Files:**
- Create: `scripts/render-template-previews.sh`

- [ ] **Step 1: Write the script for exactly one template (`jake`) to prove the pdflatex → pdftoppm → rename pipeline works before generalizing**

```bash
#!/usr/bin/env bash
set -euo pipefail

# Renders every page of each CV template's sample .tex as PNGs into
# frontend/public/template-previews/, plus a manifest.json of page counts.
# Requires: pdflatex, xelatex, pdftoppm (poppler-utils) on PATH.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATES_DIR="$ROOT_DIR/cv-templates"
OUT_DIR="$ROOT_DIR/frontend/public/template-previews"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

mkdir -p "$OUT_DIR"

# id:engine:main.tex (relative to cv-templates/<id>/)
TEMPLATES=(
  "jake:pdflatex:main.tex"
)

for entry in "${TEMPLATES[@]}"; do
  id="${entry%%:*}"
  rest="${entry#*:}"
  engine="${rest%%:*}"
  main_tex="${rest#*:}"

  src_dir="$TEMPLATES_DIR/$id"
  job_dir="$WORK_DIR/$id"
  mkdir -p "$job_dir"
  cp -r "$src_dir"/. "$job_dir"/

  echo "== $id ($engine) =="
  (cd "$job_dir" && "$engine" -interaction=nonstopmode -halt-on-error "$main_tex" >/dev/null)

  pdf_name="$(basename "$main_tex" .tex).pdf"
  pdftoppm -png -r 150 "$job_dir/$pdf_name" "$job_dir/page"

  page_count=0
  for f in "$job_dir"/page-*.png; do
    page_count=$((page_count + 1))
  done
  echo "$id: $page_count page(s)"

  # page-1.png -> <id>.png, page-2.png -> <id>-p2.png, ...
  n=1
  for f in $(ls "$job_dir"/page-*.png | sort -V); do
    if [ "$n" -eq 1 ]; then
      cp "$f" "$OUT_DIR/$id.png"
    else
      cp "$f" "$OUT_DIR/$id-p$n.png"
    fi
    n=$((n + 1))
  done
done
```

- [ ] **Step 2: Make executable and run it**

```bash
chmod +x scripts/render-template-previews.sh
./scripts/render-template-previews.sh
```
Expected: prints `== jake (pdflatex) ==` then `jake: 1 page(s)` (Jake's sample is single-page), no errors. `frontend/public/template-previews/jake.png` exists and is unchanged/regenerated.

- [ ] **Step 3: Verify output**

```bash
ls -la frontend/public/template-previews/jake*.png
```
Expected: only `jake.png` (no `jake-p2.png`, since it's 1 page).

- [ ] **Step 4: Commit**

```bash
git add scripts/render-template-previews.sh
git commit -m "feat: add template preview render script (jake only, proves pipeline)"
```

---

### Task 2: Extend script to all 8 templates + manifest.json

**Files:**
- Modify: `scripts/render-template-previews.sh`

- [ ] **Step 1: Replace the `TEMPLATES` array with all 8 entries and add manifest writing**

```bash
TEMPLATES=(
  "jake:pdflatex:main.tex"
  "dphang:pdflatex:resume.tex"
  "anubhav:pdflatex:main.tex"
  "altacv:pdflatex:sample.tex"
  "moderncv:pdflatex:template.tex"
  "plushcv:xelatex:PlushCV.tex"
  "deedy:xelatex:deedy_resume-openfont.tex"
  "awesome-cv:xelatex:resume.tex"
)
```

- [ ] **Step 2: Add manifest accumulation inside the loop and write it after the loop**

Add before the `for entry in` loop:
```bash
MANIFEST_ENTRIES=()
```

Add inside the loop, right after the `echo "$id: $page_count page(s)"` line:
```bash
MANIFEST_ENTRIES+=("  \"$id\": $page_count")
```

Add after the `done` that closes the main loop:
```bash
{
  echo "{"
  ( IFS=$'\n'; echo "${MANIFEST_ENTRIES[*]}" | sed '$!s/$/,/' )
  echo "}"
} > "$OUT_DIR/manifest.json"

echo "Wrote $OUT_DIR/manifest.json"
cat "$OUT_DIR/manifest.json"
```

- [ ] **Step 3: Run full script**

```bash
./scripts/render-template-previews.sh
```
Expected: 8 `== <id> (...) ==` blocks, no compile errors, ends printing valid JSON like:
```json
{
  "jake": 1,
  "dphang": 1,
  "anubhav": 1,
  "altacv": 1,
  "moderncv": 1,
  "plushcv": 1,
  "deedy": 1,
  "awesome-cv": 1
}
```
(Exact page counts depend on each template's actual sample content — this is the real signal for which templates need the badge/scroll UI.)

- [ ] **Step 4: Verify files on disk**

```bash
ls frontend/public/template-previews/
cat frontend/public/template-previews/manifest.json
```
Expected: for any template with `page_count > 1` in the manifest, matching `<id>-p2.png` (and further pages) exist alongside `<id>.png`.

- [ ] **Step 5: Commit**

```bash
git add scripts/render-template-previews.sh frontend/public/template-previews/
git commit -m "feat: render all pages for all 8 CV templates, add manifest.json"
```

---

### Task 3: Frontend — load manifest, add page-count badge to grid cards

**Files:**
- Modify: `frontend/src/pages/TemplatePage.jsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Add manifest state and fetch it on mount**

In `TemplatePage.jsx`, add a new state variable next to the existing ones (after line 24, `const [username, setUsername] = useState("");`):

```jsx
  const [pageCounts, setPageCounts] = useState({}); // { [templateId]: number }
```

Update the existing `useEffect` (currently lines 27-33) to also fetch the manifest, independently of the auth check so a manifest failure never blocks the page:

```jsx
  useEffect(() => {
    // reachable directly by URL, so guard it — bounce to login if no session
    api.me()
      .then((res) => setUsername(res.githubUsername))
      .catch(() => navigate("/auth"));

    // Static asset, not an authenticated call — plain fetch, not api.js.
    // Failure just means every template falls back to page-count 1 (today's behavior).
    fetch("/template-previews/manifest.json")
      .then((res) => (res.ok ? res.json() : {}))
      .then(setPageCounts)
      .catch(() => setPageCounts({}));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
```

- [ ] **Step 2: Add a helper to read page count with fallback, and render the badge on grid cards**

Add near the top of the component body (after the `navigate` line, before `confirmSelection`):

```jsx
  function pageCountFor(id) {
    return pageCounts[id] || 1;
  }
```

Update the grid card block (currently lines 55-67) to add the badge:

```jsx
        {TEMPLATES.map((t) => (
          <div
            key={t.id}
            className={`template-card ${chosen === t.id ? "chosen" : ""}`}
            onClick={() => setPreviewing(t)}
          >
            {chosen === t.id && <span className="chosen-badge">Selected</span>}
            {pageCountFor(t.id) > 1 && (
              <span className="page-count-badge">{pageCountFor(t.id)}p</span>
            )}
            <div className="thumb">
              <img src={`/template-previews/${t.id}.png`} alt={t.name} />
            </div>
            <div className="label">{t.name}</div>
          </div>
        ))}
```

- [ ] **Step 3: Add badge styling to `styles.css`**

Append to `frontend/src/styles.css`:

```css
.page-count-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  background: rgba(0, 0, 0, 0.65);
  color: #fff;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 10px;
  z-index: 1;
}
```

Confirm `.template-card` already has `position: relative` (needed for the badge's `position: absolute` to anchor correctly) — check the existing rule:

```bash
grep -n "template-card" frontend/src/styles.css
```
If `.template-card` has no `position` declared, add `position: relative;` to its existing rule block.

- [ ] **Step 4: Manual verification**

```bash
cd frontend && npm run dev
```
Open the Template page in a browser (after logging in), confirm: templates with `manifest.json` page count 1 show no badge; if any template shows `>1` in the manifest from Task 2, its card shows the `Np` badge in the top-right corner.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/TemplatePage.jsx frontend/src/styles.css
git commit -m "feat: show page-count badge on multi-page template cards"
```

---

### Task 4: Frontend — stack all pages in the modal, scrollable

**Files:**
- Modify: `frontend/src/pages/TemplatePage.jsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Replace the single modal image with a mapped stack of all pages**

Replace the modal body block (currently lines 84-86):

```jsx
            <div className="modal-body">
              <img src={`/template-previews/${previewing.id}.png`} alt={previewing.name} />
            </div>
```

with:

```jsx
            <div className="modal-body modal-body-scroll">
              {Array.from({ length: pageCountFor(previewing.id) }, (_, i) => i + 1).map((page) => (
                <img
                  key={page}
                  src={
                    page === 1
                      ? `/template-previews/${previewing.id}.png`
                      : `/template-previews/${previewing.id}-p${page}.png`
                  }
                  alt={`${previewing.name} page ${page}`}
                  className="modal-page-image"
                />
              ))}
            </div>
```

- [ ] **Step 2: Add scroll + spacing styles to `styles.css`**

Append:

```css
.modal-body-scroll {
  max-height: 70vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.modal-page-image {
  width: 100%;
  display: block;
}
```

- [ ] **Step 3: Manual verification**

```bash
cd frontend && npm run dev
```
Open Template page, click a template whose manifest page count is 1 — modal shows exactly one image, same as before. If any template has page count `>1` (from Task 2's real output), click it and confirm the modal shows all pages stacked, and that the modal scrolls instead of overflowing the viewport when the stack is taller than 70vh.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/TemplatePage.jsx frontend/src/styles.css
git commit -m "feat: show all template pages stacked and scrollable in preview modal"
```

---

## Plan self-review

- **Spec coverage:** render script (Tasks 1-2) ✓, manifest.json (Task 2) ✓, grid badge (Task 3) ✓, modal stacked+scrollable (Task 4) ✓, fallback to page-count 1 on missing/failed manifest (Task 3 Step 1) ✓, plain `fetch()` not `api.js` (Task 3 Step 1, stated explicitly) ✓, naming convention `<id>.png` / `<id>-pN.png` (Task 1-2 script, Task 4 image src logic) ✓. Out-of-scope items (backend, template-select wiring) untouched, as specified.
- **Placeholder scan:** no TBD/TODO; every step has literal code or an exact command with expected output.
- **Type/naming consistency:** `pageCountFor(id)` defined once in Task 3 Step 2, reused unchanged in Task 4 Step 1. `pageCounts` state name consistent across Tasks 3-4. Manifest key naming (`<id>: <count>`) in the script matches the frontend's `pageCounts[id]` lookup.
