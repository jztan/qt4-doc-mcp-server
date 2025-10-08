# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project adheres to Semantic Versioning.

## [Unreleased]
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
