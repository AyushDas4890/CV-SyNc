# KB INDEX — CV-Sync / RepoResume project

Compressed knowledge base. Read this file first, then only the file you need.
Style: caveman-compressed. All technical substance intact.

| File | Contains | Read when |
|---|---|---|
| 00-project.md | what project is, current state, team split | always, first |
| 01-architecture.md | 4 services, data flow, contracts | designing/integrating anything |
| 02-auth-service.md | auth service DONE: routes, userStore, profile+education storage | working on auth or profile data |
| 03-compiler-service.md | teammate's CV_BUILDER repo, API contract, known bugs | calling /api/compile |
| 04-writer-service.md | to-build: tex writer, template, escaping, diff gate | building writer |
| 05-llm-rag.md | fetch+LLM half, RAG design, prompt strategy | building summarizer |
| 06-build-plan.md | phased steps + pass checks + what's been built | deciding what next |
| 07-decisions.md | locked decisions + open questions | before proposing changes |

Canvas files (visual, in parent folder): session-auth-corrected, project-layout-build-order, document-half-v3 (v1/v2 superseded — NOTE: all document-half canvases show old docx plan, superseded by .tex plan, see 07-decisions).

ui-reference/ — onboarding flow UI, generated via Claude.ai Design (Labs). Static prototype only (CV-Sync Onboarding.dc.html + support.js runtime), NOT wired to any backend, uses Design's own `<x-dc>` rendering engine not plain React. Original mockup showed email/pw + Google auth — SUPERSEDED, real build uses GitHub-only OAuth login (see 07-decisions).

backend/auth-service/ + frontend/ — real, running code (not reference). GitHub OAuth is the login itself. 5-page onboarding: /auth → /onboarding/profile → /onboarding/experience → /onboarding/github → /onboarding/templates. Profile+Education data stored via POST /api/profile (persists to userStore in-memory, mirrors to localStorage). See 06-build-plan for full detail.

cv-templates/ — 8 real CV LaTeX templates (source: AyushDas4890/CV_TEMPLATES, note: correct repo, not the earlier CV-SyNc mixup). Each subfolder = one template's .tex + .cls + required assets only (fonts/images the template actually needs to compile), build artifacts and PDFs stripped. Compile-tested: jake, anubhav, dphang compile with plain pdflatex; altacv, moderncv need pdflatex + lato/roboto CTAN fonts (not bundled here — install separately if recompiling outside this session); plushcv, deedy, awesome-cv need xelatex (fontspec-based) + their own bundled fonts/ dirs (bundled, self-contained). altacv/sample.tex has its Publications section (biblatex-dependent) commented out — needed for the preview render, avoids a heavy bibliography dependency for something that was demo content anyway. frontend/public/template-previews/*.png = real compiled first-page renders of each (not mockups), used directly by TemplatePage's picker + preview modal.
