# ============================================================
# Clinical AI Copilot — frontend image (Next.js standalone)
#
# Multi-stage build:
#   deps    → install dependencies from the lockfile (npm ci)
#   builder → build Next.js with the public API URL baked in
#   runner  → minimal runtime: standalone server only, non-root
#
# NEXT_PUBLIC_API_URL is a BUILD-TIME value (Next.js inlines public
# env vars into the client bundle at build time). Expected values:
#   - separate API domain:  https://api.example.com/api/v1
#   - same-origin Nginx:    /api/v1   (recommended production setup)
# No .env / .env.local file is ever copied into the image.
# ============================================================

# --- 1. dependencies --------------------------------------------------------
FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# --- 2. build ---------------------------------------------------------------
FROM node:24-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Public API base URL as seen by the BROWSER (baked into the bundle).
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

# --- 3. runtime --------------------------------------------------------------
FROM node:24-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000 \
    NEXT_TELEMETRY_DISABLED=1

# Standalone output contains the traced node_modules + server.js.
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
# Static assets (favicon, etc.) — directory exists but may be empty.
COPY --from=builder /app/public ./public

# Non-root runtime user (built into the node image, uid 1000).
USER node

EXPOSE 3000

CMD ["node", "server.js"]
