from __future__ import annotations

from typing import Tuple
from pathlib import Path

from .config import Settings
from .fetcher import canonicalize_url, url_to_path, load_html
from .convert import extract_main, normalize_links, slice_fragment, to_markdown
from .cache import LRUCache, md_store_read, md_store_write


ATTRIBUTION = (
    "\n\n---\n"
    "Content © The Qt Company Ltd./Digia — GNU Free Documentation License 1.3"
)


def get_markdown_for_url(
    url: str,
    settings: Settings,
    md_lru: LRUCache | None = None,
    *,
    fragment: str | None = None,
    section_only: bool = False,
) -> Tuple[str, str, list[dict]]:
    """Return (title, markdown, links) for a canonical Qt docs URL.

    Uses disk Markdown store first, with optional in-memory LRU cache.
    """
    canonical = canonicalize_url(url)
    if md_lru:
        cached = md_lru.get(canonical)
        if cached:
            # No link list in memory cache; acceptable for read path
            return "", cached, []

    # Disk store
    stored = md_store_read(settings.md_cache_dir, canonical)
    if stored:
        if md_lru:
            md_lru.put(canonical, stored)
        return "", stored, []

    # Convert from HTML
    path = url_to_path(canonical, settings.qt_doc_base or Path("."))
    html = load_html(path)
    soup, main, title = extract_main(html)
    main = slice_fragment(soup, main, fragment, section_only)
    links = normalize_links(main, canonical)
    md = to_markdown(main)
    md = md.rstrip() + ATTRIBUTION

    md_store_write(settings.md_cache_dir, canonical, md)
    if md_lru:
        md_lru.put(canonical, md)
    return title, md, links

