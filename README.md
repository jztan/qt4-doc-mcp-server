# Qt 4.8.4 Documentation MCP Server

Offline‑only MCP Server that serves Qt 4.8.4 documentation to Agents/LLMs and IDEs.
It loads local HTML docs, converts pages to Markdown, and provides fast full‑text
search via SQLite FTS5.

 

## Project Structure

```
.
├─ README.md                    # Quick start, config, licensing
├─ LICENSE                      # MIT license for this codebase
├─ CHANGELOG.md                 # Keep a Changelog (Unreleased + releases)
├─ THIRD_PARTY_NOTICES.md       # Qt docs and deps licensing notes
├─ pyproject.toml               # Packaging, deps, console entry points
├─ scripts/
│  ├─ prepare_qt48_docs.py      # Download, extract, and stage Qt 4.8.4 docs; writes .env
├─ src/
│  └─ qt4_doc_mcp_server/
│     ├─ __init__.py            # Package version
│     ├─ main.py                # FastMCP app (+ /health) and CLI run()
│     ├─ config.py              # Env loader (dotenv) + startup checks
│     ├─ tools.py               # MCP tools (to be wired: read/search)
│     ├─ fetcher.py             # Canonical URL + local path mapping
│     ├─ convert.py             # HTML extraction, link normalization, HTML→Markdown
│     ├─ cache.py               # LRU + Markdown store (disk) helpers
│     ├─ doc_service.py         # Read path orchestration (store + convert)
│     ├─ search.py              # FTS5 index build/query stubs
│     └─ cli.py                 # Warm‑MD CLI entry (qt4-doc-warm-md)
└─ tests/                       # (planned) unit/integration tests
```

## Requirements
- Python 3.11+
- Local Qt 4.8.4 HTML documentation (see below)

## Get the Qt 4.8.4 Docs

### Prepare Docs with Python helper (recommended)

```
python scripts/prepare_qt48_docs.py # copy docs by default into ./qt4-docs-html
```
OR
```
python scripts/prepare_qt48_docs.py --segments 4 # faster download with 4 segments
```

This will:
- Download and extract the Qt 4.8.4 source archive (or reuse if present)
- Stage the HTML docs at `qt4-docs-html` (symlink by default)
- Copy `LICENSE.FDL` next to the docs
- Create/update `.env` with `QT_DOC_BASE` and sensible defaults



## Configure (dotenv)
Create a `.env` file in the repo (defaults shown):

```
QT_DOC_BASE=/absolute/path/to/qt-everywhere-opensource-src-4.8.4/doc/html
INDEX_DB_PATH=.index/fts.sqlite
MD_CACHE_DIR=.cache/md
PREINDEX_DOCS=true
PRECONVERT_MD=true
SERVER_HOST=127.0.0.1
SERVER_PORT=8000
MCP_LOG_LEVEL=WARNING
MD_CACHE_SIZE=512
```

## Dev Setup and Run
```
uv venv .venv && source .venv/bin/activate

# Option 1: run without installing the package (dev-only)
# Using uv to run the module directly
uv run python -m qt4_doc_mcp_server.main

# Option 2: install and use the CLI
uv pip install -e .[dev]
qt4-doc-mcp-server
# Health check
curl -s http://127.0.0.1:8000/health
 
# Optional: preconvert all HTML→Markdown into the store for faster reads
uv run qt4-doc-warm-md
```

## How It Works (high‑level)
- Offline‑only: no external HTTP fetches; everything reads from `QT_DOC_BASE`.
- HTML→Markdown: focused extraction of main content; normalized internal links;
  attribution appended.
- Markdown store: preconverted pages saved under `.cache/md` (sharded by URL hash)
  for fast reads; in‑memory LRU caches hot pages.
- Search: SQLite FTS5 index (title/headings/body) with bm25 ranking and snippets.

## Docker (concept)
- Mount local docs at `/docs` and optional volumes for index and MD store.
- Set envs: `QT_DOC_BASE=/docs`, `INDEX_DB_PATH=/data/index/fts.sqlite`,
  `MD_CACHE_DIR=/data/md`, `PREINDEX_DOCS=true`, `PRECONVERT_MD=true`.

## Licensing
- Code: MIT License (see `LICENSE`).
- Qt docs: © The Qt Company Ltd./Digia, licensed under GFDL 1.3. This server
  converts locally obtained docs and includes attribution in outputs. If you
  redistribute a local mirror, include `LICENSE.FDL` and preserve notices.
- See `THIRD_PARTY_NOTICES.md` for more.

## Status
This repo currently contains the specification, design, tasks, and initial
scaffold. Implementation proceeds per TASKS.md.
