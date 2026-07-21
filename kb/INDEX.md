# KB INDEX — CV-Sync / RepoResume project

Compressed knowledge base. Read this file first, then only the file you need.
Style: caveman-compressed. All technical substance intact.

| File | Contains | Read when |
|---|---|---|
| 00-project.md | what project is, current state, team split | always, first |
| 01-architecture.md | 4 services, data flow, contracts | designing/integrating anything |
| 02-auth-service.md | session auth design + fixes applied | working on auth |
| 03-compiler-service.md | teammate's CV_BUILDER repo, API contract, known bugs | calling /api/compile |
| 04-writer-service.md | to-build: tex writer, template, escaping, diff gate | building writer |
| 05-llm-rag.md | fetch+LLM half, RAG design, prompt strategy | building summarizer |
| 06-build-plan.md | phased steps + pass checks | deciding what next |
| 07-decisions.md | locked decisions + open questions | before proposing changes |

Canvas files (visual, in parent folder): session-auth-corrected, project-layout-build-order, document-half-v3 (v1/v2 superseded — NOTE: all document-half canvases show old docx plan, superseded by .tex plan, see 07-decisions).

ui-reference/ — onboarding flow UI, generated via Claude.ai Design (Labs). Static prototype only (CV-Sync Onboarding.dc.html + support.js runtime), NOT wired to any backend, uses Design's own `<x-dc>` rendering engine not plain React. Original mockup showed email/pw + Google auth — SUPERSEDED, real build uses GitHub-only OAuth login (see 07-decisions). Visual/copy reference only for: experience form (skippable), repo picker, CV template gallery (from IamAbhinav01/CV_TEMPLATES, placeholder images pending).

backend/auth-service/ + frontend/ — real, running code (not reference). GitHub OAuth is the login itself. See 06-build-plan "Out-of-order work already done" for what's real vs stubbed, and how to run both together.
