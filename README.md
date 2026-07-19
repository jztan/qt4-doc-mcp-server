# Qt Documentation MCP Server

mcp-name: io.github.jztan/qt4-doc-mcp-server

[![PyPI Version](https://img.shields.io/pypi/v/qt4-doc-mcp-server.svg)](https://pypi.org/project/qt4-doc-mcp-server/)
[![License](https://img.shields.io/github/license/jztan/qt4-doc-mcp-server.svg)](LICENSE)
[![Python Version](https://img.shields.io/pypi/pyversions/qt4-doc-mcp-server.svg)](https://pypi.org/project/qt4-doc-mcp-server/)
[![GitHub Issues](https://img.shields.io/github/issues/jztan/qt4-doc-mcp-server.svg)](https://github.com/jztan/qt4-doc-mcp-server/issues)
[![CI](https://github.com/jztan/qt4-doc-mcp-server/actions/workflows/pr-tests.yml/badge.svg)](https://github.com/jztan/qt4-doc-mcp-server/actions/workflows/pr-tests.yml)
[![Downloads](https://pepy.tech/badge/qt4-doc-mcp-server)](https://pepy.tech/project/qt4-doc-mcp-server)

Bring locally installed Qt 4.8, Qt 5, or Qt 6 documentation to your AI coding assistant. Works offline with one selected documentation set at a time.

## [Tool Reference](./docs/TOOL_REFERENCE.md) | [Changelog](./CHANGELOG.md) | [Contributing](./docs/CONTRIBUTING.md) | [Troubleshooting](./docs/TROUBLESHOOTING.md)

## ✨ Features
- 🔌 **Offline-First** - Works entirely with local documentation
- 🔍 **Full-Text Search** - Find what you need across all Qt docs
- ⚡ **Smart Caching** - Fast responses for repeated queries
- 🎯 **Fragment Support** - Extract specific sections when needed
- 🛠️ **MCP Standard** - Compatible with Claude, VS Code, and other MCP clients

## 📦 Prerequisites
- **Python 3.11+** required
- **Qt HTML Documentation** for one supported release (Qt 4.8, Qt 5, or Qt 6)
  - The included helper downloads Qt 4.8.4 only.
  - Point `QT_DOC_BASE` directly at an existing Qt 5/6 offline documentation root.
- **~500MB disk space** for docs + cache + search index
- **SQLite with FTS5 support** (included in Python 3.11+ by default)

## 🚀 Installation

### From PyPI (Recommended)
```bash
pip install qt4-doc-mcp-server
```

### From Source
```bash
git clone https://github.com/jztan/qt4-doc-mcp-server.git
cd qt4-doc-mcp-server
uv sync --locked
```

### Setup Qt Documentation
```bash
# Automated setup (recommended)
python scripts/prepare_qt48_docs.py --segments 4

# This will:
# - Download Qt 4.8.4 source archive
# - Extract HTML documentation
# - Create .env with sensible defaults
# - Copy GFDL license file
```

### Quick Start Commands
```bash
# 1. Install
pip install qt4-doc-mcp-server

# 2. Setup Qt docs
python scripts/prepare_qt48_docs.py --segments 4

# 3. Build search index
qt-doc-build-index

# 4. Start server
qt-doc-mcp

# 5. Verify health
curl -s http://127.0.0.1:8000/health
```

The legacy `qt4-doc-mcp-server` command remains available as an alias for existing client configurations.

### Agent-friendly FTS CLI

After building the index, agents can search and receive materialized absolute Markdown paths:

```bash
qt-doc-cli "accessible applications" --limit 5
```

The command reads the same `.env` settings as the server. Before searching, it automatically builds a missing/outdated FTS index and fully warms an incomplete Markdown cache. It then prints each result's title, absolute `.md` path, and FTS snippet to stdout; preparation messages, errors, and warnings go to stderr. Use `qt-doc-warm-md --force` after changing documentation in place.

## 🐳 Docker

Prebuilt multi-arch images (amd64/arm64) are published to GitHub Container Registry on every release. The container is offline-only: you mount your prepared Qt `doc/html` directory read-only at `/docs`, and all derived state (Markdown cache and search index) lives in a volume at `/data`.

```bash
# Prepare Qt docs on the host first (one-time)
python scripts/prepare_qt48_docs.py --segments 4

# Run from GHCR
docker run -d --name qt4-doc-mcp-server -p 8000:8000 \
  -v /path/to/qt-docs/html:/docs:ro \
  -v qt4-doc-data:/data \
  ghcr.io/jztan/qt4-doc-mcp-server:latest

# Verify
curl -s http://127.0.0.1:8000/health
```

First start converts and indexes the documentation into the `/data` volume; subsequent starts reuse it. Depending on the docset size, the first start can take a minute or two before the health endpoint responds.

### Docker Compose

```bash
cp .env.docker.example .env.docker   # set QT_DOC_HTML_PATH
docker compose --env-file .env.docker up -d
```

Point your MCP client at `http://127.0.0.1:8000/mcp` (streamable HTTP). Qt documentation is licensed under GFDL 1.3; the container serves your local copy and never redistributes it.

## ⚙️ Configuration
Create a `.env` file in the repo root. The helper script writes sensible defaults; adjust as needed:

| Variable | Default | Purpose |
| --- | --- | --- |
| `QT_DOC_BASE` | _required_ | Absolute path to one Qt 4.8, Qt 5, or Qt 6 HTML documentation root. The server detects the active docset. |
| `QT_DOC_STATE_DIR` | `$QT_DOC_BASE/.index` | Optional writable directory for the FTS index and Markdown cache. Use this when the documentation root is read-only. |
| `PREINDEX_DOCS` | `true` | Build search index automatically at startup if not present. |
| `PRECONVERT_MD` | `false` | Warm the Markdown cache automatically at MCP startup. |
| `SERVER_HOST` | `127.0.0.1` | Bind address for the FastMCP server (`0.0.0.0` for containers). |
| `SERVER_PORT` | `8000` | TCP port for streamable HTTP transport. |
| `MCP_LOG_LEVEL` | `WARNING` | Logging verbosity (DEBUG/INFO/WARNING/ERROR). |
| `MD_CACHE_SIZE` | `512` | In-memory CachedDoc LRU capacity (counts pages). |
| `DEFAULT_MAX_MARKDOWN_LENGTH` | `20000` | Default maximum characters returned per request (prevents token limit issues). |

The tools identify documents by their exact root-relative Markdown path, not an online URL. For example, use `qcompleter.md` for a Qt 4 page, `qtdoc/accessible.md` for a Qt 5/6 global page, or `qtcore/qobject.md` for a Qt 5/6 Core page. By default, each docset stores its own index and Markdown cache under `$QT_DOC_BASE/.index/`, so switching `QT_DOC_BASE` reuses its existing derived state. Set `QT_DOC_STATE_DIR` to relocate both to a writable directory. The Markdown cache mirrors the documentation tree: for example, `qtcore/qobject.md` is cached as `.index/md/qtcore/qobject.md` plus `qobject.meta.json` with the default state directory.

## 🔌 MCP Client Setup

By default, the server exposes an HTTP endpoint at `http://127.0.0.1:8000/mcp`. Register it with your preferred MCP-compatible agent using the instructions below.

### Stdio transport

Run the server over stdio instead of HTTP with:

```bash
qt-doc-mcp --transport stdio
```

For stdio-only MCP clients, configure that command with `args: ["--transport", "stdio"]`. Startup indexing and Markdown-cache progress are written to stderr, leaving stdout exclusively for MCP protocol messages.

<details>
<summary><strong>Visual Studio Code (Native MCP Support)</strong></summary>

VS Code has built-in MCP support via GitHub Copilot (requires VS Code 1.102+).

**Using CLI (Quickest):**
```bash
code --add-mcp '{"name":"qt-docs","type":"http","url":"http://127.0.0.1:8000/mcp"}'
```

**Using Command Palette:**
1. Open Command Palette (`Cmd/Ctrl+Shift+P`)
2. Run `MCP: Open User Configuration` (for global) or `MCP: Open Workspace Folder Configuration` (for project-specific)
3. Add the configuration:
   ```json
   {
     "servers": {
       "qt-docs": {
         "type": "http",
         "url": "http://127.0.0.1:8000/mcp"
       }
     }
   }
   ```
4. Save the file. VS Code will automatically load the MCP server.

**Manual Configuration:**
Create `.vscode/mcp.json` in your workspace (or `mcp.json` in your user profile directory):
```json
{
  "servers": {
    "qt-docs": {
      "type": "http",
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

</details>

<details>
<summary><strong>Claude Code</strong></summary>

Add to Claude Code using the CLI command:

```bash
claude mcp add --transport http qt-docs http://127.0.0.1:8000/mcp
```

Or configure manually in your Claude Code settings file (`~/.claude.json`):

```json
{
  "mcpServers": {
    "qt-docs": {
      "type": "http",
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

</details>

<details>
<summary><strong>Codex CLI</strong></summary>

Add to Codex CLI using the command:

```bash
codex mcp add qt-docs -- npx -y mcp-client-http http://127.0.0.1:8000/mcp
```

Or configure manually in `~/.codex/config.toml`:

```toml
[mcp_servers.qt-docs]
command = "npx"
args = ["-y", "mcp-client-http", "http://127.0.0.1:8000/mcp"]
```

**Note:** Codex CLI primarily supports stdio-based MCP servers. The above uses `mcp-client-http` as a bridge for HTTP transport.

</details>

<details>
<summary><strong>Kiro</strong></summary>

Kiro primarily supports stdio-based MCP servers. For HTTP servers, use an HTTP-to-stdio bridge:

1. Create or edit `.kiro/settings/mcp.json` in your workspace:
   ```json
   {
     "mcpServers": {
       "qt-docs": {
         "command": "npx",
         "args": [
           "-y",
           "mcp-client-http",
           "http://127.0.0.1:8000/mcp"
         ],
         "disabled": false
       }
     }
   }
   ```
2. Save the file and restart Kiro. The active Qt documentation tools will appear in the MCP panel.

**Note:** Direct HTTP transport support in Kiro is limited. The above configuration uses `mcp-client-http` as a bridge to connect to HTTP MCP servers.

</details>

<details>
<summary><strong>Generic MCP Clients</strong></summary>

Most MCP clients use a standard configuration format. For HTTP servers:

```json
{
  "mcpServers": {
    "qt-docs": {
      "type": "http",
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

For clients that require a command-based approach with HTTP bridge:

```json
{
  "mcpServers": {
    "qt-docs": {
      "command": "npx",
      "args": ["-y", "mcp-client-http", "http://127.0.0.1:8000/mcp"]
    }
  }
}
```

</details>

## 🛠️ Available Tools

The server provides **2 MCP tools** for working with the active local Qt documentation set:

1. **`read_documentation`** - Read and convert pages from the active Qt documentation set to Markdown
   - Fragment extraction (`#details`, `#public-functions`)
   - Pagination with `start_index` and `max_length`
   - Section-only mode for targeted content
   - Returns Markdown with normalized links and GFDL attribution

2. **`search_documentation`** - Full-text search across the active Qt documentation set
   - SQLite FTS5 with BM25 relevance ranking
   - Context snippets with highlighted matches
   - Configurable result limits (default: 10, max: 50)

For detailed API documentation including parameters, return values, examples, and error handling, see the **[Tool Reference](docs/TOOL_REFERENCE.md)**.

## 📚 Related Resources

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Qt Documentation](https://doc.qt.io/)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)
- [Tool Reference](docs/TOOL_REFERENCE.md)
- [Changelog](CHANGELOG.md)
- [Contributing Guide](docs/CONTRIBUTING.md)
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md)

## 📄 License
- **Code:** MIT License (see `LICENSE`).
- **Qt Documentation:** © The Qt Company Ltd. and contributors, licensed under GFDL 1.3. This server
  converts locally obtained docs and includes attribution in outputs. If you
  redistribute a local mirror, include `LICENSE.FDL` and preserve notices.
- See `THIRD_PARTY_NOTICES.md` for more details.
