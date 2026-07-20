"""HTML extraction, link normalization, section slicing, and HTML→Markdown.

This module uses BeautifulSoup and markdownify when available; otherwise
falls back to a simple text converter. See DESIGN.md for detailed rules.
"""
from __future__ import annotations

from typing import TypedDict, List
from urllib.parse import urljoin, urlparse, urlunparse

from .errors import DocumentationError
from .fetcher import canonicalize_path, html_to_markdown_path

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional dep
    BeautifulSoup = None  # type: ignore


class ConversionResult(TypedDict):
    markdown: str
    title: str
    links: List[dict]


def _get_soup(html: str):
    if BeautifulSoup is None:
        return None
    # Prefer lxml if present
    parser = "lxml"
    try:
        return BeautifulSoup(html, parser)
    except Exception:
        return BeautifulSoup(html, "html.parser")


def extract_main(html: str):
    """Return (soup, main_element, title).

    If BeautifulSoup is unavailable, returns (None, None, simple_title).
    """
    soup = _get_soup(html)
    if soup is None:
        # crude title extraction
        title = ""
        start = html.lower().find("<title>")
        end = html.lower().find("</title>")
        if start != -1 and end != -1 and end > start:
            title = html[start + 7 : end].strip()
        return None, None, title

    # Strip common chrome.  Qt 5/6 place the actual page body inside
    # div.header#qtdocheader, so only remove header elements that do not
    # contain a main-content block.
    for sel in [
        "div.header",
        "div.nav",
        "div.sidebar",
        "div.breadcrumbs",
        "div.ft",
        "div.footer",
        "div.qt-footer",
    ]:
        for el in soup.select(sel):
            if sel == "div.header" and el.select_one("div.mainContent"):
                continue
            el.decompose()

    main = (
        soup.select_one("div.content.mainContent")
        or soup.select_one("div.mainContent")
        or soup.select_one("div.content")
        or soup.body
        or soup
    )
    # Title
    title_el = soup.find("h1") or soup.find("title")
    title = title_el.get_text(strip=True) if title_el else ""
    return soup, main, title


def normalize_links(root, document_path: str) -> List[dict]:
    """Convert local HTML links to relative Markdown links and collect paths.

    The converted Markdown retains the source link's relative structure for
    filesystem browsing.  Link metadata contains a root-relative ``path`` for
    direct use with ``read_documentation``.
    """
    links: List[dict] = []
    if root is None or BeautifulSoup is None:
        return links

    base_url = "https://local.invalid/" + document_path
    for a in root.find_all("a"):
        href = a.get("href")
        if not href:
            continue
        parsed_href = urlparse(href)
        if parsed_href.scheme or parsed_href.netloc:
            links.append({"text": a.get_text(strip=True), "url": href})
            continue

        markdown_href = href
        if parsed_href.path:
            try:
                markdown_href = urlunparse(
                    parsed_href._replace(path=html_to_markdown_path(parsed_href.path))
                )
            except DocumentationError:
                links.append({"text": a.get_text(strip=True), "url": href})
                continue
        a["href"] = markdown_href

        links.append(
            _link_entry(a.get_text(strip=True), markdown_href, base_url, fallback_href=href)
        )
    return links


def _link_entry(text: str, href: str, base_url: str, fallback_href: str | None = None) -> dict:
    """Classify an already-normalized Markdown href into link metadata."""
    fallback = fallback_href if fallback_href is not None else href
    parsed = urlparse(href)
    if parsed.scheme or parsed.netloc:
        return {"text": text, "url": fallback}
    absolute = urljoin(base_url, href)
    resolved = urlparse(absolute)
    try:
        link_path = canonicalize_path(resolved.path)
    except DocumentationError:
        return {"text": text, "url": fallback}
    if resolved.fragment:
        link_path += "#" + resolved.fragment
    return {"text": text, "path": link_path}


def collect_links(root, document_path: str) -> List[dict]:
    """Collect link metadata from a subtree whose hrefs are already
    normalized by ``normalize_links`` (running that again would fail on the
    converted ``.md`` hrefs)."""
    links: List[dict] = []
    if root is None or BeautifulSoup is None:
        return links
    base_url = "https://local.invalid/" + document_path
    for a in root.find_all("a"):
        href = a.get("href")
        if not href:
            continue
        links.append(_link_entry(a.get_text(strip=True), href, base_url))
    return links


def _heading_level(tag) -> int | None:
    name = getattr(tag, "name", None)
    if name and len(name) == 2 and name[0].lower() == "h" and name[1].isdigit():
        return int(name[1])
    return None


def slice_fragment(soup, root, fragment: str | None, section_only: bool):
    if not fragment or root is None or BeautifulSoup is None:
        return root
    frag = fragment.lstrip("#")
    target = root.find(id=frag)
    if target is None:
        # legacy name anchors
        target = root.find(attrs={"name": frag})
    if target is None or not section_only:
        return root
    # Qt docs mark anchors with empty <a name> tags placed inside the
    # heading (function docs) or just before it (guide sections); resolve
    # the anchor to the heading that owns the section.
    heading = target if _heading_level(target) is not None else None
    if heading is None:
        heading = target.find_parent(lambda t: _heading_level(t) is not None)
    if heading is None:
        heading = target.find_next(lambda t: _heading_level(t) is not None)
    if heading is None:
        return target
    level = _heading_level(heading)
    # Collect the section's nodes before moving any of them: appending to
    # the wrapper detaches a node, which would break sibling traversal.
    nodes = [heading]
    for sib in heading.find_next_siblings():
        sib_level = _heading_level(sib)
        if sib_level is not None and sib_level <= level:
            break
        nodes.append(sib)
    wrapper = soup.new_tag("div")
    for node in nodes:
        wrapper.append(node)
    return wrapper


def _to_markdown_fallback(root) -> str:
    # Strip tags crudely
    txt = root.get_text("\n" if hasattr(root, "get_text") else " ", strip=True)
    return txt


def to_markdown(root) -> str:
    if root is None:
        return ""
    try:
        import markdownify

        return markdownify.markdownify(str(root), heading_style="ATX")
    except Exception:  # pragma: no cover - optional dep fallback
        return _to_markdown_fallback(root)
