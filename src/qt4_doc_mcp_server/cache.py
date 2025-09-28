"""Caching helpers: in-memory LRU and Markdown store (disk) primitives."""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
import hashlib
import os


class LRUCache:
    def __init__(self, capacity: int = 128):
        self.capacity = max(1, int(capacity))
        self._data: OrderedDict[str, str] = OrderedDict()

    def get(self, key: str) -> str | None:
        val = self._data.get(key)
        if val is not None:
            self._data.move_to_end(key)
        return val

    def put(self, key: str, value: str) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)


def md_store_path(base: Path, canonical_url: str) -> Path:
    h = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
    return base / h[:2] / f"{h}.md"


def md_store_read(base: Path, canonical_url: str) -> str | None:
    p = md_store_path(base, canonical_url)
    try:
        return p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def md_store_write(base: Path, canonical_url: str, markdown: str) -> None:
    p = md_store_path(base, canonical_url)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(markdown)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)

