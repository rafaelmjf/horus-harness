"""Tests for managed-block drift detection - especially the cross-reference fix."""

from horus import templates
from horus.instructions import check_drift, extract_block, normalize_block


def _file(other: str) -> str:
    return templates.instruction_file("Title", other, "Notes")


def test_extract_block_found():
    text = _file("CLAUDE.md")
    result = extract_block(text)
    assert result.found
    assert templates.BLOCK_BEGIN in result.raw
    assert templates.BLOCK_END in result.raw


def test_extract_block_missing():
    assert not extract_block("# just a heading\n").found


def test_crossreference_difference_is_not_drift():
    # The two real files differ only on the cross-reference line.
    agents = _file("CLAUDE.md")
    claude = _file("AGENTS.md")
    assert agents != claude  # genuinely different bytes
    report = check_drift(agents, "AGENTS.md", claude, "CLAUDE.md")
    assert report.status == "aligned", report.detail


def test_real_content_drift_is_detected():
    agents = _file("CLAUDE.md")
    claude = _file("AGENTS.md").replace("project continuity", "something else")
    report = check_drift(agents, "AGENTS.md", claude, "CLAUDE.md")
    assert report.status == "drift"
    assert "something else" in report.detail


def test_missing_block_reported():
    report = check_drift(_file("CLAUDE.md"), "AGENTS.md", "# no block", "CLAUDE.md")
    assert report.status == "missing"
    assert "CLAUDE.md" in report.detail


def test_shared_block_carries_version_floor_instruction():
    block = templates.shared_block("CLAUDE.md")
    assert "Version floor" in block
    assert "horus --version" in block
    assert "horus_min_version" in block
    assert "uv tool install --force" in block


def test_normalize_ignores_trailing_whitespace_and_crlf():
    a = templates.shared_block("CLAUDE.md")
    b = a.replace("\n", "\r\n") + "   "
    assert normalize_block(a) == normalize_block(b)
