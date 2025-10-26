# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project adheres to Semantic Versioning.

## [Unreleased]

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
