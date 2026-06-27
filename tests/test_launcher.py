"""Tests for the interactive terminal launcher (no real window spawned)."""

import subprocess
import sys

from horus import launcher


def test_open_terminal_returns_child_pid(monkeypatch, tmp_path):
    calls = {}

    class FakeProc:
        pid = 4242

    def fake_popen(argv, cwd=None, env=None, creationflags=0):
        calls.update(argv=argv, cwd=cwd, env=env, creationflags=creationflags)
        return FakeProc()

    monkeypatch.setattr(launcher.shutil, "which", lambda name: name)  # resolve to itself
    monkeypatch.setattr(launcher.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(sys, "platform", "win32")

    pid = launcher.open_terminal(["claude", "--session-id", "x"], cwd=tmp_path, env={"A": "1"})

    assert pid == 4242
    assert calls["argv"] == ["claude", "--session-id", "x"]
    assert calls["cwd"] == str(tmp_path)
    assert calls["env"]["A"] == "1"
    assert calls["creationflags"] == getattr(subprocess, "CREATE_NEW_CONSOLE", 0)  # own window on Windows


def test_open_terminal_fails_without_posix_display(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    try:
        launcher.open_terminal(["codex"], cwd=tmp_path)
    except OSError as exc:
        assert "no graphical display" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected OSError")
