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


def test_shared_block_requires_exact_dispatch_consent_without_cost_prediction():
    block = templates.shared_block("CLAUDE.md")
    compact = " ".join(block.split())
    assert "Authorize the exact worker envelope before spending" in block
    for field in ("exact agent", "concrete model", "effort", "account", "maximum attempts"):
        assert field in compact
    assert "owner may instead" in block and "expiring isolated-account capacity" in block
    assert "requires new approval" in block and "never silently fall back" in block
    assert "Never predict a" in block and "auto-route" in block
    assert "never in a new continuity artifact" in block


def test_normalize_ignores_trailing_whitespace_and_crlf():
    a = templates.shared_block("CLAUDE.md")
    b = a.replace("\n", "\r\n") + "   "
    assert normalize_block(a) == normalize_block(b)


def test_shared_block_carries_config_dir_isolation_rule():
    block = templates.shared_block("CLAUDE.md")
    assert "Accounts get isolated config dirs; same-dir concurrency is advised, not blocked" in block
    assert "CLAUDE_CONFIG_DIR" in block and "CODEX_HOME" in block
    assert "launch shares a config dir, then proceeds" in block
    assert "shared rate-limit budget" in block


def test_shared_block_carries_resume_confirmation_rule():
    block = templates.shared_block("CLAUDE.md")
    assert "orientation handoff, never authorization to execute" in block
    assert "asks permission before editing" in block
    assert "never ordered as a next step" in block
    assert "separate confirmation is required" in block
