# Decisions

## LOCKED
- CV format = LaTeX (Jake Gutierrez template). docx/docxtpl plan DEAD (document-half canvases v1-v3 show old plan — historical only)
- SUPERSEDED (2026-07-22, see CV_BRAIN section below): "LLM outputs JSON only; deterministic renderer writes tex" describes the writer-svc design that was never built. What actually exists (CV_BRAIN) has the LLM write the full .tex directly, guarded by a template-registry system prompt + completeness validator + one retry, not a JSON→renderer split.
- Diff + human y/N gate before any CV change. Reject = untouched. Default N — NOT built for the CV_BRAIN path: today "generate" -> "compile" -> download is a straight line, no snapshot/approve step. Flagging as a real gap vs. this locked decision, not closing it.
- Session auth (cookie session_id + Redis), NOT JWT
- Cookie: opaque session_id only, HttpOnly Secure SameSite=Lax
- projects.json = contract between halves; sample committed so doc half runs keyless
- V1 repo input = pasted links + server PAT. OAuth V2. Never user-pasted PATs
- SUPERSEDES 02-auth-service.md's email/password-primary design: GitHub OAuth is the PRIMARY/recommended login, not a separate post-login connect step. REVISED (2026-07-21): unified auth store now also supports email/password (bcrypt) and a Google OAuth path — see below. User identity = one of github_id | google_id | email (in-memory Map placeholder now, MySQL `users` table keyed on all three later). Session still cookie+Redis, unchanged.
- REVISED auth surface (unified, supersedes the "GitHub-only" line above): `userStore.service.js` is now a single in-memory store keyed by `github_id`, `google_id`, and `email`, with `findOrCreateByGithubId`, `findOrCreateByGoogleId`, `createEmailUser`/`verifyEmailUser` (bcryptjs, 12 rounds), and `publicProfile()` stripping secrets before sending to client. AuthPage.jsx shows GitHub as the primary/"Recommended" button, a Google button ("coming soon", not clickable to real flow), and an Email/Password form (login/register tabs) wired to `POST /api/auth/email/register` and `/email/login`.
- Google OAuth backend code exists (`googleAuth.controller.js`, `googleAuth.service.js`, `config/env.js` google section) but its routes are NOT mounted in `githubAuth.routes.js` — intentionally inert, matches frontend's "coming soon" stub. Not a bug if found unmounted.
- Logout: `POST /api/auth/logout` destroys session + clears cookie. Frontend `LogoutBar` component (used on Experience + Template pages) calls it then redirects to `/auth`.
- Microservices, Node/Express, MVC layout matching teammate's repo
- RAG: stuff small corpora (macros, ATS rules); retrieve only exemplars + JD
- Compile errors (422) route to renderer/dev, never fed to LLM

## OPEN (ask Ayush before assuming)
- images in CV vs ATS: conflict named, unresolved. Options: ATS-only | two templates
- writer svc language Node vs Python: Node assumed, unconfirmed
- writer svc repo: separate | inside CV_BUILDER | monorepo — unconfirmed
- auth = standalone learning project vs integrated backend: integrated assumed
- Overleaf-style live editor UI: mentioned by teammate ("later for live rendering"), scope unclear
- RESOLVED (2026-07-22): template selection now drives the actual pipeline — TemplatePage's CTA calls CV_BRAIN's `/api/generate-cv`, then ResultPage compiles via CV_BUILDER's `/api/compile`. See CV_BRAIN section below for full wiring.
- Whether/when to actually finish the Google OAuth login path (code exists, unmounted)
- Template preview images only render page 1 of each template's compiled sample content (`pdftoppm -f 1 -l 1`). Fine for now since these are style-preview thumbnails of placeholder content, not the user's real (eventually multi-page) resume — but if a template's sample spans >1 page, pages 2+ are invisible in both the grid thumbnail and the click-to-preview modal (same PNG reused for both). Not yet decided whether to fix (render+page through all pages, or add a page-count badge).

## LOCKED (2026-07-22 addition)
- Frontend template short ids (jake/dphang/anubhav/altacv/plushcv/deedy/awesome-cv) != CV_BRAIN's TEMPLATE_REGISTRY keys (Jake_s_Resume__3_ etc). Mapping now lives in `frontend/src/pages/TemplatePage.jsx` as `TEMPLATES[].brainId`, with `brainIdFor(shortId)`/`shortIdFor(brainId)` exported helpers. Any code calling CV_BRAIN's `/api/generate-cv` must send `brainId`, not the short `id`. Note: CV_BRAIN registry also has `ModernCV_and_Cover_Letter_Template__2_` with no frontend card/thumbnail yet.

## CV_BRAIN end-to-end wiring (2026-07-22)
Full path now works: Profile/Experience/GitHub/Template pages -> `frontend/src/api.js` `generateCv()` -> CV_BRAIN `/api/generate-cv` -> ResultPage `compile()` -> CV_BUILDER `/api/compile` -> PDF download.
- `frontend/src/api.js`: `buildGenerateCvPayload()` maps the 4 onboarding localStorage caches (`cv_sync_student_profile`, `cv_sync_experience`, `cv_sync_selected_repos`, `cv_sync_template`) into CV_BRAIN's `GenerateCvRequest`. Now async — it calls the new backend README-fetch endpoint for each selected repo first (best-effort: Promise.allSettled, a failed fetch just becomes `readme_content: ""`, doesn't block generation).
- Backend (`backend/auth-service`): new `GET /api/auth/github/repos/:owner/:repo/readme` (session-guarded, uses stored GitHub token). `fetchUserRepos` now also returns `topics`.
- CV_BRAIN itself needed 2 patches — CV_BRAIN is not in this repo/session, so these are staged as ready-to-apply files rather than committed: `kb/relay/cv_brain-achievements-patch/` (README there has full detail). Patch 1: added `achievements` field to `UserProfile` (frontend was collecting achievements with nowhere honest to send them — was almost mangled into `certifications`, added a real field instead). Patch 2: switched `call_llm()` to try OpenAI before Groq (Ayush: "use openai api for now"), and fixed `_call_openai()`'s import — it was pulling `ChatOpenAI` from `langchain_community.chat_models`, a package not even in `pyproject.toml`, so the "fallback" would have thrown `ImportError` the one time it was needed. Fixed to `langchain_openai`, added as a real dependency in `pyproject.toml`.
- `frontend/src/api.js` also gained `compileCv()` (posts to CV_BUILDER's `/api/compile`, handles the binary-PDF-or-JSON-error response shape) and ResultPage now has a "Compile to PDF" button with inline PDF preview/download, plus 422 log/error display.
- Still not built: the diff/approve gate (see LOCKED section above — flagged as a real gap, not silently dropped) and any UI for `target_role`/`target_pages` (both default `""`/`1` in the payload — no form field collects them yet).

## TEAMMATE RELAY (pending)
- CV_BUILDER: timeout code 15s vs README 30s
- CV_BUILDER: PORT no fallback in server.config.js
- CV_BUILDER: `getTemplateConcatenated` picks a `sample.tex`/`main.tex`/etc as the "main" file per template — confirm this always matches what CV_BRAIN's `TEMPLATE_REGISTRY` assumes for each of the 8 templates (not verified against a live server in this session, only read statically).
- CV_BRAIN: apply the 2 patches in `kb/relay/cv_brain-achievements-patch/` and run `uv sync` (new `langchain-openai` dependency).
