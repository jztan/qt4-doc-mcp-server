# Tool Reference

Complete reference for all MCP tools provided by the Qt 4.8.4 Documentation MCP Server.

## Available Tools

The server provides **2 MCP tools**:

1. [`read_documentation`](#read_documentation) - Read and convert Qt documentation pages
2. [`search_documentation`](#search_documentation) - Search across all Qt 4.8.4 documentation

---

## `read_documentation`

Read and convert specific Qt documentation pages to Markdown format.

### Features

- **Fragment extraction** - Extract specific sections using `#fragment` syntax (`#details`, `#public-functions`, etc.)
- **Pagination** - Control output size with `start_index` and `max_length` parameters
- **Normalized links** - All internal Qt links converted to canonical URLs
- **GFDL attribution** - Automatic licensing attribution appended
- **Section-only mode** - Return just the requested fragment without full page context

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | Yes | - | Qt documentation URL (canonical or relative) |
| `fragment` | string | No | `null` | HTML fragment ID to extract (e.g., `#details`) |
| `section_only` | boolean | No | `false` | If true, return only the fragment section |
| `start_index` | integer | No | `0` | Starting character index for pagination |
| `max_length` | integer | No | `20000` | Maximum characters to return |

### Return Value

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Page title extracted from HTML |
| `url` | string | Original URL requested by client |
| `canonical_url` | string | Normalized Qt documentation URL |
| `markdown` | string | Converted Markdown content |
| `links` | array | List of internal Qt documentation links with `text` and `url` |
| `attribution` | string | GFDL 1.3 license attribution |
| `content_info` | object | Pagination metadata (only when truncated) |

**`content_info` object** (appears when content is paginated):

| Field | Type | Description |
|-------|------|-------------|
| `total_length` | integer | Total length of full content |
| `returned_length` | integer | Length of content actually returned |
| `start_index` | integer | Starting position in full content |
| `truncated` | boolean | Whether content was truncated |

### Example Request

```json
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
```

### Example Response

```json
{
  "result": {
    "title": "QString Class",
    "url": "https://doc.qt.io/archives/qt-4.8/qstring.html",
    "canonical_url": "https://doc.qt.io/archives/qt-4.8/qstring.html",
    "markdown": "# QString Class\n\n## Detailed Description\n\nThe QString class provides...",
    "links": [
      {
        "text": "QStringList",
        "url": "https://doc.qt.io/archives/qt-4.8/qstringlist.html"
      },
      {
        "text": "QByteArray",
        "url": "https://doc.qt.io/archives/qt-4.8/qbytearray.html"
      }
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

### Usage Notes

**Pagination:**
- Default max length is 20,000 characters to prevent LLM token limit issues
- Use `start_index` to retrieve additional pages
- Check `content_info.truncated` to know if more content is available
- Next page: set `start_index` to `content_info.returned_length`

**Fragment Extraction:**
- Fragment IDs correspond to HTML anchor tags (e.g., `#public-functions`)
- Common fragments: `#details`, `#public-functions`, `#public-slots`, `#signals`, `#properties`
- Set `section_only=true` to get just the fragment without page header/footer
- Fragment extraction bypasses cache for fresh content

**URL Formats:**
- Canonical: `https://doc.qt.io/archives/qt-4.8/qstring.html`
- Relative: `qstring.html` (automatically normalized)
- With fragment: `qstring.html#details`

---

## `search_documentation`

Full-text search across all Qt 4.8.4 documentation using SQLite FTS5.

### Features

- **BM25 ranking** - Industry-standard relevance algorithm
- **Context snippets** - Highlighted excerpts showing match context
- **Multi-field search** - Searches title, headings, and body text
- **Configurable limits** - Control result count (default: 10, max: 50)
- **Fast indexing** - Deterministic index build for reproducible results

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query (FTS5 query syntax supported) |
| `limit` | integer | No | `10` | Maximum results to return (1-50) |
| `scope` | string | No | `"all"` | Search scope (currently only `"all"` supported) |

### Return Value

| Field | Type | Description |
|-------|------|-------------|
| `query` | string | Original query string |
| `count` | integer | Number of results returned |
| `results` | array | List of search results |

**`results` array items:**

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Page title |
| `url` | string | Canonical Qt documentation URL |
| `score` | float | BM25 relevance score (higher = more relevant) |
| `context` | string | Snippet with `<b>` tags highlighting matches |

### Example Request

```json
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
```

### Example Response

```json
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
      },
      {
        "title": "Signals & Slots",
        "url": "https://doc.qt.io/archives/qt-4.8/signalsandslots-syntaxes.html",
        "score": 7.23,
        "context": "…Connecting <b>signals</b> and <b>slots</b> with different syntaxes…"
      }
    ]
  }
}
```

### Usage Notes

**Search Query Syntax:**
- Simple terms: `QString` or `signals slots`
- Phrase search: `"signal slot"` (with quotes)
- Boolean operators: `signals AND slots`, `QString OR QByteArray`
- Prefix matching: `QStr*` matches QString, QStringList, etc.

**Result Ordering:**
- Results sorted by BM25 score (descending)
- Score reflects relevance based on term frequency and document length
- Title matches typically score higher than body matches

**Context Snippets:**
- Maximum ~10 words around each match
- Multiple matches may appear in single snippet
- `<b>` tags mark highlighted terms (not HTML escaped)
- Use `…` (ellipsis) to indicate truncation

**Index Building:**
- Build index with: `qt4-doc-build-index`
- Or set `PREINDEX_DOCS=true` in `.env` for automatic build
- Index typically 20-50MB, contains ~2000-3000 pages
- Rebuild with `--force` flag if docs are updated

**Scope Parameter** (future):
- Currently only `"all"` is supported
- Planned: `"api"` for class/function docs only
- Planned: `"guides"` for tutorial/overview pages only

---

## Error Handling

All tools return errors in standard MCP format:

```json
{
  "error": {
    "code": "ErrorCode",
    "message": "Human-readable error message"
  }
}
```

### Common Error Codes

| Code | Cause | Solution |
|------|-------|----------|
| `InvalidURL` | Malformed or unsupported URL | Check URL format matches Qt archives pattern |
| `NotAllowed` | URL outside Qt 4.8.4 docs scope | Use only Qt 4.8.4 documentation URLs |
| `NotFound` | Documentation file not found | Verify `QT_DOC_BASE` points to correct directory |
| `SearchUnavailable` | Search index not built | Run `qt4-doc-build-index` or set `PREINDEX_DOCS=true` |
| `ParseError` | HTML parsing failed | Check if HTML file is corrupted |
| `Timeout` | Operation took too long | Retry or contact support |

### Example Error Response

```json
{
  "error": {
    "code": "SearchUnavailable",
    "message": "Search index not found at .index/fts.sqlite. Run 'qt4-doc-build-index' to build the index."
  }
}
```

---

## Performance Characteristics

### `read_documentation`

- **First request:** 50-200ms (HTML parsing + Markdown conversion)
- **Cached request:** 5-20ms (served from disk or memory cache)
- **Fragment request:** Not cached (always fresh, 50-200ms)
- **Large pages:** May require pagination for pages >20KB Markdown

**Optimization tips:**
- Set `PRECONVERT_MD=true` to warm cache at startup
- Use `fragment` + `section_only` for faster, focused responses
- Increase `MD_CACHE_SIZE` for better hit rate

### `search_documentation`

- **Typical query:** 10-50ms (FTS5 index lookup + BM25 ranking)
- **Complex queries:** 50-200ms (multiple terms, Boolean operators)
- **Index size:** 20-50MB on disk
- **Index build time:** 2-5 minutes (depending on CPU)

**Optimization tips:**
- Keep `limit` reasonable (10-20 results)
- Use specific terms rather than broad queries
- Index is automatically optimized during build

---

## Related Documentation

- [Configuration Guide](CONFIGURATION.md) - Server configuration options
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- [Contributing Guide](CONTRIBUTING.md) - Development and testing
- [README](../README.md) - Quick start and overview
