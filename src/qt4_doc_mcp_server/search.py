"""SQLite FTS5 index build and query implementation.

This module builds a deterministic FTS5 full-text search index from local Qt 4.8.4
HTML documentation and provides fast ranked search with context snippets.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
import logging
from typing import List, Tuple

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

from .errors import DocumentationError

logger = logging.getLogger(__name__)


# FTS5 schema with unicode61 tokenizer for proper text handling
FTS5_SCHEMA = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5("
    "title, headings, body, url UNINDEXED, path_rel UNINDEXED, "
    "tokenize='unicode61 remove_diacritics 2'"
    ");"
)

# Metadata table for index provenance
META_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS meta ("
    "key TEXT PRIMARY KEY, value TEXT"
    ");"
)


@dataclass
class SearchResult:
    """Single search result with ranking and context."""
    title: str
    url: str
    score: float
    context: str


class SearchUnavailable(DocumentationError):
    """Search index is not available or cannot be queried."""
    def __init__(self, message: str = "Search index unavailable"):
        super().__init__("SearchUnavailable", message)


class IndexError(DocumentationError):
    """Error building or accessing the search index."""
    def __init__(self, message: str = "Index error"):
        super().__init__("IndexError", message)


def ensure_index(db_path: Path) -> None:
    """Create the database schema if it doesn't exist."""
    try:
        con = sqlite3.connect(str(db_path))
        try:
            cur = con.cursor()
            cur.execute(FTS5_SCHEMA)
            cur.execute(META_SCHEMA)
            con.commit()
        finally:
            con.close()
    except Exception as e:
        raise IndexError(f"Failed to initialize index schema: {e}")


def _extract_text_content(html: str) -> Tuple[str, str, str]:
    """Extract title, headings, and body text from HTML.

    Returns (title, headings_text, body_text).
    Headings are concatenated h1-h6 tags; body is all other text.
    """
    if BeautifulSoup is None:
        # Fallback: simple title extraction
        title = ""
        start = html.lower().find("<title>")
        end = html.lower().find("</title>")
        if start != -1 and end != -1 and end > start:
            title = html[start + 7 : end].strip()
        return title, "", ""

    soup = BeautifulSoup(html, "lxml" if "lxml" else "html.parser")

    # Remove navigation and chrome (same as convert.py)
    for sel in [
        "div.header", "div.nav", "div.sidebar",
        "div.breadcrumbs", "div.ft", "div.footer", "div.qt-footer"
    ]:
        for el in soup.select(sel):
            el.decompose()

    # Extract title
    title_el = soup.find("h1") or soup.find("title")
    title = title_el.get_text(strip=True) if title_el else ""

    # Find main content area
    main = (
        soup.select_one("div.content.mainContent")
        or soup.select_one("div.mainContent")
        or soup.select_one("div.content")
        or soup.body
        or soup
    )

    if main is None:
        return title, "", ""

    # Extract headings (h1-h6)
    headings = []
    for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        for heading in main.find_all(tag):
            text = heading.get_text(strip=True)
            if text:
                headings.append(text)

    headings_text = " ".join(headings)

    # Extract body text (remove heading tags first to avoid duplication)
    body_copy = BeautifulSoup(str(main), "lxml" if "lxml" else "html.parser")
    for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        for heading in body_copy.find_all(tag):
            heading.decompose()

    body_text = body_copy.get_text(separator=" ", strip=True)

    return title, headings_text, body_text


