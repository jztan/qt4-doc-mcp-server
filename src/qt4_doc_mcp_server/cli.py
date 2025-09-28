from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .config import load_settings, ensure_dirs, validate_settings
from .doc_service import get_markdown_for_url


BASE_CANONICAL = "https://doc.qt.io/archives/qt-4.8/"


def _iter_html_files(root: Path):
    for p in root.rglob("*.html"):
        if p.is_file():
            yield p


def warm_md_main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pre-convert all Qt 4.8.4 HTML docs to Markdown store")
    ap.add_argument("--limit", type=int, default=0, help="Limit number of files (for testing)")
    args = ap.parse_args(argv)

    settings = load_settings()
    ensure_dirs(settings)
    ok, warns = validate_settings(settings)
    for w in warns:
        print(f"Warning: {w}", file=sys.stderr)
    if not ok:
        print("Invalid settings; check QT_DOC_BASE in .env", file=sys.stderr)
        return 2

    root = settings.qt_doc_base or Path('.')
    files = list(_iter_html_files(root))
    if args.limit and args.limit > 0:
        files = files[: args.limit]
    total = len(files)
    if total == 0:
        print("No HTML files found under QT_DOC_BASE", file=sys.stderr)
        return 1

    print(f"Warming Markdown store from {total} HTML files...")
    t0 = time.monotonic()
    total_md = 0
    last_len = 0
    for i, f in enumerate(files, 1):
        rel = f.relative_to(root).as_posix()
        url = BASE_CANONICAL + rel
        try:
            doc = get_markdown_for_url(url, settings, None)
            total_md += len(doc.markdown)
        except Exception as e:
            print(f"\nError converting {rel}: {e}", file=sys.stderr)
        # progress
        pct = i * 100.0 / total
        elapsed = max(time.monotonic() - t0, 1e-6)
        eta = (total - i) * (elapsed / i)
        core = f"[{i:5d}/{total}] {pct:5.1f}%  ETA {int(eta)//60:02d}:{int(eta)%60:02d}"
        pad = max(last_len - len(core), 0)
        sys.stderr.write("\r" + core + (" " * pad))
        sys.stderr.flush()
        last_len = len(core)

    sys.stderr.write("\n")
    elapsed = time.monotonic() - t0
    print(f"Done. Wrote ~{total_md} chars of Markdown in {int(elapsed)//60:02d}:{int(elapsed)%60:02d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(warm_md_main())
