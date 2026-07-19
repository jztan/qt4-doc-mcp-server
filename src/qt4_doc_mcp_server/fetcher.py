"""Offline fetcher utilities: canonical URL validation and path mapping."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
import posixpath

from .docsets import CANONICAL_HOST, DocSet, QT4_DOCSET
from .errors import FetchError, InvalidURLError, NotAllowedError, NotFoundError

# Retained for integrations that imported the historical constant.
ARCHIVE_PREFIX = QT4_DOCSET.canonical_prefix


def canonicalize_url(url: str, docset: DocSet = QT4_DOCSET) -> str:
    """Validate and normalize a URL belonging to the active local docset."""
    u = urlparse(url)
    host = (u.netloc or "").lower()
    if host != CANONICAL_HOST or u.scheme not in {"http", "https"}:
        raise InvalidURLError("URL host or scheme not allowed")
    prefix = docset.canonical_prefix
    if not u.path.startswith(prefix):
        raise NotAllowedError(f"URL not under active {docset.display_name} documentation path")

    # Normalize path: collapse duplicate slashes, etc.
    path = posixpath.normpath(u.path)
    required_root = prefix.rstrip("/")
    if path != required_root and not path.startswith(required_root + "/"):
        raise NotAllowedError("Normalized path escaped documentation prefix")

    # Rebuild URL with normalized parts, preserve query/fragment.
    norm = f"{u.scheme}://{CANONICAL_HOST}{path}"
    if u.params:
        norm += ";" + u.params
    if u.query:
        norm += "?" + u.query
    if u.fragment:
        norm += "#" + u.fragment
    return norm


def url_to_path(canonical_url: str, base: Path, docset: DocSet = QT4_DOCSET) -> Path:
    """Map an active-docset URL to a local file path under ``QT_DOC_BASE``."""
    u = urlparse(canonical_url)
    prefix = docset.canonical_prefix
    if not u.path.startswith(prefix):
        raise NotAllowedError(f"URL not under active {docset.display_name} documentation path")
    rel = u.path[len(prefix) :].lstrip("/")
    # Prevent traversal using PurePosixPath (platform-independent).
    posix_path = PurePosixPath("/" + rel)
    try:
        safe = posix_path.relative_to("/")
    except ValueError as exc:
        raise NotAllowedError("Path traversal attempt detected") from exc
    # Convert to local path (handles Windows/Unix differences).
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
