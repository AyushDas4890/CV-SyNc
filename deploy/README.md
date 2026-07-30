# Deploying CV-Sync so you can reach it from anywhere

Two ways, depending on whether you want a permanent URL or just to reach it now.

| | Quick tunnel | Server deploy |
|---|---|---|
| Public HTTPS URL | yes (random or your domain) | yes (your domain) |
| Runs on | your own PC (must stay on) | a VPS, always on |
| Cost | free | ~$5–7/month |
| Setup time | ~10 min | ~45 min |
| Good for | showing someone today | actually using it |

## Why not Vercel

Vercel runs serverless functions with a ~4.5 GB deploy ceiling and short
execution limits. `cvsync/cv-builder` is a **2.2 GB TeX Live image** that
shells out to `latexmk` and can take 15–60 s per compile. It does not fit that
model. Render, Railway and Fly.io all run Docker containers and can host it —
Render's free tier spins down after inactivity, so a cold LaTeX compile will
be slow. A plain VPS is cheaper and more predictable, which is what the compose
file here targets.

---

## Option A — quick tunnel (fastest)

Keep the stack running on your PC exactly as it is now and expose it with
Cloudflare Tunnel. Free, real HTTPS, no port forwarding, no firewall changes.

```bash
# One-off, no account needed — gives a random trycloudflare.com URL
docker run --rm --network host cloudflare/cloudflared:latest \
  tunnel --url http://localhost:5173
```

It prints a `https://<random>.trycloudflare.com` URL.

**This alone will not work**, and it is worth understanding why: the page loads,
but every API call fails. The frontend bundle has `http://localhost:4000` baked
in, and on a visitor's machine `localhost` is *their* computer. You must rebuild
the frontend against the tunnel URLs and run tunnels for all four services —
which is why the named-domain setup below is less work overall for anything
beyond a one-minute demo.

For a persistent named tunnel with your own domain, see
<https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/>.

---

## Option B — server deploy (recommended)

One small VPS (Hetzner CX22, DigitalOcean, Vultr — 2 vCPU / 4 GB is plenty),
Docker, and Caddy for automatic HTTPS. Files in this folder:
`docker-compose.deploy.yml` and `Caddyfile`.

### 1. DNS

Point four A records at the server's public IP:

```
app.example.com     -> 203.0.113.10
api.example.com     -> 203.0.113.10
brain.example.com   -> 203.0.113.10
build.example.com   -> 203.0.113.10
```

Subdomains of **one** domain matter: `app.` and `api.` are same-site, so the
session cookie works with `SameSite=Lax`. Two different domains would force
`SameSite=None`, which more browsers and privacy settings interfere with.

### 2. Rebuild the frontend with public URLs

Do this **on your PC**, before shipping the images. Vite inlines `VITE_*` at
build time — this cannot be fixed later with an env var.

```bash
cd "/c/Users/ayush/Claude/Projects/CV SYNC"
docker compose build \
  --build-arg VITE_API_URL=https://api.example.com \
  --build-arg VITE_LLM_BRAIN_URL=https://brain.example.com \
  --build-arg VITE_CV_BUILDER_URL=https://build.example.com \
  frontend
```

### 3. Get the images onto the server

```bash
# On your PC (~3 GB, mostly TeX Live)
docker save -o cvsync-images.tar \
  cvsync/frontend:latest cvsync/auth-service:latest \
  cvsync/cv-brain:latest cvsync/cv-builder:latest \
  redis:7-alpine caddy:2-alpine
scp cvsync-images.tar deploy/docker-compose.deploy.yml deploy/Caddyfile user@server:~/cvsync/

# On the server
cd ~/cvsync && docker load -i cvsync-images.tar
```

Alternative: push to GHCR (`docker tag` + `docker push ghcr.io/ayushdas4890/...`)
and let the server pull. Better if you will redeploy often.

### 4. GitHub OAuth App

At <https://github.com/settings/developers>, set the callback URL to **exactly**:

```
https://api.example.com/api/auth/github/callback
```

A mismatch here is the single most common cause of a login that dies on
redirect.

### 5. Env file on the server

```bash
# ~/cvsync/cvsync.env
ACME_EMAIL=you@example.com
PUBLIC_APP_URL=https://app.example.com
GITHUB_CALLBACK_URL=https://api.example.com/api/auth/github/callback
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
SESSION_SECRET=<openssl rand -hex 32>
OPENAI_API_KEY=...
GROQ_API_KEY=...
```

`chmod 600 cvsync.env`. Set both LLM keys — OpenAI is primary, Groq is the
fallback, and with only one you have no cushion when it rate-limits.

### 6. Edit the Caddyfile and start

Replace `example.com` with your domain in `Caddyfile`, then:

```bash
cd ~/cvsync
docker compose -f docker-compose.deploy.yml --env-file cvsync.env up -d
docker compose -f docker-compose.deploy.yml logs -f caddy   # watch cert issuance
```

Certificates are issued on first request per hostname. Open
`https://app.example.com`.

### 7. Firewall

Only 80 and 443 need to be open. The app services use `expose:`, not `ports:`,
so they are reachable only through Caddy — never directly from the internet.

```bash
sudo ufw allow 80,443/tcp && sudo ufw enable
```

---

## Read this before you rely on it

**User data is lost on every restart.** `auth-service` keeps users and their
profile/education data in an **in-memory store** (`userStore.service.js`; see
`kb/02`). Sessions live in Redis and survive, but the user records they point
at do not — so a redeploy or crash logs everyone out and drops saved profiles.
This is fine for a demo and wrong for real users. Backing it with a real
database is the prerequisite for calling this production.

**`build.example.com` is public CPU.** Anyone who finds it can submit LaTeX and
make your server compile it. It is sandboxed — `-no-shell-escape`,
`openin_any/openout_any=p`, 60 s timeout, job dir deleted after — but there is
no rate limit, because stock Caddy has no `rate_limit` directive. Put
Cloudflare's free tier in front and rate-limit `/api/compile`, or build Caddy
with the `caddy-ratelimit` plugin (recipe is in the `Caddyfile` comments).

**LLM keys are spendable.** `ALLOWED_ORIGINS` is pinned to your frontend origin
so a browser on another site cannot call `/api/generate-cv` — but CORS does not
stop `curl`. There is no auth on the generate endpoint. Watch your usage, and
put real authentication in front of it before sharing the URL widely.

**Sizing.** A LaTeX compile is CPU-heavy and page-fitting runs up to 3 compiles
plus LLM calls per CV. 2 vCPU handles a handful of concurrent users; it is not
a scale-out design.

## Updating a deployed instance

```bash
# On your PC: rebuild, re-save, copy over
docker compose build && docker save -o cvsync-images.tar cvsync/...
scp cvsync-images.tar user@server:~/cvsync/

# On the server
docker load -i cvsync-images.tar
docker compose -f docker-compose.deploy.yml --env-file cvsync.env up -d
```

Compose recreates only the containers whose image changed. Redis and the Caddy
certificate volumes are untouched, so nobody is logged out by the deploy itself
(they will be by the in-memory store above).
