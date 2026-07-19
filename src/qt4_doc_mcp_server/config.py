"""Configuration loader with dotenv support (to be implemented).

Precedence: defaults -> .env (if present) -> environment variables.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging
import os
import shutil
import sqlite3
from typing import Tuple

from dotenv import load_dotenv

from .docsets import DocSet, detect_docset


@dataclass
class Settings:
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    qt_doc_base: Path | None = None
    preindex_docs: bool = True
    preconvert_md: bool = True
    md_cache_size: int = 512
    mcp_log_level: str = "WARNING"
    default_max_markdown_length: int = 20000
    docset: DocSet | None = None

    @property
    def index_db_path(self) -> Path:
        """Derived FTS path; it is intentionally not user-configurable."""
        return index_db_path(self)


def load_settings() -> Settings:
    """Load settings with precedence: defaults -> .env -> environment."""
    # Attempt to load .env from repository root
    try:
        here = Path(__file__).resolve()
        # Look up to four levels for a .env
        for parent in [here.parent, *here.parents]:
            candidate = parent / ".env"
            if candidate.exists():
                load_dotenv(candidate)
                break
    except Exception:
        # Non-fatal
        pass

    s = Settings()
    s.server_host = os.getenv("SERVER_HOST", s.server_host)
    s.server_port = int(os.getenv("SERVER_PORT", s.server_port))
    qdb = os.getenv("QT_DOC_BASE")
    s.qt_doc_base = Path(qdb) if qdb else None
    s.docset = detect_docset(s.qt_doc_base)
    s.preindex_docs = os.getenv("PREINDEX_DOCS", str(s.preindex_docs)).lower() == "true"
    s.preconvert_md = os.getenv("PRECONVERT_MD", str(s.preconvert_md)).lower() == "true"
    s.md_cache_size = int(os.getenv("MD_CACHE_SIZE", str(s.md_cache_size)))
    s.mcp_log_level = os.getenv("MCP_LOG_LEVEL", s.mcp_log_level)
    s.default_max_markdown_length = int(os.getenv("DEFAULT_MAX_MARKDOWN_LENGTH", str(s.default_max_markdown_length)))
    return s


def active_docset(settings: Settings) -> DocSet:
    """Return the selected docset, detecting it lazily for programmatic users."""
    if settings.docset is None:
        settings.docset = detect_docset(settings.qt_doc_base)
    return settings.docset


def mcp_state_dir(settings: Settings) -> Path:
    """Return the derived-state directory for the active local documentation set."""
    if settings.qt_doc_base is None:
        raise ValueError("QT_DOC_BASE must be configured before using derived state")
    return settings.qt_doc_base / ".index"


def index_db_path(settings: Settings) -> Path:
    """Return the FTS database path for the active local documentation set."""
    return mcp_state_dir(settings) / "fts.sqlite"


def markdown_cache_dir(settings: Settings) -> Path:
    """Return the Markdown cache directory for the active local documentation set."""
    return mcp_state_dir(settings) / "md"


def markdown_cache_complete_path(settings: Settings) -> Path:
    """Return the marker written after a complete Markdown-cache warmup."""
    return markdown_cache_dir(settings) / ".complete"


def clear_markdown_cache(settings: Settings) -> None:
    """Remove cached Markdown after rebuilding the co-located FTS index."""
    cache_dir = markdown_cache_dir(settings)
    try:
        shutil.rmtree(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
    except FileNotFoundError:
        cache_dir.mkdir(parents=True, exist_ok=True)


def ensure_dirs(settings: Settings) -> None:
    """Ensure the active documentation set's derived-state directories exist."""
    active_docset(settings)
    try:
        mcp_state_dir(settings).mkdir(parents=True, exist_ok=True)
        markdown_cache_dir(settings).mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError):
        # Derived state is optional until an index or cache entry is written.
        pass


def validate_settings(settings: Settings) -> Tuple[bool, list]:
    """Validate critical settings. Returns (ok, warnings)."""
    warnings: list = []
    ok = True
    if settings.qt_doc_base is None:
        logging.error("QT_DOC_BASE is not set. Please configure it in .env or env vars.")
        return False, warnings
    if not settings.qt_doc_base.exists() or not settings.qt_doc_base.is_dir():
        logging.error("QT_DOC_BASE does not exist or is not a directory: %s", settings.qt_doc_base)
        ok = False
    else:
        docset = active_docset(settings)
        index_html = settings.qt_doc_base / "index.html"
        qtdoc_index = settings.qt_doc_base / "qtdoc" / "index.html"
        if not index_html.exists() and not qtdoc_index.exists():
            warnings.append("No index.html or qtdoc/index.html found under QT_DOC_BASE; docs path may be incorrect")
        license_fdl = settings.qt_doc_base / "LICENSE.FDL"
        if docset.key == "qt4.8" and not license_fdl.exists():
            warnings.append("LICENSE.FDL not found under QT_DOC_BASE; ensure license is available alongside docs")
    return ok, warnings


def probe_fts5() -> bool:
    """Return True if SQLite FTS5 is available."""
    try:
        con = sqlite3.connect(":memory:")
        try:
            con.execute("CREATE VIRTUAL TABLE t USING fts5(x)")
            return True
        finally:
            con.close()
    except Exception:
        return False
