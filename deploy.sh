#!/bin/bash
# Build and deploy the Qt Documentation MCP Server with docker compose.
# Checks prerequisites, bootstraps .env.docker on first run, then starts
# the service and waits for the health endpoint.

set -euo pipefail
cd "$(dirname "$0")"

HEALTH_TIMEOUT=300  # seconds; first start indexes the docs before serving

if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Start Docker first." >&2
    exit 1
fi

if [ ! -f .env.docker ]; then
    cp .env.docker.example .env.docker
    echo "Created .env.docker from .env.docker.example"
fi

# Resolve the docs path the compose file will mount (default matches compose)
docs_path=$(grep -E '^QT_DOC_HTML_PATH=' .env.docker | tail -1 | cut -d= -f2- || true)
docs_path=${docs_path:-./qt4-docs-html}

# Resolve the published host port (default matches compose)
host_port=$(grep -E '^HOST_PORT=' .env.docker | tail -1 | cut -d= -f2- || true)
host_port=${host_port:-8000}
HEALTH_URL="http://127.0.0.1:${host_port}/health"
if [ ! -d "$docs_path" ]; then
    echo "Qt docs directory not found: $docs_path" >&2
    echo "Prepare docs with: python scripts/prepare_qt48_docs.py --segments 4" >&2
    echo "or set QT_DOC_HTML_PATH in .env.docker to your Qt doc/html path." >&2
    exit 1
fi

echo "Building and starting qt4-doc-mcp-server..."
docker compose --env-file .env.docker up -d --build

printf "Waiting for %s " "$HEALTH_URL"
elapsed=0
until curl -sf "$HEALTH_URL" > /dev/null 2>&1; do
    if [ "$elapsed" -ge "$HEALTH_TIMEOUT" ]; then
        printf "\n"
        echo "Server did not become healthy within ${HEALTH_TIMEOUT}s." >&2
        echo "Check logs with: docker compose logs -f" >&2
        exit 1
    fi
    sleep 5
    elapsed=$((elapsed + 5))
    printf "."
done
printf "\n"

echo "Server is healthy: $(curl -sf "$HEALTH_URL")"
echo "MCP endpoint: http://127.0.0.1:${host_port}/mcp"
