FROM node:22-alpine AS base

RUN apk update && apk upgrade && rm -rf /var/cache/apk/*

WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml ./

FROM base AS dev

RUN pnpm install --frozen-lockfile

EXPOSE 5173

CMD ["pnpm", "exec", "vite", "--host", "0.0.0.0"]

FROM base AS build

RUN pnpm install --frozen-lockfile

COPY . .

ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

RUN pnpm build

FROM nginx:alpine AS prod

RUN apk update && apk upgrade && rm -rf /var/cache/apk/*

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=5s --timeout=5s --start-period=10s --retries=5 \
  CMD wget --no-verbose --tries=1 --spider http://127.0.0.1/ || exit 1
