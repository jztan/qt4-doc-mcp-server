# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project adheres to Semantic Versioning.

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
