# MCP Server Response Examples

This document shows exactly what the Qt Documentation MCP Server responds with when clients call the available MCP tools. The server serves one active local Qt 4.8, Qt 5, or Qt 6 documentation set at a time.

## Overview

The server provides two MCP tools:
1. **`read_documentation`** - Read and convert pages from the active Qt documentation set to Markdown
2. **`search_documentation`** - Full-text search across the active Qt documentation set

Documents are identified by root-relative Markdown paths under `QT_DOC_BASE`, not online URLs. Examples: `qstring.md` (Qt 4), `qtcore/qstring.md` (Qt 5/6 Core), `qtdoc/accessible.md` (Qt 5/6 global page).

---

## Tool 1: `read_documentation`

### Input Parameters

```typescript
{
  path: string;             // Required: Root-relative Markdown path (e.g., "qtcore/qobject.md")
  fragment?: string;        // Optional: HTML fragment/anchor (e.g., "#details")
  section_only?: boolean;   // Optional: If true, return only the fragment section
  start_index?: number;     // Optional: Character offset for pagination
  max_length?: number;      // Optional: Max characters (default: 20000)
}
```

### Response Structure

The tool returns a **dictionary** with the following fields:

```typescript
{
  title: string;           // Page title from <h1> or <title>
  path: string;            // Normalized root-relative document path
  markdown: string;        // Converted Markdown content
  attribution: string;     // GFDL 1.3 license attribution
  links: Array<
    | { text: string; path: string }  // Local doc link (may carry "#fragment")
    | { text: string; url: string }   // External link
  >;
  content_info?: {        // Present when pagination is used
    total_length: number; // Total Markdown length before truncation
    returned_length: number; // Length of markdown returned
    start_index: number;  // Starting position
    truncated: boolean;   // Whether content was cut off
  }
}
```

---

## Example 1: Full Page Request

### Request
```json
{
  "method": "tools/call",
  "params": {
    "name": "read_documentation",
    "arguments": {
      "path": "qstring.md"
    }
  }
}
```

### Response
```json
{
  "content": [
    {
      "type": "text",
      "text": {
        "title": "QString Class Reference",
        "path": "qstring.md",
        "markdown": "# QString Class Reference\n\nThe QString class provides a Unicode character string.\n\n## Public Types\n\n- typedef `ConstIterator`\n- typedef `Iterator`\n...(truncated for brevity)...",
        "attribution": "Content © The Qt Company Ltd. and contributors — GNU Free Documentation License 1.3",
        "links": [
          {
            "text": "QChar",
            "path": "qchar.md"
          },
          {
            "text": "QStringList",
            "path": "qstringlist.md"
          },
          {
            "text": "QByteArray",
            "path": "qbytearray.md"
          }
        ],
        "content_info": {
          "total_length": 45823,
          "returned_length": 20000,
          "start_index": 0,
          "truncated": true
        }
      }
    }
  ]
}
```

**Key Points:**
- Default `max_length` is 20,000 characters to prevent token limit issues
- `content_info` is included because content was truncated
- Internal links carry a root-relative `path` usable directly in the next `read_documentation` call; external links keep a `url` field instead
- Links array allows easy navigation without parsing Markdown

---

## Example 2: Paginated Request (Continuation)

### Request
```json
{
  "method": "tools/call",
  "params": {
    "name": "read_documentation",
    "arguments": {
      "path": "qstring.md",
      "start_index": 20000,
      "max_length": 20000
    }
  }
}
```

### Response
```json
{
  "content": [
    {
      "type": "text",
      "text": {
        "title": "QString Class Reference",
        "path": "qstring.md",
        "markdown": "...continuation of content...\n\n## QString::toLatin1()\n\nReturns a Latin-1 representation...",
        "attribution": "Content © The Qt Company Ltd. and contributors — GNU Free Documentation License 1.3",
        "links": [
          {
            "text": "toLatin1",
            "path": "qstring.md#toLatin1"
          }
        ],
        "content_info": {
          "total_length": 45823,
          "returned_length": 20000,
          "start_index": 20000,
          "truncated": true
        }
      }
    }
  ]
}
```

**Key Points:**
- `start_index: 20000` continues from where previous response ended
- Same `total_length` (45823) confirms it's the same document
- Client can continue with `start_index: 40000` for next page

