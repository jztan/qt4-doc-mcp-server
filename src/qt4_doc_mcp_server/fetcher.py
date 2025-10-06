"""Offline fetcher utilities: canonical URL validation and path mapping."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
import os
import posixpath

from .errors import FetchError, InvalidURLError, NotAllowedError, NotFoundError

ARCHIVE_PREFIX = "/archives/qt-4.8/"
CANONICAL_HOST = "doc.qt.io"


def canonicalize_url(url: str) -> str:
    """Validate and normalize a canonical Qt 4.8 docs URL.

    Raises ValueError on invalid/unsupported URLs.
    """
    u = urlparse(url)
    host = (u.netloc or "").lower()
    if host != CANONICAL_HOST or not (u.scheme in {"http", "https"}):
        raise InvalidURLError("URL host or scheme not allowed")
    if not u.path.startswith(ARCHIVE_PREFIX):
        raise NotAllowedError("URL not under Qt 4.8 archive path")
    # Normalize path: collapse duplicate slashes, etc.
    path = posixpath.normpath(u.path)
    if not path.startswith(ARCHIVE_PREFIX.rstrip("/")):
        raise NotAllowedError("Normalized path escaped archive prefix")
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
    # Prevent traversal using PurePosixPath (platform-independent)
    posix_path = PurePosixPath("/" + rel)
    try:
        safe = posix_path.relative_to("/")
    except ValueError as exc:
        raise NotAllowedError("Path traversal attempt detected") from exc
    # Convert to local path (handles Windows/Unix differences)
    resolved = (base / Path(str(safe))).resolve()
    try:
        resolved.relative_to(base.resolve())
    except ValueError as exc:  # pragma: no cover - safety guard
        raise NotAllowedError("Resolved path escaped QT_DOC_BASE") from exc
    return resolved


def load_html(path: Path) -> str:
    """Read an HTML file as text (UTF-8 with latin-1 fallback)."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise NotFoundError(f"Documentation file not found: {path}") from exc
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="latin-1", errors="ignore")
        except Exception as exc:  # pragma: no cover - unexpected decode failure
            raise FetchError(f"Failed to load documentation file: {path}") from exc
    except OSError as exc:  # pragma: no cover - IO failure
        raise FetchError(f"Failed to read documentation file: {path}") from exc
