"""Human-readable FTS command-line search for the active local Qt docset."""
from __future__ import annotations

import argparse
import re
import sys

from .cache import md_store_path
from .config import (
    ensure_dirs,
    index_db_path,
    load_settings,
    markdown_cache_complete_path,
    markdown_cache_dir,
    validate_settings,
)
from .search import IndexError, SearchUnavailable, index_is_current, search


def _plain_snippet(snippet: str) -> str:
    """Render FTS highlight tags readably in a terminal."""
    return re.sub(r"</?b>", "", snippet).strip()


def search_cli_main(argv: list[str] | None = None) -> int:
    """Search the active docset and print materialized Markdown file paths."""
    parser = argparse.ArgumentParser(
        description="Search local Qt documentation and print Markdown cache paths"
    )
    parser.add_argument("query", nargs="+", help="FTS5 query (quote phrases as needed)")
    parser.add_argument("--limit", type=int, default=10, help="Maximum results (1-50; default: 10)")
    args = parser.parse_args(argv)

    settings = load_settings()
    ok, warnings = validate_settings(settings)
    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    if not ok:
        print("Invalid settings; check QT_DOC_BASE in .env", file=sys.stderr)
        return 2

    ensure_dirs(settings)
    db_path = index_db_path(settings)
    if not index_is_current(db_path):
        from .cli import build_index_main

        print("Search index is missing; building it now...", file=sys.stderr)
        if build_index_main([]) != 0:
            return 1

    if not markdown_cache_complete_path(settings).exists():
        from .cli import warm_md_main

        print("Markdown cache is incomplete; warming it now...", file=sys.stderr)
        if warm_md_main([]) != 0:
            return 1

    limit = min(50, max(1, args.limit))
    query = " ".join(args.query)
    try:
        results = search(db_path, query, limit=limit)
    except (SearchUnavailable, IndexError) as exc:
        print(f"Search failed: {exc}", file=sys.stderr)
        return 1

    cache_dir = markdown_cache_dir(settings)
    for number, result in enumerate(results, 1):
        markdown_path = md_store_path(cache_dir, result.path).resolve()
        if not markdown_path.exists():
            print(
                f"Markdown cache is incomplete: expected {markdown_path}",
                file=sys.stderr,
            )
            return 1
        print(f"{number}. {result.title}")
        print(f"   {markdown_path}")
        print(f"   {_plain_snippet(result.context)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(search_cli_main())
