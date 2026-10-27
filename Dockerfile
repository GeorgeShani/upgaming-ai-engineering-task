FROM node:24-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /bin/
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken-cache
RUN uv run --frozen --no-dev python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"
COPY backend/ ./backend/
COPY --from=frontend /build/dist ./frontend/dist
EXPOSE 8000
CMD ["sh", "-c", "exec uv run --frozen --no-dev uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000}"]
