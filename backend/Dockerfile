# Lightweight single-stage build (no heavy ML deps)
FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV UV_NO_PROGRESS=1

# Copy dependency files first (better cache)
COPY pyproject.toml uv.lock .python-version ./

# Copy application code so uv sync can resolve dependencies
COPY . .

# Install dependencies using uv sync (respects uv.lock)
RUN uv sync --frozen --no-cache

RUN mkdir -p /app/uploads

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
