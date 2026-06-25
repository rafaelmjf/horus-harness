"""Tests for the project registry: register, unregister, prune."""

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
