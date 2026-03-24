FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Skip bytecode compilation to speed up build
ENV UV_COMPILE_BYTECODE=0
# Use the project's virtual environment
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
# Disable progress for faster CI builds
ENV UV_NO_PROGRESS=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifests first (better layer caching)
COPY pyproject.toml uv.lock .python-version ./

# Install dependencies - use --no-cache to reduce memory, parallel jobs
RUN uv sync --frozen --no-install-project --no-cache

COPY . .

RUN mkdir -p /app/uploads

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
