from pathlib import Path

from qt4_doc_mcp_server.config import (
    Settings,
    ensure_dirs,
    index_db_path,
    load_settings,
    markdown_cache_dir,
    validate_settings,
)
from qt4_doc_mcp_server.doc_service import get_markdown_for_path
from qt4_doc_mcp_server.search import build_index, index_is_current, search


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
        preconvert_md=False,
        preindex_docs=False,
    )
    ensure_dirs(settings)

    assert settings.docset is not None
    assert settings.docset.key == "qt6.8"
    assert index_db_path(settings) == docs / ".index" / "fts.sqlite"
    assert markdown_cache_dir(settings) == docs / ".index" / "md"
    document_path = "qtcore/qsample.md"
    doc = get_markdown_for_path(document_path, settings)
    assert "Retained Qt 6 content" in doc.markdown
    assert doc.links[0]["path"] == "qtcore/qother.md#member"

    stats = build_index(index_db_path(settings), docs)
    assert stats == {"indexed": 1, "skipped": 0, "errors": 0}
    assert index_is_current(index_db_path(settings))
    results = search(index_db_path(settings), "Retained")
    assert results[0].path == document_path
    assert "Retained" in results[0].context


def test_qt5_qtdoc_pages_retain_local_paths(tmp_path: Path) -> None:
    docs = tmp_path / "Qt-5.15.2"
    page = docs / "qtdoc" / "accessible.html"
    page.parent.mkdir(parents=True)
    page.write_text(
        """
        <html><head><title>Accessibility | Qt 5.15.2</title></head>
        <body><div class="header"><div class="content mainContent">
        <h1>Accessibility</h1><p>Accessible application content.</p>
        </div></div></body></html>
        """,
        encoding="utf-8",
    )
    settings = Settings(
        qt_doc_base=docs,
        preconvert_md=False,
        preindex_docs=False,
    )
    ensure_dirs(settings)
    assert settings.docset is not None

    document_path = "qtdoc/accessible.md"
    assert "Accessible application content" in get_markdown_for_path(document_path, settings).markdown

    build_index(index_db_path(settings), docs)
    assert search(index_db_path(settings), "Accessible")[0].path == document_path


def test_each_docset_has_its_own_derived_state(tmp_path: Path) -> None:
    qt5 = tmp_path / "Qt-5.15.2"
    qt6 = tmp_path / "Qt-6.8.2"
    qt5.mkdir()
    qt6.mkdir()

    first = Settings(qt_doc_base=qt5)
    ensure_dirs(first)
    assert first.docset is not None and first.docset.key == "qt5"
    stale_file = markdown_cache_dir(first) / "stale.md"
    stale_file.write_text("old cache", encoding="utf-8")

    second = Settings(qt_doc_base=qt6)
    ensure_dirs(second)
    assert stale_file.exists()
    assert markdown_cache_dir(second) != markdown_cache_dir(first)
    assert second.docset is not None and second.docset.key == "qt6.8"


def test_state_dir_can_be_relocated_for_read_only_docs(tmp_path: Path) -> None:
    docs = _qt6_docs(tmp_path)
    state_dir = tmp_path / "writable-state"
    settings = Settings(qt_doc_base=docs, qt_doc_state_dir=state_dir)

    ensure_dirs(settings)

    assert index_db_path(settings) == state_dir / "fts.sqlite"
    assert markdown_cache_dir(settings) == state_dir / "md"
    assert markdown_cache_dir(settings).is_dir()


def test_load_settings_warns_about_removed_state_variables(
    tmp_path: Path, monkeypatch
) -> None:
    docs = _qt6_docs(tmp_path)
    state_dir = tmp_path / "state"
    monkeypatch.setenv("QT_DOC_BASE", str(docs))
    monkeypatch.setenv("QT_DOC_STATE_DIR", str(state_dir))
    monkeypatch.setenv("INDEX_DB_PATH", str(tmp_path / "old.sqlite"))
    monkeypatch.setenv("MD_CACHE_DIR", str(tmp_path / "old-cache"))

    settings = load_settings()
    ok, warnings = validate_settings(settings)

    assert ok
    assert settings.qt_doc_state_dir == state_dir
    assert index_db_path(settings) == state_dir / "fts.sqlite"
    assert any("INDEX_DB_PATH" in warning and "ignored" in warning for warning in warnings)
    assert any("MD_CACHE_DIR" in warning and "ignored" in warning for warning in warnings)
