"""Tests for the lightweight Horus companion shell."""

import subprocess
import sys
from pathlib import Path

from horus import companion


def test_dashboard_url_defaults_to_localhost():
    assert companion.dashboard_url() == "http://127.0.0.1:8765"
    assert companion.dashboard_url("localhost", 9000) == "http://localhost:9000"


def test_mascot_asset_is_packaged():
    path = companion.mascot_asset_path()
    assert path.name == "mascot.png"
    assert path.is_file()


def test_mascot_background_asset_is_packaged():
    path = companion.mascot_background_path()
    assert path.name == "background_egypt.png"
    assert path.is_file()


def test_mascot_animation_frames_are_packaged():
    paths = companion.mascot_frame_paths()
    assert [p.name for p in paths] == [
        "mascot_idle_0.png",
        "mascot_idle_1.png",
        "mascot_idle_2.png",
        "mascot_blink.png",
    ]
    assert all(p.is_file() for p in paths)


def test_mascot_background_sources_are_packaged():
    assets = companion.mascot_asset_path().parent
    assert (assets / "background_egypt.png").is_file()
    assert (assets / "mascot_with_background.png").is_file()
    assert (assets / "mascot_without_background.png").is_file()


def test_resolve_mascot_style_defaults_to_foreground_on_windows():
    assert companion.resolve_mascot_style("auto", platform="win32") == "foreground"


def test_resolve_mascot_style_defaults_to_layered_off_windows():
    assert companion.resolve_mascot_style("auto", platform="linux") == "layered"
    assert companion.resolve_mascot_style("auto", platform="darwin") == "layered"


def test_resolve_mascot_style_respects_explicit_choice():
    assert companion.resolve_mascot_style("foreground", platform="linux") == "foreground"
    assert companion.resolve_mascot_style("layered", platform="win32") == "layered"


def test_ensure_dashboard_does_not_spawn_when_live(monkeypatch):
    monkeypatch.setattr(companion, "dashboard_is_live", lambda url: True)

    result = companion.ensure_dashboard()

    assert result.url == "http://127.0.0.1:8765"
    assert result.started is False
    assert result.process is None


def test_singleton_lock_is_exclusive():
    first = companion.acquire_singleton_lock(8779)
    assert first is not None
    assert companion.acquire_singleton_lock(8779) is None  # second instance blocked
    first.close()
    again = companion.acquire_singleton_lock(8779)  # released on close
    assert again is not None
    again.close()


def test_open_dashboard_defaults_to_browser_tab(monkeypatch):
    calls = {}
    monkeypatch.setattr(companion, "_app_browser", lambda: ["FAKE.exe"])
    monkeypatch.setattr(companion.subprocess, "Popen", lambda cmd, **k: calls.setdefault("cmd", cmd))
    monkeypatch.setattr(companion.webbrowser, "open", lambda *a, **k: calls.setdefault("tab", a))

    companion.open_dashboard("http://x")

    assert "cmd" not in calls
    assert calls["tab"][0] == "http://x"


def test_open_dashboard_app_window_is_explicit(monkeypatch):
    calls = {}
    monkeypatch.setattr(companion, "_app_browser", lambda: ["FAKE.exe"])
    monkeypatch.setattr(companion.subprocess, "Popen", lambda cmd, **k: calls.setdefault("cmd", cmd))
    monkeypatch.setattr(companion.webbrowser, "open", lambda *a, **k: calls.setdefault("tab", a))

    companion.open_dashboard("http://x", app_window=True)

    assert "tab" not in calls
    assert calls["cmd"][0] == "FAKE.exe" and "--app=http://x" in calls["cmd"]


def test_open_dashboard_supports_flatpak_argv(monkeypatch):
    calls = {}
    monkeypatch.setattr(companion, "_app_browser", lambda: ["flatpak", "run", "com.google.Chrome"])
    monkeypatch.setattr(companion.subprocess, "Popen", lambda cmd, **k: calls.setdefault("cmd", cmd))

    companion.open_dashboard("http://x", app_window=True)

    assert calls["cmd"] == [
        "flatpak",
        "run",
        "com.google.Chrome",
        "--app=http://x",
        "--window-size=1200,760",
    ]


def test_open_dashboard_falls_back_to_tab(monkeypatch):
    calls = {}
    monkeypatch.setattr(companion, "_app_browser", lambda: None)
    monkeypatch.setattr(companion.webbrowser, "open", lambda url, **k: calls.setdefault("tab", url))

    companion.open_dashboard("http://x")

    assert calls["tab"] == "http://x"


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


def test_stop_dashboard_terminates_only_spawned():
    class FakeProc:
        def __init__(self):
            self.terminated = False
            self.waited = False

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            self.waited = True

    spawned = FakeProc()
    companion.stop_dashboard(companion.DashboardProcess("http://x", True, spawned))
    assert spawned.terminated is True
    assert spawned.waited is True

    reused = FakeProc()
    companion.stop_dashboard(companion.DashboardProcess("http://x", False, reused))
    assert reused.terminated is False  # reused/existing one is left alone
    assert reused.waited is False

    # No process at all -> no crash.
    companion.stop_dashboard(companion.DashboardProcess("http://x", True, None))


def test_stop_dashboard_kills_when_spawned_process_does_not_exit():
    class FakeProc:
        def __init__(self):
            self.terminated = False
            self.killed = False
            self.waits = 0

        def terminate(self):
            self.terminated = True

        def kill(self):
            self.killed = True

        def wait(self, timeout=None):
            self.waits += 1
            if self.waits == 1:
                raise subprocess.TimeoutExpired("horus dashboard", timeout)

    proc = FakeProc()
    companion.stop_dashboard(companion.DashboardProcess("http://x", True, proc), timeout=0.01)

    assert proc.terminated is True
    assert proc.killed is True
    assert proc.waits == 2


def test_relaunch_without_console_noop_off_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert companion.relaunch_without_console() is False


def test_relaunch_without_console_noop_when_already_detached(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("HORUS_DETACHED", "1")
    assert companion.relaunch_without_console() is False


def test_relaunch_without_console_noop_under_pythonw(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("HORUS_DETACHED", raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Python\pythonw.exe")
    assert companion.relaunch_without_console() is False


def test_relaunch_without_console_spawns_pythonw(monkeypatch):
    calls = []

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            calls.append((cmd, kwargs))

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("HORUS_DETACHED", raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Python\python.exe")
    monkeypatch.setattr(sys, "argv", ["horus", "app", "--path", "."])
    monkeypatch.setattr(Path, "is_file", lambda self: True)
    monkeypatch.setattr(subprocess, "Popen", FakePopen)

    assert companion.relaunch_without_console() is True
    cmd, kwargs = calls[0]
    assert cmd == [r"C:\Python\pythonw.exe", "-m", "horus", "app", "--path", "."]
    assert kwargs["env"]["HORUS_DETACHED"] == "1"
