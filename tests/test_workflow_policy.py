"""Tests for the [workflow] section of config.toml and the `horus workflow` CLI."""

from __future__ import annotations

import pytest

from horus import config
from horus.cli import build_parser, main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


# ---------------------------------------------------------------------------
# load_workflow_policy — defaults
# ---------------------------------------------------------------------------

def test_defaults_when_no_config(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    policy = config.load_workflow_policy()
    assert policy == config.WORKFLOW_DEFAULTS


def test_defaults_when_workflow_section_absent(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    # Write a config without [workflow].
    config.register_project(tmp_path / "p1")  # creates config.toml without [workflow]
    # Patch it to remove the [workflow] section if present.
    path = config.config_path()
    text = path.read_text(encoding="utf-8")
    # Strip [workflow] section just to be safe.
    text = text.split("\n[workflow]")[0]
    path.write_text(text, encoding="utf-8")
    policy = config.load_workflow_policy()
    assert policy == config.WORKFLOW_DEFAULTS


def test_invalid_values_fall_back_to_default(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    # Write a [workflow] section with an invalid value.
    (tmp_path / "home" / ".horus").mkdir(parents=True, exist_ok=True)
    path = config.config_path()
    path.write_text(
        '# Horus user config\nworkspace_root = "/tmp/projects"\nprojects = []\ngithub_owners = []\n\n[workflow]\nintegration = "typo-bad"\ncommit = "auto"\nmerge = "auto"\n',
        encoding="utf-8",
    )
    policy = config.load_workflow_policy()
    assert policy["integration"] == config.WORKFLOW_DEFAULTS["integration"]
    assert policy["commit"] == "auto"
    assert policy["merge"] == "auto"


# ---------------------------------------------------------------------------
# set_workflow_policy — round-trips
# ---------------------------------------------------------------------------

def test_set_integration_round_trips(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    policy = config.set_workflow_policy(integration="direct-push")
    assert policy["integration"] == "direct-push"
    assert config.load_workflow_policy()["integration"] == "direct-push"


def test_set_commit_round_trips(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    policy = config.set_workflow_policy(commit="manual")
    assert policy["commit"] == "manual"
    assert config.load_workflow_policy()["commit"] == "manual"


def test_set_merge_round_trips(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    policy = config.set_workflow_policy(merge="review")
    assert policy["merge"] == "review"
    assert config.load_workflow_policy()["merge"] == "review"


def test_partial_update_preserves_other_keys(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.set_workflow_policy(integration="local-only", commit="manual", merge="review")
    # Only change one key.
    policy = config.set_workflow_policy(merge="auto")
    assert policy["integration"] == "local-only"
    assert policy["commit"] == "manual"
    assert policy["merge"] == "auto"


def test_invalid_value_raises(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="integration"):
        config.set_workflow_policy(integration="banana")


def test_invalid_commit_raises(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="commit"):
        config.set_workflow_policy(commit="maybe")


# ---------------------------------------------------------------------------
# Cross-setter preservation: workflow preserved when other setters run
# ---------------------------------------------------------------------------

def test_register_github_owner_preserves_workflow(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.set_workflow_policy(integration="local-only")
    config.register_github_owner("some-owner")
    assert config.load_workflow_policy()["integration"] == "local-only"


def test_set_workspace_root_preserves_workflow(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.set_workflow_policy(merge="review")
    config.set_workspace_root(tmp_path / "ws")
    assert config.load_workflow_policy()["merge"] == "review"


def test_set_workflow_policy_preserves_projects(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    proj = tmp_path / "myproj"
    proj.mkdir()
    config.register_project(proj)
    config.set_workflow_policy(integration="direct-push")
    assert config._as_key(proj) in config.load_projects()


def test_set_workflow_policy_preserves_owners(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.register_github_owner("owner-abc")
    config.set_workflow_policy(commit="manual")
    assert "owner-abc" in config.load_github_owners()


# ---------------------------------------------------------------------------
# `horus workflow` CLI
# ---------------------------------------------------------------------------

def test_cli_show_prints_defaults(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    rc = main(["workflow"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "integration" in out
    assert "branch-pr-automerge" in out


def test_cli_show_flag(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    rc = main(["workflow", "--show"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "commit" in out


def test_cli_set_integration(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    rc = main(["workflow", "--integration", "local-only"])
    assert rc == 0
    assert config.load_workflow_policy()["integration"] == "local-only"


def test_cli_set_commit_policy(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    rc = main(["workflow", "--commit", "manual"])
    assert rc == 0
    assert config.load_workflow_policy()["commit"] == "manual"


def test_cli_set_merge_policy(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    rc = main(["workflow", "--merge", "review"])
    assert rc == 0
    assert config.load_workflow_policy()["merge"] == "review"


def test_cli_invalid_integration_exits_nonzero(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    # argparse will reject an unrecognised choice before we even get to cmd_workflow.
    parser = build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["workflow", "--integration", "banana"])
    assert exc_info.value.code != 0
