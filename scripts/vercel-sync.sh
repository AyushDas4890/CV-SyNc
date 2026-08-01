#!/usr/bin/env bash
#
# Wires the Vercel-hosted frontend to the backends running on this PC.
#
#   ./scripts/vercel-sync.sh
#
# Run it once to set the whole thing up, and again every time the Cloudflare
# quick tunnel hands out a new URL (i.e. after any `docker compose ... restart
# tunnel`, or after rebooting). It is idempotent — running it when nothing
# changed just redeploys the same config.
#
# What it does, in order:
#   1. links ./frontend to a Vercel project (once) and works out its public URL
#   2. brings up the local stack + router + tunnel with that URL baked in
#   3. reads the tunnel's current hostname out of the cloudflared logs
#   4. rewrites frontend/vercel.json so /api/auth/* proxies to that tunnel
#   5. pushes the tunnel URL to Vercel as build-time VITE_* env vars
#   6. deploys to production
#
# Why the URL has to be pushed rather than read at runtime: Vite inlines every
# VITE_* value into the bundle at BUILD time. A new tunnel URL therefore means
# a new build, which is exactly why this is a script and not a checklist.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Paths stay RELATIVE to $ROOT from here on. node, docker and vercel are all
# Windows-native binaries, and Git Bash hands them POSIX paths like
# /c/Users/... which they cannot open. Relative paths work on both platforms.
cd "$ROOT"
ENV_FILE="vercel.env"
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.vercel.yml --env-file "$ENV_FILE")

die() { echo "error: $*" >&2; exit 1; }
step() { echo; echo "==> $*"; }

[ -f "$ENV_FILE" ] || die "$ENV_FILE not found. Copy vercel.env.example to vercel.env and fill it in."

# The vercel CLI is run from inside frontend/ rather than with --cwd, for the
# same POSIX-vs-Windows path reason noted above.
vercel_() { ( cd frontend && vercel "$@" ); }

# ── 1. Vercel project ────────────────────────────────────────────────────
step "Vercel project"

if [ ! -f "frontend/.vercel/project.json" ]; then
  echo "Not linked yet — creating/linking the project."
  # Named explicitly: left to itself the CLI uses the directory name, and a
  # project called "frontend" gets a correspondingly useless production alias.
  vercel_ link --project cv-sync --yes
fi

PROJECT_NAME="$(node -p "require('./frontend/.vercel/project.json').projectName")"
[ -n "$PROJECT_NAME" ] || die "could not read projectName from frontend/.vercel/project.json"

PUBLIC_APP_URL="$(grep -E '^PUBLIC_APP_URL=' "$ENV_FILE" | tail -1 | cut -d= -f2- | tr -d '"' | tr -d "\r" || true)"

# The production alias cannot be guessed. `cv-sync` produced
# `cv-sync-five.vercel.app` here, because Vercel appends a disambiguator when
# the name is taken globally — and it is, for anything short. So on the first
# run, deploy once purely to be told the real alias, then record it. The env
# vars are wrong for this one build; it exists to learn the URL, and the real
# deploy at step 6 fixes them.
if [ -z "$PUBLIC_APP_URL" ]; then
  echo "PUBLIC_APP_URL not set — running a bootstrap deploy to discover the production alias."
  BOOTSTRAP_OUT="$(vercel_ deploy --prod --yes 2>&1 || true)"
  PUBLIC_APP_URL="$(echo "$BOOTSTRAP_OUT" \
    | grep -oE 'Aliased +https://[a-z0-9.-]+\.vercel\.app' \
    | grep -oE 'https://.*' | tail -1 || true)"
  [ -n "$PUBLIC_APP_URL" ] || die "could not find the production alias in the deploy output.
     Look it up at https://vercel.com/dashboard, set PUBLIC_APP_URL in $ENV_FILE, and re-run.
     Deploy output was:
$BOOTSTRAP_OUT"
  printf '\nPUBLIC_APP_URL=%s\n' "$PUBLIC_APP_URL" >> "$ENV_FILE"
  echo "discovered and saved to $ENV_FILE"
fi
echo "project:  $PROJECT_NAME"
echo "app URL:  $PUBLIC_APP_URL"

# ── 2. local stack ───────────────────────────────────────────────────────
step "Starting local stack (redis, cv-builder, cv-brain, auth-service, router, tunnel)"
"${COMPOSE[@]}" up -d

