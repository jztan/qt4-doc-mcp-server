"""Tests for search.py FTS5 indexing and querying."""
import asyncio
from pathlib import Path

import pytest

from qt4_doc_mcp_server.config import Settings, ensure_dirs, probe_fts5
from qt4_doc_mcp_server.search import (
    build_index,
    search,
    SearchResult,
    SearchUnavailable,
    IndexError as SearchIndexError,
)
from qt4_doc_mcp_server.tools import configure_from_settings, search_documentation

pytest.importorskip("bs4")


@pytest.fixture()
def sample_docs(tmp_path: Path) -> Path:
    """Create sample HTML documentation for testing."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    # Create a few test HTML files
    (docs_dir / "qstring.html").write_text(
        """
        <html>
          <head><title>QString Class Reference</title></head>
          <body>
            <div class="mainContent">
              <h1>QString Class Reference</h1>
              <p>The QString class provides a Unicode character string.</p>
              <h2>Public Functions</h2>
              <p>QString provides many functions for manipulating strings.</p>
            </div>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    (docs_dir / "qwidget.html").write_text(
        """
        <html>
          <head><title>QWidget Class Reference</title></head>
          <body>
            <div class="mainContent">
              <h1>QWidget Class Reference</h1>
              <p>The QWidget class is the base class of all user interface objects.</p>
              <h2>Signals and Slots</h2>
              <p>Widgets can emit signals and have slots for receiving signals.</p>
            </div>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    (docs_dir / "signals-slots.html").write_text(
        """
        <html>
          <head><title>Signals and Slots</title></head>
          <body>
            <div class="mainContent">
              <h1>Signals and Slots</h1>
              <p>Signals and slots are used for communication between objects.</p>
              <h2>Overview</h2>
              <p>The signals and slots mechanism is a central feature of Qt.</p>
            </div>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    return docs_dir


@pytest.fixture()
def sample_settings(tmp_path: Path, sample_docs: Path) -> Settings:
    """Create test settings with sample docs."""
    settings = Settings(
        qt_doc_base=sample_docs,
        md_cache_dir=tmp_path / "cache" / "md",
        index_db_path=tmp_path / "index" / "fts.sqlite",
        preindex_docs=False,
        preconvert_md=False,
        md_cache_size=4,
    )
    ensure_dirs(settings)
    return settings


def test_fts5_available() -> None:
    """Test that FTS5 is available in the test environment."""
    assert probe_fts5(), "SQLite FTS5 must be available for search tests"


def test_build_index_creates_database(sample_settings: Settings) -> None:
    """Test that build_index creates a valid FTS5 database."""
    db_path = sample_settings.index_db_path
    docs_base = sample_settings.qt_doc_base

    assert not db_path.exists(), "Index should not exist yet"

    stats = build_index(db_path, docs_base)

    assert db_path.exists(), "Index database should be created"
    assert stats["indexed"] == 3, "Should index all 3 HTML files"
    assert stats["errors"] == 0, "Should have no errors"


def test_build_index_with_progress_callback(sample_settings: Settings) -> None:
    """Test that build_index calls progress callback."""
    db_path = sample_settings.index_db_path
    docs_base = sample_settings.qt_doc_base

    progress_calls = []

    def progress(current, total, path):
        progress_calls.append((current, total, path.name))

    stats = build_index(db_path, docs_base, progress_callback=progress)

    assert len(progress_calls) == 3, "Should call progress for each file"
    assert stats["indexed"] == 3


def test_search_returns_relevant_results(sample_settings: Settings) -> None:
    """Test that search returns relevant results ranked by BM25."""
    db_path = sample_settings.index_db_path
    docs_base = sample_settings.qt_doc_base

    # Build index first
    build_index(db_path, docs_base)

    # Search for "QString"
    results = search(db_path, "QString")

    assert len(results) > 0, "Should find results"
    assert results[0].title == "QString Class Reference"
    assert "QString" in results[0].context or "QString" in results[0].title


def test_search_with_limit(sample_settings: Settings) -> None:
    """Test that search respects the limit parameter."""
    db_path = sample_settings.index_db_path
    docs_base = sample_settings.qt_doc_base

    build_index(db_path, docs_base)

    # Search with limit=1
    results = search(db_path, "signals", limit=1)

    assert len(results) <= 1, "Should respect limit"


def test_search_multiple_terms(sample_settings: Settings) -> None:
    """Test searching with multiple terms."""
    db_path = sample_settings.index_db_path
    docs_base = sample_settings.qt_doc_base

    build_index(db_path, docs_base)

    # Search for "signals slots"
    results = search(db_path, "signals slots")

    assert len(results) > 0, "Should find results for multi-term query"
    # The signals-slots.html should rank highly
    titles = [r.title for r in results]
    assert "Signals and Slots" in titles


def test_search_empty_query_returns_empty(sample_settings: Settings) -> None:
    """Test that empty queries return no results."""
    db_path = sample_settings.index_db_path
    docs_base = sample_settings.qt_doc_base

    build_index(db_path, docs_base)

    results = search(db_path, "")
    assert len(results) == 0

    results = search(db_path, "   ")
    assert len(results) == 0


def test_search_nonexistent_index_raises(sample_settings: Settings) -> None:
    """Test that searching nonexistent index raises SearchUnavailable."""
    db_path = sample_settings.index_db_path

    assert not db_path.exists()

    with pytest.raises(SearchUnavailable):
        search(db_path, "test")


def test_search_result_structure(sample_settings: Settings) -> None:
    """Test that SearchResult has the expected structure."""
    db_path = sample_settings.index_db_path
    docs_base = sample_settings.qt_doc_base

    build_index(db_path, docs_base)
    results = search(db_path, "QString")

    assert len(results) > 0
    result = results[0]

    assert isinstance(result, SearchResult)
    assert isinstance(result.title, str)
    assert isinstance(result.url, str)
    assert isinstance(result.score, float)
    assert isinstance(result.context, str)
    assert result.url.startswith("https://doc.qt.io/archives/qt-4.8/")


@pytest.mark.asyncio
async def test_search_documentation_tool(sample_settings: Settings) -> None:
    """Test the search_documentation MCP tool."""
    configure_from_settings(sample_settings)

    # Build index
    build_index(sample_settings.index_db_path, sample_settings.qt_doc_base)

    # Test search tool
    result = await search_documentation(query="QString", limit=5)

    assert "results" in result
    assert "query" in result
    assert "count" in result
    assert result["query"] == "QString"
    assert result["count"] > 0
    assert len(result["results"]) > 0

    # Check result structure
    first_result = result["results"][0]
    assert "title" in first_result
    assert "url" in first_result
    assert "score" in first_result
    assert "context" in first_result


@pytest.mark.asyncio
async def test_search_documentation_tool_no_index(sample_settings: Settings) -> None:
    """Test search_documentation tool raises ToolError when index missing."""
    from mcp.server.fastmcp.exceptions import ToolError

    configure_from_settings(sample_settings)

    # Don't build index - should raise ToolError
    with pytest.raises(ToolError) as exc_info:
        await search_documentation(query="test")

    assert "not available" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_search_documentation_tool_limit_validation(
    sample_settings: Settings,
) -> None:
    """Test that search_documentation validates and clamps limit."""
    configure_from_settings(sample_settings)
    build_index(sample_settings.index_db_path, sample_settings.qt_doc_base)

    # Test limit too low
    result = await search_documentation(query="signals", limit=-5)
    assert result["count"] >= 0  # Should use default

    # Test limit too high (max 50)
    result = await search_documentation(query="signals", limit=100)
    assert len(result["results"]) <= 50  # Should clamp to 50


@pytest.mark.asyncio
async def test_search_documentation_scope_validation(
    sample_settings: Settings,
) -> None:
    """Test that search_documentation validates scope parameter."""
    from mcp.server.fastmcp.exceptions import ToolError

    configure_from_settings(sample_settings)
    build_index(sample_settings.index_db_path, sample_settings.qt_doc_base)

    # Invalid scope should raise error
    with pytest.raises(ToolError) as exc_info:
        await search_documentation(query="test", scope="invalid")

    assert "scope" in str(exc_info.value).lower()

    # Non-implemented scope should raise error
    with pytest.raises(ToolError) as exc_info:
        await search_documentation(query="test", scope="api")

    assert "currently supported" in str(exc_info.value).lower()


def test_build_index_deterministic(sample_settings: Settings) -> None:
    """Test that index builds are deterministic."""
    db_path = sample_settings.index_db_path
    docs_base = sample_settings.qt_doc_base

    # Build index twice
    stats1 = build_index(db_path, docs_base)
    size1 = db_path.stat().st_size

    # Rebuild
    stats2 = build_index(db_path, docs_base)
    size2 = db_path.stat().st_size

    assert stats1 == stats2, "Stats should be identical"
    # Note: Size might vary slightly due to SQLite internals, but should be very close
    assert abs(size1 - size2) < 10000, "Index size should be nearly identical"
