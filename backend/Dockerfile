# Hintro Meeting Intelligence API
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# uv for fast, reproducible dependency installs.
RUN pip install --no-cache-dir uv

# Install dependencies first for better layer caching.
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project || uv sync --no-dev

# Application code.
COPY . .

EXPOSE 8000

# Run migrations, then start the server. PORT is provided by the platform (Render).
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
