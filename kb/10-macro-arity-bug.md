# Macro arity bug + template-wide audit (2026-07-29)

## The failure

Compile died on the Anubhav template:

```
./doc.tex:124: Missing number, treated as zero.
<to be read again> \relax
l.124     \resumeItem{Project Overview}
==> Fatal error occurred, no output PDF file produced!
```

## Root cause: the registry lied to the LLM

Anubhav defines:

```latex
\newcommand{\resumeItem}[2]{ \item\small{ \textbf{#1}{: #2 \vspace{-2pt}} } }
```

**Two mandatory arguments.** `template_registry.py` documented it as
`\resumeItem[Label]{Description}` — an *optional* bracket label plus one
mandatory arg. The LLM followed the documentation and emitted one-argument
calls. TeX then scanned forward for the missing `#2`, swallowed the following
tokens, and `\vspace{-2pt}` ended up with no number.

The error message names `\resumeItem` and says "Missing number", which points
at neither the missing argument nor the macro's arity. Easy to misread as a
`\vspace` problem.

Contributing factor: system-prompt rules 11a/11b (added earlier the same day)
hardcoded a **one-argument** `\resumeItem` in their tech-stack example, which
is Jake-specific. Now written per-arity.

## Diagnosis tell

`LaTeX Warning: Unused global option(s): [20pt].` — only
`Resume_Template_by_Anubhav__2_` uses `\documentclass[a4paper,20pt]{article}`
(article supports 10/11/12pt only). That identified the template immediately;
the reported failure was **not** Jake's.

## Full audit of all 8 templates

Ground truth was extracted by parsing `\newcommand`/`\renewcommand` from every
`.tex`/`.cls`, then diffed against every registry claim.

**Genuine bugs found (3):**

| Template | Registry claimed | Actual | Consequence |
|---|---|---|---|
| Anubhav | `\resumeItem[Label]{Description}` | **2 mandatory** | the reported fatal error |
| PlushCV | `\skills{\skillEntry{...}{...}}` | **does not exist anywhere** | "Undefined control sequence" |
| AltaCV | `\wheelchart{...}` (1 arg) | **4 args** (1 optional) | fatal if emitted |

All three fixed. PlushCV's skills entry now points at a plain `tightemize`
list; `\wheelchart` is marked DO-NOT-USE (decorative, worthless for ATS).

**False positives** (registry was right, naive checker wrong): optional-first
macros (`\cvsection[2][]`, `\makecvheader[1][C]`), nested braces in examples
(`\resumeProjectHeading`), and class-provided commands (`\section`, `\begin`,
all moderncv macros). Worth knowing before "fixing" them.

## The permanent fix: runtime arity validation

Registry docs drift. `app/service/macro_validator.py` parses arity **from the
template source at request time** — the template is the ground truth, not the
documentation.

- `extract_macro_arity(template_tex)` → `{macro: (nargs, first_is_optional)}`.
  With `[n][default]`, mandatory count is `n-1`.
- `check_macro_calls(tex, arity)` → calls supplying too few `{...}` groups.
  Brace-matched (handles nesting and `\{`), multi-line aware, skips definition
  sites and commented-out lines.
- `describe_macro_signatures(arity)` → injected into the system prompt under
  **"EXACT MACRO SIGNATURES — AUTHORITATIVE"**, explicitly overriding the
  registry text.

Wired in as **Step 8b**, before the compile: wrong arity is always fatal, so
catching it deterministically is cheaper and clearer than paying for a compile
round-trip. Up to 2 bounded repair attempts; anything left becomes a `warnings`
entry rather than a hard failure.

## Verified

- **Self-test: all 8 templates validate their own sample content with ZERO
  false positives.** If the checker flagged a template's own valid usage it
  would be wrong — including Anubhav's genuine two-argument call split across
  two lines.
- Reproduces the exact reported failure: flags
  `line 5: \resumeItem needs 2 argument(s) but only 1 was/were supplied`,
  while correctly ignoring the valid 2-arg call and 0-arg list macros.
- Repair loop fixes it in one pass; the stubborn case stops after 2 attempts
  and reports.
- Registry now has **0** undefined-macro claims across all templates.
- Page-metric and structure-review tests still pass.

**Still not verified:** a real compile. There is no TeX in this session, so
this is validated by parsing, not by pdflatex. Run one real generation per
template to confirm.

