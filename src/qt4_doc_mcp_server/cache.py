"""Caching helpers: in-memory LRU and Markdown store (disk) primitives."""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib
import json
import os


@dataclass
class CachedDoc:
    canonical_url: str
    title: str
    markdown: str
    links: list[dict[str, Any]]


class LRUCache:
    def __init__(self, capacity: int = 128):
        self.capacity = max(1, int(capacity))
        self._data: OrderedDict[str, CachedDoc] = OrderedDict()

    def get(self, key: str) -> CachedDoc | None:
        val = self._data.get(key)
        if val is not None:
            self._data.move_to_end(key)
        return val

    def put(self, key: str, value: CachedDoc) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)


def md_store_path(base: Path, canonical_url: str) -> Path:
    h = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
    return base / h[:2] / f"{h}.md"


def md_store_meta_path(base: Path, canonical_url: str) -> Path:
    h = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
    return base / h[:2] / f"{h}.meta.json"


def md_store_read(base: Path, canonical_url: str) -> CachedDoc | None:
    md_path = md_store_path(base, canonical_url)
    meta_path = md_store_meta_path(base, canonical_url)
    if not md_path.exists() or not meta_path.exists():
        return None
    try:
        markdown = md_path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    title = str(meta.get("title", ""))
    links = meta.get("links") or []
    if not isinstance(links, list):
        links = []
    return CachedDoc(canonical_url=canonical_url, title=title, markdown=markdown, links=links)


def md_store_write(base: Path, canonical_url: str, doc: CachedDoc) -> None:
    md_path = md_store_path(base, canonical_url)
    meta_path = md_store_meta_path(base, canonical_url)
    md_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_md = md_path.with_suffix(".md.tmp")
    tmp_meta = meta_path.with_suffix(".meta.json.tmp")

    with open(tmp_md, "w", encoding="utf-8") as f:
        f.write(doc.markdown)
        f.flush()
        os.fsync(f.fileno())

    with open(tmp_meta, "w", encoding="utf-8") as f:
        json.dump({"title": doc.title, "links": doc.links}, f)
        f.flush()
        os.fsync(f.fileno())

    os.replace(tmp_md, md_path)
    os.replace(tmp_meta, meta_path)
