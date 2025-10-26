# Contributing to Qt 4.8.4 Documentation MCP Server

Thank you for your interest in contributing to the Qt 4.8.4 Documentation MCP Server! This guide will help you get started.

## 📋 Table of Contents
- [Ways to Contribute](#ways-to-contribute)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Commit Message Convention](#commit-message-convention)
- [Pull Request Process](#pull-request-process)
- [Documentation Updates](#documentation-updates)
- [Release Process](#release-process)

## 🤝 Ways to Contribute

We welcome contributions in several forms:

- **Bug Reports** - Report issues via GitHub Issues
- **Feature Requests** - Suggest new functionality or improvements
- **Bug Fixes** - Submit fixes for known issues
- **New Features** - Implement requested features
- **Documentation** - Improve README, guides, and code comments
- **Tests** - Expand test coverage and add edge case tests
- **Code Quality** - Refactoring, type hints, performance improvements

## 🛠️ Development Setup

### Prerequisites
- **Python 3.11+** required
- **Git** for version control
- **Qt 4.8.4 HTML Documentation** for testing
- **SQLite with FTS5** (included in Python 3.11+)
- Familiarity with **MCP (Model Context Protocol)**

### Setup Steps

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/qt4-doc-mcp-server.git
   cd qt4-doc-mcp-server
   ```

2. **Create Virtual Environment**
   ```bash
   uv venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   uv pip install -e .[dev]
   ```

4. **Setup Qt Documentation**
   ```bash
   python scripts/prepare_qt48_docs.py --segments 4
   ```

5. **Configure Environment**
   ```bash
   # .env file is created by the setup script
   # Verify QT_DOC_BASE points to the correct location
   cat .env
   ```

6. **Build Search Index**
   ```bash
   qt4-doc-build-index
   ```

7. **Run Tests**
   ```bash
   uv run python -m pytest -v
   ```

## 🔄 Development Workflow

### Branch Naming
Use descriptive branch names with prefixes:
- `feature/` - New features (e.g., `feature/add-caching-metrics`)
- `fix/` - Bug fixes (e.g., `fix/search-encoding-issue`)
- `docs/` - Documentation updates (e.g., `docs/update-contributing-guide`)
- `test/` - Test additions (e.g., `test/add-converter-tests`)
- `refactor/` - Code refactoring (e.g., `refactor/simplify-cache-logic`)

### Development Cycle

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write code following our standards
   - Add/update tests
   - Update documentation

3. **Run Quality Checks**
   ```bash
   # Run tests
   uv run python -m pytest -v

   # Format code (if using ruff)
   ruff format src/ tests/

   # Lint code
   ruff check src/ tests/
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   # Then create a Pull Request on GitHub
   ```

## 📏 Code Standards

### Style Guidelines
- **Line Length:** Maximum 100 characters (flexible for long URLs or strings)
- **Formatting:** Use `ruff format` or follow PEP 8
- **Type Hints:** Required for all function signatures
- **Docstrings:** Required for all public functions, classes, and modules
- **Naming Conventions:** Follow PEP 8 (snake_case for functions/variables, PascalCase for classes)

### Code Quality Requirements
```python
# Good example
def extract_text_content(html: str) -> tuple[str, str, str]:
    """Extract title, headings, and body text from HTML.

    Args:
        html: Raw HTML content to parse

    Returns:
        Tuple of (title, headings_text, body_text)
    """
    # Implementation
    pass

# Bad example - missing type hints and docstring
def extract_text_content(html):
    pass
```

### Error Handling
- Use custom exceptions from `errors.py`
- Provide clear, user-friendly error messages
- Include context in error messages

```python
# Good
if not db_path.exists():
    raise SearchUnavailable(f"Search index not found at {db_path}")

# Bad
if not db_path.exists():
    raise Exception("not found")
```

### Async/Await Patterns
- MCP tools should be `async def`
- Use `await` for I/O operations when beneficial
- Maintain consistency with existing async patterns

## 🧪 Testing Requirements

### Test Coverage
- **Target:** >80% code coverage
- **Required:** All new features must include tests
- **Required:** Bug fixes must include regression tests

### Test Types

1. **Unit Tests** - Test individual functions in isolation
   ```python
   def test_canonical_url_normalization():
       """Test URL normalization to canonical form."""
       assert _to_canonical("qstring.html") == "https://doc.qt.io/archives/qt-4.8/qstring.html"
   ```

2. **Integration Tests** - Test component interactions
   ```python
   async def test_search_documentation_tool():
       """Test search_documentation MCP tool end-to-end."""
       result = await search_documentation(query="QString", limit=5)
       assert result["count"] > 0
   ```

3. **Edge Cases** - Test boundary conditions and error paths
   ```python
   def test_search_empty_query_returns_empty():
       """Test that empty search query returns empty results."""
       results = search(db_path, query="", limit=10)
       assert len(results) == 0
   ```

### Running Tests

```bash
# All tests
uv run python -m pytest -v

# Specific test file
uv run python -m pytest tests/test_search.py -v

# Specific test
uv run python -m pytest tests/test_search.py::test_search_returns_relevant_results -v

# With coverage
uv run python -m pytest --cov=qt4_doc_mcp_server --cov-report=html

# Quick run
uv run python -m pytest -q
```

### Test Requirements Checklist
- [ ] All tests pass
- [ ] New features have tests
- [ ] Bug fixes include regression tests
- [ ] Edge cases are tested
- [ ] Error handling is tested
- [ ] Coverage doesn't decrease

## 💬 Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/) format:

```
type: brief description

Optional detailed explanation of changes.

Optional footer with issue references.
```

### Commit Types
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions or modifications
- `refactor:` - Code refactoring without behavior changes
- `chore:` - Maintenance tasks, dependency updates
- `perf:` - Performance improvements
- `style:` - Code style/formatting changes

### Examples

```bash
# Good commit messages
feat: add pagination support to search_documentation tool
fix: correct URL encoding in fragment requests
docs: update README with troubleshooting section
test: add tests for cache corruption scenarios
chore: update dependencies to latest stable versions

# Bad commit messages
update code
fix bug
changes
WIP
```

### Important Rules
- ❌ **Never include Claude Code attribution** in commit messages
- ❌ **Do not add** "🤖 Generated with Claude Code" footers
- ❌ **Do not add** "Co-Authored-By: Claude" tags
- ✅ Keep messages professional and focused on technical changes

## 🔀 Pull Request Process

### Before Submitting

**Pre-submission Checklist:**
- [ ] All tests pass (`uv run python -m pytest -v`)
- [ ] Code is formatted (if using `ruff format`)
- [ ] Lint checks pass (if using `ruff check`)
- [ ] Type hints are included
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated (for features/fixes)
- [ ] Commit messages follow convention
- [ ] No merge conflicts with develop branch

### PR Template

When creating a pull request, include:

```markdown
## Description
Brief description of changes and motivation.

## Related Issues
Fixes #123
Related to #456

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Other (describe)

## Testing
Describe how you tested these changes:
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests pass locally
- [ ] CHANGELOG.md updated
```

### Review Process

1. **Automated Checks** - CI runs tests and linting
2. **Code Review** - Maintainer reviews code quality and design
3. **Testing** - Reviewer verifies functionality
4. **Approval** - Maintainer approves and merges

### After Merge

- Your changes will be included in the next release
- CHANGELOG.md tracks all changes
- Delete your feature branch after merge

## 📚 Documentation Updates

Update documentation when:
- Adding new features or MCP tools
- Modifying existing functionality
- Fixing user-impacting bugs
- Adding configuration options
- Changing behavior or APIs

### Files to Update

- **README.md** - User-facing documentation, quick start, features
- **CHANGELOG.md** - Keep a Changelog format, track all changes
- **CLAUDE.md** - Development guidelines for Claude Code (not committed)
- **Code docstrings** - Function/class documentation
- **Type hints** - Function signatures

### Documentation Standards

- Use clear, concise language
- Include code examples where helpful
- Keep examples up-to-date with code
- Use proper markdown formatting
- Link to related sections

## 🚀 Release Process

Releases are managed by project maintainers following this process:

1. **Version Bump**
   - Update version in `pyproject.toml`
   - Update version in `src/qt4_doc_mcp_server/__init__.py`

2. **CHANGELOG Update**
   - Move changes from `[Unreleased]` to new version section
   - Add release date
   - Follow Keep a Changelog format

3. **Create Release Branch**
   ```bash
   git checkout -b release/v0.X.0
   git commit -m "Bump version to 0.X.0"
   ```

4. **Merge and Tag**
   - Merge to `master`
   - Tag with version: `git tag -a v0.X.0 -m "Release version 0.X.0"`
   - Merge back to `develop`

5. **Publish**
   - GitHub Actions automatically publishes to PyPI
   - Create GitHub Release with changelog

### Semantic Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0) - Incompatible API changes
- **MINOR** (0.1.0) - New features, backward-compatible
- **PATCH** (0.0.1) - Bug fixes, backward-compatible

## 🙏 Thank You!

Your contributions make this project better for everyone. Thank you for taking the time to contribute!

If you have questions, feel free to:
- Open a GitHub Issue
- Start a Discussion
- Contact the maintainers