---

## Example 3: Fragment/Section Request

### Request
```json
{
  "method": "tools/call",
  "params": {
    "name": "read_documentation",
    "arguments": {
      "path": "qstring.md",
      "fragment": "#public-functions",
      "section_only": true
    }
  }
}
```

### Response
```json
{
  "content": [
    {
      "type": "text",
      "text": {
        "title": "QString Class Reference",
        "path": "qstring.md",
        "markdown": "## Public Functions\n\n- `QString()`\n- `QString(const QChar *unicode, int size = -1)`\n- `QString(QChar ch)`\n...(only public-functions section content)...",
        "attribution": "Content © The Qt Company Ltd. and contributors — GNU Free Documentation License 1.3",
        "links": [
          {
            "text": "QChar",
            "path": "qchar.md"
          }
        ]
      }
    }
  ]
}
```

**Key Points:**
- `section_only: true` returns ONLY the specified section
- Fragments are passed separately; the `path` itself must not contain `#`
- Fragment requests **bypass cache** (intentional design)
- Links are still extracted from the section

---

## Example 4: Custom Max Length

### Request
```json
{
  "method": "tools/call",
  "params": {
    "name": "read_documentation",
    "arguments": {
      "path": "qwidget.md",
      "max_length": 5000
    }
  }
}
```

### Response
```json
{
  "content": [
    {
      "type": "text",
      "text": {
        "title": "QWidget Class Reference",
        "path": "qwidget.md",
        "markdown": "# QWidget Class Reference\n\nThe QWidget class is the base class...(shortened)",
        "attribution": "Content © The Qt Company Ltd. and contributors — GNU Free Documentation License 1.3",
        "links": [...],
        "content_info": {
          "total_length": 38492,
          "returned_length": 5000,
          "start_index": 0,
          "truncated": true
        }
      }
    }
  ]
}
```

**Key Points:**
- Custom `max_length` overrides default 20,000
- Useful for getting quick previews or working with smaller context windows

---

## Tool 2: `search_documentation`

### Input Parameters

```typescript
{
  query: string;     // Required: Search terms (supports FTS5 query syntax)
  limit?: number;    // Optional: Max results (default: 10, max: 50)
  scope?: string;    // Optional: 'all', 'api', or 'guides' (currently 'all' only)
}
```

### Response Structure

```typescript
{
  query: string;          // Echo of search query
  count: number;          // Number of results returned
  results: Array<{
    title: string;        // Page title
    path: string;         // Root-relative document path
    score: number;        // BM25 relevance score (higher = more relevant)
    context: string;      // Snippet with <b> tag highlighting
  }>
}
```

---

## Example 5: Simple Search

### Request
```json
{
  "method": "tools/call",
  "params": {
    "name": "search_documentation",
    "arguments": {
      "query": "signals slots"
    }
  }
}
```

### Response
```json
{
  "content": [
    {
      "type": "text",
      "text": {
        "query": "signals slots",
        "count": 10,
        "results": [
          {
            "title": "Signals and Slots",
            "path": "signalsandslots.md",
            "score": 15.234,
            "context": "…are used for communication between objects. <b>Signals</b> and <b>slots</b> are a central feature of Qt…"
          },
          {
            "title": "QObject Class Reference",
            "path": "qobject.md",
            "score": 12.891,
            "context": "…The QObject class is the base of all Qt objects. <b>Signals</b> and <b>slots</b> mechanism provides inter-object communication…"
          },
          {
            "title": "QMetaObject Class Reference",
            "path": "qmetaobject.md",
            "score": 10.567,
            "context": "…Runtime introspection for <b>signals</b> and <b>slots</b>. The meta-object system allows…"
          }
        ]
      }
    }
  ]
}
```

**Key Points:**
- Results ranked by BM25 score (most relevant first)
- Context snippets show matches with `<b>` tags for highlighting
- Default limit is 10 results
- Ellipsis (…) indicates truncated context
- Result `path` values feed directly into `read_documentation`

---

## Example 6: Search with Custom Limit

### Request
```json
{
  "method": "tools/call",
  "params": {
    "name": "search_documentation",
    "arguments": {
      "query": "QWidget",
      "limit": 3
    }
  }
}
```