def build_index(db_path: Path, docs_base: Path, progress_callback=None) -> dict:
    """Build the FTS5 index from local HTML docs.

    Args:
        db_path: Path to SQLite database file
        docs_base: Root directory containing HTML files
        progress_callback: Optional callable(current, total, path) for progress updates

    Returns:
        dict with stats: indexed, skipped, errors
    """
    if not docs_base.exists() or not docs_base.is_dir():
        raise IndexError(f"Documentation base directory not found: {docs_base}")

    # Collect all HTML files in deterministic order
    html_files = sorted(docs_base.rglob("*.html"))
    if not html_files:
        raise IndexError(f"No HTML files found under {docs_base}")

    logger.info(f"Building index from {len(html_files)} HTML files")

    stats = {"indexed": 0, "skipped": 0, "errors": 0}

    try:
        # Ensure parent directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing database for clean rebuild
        if db_path.exists():
            db_path.unlink()

        con = sqlite3.connect(str(db_path))
        try:
            # Enable WAL mode for better concurrency
            con.execute("PRAGMA journal_mode=WAL")

            cur = con.cursor()
            cur.execute(FTS5_SCHEMA)
            cur.execute(META_SCHEMA)

            # Store metadata
            cur.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("doc_base", str(docs_base))
            )
            cur.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("total_files", str(len(html_files)))
            )

            # Index each file
            for idx, html_path in enumerate(html_files):
                if progress_callback:
                    progress_callback(idx + 1, len(html_files), html_path)

                try:
                    # Read HTML
                    html_content = html_path.read_text(encoding="utf-8", errors="replace")

                    # Extract content
                    title, headings, body = _extract_text_content(html_content)

                    # Skip if no meaningful content
                    if not title and not body:
                        stats["skipped"] += 1
                        continue

                    # Compute relative path and canonical URL
                    path_rel = html_path.relative_to(docs_base).as_posix()
                    canonical_url = f"https://doc.qt.io/archives/qt-4.8/{path_rel}"

                    # Insert into FTS5 table
                    cur.execute(
                        "INSERT INTO docs (title, headings, body, url, path_rel) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (title, headings, body, canonical_url, path_rel)
                    )

                    stats["indexed"] += 1

                except Exception as e:
                    logger.warning(f"Failed to index {html_path}: {e}")
                    stats["errors"] += 1

            # Optimize index for better query performance
            logger.info("Optimizing index...")
            cur.execute("INSERT INTO docs(docs) VALUES('optimize')")

            con.commit()

            # VACUUM to compact database
            logger.info("Compacting database...")
            con.execute("VACUUM")

        finally:
            con.close()

        logger.info(
            f"Index build complete: {stats['indexed']} indexed, "
            f"{stats['skipped']} skipped, {stats['errors']} errors"
        )

        return stats

    except Exception as e:
        raise IndexError(f"Failed to build index: {e}")


def search(
    db_path: Path,
    query: str,
    limit: int = 10,
    scope: str = "all"
) -> List[SearchResult]:
    """Run a MATCH query and return ranked results with snippets.

    Args:
        db_path: Path to SQLite database
        query: Search query string
        limit: Maximum number of results to return
        scope: Filter scope - 'all', 'api', or 'guides' (MVP: all only)

    Returns:
        List of SearchResult objects ranked by relevance
    """
    if not db_path.exists():
        raise SearchUnavailable(f"Search index not found at {db_path}")

    if not query or not query.strip():
        return []

    try:
        con = sqlite3.connect(str(db_path))
        try:
            cur = con.cursor()

            # Build FTS5 query - search across title, headings, and body
            # Use BM25 ranking (default in FTS5)
            fts_query = query.strip()

            # Execute search with snippet generation
            # snippet(table, column, prefix, suffix, ellipsis, max_tokens)
            # Column 2 = body (0=title, 1=headings, 2=body)
            cur.execute(
                """
                SELECT
                    title,
                    url,
                    bm25(docs) as score,
                    snippet(docs, 2, '<b>', '</b>', '…', 10) as context
                FROM docs
                WHERE docs MATCH ?
                ORDER BY bm25(docs) ASC
                LIMIT ?
                """,
                (fts_query, limit)
            )

            results = []
            for row in cur.fetchall():
                title, url, score, context = row

                # Clean up context snippet
                if not context or context.strip() == "":
                    # Fall back to title if no body snippet
                    context = title[:200] if title else "No preview available"

                results.append(SearchResult(
                    title=title or "Untitled",
                    url=url,
                    score=abs(score),  # BM25 returns negative scores; abs for clarity
                    context=context
                ))

            return results

        finally:
            con.close()

    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            raise SearchUnavailable("Search index not initialized")
        raise IndexError(f"Search query failed: {e}")
    except Exception as e:
        raise IndexError(f"Search error: {e}")

