# Bug sweep + deployment hardening — 2026-07-29

Full-repo audit (auth-service, CV_BRAIN, frontend, Docker) against the KB.
All findings below were fixed and verified in-session unless marked OPEN.

## SECURITY (fixed)

1. **TLS verification was disabled on every GitHub call.** `githubAuth.service.js`
   had `rejectUnauthorized: process.env.NODE_TLS_REJECT_UNAUTHORIZED !== "0" && false`
   — the `&& false` made it unconditionally `false`. This covered the OAuth
   **token exchange**, so a MITM could lift the GitHub client secret and user
   access tokens. Now verifies by default; opt out only via
   `ALLOW_INSECURE_TLS=true`, which is additionally ignored when
   `NODE_ENV=production`. Behind an SSL-inspection proxy prefer
   `NODE_EXTRA_CA_CERTS`.
2. **Placeholder session secret could reach production.** `SESSION_SECRET`
   silently defaulted to `dev-secret-change-me` (and compose passed `change-me`)
   — forgeable session cookies. `config/env.js` now `process.exit(1)`s in
   production if `SESSION_SECRET` is missing/default, or if
   `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` / `GITHUB_CALLBACK_URL` /
   `FRONTEND_URL` are unset.
3. **CV_BRAIN CORS was `allow_origins=["*"]` with `allow_credentials=True`.**
   `/api/generate-cv` spends real LLM credits, so any site could drive it from a
   visitor's browser. (The combination is also invalid CORS that browsers
   reject.) Now an allowlist from `ALLOWED_ORIGINS` / `FRONTEND_URL`.
4. **CV_BRAIN leaked internals on error.** The catch-all returned
   `detail=str(err)` to the client. Now logs the traceback server-side and
   returns a generic message.
5. **GitHub OAuth scope over-provisioned.** Default was `public_repo`, which is
   a **write** scope (push access to all the user's public repos). Only
   identity + public repo listing is needed → default is now `read:user`.
6. `GET /repos/:owner/:repo/readme` interpolated params unencoded →
   `encodeURIComponent` on both.

## CORRECTNESS (fixed)

7. **CV_BRAIN blocked its own event loop.** `call_llm()` uses LangChain's
   synchronous `.invoke()` but was called directly from the `async` handler, so
   one CV generation stalled *every* other request (including `/health`) for the
   whole LLM round-trip. Added `call_llm_async()` →
   `anyio.to_thread.run_sync`; both the first attempt and the retry now use it.
8. **Prompt truncation could produce an empty prompt.** `_call_openai`'s
   `user_prompt[:-overflow]` returns `""` whenever overflow ≥ len(user_prompt)
   (large system prompt / big template) — the LLM then returned garbage for no
   visible reason. Now clamps to a 10k-char floor and logs the new length.
9. `output_validator` used pydantic-v1 `.dict()` → `.model_dump()`.
10. `RepoDetail` got `populate_by_name=True`. Previously only the aliases
    (`full_name`, `readme_content`, …) were accepted and a camelCase caller had
    fields silently dropped to defaults rather than erroring.
11. `httpx.RequestError` (CV_BUILDER down) fell through to the generic 500
    handler; it's now grouped with `HTTPStatusError` → clean 502.
12. Frontend showed a **blank username for non-GitHub users** — four pages read
    `res.githubUsername` with no fallback. Now falls back to
    `displayName` → `email` (ProfilePage already did this).

## DEPLOYMENT (fixed)

13. **The frontend image shipped the Vite dev server** (`npx vite`) — no
    minification, HMR websocket, explicitly not for production. Replaced with a
    multi-stage build → `nginx:1.27-alpine` serving the static bundle, still on
    port 5173 so nothing else changes. Added `frontend/nginx.conf` with the
    SPA history fallback (**without it, refreshing any deep link like
    `/onboarding/profile` 404s**), immutable asset caching, no-cache on
    index.html, gzip, and basic security headers.
14. **Vite env vars must be build args, not runtime env.** `VITE_*` is inlined
    at build time, so compose's `environment:` block had no effect. Moved to
    `build.args`; added the two that were missing entirely
    (`VITE_LLM_BRAIN_URL`, `VITE_CV_BUILDER_URL` — previously always fell back
    to hardcoded localhost).
15. **`trust proxy` was missing.** Behind a TLS-terminating proxy,
    express-session checks `req.secure` before issuing a `secure` cookie — so in
    production login would appear to succeed then immediately log out. Now set
    when `NODE_ENV=production`.
16. **Silent MemoryStore fallback in production.** If Redis failed to connect
    the service quietly degraded to MemoryStore (leaks memory, drops all
    sessions on restart, breaks across instances). Now fatal in production;
    also fatal if `USE_REDIS!=="true"` in production.
17. Added `COOKIE_SAMESITE` (needs `none` if frontend and API are on different
    registrable domains; requires HTTPS).
18. compose: healthchecks on all four services + `depends_on: condition:
    service_healthy` (was unordered), `express.json({limit:"1mb"})`.
19. New **`docker-compose.prod.yml`** overlay:
    `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`.
    Sets `NODE_ENV=production` / `ENV=production`, unpublishes internal ports,
    and uses `${VAR:?}` so a missing secret fails the run instead of booting
    insecurely. Base compose stays the local-dev stack.
20. `.env.example` documents every new/changed var.

## VERIFIED THIS SESSION

- `node --check` on all auth-service files; `compileall` on CV_BRAIN.
- Both compose files parse; `vite build` succeeds (196 kB, 61 kB gzip) and all
  three `VITE_*` URLs confirmed baked into the bundle.
- **auth-service live**: health 200 · `/api/auth/me` 401 without cookie ·
  dev/login sets session · register 201 · duplicate 409 · wrong password 401 ·
  correct password 200 · profile POST/GET round-trips · logout then `me` 401 ·
  `/api/auth/github` 302 · `publicProfile` confirmed stripping `passwordHash`.
- **Fail-fast confirmed**: production boot exits 1 on placeholder
  `SESSION_SECRET`, and on `USE_REDIS` not being `true`.
- **CV_BRAIN live**: `/health` and `/api/templates` 200 · CORS preflight allows
  `localhost:5173` and **rejects `evil.example` with 400** · generate-cv with
  CV_BUILDER down returns 502 with the generic message (no internals).

Sandbox note: `require('express')` takes ~17s off the mounted filesystem, so a
service that looks hung on first boot here is usually just module loading.

## OPEN (not fixed — needs your call)

- **No rate limiting on `/api/auth/email/login`** — brute-forceable. Fix needs
  `express-rate-limit`; left alone per the no-new-dependencies rule. This is the
  main remaining security gap.
- **`userStore` is still in-memory.** Every user, profile and GitHub token is
  lost on restart and is not shared across instances — so the app cannot run
  more than one replica. The MySQL `users` table (02-auth-service.md) is the
  real blocker for production, independent of everything above.
- Diff/approve gate still absent (pre-existing, see 07-decisions LOCKED).
- `latex_sanitizer.fix_subheading_args` matches args with `\{[^{}]*\}`, which
  can't handle nested braces (e.g. `{\textbf{X}}`) and may rewrite such a
  `\resumeSubheading` wrongly. Not touched — needs a compile-level test first.
- `fallback_latex_filler` is imported but unused in
  `latex_generator_services.py` (generation now raises instead of falling back).
- CV_BUILDER relay items in 07-decisions are unchanged — that repo isn't vendored.
