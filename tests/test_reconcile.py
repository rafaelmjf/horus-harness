"""Tests for `horus reconcile instructions` block projection."""

from horus import templates
from horus.instructions import check_drift, extract_block, reconcile, set_crossref


def _file(other: str) -> str:
    return templates.instruction_file("Title", other, "Notes")


def test_set_crossref_points_at_other():
    block = templates.shared_block("CLAUDE.md")
    switched = set_crossref(block, "AGENTS.md")
    assert "matching block in `AGENTS.md`" in switched
    assert "matching block in `CLAUDE.md`" not in switched


def test_reconcile_aligned_is_noop():
    agents = _file("CLAUDE.md")
    claude = _file("AGENTS.md")
    result = reconcile(agents, "AGENTS.md", claude, "CLAUDE.md")
    assert result.status == "already-aligned"
    assert result.new_target_text is None


def test_reconcile_syncs_drift_and_preserves_outside_content():
    agents = _file("CLAUDE.md").replace("project continuity", "project CONTINUITY v2")
    claude = _file("AGENTS.md") + "\n## Claude-only notes\n\n- keep me\n"

    result = reconcile(agents, "AGENTS.md", claude, "CLAUDE.md")
    assert result.status == "synced"
    new_claude = result.new_target_text

    # Drift resolved, cross-reference correct for the target, agent-specific content kept.
    assert "project CONTINUITY v2" in new_claude
    assert "matching block in `AGENTS.md`" in new_claude
    assert "## Claude-only notes" in new_claude
    assert "- keep me" in new_claude

    report = check_drift(agents, "AGENTS.md", new_claude, "CLAUDE.md")
    assert report.status == "aligned"


def test_reconcile_injects_into_blockless_target():
    agents = _file("CLAUDE.md")
    claude = "# Claude\n\nhand-written, no block yet\n"
    result = reconcile(agents, "AGENTS.md", claude, "CLAUDE.md")
    assert result.status == "synced"
    assert "hand-written, no block yet" in result.new_target_text
    assert extract_block(result.new_target_text).found


def test_reconcile_no_source_block():
    result = reconcile("# no block here", "AGENTS.md", _file("AGENTS.md"), "CLAUDE.md")
    assert result.status == "no-source-block"
    assert result.new_target_text is None
