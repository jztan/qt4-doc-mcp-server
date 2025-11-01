# Qt 4.8.4 Documentation MCP Server

[![PyPI Version](https://img.shields.io/pypi/v/qt4-doc-mcp-server.svg)](https://pypi.org/project/qt4-doc-mcp-server/)
[![License](https://img.shields.io/github/license/jztan/qt4-doc-mcp-server.svg)](LICENSE)
[![Python Version](https://img.shields.io/pypi/pyversions/qt4-doc-mcp-server.svg)](https://pypi.org/project/qt4-doc-mcp-server/)
[![GitHub Issues](https://img.shields.io/github/issues/jztan/qt4-doc-mcp-server.svg)](https://github.com/jztan/qt4-doc-mcp-server/issues)
[![CI](https://github.com/jztan/qt4-doc-mcp-server/actions/workflows/pr-tests.yml/badge.svg)](https://github.com/jztan/qt4-doc-mcp-server/actions/workflows/pr-tests.yml)
[![Downloads](https://pepy.tech/badge/qt4-doc-mcp-server)](https://pepy.tech/project/qt4-doc-mcp-server)

Bring Qt 4.8.4 documentation to your AI coding assistant. Works offline with local docs.

## [Tool Reference](./docs/TOOL_REFERENCE.md) | [Changelog](./CHANGELOG.md) | [Contributing](./docs/CONTRIBUTING.md) | [Troubleshooting](./docs/TROUBLESHOOTING.md)

## ✨ Features
- 🔌 **Offline-First** - Works entirely with local documentation
- 🔍 **Full-Text Search** - Find what you need across all Qt docs
- ⚡ **Smart Caching** - Fast responses for repeated queries
- 🎯 **Fragment Support** - Extract specific sections when needed
- 🛠️ **MCP Standard** - Compatible with Claude, VS Code, and other MCP clients

## 📦 Prerequisites
- **Python 3.11+** required
- **Qt 4.8.4 HTML Documentation**
  - Download automatically via included script, or
  - Manual download from qt.io archives
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
pip install -e .[dev]
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
qt4-doc-build-index

# 4. Start server
qt4-doc-mcp-server

# 5. Verify health
curl -s http://127.0.0.1:8000/health
```

## ⚙️ Configuration
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

## 🔌 MCP Client Setup

The server exposes an HTTP endpoint at `http://127.0.0.1:8000/mcp`. Register it with your preferred MCP-compatible agent using the instructions below.

<details>
<summary><strong>Visual Studio Code (Native MCP Support)</strong></summary>

VS Code has built-in MCP support via GitHub Copilot (requires VS Code 1.102+).

**Using CLI (Quickest):**
```bash
code --add-mcp '{"name":"qt4-docs","type":"http","url":"http://127.0.0.1:8000/mcp"}'
```

**Using Command Palette:**
1. Open Command Palette (`Cmd/Ctrl+Shift+P`)
2. Run `MCP: Open User Configuration` (for global) or `MCP: Open Workspace Folder Configuration` (for project-specific)
3. Add the configuration:
   ```json
   {
     "servers": {
       "qt4-docs": {
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
    "qt4-docs": {
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
claude mcp add --transport http qt4-docs http://127.0.0.1:8000/mcp
```

Or configure manually in your Claude Code settings file (`~/.claude.json`):

```json
{
  "mcpServers": {
    "qt4-docs": {
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
codex mcp add qt4-docs -- npx -y mcp-client-http http://127.0.0.1:8000/mcp
```

Or configure manually in `~/.codex/config.toml`:

```toml
[mcp_servers.qt4-docs]
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
       "qt4-docs": {
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
2. Save the file and restart Kiro. The Qt 4.8.4 documentation tools will appear in the MCP panel.

**Note:** Direct HTTP transport support in Kiro is limited. The above configuration uses `mcp-client-http` as a bridge to connect to HTTP MCP servers.

</details>

<details>
<summary><strong>Generic MCP Clients</strong></summary>

Most MCP clients use a standard configuration format. For HTTP servers:

```json
{
  "mcpServers": {
    "qt4-docs": {
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
    "qt4-docs": {
      "command": "npx",
      "args": ["-y", "mcp-client-http", "http://127.0.0.1:8000/mcp"]
    }
  }
}
```

</details>

## 🛠️ Available Tools

The server provides **2 MCP tools** for working with Qt 4.8.4 documentation:

1. **`read_documentation`** - Read and convert specific Qt documentation pages to Markdown
   - Fragment extraction (`#details`, `#public-functions`)
   - Pagination with `start_index` and `max_length`
   - Section-only mode for targeted content
   - Returns Markdown with normalized links and GFDL attribution

2. **`search_documentation`** - Full-text search across all Qt 4.8.4 documentation
   - SQLite FTS5 with BM25 relevance ranking
   - Context snippets with highlighted matches
   - Configurable result limits (default: 10, max: 50)

For detailed API documentation including parameters, return values, examples, and error handling, see the **[Tool Reference](docs/TOOL_REFERENCE.md)**.

## 📚 Related Resources

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Qt 4.8.4 Documentation Archive](https://doc.qt.io/archives/qt-4.8/)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)
- [Tool Reference](docs/TOOL_REFERENCE.md)
- [Changelog](CHANGELOG.md)
- [Contributing Guide](docs/CONTRIBUTING.md)
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md)

## 📄 License
- **Code:** MIT License (see `LICENSE`).
- **Qt Documentation:** © The Qt Company Ltd./Digia, licensed under GFDL 1.3. This server
  converts locally obtained docs and includes attribution in outputs. If you
  redistribute a local mirror, include `LICENSE.FDL` and preserve notices.
- See `THIRD_PARTY_NOTICES.md` for more details.
