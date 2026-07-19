"""MCP entry point for the active local Qt Documentation MCP Server.

Implements MCP using FastMCP with streamable HTTP (the default) or stdio
transport. The HTTP variant exposes a /health route via FastMCP custom routing.
"""
from __future__ import annotations

import argparse
import logging
import os

if __package__ in (None, ""):
    # Allow running this module as a script (python path fix)
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    __package__ = "qt4_doc_mcp_server"

from dotenv import load_dotenv

from .config import (
    ensure_dirs,
    index_db_path,
    load_settings,
    probe_fts5,
    validate_settings,
)
from .server import ensure_tools_loaded, mcp
from .tools import configure_from_settings


logger = logging.getLogger(__name__)

# Ensure MCP tools are registered even when imported via alternate entry points.
ensure_tools_loaded()


@mcp.custom_route("/health", methods=["GET"])
async def health(request):  # noqa: ARG001 (unused)
    from starlette.responses import JSONResponse

    return JSONResponse({"status": "ok", "service": "qt4_doc_mcp_server"})


# Export ASGI app for hosting/testing
app = mcp.streamable_http_app()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local Qt documentation MCP server")
    parser.add_argument(
        "--transport",
        choices=("streamable-http", "stdio"),
        default="streamable-http",
        help="MCP transport to use (default: streamable-http)",
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> None:
    """Console entry: launch FastMCP over streamable HTTP or stdio."""
    args = _parse_args(argv)

    # Load .env from repo root if present
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

    # Load and validate settings
    settings = load_settings()
    ok, warns = validate_settings(settings)
    for w in warns:
        logger.warning(w)
    if not ok:
        logger.error("Startup validation failed; fix settings and retry.")
        raise SystemExit(2)

    ensure_dirs(settings)
    configure_from_settings(settings)

    # Probe FTS5 and warn if unavailable
    if not probe_fts5():
        logger.warning("SQLite FTS5 not available; search indexing will not work.")

    # Build first: a successful rebuild clears Markdown derived from an older
    # source snapshot before any optional cache warmup runs.
    if settings.preindex_docs:
        try:
            from .cli import build_index_main
            from .search import index_is_current

            if not index_is_current(index_db_path(settings)):
                logger.info("PREINDEX_DOCS=true: building search index before start...")
                rc = build_index_main([])
                if rc != 0:
                    logger.warning("Index build exited with code %s", rc)
            else:
                logger.info("Search index already exists at %s", index_db_path(settings))
        except Exception as e:
            logger.warning("Index build failed: %s", e)

    # Optionally preconvert Markdown store at startup.
    if settings.preconvert_md:
        try:
            from .cli import warm_md_main

            logger.info("PRECONVERT_MD=true: checking Markdown cache before start...")
            rc = warm_md_main([])
            if rc != 0:
                logger.warning("Markdown preconversion exited with code %s", rc)
        except Exception as e:
            logger.warning("Markdown preconversion failed: %s", e)

    level = settings.mcp_log_level.upper()
    logging.basicConfig(level=getattr(logging, level, logging.WARNING))

    if args.transport == "streamable-http":
        mcp.settings.host = settings.server_host
        mcp.settings.port = settings.server_port
        mcp.settings.stateless_http = True
        logger.info(
            "Starting MCP server (streamable-http) on %s:%s",
            mcp.settings.host,
            mcp.settings.port,
        )
    else:
        logger.info("Starting MCP server over stdio")

    try:
        registered = list(getattr(mcp._tool_manager, "_tools", {}).keys())
        logger.info("Registered MCP tools: %s", registered)
    except Exception as exc:  # pragma: no cover
        logger.debug("Unable to introspect tool registry: %s", exc)

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    # Allow running via: `python src/qt4_doc_mcp_server/main.py`
    run()
