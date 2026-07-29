# CV_BUILDER fixes — pending relay to Abhinav (2026-07-29)

Two commits made in the local `cv_builder_src/` checkout that **could not be
pushed**. `git push origin master` returns:

```
remote: Permission to IamAbhinav01/CV_BUILDER.git denied to AyushDas4890.
fatal: ... The requested URL returned error: 403
```

So Ayush does **not** have push access to CV_BUILDER, contrary to what
00-project.md and INDEX.md previously claimed. Corrected there.

Base: `2e043a6` (`origin/master` as of 2026-07-29).
Result: `853bfe0`, tree `87e01eb`.

## What's here

| File | What |
|---|---|
| `cv_builder-fixes.bundle` | **Preferred.** Both commits as real git objects. |
| `0001-fix-PORT-fallback-...patch` | Fallback: the code fixes only, no normalization. |

## Commit 1 — chore: add .gitattributes and normalize line endings to LF

CV_BUILDER has no `.gitattributes` and `core.autocrlf` is unset, so a Windows
checkout whose editor writes CRLF marked all 66 tracked files modified —
**8260 insertions against 8260 deletions, zero content change** — and the
working tree could never be clean. That churn is also what kept the
`cv_builder_src` gitlink permanently dirty inside CV-SyNc.

`* text=auto` plus explicit `binary` rules for the bundled fonts and images.
Content verified unchanged with `git diff --ignore-cr-at-eol`.

## Commit 2 — fix: PORT fallback, configurable compile timeout, real error logging

Closes every CV_BUILDER item on the 07-decisions relay list except the
`getTemplateConcatenated` question.

- `src/config/server.config.js` — `PORT: process.env.PORT` had no fallback, so
  a bare `npm run dev` without a `.env` bound to `undefined`. Docker sets PORT,
  which is why this only ever bit local runs. → `process.env.PORT || 3000`.
- `src/service/latex.service.js` — `COMPILE_TIMEOUT_MS` was hardcoded 15s while
  the README documented 30s. Now env-configurable, default **60s**. The 15s cap
  was actively harmful: xelatex/fontspec templates (plushcv, deedy, awesome-cv)
  routinely exceed it on a cold run and were SIGKILLed mid-compile, surfacing to
  the caller as an opaque failure rather than a LaTeX error.
- `src/controller/latex.controller.js` — the 422 branch logged the fixed string
  `'invalid respone from controleer'` and discarded the compile log and parsed
  error list it had just built. Now logs both.

## How to apply — bundle (preferred, verified)

Works regardless of platform line-ending settings, because a bundle carries
real git objects rather than patch text.

```bash
git clone https://github.com/IamAbhinav01/CV_BUILDER.git
cd CV_BUILDER
git bundle verify /path/to/cv_builder-fixes.bundle    # expects base 2e043a6
git fetch /path/to/cv_builder-fixes.bundle master:incoming
git merge --ff-only incoming
git push origin master
```

Verified end-to-end: resulting tree hash is exactly `87e01eb`, matching the
local checkout, with a clean working tree.

## How to apply — patch (fallback, code fixes only)

**`--keep-cr` is required.** Without it `git am` fails on CRLF context lines:
`error: patch failed: src/config/server.config.js:3`.

```bash
git am --keep-cr 0001-fix-PORT-fallback-*.patch
```

It prints ~197 whitespace warnings; those are the CRLF line endings, not real
problems, and it completes. This patch deliberately **excludes** the
normalization commit — a normalization diff can never apply cleanly as text,
since its own "before" context is the CRLF it's removing. To get that part,
run it directly instead:

```bash
# after copying in the .gitattributes from the bundle, or writing your own
git add .gitattributes
git add --renormalize .
git commit -m "chore: normalize line endings to LF"
```

## Note on the CV-SyNc gitlink

`cv_builder_src` is tracked as a **gitlink (mode 160000) with no `.gitmodules`**
— a half-configured submodule. With these commits applied locally the gitlink
moves `2e043a6 → 853bfe0`, which is why CV-SyNc shows ` M cv_builder_src`.

That bump is deliberately **not** committed: it would point CV-SyNc at commits
that exist on no remote, breaking any fresh clone. Commit it only once these
land on CV_BUILDER's master.

Still undecided: whether `cv_builder_src` should be a real submodule (add
`.gitmodules`) or be gitignored entirely.

## Also spotted

`app.log` is tracked in CV_BUILDER — a runtime log file that should be
gitignored, not versioned. Left alone; Abhinav's call.
