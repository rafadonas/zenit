FROM node:22-alpine AS dependencies

WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/dashboard/package.json ./apps/dashboard/package.json
RUN npm ci

FROM node:22-alpine AS builder

WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=dependencies /app/node_modules ./node_modules
COPY package.json package-lock.json ./
COPY apps/dashboard ./apps/dashboard
RUN npm run build --workspace=@zenit/dashboard

FROM node:22-alpine AS runtime

WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

RUN addgroup --system zenit && adduser --system --ingroup zenit zenit
COPY --from=builder --chown=zenit:zenit /app/apps/dashboard/.next/standalone ./
COPY --from=builder --chown=zenit:zenit /app/apps/dashboard/.next/static ./apps/dashboard/.next/static

USER zenit
EXPOSE 3000
CMD ["node", "apps/dashboard/server.js"]
