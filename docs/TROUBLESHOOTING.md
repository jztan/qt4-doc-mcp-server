# Troubleshooting Guide

This guide covers common issues you might encounter when using the Qt 4.8.4 Documentation MCP Server and their solutions.

## 📋 Table of Contents
- [Search Index Issues](#search-index-issues)
- [Documentation Files Issues](#documentation-files-issues)
- [Markdown Conversion Issues](#markdown-conversion-issues)
- [Server Connection Issues](#server-connection-issues)
- [Cache and Index Corruption](#cache-and-index-corruption)
- [Performance Issues](#performance-issues)
- [Getting Help](#getting-help)

## 🔍 Search Index Issues

### Search index not found

**Problem:** `SearchUnavailable: Search index not found at .index/fts.sqlite`

**Cause:** The FTS5 search index hasn't been built yet.

**Solution:**
```bash
# Option 1: Build the index manually
qt4-doc-build-index

# Option 2: Enable automatic build at startup
echo "PREINDEX_DOCS=true" >> .env
# Then restart the server
```

**Verification:**
```bash
# Check if index file exists
ls -lh .index/fts.sqlite

# Expected output shows file size (typically 20-50MB)
# -rw-r--r--  1 user  staff   32M Oct 26 08:45 .index/fts.sqlite
```

### Search returns no results

**Problem:** Search queries return empty results even for common terms.

**Cause:** Index might be empty or corrupted.

**Solution:**
```bash
# Rebuild the search index
rm -f .index/fts.sqlite
qt4-doc-build-index --force

# Verify index has content
sqlite3 .index/fts.sqlite "SELECT COUNT(*) FROM docs;"
# Should return a number > 0 (typically around 2000-3000)
```

## 📁 Documentation Files Issues

### Documentation files missing

**Problem:** `QT_DOC_BASE not found` or `Invalid QT_DOC_BASE: directory does not exist`

**Cause:** Qt documentation hasn't been downloaded or path is incorrect.

**Solution:**
```bash
# Option 1: Run the automated setup script (recommended)
python scripts/prepare_qt48_docs.py --segments 4

# Option 2: Download manually
# 1. Download from https://download.qt.io/archive/qt/4.8/4.8.4/
# 2. Extract the archive
# 3. Update .env with the correct path:
echo "QT_DOC_BASE=/path/to/qt-everywhere-opensource-src-4.8.4/doc/html" >> .env
```

**Verification:**
```bash
# Check if Qt docs directory exists
ls -la $QT_DOC_BASE

# Should see HTML files like:
# qstring.html
# qobject.html
# index.html
# etc.
```

### Incomplete documentation

**Problem:** Some documentation pages fail to load or return errors.

**Cause:** Qt documentation download was interrupted or files are corrupted.

**Solution:**
```bash
# Re-download Qt documentation
rm -rf qt-everywhere-opensource-src-4.8.4/
python scripts/prepare_qt48_docs.py --segments 4

# Verify download integrity
cd qt-everywhere-opensource-src-4.8.4/doc/html
find . -name "*.html" | wc -l
# Should return around 2000-3000 files
```

## 📝 Markdown Conversion Issues

### Markdown conversion fails

**Problem:** HTML parsing errors or empty Markdown output

**Cause:** Missing dependencies or corrupted HTML files.

**Solution:**
```bash
# 1. Verify required packages are installed
pip list | grep -E "beautifulsoup4|lxml|markdownify"

# Expected output:
# beautifulsoup4    4.14.0
# lxml              6.0.0
# markdownify       1.2.0

# 2. Reinstall if missing
pip install beautifulsoup4 lxml markdownify

# 3. Clear Markdown cache and regenerate
rm -rf .cache/md
qt4-doc-warm-md
```

### Incorrect formatting in Markdown output

**Problem:** Markdown has broken links, missing formatting, or garbled text.

**Cause:** HTML structure issues or converter bugs.

**Solution:**
```bash
# 1. Check source HTML file
cat $QT_DOC_BASE/qstring.html | head -50

# 2. Clear cache for specific page
rm -rf .cache/md/$(echo -n "qstring.html" | md5)*/

# 3. Test conversion manually
uv run python -c "
from qt4_doc_mcp_server.doc_service import get_markdown_for_url
md = get_markdown_for_url('https://doc.qt.io/archives/qt-4.8/qstring.html')
print(md[:500])
"
```

## 🌐 Server Connection Issues

### Port already in use

**Problem:** `Address already in use: 127.0.0.1:8000`

**Cause:** Another process is using port 8000.

**Solution:**
```bash
# Option 1: Change server port in .env
echo "SERVER_PORT=8001" >> .env

# Option 2: Find and kill process using port 8000 (macOS/Linux)
lsof -ti:8000 | xargs kill -9

# Option 3: Find process on Windows
netstat -ano | findstr :8000
# Then kill it: taskkill /PID <PID> /F
```

### Server won't start

**Problem:** Server fails to start with configuration errors.

**Cause:** Invalid `.env` configuration or missing dependencies.

**Solution:**
```bash
# 1. Verify .env file exists and is valid
cat .env

# Required variables:
# QT_DOC_BASE=/path/to/qt/docs

# 2. Check Python version
python --version
# Should be 3.11 or higher

# 3. Verify all dependencies installed
pip check

# 4. Try running with verbose logging
MCP_LOG_LEVEL=DEBUG qt4-doc-mcp-server
```

### Health check fails

**Problem:** `curl http://127.0.0.1:8000/health` returns error or timeout.

**Cause:** Server not running or wrong port.

**Solution:**
```bash
# 1. Check if server is running
ps aux | grep qt4-doc-mcp-server

# 2. Check server logs
MCP_LOG_LEVEL=INFO qt4-doc-mcp-server

# 3. Verify port in .env matches your curl request
grep SERVER_PORT .env

# 4. Test with correct port
curl -s http://127.0.0.1:$(grep SERVER_PORT .env | cut -d= -f2)/health
```

## 🗂️ Cache and Index Corruption

### Cache or index corruption

**Problem:** Unexpected errors reading from cache or search index, random crashes, or inconsistent results.

**Cause:** Corrupted cache files or database.

**Solution:**
```bash
# Full reset (safest option)
rm -rf .cache/md .index/fts.sqlite

# Rebuild everything
qt4-doc-build-index
qt4-doc-warm-md

# Verify rebuild
ls -lh .cache/md/ | head
ls -lh .index/fts.sqlite
```

### Stale cache after docs update

**Problem:** Old content appears even after updating Qt documentation.

**Cause:** Markdown cache hasn't been invalidated.

**Solution:**
```bash
# Clear Markdown cache
rm -rf .cache/md

# Rebuild search index
rm -f .index/fts.sqlite
qt4-doc-build-index

# Warm cache with new content
qt4-doc-warm-md
```

## ⚡ Performance Issues

### Slow search queries

**Problem:** Search takes several seconds to return results.

**Cause:** Index not optimized or running on slow storage.

**Solution:**
```bash
# Rebuild and optimize index
rm -f .index/fts.sqlite
qt4-doc-build-index

# The build process automatically runs OPTIMIZE and VACUUM

# Verify index is optimized
sqlite3 .index/fts.sqlite "PRAGMA integrity_check;"
# Should return: ok
```

### High memory usage

**Problem:** Server uses excessive RAM (>1GB).

**Cause:** Cache size too large.

**Solution:**
```bash
# Reduce in-memory cache size in .env
echo "MD_CACHE_SIZE=128" >> .env
# Default is 512, reduce to 128 or 256

# Restart server
pkill -f qt4-doc-mcp-server
qt4-doc-mcp-server
```

### Slow first response

**Problem:** First documentation request takes a long time.

**Cause:** Cache is cold (not pre-warmed).

**Solution:**
```bash
# Enable automatic cache warming at startup
echo "PRECONVERT_MD=true" >> .env

# Or warm cache manually
qt4-doc-warm-md

# This converts all HTML to Markdown ahead of time
```

## 🆘 Getting Help

If you're still experiencing issues after trying these solutions:

### Before Opening an Issue

1. **Check existing issues:** Search [GitHub Issues](https://github.com/jztan/qt4-doc-mcp-server/issues)
2. **Enable debug logging:**
   ```bash
   MCP_LOG_LEVEL=DEBUG qt4-doc-mcp-server 2>&1 | tee server.log
   ```
3. **Gather information:**
   - Python version: `python --version`
   - Package version: `pip show qt4-doc-mcp-server`
   - OS and version: `uname -a` (Linux/Mac) or `ver` (Windows)
   - Error messages and stack traces

### Opening an Issue

Include the following in your issue report:

```markdown
## Environment
- OS: [e.g., macOS 14.0, Ubuntu 22.04, Windows 11]
- Python version: [e.g., 3.11.5]
- Package version: [e.g., 0.5.0]

## Problem Description
[Clear description of what's wrong]

## Steps to Reproduce
1. [First step]
2. [Second step]
3. [etc.]

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Logs
```
[Paste relevant log output]
```

## Additional Context
[Any other relevant information]
```

### Community Resources

- **GitHub Issues:** [Report bugs and request features](https://github.com/jztan/qt4-doc-mcp-server/issues)
- **Discussions:** [Ask questions and share ideas](https://github.com/jztan/qt4-doc-mcp-server/discussions)
- **Contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md) for development help


