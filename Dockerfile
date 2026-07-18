# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.8.17 AS uv-bin

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/app/.venv/bin:$PATH

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app app

WORKDIR /app
COPY --from=uv-bin /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --no-dev \
    && mkdir -p /app/workspace \
    && chown -R app:app /app

USER app
EXPOSE 8000

FROM node:22.17-alpine AS web-build

WORKDIR /web
COPY apps/gui-web/package.json apps/gui-web/package-lock.json ./
RUN npm ci
COPY apps/gui-web/ ./
ARG VITE_DRA_API_BASE_URL=http://127.0.0.1:8000
ENV VITE_DRA_API_BASE_URL=$VITE_DRA_API_BASE_URL
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27.5-alpine AS web

COPY deploy/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=web-build /web/dist /usr/share/nginx/html

USER nginx
EXPOSE 8080