### Response
```json
{
  "content": [
    {
      "type": "text",
      "text": {
        "query": "QWidget",
        "count": 3,
        "results": [
          {
            "title": "QWidget Class Reference",
            "path": "qwidget.md",
            "score": 18.456,
            "context": "<b>QWidget</b> Class Reference. The <b>QWidget</b> class is the base class of all user interface objects…"
          },
          {
            "title": "QMainWindow Class Reference",
            "path": "qmainwindow.md",
            "score": 9.234,
            "context": "…QMainWindow inherits <b>QWidget</b> and provides a main application window. Central <b>QWidget</b> can be set…"
          },
          {
            "title": "Creating Custom Widgets",
            "path": "widgets-tutorial.md",
            "score": 7.891,
            "context": "…To create a custom widget, subclass <b>QWidget</b> and reimplement paintEvent()…"
          }
        ]
      }
    }
  ]
}
```

**Key Points:**
- Limit clamped to range [1, 50]
- If `limit: 100` is passed, it's automatically reduced to 50
- If `limit: 0` is passed, it's automatically increased to 10

---

## Example 7: Multi-Term Search (Qt 6 docset)

### Request
```json
{
  "method": "tools/call",
  "params": {
    "name": "search_documentation",
    "arguments": {
      "query": "paint event widget"
    }
  }
}
```

### Response
```json
{
  "content": [
    {
      "type": "text",
      "text": {
        "query": "paint event widget",
        "count": 10,
        "results": [
          {
            "title": "QWidget Class Reference",
            "path": "qtwidgets/qwidget.md",
            "score": 16.789,
            "context": "…void <b>QWidget</b>::<b>paintEvent</b>(QPaintEvent *<b>event</b>). This <b>event</b> handler can be reimplemented to receive <b>paint</b> events…"
          },
          {
            "title": "The Paint System",
            "path": "qtgui/paintsystem.md",
            "score": 14.234,
            "context": "…Qt's <b>paint</b> system provides classes for <b>painting</b> on <b>widgets</b> and other devices. When a <b>paint</b> <b>event</b> occurs…"
          }
        ]
      }
    }
  ]
}
```

**Key Points:**
- Multiple terms are ANDed together by FTS5
- BM25 scoring considers term frequency and document length
- All matching terms get highlighted in context
- Qt 5/6 docsets prefix paths with the module directory (`qtwidgets/`, `qtgui/`, ...)

---

## Error Responses

### Invalid Path Error

**Request:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "read_documentation",
    "arguments": {
      "path": "https://doc.qt.io/qt-6/qobject.html"
    }
  }
}
```

**Response:**
```json
{
  "error": {
    "code": "TOOL_ERROR",
    "message": "InvalidPath: Expected a local documentation path, not a URL"
  }
}
```

### Path Escapes Documentation Root

**Request:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "read_documentation",
    "arguments": {
      "path": "../secrets.md"
    }
  }
}
```

**Response:**
```json
{
  "error": {
    "code": "TOOL_ERROR",
    "message": "NotAllowed: Documentation path must stay under QT_DOC_BASE"
  }
}
```

### File Not Found Error

**Request:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "read_documentation",
    "arguments": {
      "path": "nonexistent.md"
    }
  }
}
```

**Response:**
```json
{
  "error": {
    "code": "TOOL_ERROR",
    "message": "NotFound: Documentation file not found: /path/to/docs/nonexistent.html"
  }
}
```

### Search Index Not Available

**Request:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "search_documentation",
    "arguments": {
      "query": "test"
    }
  }
}
```

**Response (if index not built or built for a different docset/format):**
```json
{
  "error": {
    "code": "TOOL_ERROR",
    "message": "Search index not available: Search index is missing or belongs to a different documentation set. Run 'qt-doc-build-index' to build the index for the active docset."
  }
}
```

---

## Data Flow Summary

```
Client Request
     ↓
MCP Tool (read_documentation or search_documentation)
     ↓
[Cache Check] → Cache Hit → Return Cached Data
     ↓ (miss)
[Fetch from Disk] → HTML Files under QT_DOC_BASE
     ↓
[Convert to Markdown] → BeautifulSoup + Markdownify
     ↓
[Normalize Links] → Relative Markdown links + root-relative paths
     ↓
[Apply Pagination] → Truncate if needed
     ↓
[Format Response] → Add attribution, links, content_info
     ↓
Client Response (JSON)
```

