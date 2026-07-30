# Running CV-Sync from Docker images

The whole application — frontend, auth service, LLM service, LaTeX compiler and
Redis — runs from four built images plus stock `redis:7-alpine`. **Nothing is
read from the project directory at runtime.** Once the images are built you can
delete or move the source tree and the app still starts.

| Image | Contains | Port |
|---|---|---|
| `cvsync/frontend` | built Vite bundle, served by `serve` (SPA fallback) | 5173 |
| `cvsync/auth-service` | Express + GitHub OAuth, Redis-backed sessions | 4000 |
| `cvsync/cv-brain` | FastAPI + venv, LLM generation, template registry | 8000 |
| `cvsync/cv-builder` | TeX Live 2023 + Node, **all CV templates baked in** | 3000 |
| `redis:7-alpine` | session store (named volume `redis-data`) | internal |

Two compose files:

- **`docker-compose.yml`** — development. Has `build:` sections, so it needs the
  source tree. Use it to build and iterate.
- **`docker-compose.release.yml`** — release. Images only, **no `build:`, no bind
  mounts**. Copy this one file anywhere and run it.

---

## 1. Build the images

From the project root:

```bash
docker compose build
```

This produces `cvsync/frontend`, `cvsync/auth-service`, `cvsync/cv-brain` and
`cvsync/cv-builder`, all tagged `:latest`. To tag a specific version instead:

```bash
CVSYNC_TAG=1.0.0 docker compose build
```

Confirm they exist:

```bash
docker images --filter "reference=cvsync/*"
```

> **If the build fails with `502 Too many open files`** resolving
> `python:3.11-slim` or `node:20-alpine`, that is the network's TLS-inspecting
> proxy failing to reach `docker.io`, not a problem with the Dockerfile. Simply
> run the build again — it usually succeeds within two or three attempts.

## 2. Set up an env file (outside the project)

Secrets are **never** baked into the images. They are supplied at container
start. Copy the template somewhere outside the project — this is the file you
keep when the source tree goes away:

```bash
mkdir -p ~/cvsync
cp .env.release.example ~/cvsync/cvsync.env
# then edit ~/cvsync/cvsync.env and fill in real values
```

At minimum set `OPENAI_API_KEY` **or** `GROQ_API_KEY` (CV generation returns
HTTP 400 without one), plus `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` for
login. Generate a session key with `openssl rand -hex 32`.

Also copy the release compose file next to it:

```bash
cp docker-compose.release.yml ~/cvsync/
```

`~/cvsync/` now holds everything needed to run the app forever.

## 3. Run the container stack

```bash
cd ~/cvsync
docker compose -p cvsync -f docker-compose.release.yml --env-file cvsync.env up -d
```

Open <http://localhost:5173>.

Check status and health:

```bash
docker compose -p cvsync -f docker-compose.release.yml ps
curl http://localhost:8000/health
curl http://localhost:4000/api/health
curl http://localhost:3000/api/health
```

## 4. Stop / remove

```bash
# Stop, keep containers
docker compose -p cvsync -f docker-compose.release.yml stop

# Stop and remove containers + network (KEEPS the redis volume)
docker compose -p cvsync -f docker-compose.release.yml down

# Also delete the persisted session data
docker compose -p cvsync -f docker-compose.release.yml down -v
```

## 5. Start again from the existing images

Exactly the same command as step 3 — nothing is rebuilt, because the release
file has no `build:` section:

```bash
cd ~/cvsync
docker compose -p cvsync -f docker-compose.release.yml --env-file cvsync.env up -d
```

---

## Proving it does not depend on the source directory

This is the test in full. **It never deletes anything** — it moves the project
aside and puts it back.

```bash
# 1. Build, from the project
cd "/c/Users/ayush/Claude/Projects/CV SYNC"
docker compose build

# 2. Run it and confirm it works
docker compose up -d
curl http://localhost:5173/          # 200
docker compose down

# 3. Stage the release files somewhere else
mkdir -p ~/cvsync
cp docker-compose.release.yml ~/cvsync/
cp .env ~/cvsync/cvsync.env          # your real values

# 4. MOVE the project away (reversible — do not delete)
cd ~
mv "/c/Users/ayush/Claude/Projects/CV SYNC" "/c/Users/ayush/Claude/Projects/CV SYNC.moved"

# 5. Start from images only, with the source tree gone
cd ~/cvsync
docker compose -p cvsync -f docker-compose.release.yml --env-file cvsync.env up -d

# 6. Verify the app still works
curl -o /dev/null -w "frontend %{http_code}\n" http://localhost:5173/
curl -o /dev/null -w "cv-brain %{http_code}\n" http://localhost:8000/health
curl -o /dev/null -w "auth     %{http_code}\n" http://localhost:4000/api/health
curl -o /dev/null -w "builder  %{http_code}\n" http://localhost:3000/api/health
curl -s http://localhost:8000/api/templates    # template list served from the image

# 7. Put the project back
mv "/c/Users/ayush/Claude/Projects/CV SYNC.moved" "/c/Users/ayush/Claude/Projects/CV SYNC"
```

### Verifying independence without moving anything

Two checks that prove it directly:

```bash
# A. No container has a bind mount to the host. Expect only the redis
#    named volume; any line containing "bind" is a host dependency.
docker inspect $(docker ps -q --filter "name=cvsync") \
  --format '{{.Name}}: {{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}} {{end}}'

# B. The release config contains no build context at all.
docker compose -f docker-compose.release.yml config | grep -E "build:|context:|type: bind"
#    Expect NO output.
```

You can also confirm the templates live inside the image rather than on disk:

```bash
docker exec cvsync-cv-builder-1 ls /app/src/templates
```

---

## Moving the images to another machine

The images are self-contained, so a tarball is all you need — no source, no
registry:

```bash
# On the machine that has them
docker save -o cvsync-images.tar \
  cvsync/frontend:latest cvsync/auth-service:latest \
  cvsync/cv-brain:latest cvsync/cv-builder:latest redis:7-alpine

# On the target machine
docker load -i cvsync-images.tar
# then copy docker-compose.release.yml + your env file across and run step 3
```

The tarball is roughly 3 GB, most of it TeX Live in `cvsync/cv-builder`.

---

## Things worth knowing

**The frontend's API URLs are baked in at build time.** Vite inlines
`import.meta.env.VITE_*` into the bundle, so setting them as container env vars
does nothing. They are build args. To point the UI at other hosts, rebuild:

```bash
docker compose build \
  --build-arg VITE_API_URL=https://api.example.com \
  --build-arg VITE_LLM_BRAIN_URL=https://brain.example.com \
  --build-arg VITE_CV_BUILDER_URL=https://build.example.com \
  frontend
```

**Only Redis gets a volume.** Everything else is stateless by design: generated
CVs stream back to the browser and LaTeX jobs are compiled in a temp dir that is
deleted immediately after. `down -v` therefore only costs you logged-in
sessions.

**Going to production** needs the overlay, a real `SESSION_SECRET`, and a
TLS-terminating reverse proxy in front:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

`NODE_ENV=production` turns on secure cookies, which browsers refuse to send
over plain HTTP — without TLS the symptom is logging in and being immediately
logged out. See `kb/08-bugfix-deploy-2026-07-29.md`.

**Secrets never enter an image.** Each service's `.dockerignore` excludes
`.env`, verified with:

```bash
docker run --rm --entrypoint sh cvsync/cv-brain -c 'ls -a /app/.env'
# ls: /app/.env: No such file or directory
```
