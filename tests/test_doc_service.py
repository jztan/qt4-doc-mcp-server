import asyncio
from pathlib import Path

import pytest

from mcp.server.fastmcp.exceptions import ToolError

from qt4_doc_mcp_server.cache import LRUCache, md_store_meta_path, md_store_path
from qt4_doc_mcp_server.config import Settings, ensure_dirs
from qt4_doc_mcp_server.doc_service import get_markdown_for_url
from qt4_doc_mcp_server.tools import configure_from_settings, read_documentation

pytest.importorskip("bs4")


@pytest.fixture()
def sample_settings(tmp_path: Path) -> Settings:
    html = """
    <html>
      <head><title>Sample Title</title></head>
      <body>
        <div class="mainContent">
          <h1>Sample Title</h1>
          <p>Intro paragraph.</p>
          <h2 id="section">Section Heading</h2>
          <p>Section content with a <a href="qtother.html#anchor">link</a>.</p>
        </div>
      </body>
    </html>
    """
    (tmp_path / "qsample.html").write_text(html, encoding="utf-8")
    settings = Settings(
        qt_doc_base=tmp_path,
        md_cache_dir=tmp_path / "cache" / "md",
        index_db_path=tmp_path / "index" / "fts.sqlite",
        preindex_docs=False,
        preconvert_md=False,
        md_cache_size=4,
    )
    ensure_dirs(settings)
    return settings


def _canonical_url() -> str:
    return "https://doc.qt.io/archives/qt-4.8/qsample.html"


def test_metadata_persists_through_cache(sample_settings: Settings) -> None:
    lru = LRUCache(4)
    url = _canonical_url()

    doc = get_markdown_for_url(url, sample_settings, lru)
    assert doc.title == "Sample Title"
    assert doc.links
    assert doc.links[0]["url"].startswith("https://doc.qt.io/archives/qt-4.8/")

    meta_path = md_store_meta_path(sample_settings.md_cache_dir, url)
    md_path = md_store_path(sample_settings.md_cache_dir, url)
    assert meta_path.exists()
    assert md_path.exists()

    cached = get_markdown_for_url(url, sample_settings, lru)
    assert cached.title == doc.title
    assert cached.links == doc.links


def test_section_only_not_cached(sample_settings: Settings) -> None:
    url = _canonical_url()
    meta_path = md_store_meta_path(sample_settings.md_cache_dir, url)

    section_doc = get_markdown_for_url(
        url,
        sample_settings,
        None,
        fragment="#section",
        section_only=True,
    )
    assert "Section Heading" in section_doc.markdown
    assert "Intro paragraph" not in section_doc.markdown
    assert not meta_path.exists()

    full_doc = get_markdown_for_url(url, sample_settings, None)
    assert "Intro paragraph" in full_doc.markdown
    assert meta_path.exists()


def test_read_documentation_invalid_url_raises(sample_settings: Settings) -> None:
    configure_from_settings(sample_settings)
    with pytest.raises(ToolError) as exc_info:
        asyncio.run(read_documentation("https://example.com/other.html"))
    assert str(exc_info.value).startswith("InvalidURL")


def test_read_documentation_missing_file(sample_settings: Settings) -> None:
    configure_from_settings(sample_settings)
    with pytest.raises(ToolError) as exc_info:
        asyncio.run(
            read_documentation("https://doc.qt.io/archives/qt-4.8/missing.html")
        )
    assert str(exc_info.value).startswith("NotFound")


def test_read_documentation_returns_section_only(sample_settings: Settings) -> None:
    configure_from_settings(sample_settings)
    result_full = asyncio.run(read_documentation(_canonical_url()))
    result_section = asyncio.run(
        read_documentation(_canonical_url(), fragment="#section", section_only=True)
    )

    assert len(result_section["markdown"]) < len(result_full["markdown"])  # smaller slice
    assert result_section["links"]
    assert any("#anchor" in link["url"] for link in result_section["links"])


