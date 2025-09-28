"""MCP tools for the Qt 4.8.4 Docs server."""

from __future__ import annotations

import asyncio
from typing import Optional

from mcp.server.fastmcp.exceptions import ToolError

from .server import mcp
from .cache import LRUCache, CachedDoc
from .config import Settings, load_settings
from .doc_service import get_markdown_for_url
from .errors import (
    DocumentationError,
    FetchError,
    TimeoutDocumentationError,
)


_settings: Settings | None = None
_md_lru: Optional[LRUCache] = None


def configure_from_settings(settings: Settings) -> None:
    """Initialize cached settings and LRU cache sizing."""
    global _settings, _md_lru
    _settings = settings
    _md_lru = LRUCache(settings.md_cache_size)


def _get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def _get_lru() -> LRUCache:
    global _md_lru
    if _md_lru is None:
        settings = _get_settings()
        _md_lru = LRUCache(settings.md_cache_size)
    return _md_lru


def _format_result(doc: CachedDoc, url: str, *, start_index: int | None, max_length: int | None) -> dict:
    markdown = doc.markdown
    if start_index is not None or max_length is not None:
        start = max(0, start_index or 0)
        if max_length is not None and max_length >= 0:
            markdown = markdown[start : start + max_length]
        else:
            markdown = markdown[start:]
    clean_attr = "Content © The Qt Company Ltd./Digia — GNU Free Documentation License 1.3"
    return {
        "title": doc.title,
        "url": url,
        "canonical_url": doc.canonical_url,
        "markdown": markdown,
        "attribution": clean_attr,
        "links": [dict(link) for link in doc.links],
    }


@mcp.tool()
async def read_documentation(
    url: str,
    fragment: str | None = None,
    section_only: bool = False,
    start_index: int | None = None,
    max_length: int | None = None,
) -> dict:
    """Fetch a Qt 4.8.4 docs page and return Markdown."""
    settings = _get_settings()
    lru = _get_lru()

    try:
        doc = get_markdown_for_url(
            url,
            settings,
            lru,
            fragment=fragment,
            section_only=section_only,
        )
    except DocumentationError as exc:
        raise ToolError(exc.tool_message()) from exc
    except (asyncio.TimeoutError, TimeoutError) as exc:  # pragma: no cover - defensive
        err = TimeoutDocumentationError("Timed out fetching documentation")
        raise ToolError(err.tool_message()) from exc
    except Exception as exc:  # pragma: no cover - unexpected failure
        err = FetchError(f"Unexpected error: {exc}")
        raise ToolError(err.tool_message()) from exc

    return _format_result(doc, url, start_index=start_index, max_length=max_length)
