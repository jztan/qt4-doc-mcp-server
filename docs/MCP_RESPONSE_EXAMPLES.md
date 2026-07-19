# MCP Server Response Examples

This document shows exactly what the Qt 4.8.4 Documentation MCP Server responds with when clients call the available MCP tools.

## Overview

The server provides two MCP tools:
1. **`read_documentation`** - Read and convert Qt documentation pages to Markdown
2. **`search_documentation`** - Full-text search across all Qt 4.8.4 documentation

---

## Tool 1: `read_documentation`

### Input Parameters

```typescript
{
  url: string;              // Required: Qt documentation URL
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
  url: string;             // Original URL passed in
  canonical_url: string;   // Normalized Qt docs URL
  markdown: string;        // Converted Markdown content
  attribution: string;     // GFDL 1.3 license attribution
  links: Array<{          // Extracted links from the page
    text: string;         // Link text
    url: string;          // Absolute canonical URL
  }>;
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
      "url": "https://doc.qt.io/archives/qt-4.8/qstring.html"
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
        "url": "https://doc.qt.io/archives/qt-4.8/qstring.html",
        "canonical_url": "https://doc.qt.io/archives/qt-4.8/qstring.html",
        "markdown": "# QString Class Reference\n\nThe QString class provides a Unicode character string.\n\n## Public Types\n\n- typedef `ConstIterator`\n- typedef `Iterator`\n...(truncated for brevity)...",
        "attribution": "Content © The Qt Company Ltd./Digia — GNU Free Documentation License 1.3",
        "links": [
          {
            "text": "QChar",
            "url": "https://doc.qt.io/archives/qt-4.8/qchar.html"
          },
          {
            "text": "QStringList",
            "url": "https://doc.qt.io/archives/qt-4.8/qstringlist.html"
          },
          {
            "text": "QByteArray",
            "url": "https://doc.qt.io/archives/qt-4.8/qbytearray.html"
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
- All internal links are normalized to canonical Qt URLs
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
      "url": "https://doc.qt.io/archives/qt-4.8/qstring.html",
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
        "url": "https://doc.qt.io/archives/qt-4.8/qstring.html",
        "canonical_url": "https://doc.qt.io/archives/qt-4.8/qstring.html",
        "markdown": "...continuation of content...\n\n## QString::toLatin1()\n\nReturns a Latin-1 representation...",
        "attribution": "Content © The Qt Company Ltd./Digia — GNU Free Documentation License 1.3",
        "links": [
          {
            "text": "toLatin1",
            "url": "https://doc.qt.io/archives/qt-4.8/qstring.html#toLatin1"
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
      "url": "https://doc.qt.io/archives/qt-4.8/qstring.html",
      "fragment": "public-functions",
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
        "url": "https://doc.qt.io/archives/qt-4.8/qstring.html",
        "canonical_url": "https://doc.qt.io/archives/qt-4.8/qstring.html#public-functions",
        "markdown": "## Public Functions\n\n- `QString()`\n- `QString(const QChar *unicode, int size = -1)`\n- `QString(QChar ch)`\n...(only public-functions section content)...",
        "attribution": "Content © The Qt Company Ltd./Digia — GNU Free Documentation License 1.3",
        "links": [
          {
            "text": "QChar",
            "url": "https://doc.qt.io/archives/qt-4.8/qchar.html"
          }
        ]
      }
    }
  ]
}
```

