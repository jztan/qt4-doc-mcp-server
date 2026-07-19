"""Offline fetcher utilities: safe Markdown-path validation and HTML loading."""
from __future__ import annotations

from pathlib import Path, PurePosixPath

from .errors import FetchError, InvalidPathError, NotAllowedError, NotFoundError


def canonicalize_path(path: str) -> str:
    """Validate and normalize a root-relative Markdown document path."""
    if not path or not path.strip():
        raise InvalidPathError("Documentation path must not be empty")
    if "#" in path or "?" in path:
        raise InvalidPathError("Pass fragments separately; path must not contain '#' or '?'")
    if "://" in path:
        raise InvalidPathError("Expected a local documentation path, not a URL")

    normalized = path.replace("\\", "/").lstrip("/")
    posix_path = PurePosixPath(normalized)
    if posix_path.is_absolute() or any(part in {"", ".", ".."} for part in posix_path.parts):
        raise NotAllowedError("Documentation path must stay under QT_DOC_BASE")
    if posix_path.suffix.lower() != ".md":
        raise InvalidPathError("Documentation paths must use the '.md' extension")
    return posix_path.as_posix()


def html_to_markdown_path(html_path: str) -> str:
    """Convert an offline root-relative HTML path to its public Markdown path."""
    posix_path = PurePosixPath(html_path.replace("\\", "/").lstrip("/"))
    if posix_path.suffix.lower() != ".html":
        raise InvalidPathError("Source documentation path must use the '.html' extension")
    return posix_path.with_suffix(".md").as_posix()


def path_to_local_path(document_path: str, base: Path) -> Path:
    """Map a validated Markdown path to its source HTML file under ``QT_DOC_BASE``."""
    safe_path = PurePosixPath(canonicalize_path(document_path)).with_suffix(".html")
    resolved = (base / Path(str(safe_path))).resolve()
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
