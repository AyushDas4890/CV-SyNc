#!/usr/bin/env bash
# Tag the four local CV-Sync images and push them to Docker Hub.
#
#   docker login                          # once, interactively — this script won't do it
#   ./scripts/push-to-dockerhub.sh <your-dockerhub-username>
#
# Afterwards, anyone with Docker can run the whole app with no source code:
#   docker compose -f docker-compose.release.yml --env-file cvsync.env up -d
# with the *_IMAGE vars set (the script prints the exact lines to paste).
#
# NOTE: repos created this way are PUBLIC on Docker Hub's free plan. That is
# fine here — the images contain no secrets (every .dockerignore excludes .env,
# and the app reads keys from the environment at start) — but anyone will be
# able to pull them. Do not push if you have added credentials to an image.

set -euo pipefail

USER="${1:-}"
TAG="${2:-latest}"

if [[ -z "$USER" ]]; then
  echo "usage: $0 <dockerhub-username> [tag]" >&2
  exit 1
fi

# Fail early with a clear message rather than a confusing denied-push later.
if ! docker info 2>/dev/null | grep -qi "^ *Username:"; then
  echo "ERROR: not logged in to Docker Hub. Run:  docker login" >&2
  exit 1
fi

SERVICES=(frontend auth-service cv-brain cv-builder)

echo "==> tagging"
for s in "${SERVICES[@]}"; do
  echo "    cvsync/$s:latest  ->  $USER/cvsync-$s:$TAG"
  docker tag "cvsync/$s:latest" "$USER/cvsync-$s:$TAG"
done

echo "==> pushing (cv-builder is ~2.2 GB and will take a while)"
for s in "${SERVICES[@]}"; do
  echo "--- $USER/cvsync-$s:$TAG"
  docker push "$USER/cvsync-$s:$TAG"
done

cat <<EOF

==> done.

Add these lines to your env file (e.g. ~/cvsync/cvsync.env) so compose pulls
from Docker Hub instead of looking for local images:

FRONTEND_IMAGE=$USER/cvsync-frontend
AUTH_IMAGE=$USER/cvsync-auth-service
CVBRAIN_IMAGE=$USER/cvsync-cv-brain
CVBUILDER_IMAGE=$USER/cvsync-cv-builder
CVSYNC_TAG=$TAG

Then on ANY machine with Docker — no source code needed:

  docker compose -f docker-compose.release.yml --env-file cvsync.env up -d

Verify a fresh pull works by removing a local image first:

  docker rmi $USER/cvsync-frontend:$TAG
  docker pull $USER/cvsync-frontend:$TAG
EOF
