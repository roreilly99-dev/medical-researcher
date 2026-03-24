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

# Install dependencies
RUN uv venv /app/.venv && \
    uv sync --frozen --no-install-project --no-cache

# Copy application code
COPY . .

RUN mkdir -p /app/uploads

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
