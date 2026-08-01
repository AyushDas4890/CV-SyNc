# Frontend on Vercel, backends on your PC

Public HTTPS URL you can send to anyone, while the LaTeX compiler and the LLM
calls keep running on your machine. No VPS, no domain, no signup beyond the
Vercel account you already have.

The catch is that your PC has to be on, with the stack running, for the app to
work. Close the laptop and the site loads but every button fails.

## Setup

```bash
cp vercel.env.example vercel.env
# fill in SESSION_SECRET, GITHUB_CLIENT_ID/SECRET, and an LLM key
./scripts/vercel-sync.sh
```

The script prints a GitHub OAuth callback URL at the end. Paste it into your
OAuth App at <https://github.com/settings/developers> once and you are done —
that URL never changes, even though the tunnel's does.

**Re-run `./scripts/vercel-sync.sh` after every reboot or tunnel restart.** The
Cloudflare quick tunnel gets a new random hostname each time it starts, and the
frontend has that hostname compiled into its bundle.

## How it fits together

```
                    ┌──────────────────── your PC ────────────────────┐
                    │                                                 │
browser ──┬── https://<app>.vercel.app         (static SPA, Vercel)   │
          │              │                                            │
          │              └── /api/auth/*  ──rewrite──┐                │
          │                 /api/profile             │                │
          │                                          ▼                │
          │                                    cloudflared            │
          └── https://<random>.trycloudflare.com ────┤                │
                 /api/generate-cv                    ▼                │
                 /api/compile                    Caddy :8080          │
                 /api/templates                      │                │
                    │                    ┌───────────┼───────────┐    │
                    │                    ▼           ▼           ▼    │
                    │              auth-service   cv-brain   cv-builder
                    │                 :4000        :8000       :3000  │
                    │                    │                       ▲    │
                    │                  redis                     │    │
                    │                              page-fit compiles  │
                    │                              stay internal ─────┘
                    └─────────────────────────────────────────────────┘
```

Two paths into the same tunnel, and the split is deliberate.

## Why auth goes through Vercel but generation does not

**Auth takes the long way round** because of the session cookie and the OAuth
callback.

Routed through the Vercel origin, the cookie is first-party — `SameSite=Lax`
holds, there is no CORS preflight, and no browser privacy setting drops it.
More importantly the GitHub OAuth App's callback URL becomes
`https://<app>.vercel.app/api/auth/github/callback`, which is **stable**. Point
it at the tunnel instead and you would be editing your OAuth App by hand every
time the tunnel restarts. These are short requests, so Vercel's proxy is a fine
place for them.

**Generation and compile go straight to the tunnel** because they are slow.
[kb/09](../../kb/09-page-fitting-and-structure-review.md) measured
`/api/generate-cv` at **55–95 s**. Vercel's proxy will not hold a connection
open that long, so routing it through the rewrite would fail after the LLM
credits were already spent. Neither call carries a cookie — cv-brain has no
session of its own and `api.js` deliberately omits `credentials: include` — so
going cross-origin costs nothing here. Plain CORS covers it.

## Why one tunnel and not three

A quick tunnel points at exactly one port, and the browser needs three
services. Caddy fronts all three on `:8080` and splits by path, so there is one
hostname to keep in sync instead of three.

That routing is not purely mechanical. **`/api/templates` is served by both
cv-brain and cv-builder** — the frontend wants cv-brain's, because those
responses carry the `brainId` values `/api/generate-cv` accepts.
[the Caddyfile](Caddyfile) pins it there. Nothing in the browser needs
cv-builder's copy; cv-brain reaches that one over the internal Docker network.

## Page fitting is off

`docker-compose.vercel.yml` sets `ENABLE_PAGE_FIT=false`.

Cloudflare terminates any request over **100 s** on the free plan, and
generation with page fitting on measured 55–95 s — inside the limit on a good
run, over it on a slow one. That failure mode is the nasty kind: the CV
generates fine, the credits are spent, and the user still sees an error,
because the proxy hung up before the response came back. Intermittent, and it
looks random.

With page fitting off, generation lands around 30–45 s with real margin. The
cost is that the CV is no longer held to a whole page count.

To get it back, move the brain onto a tunnel with no cap — ngrok and Tailscale
Funnel both qualify, and Cloudflare's own docs recommend moving long requests
off their proxy — then set `ENABLE_PAGE_FIT=true`. The proper fix is making
generation async (job id + poll), which is also the most work.

## Known limitation

auth-service keeps users and profiles in an **in-memory store**
(see [kb/02](../../kb/02-auth-service.md)). Sessions live in Redis and survive a
restart, but the user records they point at do not. Every `docker compose down`
logs everyone out and drops saved profile and education data.

## Troubleshooting

**Login redirects, then immediately logged out.** The session cookie was not
issued. Almost always the GitHub OAuth App callback URL not matching
`$PUBLIC_APP_URL/api/auth/github/callback` character for character.

**Every API call fails with CORS errors after a reboot.** The tunnel rotated.
Re-run `./scripts/vercel-sync.sh`.

**`/api/generate-cv` returns 524.** The request passed 100 s. Confirm
`ENABLE_PAGE_FIT` is `false`, or move to an uncapped tunnel.

**Check the layers in order** — this narrows it fast:

```bash
curl http://localhost:8000/api/templates            # cv-brain itself
curl http://localhost:8080/api/templates            # + the Caddy router
curl https://<tunnel>.trycloudflare.com/api/templates   # + the tunnel
curl https://<app>.vercel.app/api/auth/me           # + the Vercel rewrite
```
