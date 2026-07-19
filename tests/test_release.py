"""Tests for the pure helpers in scripts/release.py."""
import importlib.util
import json
from datetime import date
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "release", Path(__file__).parent.parent / "scripts" / "release.py"
)
release = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(release)


def test_calculate_new_version_patch():
    assert release.calculate_new_version("0.5.0", "patch") == "0.5.1"


def test_calculate_new_version_minor():
    assert release.calculate_new_version("0.5.2", "minor") == "0.6.0"


def test_calculate_new_version_major():
    assert release.calculate_new_version("0.5.0", "major") == "1.0.0"


def test_calculate_new_version_rejects_invalid():
    with pytest.raises(SystemExit):
        release.calculate_new_version("0.5", "patch")


def test_parse_title_with_contract():
    title, body = release._parse_title("TITLE: v1.0.0 - Big release\nBody here", "v1.0.0")
    assert title == "v1.0.0 - Big release"
    assert body == "Body here"


def test_parse_title_missing_falls_back_to_tag():
    title, body = release._parse_title("Just body text", "v1.0.0")
    assert title == "v1.0.0"
    assert body == "Just body text"


def test_notes_file_roundtrip(tmp_path):
    path = tmp_path / "notes.md"
    release.write_notes_file(path, "My Title", "Body line 1\nBody line 2")
    title, body = release.read_notes_file(path)
    assert title == "My Title"
    assert body == "Body line 1\nBody line 2"


def test_build_raw_release_body_has_install_line():
    body = release.build_raw_release_body("### Added\n- thing", "0.6.0")
    assert "pip install qt4-doc-mcp-server==0.6.0" in body
    assert "### Added" in body


CHANGELOG = """\
# Changelog

## [Unreleased]
### Added
- New search tool

## [0.5.0] - 2025-10-26
### Added
- FTS5 search
"""


def test_extract_unreleased_section(tmp_path):
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG)
    section = release.extract_unreleased_section(tmp_path)
    assert "New search tool" in section
    assert "FTS5" not in section


def test_extract_changelog_section(tmp_path):
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG)
    section = release.extract_changelog_section(tmp_path, "0.5.0")
    assert "FTS5 search" in section
    assert "New search tool" not in section


def test_update_changelog_stamps_version_and_date(tmp_path):
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG)
    release.update_changelog(tmp_path, "0.6.0", dry_run=False)
    content = (tmp_path / "CHANGELOG.md").read_text()
    today = date.today().strftime("%Y-%m-%d")
    assert f"## [0.6.0] - {today}" in content
    assert "## [Unreleased]" not in content


def test_update_changelog_rejects_empty_unreleased(tmp_path):
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\n## [0.5.0] - 2025-10-26\n### Added\n- x\n"
    )
    with pytest.raises(SystemExit):
        release.update_changelog(tmp_path, "0.6.0", dry_run=False)


def test_update_changelog_rejects_missing_unreleased(tmp_path):
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [0.5.0] - 2025-10-26\n### Added\n- x\n"
    )
    with pytest.raises(SystemExit):
        release.update_changelog(tmp_path, "0.6.0", dry_run=False)


def test_update_server_json_updates_both_versions(tmp_path):
    (tmp_path / "server.json").write_text(
        json.dumps(
            {
                "version": "0.5.0",
                "packages": [{"identifier": "qt4-doc-mcp-server", "version": "0.5.0"}],
            }
        )
    )
    release.update_server_json(tmp_path, "0.6.0", dry_run=False)
    content = json.loads((tmp_path / "server.json").read_text())
    assert content["version"] == "0.6.0"
    assert content["packages"][0]["version"] == "0.6.0"


def test_repo_server_json_matches_pyproject_version():
    root = Path(__file__).parent.parent
    server = json.loads((root / "server.json").read_text())
    pyproject_version = release.get_current_version(root)
    assert server["version"] == pyproject_version
    assert server["packages"][0]["version"] == pyproject_version