# ── 3. tunnel hostname ───────────────────────────────────────────────────
step "Waiting for the Cloudflare tunnel to publish a hostname"

TUNNEL_URL=""
for _ in $(seq 1 30); do
  TUNNEL_URL="$("${COMPOSE[@]}" logs tunnel 2>/dev/null \
    | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1 || true)"
  [ -n "$TUNNEL_URL" ] && break
  sleep 2
done
[ -n "$TUNNEL_URL" ] || die "no trycloudflare.com URL in the tunnel logs after 60s. Check: ${COMPOSE[*]} logs tunnel"

TUNNEL_HOST="${TUNNEL_URL#https://}"
echo "tunnel:   $TUNNEL_URL"

# Prove the tunnel actually reaches the router and the router reaches cv-brain,
# before spending a Vercel build on a URL that does not work.
step "Checking the tunnel reaches CV_BRAIN"
if ! curl -fsS --max-time 20 "$TUNNEL_URL/api/templates" >/dev/null; then
  die "GET $TUNNEL_URL/api/templates failed. The tunnel is up but the router or cv-brain is not answering.
     Try: ${COMPOSE[*]} ps    and    curl http://localhost:8080/api/templates"
fi
echo "ok"

# ── 4. vercel.json rewrites ──────────────────────────────────────────────
step "Pointing frontend/vercel.json rewrites at $TUNNEL_HOST"
node - "frontend/vercel.json" "$TUNNEL_HOST" <<'NODE'
const fs = require("fs");
const [file, host] = process.argv.slice(2);
const cfg = JSON.parse(fs.readFileSync(file, "utf8"));
// Rewrite the host in place and leave the paths alone, so this works whether
// the file still has the committed placeholder or a previous tunnel's host.
cfg.rewrites = cfg.rewrites.map((r) =>
  r.destination.startsWith("https://")
    ? { ...r, destination: r.destination.replace(/^https:\/\/[^/]+/, `https://${host}`) }
    : r
);
fs.writeFileSync(file, JSON.stringify(cfg, null, 2) + "\n");
NODE
echo "ok"

# ── 5. Vercel env vars ───────────────────────────────────────────────────
step "Pushing build-time env vars to Vercel"

set_env() {
  local name="$1" value="$2"
  # `vercel env add` refuses to overwrite, so remove first. The rm fails when
  # the var was never set, which is fine on a first run.
  vercel_ env rm "$name" production --yes >/dev/null 2>&1 || true
  printf '%s' "$value" | vercel_ env add "$name" production >/dev/null
  echo "  $name = $value"
}

# Auth points at Vercel itself, not the tunnel: those calls carry the session
# cookie, and routing them through the app's own origin keeps that cookie
# first-party. vercel.json rewrites them on to the tunnel server-side.
set_env VITE_API_URL "$PUBLIC_APP_URL"
# Generation and compile go straight to the tunnel, skipping Vercel's proxy —
# /api/generate-cv runs far longer than that proxy will hold a connection open.
set_env VITE_LLM_BRAIN_URL "$TUNNEL_URL"
set_env VITE_CV_BUILDER_URL "$TUNNEL_URL"

# ── 6. deploy ────────────────────────────────────────────────────────────
step "Deploying to production"
vercel_ deploy --prod --yes

step "Verifying $PUBLIC_APP_URL responds"
if curl -fsS -o /dev/null --max-time 20 "$PUBLIC_APP_URL"; then
  echo "ok"
else
  echo "WARNING: $PUBLIC_APP_URL did not respond."
  echo "Vercel may have assigned a different production alias (it appends a"
  echo "suffix when the project name is taken). Find the real one in the deploy"
  echo "output above or at https://vercel.com/dashboard, set it as"
  echo "PUBLIC_APP_URL in vercel.env, and re-run this script."
fi

cat <<EOF

──────────────────────────────────────────────────────────────────────────
Done.

  App          $PUBLIC_APP_URL
  Tunnel       $TUNNEL_URL   (rotates on restart — re-run this script)

One-time, if you have not done it already: set the GitHub OAuth App callback
URL at https://github.com/settings/developers to EXACTLY

  $PUBLIC_APP_URL/api/auth/github/callback

That URL is stable, so this is genuinely one-time even though the tunnel
hostname keeps changing.
──────────────────────────────────────────────────────────────────────────
EOF
