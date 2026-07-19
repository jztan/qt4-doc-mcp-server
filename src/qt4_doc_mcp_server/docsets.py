"""Detection and URL rules for one active local Qt documentation set."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


CANONICAL_HOST = "doc.qt.io"
QT4_PREFIX = "/archives/qt-4.8/"


@dataclass(frozen=True)
class DocSet:
    """A locally installed Qt documentation release and its public URL space."""

    key: str
    display_name: str
    canonical_prefix: str

    @property
    def canonical_base_url(self) -> str:
        return f"https://{CANONICAL_HOST}{self.canonical_prefix}"


QT4_DOCSET = DocSet("qt4.8", "Qt 4.8", QT4_PREFIX)


def _docset_for_version(major: int, minor: int | None = None) -> DocSet:
    if major == 4:
        return QT4_DOCSET
    if major == 5:
        # Qt 5 online documentation is published under one stable URL series.
        return DocSet("qt5", "Qt 5", "/qt-5/")
    if major == 6 and minor is not None:
        return DocSet(f"qt6.{minor}", f"Qt 6.{minor}", f"/qt-6.{minor}/")
    if major == 6:
        return DocSet("qt6", "Qt 6", "/qt-6/")
    raise ValueError(f"Unsupported Qt major version: {major}")


def _version_from_text(text: str) -> tuple[int, int | None] | None:
    match = re.search(r"\bQt\s+([456])\.(\d+)(?:\.\d+)?\b", text)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def detect_docset(doc_base: Path | None) -> DocSet:
    """Infer the active docset from a local Qt documentation directory.

    Directory names used by Qt's offline documentation packages (for example
    ``Qt-6.8.2``) are preferred.  For copied or renamed directories, inspect a
    small set of QDoc-generated entry pages.  Unrecognised layouts retain the
    historical Qt 4.8 behaviour for backwards compatibility.
    """
    if doc_base is None:
        return QT4_DOCSET

    for candidate in (doc_base, *doc_base.parents):
        version = _version_from_text(candidate.name.replace("-", " "))
        if version:
            return _docset_for_version(*version)

    for relative in ("qtdoc/index.html", "qtcore/qobject.html", "qtdoc/qtdoc.qhp"):
        path = doc_base / relative
        try:
            version = _version_from_text(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if version:
            return _docset_for_version(*version)

    return QT4_DOCSET
