"""Configuration loader with dotenv support (to be implemented).

Precedence: defaults -> .env (if present) -> environment variables.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import logging
import sqlite3
from typing import Tuple

from dotenv import load_dotenv


@dataclass
class Settings:
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    qt_doc_base: Path | None = None
    index_db_path: Path = Path(".index/fts.sqlite")
    md_cache_dir: Path = Path(".cache/md")
    preindex_docs: bool = True
    preconvert_md: bool = True
    md_cache_size: int = 512
    mcp_log_level: str = "WARNING"


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
    s.index_db_path = Path(os.getenv("INDEX_DB_PATH", str(s.index_db_path)))
    s.md_cache_dir = Path(os.getenv("MD_CACHE_DIR", str(s.md_cache_dir)))
    s.preindex_docs = os.getenv("PREINDEX_DOCS", str(s.preindex_docs)).lower() == "true"
    s.preconvert_md = os.getenv("PRECONVERT_MD", str(s.preconvert_md)).lower() == "true"
    s.md_cache_size = int(os.getenv("MD_CACHE_SIZE", str(s.md_cache_size)))
    s.mcp_log_level = os.getenv("MCP_LOG_LEVEL", s.mcp_log_level)
    return s


def ensure_dirs(settings: Settings) -> None:
    """Ensure index and markdown store directories exist."""
    try:
        settings.index_db_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    try:
        settings.md_cache_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
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
        index_html = settings.qt_doc_base / "index.html"
        if not index_html.exists():
            warnings.append("index.html not found under QT_DOC_BASE; docs path may be incorrect")
        license_fdl = settings.qt_doc_base / "LICENSE.FDL"
        if not license_fdl.exists():
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
