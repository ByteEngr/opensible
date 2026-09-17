# Frontend — Vite/React SPA served via nginx
# Build context: repo root  (docker build -f Dockerfile .)

# ---------- build stage ----------
# oven/bun publishes no Alpine-version-suffixed tag; this is Alpine 3.22.5 today.
FROM oven/bun:1 AS builder
WORKDIR /app

# Install deps first for better layer caching
COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile || bun install

# Copy source, build scripts, and blueprint definitions
COPY tsconfig.json vite.config.ts index.html ./
COPY public ./public
COPY src ./src
COPY scripts ./scripts
COPY IaC/blueprints ./IaC/blueprints

RUN bun run build

# ---------- runtime stage ----------
FROM nginx:1.29-alpine-slim

COPY nginx-docker.conf /etc/nginx/templates/default.conf.template
COPY docker-entrypoint.sh /docker-entrypoint-frontend.sh
RUN chmod +x /docker-entrypoint-frontend.sh

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
ENTRYPOINT ["/docker-entrypoint-frontend.sh"]
CMD ["nginx", "-g", "daemon off;"]
