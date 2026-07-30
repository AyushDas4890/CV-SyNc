# Per-template compile failures + the undefined-macro gate (2026-07-30)

Reported: Jake, Anubhav and Deedy generate fine; **every other template errors**.
Reproduced against the running stack, root-caused, fixed, re-verified.

## Method — and the one thing worth copying

The stack was already up (`docker compose ps`), so failures were reproduced for
real instead of reasoned about. The decisive step was **bisecting the pipeline
before spending a single LLM call**:

| Stage | What was compiled | Result |
|---|---|---|
| baseline | each template's own pristine `.tex` | **8/8 compiled** |
| A | concatenated tex from `/api/templates/:id/full` | 8/8 |
| B | A + `sanitize_generated_tex` | 7/8 (AltaCV broke) |
| C | B + `replace_preamble_with_original` (production path) | 8/8 |

That killed the obvious hypotheses immediately: the TeX image, the engine
selection, the bundled fonts and the template assets are all **fine**. Whatever
was wrong had to be in the LLM stage. Only then were real generations run.

`kb/10` said "still not verified: a real compile. There is no TeX in this
session." There is now — the `cvsync-cv-builder-1` container. Use it.

## The failures

Five templates, four distinct root causes. None of them was the compiler.

### 1. `\resumeItem` leaked into AltaCV and PlushCV — `Undefined control sequence`

```
doc.tex:147: Undefined control sequence.
\item \resumeItem{Tech Stack}{Python, FastAPI, Express, LaTeX}
```

**The prompt was the bug.** System-prompt rules 11a/11b spelled their
tech-stack example literally as `\resumeItem{...}`, a macro defined ONLY in
Jake's and Anubhav's templates. The model copied the example verbatim into
templates whose bullet is plain `\item`.

Same failure mode as the arity bug in `kb/10`, one level up: there, the
*registry* lied about a macro; here, the *rule text* hardcoded a macro name.
Any example in a shared prompt is read as an instruction.

Fixed: `_tech_stack_rule()` now describes the bullet macro by shape (plain
`\item` / 1-arg / 2-arg) and never names one. Rule 2 additionally spells out
that resume macro names are not portable between templates. The arity-repair
prompt in `review_prompts.py` had the same literal and was neutralised too.

### 2. dphang has no hyperref — `\href` is undefined

```
doc.tex:52: Undefined control sequence.
l.52 ...\faGithubSquare} \ \ \href
```

The reported line number pointed at `\faGithubSquare`; the actual undefined
token was the **`\href` that follows it** (TeX prints what it has read, then
what it has not). dphang's preamble loads geometry, lato, fontawesome5 and
enumitem — no hyperref. It is the only template of the eight without it.

The model could not have fixed this itself: **step 8 restores the original
preamble**, so any `\usepackage{hyperref}` it added would be discarded and only
the broken `\href` calls would survive. Prompting alone is not enough here.

Fixed three ways: `supports_hyperlinks` in the registry (dphang `False`), the
registry's own dphang `header_pattern` no longer uses `\href` (it did — the
registry was instructing the failure), and `strip_hyperlinks()` deterministically
flattens `\href{url}{label}` → `label` inside `_finalize`, the choke point every
repair path funnels through.

### 3. Anubhav — `Lonely \item`, and a content-destroying macro

```
doc.tex:98: LaTeX Error: Lonely \item--perhaps a missing list environment.
\resumeItemWithoutTitle{Backend-leaning full-stack developer...}
```

`\resumeItemWithoutTitle` is defined by the template, never used by it, and its
body is `\item\small{ {\vspace{-2pt}} }` — **argument #1 is discarded**, so the
text passed to it vanishes even when it does compile. It also expands to
`\item`, so calling it outside a list is fatal.

