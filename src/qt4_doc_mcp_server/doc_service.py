from __future__ import annotations

from pathlib import Path

from .cache import CachedDoc, LRUCache, md_store_read, md_store_write
from .config import Settings
from .convert import extract_main, normalize_links, slice_fragment, to_markdown
from .errors import DocumentationError, FetchError, ParseError
from .fetcher import canonicalize_url, url_to_path, load_html


ATTRIBUTION = (
    "\n\n---\n"
    "Content © The Qt Company Ltd./Digia — GNU Free Documentation License 1.3"
)


def _append_attribution(markdown: str) -> str:
    return markdown.rstrip() + ATTRIBUTION


def get_markdown_for_url(
    url: str,
    settings: Settings,
    md_lru: LRUCache | None = None,
    *,
    fragment: str | None = None,
    section_only: bool = False,
) -> CachedDoc:
    """Return cached or freshly converted documentation for a canonical Qt URL."""
    canonical = canonicalize_url(url)
    cache_enabled = not section_only

    if cache_enabled and md_lru:
        cached = md_lru.get(canonical)
        if cached:
            return cached

    stored = md_store_read(settings.md_cache_dir, canonical) if cache_enabled else None
    if stored:
        if md_lru:
            md_lru.put(canonical, stored)
        return stored

    doc_base = settings.qt_doc_base or Path(".")
    try:
        path = url_to_path(canonical, doc_base)
        html = load_html(path)
    except DocumentationError:
        raise
    except Exception as exc:  # pragma: no cover - unexpected loader failure
        raise FetchError(f"Unexpected failure reading documentation: {exc}") from exc

    try:
        soup, main, title = extract_main(html)
    except Exception as exc:
        raise ParseError(f"Failed to extract content from {canonical}") from exc

    if main is None:
        raise ParseError(f"Unable to identify main content block in {canonical}")

    try:
        full_links = normalize_links(main, canonical)
    except Exception as exc:
        raise ParseError(f"Failed to normalize links for {canonical}") from exc

    try:
        full_markdown = to_markdown(main)
    except Exception as exc:
        raise ParseError(f"Failed to convert HTML to Markdown for {canonical}") from exc

    full_doc = CachedDoc(
        canonical_url=canonical,
        title=title,
        markdown=_append_attribution(full_markdown),
        links=full_links,
    )

    if cache_enabled:
        md_store_write(settings.md_cache_dir, canonical, full_doc)
        if md_lru:
            md_lru.put(canonical, full_doc)

    if fragment is None or not section_only:
        return full_doc

    try:
        fragment_root = slice_fragment(soup, main, fragment, section_only=True)
    except Exception as exc:
        raise ParseError(f"Failed to slice fragment '{fragment}' in {canonical}") from exc

    if fragment_root is None:
        return full_doc

    try:
        fragment_links = normalize_links(fragment_root, canonical)
    except Exception as exc:
        raise ParseError(f"Failed to normalize links for fragment '{fragment}'") from exc

    try:
        fragment_markdown = to_markdown(fragment_root)
    except Exception as exc:
        raise ParseError(f"Failed to convert fragment '{fragment}' to Markdown") from exc

    return CachedDoc(
        canonical_url=canonical,
        title=title,
        markdown=_append_attribution(fragment_markdown),
        links=fragment_links or full_links,
    )
