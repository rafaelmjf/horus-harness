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
