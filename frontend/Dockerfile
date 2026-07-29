# ── Stage 1: build the static bundle ──────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

# Vite inlines import.meta.env.VITE_* at BUILD time, not runtime, so these
# must be build args — setting them as container env vars has no effect.
ARG VITE_API_URL=http://localhost:4000
ARG VITE_LLM_BRAIN_URL=http://localhost:8000
ARG VITE_CV_BUILDER_URL=http://localhost:3000
ENV VITE_API_URL=$VITE_API_URL \
    VITE_LLM_BRAIN_URL=$VITE_LLM_BRAIN_URL \
    VITE_CV_BUILDER_URL=$VITE_CV_BUILDER_URL

COPY . .
RUN npm run build

# ── Stage 2: serve the built files ────────────────────────────────────────
# nginx would be the better runtime (see nginx.conf, kept for that purpose),
# but docker.io is unreachable from this network — every nginx tag fails to
# resolve through the TLS-inspecting proxy — while node:20-alpine is already
# present locally and the npm registry is reachable. So the static bundle is
# served by `serve`, which also does the SPA history fallback that deep links
# such as /onboarding/profile need.
#
# To move back to nginx once docker.io is reachable, restore the
# `FROM nginx:1.27-alpine` stage that copies dist/ and nginx.conf.
FROM node:20-alpine

WORKDIR /app

RUN npm install -g serve@14

COPY --from=build /app/dist ./dist

EXPOSE 5173

# -s = single-page app: unknown paths fall back to index.html.
CMD ["serve", "-s", "dist", "-l", "5173"]
