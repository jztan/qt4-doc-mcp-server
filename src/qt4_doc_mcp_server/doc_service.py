from __future__ import annotations

from pathlib import Path

from .cache import CachedDoc, LRUCache, md_store_read, md_store_write
from .config import Settings, markdown_cache_dir
from .convert import collect_links, extract_main, normalize_links, slice_fragment, to_markdown
from .errors import DocumentationError, FetchError, ParseError
from .fetcher import canonicalize_path, load_html, path_to_local_path


ATTRIBUTION = (
    "\n\n---\n"
    "Content © The Qt Company Ltd. and contributors — GNU Free Documentation License 1.3"
)


def _append_attribution(markdown: str) -> str:
    return markdown.rstrip() + ATTRIBUTION


def get_markdown_for_path(
    path: str,
    settings: Settings,
    md_lru: LRUCache | None = None,
    *,
    fragment: str | None = None,
    section_only: bool = False,
) -> CachedDoc:
    """Return cached or freshly converted documentation for a local document path."""
    document_path = canonicalize_path(path)
    cache_enabled = not section_only

    if cache_enabled and md_lru:
        cached = md_lru.get(document_path)
        if cached:
            return cached

    cache_dir = markdown_cache_dir(settings)
    stored = md_store_read(cache_dir, document_path) if cache_enabled else None
    if stored:
        if md_lru:
            md_lru.put(document_path, stored)
        return stored

    doc_base = settings.qt_doc_base or Path(".")
    try:
        local_path = path_to_local_path(document_path, doc_base)
        html = load_html(local_path)
    except DocumentationError:
        raise
    except Exception as exc:  # pragma: no cover - unexpected loader failure
        raise FetchError(f"Unexpected failure reading documentation: {exc}") from exc

    try:
        soup, main, title = extract_main(html)
    except Exception as exc:
        raise ParseError(f"Failed to extract content from {document_path}") from exc

    if main is None:
        raise ParseError(f"Unable to identify main content block in {document_path}")

    try:
        full_links = normalize_links(main, document_path)
    except Exception as exc:
        raise ParseError(f"Failed to normalize links for {document_path}") from exc

    try:
        full_markdown = to_markdown(main)
    except Exception as exc:
        raise ParseError(f"Failed to convert HTML to Markdown for {document_path}") from exc

    full_doc = CachedDoc(
        path=document_path,
        title=title,
        markdown=_append_attribution(full_markdown),
        links=full_links,
    )

    if cache_enabled:
        md_store_write(cache_dir, document_path, full_doc)
        if md_lru:
            md_lru.put(document_path, full_doc)

    if fragment is None or not section_only:
        return full_doc

    try:
        fragment_root = slice_fragment(soup, main, fragment, section_only=True)
    except Exception as exc:
        raise ParseError(f"Failed to slice fragment '{fragment}' in {document_path}") from exc

    if fragment_root is None:
        return full_doc

    try:
        # Hrefs inside the fragment were already normalized on the full page;
        # only collect them, never normalize twice.
        fragment_links = collect_links(fragment_root, document_path)
    except Exception as exc:
        raise ParseError(f"Failed to collect links for fragment '{fragment}'") from exc

    try:
        fragment_markdown = to_markdown(fragment_root)
    except Exception as exc:
        raise ParseError(f"Failed to convert fragment '{fragment}' to Markdown") from exc

    return CachedDoc(
        path=document_path,
        title=title,
        markdown=_append_attribution(fragment_markdown),
        links=fragment_links or full_links,
    )
