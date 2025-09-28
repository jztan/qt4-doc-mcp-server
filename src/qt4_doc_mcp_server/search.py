"""SQLite FTS5 index build and query stubs."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3


FTS5_SCHEMA = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5("
    "title, headings, body, url UNINDEXED, path_rel UNINDEXED, "
    "tokenize='unicode61 remove_diacritics 2'"
    ");"
)


@dataclass
class SearchResult:
    title: str
    url: str
    score: float
    context: str


def ensure_index(db_path: Path) -> None:
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(FTS5_SCHEMA)
        con.commit()
    finally:
        con.close()


def build_index(db_path: Path, docs_base: Path) -> None:
    """Build the FTS5 index from local HTML docs (placeholder)."""
    raise NotImplementedError


def search(db_path: Path, query: str, limit: int = 10) -> list[SearchResult]:
    """Run a MATCH query and return ranked results (placeholder)."""
    raise NotImplementedError

