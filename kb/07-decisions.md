# Decisions

## LOCKED
- CV format = LaTeX (Jake Gutierrez template). docx/docxtpl plan DEAD (document-half canvases v1-v3 show old plan — historical only)
- LLM outputs JSON only; deterministic renderer writes tex. Never LLM → raw LaTeX into CV
- Diff + human y/N gate before any CV change. Reject = untouched. Default N
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
- What happens after a user selects a CV template on TemplatePage — no backend call yet, selection is local React state only. Ayush: "i will tell later"
- Whether/when to actually finish the Google OAuth login path (code exists, unmounted)
- Template preview images only render page 1 of each template's compiled sample content (`pdftoppm -f 1 -l 1`). Fine for now since these are style-preview thumbnails of placeholder content, not the user's real (eventually multi-page) resume — but if a template's sample spans >1 page, pages 2+ are invisible in both the grid thumbnail and the click-to-preview modal (same PNG reused for both). Not yet decided whether to fix (render+page through all pages, or add a page-count badge).

## TEAMMATE RELAY (pending)
- CV_BUILDER: timeout code 15s vs README 30s
- CV_BUILDER: PORT no fallback in server.config.js
