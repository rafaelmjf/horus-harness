"""Remote-authoritative fleet review data model and CLI."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from horus import cli, fleet_review


PRD = """---
status: active
current_focus: "Remote focus"
next_action: "Remote next"
---

## Vision

Remote project is the canonical thing.

## Shipped

- Remote capability
"""

OPEN_CARD = """---
title: Remote bug
status: open
priority: high
type: bug
---
"""

SHIPPED_CARD = """---
title: Old work
status: shipped
priority: high
type: feature
---
"""


def _manifest(path: Path, rows: str) -> Path:
    path.write_text(f"version = 1\n{rows}", encoding="utf-8")
    return path


def test_load_manifest_requires_unique_path_free_repository_entries(tmp_path):
    path = _manifest(
        tmp_path / "fleet.toml",
        """
[[projects]]
id = "zeta"
repo = "owner/zeta"
status = "maintenance"

[[projects]]
id = "alpha"
repo = "owner/alpha"
status = "active"
""",
    )
    loaded_path, projects = fleet_review.load_manifest([], path)
    assert loaded_path == path
    assert [(p.id, p.repo, p.status) for p in projects] == [
        ("alpha", "owner/alpha", "active"),
        ("zeta", "owner/zeta", "maintenance"),
    ]

    duplicate = _manifest(
        tmp_path / "duplicate.toml",
        '[[projects]]\nid = "same"\nrepo = "owner/one"\n'
        '[[projects]]\nid = "same"\nrepo = "owner/two"\n',
    )
    with pytest.raises(ValueError, match="duplicate"):
        fleet_review.load_manifest([], duplicate)


def test_local_remote_truth_reads_origin_ref_and_excludes_terminal_cards(monkeypatch, tmp_path):
    calls = []

    def fake_git(root, *args):
        calls.append(args)
        mapping = {
            ("show", "origin/main:.horus/PRD.md"): PRD,
            ("rev-parse", "origin/main"): "abcdef123456\n",
            ("ls-tree", "--name-only", "origin/main:.horus/backlog"): "open.md\nold.md\narchive\n",
            ("show", "origin/main:.horus/backlog/open.md"): OPEN_CARD,
            ("show", "origin/main:.horus/backlog/old.md"): SHIPPED_CARD,
            ("log", "-1", "--format=%H", "origin/main", "--", ".horus/PRD.md"): "continuity\n",
            (
                "rev-list",
                "--count",
                "continuity..origin/main",
                "--",
                ".",
                ":(exclude).horus/**",
            ): "2\n",
        }
        return mapping.get(args)

    monkeypatch.setattr(fleet_review, "_git", fake_git)
    truth = fleet_review._local_remote_truth(tmp_path, {"default_branch": "main"})
    assert truth.available and truth.source == "git"
    assert truth.current_focus == "Remote focus"
    assert truth.capabilities == ["Remote capability"]
    assert [card["name"] for card in truth.backlog] == ["open"]
    assert truth.backlog_mode == "cards"
    assert truth.source_commits_since_continuity == 2
    assert ("show", "origin/main:.horus/PRD.md") in calls

    stale = fleet_review._local_remote_truth(
        tmp_path, {"default_branch": "main", "fetch_status": "failed"}
    )
    assert "may be stale" in stale.note


def test_build_keeps_remote_and_local_state_separate_and_uses_github_fallback(
    monkeypatch, tmp_path
):
    local = tmp_path / "local"
    local.mkdir()
    manifest = _manifest(
        tmp_path / "fleet.toml",
        """
[[projects]]
id = "local"
repo = "owner/local"
status = "active"

[[projects]]
id = "remote-only"
repo = "owner/remote-only"
status = "active"
""",
    )
    monkeypatch.setattr(fleet_review, "_local_roots", lambda _paths: {"owner/local": local})
    fetched = {
        "default_branch": "main",
        "branch": "feature/local",
        "commit": {"hash": "123", "rel": "now", "subject": "work"},
        "dirty": True,
        "upstream": "origin/feature/local",
        "behind": 0,
        "ahead": 1,
        "remote_url": "https://github.com/owner/local.git",
        "detached": False,
        "own_upstream_gone": False,
        "default_ahead": 1,
        "default_behind": 0,
        "fetch_status": "ok",
    }
    monkeypatch.setattr(fleet_review.fetchcheck, "fetch_and_state", lambda root, ttl=0: fetched)
    monkeypatch.setattr(
        fleet_review,
        "_local_remote_truth",
        lambda root, state: fleet_review.RemoteTruth(
            available=True, source="git", ref="origin/main", current_focus="upstream"
        ),
    )
    monkeypatch.setattr(
        fleet_review,
        "_github_remote_truth",
        lambda repo: fleet_review.RemoteTruth(
            available=True, source="github", ref="main", current_focus="github"
        ),
    )

    review = fleet_review.build([str(local)], manifest_path=manifest)
    first, second = review.projects
    assert first.remote.current_focus == "upstream"
    assert "feature/local" in first.local.summary and "uncommitted" in first.local.summary
    assert second.remote.source == "github"
    assert second.local.available is False

    rendered = fleet_review.render_text(review)
    assert "REMOTE SHIPPED TRUTH" in rendered
    assert "LOCAL WORKING STATE" in rendered
    assert rendered.index("upstream") < rendered.index("feature/local")


def test_github_fallback_decodes_remote_prd_and_cards(monkeypatch):
    encoded_prd = base64.b64encode(PRD.encode()).decode()
    encoded_card = base64.b64encode(OPEN_CARD.encode()).decode()

    def fake_json(endpoint):
        mapping = {
            "repos/owner/demo": {"default_branch": "main"},
            "repos/owner/demo/contents/.horus/PRD.md?ref=main": {
                "encoding": "base64",
                "content": encoded_prd,
            },
            "repos/owner/demo/commits/main": {"sha": "abcdef"},
            "repos/owner/demo/contents/.horus/backlog?ref=main": [
                {"type": "file", "name": "bug.md"}
            ],
            "repos/owner/demo/contents/.horus/backlog/bug.md?ref=main": {
                "encoding": "base64",
                "content": encoded_card,
            },
            "repos/owner/demo/commits?sha=main&path=.horus/PRD.md&per_page=1": [
                {"sha": "continuity"}
            ],
        }
        return mapping.get(endpoint)

    monkeypatch.setattr(fleet_review, "_gh_json", fake_json)
    truth = fleet_review._github_remote_truth("owner/demo")
    assert truth.available and truth.source == "github"
    assert truth.current_focus == "Remote focus"
    assert truth.backlog[0]["name"] == "bug"
    assert truth.continuity_sha == "continuity"


def test_cli_fleet_review_renders_json(monkeypatch, capsys):
    review = fleet_review.FleetReview(
        "fleet.toml",
        [
            fleet_review.ProjectReview(
                "demo",
                "owner/demo",
                "active",
                fleet_review.RemoteTruth(available=True, source="git", ref="origin/main"),
                fleet_review.LocalWorkingState(),
            )
        ],
    )
    monkeypatch.setattr(cli.config, "load_projects", lambda: ["/demo"])
    monkeypatch.setattr(cli.fleet_review, "build", lambda projects: review)
    assert cli.main(["fleet", "--review", "--stdout"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == 1
    assert payload["projects"][0]["remote"]["source"] == "git"