**Key Points:**
- `section_only: true` returns ONLY the specified section
- No `content_info` because it's not paginated (section fits in response)
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
      "url": "https://doc.qt.io/archives/qt-4.8/qwidget.html",
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
        "url": "https://doc.qt.io/archives/qt-4.8/qwidget.html",
        "canonical_url": "https://doc.qt.io/archives/qt-4.8/qwidget.html",
        "markdown": "# QWidget Class Reference\n\nThe QWidget class is the base class...(shortened)",
        "attribution": "Content © The Qt Company Ltd./Digia — GNU Free Documentation License 1.3",
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
    url: string;          // Canonical URL
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
            "url": "https://doc.qt.io/archives/qt-4.8/signalsandslots.html",
            "score": 15.234,
            "context": "…are used for communication between objects. <b>Signals</b> and <b>slots</b> are a central feature of Qt…"
          },
          {
            "title": "QObject Class Reference",
            "url": "https://doc.qt.io/archives/qt-4.8/qobject.html",
            "score": 12.891,
            "context": "…The QObject class is the base of all Qt objects. <b>Signals</b> and <b>slots</b> mechanism provides inter-object communication…"
          },
          {
            "title": "QMetaObject Class Reference",
            "url": "https://doc.qt.io/archives/qt-4.8/qmetaobject.html",
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
            "url": "https://doc.qt.io/archives/qt-4.8/qwidget.html",
            "score": 18.456,
            "context": "<b>QWidget</b> Class Reference. The <b>QWidget</b> class is the base class of all user interface objects…"
          },
          {
            "title": "QMainWindow Class Reference",
            "url": "https://doc.qt.io/archives/qt-4.8/qmainwindow.html",
            "score": 9.234,
            "context": "…QMainWindow inherits <b>QWidget</b> and provides a main application window. Central <b>QWidget</b> can be set…"
          },
          {
            "title": "Creating Custom Widgets",
            "url": "https://doc.qt.io/archives/qt-4.8/widgets-tutorial.html",
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

## Example 7: Multi-Term Search

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
            "url": "https://doc.qt.io/archives/qt-4.8/qwidget.html#paintEvent",
            "score": 16.789,
            "context": "…void <b>QWidget</b>::<b>paintEvent</b>(QPaintEvent *<b>event</b>). This <b>event</b> handler can be reimplemented to receive <b>paint</b> events…"
          },
          {
            "title": "The Paint System",
            "url": "https://doc.qt.io/archives/qt-4.8/paintsystem.html",
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

---

## Error Responses

### Invalid URL Error

**Request:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "read_documentation",
    "arguments": {
      "url": "https://example.com/invalid.html"
    }
  }
}
```

**Response:**
```json
{
  "error": {
    "code": "TOOL_ERROR",
    "message": "InvalidURL: URL must be from Qt 4.8 documentation (doc.qt.io/archives/qt-4.8/)"
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
      "url": "https://doc.qt.io/archives/qt-4.8/nonexistent.html"
    }
  }
}
```

**Response:**
```json
{
  "error": {
    "code": "TOOL_ERROR",
    "message": "NotFound: No local file found for URL"
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

**Response (if index not built):**
```json
{
  "error": {
    "code": "TOOL_ERROR",
    "message": "SearchUnavailable: Search index not found at .index/fts.sqlite. Run 'qt4-doc-build-index' to build the index."
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
[Fetch from Disk] → HTML Files
     ↓
[Convert to Markdown] → BeautifulSoup + Markdownify
     ↓
[Normalize Links] → Canonical URLs
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

---

## Implementation Details

### Response Assembly (Code Flow)

```python
# tools.py:48-81
def _format_result(doc: CachedDoc, url: str, *, start_index, max_length) -> dict:
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
        "url": url,                       # Original URL
        "canonical_url": doc.canonical_url,  # Normalized URL
        "markdown": markdown,             # Converted Markdown
        "attribution": "Content © ...",   # GFDL 1.3 notice
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

All links in the response are **absolute canonical URLs**:

```python
# Example link extraction from convert.py
Input HTML:  <a href="qstring.html">QString</a>
Output JSON: {"text": "QString", "url": "https://doc.qt.io/archives/qt-4.8/qstring.html"}

Input HTML:  <a href="#details">Details</a>
Output JSON: {"text": "Details", "url": "https://doc.qt.io/archives/qt-4.8/currentpage.html#details"}
```

This allows clients to:
1. Navigate between pages without URL parsing
2. Use URLs directly in new `read_documentation` calls
3. Track visited pages accurately

---

## Use Cases

### Use Case 1: AI Agent Exploring Qt Documentation

```
1. Agent searches: search_documentation("QListWidget")
2. Gets top 10 results with scores and snippets
3. Picks most relevant: "QListWidget Class Reference"
4. Reads page: read_documentation(url from search)
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
5. IDE calls: read_documentation(url, fragment="toLower", section_only=true)
6. Displays just that method documentation
```

### Use Case 3: Documentation Bot

```
1. User asks: "How do I create a custom widget?"
2. Bot searches: search_documentation("create custom widget")
3. Gets relevant pages with highlighted snippets
4. Bot reads top 3 results in full
5. Synthesizes answer with citations (URLs in response)
```

---

## Summary

The MCP server returns **rich, structured JSON responses** containing:
- ✅ Cleaned Markdown content
- ✅ Normalized absolute URLs for all links
- ✅ Pagination metadata for large documents
- ✅ Search results with BM25 scoring and highlighted snippets
- ✅ License attribution (GFDL 1.3)
- ✅ Error messages with actionable guidance

All responses are **designed for AI agents and programmatic clients** with:
- Consistent JSON structure
- Machine-readable metadata
- Easy navigation via normalized links
- Token-aware pagination
- Clear error taxonomy
