"""Tests for the lightweight Horus companion shell."""

import subprocess
import sys

from horus import companion


def test_dashboard_url_defaults_to_localhost():
    assert companion.dashboard_url() == "http://127.0.0.1:8765"
    assert companion.dashboard_url("localhost", 9000) == "http://localhost:9000"


def test_mascot_asset_is_packaged():
    path = companion.mascot_asset_path()
    assert path.name == "mascot.png"
    assert path.is_file()


def test_ensure_dashboard_does_not_spawn_when_live(monkeypatch):
    monkeypatch.setattr(companion, "dashboard_is_live", lambda url: True)

    result = companion.ensure_dashboard()

    assert result.url == "http://127.0.0.1:8765"
    assert result.started is False
    assert result.process is None


def test_ensure_dashboard_respects_no_start(monkeypatch):
    monkeypatch.setattr(companion, "dashboard_is_live", lambda url: False)

    result = companion.ensure_dashboard(start=False)

    assert result.started is False
    assert result.process is None


def test_ensure_dashboard_spawns_horus_dashboard(monkeypatch):
    calls = []

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            calls.append((cmd, kwargs))

    monkeypatch.setattr(companion, "dashboard_is_live", lambda url: False)
    monkeypatch.setattr(subprocess, "Popen", FakePopen)

    result = companion.ensure_dashboard(port=9999)

    assert result.started is True
    assert calls[0][0] == [sys.executable, "-m", "horus", "dashboard", "--host", "127.0.0.1", "--port", "9999"]
