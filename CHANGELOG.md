# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Fixed
- Added the `mcp-name: io.github.jztan/qt4-doc-mcp-server` marker to the README
  so the MCP Registry can validate PyPI package ownership; the 0.6.0 registry
  publish failed because the marker was missing from the README on PyPI

## [0.6.0] - 2026-07-19
### Added
- Python 3.14 support: trove classifier and CI test matrix entry (full test suite passes on 3.14.2)
- Release automation script (`scripts/release.py`): gitflow release with preflight checks, version bumping, LLM-drafted release notes with approval loop, PyPI/workflow watching, GitHub release creation, and MCP Registry publish
- Dependency audit script (`scripts/audit.sh`) using pip-audit, run in CI and release preflight
- `server.json` manifest for MCP Registry publication
- Tests for release script helpers (version bumping, changelog stamping, notes persistence)
- Qt 5 and Qt 6 documentation support with automatic docset detection, so the
  server now works against any Qt 4/5/6 `doc/html` tree pointed at by
  `QT_DOC_BASE` ([#5](https://github.com/jztan/qt4-doc-mcp-server/pull/5))
- Stdio transport for MCP clients that spawn the server as a subprocess, and an
  agent-friendly `qt-doc-cli` full-text search command that works without
  installing an MCP client ([#5](https://github.com/jztan/qt4-doc-mcp-server/pull/5))
- `QT_DOC_STATE_DIR` override for storing all derived state (search index and
  Markdown cache) outside read-only documentation roots ([#5](https://github.com/jztan/qt4-doc-mcp-server/pull/5))

### Changed
- Dependency audit (`scripts/audit.sh`) now audits the exported `uv.lock` for a
  deterministic gate, and the release script regenerates and stages `uv.lock`
  during the version bump
- `server.json` and `docs/MCP_RESPONSE_EXAMPLES.md` updated for Qt 4/5/6
  support and the path-based tool API
- Updated `mcp[cli]` dependency: 1.19.0 → 1.28.1 (capped below 2.0 pre-releases)
- Updated `uvicorn` dependency: 0.38.0 → 0.51.0
- Updated `python-dotenv` dependency: 1.1.1 → 1.2.2
- Updated `beautifulsoup4` dependency: 4.14.0 → 4.15.0
- Updated `markdownify` dependency: 1.2.0 → 1.2.3
- Updated `lxml` dependency: 6.0.0 → 6.1.1
- Updated dev dependencies: pytest 9.x, pytest-asyncio 1.4, ruff 0.15
- New CLI commands use the `qt-doc-*` prefix; `qt4-doc-mcp-server` remains as a
  compatibility alias ([#5](https://github.com/jztan/qt4-doc-mcp-server/pull/5))

### Breaking
- Document identifiers and MCP tool parameters now use root-relative Markdown
  `path` values instead of online `url` values. Update MCP callers to pass and
  consume `path` values, and the generated Markdown store is now browsable
  directly on disk ([#5](https://github.com/jztan/qt4-doc-mcp-server/pull/5))
- Search indexes and Markdown caches now default to `$QT_DOC_BASE/.index`. Old
  working-directory `.index` and `.cache` directories are not migrated and can
  be removed after rebuilding derived state in the new location (or in
  `QT_DOC_STATE_DIR`) ([#5](https://github.com/jztan/qt4-doc-mcp-server/pull/5))
- `INDEX_DB_PATH` and `MD_CACHE_DIR` in existing `.env` files are now ignored
  with a startup warning; replace both with `QT_DOC_STATE_DIR` when a writable
  override is needed ([#5](https://github.com/jztan/qt4-doc-mcp-server/pull/5))
- `PRECONVERT_MD` now defaults to `false`; set `PRECONVERT_MD=true` explicitly
  to retain the previous eager Markdown warmup behavior ([#5](https://github.com/jztan/qt4-doc-mcp-server/pull/5))

### Fixed
- Removed unused imports and a membership-test style issue flagged by ruff 0.15
- Search and index-format SQLite connections are now opened read-only, allowing
  concurrent server instances without write access to the index
  ([#5](https://github.com/jztan/qt4-doc-mcp-server/pull/5))
- SQLite connections are closed after index-format checks
  ([#5](https://github.com/jztan/qt4-doc-mcp-server/pull/5))
- The Markdown cache completion marker is cleared before a forced, limited
  warmup, so a later full warmup is not skipped
  ([#5](https://github.com/jztan/qt4-doc-mcp-server/pull/5))
- `qt-doc-cli` now distinguishes an outdated search index from a missing one in
  its error output ([#5](https://github.com/jztan/qt4-doc-mcp-server/pull/5))

### Contributors
- @mrexodia, added Qt 5 and Qt 6 documentation support, stdio transport and the
  `qt-doc-cli` command, moved derived state under `$QT_DOC_BASE/.index` with a
  `QT_DOC_STATE_DIR` override, switched document identifiers to root-relative
  `path` values, and hardened concurrent index access
  ([#5](https://github.com/jztan/qt4-doc-mcp-server/pull/5))

## [0.5.0] - 2025-10-26
### Added
- SQLite FTS5 full-text search functionality with BM25 ranking and context snippets
- `search_documentation` MCP tool for searching across all Qt 4.8.4 documentation
- `qt4-doc-build-index` CLI command for building the search index
- `PREINDEX_DOCS` configuration option to automatically build search index at startup
- Comprehensive MCP client configuration guide in README (VS Code, Claude Code, Codex CLI, Kiro)
- Search index metadata persistence and deterministic build process
- Progress tracking with ETA for index building
- 14 new test cases for search functionality (total: 22 tests)

### Changed
- Updated `mcp[cli]` dependency: 1.14.1 → 1.19.0
- Updated `uvicorn` dependency: 0.30 → 0.38.0
- Updated `python-dotenv` dependency: 1.0 → 1.1.1
- Updated `beautifulsoup4` dependency: 4.12.0 → 4.14.0
- Updated `markdownify` dependency: 0.11.0 → 1.2.0 (major version)
- Updated `lxml` dependency: 4.9.0 → 6.0.0 (major version)
- Added `pytest-asyncio` to dev dependencies

### Fixed
- (none)

## [0.4.0] - 2025-10-08
### Added
- `DEFAULT_MAX_MARKDOWN_LENGTH` configuration setting (default: 20000 characters) to prevent response token limit issues
- `content_info` field in `read_documentation` responses showing pagination metadata when content is truncated
- Automatic application of default max length when `max_length` parameter is not explicitly provided

### Changed
- `read_documentation` now defaults to returning max 20,000 characters to avoid exceeding LLM token limits (e.g., Claude's 25,000 token limit)
- Enhanced docstring for `read_documentation` tool with detailed parameter and return value documentation

## [0.3.0] - 2025-10-06
### Fixed
- Windows compatibility: Use `posixpath.normpath()` for URL path normalization instead of `os.path.normpath()`
- Windows compatibility: Use `PurePosixPath` for platform-independent path handling in `url_to_path()`
- Explicit string conversion when passing `PurePosixPath` to `Path()` constructor for cross-platform compatibility

### Changed
- Moved `beautifulsoup4`, `markdownify`, and `lxml` from optional `[convert]` extras to required dependencies
- Simplified installation: `pip install qt4-doc-mcp-server` now includes all necessary dependencies
- Updated GitHub CI workflows to remove `[convert]` extras references
- Updated README.md to reflect simplified installation

### Added
- `.pytest_cache/` to `.gitignore`

## [0.2.1] - 2025-09-29
### Changed
- README synced with current structure and helpers

## [0.2.0] - 2025-09-29
### Added
- Structured `DocumentationError` taxonomy and pytest coverage for the read tool.

### Changed
- Shared FastMCP bootstrap that registers tools across every entry point.
- Markdown cache now stores titles and normalized link metadata for warm reads.
- `read_documentation` section-only responses preserve outbound links and chunking behaviour.
- README documents the local test workflow (`uv run python -m pytest -q`).

### Fixed
- MCP clients can reliably discover the `read_documentation` tool after server startup.

## [0.1.0] - 2025-09-28
### Added
- LICENSE (MIT) and THIRD_PARTY_NOTICES.md
- Python helper: `scripts/prepare_qt48_docs.py` (progress bars, ETA, segmented download)
- FastMCP server skeleton with `/health` and .env startup checks
- Converter pipeline (BeautifulSoup/markdownify fallback), Markdown store + LRU
- Warm‑MD CLI: `qt4-doc-warm-md` to preconvert all HTML→Markdown

### Changed
- Project/CLI/module names standardized to `qt4-doc-mcp-server` / `qt4_doc_mcp_server`
- README synced with current structure and helpers

### Removed
- (none)
