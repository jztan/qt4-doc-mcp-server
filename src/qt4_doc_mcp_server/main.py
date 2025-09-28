"""MCP entry point for the Qt 4.8.4 Documentation MCP Server.

Implements MCP using the FastMCP server with streamable HTTP transport
(stateless). Exposes a /health route via FastMCP custom routing.
"""
from __future__ import annotations

import logging
import os

if __package__ in (None, ""):
    # Allow running this module as a script (python path fix)
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    __package__ = "qt4_doc_mcp_server"

from dotenv import load_dotenv

from .config import load_settings, ensure_dirs, validate_settings, probe_fts5
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


def run() -> None:
    """Console entry: launch FastMCP with streamable HTTP transport."""
    # Load .env from repo root if present
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

    # Load and validate settings
    settings = load_settings()
    ensure_dirs(settings)

    ok, warns = validate_settings(settings)
    for w in warns:
        logger.warning(w)
    if not ok:
        logger.error("Startup validation failed; fix settings and retry.")
        raise SystemExit(2)

    configure_from_settings(settings)

    # Probe FTS5 and warn if unavailable
    if not probe_fts5():
        logger.warning("SQLite FTS5 not available; search indexing will not work.")

    # Optionally preconvert Markdown store at startup
    if settings.preconvert_md:
        try:
            from .cli import warm_md_main

            logger.info("PRECONVERT_MD=true: warming Markdown store before start...")
            rc = warm_md_main([])
            if rc != 0:
                logger.warning("Markdown preconversion exited with code %s", rc)
        except Exception as e:
            logger.warning("Markdown preconversion failed: %s", e)

    # Configure FastMCP settings
    mcp.settings.host = settings.server_host
    mcp.settings.port = settings.server_port
    mcp.settings.stateless_http = True

    level = settings.mcp_log_level.upper()
    logging.basicConfig(level=getattr(logging, level, logging.WARNING))
    logger.info(
        "Starting MCP server (streamable-http) on %s:%s",
        mcp.settings.host,
        mcp.settings.port,
    )

    try:
        registered = list(getattr(mcp._tool_manager, "_tools", {}).keys())
        logger.info("Registered MCP tools: %s", registered)
    except Exception as exc:  # pragma: no cover
        logger.debug("Unable to introspect tool registry: %s", exc)

    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    # Allow running via: `python src/qt4_doc_mcp_server/main.py`
    run()
