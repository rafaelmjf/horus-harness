"""Tests for `horus doctor machine` — machine-level checks (CLI on PATH, interpreter
floor, hook commands resolvable, Tk, gh auth). Every host dependency (shutil.which,
subprocess.run, dist metadata, the tkinter import) is monkeypatched so these tests never
depend on the host actually having gh/Tk/network."""

import json
import subprocess

from horus import doctor_machine, native_hooks
from horus.cli import main


def _stub_ok(monkeypatch):
    """Patch every machine check to a passing state; tests override individual pieces."""
    monkeypatch.setattr(doctor_machine.shutil, "which", lambda cmd: f"/usr/bin/{cmd}")
    monkeypatch.setattr(doctor_machine, "_dist_requires_python", lambda: None)
    monkeypatch.setattr(doctor_machine, "_tkinter_probe", lambda: True)
    monkeypatch.setattr(
        doctor_machine.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="", stderr=""),
    )


def test_console_script_missing_fails(monkeypatch):
    _stub_ok(monkeypatch)
    monkeypatch.setattr(
        doctor_machine.shutil, "which",
        lambda cmd: None if cmd == "horus" else f"/usr/bin/{cmd}",
    )

    findings = doctor_machine.machine_findings()

    fails = [f for f in findings if f.level == "fail"]
    assert any("not found on PATH" in f.message and "horus" in f.message for f in fails)


def test_interpreter_below_floor_warns(monkeypatch):
    _stub_ok(monkeypatch)
    monkeypatch.setattr(doctor_machine, "_dist_requires_python", lambda: ">=99.0")

    findings = doctor_machine.machine_findings()

    warns = [f for f in findings if f.level == "warn"]
    assert any("requires-python floor" in f.message for f in warns)
    assert any("uv tool install --force --python 99.0 horus-harness" in f.message for f in warns)


def test_interpreter_meets_floor_ok(monkeypatch):
    _stub_ok(monkeypatch)
    monkeypatch.setattr(doctor_machine, "_dist_requires_python", lambda: ">=3.0")

    findings = doctor_machine.machine_findings()

    assert any(f.level == "ok" and "satisfies requires-python" in f.message for f in findings)


def test_missing_dist_metadata_skips_interpreter_check(monkeypatch):
    _stub_ok(monkeypatch)  # _dist_requires_python already stubbed to None (missing dist)

    findings = doctor_machine.machine_findings()

    assert not any("requires-python" in f.message for f in findings)


def test_dist_requires_python_missing_dist_returns_none():
    # A dist name that is guaranteed not to be installed exercises the real
    # PackageNotFoundError path (no monkeypatching needed).
    assert doctor_machine._dist_requires_python("definitely-not-a-real-dist-xyz") is None


def test_no_hook_config_produces_no_hook_findings(tmp_path):
    assert doctor_machine._hook_command_findings(tmp_path) == []


def test_hook_command_unresolvable_fails(tmp_path, monkeypatch):
    # Write a hook config the way native_hooks does, then splice in an extra hook
    # handler whose executable can never resolve.
    native_hooks.install_claude_usage_hook(tmp_path)
    settings_path = native_hooks.claude_settings_path(tmp_path)
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    data["hooks"].setdefault("PreToolUse", []).append(
        {
            "matcher": "Bash",
            "hooks": [{"type": "command", "command": "definitely-not-a-real-binary --flag"}],
        }
    )
    settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    _stub_ok(monkeypatch)
    monkeypatch.setattr(
        doctor_machine.shutil, "which",
        lambda cmd: None if cmd == "definitely-not-a-real-binary" else f"/usr/bin/{cmd}",
    )

    findings = doctor_machine.machine_findings(tmp_path)

    fails = [f for f in findings if f.level == "fail"]
    assert any("definitely-not-a-real-binary" in f.message for f in fails)


def test_everything_present_all_ok(tmp_path, monkeypatch):
    native_hooks.install_claude_usage_hook(tmp_path)
    _stub_ok(monkeypatch)

    findings = doctor_machine.machine_findings(tmp_path)

    assert findings
    assert not any(f.level in ("warn", "fail") for f in findings)


def test_gh_missing_warns(monkeypatch):
    _stub_ok(monkeypatch)
    monkeypatch.setattr(
        doctor_machine.shutil, "which",
        lambda cmd: None if cmd == "gh" else f"/usr/bin/{cmd}",
    )

    findings = doctor_machine.machine_findings()

    warns = [f for f in findings if f.level == "warn"]
    assert any("gh" in f.message for f in warns)


def test_gh_unauthenticated_warns(monkeypatch):
    _stub_ok(monkeypatch)
    monkeypatch.setattr(
        doctor_machine.subprocess, "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 1, stdout="", stderr="not logged in"),
    )

    findings = doctor_machine.machine_findings()

    warns = [f for f in findings if f.level == "warn"]
    assert any("not authenticated" in f.message for f in warns)


def test_tk_missing_warns(monkeypatch):
    _stub_ok(monkeypatch)
    monkeypatch.setattr(doctor_machine, "_tkinter_probe", lambda: False)

    findings = doctor_machine.machine_findings()

    warns = [f for f in findings if f.level == "warn"]
    assert any("tkinter" in f.message for f in warns)


def test_cli_doctor_machine_prints_section(tmp_path, monkeypatch, capsys):
    _stub_ok(monkeypatch)

    rc = main(["doctor", "machine", "--path", str(tmp_path)])

    out = capsys.readouterr().out
    assert "doctor machine:" in out
    assert rc == 0


def test_cli_doctor_all_includes_machine_section(tmp_path, monkeypatch, capsys):
    _stub_ok(monkeypatch)

    main(["doctor", "all", "--path", str(tmp_path)])

    out = capsys.readouterr().out
    assert "doctor machine:" in out


def test_cli_doctor_machine_fail_sets_exit_code(tmp_path, monkeypatch, capsys):
    _stub_ok(monkeypatch)
    monkeypatch.setattr(
        doctor_machine.shutil, "which",
        lambda cmd: None if cmd == "horus" else f"/usr/bin/{cmd}",
    )

    rc = main(["doctor", "machine", "--path", str(tmp_path)])

    assert rc == 1


def test_cli_doctor_machine_warn_does_not_set_exit_code(tmp_path, monkeypatch, capsys):
    _stub_ok(monkeypatch)
    monkeypatch.setattr(
        doctor_machine.shutil, "which",
        lambda cmd: None if cmd == "gh" else f"/usr/bin/{cmd}",
    )

    rc = main(["doctor", "machine", "--path", str(tmp_path)])

    assert rc == 0
