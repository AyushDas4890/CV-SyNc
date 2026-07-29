# Page fitting + structure review (2026-07-29)

Two refinement passes added to CV_BRAIN after generation:

1. **Structure review** — an LLM audits the generated .tex against the template.
2. **Page fitting** — compile, measure, expand/condense until the CV lands on
   1, 1.5 or 2 pages.

## Why page count needs a compile loop

Page count is **not knowable before compiling**. The old approach was Rule 10 in
the system prompt ("the output MUST fill N full pages") — a hope, with nothing
measuring the result. An LLM cannot predict how many pages its LaTeX will
occupy, so prompting alone can't enforce a page budget.

## What "1.5 pages" means

A PDF has an **integer** page count, so 1.5 can't be read off it directly. What
it means in practice is *two pages, the second about half full*. So the
measurement is two numbers:

```
length = (pages - 1) + fill_ratio
```

`fill_ratio` = how much of the LAST page carries content, derived from the
lowest text baseline on that page relative to its usable height (assuming a
symmetric margin, capped at 1 inch).

Bands: **1.0, 1.5, 2.0**, tolerance **±0.12 page** (~5 lines of text).

`EXPECTED_PAGES = {1.0: 1, 1.5: 2, 2.0: 2}` is enforced separately from the
length. This matters: two pages with a three-line orphan second page measures
~1.05 and would otherwise pass as a tidy "1 page". It's rejected. That bug was
caught by the unit tests, not by reading the code.

## Flow

```
generate → validate (existing) → structure review → repair if fatal/major
        → compile → measure → expand/condense → repeat (bounded) → return
```

`target_pages` in the request: `"auto"` (default), `1`, `1.5`, or `2`.
Anything else is a 422. **"auto"** picks whichever band the first compile lands
nearest, then **locks it** — otherwise the loop chases a moving target,
condensing toward 1.0 then expanding back toward 1.5.

## Files

| File | Role |
|---|---|
| `app/service/page_metrics.py` | measure PDF, classify into bands, decide expand/condense |
| `app/service/compile_client.py` | POST tex to CV_BUILDER, return PDF + X-Page-Count |
| `app/service/structure_reviewer.py` | parse the LLM audit into a usable verdict |
| `app/prompts/review_prompts.py` | audit / repair / page-fit prompts |
| `app/service/latex_generator_services.py` | `run_structure_review`, `apply_structure_repair`, `fit_to_page_target`, wired into `generate_cv` |

CV_BUILDER side: `X-Page-Count` header from the latexmk log (relay commit 3).

## Config (all env vars)

| Var | Default | Meaning |
|---|---|---|
| `ENABLE_STRUCTURE_REVIEW` | `true` | LLM structure audit on/off |
| `ENABLE_PAGE_FIT` | `true` | compile-measure-adjust loop on/off |
| `PAGE_FIT_MAX_ATTEMPTS` | `3` | each attempt = 1 LLM call + 1 compile |
| `PAGE_FIT_COMPILE_TIMEOUT` | `120` | seconds per measurement compile |

## Cost / latency — READ THIS

`/api/generate-cv` is now **much slower**. Worst case per request:
1 generation + 1 validation retry + 1 review + 1 repair + 3 page-fit calls
= **up to 7 LLM calls and 3 compiles**. Typical case is 2-3 calls.

The measurement compiles are *in addition to* the frontend's own compile for
the user's PDF. Set `ENABLE_PAGE_FIT=false` to get the old fast behaviour.

## Degradation — never blocks a CV

Every failure path returns the best available document plus a `warnings` entry:
- CV_BUILDER unreachable or returns 422 → page fitting skipped
- `pypdf` missing → falls back to X-Page-Count, assumes a full last page
- PDF unparseable → falls back to the header hint
- LLM adjustment returns invalid LaTeX → stop, keep the last good version
- target never hit within the attempt budget → closest attempt + warning

The structure review is advisory: an unparseable review is treated as
"no opinion", never as a failure. The reviewer also **overrides the model's own
`structure_ok`** when the issue list contains a fatal/major entry — models do
report `structure_ok: true` while listing fatal problems.

## New dependency

`pypdf>=5.1.0` — pure Python, read-only. Required for fill-ratio measurement;
without it 1.5-page detection is impossible (page count alone can't distinguish
"2 full pages" from "1 page plus 3 orphan lines").

## Verified

- Band classification across 12 length/target combinations.
- Fill ratio against generated PDFs of known extent: sparse 1pg → 0.20, full
  1pg → 0.99, 2pg half → 1.45 (**1.5 band**), 2pg full → 1.96 (**2.0 band**).
- Orphan/overflow rejection: 2pg-stub, 3pg, 3pg-stub, 4pg all → `condense`.
- Loop convergence: 3 pages → condense → 1.96 → accepted, target locked.
- All degradation paths above.
- Review parsing: clean JSON, markdown-fenced, prose-wrapped, contradictory,
  garbage, empty.
- `target_pages` validation live: `auto`/`1`/`1.5`/`2`/`"1.5"` accepted;
  `3`/`1.7`/`"banana"` → 422.
- Full `generate_cv` orchestration with stubbed LLM + compiler.

**Not verified**: a real end-to-end run against live LLM APIs and a real
LaTeX compile — no API keys and no TeX install in this session. The tuning
constants (`BAND_TOLERANCE`, the margin assumption, `LINES_PER_PAGE = 45` used
to convert a page delta into a line budget) are reasoned estimates and may need
adjusting against real compiled output.
