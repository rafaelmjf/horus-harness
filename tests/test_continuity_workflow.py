"""The GitHub freshness job is a required-check candidate, never advisory."""

from pathlib import Path


def test_continuity_workflow_fails_on_pr_diff_freshness():
    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "continuity.yml"
    ).read_text(encoding="utf-8")
    assert 'close --check --base-ref "origin/${{ github.base_ref }}"' in workflow
    assert "|| echo" not in workflow
    assert "::warning::Continuity" not in workflow
