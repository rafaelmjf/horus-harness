"""Tests for account isolation by default.

`config.isolate_account` provisions a per-account CLAUDE_CONFIG_DIR / CODEX_HOME
by copying the current login into ~/.horus/accounts/<agent>-<alias> and mapping it,
so an onboarded account never shares the ambient dir (two agent CLIs on one config
dir corrupt its JSON state). Wired into `horus account --set`/`--isolate` and the
dashboard's account-add.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from horus import cli, claude_usage, config, dashboard


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)


def _login_claude(tmp_path) -> Path:
    d = tmp_path / "home" / ".claude"
    d.mkdir(parents=True, exist_ok=True)
    (d / ".credentials.json").write_text('{"claudeAiOauth": {"accessToken": "x"}}', encoding="utf-8")
    (d / ".claude.json").write_text('{"oauthAccount": {"emailAddress": "a@b.com"}}', encoding="utf-8")
    return d


# --- the provisioning primitive -----------------------------------------------


def test_default_account_dir_naming(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert config.default_account_dir("claude", "work") == config.config_dir() / "accounts" / "claude-work"
    assert config.default_account_dir("codex", "work") == config.config_dir() / "accounts" / "codex-work"


def test_isolate_claude_copies_login_and_maps(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    _login_claude(tmp_path)

    isolated, _msg = config.isolate_account("claude", "work")

    assert isolated is True
    dest = config.config_dir() / "accounts" / "claude-work"
    assert (dest / ".credentials.json").exists() and (dest / ".claude.json").exists()
    assert config.load_account_config_dirs()["work"] == str(dest)
    # Non-destructive: the ambient login is left intact (copy, not move).
    assert (tmp_path / "home" / ".claude" / ".credentials.json").exists()


def test_isolate_is_idempotent_when_already_mapped(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    _login_claude(tmp_path)
    config.isolate_account("claude", "work")
    isolated, msg = config.isolate_account("claude", "work")
    assert isolated is True and "already isolated" in msg


def test_isolate_returns_error_when_no_login(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)  # no ~/.claude created
    isolated, msg = config.isolate_account("claude", "work")
    assert isolated is False and "no claude login" in msg


def test_isolate_maps_in_place_when_source_is_canonical(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    dest = config.config_dir() / "accounts" / "claude-work"
    dest.mkdir(parents=True)
    (dest / ".credentials.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(dest))  # login already lives in the canonical dir

    isolated, _msg = config.isolate_account("claude", "work")

    assert isolated is True
    assert config.load_account_config_dirs()["work"] == str(dest)


def test_isolate_codex_copies_auth_json(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    ch = tmp_path / "home" / ".codex"
    ch.mkdir(parents=True)
    (ch / "auth.json").write_text('{"account_id": "abc"}', encoding="utf-8")

    isolated, _msg = config.isolate_account("codex", "work")

    assert isolated is True
    dest = config.config_dir() / "accounts" / "codex-work"
    assert (dest / "auth.json").exists()
    assert config.load_account_codex_homes()["work"] == str(dest)


# --- CLI wiring: `horus account --set` isolates by default --------------------


def _account_args(**kw):
    base = {"agent": "claude", "alias": None, "set_dir": None, "set_codex_home": None,
            "alias_name": None, "isolate": False, "no_isolate": False}
    base.update(kw)
    return argparse.Namespace(**base)


def test_cmd_account_set_isolates_by_default(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    _login_claude(tmp_path)
    monkeypatch.setattr(claude_usage, "current_account", lambda *a, **k: "user@example.com")

    assert cli.cmd_account(_account_args(alias="work")) == 0
    dest = config.config_dir() / "accounts" / "claude-work"
    assert config.load_account_config_dirs().get("work") == str(dest)


def test_cmd_account_no_isolate_only_aliases(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    _login_claude(tmp_path)
    monkeypatch.setattr(claude_usage, "current_account", lambda *a, **k: "user@example.com")

    assert cli.cmd_account(_account_args(alias="work", no_isolate=True)) == 0
    assert "work" not in config.load_account_config_dirs()


def test_cmd_account_explicit_isolate_flag(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    _login_claude(tmp_path)
    monkeypatch.setattr(claude_usage, "current_account", lambda *a, **k: "user@example.com")
    config.set_account_alias("user@example.com", "work")

    assert cli.cmd_account(_account_args(isolate=True, alias_name="work")) == 0
    dest = config.config_dir() / "accounts" / "claude-work"
    assert config.load_account_config_dirs().get("work") == str(dest)


# --- dashboard account-add: no path -> isolate by default ---------------------


def test_dashboard_add_without_path_isolates(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    _login_claude(tmp_path)

    assert dashboard.process_account_add({"agent": "claude", "alias": "work"}) == "account=added"
    dest = config.config_dir() / "accounts" / "claude-work"
    assert config.load_account_config_dirs()["work"] == str(dest)


def test_dashboard_add_without_path_errors_when_no_login(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert dashboard.process_account_add({"agent": "claude", "alias": "work"}).startswith("error=")


def test_dashboard_add_with_explicit_path_still_works(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    custom = tmp_path / "custom"
    assert dashboard.process_account_add(
        {"agent": "claude", "alias": "work", "path": str(custom)}
    ) == "account=added"
    assert config.load_account_config_dirs()["work"] == str(custom)