## Performance Characteristics

| Operation | Cold (No Cache) | Warm (Cached) |
|-----------|----------------|---------------|
| `read_documentation` (full page) | ~500ms - 2s | ~10ms - 50ms |
| `read_documentation` (section) | ~300ms - 1s | N/A (bypasses cache) |
| `search_documentation` | ~20ms - 100ms | Same (no cache) |

**Notes:**
- Cold reads depend on HTML size and conversion time
- Search performance depends on query complexity and index size
- Fragment/section requests always parse HTML (no cache)
- Default pagination (20K chars) prevents token overflow
- The Markdown cache lives under `$QT_DOC_BASE/.index/md/` (or `QT_DOC_STATE_DIR`) and mirrors the documentation tree, so it is directly browsable on disk

---

## Implementation Details

### Response Assembly (Code Flow)

```python
# tools.py: _format_result
def _format_result(doc: CachedDoc, *, start_index, max_length) -> dict:
    # 1. Get markdown from CachedDoc
    markdown = doc.markdown
    total_length = len(markdown)

    # 2. Apply pagination
    if start_index or max_length:
        start = max(0, start_index or 0)
        markdown = markdown[start : start + max_length]
        truncated = (start + max_length) < total_length

    # 3. Build response dictionary
    result = {
        "title": doc.title,              # From HTML <h1> or <title>
        "path": doc.path,                # Normalized root-relative path
        "markdown": markdown,            # Converted Markdown
        "attribution": "Content © ...",  # GFDL 1.3 notice
        "links": [dict(link) for link in doc.links],  # Extracted links
    }

    # 4. Add pagination metadata if truncated
    if truncated or start_index or max_length:
        result["content_info"] = {
            "total_length": total_length,
            "returned_length": len(markdown),
            "start_index": start_index or 0,
            "truncated": truncated,
        }

    return result
```

### Link Normalization

Links inside the Markdown keep their relative structure (so the cached `.md` tree is browsable on disk), while link metadata carries root-relative paths:

```python
# Example link extraction from convert.py
Input HTML:  <a href="qstring.html">QString</a>
Output JSON: {"text": "QString", "path": "qstring.md"}

Input HTML:  <a href="#details">Details</a>
Output JSON: {"text": "Details", "path": "currentpage.md#details"}

Input HTML:  <a href="https://www.example.com/">Example</a>
Output JSON: {"text": "Example", "url": "https://www.example.com/"}
```

This allows clients to:
1. Navigate between pages without URL parsing
2. Use `path` values directly in new `read_documentation` calls
3. Track visited pages accurately

---

## Use Cases

### Use Case 1: AI Agent Exploring Qt Documentation

```
1. Agent searches: search_documentation("QListWidget")
2. Gets top 10 results with scores and snippets
3. Picks most relevant: "QListWidget Class Reference"
4. Reads page: read_documentation(path from search)
5. Gets paginated content (20K chars)
6. Follows link to QListWidgetItem
7. Continues exploration...
```

### Use Case 2: IDE Integration

```
1. User types "QString::" in IDE
2. IDE calls: search_documentation("QString methods")
3. Shows quick preview from context snippets
4. User selects "QString::toLower"
5. IDE calls: read_documentation(path, fragment="#toLower", section_only=true)
6. Displays just that method documentation
```

### Use Case 3: Documentation Bot

```
1. User asks: "How do I create a custom widget?"
2. Bot searches: search_documentation("create custom widget")
3. Gets relevant pages with highlighted snippets
4. Bot reads top 3 results in full
5. Synthesizes answer with citations (paths in response)
```

---

## Summary

The MCP server returns **rich, structured JSON responses** containing:
- ✅ Cleaned Markdown content
- ✅ Root-relative document paths for all internal links
- ✅ Pagination metadata for large documents
- ✅ Search results with BM25 scoring and highlighted snippets
- ✅ License attribution (GFDL 1.3)
- ✅ Error messages with actionable guidance

All responses are **designed for AI agents and programmatic clients** with:
- Consistent JSON structure
- Machine-readable metadata
- Easy navigation via document paths
- Token-aware pagination
- Clear error taxonomy
