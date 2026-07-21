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
GitHub OAuth is now the login itself (not a post-login connect step). Google skipped, no email/password V1. This supersedes 9a-e above for auth — see 07-decisions.

- `backend/auth-service/`: routes — GET /api/auth/github (login, redirects to GitHub), GET /api/auth/github/callback (creates/finds user by github_id, starts session, regenerates session id on login), GET /api/auth/me, POST /api/auth/logout, GET /api/auth/github/repos (requireSession-guarded). CORS+credentials configured. `userStore.service.js` still an in-memory Map keyed on github_id — TODO MySQL. No more `/dev/login`, removed once GitHub-login replaced it.
- `frontend/`: Vite+React, 4 pages (auth, experience, github-repos, template-picker) styled off kb/ui-reference. Auth page = single "Continue with GitHub" button. Experience + GitHub-repos pages both guard on `/api/auth/me`, bounce to /auth if not logged in. Login redirect flow: AuthPage → github.com consent → backend callback → lands on /onboarding/experience → then /onboarding/github (repo picker, no connect button, already logged in) → /onboarding/templates (placeholder thumbnails, real CV_TEMPLATES images still pending).
- Verified end-to-end against a real (locally-built) Redis + Node server: full session lifecycle (401 unauthenticated → login redirect to real github.com authorize URL with correct client_id/scope/state → session cookie set → still 401 until callback completes), CORS preflight/headers, 503-not-hang fallback when Redis is down, userStore identity dedup on re-login. NOT verified: the actual GitHub consent screen + callback token exchange — needs a real registered GitHub OAuth App + a browser, which requires you to run it locally.
- To run together: auth-service needs Redis running locally + a real GitHub OAuth App (client id/secret + callback URL registered on github.com must match .env exactly). `cd backend/auth-service && npm install && npm run dev`. `cd frontend && npm install && npm run dev`.

## Local run status (Ayush's machine, 2026-07-21)
- GitHub OAuth App registered, .env filled in — done.
- Backend runs locally: `npm run dev` → "auth-service listening on :4000" confirmed.
- BLOCKED: Redis not running locally yet → backend logs "[redis] connection failed", session routes 503 (this is the coded fallback working as designed, not a crash).
- Tried `docker run -d -p 6379:6379 redis` → failed: DNS resolution error pulling the image (`getaddrinfo` failure reaching production.cloudfront.docker.com). Possibly Cloudflare One Client (VPN/network tool, installed on this machine) interfering with DNS, or a transient network issue. Not yet resolved.
- Fallback not yet tried: WSL is installed on this machine — install Redis natively inside a WSL distro instead of fighting Docker networking (`sudo apt install redis-server`, more reliable than Docker Desktop's registry pull on this network).
- Once Redis is up: restart backend (`npm run dev`) — it only connects to Redis once at boot, no retry loop, so it must be restarted after Redis becomes available, not just left running.
- Frontend not started yet this session — do after Redis+backend are confirmed working (`cd frontend && npm run dev`, opens on :5173).
