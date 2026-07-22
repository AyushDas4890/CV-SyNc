# Build plan — phased, each step has pass check. Run check before next step.

## Phase A — writer service (CURRENT)
1. CV → LaTeX by hand (Jake template), add % PROJECTS_START/END markers. PASS: compiles on /api/compile, PDF = current CV
2. Scaffold writer svc (MVC like teammate). PASS: /api/health 200
3. Renderer: escape + emit blocks + splice markers. PASS: sample projects.json → tex compiles, only Projects changed
4. Wire compiler call, relay PDF/422. PASS: json → PDF one request
5. Diff gate: snapshot + dry=true diff + approve endpoint. PASS: reject leaves all untouched

## Phase B — fetch + LLM
6. fetch: README/langs/topics per repo, server PAT. PASS: repo without README = graceful skip
7. summarize: OpenAI → validated projects.json, 1 retry. PASS: contract shape + notes metric appears in bullet
8. RAG: stuff A+B; exemplar bank C + retrieval; JD keywords D. PASS: retrieved exemplars match repo domain

## Phase C — auth + glue
9. auth svc build order: (a) E2E spike signup→cookie→protected ~100 lines PASS: curl 200 w/ cookie, 401 without; (b) migration users table PASS: dup email fails; (c) /signin + dummy verify PASS: wrong pw & unknown email identical 401; (d) /logout PASS: old sid 401 after; (e) validation + rate limit middlewares PASS: 400 bad body, 429 11th rapid req
10. auth guards all writer/fetch endpoints. PASS: no cookie → 401 everywhere
11. docker-compose all services + mysql + redis. PASS: one curl full flow
12. frontend: repo picker, diff view, approve button, overleaf-style error display (uses compiler errors[])

Rule: riskiest piece first — A1 proves template feasibility, 9a proves auth integrations.

## Out-of-order work already done (ahead of Phase C) — auth model revised
GitHub OAuth is the primary/recommended login. REVISED again 2026-07-21: auth is now unified — GitHub OAuth + email/password both fully working, Google OAuth code present but unmounted ("coming soon"). This supersedes 9a-e above for auth — see 07-decisions.

- `backend/auth-service/`: routes — GET /api/auth/github (login, redirects to GitHub), GET /api/auth/github/callback (creates/finds user by github_id, session.regenerate on login), GET /api/auth/me, POST /api/auth/logout, GET /api/auth/github/repos (requireSession-guarded), POST /api/auth/email/register, POST /api/auth/email/login. CORS+credentials configured. `userStore.service.js` is a unified in-memory store (github_id / google_id / email, bcryptjs for passwords) — TODO MySQL. Google routes exist (`googleAuth.controller.js`) but not mounted in the router — inert by design.
- `frontend/`: Vite+React, 5 pages (auth, profile, experience, github-repos, template-picker) styled off kb/ui-reference. AuthPage = GitHub button (primary, "Recommended" badge) + Google button (disabled/"coming soon") + Email/Password login-or-register form. After auth → /onboarding/profile. Experience + Template pages both guard on `/api/auth/me`, bounce to /auth if not logged in, and show a `LogoutBar` (username + logout button → POST /api/auth/logout → redirect /auth).
- `frontend/src/pages/TemplatePage.jsx`: real 8-template grid reading thumbnails from `frontend/public/template-previews/<id>.png`. Click → modal → "Select this template" → sets local `chosen` state only (no backend call yet).
- Verified end-to-end: full session lifecycle, CORS, 503-not-hang fallback when Redis down.

## Profile + Education onboarding step (2026-07-22 — DONE)
- New page `frontend/src/pages/ProfilePage.jsx` at route `/onboarding/profile`
- Fields: Full Name, Phone, Email, GitHub URL, LinkedIn URL, + dynamic Education repeater (Institution, Degree, Field of Study, Dates, CGPA/Percentage/GPA)
- On Continue: POST /api/profile → saves to user.studentProfile in userStore. Also mirrors to localStorage (`cv_sync_student_profile`). On mount: GET /api/profile → pre-fills form.
- Backend: `profile.controller.js`, `profile.routes.js`, `saveProfile`/`getProfile` in userStore. Mounted at /api/profile in server.js.
- Step indicator updated across all 5 pages: Account → Profile → Experience → GitHub → Template.
- OAuth callback now redirects to /onboarding/profile (was /onboarding/experience).
- To run: both servers already running dev mode. Frontend: http://localhost:5173. Backend: http://localhost:4000.

## CV templates (`cv-templates/`, done 2026-07-21)
- 8 templates pulled from `AyushDas4890/CV_TEMPLATES` (cv-formats/), each verified by actually compiling (xelatex where fontspec is used — deedy, plushcv; pdflatex otherwise). Missing CTAN packages (lato, fontawesome5/4, roboto, sourcesans, biblatex) fetched and installed into TEXMFHOME without root — see kb history for exact package fixes.
- Cleaned to LaTeX source + only-required assets (font folders kept only for deedy/plushcv which need them via `\setmainfont Path=`). No PDFs, no .aux/.log/.out build junk committed.
- `altacv/sample.tex`: Publications section commented out (needed biblatex just for unrelated demo content) — real edit, not a template defect.
- `frontend/public/template-previews/*.png`: real compiled renders, `pdftoppm -png -r 150 -f 1 -l 1` — **page 1 only, always**. See OPEN item in 07-decisions re: multi-page templates.
- NOT wired into backend anywhere — no service reads `cv-templates/` yet. Template selection on the frontend is currently decorative/local-state only (writer-service doesn't exist yet to consume it).
- PENDING: push cleaned `cv-templates/` folder to `AyushDas4890/CV_TEMPLATES` repo, and push CV-SyNc repo changes — both blocked on git credentials not available in the sandbox; must be run by Ayush locally (`git push`).

## Local run status (Ayush's machine, 2026-07-22)
- GitHub OAuth App registered, .env filled in — done.
- Both servers running: backend on :4000, frontend on :5173.
- MemoryStore in use (no Redis required in dev — sessions stored in process memory, lost on restart).
- Redis optional: set USE_REDIS=true in .env, start Redis, restart backend.
- Full onboarding flow verified: /auth → /onboarding/profile → /onboarding/experience → /onboarding/github → /onboarding/templates.
