# Decisions

## LOCKED
- CV format = LaTeX (Jake Gutierrez template). docx/docxtpl plan DEAD (document-half canvases v1-v3 show old plan — historical only)
- LLM outputs JSON only; deterministic renderer writes tex. Never LLM → raw LaTeX into CV
- Diff + human y/N gate before any CV change. Reject = untouched. Default N
- Session auth (cookie session_id + Redis), NOT JWT
- Cookie: opaque session_id only, HttpOnly Secure SameSite=Lax
- projects.json = contract between halves; sample committed so doc half runs keyless
- V1 repo input = pasted links + server PAT. OAuth V2. Never user-pasted PATs
- SUPERSEDES 02-auth-service.md's email/password-primary design: GitHub OAuth IS the login (V1), not a separate post-login connect step. Google auth explicitly skipped. No password/email signup built or planned for V1. User identity = github_id (in-memory placeholder now, MySQL `users` keyed on github_id later). Session still cookie+Redis, unchanged.
- Microservices, Node/Express, MVC layout matching teammate's repo
- RAG: stuff small corpora (macros, ATS rules); retrieve only exemplars + JD
- Compile errors (422) route to renderer/dev, never fed to LLM

## OPEN (ask Ayush before assuming)
- images in CV vs ATS: conflict named, unresolved. Options: ATS-only | two templates
- writer svc language Node vs Python: Node assumed, unconfirmed
- writer svc repo: separate | inside CV_BUILDER | monorepo — unconfirmed
- auth = standalone learning project vs integrated backend: integrated assumed
- Overleaf-style live editor UI: mentioned by teammate ("later for live rendering"), scope unclear

## TEAMMATE RELAY (pending)
- CV_BUILDER: timeout code 15s vs README 30s
- CV_BUILDER: PORT no fallback in server.config.js
