"""Tests for the project registry: register, unregister, prune."""

import pytest

from horus import config


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def test_register_and_unregister(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    proj = tmp_path / "p1"
    proj.mkdir()

    assert config.register_project(proj) is True
    assert config.register_project(proj) is False  # idempotent
    assert config._as_key(proj) in config.load_projects()

    assert config.unregister_project(proj) is True
    assert config.unregister_project(proj) is False
    assert config._as_key(proj) not in config.load_projects()


def test_github_owner_registry_coexists_with_projects(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    proj = tmp_path / "p1"
    proj.mkdir()

    saved_root = config.set_workspace_root(tmp_path / "workspace")
    assert config.register_github_owner("rafaelmjf") is True
    assert config.register_github_owner("rafaelmjf") is False
    assert config.register_project(proj) is True

    assert config.load_github_owners() == ["rafaelmjf"]
    assert config._as_key(proj) in config.load_projects()
    assert config.load_workspace_root() == saved_root

    assert config.unregister_project(proj) is True
    assert config.load_github_owners() == ["rafaelmjf"]
    assert config.load_workspace_root() == saved_root


def test_workspace_root_defaults_and_round_trips(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert config.load_workspace_root().endswith("/home/projects")

    saved = config.set_workspace_root(tmp_path / "remote projects")
    assert saved == (tmp_path / "remote projects").resolve().as_posix()
    assert config.load_workspace_root() == saved


def test_prune_removes_only_stale(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    live = tmp_path / "live"
    (live / ".horus").mkdir(parents=True)
    gone = tmp_path / "gone"  # never created

    config.register_project(live)
    # Register a path that lacks .horus by creating then removing the marker.
    (gone / ".horus").mkdir(parents=True)
    config.register_project(gone)
    import shutil

    shutil.rmtree(gone)

    removed = config.prune_projects()
    assert config._as_key(gone) in removed
    assert config._as_key(live) in config.load_projects()
    assert config._as_key(gone) not in config.load_projects()


def test_prune_noop_when_all_live(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    live = tmp_path / "live"
    (live / ".horus").mkdir(parents=True)
    config.register_project(live)
    assert config.prune_projects() == []


def test_alias_for_uses_configured_mapping(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.set_account_alias("rafael@example.com", "rafa-personal")
    assert config.alias_for("rafael@example.com") == "rafa-personal"
    # round-trips through the file
    assert config.load_account_aliases()["rafael@example.com"] == "rafa-personal"


def test_alias_for_falls_back_without_exposing_email(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    alias = config.alias_for("rafael@example.com")
    assert alias.startswith("acct-")
    assert "rafael" not in alias and "@" not in alias  # email never leaks
    # stable for the same identifier, distinct for another
    assert alias == config.alias_for("rafael@example.com")
    assert alias != config.alias_for("other@example.com")


def test_alias_for_none_when_no_identifier(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert config.alias_for(None) is None
    assert config.alias_for("") is None


def test_set_account_alias_preserves_projects(tmp_path, monkeypatch):
    # accounts live in their own file, so writing an alias must not touch projects.
    _home(tmp_path, monkeypatch)
    proj = tmp_path / "p1"
    proj.mkdir()
    config.register_project(proj)
    config.set_account_alias("a@b.com", "work")
    assert config._as_key(proj) in config.load_projects()


def test_account_aliases_and_config_dirs_coexist(tmp_path, monkeypatch):
    # Both sections live in accounts.toml; writing one must preserve the other.
    _home(tmp_path, monkeypatch)
    config.set_account_alias("rafa@work.com", "work")
    config.set_account_config_dir("work", "/home/rafa/.claude-work")
    config.set_account_alias("rafa@home.com", "personal")  # second alias write

    assert config.load_account_aliases() == {"rafa@work.com": "work", "rafa@home.com": "personal"}
    assert config.load_account_config_dirs() == {"work": "/home/rafa/.claude-work"}


def test_config_dirs_empty_by_default(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert config.load_account_config_dirs() == {}


# --------------------------------------------------------------------------- #
# Unmanaged tables (e.g. [access]) must survive a config rewrite — regression for
# the 2026-07-10 outage where register_project dropped [access] and the exposed
# dashboard crash-looped on the missing gate.
# --------------------------------------------------------------------------- #

def _home_cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    from horus import config
    config.config_dir().mkdir(parents=True, exist_ok=True)
    config.config_path().write_text(
        'workspace_root = "/x"\n\nprojects = [\n]\n\ngithub_owners = [\n]\n\n'
        '[workflow]\ncommit = "auto"\n\n[access]\n'
        'owner_email = "o@example.com"\nteam_domain = "t.cloudflareaccess.com"\n'
        'aud = "abc123"\njwks_url = "https://t/certs"\n',
        encoding="utf-8",
    )
    return config


def test_register_project_preserves_access_block(tmp_path, monkeypatch):
    config = _home_cfg(tmp_path, monkeypatch)
    assert config.register_project(tmp_path / "proj") is True
    access = config.load_dashboard_access()
    assert access is not None
    assert access.owner_email == "o@example.com"
    assert access.access.aud == "abc123"
    assert str(tmp_path / "proj") in config.load_projects()  # the write still did its job


def test_set_workflow_policy_preserves_access_block(tmp_path, monkeypatch):
    config = _home_cfg(tmp_path, monkeypatch)
    config.set_workflow_policy(commit="manual")
    assert config.load_dashboard_access() is not None
    assert config.load_workflow_policy()["commit"] == "manual"


# --------------------------------------------------------------------------- #
# TUI launch defaults ([launch] table, home-level Defaults screen).
# --------------------------------------------------------------------------- #


def test_launch_defaults_default_to_default_posture(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert config.load_launch_defaults() == {"posture": "default"}


def test_set_launch_default_posture_round_trips(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert config.set_launch_default_posture("full-auto") == "full-auto"
    assert config.load_launch_defaults() == {"posture": "full-auto"}

    assert config.set_launch_default_posture("read-only") == "read-only"
    assert config.load_launch_defaults() == {"posture": "read-only"}


def test_set_launch_default_posture_rejects_unknown_value(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    try:
        config.set_launch_default_posture("yolo")
        raised = False
    except ValueError:
        raised = True
    assert raised
    assert config.load_launch_defaults() == {"posture": "default"}  # unchanged


def test_launch_defaults_tolerates_malformed_stored_value(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.config_dir().mkdir(parents=True, exist_ok=True)
    config.config_path().write_text('[launch]\nposture = "not-a-real-posture"\n', encoding="utf-8")
    assert config.load_launch_defaults() == {"posture": "default"}


def test_set_launch_default_posture_preserves_access_block(tmp_path, monkeypatch):
    config = _home_cfg(tmp_path, monkeypatch)
    config.set_launch_default_posture("auto-edit")
    assert config.load_dashboard_access() is not None
    assert config.load_launch_defaults() == {"posture": "auto-edit"}


def test_launch_defaults_coexist_with_projects_and_workflow(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    proj = tmp_path / "p1"
    proj.mkdir()
    config.register_project(proj)
    config.set_workflow_policy(commit="manual")
    config.set_launch_default_posture("plan")

    assert config._as_key(proj) in config.load_projects()
    assert config.load_workflow_policy()["commit"] == "manual"
    assert config.load_launch_defaults() == {"posture": "plan"}

    # Registering another project afterward must not disturb the launch default.
    other = tmp_path / "p2"
    other.mkdir()
    config.register_project(other)
    assert config.load_launch_defaults() == {"posture": "plan"}


def test_continuity_defaults_to_handoff_and_persists_choices(tmp_path, monkeypatch):
    config = _home_cfg(tmp_path, monkeypatch)
    assert config.load_continuity_defaults() == {"granularity": "handoff"}

    for choice in config.CONTINUITY_GRANULARITY_CHOICES:
        assert config.set_continuity_granularity(choice) == choice
        assert config.load_continuity_defaults() == {"granularity": choice}

    with pytest.raises(ValueError):
        config.set_continuity_granularity("yolo")


def test_continuity_setting_survives_other_config_writes(tmp_path, monkeypatch):
    config = _home_cfg(tmp_path, monkeypatch)
    config.set_continuity_granularity("delivery")
    config.register_project(tmp_path / "project")
    config.set_launch_default_posture("auto-edit")
    config.set_workflow_policy(commit="manual")

    assert config.load_continuity_defaults() == {"granularity": "delivery"}


def test_continuity_setting_tolerates_malformed_stored_value(tmp_path, monkeypatch):
    config = _home_cfg(tmp_path, monkeypatch)
    config.config_dir().mkdir(parents=True, exist_ok=True)
    config.config_path().write_text('[continuity]\ngranularity = "sometimes"\n', encoding="utf-8")
    assert config.load_continuity_defaults() == {"granularity": "handoff"}