Invisible to both existing gates: the macro *is* defined (undefined gate can't
see it) and the argument count *is* right (arity gate can't see it). What was
wrong was the **context**. Marked DO-NOT-USE in the registry, plus a new gate
(below).

### 4. Anubhav — `\resumeSubheading` called with 2 of 4 arguments

Intermittent, and the more interesting failure: the gate **caught** it and the
LLM repair loop **could not fix it** across both attempts.

Cause: Anubhav's Projects section uses `\resumeSubItem{Name (Tech)}{Description}`
— which was **not listed in the registry at all**. With no project macro
offered, the model reached for the 4-argument `\resumeSubheading` and supplied
two. Compounding it, rule 11a demands 3+ bullets per project, which Anubhav's
single-entry project pattern cannot express, so the model improvised.

Fixed by removing the ambiguity rather than by better repair: `\resumeSubItem`
is now in `available_macros`, the notes state that this template has no project
heading macro, and rules 11a/11b now defer to a template whose Projects section
is single-entry. 3/3 consecutive Anubhav runs clean afterwards.

### 5. ModernCV — hallucinated sections, 2 pages

Compiled, so it never surfaced as an "error", but it invented
`Languages: English (Fluent), Hindi (Fluent)` and `Interests: Hiking, Reading`
from the template's demo sections — data the user never supplied. That is a
zero-hallucination violation that also pushed the CV onto a second page.

Rule 17 covered placeholder *names* ('Jake Ryan'); nothing covered placeholder
*sections*. New rule 18 requires deleting them outright, and the ModernCV
registry notes list them by name (Languages, Interests, Extra 1/2/3, the
`\subsection{Vocational}` heading and the whole post-`\clearpage` cover letter).

### 6. Sanitizer sliced at a commented-out `\documentclass` (AltaCV)

`sanitize_generated_tex` step 1b cut the document at `tex.find(r'\documentclass')`.
AltaCV's sample opens with a commented alternative:

```latex
% \documentclass[10pt,a4paper,withhyper,normalphoto]{altacv}
\documentclass[10pt,a4paper,withhyper]{altacv}
```

The cut landed *after* the `% `, promoting the comment to live code →
`LaTeX Error: Two \documentclass or \documentstyle commands.` Only the later
preamble swap was hiding it. Now uses `_first_uncommented()`.

## The permanent fixes: two new deterministic gates

Same principle as the arity gate — **the template is the ground truth, at
request time** — and both run at all three checkpoints (step 8b, the page-fit
re-check, and the final step 11 gate).

### `check_undefined_macros()`

Allowed-set = macros the template **defines** ∪ macros the template **uses**
∪ the registry's documented macros ∪ a LaTeX kernel whitelist.

The "uses" term is what makes it work without reading the `.cls`: CV_BUILDER's
template endpoints only return `.tex`, but the sample **compiles**, so every
control sequence it invokes demonstrably resolves. That covers class-provided
macros like AltaCV's `\cvevent` and Deedy's `\runsubsection` for free.

### `check_lonely_items()`

Classifies each template macro from its definition body into openers (body
opens a list), closers, and item emitters (body contains a bare `\item`), then
walks the document tracking list depth. An emitter at depth 0 is fatal.

### Both were self-tested for false positives first

Every template validated against its **own** source must be clean — if a gate
flags a template's own valid usage, the gate is wrong. **0 false positives
across all 8, for both gates**, while catching each reproduced failure at the
exact line. Run that check before trusting either.

## Verified

- **8/8 templates generate and compile.** Previously 3/8.
- Anubhav 3/3 consecutive clean runs (it was the flaky one).
- Real `latexmk` compiles through the live stack, not parsing.

## Still open

- **ModernCV lands ~1.06–1.21 pages** against a 1-page target — compiles, but
  spills a few lines onto page 2 and page-fit gives up after 3 attempts. It
  reports this honestly in `warnings`. AltaCV missed the band once (2.0) in one
  run. Page fitting is the weakest remaining link; compiling is no longer.
- Generation is stochastic: **a single green run is not proof**. Both the
  Anubhav failures appeared only on a second or later run. Re-run a template a
  few times before calling it fixed.

## Checking which build is running

```
GET :8000/health → "build": "2026-07-30-undefined-macro-gate-v6"
  features: undefined_macro_gate, lonely_item_gate, hyperlink_capability_strip
```

CV_BRAIN has **no source volume mount** — the code is baked into the image. A
`docker compose restart` silently keeps running the old code; you need
`docker compose build cv-brain && docker compose up -d --force-recreate cv-brain`,
then confirm the build string changed. Note that `docker.io` is intermittently
unreachable here (`502 Too many open files` resolving `python:3.11-slim`) — the
build simply fails and leaves the old container running. Retrying usually works;
always re-check `/health` rather than assuming the rebuild took.
