# KB INDEX — CV-Sync / RepoResume project

Compressed knowledge base. Read this file first, then only the file you need.
Style: caveman-compressed. All technical substance intact.

| File | Contains | Read when |
|---|---|---|
| 00-project.md | what project is, current state, team split | always, first |
| 01-architecture.md | ACTUAL 3-service architecture (shipped) + original 4-service design (superseded, kept for history) | designing/integrating anything |
| 02-auth-service.md | auth service DONE: routes, userStore, profile+education storage, repo README fetch | working on auth or profile data |
| 03-compiler-service.md | teammate's CV_BUILDER repo, API contract, known bugs | calling /api/compile |
| 04-writer-service.md | historical: original tex-writer/diff-gate design, NEVER BUILT — superseded by CV_BRAIN (see 07-decisions) | understanding what was originally planned |
| 05-llm-rag.md | historical: original standalone fetch+LLM/RAG design — superseded by CV_BRAIN, which does this differently | understanding what was originally planned |
| 06-build-plan.md | phased steps + pass checks + what's been built | deciding what next |
| 07-decisions.md | locked decisions + open questions + CV_BRAIN wiring notes | before proposing changes |

Canvas files (visual, in parent folder): session-auth-corrected, project-layout-build-order, document-half-v3 (v1/v2 superseded — NOTE: all document-half canvases show old docx plan, superseded by .tex plan, see 07-decisions).

ui-reference/ — onboarding flow UI, generated via Claude.ai Design (Labs). Static prototype only (CV-Sync Onboarding.dc.html + support.js runtime), NOT wired to any backend, uses Design's own `<x-dc>` rendering engine not plain React. Original mockup showed email/pw + Google auth — SUPERSEDED, real build uses GitHub-only OAuth login (see 07-decisions).

backend/auth-service/ + frontend/ + CV_BRAIN/ — real, running code (not reference), all three now live together in this repo. GitHub OAuth is the login itself. 5-page onboarding: /auth → /onboarding/profile → /onboarding/experience → /onboarding/github → /onboarding/templates → /onboarding/result. Profile+Education data stored via POST /api/profile (persists to userStore in-memory, mirrors to localStorage). See 06-build-plan for full detail.

CV_BRAIN/ — Python/FastAPI LLM generation service, vendored in 2026-07-22 from github.com/IamAbhinav01/CV_BRAIN (still the canonical upstream — Ayush has push access, commit f5e3417 there matches what's here). Fetches template tex from CV_BUILDER, fills it via LLM (OpenAI first, Groq fallback), validates completeness, retries once. See 01-architecture.md and 07-decisions.md for the full wiring — this is NOT the projects.json/writer-svc design in 04/05, it's a different, already-working approach. CV_BUILDER itself (the compiler, Abhinav's) is still NOT vendored here — only referenced by URL/port.

cv-templates/ — 7 real CV LaTeX templates (source: AyushDas4890/CV_TEMPLATES, note: correct repo, not the earlier CV-SyNc mixup). Each subfolder = one template's .tex + .cls + required assets only (fonts/images the template actually needs to compile), build artifacts and PDFs stripped. Compile-tested: jake, anubhav, dphang compile with plain pdflatex; altacv needs pdflatex + lato/roboto CTAN fonts (not bundled here — install separately if recompiling outside this session); plushcv, deedy, awesome-cv need xelatex (fontspec-based) + their own bundled fonts/ dirs (bundled, self-contained). altacv/sample.tex has its Publications section (biblatex-dependent) commented out — needed for the preview render, avoids a heavy bibliography dependency for something that was demo content anyway. frontend/public/template-previews/*.png = real compiled first-page renders of each (not mockups), used directly by TemplatePage's picker + preview modal.
