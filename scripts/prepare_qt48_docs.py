#!/usr/bin/env python3
"""Prepare Qt 4.8.4 docs locally (cross‑platform).

Steps:
  1) Download archive (or reuse a provided file)
  2) Extract to a work directory
  3) Stage HTML docs at a stable destination (symlink if possible, else copy)
  4) Copy LICENSE.FDL next to staged docs if present
  5) Write a .env with QT_DOC_BASE and sensible defaults

Usage:
  python scripts/prepare_qt48_docs.py [--copy] [--url URL] [--archive FILE]
                                      [--workdir DIR] [--dest DIR] [--env FILE]
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tarfile
import zipfile
from pathlib import Path
from urllib.request import urlretrieve
import time
import math


DEFAULT_URL = (
    "https://download.qt.io/archive/qt/4.8/4.8.4/"
    "qt-everywhere-opensource-src-4.8.4.tar.gz"
)


def _fmt_bytes(n: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024.0
        i += 1
    return f"{n:.1f} {units[i]}"


def _fmt_eta(seconds: float) -> str:
    if seconds is None or math.isinf(seconds) or math.isnan(seconds):
        return "--:--"
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _segmented_download(url: str, dest: Path, total_size: int, segments: int) -> None:
    """Download using HTTP Range requests split into segments and merge.

    Falls back to raising on errors so caller can use single-stream download.
    """
    import threading
    from urllib.request import Request, urlopen

    seg_size = total_size // segments
    ranges: list[tuple[int, int]] = []
    for i in range(segments):
        start = i * seg_size
        end = (start + seg_size - 1) if i < segments - 1 else total_size - 1
        ranges.append((start, end))

    tmp_parts: list[Path] = [dest.with_suffix(dest.suffix + f".part{i}") for i in range(segments)]

    downloaded = 0
    downloaded_lock = threading.Lock()
    start_time = time.monotonic()
    prev_len = 0
    ema_speed = 0.0

    def worker(idx: int, byte_range: tuple[int, int]) -> None:
        nonlocal downloaded, ema_speed
        req = Request(url, headers={"Range": f"bytes={byte_range[0]}-{byte_range[1]}"})
        with urlopen(req) as resp, open(tmp_parts[idx], "wb") as out:
            while True:
                chunk = resp.read(1024 * 64)
                if not chunk:
                    break
                out.write(chunk)
                with downloaded_lock:
                    downloaded += len(chunk)

    def printer() -> None:
        nonlocal prev_len, ema_speed
        while True:
            with downloaded_lock:
                done = downloaded
            pct = min(100.0, done * 100.0 / total_size)
            elapsed = max(time.monotonic() - start_time, 1e-6)
            inst_speed = done / elapsed
            if ema_speed <= 0:
                ema_speed = inst_speed
            else:
                alpha = 0.2
                ema_speed = alpha * inst_speed + (1 - alpha) * ema_speed
            remaining = max(total_size - done, 0)
            eta = remaining / max(ema_speed, 1e-6)
            bar_len = 30
            filled = int(bar_len * pct / 100)
            bar = "#" * filled + "-" * (bar_len - filled)
            core = (
                f"Downloading [{bar}] {pct:5.1f}%  "
                f"{_fmt_bytes(done)}/{_fmt_bytes(total_size)}  "
                f"{_fmt_bytes(ema_speed)}/s ETA {_fmt_eta(eta)}"
            )
            pad = max(prev_len - len(core), 0)
            sys.stderr.write("\r" + core + (" " * pad))
            sys.stderr.flush()
            prev_len = len(core)
            if done >= total_size:
                break
            time.sleep(0.1)

    # Launch workers
    import threading as th

    threads = [th.Thread(target=worker, args=(i, rng), daemon=True) for i, rng in enumerate(ranges)]
    for t in threads:
        t.start()
    printer()
    for t in threads:
        t.join()
    # Force final 100% line
    core = (
        f"Downloading [{'#'*30}] {100.0:5.1f}%  "
        f"{_fmt_bytes(total_size)}/{_fmt_bytes(total_size)}  "
        f"{_fmt_bytes(ema_speed)}/s ETA 00:00"
    )
    pad = max(prev_len - len(core), 0)
    sys.stderr.write("\r" + core + (" " * pad) + "\n")

    # Merge parts
    with open(dest, "wb") as out:
        for part in tmp_parts:
            with open(part, "rb") as f:
                shutil.copyfileobj(f, out)
            part.unlink(missing_ok=True)


def download(url: str, dest: Path, segments: int = 1) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"Using existing archive: {dest}")
        return dest

    start = time.monotonic()
    last_time = start
    last_count = 0
    prev_len = 0
    ema_speed = 0.0  # exponential moving average of speed (bytes/s)

    def reporthook(count: int, block_size: int, total_size: int):  # noqa: ANN001
        nonlocal last_time, last_count, prev_len, ema_speed
        now = time.monotonic()
        downloaded = count * block_size
        elapsed = now - start
        # instantaneous speed over last interval
        interval = max(now - last_time, 1e-6)
        inst_speed = (downloaded - last_count) / interval
        # smooth speed for display (EMA)
        if ema_speed <= 0:
            ema_speed = inst_speed
        else:
            alpha = 0.2  # smoothing factor
            ema_speed = alpha * inst_speed + (1 - alpha) * ema_speed
        last_time = now
        last_count = downloaded

        if total_size > 0:
            pct = min(100.0, downloaded * 100.0 / total_size)
            avg_speed = downloaded / max(elapsed, 1e-6)
            remaining = max(total_size - downloaded, 0)
            eta = remaining / max(avg_speed, 1e-6)
            bar_len = 30
            filled = int(bar_len * pct / 100)
            bar = "#" * filled + "-" * (bar_len - filled)
            msg_core = (
                f"Downloading [{bar}] {pct:5.1f}%  "
                f"{_fmt_bytes(downloaded)}/{_fmt_bytes(total_size)}  "
                f"{_fmt_bytes(ema_speed)}/s ETA {_fmt_eta(eta)}"
            )
        else:
            msg_core = f"Downloading {_fmt_bytes(downloaded)}  {_fmt_bytes(ema_speed or inst_speed)}/s"
        # Clear previous line tail if shorter than before
        msg = "\r" + msg_core
        pad = max(prev_len - len(msg_core), 0)
        sys.stderr.write(msg + (" " * pad))
        sys.stderr.flush()
        prev_len = len(msg_core)

    # If segments > 1, attempt Range-based segmented download first
    if segments > 1:
        from urllib.request import Request, urlopen

        try:
            # Probe total size via a range request
            req = Request(url, headers={"Range": "bytes=0-0"})
            with urlopen(req) as resp:
                cr = resp.headers.get("Content-Range", "")
                # Expect format: bytes 0-0/123456
                total = int(cr.split("/")[-1]) if "/" in cr else 0
            if total > 0:
                t0 = time.monotonic()
                _segmented_download(url, dest, total, segments)
                elapsed = time.monotonic() - t0
                sys.stderr.write(
                    f"Downloaded {_fmt_bytes(total)} in {_fmt_eta(elapsed)}\n"
                )
                return dest
        except Exception:
            # Fall back to single-stream
            pass

    try:
        urlretrieve(url, dest, reporthook=reporthook)  # nosec: B310 (trusted)
        # Print final summary
        size = dest.stat().st_size if dest.exists() else 0
        elapsed = time.monotonic() - start
        sys.stderr.write(
            f"Downloaded {_fmt_bytes(size)} in {_fmt_eta(elapsed)}\n"
        )
    except Exception:
        # ensure newline on failure
        sys.stderr.write("\n")
        raise
    return dest


def extract(archive: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Extracting {archive} ...")
    t0 = time.monotonic()
    if archive.suffixes[-2:] == [".tar", ".gz"] or archive.suffix == ".tgz":
        with tarfile.open(archive) as tf:
            members = tf.getmembers()
            total = sum(getattr(m, "size", 0) for m in members if m.isfile()) or 1
            done = 0
            last_update = time.monotonic()
            start = last_update
            prev_len = 0
            for m in members:
                tf.extract(m, out_dir)  # nosec: B202 (trusted)
                if m.isfile():
                    done += getattr(m, "size", 0)
                now = time.monotonic()
                if now - last_update > 0.1:
                    pct = min(100.0, done * 100.0 / total)
                    elapsed = now - start
                    avg_speed = done / max(elapsed, 1e-6)
                    eta = (total - done) / max(avg_speed, 1e-6)
                    bar_len = 30
                    filled = int(bar_len * pct / 100)
                    bar = "#" * filled + "-" * (bar_len - filled)
                    core = (
                        f"Extracting  [{bar}] {pct:5.1f}%  "
                        f"{_fmt_bytes(done)}/{_fmt_bytes(total)}  ETA {_fmt_eta(eta)}"
                    )
                    pad = max(prev_len - len(core), 0)
                    sys.stderr.write("\r" + core + (" " * pad))
                    sys.stderr.flush()
                    last_update = now
                    prev_len = len(core)
            # Force final 100% line
            core = (
                f"Extracting  [{'#'*30}] {100.0:5.1f}%  "
                f"{_fmt_bytes(total)}/{_fmt_bytes(total)}  ETA 00:00"
            )
            pad = max(prev_len - len(core), 0)
            sys.stderr.write("\r" + core + (" " * pad) + "\n")
            sys.stderr.flush()
            elapsed = time.monotonic() - t0
            sys.stderr.write(f"Extracted {_fmt_bytes(total)} in {_fmt_eta(elapsed)}\n")
    elif archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as zf:
            infos = zf.infolist()
            total = sum(getattr(i, "file_size", 0) for i in infos) or 1
            done = 0
            last_update = time.monotonic()
            start = last_update
            prev_len = 0
            for info in infos:
                zf.extract(info, out_dir)
                done += getattr(info, "file_size", 0)
                now = time.monotonic()
                if now - last_update > 0.1:
                    pct = min(100.0, done * 100.0 / total)
                    elapsed = now - start
                    avg_speed = done / max(elapsed, 1e-6)
                    eta = (total - done) / max(avg_speed, 1e-6)
                    bar_len = 30
                    filled = int(bar_len * pct / 100)
                    bar = "#" * filled + "-" * (bar_len - filled)
                    core = (
                        f"Extracting  [{bar}] {pct:5.1f}%  "
                        f"{_fmt_bytes(done)}/{_fmt_bytes(total)}  ETA {_fmt_eta(eta)}"
                    )
                    pad = max(prev_len - len(core), 0)
                    sys.stderr.write("\r" + core + (" " * pad))
                    sys.stderr.flush()
                    last_update = now
                    prev_len = len(core)
            core = (
                f"Extracting  [{'#'*30}] {100.0:5.1f}%  "
                f"{_fmt_bytes(total)}/{_fmt_bytes(total)}  ETA 00:00"
            )
            pad = max(prev_len - len(core), 0)
            sys.stderr.write("\r" + core + (" " * pad) + "\n")
            sys.stderr.flush()
            elapsed = time.monotonic() - t0
            sys.stderr.write(f"Extracted {_fmt_bytes(total)} in {_fmt_eta(elapsed)}\n")
    else:
        raise ValueError(f"Unsupported archive format: {archive}")

    # Prefer the known root folder name if present, else first directory
    known = out_dir / "qt-everywhere-opensource-src-4.8.4"
    if known.exists():
        return known
    for p in out_dir.iterdir():
        if p.is_dir():
            return p
    raise FileNotFoundError("Could not locate extracted root directory")


def stage_docs(doc_html: Path, dest: Path, copy: bool) -> Path:
    if dest.exists() or dest.is_symlink():
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        else:
            shutil.rmtree(dest)
    if copy or os.name == "nt":
        # On Windows, symlink needs privileges; default to copy
        shutil.copytree(doc_html, dest)
        return dest
    try:
        dest.symlink_to(doc_html, target_is_directory=True)
        return dest
    except OSError:
        # Fallback to copy if symlink fails
        shutil.copytree(doc_html, dest)
        return dest


def write_env(env_path: Path, qt_doc_base: Path) -> None:
    content = (
        f"QT_DOC_BASE={qt_doc_base}\n"
        "INDEX_DB_PATH=.index/fts.sqlite\n"
        "MD_CACHE_DIR=.cache/md\n"
        "PREINDEX_DOCS=true\n"
        "PRECONVERT_MD=true\n"
        "SERVER_HOST=127.0.0.1\n"
        "SERVER_PORT=8000\n"
        "MCP_LOG_LEVEL=WARNING\n"
        "MD_CACHE_SIZE=512\n"
    )
    env_path.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Prepare Qt 4.8.4 docs locally")
    ap.add_argument("--url", default=DEFAULT_URL, help="Archive URL")
    ap.add_argument("--archive", default="", help="Local archive to use")
    ap.add_argument("--workdir", default=".work/qt4", help="Work directory")
    ap.add_argument(
        "--dest", default="qt4-docs-html", help="Destination docs dir/symlink"
    )
    ap.add_argument(
        "--copy", action="store_true", help="Copy docs instead of creating a symlink"
    )
    ap.add_argument("--env", default=".env", help="Path to .env to write")
    ap.add_argument(
        "--segments",
        type=int,
        default=1,
        help="Parallel download segments (requires server Range support)",
    )
    args = ap.parse_args(argv)

    work = Path(args.workdir)
    downloads = work / "downloads"
    extracted = work / "extracted"
    downloads.mkdir(parents=True, exist_ok=True)
    extracted.mkdir(parents=True, exist_ok=True)

    if args.archive:
        archive_path = Path(args.archive)
        if not archive_path.exists():
            print(f"Archive not found: {archive_path}", file=sys.stderr)
            return 2
    else:
        archive_path = downloads / Path(args.url).name
        try:
            download(args.url, archive_path, segments=max(1, int(args.segments)))
        except Exception as e:
            print(f"Download failed: {e}", file=sys.stderr)
            return 2

    try:
        root = extract(archive_path, extracted)
    except Exception as e:
        print(f"Extract failed: {e}", file=sys.stderr)
        return 2

    doc_html = root / "doc" / "html"
    if not doc_html.exists():
        print(f"doc/html not found under {root}", file=sys.stderr)
        return 2

    dest = stage_docs(doc_html, Path(args.dest), copy=args.copy)

    # Copy LICENSE.FDL if present
    license_fdl = root / "LICENSE.FDL"
    try:
        if license_fdl.exists():
            shutil.copy2(license_fdl, dest / "LICENSE.FDL")
    except Exception:
        pass

    # Absolute QT_DOC_BASE path
    qt_doc_base = dest.resolve()
    write_env(Path(args.env), qt_doc_base)

    print(qt_doc_base)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
