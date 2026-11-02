# Стадия 1: сборка Mini App
FROM node:22-alpine AS webapp
WORKDIR /webapp
COPY webapp/package.json webapp/package-lock.json ./
RUN npm ci
COPY webapp/ ./
RUN npm run build

# Стадия 2: backend (бот + API) и статика Mini App
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0

WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/ ./
COPY --from=webapp /webapp/dist ./static

RUN useradd --create-home appuser
USER appuser

# PORT задаёт хостинг. Миграции — перед запуском: на бесплатном Render нет pre-deploy.
# Повторный запуск alembic безопасен, на Railway их же выполняет preDeployCommand
CMD ["sh", "-c", "alembic upgrade head && exec python -m app.main"]
