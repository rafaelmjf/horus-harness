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
    assert config.load_launch_defaults() == {"posture": "default", "window": "takeover"}


def test_set_launch_default_posture_round_trips(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert config.set_launch_default_posture("full-auto") == "full-auto"
    assert config.load_launch_defaults() == {"posture": "full-auto", "window": "takeover"}

    assert config.set_launch_default_posture("read-only") == "read-only"
    assert config.load_launch_defaults() == {"posture": "read-only", "window": "takeover"}


def test_set_launch_default_posture_rejects_unknown_value(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    try:
        config.set_launch_default_posture("yolo")
        raised = False
    except ValueError:
        raised = True
    assert raised
    assert config.load_launch_defaults() == {"posture": "default", "window": "takeover"}  # unchanged


def test_launch_defaults_tolerates_malformed_stored_value(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.config_dir().mkdir(parents=True, exist_ok=True)
    config.config_path().write_text('[launch]\nposture = "not-a-real-posture"\n', encoding="utf-8")
    assert config.load_launch_defaults() == {"posture": "default", "window": "takeover"}


def test_set_launch_default_posture_preserves_access_block(tmp_path, monkeypatch):
    config = _home_cfg(tmp_path, monkeypatch)
    config.set_launch_default_posture("auto-edit")
    assert config.load_dashboard_access() is not None
    assert config.load_launch_defaults() == {"posture": "auto-edit", "window": "takeover"}


def test_set_launch_default_window_round_trips_and_preserves_posture(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.set_launch_default_posture("plan")
    assert config.set_launch_default_window("new-window") == "new-window"
    # The window write must not clobber the sibling posture key (shared [launch] table).
    assert config.load_launch_defaults() == {"posture": "plan", "window": "new-window"}
    # And a later posture write must preserve the window choice.
    config.set_launch_default_posture("read-only")
    assert config.load_launch_defaults() == {"posture": "read-only", "window": "new-window"}


def test_set_launch_default_window_rejects_unknown_value(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        config.set_launch_default_window("floating")
    assert config.load_launch_defaults()["window"] == "takeover"  # unchanged


def test_launch_defaults_tolerate_malformed_window_value(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.config_dir().mkdir(parents=True, exist_ok=True)
    config.config_path().write_text('[launch]\nwindow = "hologram"\n', encoding="utf-8")
    assert config.load_launch_defaults()["window"] == "takeover"


def test_launch_defaults_coexist_with_projects_and_workflow(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    proj = tmp_path / "p1"
    proj.mkdir()
    config.register_project(proj)
    config.set_workflow_policy(commit="manual")
    config.set_launch_default_posture("plan")

    assert config._as_key(proj) in config.load_projects()
    assert config.load_workflow_policy()["commit"] == "manual"
    assert config.load_launch_defaults() == {"posture": "plan", "window": "takeover"}

    # Registering another project afterward must not disturb the launch default.
    other = tmp_path / "p2"
    other.mkdir()
    config.register_project(other)
    assert config.load_launch_defaults() == {"posture": "plan", "window": "takeover"}


def test_launch_profile_absent_until_saved(tmp_path, monkeypatch):
    config = _home_cfg(tmp_path, monkeypatch)
    # No saved preference is absence, not a guessed default — the form resolves a
    # missing key to the agent's own default rather than inventing a model name.
    assert config.load_launch_profile("claude") == {}
    assert config.load_launch_profile("") == {}


def test_launch_profile_round_trips_per_agent(tmp_path, monkeypatch):
    config = _home_cfg(tmp_path, monkeypatch)
    config.save_launch_profile("claude", {"model": "opus", "effort": "high", "posture": "default"})
    config.save_launch_profile("codex", {"model": "sol", "effort": "high"})

    assert config.load_launch_profile("claude") == {
        "model": "opus", "effort": "high", "posture": "default",
    }
    assert config.load_launch_profile("codex") == {"model": "sol", "effort": "high"}


def test_launch_profile_rejects_an_invalid_posture(tmp_path, monkeypatch):
    config = _home_cfg(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        config.save_launch_profile("claude", {"posture": "yolo"})
    with pytest.raises(ValueError):
        config.save_launch_profile("", {"model": "opus"})


def test_launch_profile_survives_other_config_writes(tmp_path, monkeypatch):
    config = _home_cfg(tmp_path, monkeypatch)
    config.save_launch_profile("claude", {"model": "opus", "effort": "high"})
    config.register_project(tmp_path / "project")
    config.set_launch_default_posture("auto-edit")
    config.set_workflow_policy(commit="manual")

    assert config.load_launch_profile("claude") == {"model": "opus", "effort": "high"}


def test_launch_profile_tolerates_a_malformed_stored_table(tmp_path, monkeypatch):
    config = _home_cfg(tmp_path, monkeypatch)
    config.config_dir().mkdir(parents=True, exist_ok=True)
    config.config_path().write_text('launch_profiles = "nope"\n', encoding="utf-8")
    assert config.load_launch_profile("claude") == {}


def test_a_stale_continuity_table_is_dropped_not_carried_forward(tmp_path, monkeypatch):
    """The granularity axis is retired; an older machine's `[continuity]` table must
    not survive a config rewrite as an unmanaged entry."""
    config = _home_cfg(tmp_path, monkeypatch)
    config.config_dir().mkdir(parents=True, exist_ok=True)
    config.config_path().write_text(
        'projects = []\n\n[continuity]\ngranularity = "delivery"\n', encoding="utf-8"
    )
    config.set_launch_default_posture("auto-edit")

    assert "[continuity]" not in config.config_path().read_text(encoding="utf-8")
    assert not hasattr(config, "set_continuity_granularity")


# --------------------------------------------------------------------------- #
# TUI backlog fields ([tui] table, backlog field picker). User-level: one list
# for every project's backlog on this machine.
# --------------------------------------------------------------------------- #


def test_backlog_fields_default_to_empty(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert config.load_backlog_fields() == []
    assert config.load_tui_defaults() == {"backlog_fields": []}


def test_set_backlog_fields_round_trips_and_keeps_pick_order(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert config.set_backlog_fields(["tier", "status"]) == ["tier", "status"]
    assert config.load_backlog_fields() == ["tier", "status"]

    # Order is the owner's, not sorted: it's the render order on the card row.
    assert config.set_backlog_fields(["status", "tier"]) == ["status", "tier"]
    assert config.load_backlog_fields() == ["status", "tier"]


def test_set_backlog_fields_dedupes_and_rejects_unusable_names(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert config.set_backlog_fields(["tier", "tier", " status "]) == ["tier", "status"]

    for bad in ["not a field", "with:colon", ""]:
        with pytest.raises(ValueError):
            config.set_backlog_fields([bad])
    assert config.load_backlog_fields() == ["tier", "status"]  # unchanged


def test_toggle_backlog_field_adds_then_removes(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert config.toggle_backlog_field("tier") == ["tier"]
    assert config.toggle_backlog_field("status") == ["tier", "status"]
    assert config.toggle_backlog_field("tier") == ["status"]
    assert config.load_backlog_fields() == ["status"]


def test_backlog_fields_tolerate_malformed_stored_value(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.config_dir().mkdir(parents=True, exist_ok=True)
    config.config_path().write_text(
        '[tui]\nbacklog_fields = ["tier", 3, "not a field", "tier", "status"]\n',
        encoding="utf-8",
    )
    # Garbled entries drop out; the readable ones still render.
    assert config.load_backlog_fields() == ["tier", "status"]

    config.config_path().write_text('[tui]\nbacklog_fields = "tier"\n', encoding="utf-8")
    assert config.load_backlog_fields() == []


def test_backlog_fields_survive_other_config_writes(tmp_path, monkeypatch):
    config = _home_cfg(tmp_path, monkeypatch)
    config.set_backlog_fields(["tier", "vision_facet"])
    config.register_project(tmp_path / "project")
    config.set_launch_default_posture("auto-edit")
    config.save_launch_profile("claude", {"model": "opus"})

    assert config.load_backlog_fields() == ["tier", "vision_facet"]
    assert config.load_dashboard_access() is not None


# --- shipped status-line pointer (horus-statusline-default) --------------------


def test_write_statusline_pointer_creates_and_is_idempotent(tmp_path):
    import json
    cfg = tmp_path / "acct"
    assert config.write_statusline_pointer(cfg) is True   # created
    data = json.loads((cfg / "settings.json").read_text())
    assert data["statusLine"] == {"type": "command", "command": "horus statusline"}
    assert config.write_statusline_pointer(cfg) is False  # already set -> no-op


def test_write_statusline_pointer_preserves_other_settings(tmp_path):
    import json
    cfg = tmp_path / "acct"
    cfg.mkdir()
    (cfg / "settings.json").write_text(json.dumps({"env": {"FOO": "bar"}, "model": "opus"}))
    assert config.write_statusline_pointer(cfg) is True
    data = json.loads((cfg / "settings.json").read_text())
    assert data["env"] == {"FOO": "bar"} and data["model"] == "opus"   # preserved
    assert data["statusLine"]["command"] == "horus statusline"


def test_isolate_account_writes_the_statusline_pointer(tmp_path, monkeypatch):
    import json
    _home(tmp_path, monkeypatch)
    # a claude login in the ambient dir to isolate
    ambient = tmp_path / "home" / ".claude"
    ambient.mkdir(parents=True)
    (ambient / ".credentials.json").write_text("{}")
    ok, _msg = config.isolate_account("claude", "work")
    assert ok
    dest = config.default_account_dir("claude", "work")
    data = json.loads((dest / "settings.json").read_text())
    assert data["statusLine"]["command"] == "horus statusline"


# --- proxy env clearer (vision-branch-x4; migration cleanup only) ----------------
# There is deliberately no write_proxy_env: B injects proxy env at launch, never into
# a shared settings.json (that poisons running sessions). clear_proxy_env stays to
# strip env a pre-B build wrote.

def test_clear_proxy_env_removes_only_proxy_keys(tmp_path):
    import json
    d = tmp_path / "acct"
    d.mkdir()
    (d / "settings.json").write_text(json.dumps({"env": {
        "FOO": "bar", "ANTHROPIC_BASE_URL": "u", "ANTHROPIC_AUTH_TOKEN": "t",
        "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY": "1"}}), encoding="utf-8")
    assert config.clear_proxy_env(d) is True
    data = json.loads((d / "settings.json").read_text())
    assert data["env"] == {"FOO": "bar"}               # only proxy keys removed
    assert config.clear_proxy_env(d) is False           # nothing left to clear


def test_clear_proxy_env_drops_an_emptied_env_block(tmp_path):
    import json
    d = tmp_path / "acct"
    d.mkdir()
    (d / "settings.json").write_text(json.dumps({"model": "opus", "env": {
        "ANTHROPIC_BASE_URL": "u", "ANTHROPIC_AUTH_TOKEN": "t"}}), encoding="utf-8")
    assert config.clear_proxy_env(d) is True
    data = json.loads((d / "settings.json").read_text())
    assert "env" not in data and data["model"] == "opus"   # empty env removed, rest kept
