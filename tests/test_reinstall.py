"""`horus reinstall --verify <marker>` — uv cache clean + force-reinstall, then
grep the INSTALLED surface (not this process's already-imported modules) for
a marker string.

All subprocess calls go through `reinstall._run` (uv/systemctl); monkeypatched
here to scripted fakes so the sequence and marker grep are tested without a
real uv install or a real systemd.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from horus import reinstall


class _Proc:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _make_tool_env(tmp_path: Path, package: str, python: str = "3.12") -> Path:
    site = tmp_path / "tools" / package / "lib" / f"python{python}" / "site-packages"
    site.mkdir(parents=True)
    return site


def test_reinstall_runs_cache_clean_then_install(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, *, timeout):
        calls.append(cmd)
        if cmd[:3] == ["uv", "cache", "clean"]:
            return _Proc(0)
        if cmd[:3] == ["uv", "tool", "install"]:
            return _Proc(0)
        if cmd == ["uv", "tool", "dir"]:
            return _Proc(0, stdout=str(tmp_path / "tools") + "\n")
        raise AssertionError(cmd)

    monkeypatch.setattr(reinstall, "_run", fake_run)
    monkeypatch.setattr(reinstall, "_service_notes", lambda: [])
    _make_tool_env(tmp_path, "horus-harness")

    result = reinstall.reinstall("/some/path", "MARKER_X", package="horus-harness", python="3.12")
    assert result.ok is True
    assert calls[0] == ["uv", "cache", "clean", "horus-harness"]
    assert calls[1] == ["uv", "tool", "install", "--force", "--reinstall", "--python", "3.12", "/some/path"]


def test_reinstall_raises_when_cache_clean_fails(monkeypatch):
    monkeypatch.setattr(reinstall, "_run", lambda cmd, *, timeout: _Proc(1, stderr="boom"))
    with pytest.raises(reinstall.ReinstallError, match="uv cache clean failed"):
        reinstall.reinstall("/some/path", "X")


def test_reinstall_raises_when_install_fails(monkeypatch):
    def fake_run(cmd, *, timeout):
        if cmd[:3] == ["uv", "cache", "clean"]:
            return _Proc(0)
        return _Proc(1, stderr="install exploded")

    monkeypatch.setattr(reinstall, "_run", fake_run)
    with pytest.raises(reinstall.ReinstallError, match="uv tool install failed"):
        reinstall.reinstall("/some/path", "X")


def test_reinstall_marker_found_in_installed_surface(monkeypatch, tmp_path):
    site = _make_tool_env(tmp_path, "horus-harness")
    (site / "horus").mkdir()
    (site / "horus" / "cli.py").write_text("MARKER_PRESENT = True\n", encoding="utf-8")

    def fake_run(cmd, *, timeout):
        if cmd == ["uv", "tool", "dir"]:
            return _Proc(0, stdout=str(tmp_path / "tools") + "\n")
        return _Proc(0)

    monkeypatch.setattr(reinstall, "_run", fake_run)
    monkeypatch.setattr(reinstall, "_service_notes", lambda: [])

    result = reinstall.reinstall("/some/path", "MARKER_PRESENT", package="horus-harness", python="3.12")
    assert result.marker_found is True
    assert "cli.py" in result.detail


def test_reinstall_marker_absent_is_not_an_error(monkeypatch, tmp_path):
    _make_tool_env(tmp_path, "horus-harness")

    def fake_run(cmd, *, timeout):
        if cmd == ["uv", "tool", "dir"]:
            return _Proc(0, stdout=str(tmp_path / "tools") + "\n")
        return _Proc(0)

    monkeypatch.setattr(reinstall, "_run", fake_run)
    monkeypatch.setattr(reinstall, "_service_notes", lambda: [])

    result = reinstall.reinstall("/some/path", "NOPE_NOT_THERE", package="horus-harness", python="3.12")
    assert result.ok is True
    assert result.marker_found is False
    assert "not found" in result.detail


def test_reinstall_reports_unresolvable_tool_dir(monkeypatch):
    def fake_run(cmd, *, timeout):
        if cmd == ["uv", "tool", "dir"]:
            return _Proc(1)
        return _Proc(0)

    monkeypatch.setattr(reinstall, "_run", fake_run)
    monkeypatch.setattr(reinstall, "_service_notes", lambda: [])
    result = reinstall.reinstall("/some/path", "X")
    assert result.marker_found is False
    assert "could not locate" in result.detail


def test_reinstall_surfaces_active_known_service(monkeypatch, tmp_path):
    _make_tool_env(tmp_path, "horus-harness")

    def fake_run(cmd, *, timeout):
        if cmd == ["uv", "tool", "dir"]:
            return _Proc(0, stdout=str(tmp_path / "tools") + "\n")
        return _Proc(0)

    monkeypatch.setattr(reinstall, "_run", fake_run)
    monkeypatch.setattr(reinstall, "_service_notes", lambda: ["horus-dashboard.service is active — restart it to load this reinstall (systemctl restart horus-dashboard.service)"])

    result = reinstall.reinstall("/some/path", "X", package="horus-harness")
    assert result.service_notes and "horus-dashboard.service" in result.service_notes[0]
