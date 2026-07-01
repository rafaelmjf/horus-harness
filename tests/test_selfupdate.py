"""Tests for the self-update signal (installed CLI vs latest PyPI release)."""

from horus import selfupdate


def test_is_newer():
    assert selfupdate.is_newer("0.0.3", "0.0.2")
    assert selfupdate.is_newer("0.1.0", "0.0.9")
    assert not selfupdate.is_newer("0.0.2", "0.0.2")
    assert not selfupdate.is_newer("0.0.1", "0.0.2")


def test_check_update_caches_the_pypi_answer(tmp_path, monkeypatch):
    monkeypatch.setattr(selfupdate.config, "config_dir", lambda: tmp_path)
    calls: list[int] = []

    def fake_fetch(timeout: float = 3.0):
        calls.append(1)
        return "9.9.9"

    monkeypatch.setattr(selfupdate, "fetch_latest_version", fake_fetch)

    first = selfupdate.check_update(now=1000.0)
    assert first["update_available"] and first["latest"] == "9.9.9"
    selfupdate.check_update(now=1001.0)
    assert len(calls) == 1  # inside the TTL: served from cache
    selfupdate.check_update(now=1000.0 + selfupdate.CACHE_TTL_SECONDS + 1)
    assert len(calls) == 2  # TTL expired: refetched


def test_check_update_offline_is_silent(tmp_path, monkeypatch):
    monkeypatch.setattr(selfupdate.config, "config_dir", lambda: tmp_path)
    monkeypatch.setattr(selfupdate, "fetch_latest_version", lambda timeout=3.0: None)
    status = selfupdate.check_update(now=0.0)
    assert status["latest"] is None
    assert status["update_available"] is False


def test_run_upgrade_reports_last_line(monkeypatch):
    class Result:
        returncode = 0
        stdout = "Resolved 1 package\nUpdated horus-harness v0.0.2 -> v0.0.3\n"
        stderr = ""

    monkeypatch.setattr(selfupdate.subprocess, "run", lambda *a, **k: Result())
    ok, detail = selfupdate.run_upgrade()
    assert ok and "0.0.3" in detail


def test_run_upgrade_without_uv(monkeypatch):
    def missing(*a, **k):
        raise FileNotFoundError

    monkeypatch.setattr(selfupdate.subprocess, "run", missing)
    ok, detail = selfupdate.run_upgrade()
    assert not ok and "uv" in detail
