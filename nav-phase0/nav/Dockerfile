# syntax=docker/dockerfile:1
#
# N.A.V. API and Celery worker. One image, two commands.
#
# This sits at the repository root because that is where every platform looks
# by default (Render, Railway, Fly, Cloud Run). Paths below are relative to the
# repository root, so `docker build .` works with no extra configuration.
#
# The console has its own Dockerfile at apps/web/Dockerfile.
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv/api

# Build tools are needed for wheels that have no manylinux build, then removed.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Only two paths are copied. Migrations live inside app/, so there is no
# separate directory that can be missing from a checkout.
COPY apps/api/pyproject.toml apps/api/alembic.ini ./
COPY apps/api/app ./app
RUN pip install --no-cache-dir . \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y

# The application never runs as root.
RUN useradd --system --create-home --uid 10001 nav \
    && chown -R nav:nav /srv/api
USER nav

EXPOSE 8000
# The entry point is a module inside the package copied above, so there is no
# loose script to commit, chmod, or keep free of CRLF line endings.
ENTRYPOINT ["python", "-m", "app.cli.entrypoint"]
# Shell form so a platform-injected $PORT (Render, Fly, Cloud Run) wins;
# locally and in compose it falls back to 8000.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
