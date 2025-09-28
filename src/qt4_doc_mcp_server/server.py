from __future__ import annotations

import importlib
import logging
import sys

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("qt4_doc_mcp_server")


def ensure_tools_loaded() -> None:
    """Ensure built-in MCP tools are imported and registered."""
    module_name = "qt4_doc_mcp_server.tools"
    if module_name in sys.modules:
        return
    try:
        importlib.import_module(module_name)
    except Exception:  # pragma: no cover - import-time failure
        logger.exception("Failed to import MCP tools: %s", module_name)
        raise


# Load tools at import so any entry point using mcp has them registered.
ensure_tools_loaded()
