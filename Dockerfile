# Multi-stage build for the Qt Documentation MCP Server
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install locked dependencies first so source edits reuse this layer
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --no-editable

# Then install the project itself (README and LICENSE are referenced by
# pyproject.toml metadata)
COPY src/ ./src/
COPY README.md LICENSE ./
RUN uv sync --locked --no-dev --no-editable

# Production stage
FROM python:3.13-slim AS runtime

# SERVER_HOST binds 0.0.0.0 so the server is reachable from outside the
# container; QT_DOC_BASE and QT_DOC_STATE_DIR point at the two mount
# points. Override any of these with -e or an env file.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    SERVER_HOST=0.0.0.0 \
    SERVER_PORT=8000 \
    QT_DOC_BASE=/docs \
    QT_DOC_STATE_DIR=/data

# curl is needed by the container healthcheck
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

WORKDIR /app

# /docs: read-only Qt HTML documentation (required mount)
# /data: derived state (Markdown cache + FTS index), persist via volume
RUN mkdir -p /docs /data && \
    chown appuser:appuser /data

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
    CMD curl -f http://localhost:${SERVER_PORT:-8000}/health || exit 1

# Informational only; override with SERVER_PORT env var
EXPOSE 8000

CMD ["qt4-doc-mcp-server"]
