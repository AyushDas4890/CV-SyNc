# Docker for this project — start here

Written for someone new to Docker, using CV-Sync's actual setup. If you want
only the commands, jump to [The five commands](#the-five-commands-you-actually-need).

## The three words you need

**Image** — a frozen snapshot of an installed, ready-to-run app. Think of a
`.zip` containing the OS libraries, the runtime and your code, all set up.
Images never change once built.

**Container** — a running copy of an image. Start it, stop it, delete it, start
another. Deleting a container does not touch the image, the same way deleting an
unzipped folder does not delete the `.zip`.

**Volume** — a disk that survives when a container is deleted. Containers are
disposable and forget everything; a volume is where the data you want to keep
lives. This project uses exactly one, for Redis (login sessions).

The mental model: image = the recipe, container = the meal, volume = the fridge.

## What this project is made of

Five containers that talk to each other:

```
  your browser
       │
       ▼
  frontend (5173) ──► auth-service (4000) ──► redis  (sessions)
       │
       ├──────────► cv-brain (8000)   the LLM that writes your CV
       │                  │
       └──────────► cv-builder (3000) ◄┘  LaTeX → PDF
```

`5173`, `4000` etc. are **ports** — numbered doors on your machine. The frontend
listens on 5173, which is why you open `localhost:5173`.

Running five containers by hand would be tedious, so **Docker Compose** does it
from one file. That is what `docker compose` commands are: "do this to all five
at once."

## Two compose files, and when to use which

| File | Use it when | Needs the source code? |
|---|---|---|
| `docker-compose.yml` | you changed the code and want to rebuild | **yes** |
| `docker-compose.release.yml` | you just want to run the app | no |

The difference: the first has `build:` instructions, the second only says "run
this pre-built image". That is why the release file works even if the project
folder is deleted.

## The five commands you actually need

Run these from `~/cvsync` (release) or the project folder (dev).

```bash
# 1. START everything in the background
docker compose -p cvsync -f docker-compose.release.yml --env-file cvsync.env up -d

# 2. IS IT RUNNING?
docker ps

# 3. WHAT WENT WRONG? (Ctrl+C to stop watching)
docker compose -p cvsync -f docker-compose.release.yml logs -f cv-brain

# 4. STOP everything
docker compose -p cvsync -f docker-compose.release.yml down

# 5. REBUILD after changing code (project folder, dev file)
docker compose build && docker compose up -d --force-recreate
```

Decoding the flags, once:

- `-d` — **detached**: run in the background and give you your terminal back.
  Without it your terminal is stuck showing logs until you press Ctrl+C.
- `-p cvsync` — **project name**: groups the five containers under one label.
  Use the same name every time or you will end up with two separate copies.
- `-f <file>` — which compose file to use.
- `--env-file cvsync.env` — where your secrets and settings come from.
- `--force-recreate` — throw away the old containers and make new ones from the
  freshly built image. Explained below, because it matters here.

## The mistake everyone makes once

**`restart` does not pick up code changes.** This project bakes the code into
the image, so:

```bash
docker compose restart cv-brain     # ← restarts the OLD code. Nothing changes.
```

To actually deploy an edit you must rebuild the image and replace the container:

```bash
docker compose build cv-brain
docker compose up -d --force-recreate cv-brain
```

Then confirm the new build is really live:

```bash
curl http://localhost:8000/health
```

It reports a `build` string. If it did not change, your edit is not running —
you are looking at a stale container, which looks exactly like a fix that
did not work.

## Reading `docker ps`

```
NAMES                  STATUS                    PORTS
cvsync-cv-brain-1      Up 59 minutes (healthy)   0.0.0.0:8000->8000/tcp
```

- `Up ... (healthy)` — running, and its self-check passes. What you want.
- `Up ... (unhealthy)` — running but failing its own check. Read the logs.
- `Restarting` — crashing on startup, over and over. Read the logs.
- **Missing entirely** — it stopped. `docker ps -a` shows stopped ones too.

`0.0.0.0:8000->8000` means "port 8000 on your PC forwards to port 8000 inside
the container". That arrow is why `localhost:8000` reaches it.

## When something is broken

Work down this list, in order:

```bash
# 1. Is Docker Desktop even on?
docker info

# 2. What is the state of the five?
docker ps -a

# 3. What did the broken one say? (last 50 lines)
docker compose -p cvsync -f docker-compose.release.yml logs --tail 50 auth-service

# 4. Nuclear option: recreate everything (keeps your data volume)
docker compose -p cvsync -f docker-compose.release.yml down
docker compose -p cvsync -f docker-compose.release.yml --env-file cvsync.env up -d
```

Three errors you will probably hit, and what they really mean:

**`port is already allocated`** — something else already uses that port, usually
an older copy of this same stack. Find it with `docker ps`, then `down` it.

**`dependency failed to start: container ... is unhealthy`** — a service could
not reach one it depends on. Read the *dependency's* logs, not the one that
reported the error. A `down --remove-orphans` followed by `up -d` clears the
stale-network version of this.

**`502 Too many open files`** during a build — your network could not reach
Docker Hub to fetch a base image. Nothing to do with your code. Run the build
again; it usually works within two or three tries.

## Things that are safe vs things that delete data

Safe, do freely:

```bash
docker compose ... down          # removes containers, KEEPS volumes
docker compose ... restart
docker compose ... logs
```

Destroys data — only when you mean it:

```bash
docker compose ... down -v       # -v also deletes volumes → everyone logged out
docker system prune -a           # deletes ALL unused images → 3 GB rebuild
```

`down` is not scary. `down -v` and `prune -a` are the two to think twice about.

## Where things live

| | Where | Survives what |
|---|---|---|
| Your code | the project folder | — |
| Built images | Docker's internal store | deleting the project folder |
| Sessions | volume `cvsync_redis-data` | `down`, restarts, reboots |
| Your secrets | `~/cvsync/cvsync.env` | everything (it is just a file) |

Secrets are **never** inside the images. They are read from the env file each
time a container starts, which is why the images are safe to share and the env
file is not.

## Next steps

- Everyday commands and the move-aside test: `DOCKER.md`
- Putting it on the public internet: `deploy/README.md`
