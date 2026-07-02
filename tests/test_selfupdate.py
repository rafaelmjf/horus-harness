"""Tests for the self-update signal (installed CLI vs latest PyPI release)."""

from horus import selfupdate


def test_is_newer():
    assert selfupdate.is_newer("0.0.3", "0.0.2")
    assert selfupdate.is_newer("0.1.0", "0.0.9")
    assert not selfupdate.is_newer("0.0.2", "0.0.2")
    assert not selfupdate.is_newer("0.0.1", "0.0.2")


def test_build_state_stale_only_when_disk_is_newer(monkeypatch):
    monkeypatch.setattr(selfupdate, "installed_disk_version", lambda: "9.9.9")
    state = selfupdate.build_state()
    assert state["stale"] is True and state["disk"] == "9.9.9"
    monkeypatch.setattr(selfupdate, "installed_disk_version", lambda: selfupdate.__version__)
    assert selfupdate.build_state()["stale"] is False  # in sync
    monkeypatch.setattr(selfupdate, "installed_disk_version", lambda: "0.0.0")
    assert selfupdate.build_state()["stale"] is False  # dev source ahead of install metadata
    monkeypatch.setattr(selfupdate, "installed_disk_version", lambda: None)
    assert selfupdate.build_state()["stale"] is False  # no dist on disk


def test_python_floor_parsing():
    assert selfupdate._python_floor(">=3.12") == (3, 12)
    assert selfupdate._python_floor(">=3.12,<4") == (3, 12)
    assert selfupdate._python_floor("<4,>= 3.13") == (3, 13)
    assert selfupdate._python_floor(">=junk") is None
    assert selfupdate._python_floor("~=3.12") is None  # only >= floors are read
    assert selfupdate._python_floor(None) is None


def test_check_update_caches_the_pypi_answer(tmp_path, monkeypatch):
    monkeypatch.setattr(selfupdate.config, "config_dir", lambda: tmp_path)
    calls: list[int] = []

    def fake_fetch(timeout: float = 3.0):
        calls.append(1)
        return {"version": "9.9.9", "requires_python": ">=3.12"}

    monkeypatch.setattr(selfupdate, "fetch_release_info", fake_fetch)

    first = selfupdate.check_update(now=1000.0)
    assert first["update_available"] and first["latest"] == "9.9.9"
    assert first["requires_python"] == ">=3.12"
    cached = selfupdate.check_update(now=1001.0)
    assert len(calls) == 1  # inside the TTL: served from cache
    assert cached["requires_python"] == ">=3.12"  # the floor survives the cache round-trip
    selfupdate.check_update(now=1000.0 + selfupdate.CACHE_TTL_SECONDS + 1)
    assert len(calls) == 2  # TTL expired: refetched


def test_check_update_offline_is_silent(tmp_path, monkeypatch):
    monkeypatch.setattr(selfupdate.config, "config_dir", lambda: tmp_path)
    monkeypatch.setattr(selfupdate, "fetch_release_info", lambda timeout=3.0: None)
    status = selfupdate.check_update(now=0.0)
    assert status["latest"] is None
    assert status["update_available"] is False


def _quiet_update_status(monkeypatch, *, latest=None, requires=None):
    monkeypatch.setattr(
        selfupdate,
        "check_update",
        lambda **kw: {
            "installed": selfupdate.__version__,
            "latest": latest,
            "requires_python": requires,
            "update_available": bool(latest),
        },
    )


def test_run_upgrade_reports_last_line(monkeypatch):
    class Result:
        returncode = 0
        stdout = "Resolved 1 package\nUpdated horus-harness v0.0.2 -> v0.0.3\n"
        stderr = ""

    _quiet_update_status(monkeypatch)
    monkeypatch.setattr(selfupdate, "installed_disk_version", lambda: None)
    monkeypatch.setattr(selfupdate.subprocess, "run", lambda *a, **k: Result())
    ok, detail = selfupdate.run_upgrade()
    assert ok and "0.0.3" in detail


def test_run_upgrade_without_uv(monkeypatch):
    def missing(*a, **k):
        raise FileNotFoundError

    _quiet_update_status(monkeypatch)
    monkeypatch.setattr(selfupdate.subprocess, "run", missing)
    ok, detail = selfupdate.run_upgrade()
    assert not ok and "uv" in detail


def test_run_upgrade_refreshes_the_index(monkeypatch):
    """A stale uv index cache silently no-ops `uv tool upgrade` (seen live twice).
    `--reinstall` implies `--refresh`; upgrade rejects a bare `--refresh` (uv 0.11)."""
    commands: list[list[str]] = []

    class Result:
        returncode = 0
        stdout = "ok\n"
        stderr = ""

    _quiet_update_status(monkeypatch, latest="9.9.9", requires=">=3.0")
    monkeypatch.setattr(selfupdate, "installed_disk_version", lambda: "9.9.9")
    monkeypatch.setattr(
        selfupdate.subprocess, "run", lambda cmd, **k: commands.append(cmd) or Result()
    )
    ok, _ = selfupdate.run_upgrade()
    assert ok
    assert commands[0][:3] == ["uv", "tool", "upgrade"] and "--reinstall" in commands[0]


def test_run_upgrade_migrates_an_interpreter_pinned_env(monkeypatch):
    """Env python below the latest release's floor: a plain upgrade would silently
    resolve the newest OLD release, so the env is recreated with --python."""
    commands: list[list[str]] = []

    class Result:
        returncode = 0
        stdout = "installed\n"
        stderr = ""

    _quiet_update_status(monkeypatch, latest="9.9.9", requires=">=99.9")
    monkeypatch.setattr(selfupdate, "installed_disk_version", lambda: None)
    monkeypatch.setattr(
        selfupdate.subprocess, "run", lambda cmd, **k: commands.append(cmd) or Result()
    )
    ok, _ = selfupdate.run_upgrade()
    assert ok
    assert commands[0][:4] == ["uv", "tool", "install", "--force"]
    assert "--python" in commands[0] and "99.9" in commands[0]


def test_run_upgrade_detects_the_silent_old_version_success(monkeypatch):
    """uv exits 0 but the disk never reached the latest release — the pinned-env
    trap. Must NOT report success; must name the one-time migration command."""

    class Result:
        returncode = 0
        stdout = "Nothing to upgrade\n"
        stderr = ""

    # requires_python unknown (e.g. stale cache without the field): the plain
    # upgrade path runs, then the post-verify catches the stall.
    _quiet_update_status(monkeypatch, latest="9.9.9", requires=None)
    monkeypatch.setattr(selfupdate, "installed_disk_version", lambda: "0.0.6")
    monkeypatch.setattr(selfupdate.subprocess, "run", lambda *a, **k: Result())
    ok, detail = selfupdate.run_upgrade()
    assert not ok
    assert "uv tool install --force --python" in detail and "0.0.6" in detail
