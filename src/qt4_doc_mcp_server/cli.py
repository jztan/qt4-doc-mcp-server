from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .config import (
    clear_markdown_cache,
    ensure_dirs,
    index_db_path,
    load_settings,
    markdown_cache_complete_path,
    validate_settings,
)
from .doc_service import get_markdown_for_path
from .fetcher import html_to_markdown_path
from .search import build_index, index_is_current


def _iter_html_files(root: Path):
    for p in root.rglob("*.html"):
        if p.is_file():
            yield p


def warm_md_main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pre-convert the active Qt HTML documentation set to Markdown store")
    ap.add_argument("--limit", type=int, default=0, help="Limit number of files (for testing)")
    ap.add_argument("--force", action="store_true", help="Rebuild even when the cache is complete")
    args = ap.parse_args(argv)

    settings = load_settings()
    ok, warns = validate_settings(settings)
    for w in warns:
        print(f"Warning: {w}", file=sys.stderr)
    if not ok:
        print("Invalid settings; check QT_DOC_BASE in .env", file=sys.stderr)
        return 2

    ensure_dirs(settings)
    root = settings.qt_doc_base or Path('.')
    complete_marker = markdown_cache_complete_path(settings)
    if complete_marker.exists() and not args.force:
        print("Markdown cache is already complete; use --force to rebuild.", file=sys.stderr)
        return 0

    if args.force:
        # A partial forced warmup must never retain a stale completeness claim.
        complete_marker.unlink(missing_ok=True)

    files = list(_iter_html_files(root))
    limited = args.limit and args.limit > 0
    if limited:
        files = files[: args.limit]
    total = len(files)
    if total == 0:
        print("No HTML files found under QT_DOC_BASE", file=sys.stderr)
        return 1

    print(f"Warming Markdown store from {total} HTML files...", file=sys.stderr)
    t0 = time.monotonic()
    total_md = 0
    last_len = 0
    errors = 0
    show_progress = sys.stderr.isatty()
    for i, f in enumerate(files, 1):
        rel = f.relative_to(root).as_posix()
        try:
            doc = get_markdown_for_path(html_to_markdown_path(rel), settings, None)
            total_md += len(doc.markdown)
        except Exception as e:
            errors += 1
            print(f"\nError converting {rel}: {e}", file=sys.stderr)
        # Progress is intentionally interactive-only: stderr may be captured by
        # an MCP client and per-file updates are not useful in its logs.
        if not show_progress:
            continue
        pct = i * 100.0 / total
        elapsed = max(time.monotonic() - t0, 1e-6)
        eta = (total - i) * (elapsed / i)
        core = f"[{i:5d}/{total}] {pct:5.1f}%  ETA {int(eta)//60:02d}:{int(eta)%60:02d}"
        pad = max(last_len - len(core), 0)
        sys.stderr.write("\r" + core + (" " * pad))
        sys.stderr.flush()
        last_len = len(core)

    if show_progress:
        sys.stderr.write("\n")
    elapsed = time.monotonic() - t0
    print(
        f"Done. Processed ~{total_md} chars of Markdown in "
        f"{int(elapsed)//60:02d}:{int(elapsed)%60:02d}",
        file=sys.stderr,
    )
    if not limited and errors == 0:
        complete_marker.touch()
        return 0
    if errors:
        print(f"Markdown warmup failed for {errors} file(s).", file=sys.stderr)
        return 1
    return 0


def build_index_main(argv: list[str] | None = None) -> int:
    """CLI entry point for building the FTS5 search index."""
    ap = argparse.ArgumentParser(
        description="Build FTS5 search index from the active Qt HTML documentation set"
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild even if index already exists"
    )
    args = ap.parse_args(argv)

    settings = load_settings()
    ok, warns = validate_settings(settings)
    for w in warns:
        print(f"Warning: {w}", file=sys.stderr)
    if not ok:
        print("Invalid settings; check QT_DOC_BASE in .env", file=sys.stderr)
        return 2

    ensure_dirs(settings)
    docs_base = settings.qt_doc_base
    if not docs_base:
        print("QT_DOC_BASE not configured", file=sys.stderr)
        return 2

    index_path = index_db_path(settings)
    # Reuse the co-located index when its schema and path format are current.
    if index_path.exists() and not args.force and index_is_current(index_path):
        print(f"Index already exists at {index_path}", file=sys.stderr)
        print("Use --force to rebuild", file=sys.stderr)
        return 0
    if index_path.exists() and not args.force:
        print("Existing index has an outdated or incomplete format; rebuilding.", file=sys.stderr)

    print(f"Building search index from {docs_base}", file=sys.stderr)
    print(f"Index will be written to {index_path}", file=sys.stderr)

    t0 = time.monotonic()
    last_len = 0
    show_progress = sys.stderr.isatty()

    def progress(current, total, path):
        nonlocal last_len
        if not show_progress:
            return
        pct = current * 100.0 / total
        elapsed = max(time.monotonic() - t0, 1e-6)
        rate = current / elapsed
        eta = (total - current) / rate if rate > 0 else 0

        msg = f"[{current:5d}/{total}] {pct:5.1f}%  ETA {int(eta)//60:02d}:{int(eta)%60:02d}"
        pad = max(last_len - len(msg), 0)
        sys.stderr.write("\r" + msg + (" " * pad))
        sys.stderr.flush()
        last_len = len(msg)

    try:
        stats = build_index(index_path, docs_base, progress_callback=progress)
        clear_markdown_cache(settings)
        if show_progress:
            sys.stderr.write("\n")

        elapsed = time.monotonic() - t0
        print(
            f"\nIndex build complete in {int(elapsed)//60:02d}:{int(elapsed)%60:02d}",
            file=sys.stderr,
        )
        print(f"  Indexed: {stats['indexed']}", file=sys.stderr)
        print(f"  Skipped: {stats['skipped']}", file=sys.stderr)
        print(f"  Errors:  {stats['errors']}", file=sys.stderr)

        # Show index size
        if index_path.exists():
            size_mb = index_path.stat().st_size / (1024 * 1024)
            print(f"  Index size: {size_mb:.1f} MB", file=sys.stderr)

        return 0

    except Exception as e:
        sys.stderr.write("\n")
        print(f"Error building index: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(warm_md_main())
