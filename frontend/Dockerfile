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

# ── Stage 2: serve it ─────────────────────────────────────────────────────
# The previous image ran `npx vite` — the dev server. No minification, no
# cache headers, an HMR websocket, and explicitly not for production use.
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 5173

CMD ["nginx", "-g", "daemon off;"]
