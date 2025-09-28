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
