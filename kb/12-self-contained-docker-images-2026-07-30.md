# Self-contained Docker images (2026-07-30)

Goal: the app runs from built images alone. Delete or move the source tree and
`docker compose up` still works. Full command reference lives in `DOCKER.md` at
the repo root — this file records what was changed and why.

## Starting point was already most of the way there

Worth knowing before "fixing" anything: the stack **already had no bind
mounts**, every Dockerfile already `COPY`d its source in, and every service's
`.dockerignore` already excluded `.env`. Verified rather than assumed:

```
docker inspect <container> --format '{{range .Mounts}}...'   → only redis's named volume
docker run --rm --entrypoint sh cvsync/cv-brain -c 'ls -a /app/.env'  → No such file
```

So the containers never depended on the host tree. The single thing that did
was **`docker-compose.yml` itself**: its `build:` sections need the source, so
with the project gone `docker compose up` fails before it starts anything.

## What changed

**1. Explicit image tags** (`docker-compose.yml`). Services were relying on
compose's auto-generated names (`cvsync-cv-brain`), which are derived from the
directory name and change if the folder is renamed. Now pinned to
`cvsync/<service>:${CVSYNC_TAG:-latest}` so another compose file can name them.

**2. `docker-compose.release.yml`** — the actual deliverable. Same topology,
`image:` only, **no `build:`, no bind mounts**, ports and env overridable. This
one file plus an env file is a complete, portable deployment.

**3. `.dockerignore` at the repo root and in `cv_builder_src/`.** Root was
missing entirely; `cv_builder_src` was missing one and its context included
`node_modules` and the tracked `app.log`.

**4. `.env.release.example`** — env template meant to live *outside* the
project, since after the source tree goes away the root `.env` goes with it.

## Verified by actually relocating the stack

Not reasoned about — run. The dev stack was taken down, then the release stack
was started from a scratch directory containing **only**
`docker-compose.release.yml` and an env file:

- all 5 services healthy; frontend/auth/cv-brain/cv-builder all return 200
- `docker inspect` across all five: **zero bind mounts**, only the redis volume
- `docker compose config | grep build:` → no output
- templates listed from *inside* the cv-builder image (`/app/src/templates`)
- a full CV generation + LaTeX compile succeeded through the relocated stack

The project directory was **not** deleted. `DOCKER.md` documents the move-aside
test with `mv` (reversible) rather than `rm`.

## Gotchas that cost time

**The dev stack restarts itself.** `restart: unless-stopped` plus Docker
Desktop means a `docker compose down` can be followed by the containers being
back minutes later, and the release stack then fails with
`Bind for 0.0.0.0:3000 failed: port is already allocated`. Check `docker ps`
before blaming the new compose file.

**A partially-failed `up` leaves a stale network.** After the port clash above,
redis was left attached to a network that the retry recreated, and auth-service
died with `[redis] error: Connection timeout` — which reads like a Redis
problem and is not. `down --remove-orphans` then `up` fixes it.

**`docker exec ... ls /app/...` under Git Bash** rewrites the path to
`C:/Program Files/Git/app/...`. Prefix with `MSYS_NO_PATHCONV=1`.

**docker.io is intermittently unreachable** here (`502 Too many open files`
resolving `python:3.11-slim`). The build just fails and leaves the previous
image in place; retry two or three times. Always confirm with
`GET :8000/health` that the build string actually changed.

## Deliberate non-goals

- **`cv_builder_src/` still builds from the local checkout.** It is a gitlink to
  a repo with no push access, and `.dockerignore` added there is untracked in
  that submodule. The image itself is self-contained; only the *build* needs
  the checkout.
- **Frontend API URLs stay build-time.** Vite inlines `VITE_*` into the bundle,
  so they cannot be runtime env vars. `docker-compose.release.yml` says so
  where someone would otherwise try; changing them means rebuilding that image.
- **Only Redis gets a volume**, holding sessions. Everything else is genuinely
  stateless — generated CVs stream to the browser and LaTeX job dirs are
  deleted right after compiling — so `down -v` costs only logins.
