#!/usr/bin/env bash
# Shared pip-audit invocation. Used by:
#   - .github/workflows/pr-tests.yml
#   - .github/workflows/publish-pypi.yml
#   - scripts/release.py (preflight)
#
# Audits the project's resolved runtime dependency tree (what
# `pip install qt4-doc-mcp-server` ships), not the ambient Python
# environment. Auditing the live interpreter is fragile: a uv-managed
# .venv has no pip, so bare `pip-audit` silently falls back to whatever
# global Python is on PATH and audits unrelated packages.
#
# This repo does not commit uv.lock, so pins are compiled from
# pyproject.toml at audit time. That means the audit tracks the newest
# versions the constraints allow, which is exactly what a fresh
# `pip install` would get.
#
# Keep the ignore list here, in one place, so local preflight and CI
# cannot drift.
set -eo pipefail

cd "$(dirname "$0")/.."

req="$(mktemp)"
trap 'rm -f "$req"' EXIT
uv pip compile --quiet pyproject.toml -o "$req"

# --disable-pip: the compiled file is already a fully pinned transitive
# closure, so pip-audit must not build a virtualenv to re-resolve it.
exec uvx pip-audit --disable-pip --no-deps --requirement "$req" "$@"
