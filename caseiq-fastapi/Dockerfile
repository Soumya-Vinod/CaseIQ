FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root runtime user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# 8000 is the local-dev/docker-compose default (EXPOSE is documentation --
# it doesn't restrict what the process actually binds to). Render injects
# its own PORT env var at runtime and a hardcoded --port 8000 fails Render's
# health checks, since Render proxies to whatever port IT chose, not 8000 --
# ${PORT:-8000} binds to Render's port when PORT is set, falls back to 8000
# for plain `docker run` with no PORT set. Needs shell form (no JSON-array
# CMD) for that expansion to happen at all.
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD curl -fsS http://localhost:${PORT:-8000}/health || exit 1

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