def test_read_documentation_applies_default_max_length(tmp_path: Path) -> None:
    """Test that default_max_markdown_length is applied when max_length is not provided."""
    # Create a longer HTML document
    long_content = "\n".join([f"<p>Paragraph {i} with some content.</p>" for i in range(100)])
    html = f"""
    <html>
      <head><title>Long Document</title></head>
      <body>
        <div class="mainContent">
          <h1>Long Document</h1>
          {long_content}
        </div>
      </body>
    </html>
    """
    (tmp_path / "qlong.html").write_text(html, encoding="utf-8")
    
    settings = Settings(
        qt_doc_base=tmp_path,
        md_cache_dir=tmp_path / "cache" / "md",
        index_db_path=tmp_path / "index" / "fts.sqlite",
        preindex_docs=False,
        preconvert_md=False,
        md_cache_size=4,
        default_max_markdown_length=500,  # Short limit for testing
    )
    ensure_dirs(settings)
    configure_from_settings(settings)
    
    url = "https://doc.qt.io/archives/qt-4.8/qlong.html"
    result = asyncio.run(read_documentation(url))
    
    # Should be truncated to 500 characters
    assert len(result["markdown"]) == 500
    assert "content_info" in result
    assert result["content_info"]["truncated"] is True
    assert result["content_info"]["returned_length"] == 500
    assert result["content_info"]["total_length"] > 500


def test_read_documentation_explicit_max_length_overrides_default(tmp_path: Path) -> None:
    """Test that explicit max_length parameter overrides default setting."""
    long_content = "\n".join([f"<p>Paragraph {i}.</p>" for i in range(100)])
    html = f"""
    <html>
      <head><title>Long Document</title></head>
      <body>
        <div class="mainContent">
          <h1>Long Document</h1>
          {long_content}
        </div>
      </body>
    </html>
    """
    (tmp_path / "qlong2.html").write_text(html, encoding="utf-8")
    
    settings = Settings(
        qt_doc_base=tmp_path,
        md_cache_dir=tmp_path / "cache" / "md",
        index_db_path=tmp_path / "index" / "fts.sqlite",
        preindex_docs=False,
        preconvert_md=False,
        md_cache_size=4,
        default_max_markdown_length=500,
    )
    ensure_dirs(settings)
    configure_from_settings(settings)
    
    url = "https://doc.qt.io/archives/qt-4.8/qlong2.html"
    # Explicitly request 300 characters
    result = asyncio.run(read_documentation(url, max_length=300))
    
    # Should use explicit value, not default
    assert len(result["markdown"]) == 300
    assert "content_info" in result
    assert result["content_info"]["returned_length"] == 300


def test_read_documentation_pagination_with_start_index(tmp_path: Path) -> None:
    """Test pagination using start_index and max_length."""
    html = """
    <html>
      <head><title>Paginated Doc</title></head>
      <body>
        <div class="mainContent">
          <h1>Paginated Doc</h1>
          <p>First paragraph.</p>
          <p>Second paragraph.</p>
          <p>Third paragraph.</p>
        </div>
      </body>
    </html>
    """
    (tmp_path / "qpage.html").write_text(html, encoding="utf-8")
    
    settings = Settings(
        qt_doc_base=tmp_path,
        md_cache_dir=tmp_path / "cache" / "md",
        index_db_path=tmp_path / "index" / "fts.sqlite",
        preindex_docs=False,
        preconvert_md=False,
        md_cache_size=4,
        default_max_markdown_length=20000,
    )
    ensure_dirs(settings)
    configure_from_settings(settings)
    
    url = "https://doc.qt.io/archives/qt-4.8/qpage.html"
    
    # Get first page
    page1 = asyncio.run(read_documentation(url, start_index=0, max_length=50))
    assert len(page1["markdown"]) == 50
    assert page1["content_info"]["start_index"] == 0
    
    # Get second page
    page2 = asyncio.run(read_documentation(url, start_index=50, max_length=50))
    assert len(page2["markdown"]) == 50
    assert page2["content_info"]["start_index"] == 50
    
    # Pages should have different content
    assert page1["markdown"] != page2["markdown"]

