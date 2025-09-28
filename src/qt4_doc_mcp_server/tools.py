"""MCP tools for the Qt 4.8.4 Docs server."""

from __future__ import annotations

from typing import Optional

from .server import mcp
from .config import load_settings
from .cache import LRUCache
from .doc_service import get_markdown_for_url, ATTRIBUTION
from .fetcher import canonicalize_url


_md_lru: Optional[LRUCache] = None


def _get_lru() -> LRUCache:
    global _md_lru
    if _md_lru is None:
        settings = load_settings()
        _md_lru = LRUCache(settings.md_cache_size)
    return _md_lru


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
        url: Canonical Qt docs URL (https://doc.qt.io/archives/qt-4.8/...).
        fragment: Optional #fragment to focus.
        section_only: When true, return only the fragment section content.
        start_index: Optional start offset for chunking the markdown.
        max_length: Optional max chars for chunking the markdown.
    Returns:
        dict with fields: title, url, canonical_url, markdown, attribution, links
    """
    settings = load_settings()
    lru = _get_lru()
    title, markdown, links = get_markdown_for_url(
        url,
        settings,
        lru,
        fragment=fragment,
        section_only=section_only,
    )
    canonical_url = canonicalize_url(url)

    # Optional chunking
    if start_index is not None or max_length is not None:
        s = max(0, start_index or 0)
        if max_length is not None and max_length >= 0:
            markdown = markdown[s : s + max_length]
        else:
            markdown = markdown[s:]

    # Provide a clean attribution string separately (without formatting lines)
    clean_attr = "Content © The Qt Company Ltd./Digia — GNU Free Documentation License 1.3"

    return {
        "title": title,
        "url": url,
        "canonical_url": canonical_url,
        "markdown": markdown,
        "attribution": clean_attr,
        "links": links,
    }

