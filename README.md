# Qt 4.8.4 Documentation MCP Server

[![PyPI Version](https://img.shields.io/pypi/v/qt4-doc-mcp-server.svg)](https://pypi.org/project/qt4-doc-mcp-server/)
[![License](https://img.shields.io/github/license/jztan/qt4-doc-mcp-server.svg)](LICENSE)
[![Python Version](https://img.shields.io/pypi/pyversions/qt4-doc-mcp-server.svg)](https://pypi.org/project/qt4-doc-mcp-server/)
[![GitHub Issues](https://img.shields.io/github/issues/jztan/qt4-doc-mcp-server.svg)](https://github.com/jztan/qt4-doc-mcp-server/issues)
[![CI](https://github.com/jztan/qt4-doc-mcp-server/actions/workflows/pr-tests.yml/badge.svg)](https://github.com/jztan/qt4-doc-mcp-server/actions/workflows/pr-tests.yml)

Offline‑only MCP Server that serves Qt 4.8.4 documentation to Agents/LLMs and IDEs.
It loads local HTML docs, converts pages to Markdown, and provides fast full‑text
search via SQLite FTS5.

## Quickstart
1. Install the package: `pip install qt4-doc-mcp-server`.
2. Fetch and stage the Qt docs (one-time): `python scripts/prepare_qt48_docs.py --segments 4`.
3. Copy `.env` from the script output or create one manually (see table below).
4. Build the search index: `qt4-doc-build-index` (required for search functionality).
5. Run the server: `qt4-doc-mcp-server` (or `uv run python -m qt4_doc_mcp_server.main`).
6. Verify health: `curl -s http://127.0.0.1:8000/health` → `{ "status": "ok" }`.
7. Optional: warm the Markdown cache for faster responses: `qt4-doc-warm-md`.

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
│     ├─ tools.py               # MCP tools (read_documentation, search_documentation)
│     ├─ fetcher.py             # Canonical URL + local path mapping
│     ├─ convert.py             # HTML extraction, link normalization, HTML→Markdown
│     ├─ cache.py               # LRU + Markdown store (disk) helpers
│     ├─ doc_service.py         # Read path orchestration (store + convert)
│     ├─ search.py              # FTS5 index build/query with BM25 ranking
│     └─ cli.py                 # CLI utilities (qt4-doc-warm-md, qt4-doc-build-index)
└─ tests/                       # pytest suite (e.g., test_doc_service.py)
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
Create a `.env` file in the repo root. The helper script writes sensible defaults; adjust as needed:

| Variable | Default | Purpose |
| --- | --- | --- |
| `QT_DOC_BASE` | _required_ | Absolute path to the Qt 4.8.4 HTML docs (`.../doc/html`). |
| `INDEX_DB_PATH` | `.index/fts.sqlite` | Location of the SQLite FTS5 search index. |
| `MD_CACHE_DIR` | `.cache/md` | Directory for cached Markdown blobs + metadata. |
| `PREINDEX_DOCS` | `true` | Build search index automatically at startup if not present. |
| `PRECONVERT_MD` | `true` | Warm the Markdown cache automatically at startup. |
| `SERVER_HOST` | `127.0.0.1` | Bind address for the FastMCP server (`0.0.0.0` for containers). |
| `SERVER_PORT` | `8000` | TCP port for streamable HTTP transport. |
| `MCP_LOG_LEVEL` | `WARNING` | Logging verbosity (DEBUG/INFO/WARNING/ERROR). |
| `MD_CACHE_SIZE` | `512` | In-memory CachedDoc LRU capacity (counts pages). |
| `DEFAULT_MAX_MARKDOWN_LENGTH` | `20000` | Default maximum characters returned per request (prevents token limit issues). |

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

# Build the search index (required for search_documentation tool)
uv run qt4-doc-build-index

# Optional: preconvert all HTML→Markdown into the store for faster reads
uv run qt4-doc-warm-md

# Run tests (ensure TMPDIR points to a writable location when sandboxed)
uv run python -m pytest -q
```

## How It Works (high‑level)
- Offline‑only: no external HTTP fetches; everything reads from `QT_DOC_BASE`.
- HTML→Markdown: focused extraction of main content; normalized internal links;
  attribution appended.
- Markdown store: preconverted pages saved under `.cache/md` (sharded by URL hash)
  for fast reads; in‑memory LRU caches hot pages.
- Search: SQLite FTS5 index (title/headings/body) with BM25 ranking and context snippets.

## MCP Tools

The server provides two MCP tools:

1. **`read_documentation`** - Read and convert a specific Qt documentation page
2. **`search_documentation`** - Search across all Qt 4.8.4 documentation

### Example: read_documentation

Example MCP request/response (trimmed for brevity):

```json
// request
{
  "method": "tools/run",
  "params": {
    "name": "read_documentation",
    "arguments": {
      "url": "https://doc.qt.io/archives/qt-4.8/qstring.html",
      "fragment": "#details",
      "section_only": true,
      "max_length": 2000
    }
  }
}

// response
{
  "result": {
    "title": "QString Class",
    "canonical_url": "https://doc.qt.io/archives/qt-4.8/qstring.html",
    "markdown": "# QString Class\n...",
    "links": [
      {"text": "QStringList", "url": "https://doc.qt.io/archives/qt-4.8/qstringlist.html"}
    ],
    "attribution": "Content © The Qt Company Ltd./Digia — GNU Free Documentation License 1.3",
    "content_info": {
      "total_length": 15234,
      "returned_length": 2000,
      "start_index": 0,
      "truncated": true
    }
  }
}
```

**Note**: The `content_info` field appears when content is paginated or truncated. Use `start_index` and `max_length` parameters to retrieve additional pages. By default, responses are limited to 20,000 characters to avoid exceeding LLM token limits.

### Example: search_documentation

Example MCP request/response for searching:

```json
// request
{
  "method": "tools/run",
  "params": {
    "name": "search_documentation",
    "arguments": {
      "query": "signals slots",
      "limit": 5
    }
  }
}

// response
{
  "result": {
    "query": "signals slots",
    "count": 5,
    "results": [
      {
        "title": "Signals and Slots",
        "url": "https://doc.qt.io/archives/qt-4.8/signalsandslots.html",
        "score": 12.34,
        "context": "…used for communication between objects. <b>Signals</b> and <b>slots</b> mechanism is a central…"
      },
      {
        "title": "QObject Class Reference",
        "url": "https://doc.qt.io/archives/qt-4.8/qobject.html",
        "score": 8.76,
        "context": "…The QObject class supports <b>signals</b> and <b>slots</b> for inter-object communication…"
      }
    ]
  }
}
```

**Notes**:
- Search uses SQLite FTS5 with BM25 ranking for relevance
- Context snippets highlight matching terms with `<b>` tags
- The `limit` parameter controls maximum results (default: 10, max: 50)
- Build the index first with `qt4-doc-build-index` or set `PREINDEX_DOCS=true`

## Deployment
- **Direct (systemd, bare metal, CI runners):**
  - Install with `pip install qt4-doc-mcp-server`.
  - Ensure `.env` points to your Qt docs and writable cache/index directories.
  - Start with `qt4-doc-mcp-server`; add `PRECONVERT_MD=true` for faster first reads.
- **Containerization (roadmap):**
  - Docker support is planned; follow the repository for updates or open an issue if you need it sooner.

## Licensing
- Code: MIT License (see `LICENSE`).
- Qt docs: © The Qt Company Ltd./Digia, licensed under GFDL 1.3. This server
  converts locally obtained docs and includes attribution in outputs. If you
  redistribute a local mirror, include `LICENSE.FDL` and preserve notices.
- See `THIRD_PARTY_NOTICES.md` for more.
