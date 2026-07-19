from pathlib import Path

from qt4_doc_mcp_server.config import Settings, ensure_dirs
from qt4_doc_mcp_server.doc_service import get_markdown_for_url
from qt4_doc_mcp_server.search import build_index, index_matches_docs, search


def _qt6_docs(tmp_path: Path) -> Path:
    root = tmp_path / "Qt-6.8.2"
    page = root / "qtcore" / "qsample.html"
    page.parent.mkdir(parents=True)
    page.write_text(
        """
        <html><head><title>Sample Class | Qt Core 6.8.2</title></head>
        <body>
          <div class="header" id="qtdocheader">
            <div class="content mainContent">
              <div class="sidebar">Table of contents</div>
              <h1>Sample Class</h1>
              <p>Retained Qt 6 content for full text search.</p>
              <h2 id="details">Detailed Description</h2>
              <p>Details with a <a href="qother.html#member">related class</a>.</p>
            </div>
          </div>
          <div class="footer">copyright chrome</div>
        </body></html>
        """,
        encoding="utf-8",
    )
    return root


def test_qt6_docset_detection_reading_and_search(tmp_path: Path) -> None:
    docs = _qt6_docs(tmp_path)
    settings = Settings(
        qt_doc_base=docs,
        md_cache_dir=tmp_path / "cache",
        index_db_path=tmp_path / "index" / "fts.sqlite",
        preconvert_md=False,
        preindex_docs=False,
    )
    ensure_dirs(settings)

    assert settings.docset is not None
    assert settings.docset.key == "qt6.8"
    assert settings.docset.canonical_prefix == "/qt-6.8/"

    url = "https://doc.qt.io/qt-6.8/qtcore/qsample.html"
    doc = get_markdown_for_url(url, settings)
    assert "Retained Qt 6 content" in doc.markdown
    assert doc.links[0]["url"] == "https://doc.qt.io/qt-6.8/qtcore/qother.html#member"

    stats = build_index(settings.index_db_path, docs, docset=settings.docset)
    assert stats == {"indexed": 1, "skipped": 0, "errors": 0}
    assert index_matches_docs(settings.index_db_path, docs, settings.docset)
    results = search(settings.index_db_path, "Retained")
    assert results[0].url == url
    assert "Retained" in results[0].context


def test_cache_is_invalidated_when_docset_changes(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    qt5 = tmp_path / "Qt-5.15.2"
    qt6 = tmp_path / "Qt-6.8.2"
    qt5.mkdir()
    qt6.mkdir()

    first = Settings(qt_doc_base=qt5, md_cache_dir=cache_dir)
    ensure_dirs(first)
    assert first.docset is not None and first.docset.key == "qt5"
    assert first.docset.canonical_prefix == "/qt-5/"
    stale_file = cache_dir / "stale.md"
    stale_file.write_text("old cache", encoding="utf-8")

    second = Settings(qt_doc_base=qt6, md_cache_dir=cache_dir)
    ensure_dirs(second)
    assert not stale_file.exists()
    assert second.docset is not None and second.docset.key == "qt6.8"
