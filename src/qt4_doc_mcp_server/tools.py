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
from .search import search, SearchUnavailable, IndexError as SearchIndexError


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
    total_length = len(markdown)
    truncated = False
    
    if start_index is not None or max_length is not None:
        start = max(0, start_index or 0)
        if max_length is not None and max_length >= 0:
            markdown = markdown[start : start + max_length]
            truncated = (start + max_length) < total_length
        else:
            markdown = markdown[start:]
            truncated = start > 0
    
    clean_attr = "Content © The Qt Company Ltd./Digia — GNU Free Documentation License 1.3"
    result = {
        "title": doc.title,
        "url": url,
        "canonical_url": doc.canonical_url,
        "markdown": markdown,
        "attribution": clean_attr,
        "links": [dict(link) for link in doc.links],
    }
    
    # Add pagination metadata when content is truncated
    if truncated or start_index is not None or max_length is not None:
        result["content_info"] = {
            "total_length": total_length,
            "returned_length": len(markdown),
            "start_index": start_index or 0,
            "truncated": truncated,
        }
    
    return result


@mcp.tool()
async def read_documentation(
    url: str,
    fragment: str | None = None,
    section_only: bool = False,
    start_index: int | None = None,
    max_length: int | None = None,
) -> dict:
    """Fetch a Qt 4.8.4 docs page and return Markdown.
    
    Args:
        url: Qt documentation URL
        fragment: Optional HTML fragment (e.g., '#details')
        section_only: If True with fragment, return only that section
        start_index: Character offset to start from (for pagination)
        max_length: Maximum characters to return (defaults to configured limit)
    
    Returns:
        Dictionary with title, url, markdown, links, and pagination info
    """
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

    # Apply default max_length if not explicitly provided
    effective_max_length = max_length
    if effective_max_length is None:
        effective_max_length = settings.default_max_markdown_length

    return _format_result(doc, url, start_index=start_index, max_length=effective_max_length)


@mcp.tool()
async def search_documentation(
    query: str,
    limit: int = 10,
    scope: str = "all",
) -> dict:
    """Search Qt 4.8.4 documentation for relevant pages.

    Args:
        query: Search terms (FTS5 query syntax supported)
        limit: Maximum number of results to return (default: 10, max: 50)
        scope: Search scope - 'all', 'api', or 'guides' (currently 'all' only)

    Returns:
        Dictionary with results array containing title, url, score, and context snippet
    """
    settings = _get_settings()

    # Validate and clamp limit
    if limit < 1:
        limit = 10
    elif limit > 50:
        limit = 50

    # Validate scope (currently only 'all' is implemented)
    if scope not in ("all", "api", "guides"):
        raise ToolError(f"Invalid scope '{scope}'. Must be one of: all, api, guides")

    if scope != "all":
        raise ToolError("Only scope='all' is currently supported")

    try:
        results = search(
            db_path=settings.index_db_path,
            query=query,
            limit=limit,
            scope=scope,
        )

        return {
            "results": [
                {
                    "title": r.title,
                    "url": r.url,
                    "score": r.score,
                    "context": r.context,
                }
                for r in results
            ],
            "query": query,
            "count": len(results),
        }

    except SearchUnavailable as exc:
        raise ToolError(
            f"Search index not available: {exc}. "
            "Run 'qt4-doc-build-index' to build the index."
        ) from exc
    except SearchIndexError as exc:
        raise ToolError(f"Search error: {exc}") from exc
    except DocumentationError as exc:
        raise ToolError(exc.tool_message()) from exc
    except Exception as exc:  # pragma: no cover - unexpected failure
        raise ToolError(f"Unexpected search error: {exc}") from exc
