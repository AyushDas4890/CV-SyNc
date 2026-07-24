# CV-Sync — Session Summary (2026-07-22)

Goal for the session: **analyze the project and run the website**, then fix the
issues that surfaced while clicking through the app.

---

## 1. Project analysis

CV-Sync is a multi-service app:

| Service | Stack | Port | Role |
|---|---|---|---|
| **frontend** | React + Vite | 5173 | UI / onboarding flow |
| **auth-service** | Node/Express + Redis | 4000 | Session auth + GitHub/Google OAuth |
| **CV_BRAIN** | FastAPI (Python) | 8000 | LLM ATS resume + LaTeX generation |
| **mock-cv-builder** | Node/Express | 3000 | Local mock of CV_BUILDER (serves `.tex` templates) |

Frontend API wiring lives in [frontend/src/api.js](../frontend/src/api.js):
- `VITE_API_URL` → auth-service (4000)
- `VITE_LLM_BRAIN_URL` → CV_BRAIN (8000)
- `VITE_CV_BUILDER_URL` → CV builder (3000)

---

## 2. Docker setup (Redis)

For real session storage (instead of in-memory fallback), auth-service needs
Redis. Since Redis is not natively available on Windows, I containerized it
with Docker:

1. **Check Docker installation:**
   ```bash
   docker --version
   # Output: Docker version 29.5.2, build 79eb04c
   ```

2. **Start Docker Desktop** (if not already running):
   ```powershell
   Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
   # Wait ~5 seconds for daemon to initialize
   ```

3. **Verify Docker daemon is ready:**
   ```bash
   docker ps
   # Should list containers with no errors
   ```

4. **Run Redis in a container:**
   ```bash
   docker run -d --name cv-sync-redis -p 6379:6379 redis:7-alpine
   ```
   - `-d` = detached (runs in background)
   - `--name cv-sync-redis` = container name (for reference)
   - `-p 6379:6379` = port mapping (container port 6379 → localhost 6379)
   - `redis:7-alpine` = lightweight Redis 7 image (~50MB, pulled on first run)

5. **Verify Redis is running:**
   ```bash
   docker ps --filter name=cv-sync-redis
   # Output: cv-sync-redis Up X seconds 0.0.0.0:6379->6379/tcp
   
   docker exec cv-sync-redis redis-cli ping
   # Output: PONG
   ```

**Result:** auth-service can now connect to `redis://localhost:6379` via
`REDIS_URL` env var (configured in `.env`). Sessions are persisted in Redis
instead of ephemeral in-memory store.

---

1. **Frontend** — `npm run dev`. Started fine but was only bound to IPv6
   (`[::1]:5173`), so `localhost` (IPv4) gave **ERR_CONNECTION_REFUSED**.
   - **Fix:** relaunched with `npm run dev -- --host 127.0.0.1`. Now reachable
     at http://127.0.0.1:5173 and http://localhost:5173.

2. **CV_BRAIN** — `uv run python main.py` (FastAPI on 8000). Docs at `/docs`,
   health at `/health`.

3. **auth-service** — `npm run dev`. It only uses Redis when `USE_REDIS=true`
   (otherwise falls back to in-memory MemoryStore).
   - **Started with:** `USE_REDIS=true npm run dev` → `[redis] Connected to
     Redis session store`, listening on :4000.

4. **mock-cv-builder** — discovered CV_BRAIN needs it at port 3000 to fetch
   templates (first "Generate CV" failed with *All connection attempts failed*
   because it was down). Started with `npm run dev` → serves templates from
   `cv-templates/`.
   - Note: its `POST /api/compile` is a **stub returning 503**, so final PDF
     compilation won't work yet — template fetch + CV generation do.

---

## 4. Bugs found & fixed

### 4a. Frontend not reachable on `localhost`
Vite bound to IPv6 only. Fixed by forcing `--host 127.0.0.1` (see above).

### 4b. Misleading "invalid/rate-limited API key" error
"Generate CV" returned:
> Resume validation failed: has_education_section, has_skills_section,
> min_content_lines, has_bullet_content. Please ensure your LLM API keys are
> valid and not rate-limited (TPD/TPM limits).

**This was a red herring.** Logs showed the OpenAI key (`gpt-4o-mini`) working
fine and returning valid LaTeX every attempt. The real failure was the
**output validator** in
[CV_BRAIN/app/service/output_validator.py](../CV_BRAIN/app/service/output_validator.py).

- `.env` note for the user: the OpenAI key must **not** be wrapped in quotes.
  `python-dotenv` does not strip quotes, so `OPENAI_API_KEY="sk-..."` would make
  the quote characters part of the key. It is already correct (unquoted).

### 4c. Validator: too-strict section-header matching
`_check_section_present()` did an **exact** brace match
(`\section{Education}`), but the Anubhav template decorates headers:
- `\section{~~Education}`
- `\section{Skills Summary}`

So legitimately-present sections were reported missing, and retries made the
LLM second-guess and mangle sections that were already fine.

**Fix applied:** loosened the regex to match the section name *anywhere inside
the braces* (with `re.escape` + optional starred sections). Verified in
isolation:
```
Education: True
Skills:    True
```

### 4d. Uvicorn `--reload` not picking up edits
The running CV_BRAIN process was stale — edits on disk weren't hot-reloaded (no
reload event in logs, no debug output).

**Fix:** killed the stale process tree (PIDs 31512 / 50860) and restarted
CV_BRAIN cleanly with
`uv run uvicorn main:app --host 0.0.0.0 --port 8000`.

---

## 5. Debug instrumentation added (temporary)

In [CV_BRAIN/app/service/latex_generator_services.py](../CV_BRAIN/app/service/latex_generator_services.py),
right after the first `call_llm(...)`, added a debug dump of every
`\section{...}` header the LLM emits, to diagnose the remaining
`has_education_section` / `has_skills_section` failures:

```python
import re as _re
for _m in _re.findall(r"\\section\*?\{[^}]*\}", edited_tex or ""):
    print(f"[LLM_BRAIN][DEBUG] section header: {_m!r}")
```

> **TODO / cleanup:** remove this debug block once the validator issue is fully
> confirmed resolved.

---

## 6. Current state

- All four services running:
  - frontend → http://127.0.0.1:5173
  - auth-service → http://localhost:4000 (Redis-backed sessions)
  - CV_BRAIN → http://localhost:8000 (with validator fix + debug dump)
  - mock-cv-builder → http://localhost:3000
- Redis running in Docker (`cv-sync-redis`).

## 7. Open items / next steps

1. **Confirm the validator fix end-to-end** — the last restart loaded the fix
   but a fresh "Generate CV" hadn't been re-run yet. Read the new
   `[LLM_BRAIN][DEBUG] section header:` lines to see exactly what the LLM emits
   vs. what the validator expects.
2. If `has_education_section`/`has_skills_section` still fail, the LLM may be
   *renaming* headers (e.g. dropping "Education") — would need a prompt tweak to
   force the template's exact section names, or broaden the validator's accepted
   synonyms.
3. **Remove the temporary DEBUG block** in `latex_generator_services.py`.
4. **mock-cv-builder `/api/compile` is a 503 stub** — real PDF compilation
   still needs a working CV_BUILDER (LaTeX engine) before end-to-end PDF output.
5. Google OAuth creds in `auth-service/.env` are empty — only GitHub OAuth is
   configured.
