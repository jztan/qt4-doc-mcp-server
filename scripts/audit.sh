#!/usr/bin/env bash
# Shared pip-audit invocation. Used by:
#   - .github/workflows/pr-tests.yml
#   - .github/workflows/publish-pypi.yml
#   - scripts/release.py (preflight)
#
# Audits the project's LOCKED runtime dependency tree (what
# `pip install qt4-doc-mcp-server` actually ships), NOT the ambient Python
# environment. Auditing the live interpreter is fragile: a uv-managed
# .venv has no pip, so bare `pip-audit` silently falls back to whatever
# global Python is on PATH and audits unrelated packages. Exporting the
# lockfile makes the gate deterministic and identical locally and in CI.
#
# Keep the ignore list here, in one place, so local preflight and CI
# cannot drift.
set -eo pipefail

cd "$(dirname "$0")/.."

req="$(mktemp)"
trap 'rm -f "$req"' EXIT
uv export --frozen --no-dev --no-emit-project --format requirements-txt -o "$req"

# --disable-pip: the exported lockfile is fully pinned and hashed, so
# pip-audit must not build a virtualenv to re-resolve it.
exec uvx pip-audit --disable-pip --requirement "$req" "$@"
