# syntax=docker/dockerfile:1
# Built from the repository root so the npm workspace (and @nav/shared-types)
# resolves the same way it does locally.
FROM node:22-alpine AS deps
WORKDIR /srv
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY packages/shared-types/package.json packages/shared-types/package.json
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /srv
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /srv/node_modules ./node_modules
COPY --from=deps /srv/apps/web/node_modules ./apps/web/node_modules
COPY package.json package-lock.json ./
COPY packages ./packages
COPY apps/web ./apps/web
RUN npm run build --workspace=@nav/web

FROM node:22-alpine AS runner
WORKDIR /srv
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 10002 nav && adduser --system --uid 10002 nav

# `output: standalone` emits only the files the server actually needs.
COPY --from=builder --chown=nav:nav /srv/apps/web/.next/standalone ./
COPY --from=builder --chown=nav:nav /srv/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=nav:nav /srv/apps/web/public ./apps/web/public

USER nav
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