---

# Sanitizer bugs found by compiling for real (2026-07-29, second failure)

Reported: `./doc.tex:122: Misplaced alignment tab character &.` on
`\resumeItem{Interview Prep.}{... 730+ Q&A boxes ...}`.

Compiling the templates through the sanitizer for real (TeX Live is available
in the dev sandbox) exposed **three** bugs, only one of which was the reported
symptom. All are fixed and verified by actual `latexmk` runs.

## Bug 1 — specials inside macro arguments were never escaped

Escaping was done line by line and skipped any line starting with a known TeX
command. Since essentially every content line starts with `\resumeItem`,
`\cvitem` and friends, `&` and `_` inside macro **arguments** were never
touched. That is how "Q&A" reached the compiler.

Replaced with `escape_body_specials()`, which walks the body and understands
where these characters are legitimate:
  - math mode (`$...$`) — `_` is a subscript
  - alignment environments (tabular, array, align, …) — `&` is a column tab
  - URL arguments of `\href` / `\url` — must keep raw `&` and `_`
  - comments, and already-escaped `\&` / `\_`

## Bug 2 — `fix_href_extra_braces` corrupted balanced input (FATAL)

It removed any `}` following a `\href{...}{...}`, assuming it was a stray. But
in `\namesection{A}{B}{\href{url}{Label}}` that brace closes the **enclosing**
group. Deedy and PlushCV both died with
`File ended while scanning use of \namesection`.

Now guarded: it only acts when the line genuinely has more `}` than `{`.

## Bug 3 — `drop_itemless_itemize` emptied preamble macro definitions

Its `DOTALL` match ran from the `\begin{itemize}` inside
`\newcommand{\resumeSubHeadingListStart}{...}` to the `\end{itemize}` inside
`\newcommand{\resumeSubHeadingListEnd}{...}`, deleting both bodies and
producing `Lonely \item`. Only the later `replace_preamble_with_original()`
call was hiding the damage. Now refuses to span a macro definition.

## Verified with real compiles

Before: running the sanitizer over each template's own source produced **0 of 4
compilable**. After: **4 of 4**, both through the sanitizer alone and through
the full production path (`sanitize` + `replace_preamble_with_original`).

The reported failing document — unescaped `&` in a macro argument, plus the
label-colon and arity mistakes — now compiles to 1 page with `Q&A` and `R&D`
rendered correctly and no doubled colon.

---

# The arity gate had a hole (2026-07-29, third failure)

The same "Missing number, treated as zero" on Anubhav came back **after** the
arity gate was added. The gate itself was fine; the pipeline order was not.

```
step 8b  arity gate            <- fixes wrong-arity calls
step 9   structure review/repair  <- LLM rewrites the WHOLE document
step 10  page fit                 <- LLM rewrites the WHOLE document, up to 3x
         (nothing re-checked arity afterwards)
```

Both later steps hand the entire document back to the model. A condense pass
rewriting every bullet can trivially drop a second argument, and the result
went straight to the compiler unchecked.

Fixes:
- **Page-fit adjustments are validated.** If an adjustment introduces a bad
  call, it is repaired; if it is still broken, the adjustment is **discarded**
  and the loop stops. A correctly-sized document that doesn't compile is worth
  less than a slightly mis-sized one that does.
- **Final arity gate (step 11)** after all LLM rewrites — the last thing to
  touch the tex before it is returned.

Verified by driving the full pipeline with a page-fit pass that deliberately
returns a one-argument `\resumeItem` on every call: no wrong-arity call escapes.

## Checking WHICH build is running

`GET /health` now reports it:

```json
{"build": "2026-07-29-arity-gate-v2",
 "features": {"macro_arity_gate": true, "macro_arity_final_gate": true,
              "page_fit": true, "page_bands": [1.0, 2.0]}}
```

If a fix appears not to have taken effect, check this first — a stale container
or an unrestarted `uvicorn` looks exactly like a failed fix. The ResultPage also
now shows measured page length, which is absent on older frontend builds.

## If a compile fails again

1. Check `LaTeX Warning: Unused global option(s)` — identifies the template.
2. The reported line number is where TeX *noticed*, not necessarily the fault.
3. `Missing number, treated as zero` after a custom macro almost always means
   too few arguments, not a `\vspace` problem.
4. Diff registry claims against `extract_macro_arity()` output for that
   template.
