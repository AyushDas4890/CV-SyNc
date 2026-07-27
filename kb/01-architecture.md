# Architecture

REVISED 2026-07-22 — this is the shipped architecture, not the original 4-service design
below (kept struck-through for history/rationale; see 07-decisions.md for the full
supersession note).

3 services, actually built:

```
frontend (React)
  ├─ auth-service (Node/Express, port 4000)   — session cookie guards all its APIs
  │    also: GET /api/auth/github/repos/:owner/:repo/readme (README+topics fetch)
  ├─ CV_BRAIN (Python/FastAPI, port 8000, vendored at CV_BRAIN/)
  │    fetches template tex from CV_BUILDER, LLM (OpenAI first, Groq fallback)
  │    fills it directly, validates completeness, retries once, sanitizes
  └─ CV_BUILDER (Node/Express, port 3000, NOT in this repo — github.com/IamAbhinav01/CV_BUILDER)
       serves template tex, compiles final tex → PDF
```

Real flow (frontend/src/api.js `generateCv()` + `compileCv()`):
```
user completes onboarding (profile/education/achievements/experience, repo picks, template)
  → frontend fetches READMEs for selected repos via auth-service
  → frontend POSTs to CV_BRAIN /api/generate-cv {user_profile, selected_repos, template_id}
  → CV_BRAIN fetches template tex from CV_BUILDER, LLM fills it, returns {tex, engine}
  → frontend POSTs {tex, engine, templateId} to CV_BUILDER /api/compile
  → 200 PDF binary, or 422 {log, errors} shown inline
```

Contracts (as actually implemented):
1. CV_BRAIN `POST /api/generate-cv`: see `CV_BRAIN/app/models.py` (`GenerateCvRequest`, `UserProfile`, `RepoDetail`, `AchievementEntry`) → `{ok, tex, engine, template_id, summary}`
2. CV_BUILDER `POST /api/compile {tex, engine?, templateId?}` → 200 PDF binary | 422 `{ok:false, log, errors:[{file,line,message}]}` | 400 missing | 413 >2M chars
3. Template id mapping: frontend short ids (`jake`, `altacv`, ...) vs CV_BRAIN's registry keys (`Jake_s_Resume__3_`, ...) — see `frontend/src/pages/TemplatePage.jsx` `TEMPLATES[].brainId` / `brainIdFor()` / `shortIdFor()`

Known gap vs. the original design principle below: no diff/approve gate exists on this path — CV_BRAIN generates the full tex directly and it goes straight to compile. Not built, not forgotten — see 07-decisions.md OPEN section.

---

## Original design (2026-07 initial planning, NOT what shipped)

4 services, Node/Express assumed everywhere (match teammate).

```
user → [auth svc] session cookie guards all APIs
user pick repos → [fetch+LLM svc] → data/projects.json
projects.json + cv_template.tex → [writer svc] → final .tex + diff gate
final .tex → POST compiler /api/compile → PDF (or 422 errors)
```

Contracts (never implemented):
1. projects.json (LLM half → writer half):
```json
[{"title":"...","tech_stack":["..."],"bullets":["..."],"repo_url":"...","dates":"..."}]
```
2. writer API (planned, never built): POST /api/write {projects} (?dry=true → diff only), POST /api/approve → compile + snapshot.

Infra (containerised, working as of 2026-07-27): `docker-compose.yml` at repo root orchestrates 5 services:
  - `redis` (redis:7-alpine) — session store for auth-service
  - `cv-builder` (builds from `./cv_builder_src`) — TexLive + Node, port 3000
  - `cv-brain` (builds from `./CV_BRAIN`) — Python 3.11 + FastAPI, port 8000
  - `auth-service` (builds from `./backend/auth-service`) — Node/Express, port 4000
  - `frontend` (builds from `./frontend`) — Vite dev server, port 5173

Docker gotcha: CV_BRAIN's `.python-version` says `3.10` but its Dockerfile uses `python:3.11-slim`. `ENV UV_PYTHON=python3.11` overrides this so `uv` doesn't try to download Python 3.10 at build/runtime. `ENV UV_SYSTEM_CERTS=1` + `--trusted-host` flags handle corporate SSL-inspection proxies (e.g., Sophos/Zscaler). CMD invokes `.venv/bin/uvicorn` directly instead of `uv run` to avoid any runtime network calls.

Key principle (NOT how CV_BRAIN actually works — see above): LLM outputs JSON ONLY, never raw LaTeX. Deterministic renderer owns tex. Diff gate between LLM and CV always.
