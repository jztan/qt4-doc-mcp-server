"""Offline fetcher utilities: canonical URL validation and path mapping."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
import os

ARCHIVE_PREFIX = "/archives/qt-4.8/"
CANONICAL_HOST = "doc.qt.io"


def canonicalize_url(url: str) -> str:
    """Validate and normalize a canonical Qt 4.8 docs URL.

    Raises ValueError on invalid/unsupported URLs.
    """
    u = urlparse(url)
    host = (u.netloc or "").lower()
    if host != CANONICAL_HOST or not (u.scheme in {"http", "https"}):
        raise ValueError("InvalidURL: URL host/scheme not allowed")
    if not u.path.startswith(ARCHIVE_PREFIX):
        raise ValueError("NotAllowed: URL not under Qt 4.8 archive path")
    # Normalize path: collapse duplicate slashes, etc.
    path = os.path.normpath(u.path)
    if not path.startswith(ARCHIVE_PREFIX.rstrip("/")):
        raise ValueError("NotAllowed: normalized path escaped archive prefix")
    # Rebuild URL with normalized parts, preserve query/fragment
    norm = f"{u.scheme}://{CANONICAL_HOST}{path}"
    if u.params:
        norm += ";" + u.params
    if u.query:
        norm += "?" + u.query
    if u.fragment:
        norm += "#" + u.fragment
    return norm


def url_to_path(canonical_url: str, base: Path) -> Path:
    """Map a canonical URL to a local file path under QT_DOC_BASE."""
    u = urlparse(canonical_url)
    rel = u.path[len(ARCHIVE_PREFIX) :].lstrip("/")
    # Prevent traversal
    safe = Path("/" + rel).resolve().relative_to("/")
    return (base / safe).resolve()


def load_html(path: Path) -> str:
    """Read an HTML file as text (UTF-8 with latin-1 fallback)."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1", errors="ignore")

