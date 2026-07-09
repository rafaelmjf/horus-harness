"""Tests for `horus doctor machine` — machine-level checks (CLI on PATH, interpreter
floor, hook commands resolvable, Tk, gh auth). Every host dependency (shutil.which,
subprocess.run, dist metadata, the tkinter import) is monkeypatched so these tests never
depend on the host actually having gh/Tk/network."""

import json
import os
import subprocess

from horus import doctor_machine, native_hooks
from horus.cli import main


def _stub_ok(monkeypatch):
    """Patch every machine check to a passing state; tests override individual pieces."""
    monkeypatch.setattr(doctor_machine.shutil, "which", lambda cmd: f"/usr/bin/{cmd}")
    monkeypatch.setattr(doctor_machine, "_dist_requires_python", lambda: None)
    monkeypatch.setattr(doctor_machine, "_tkinter_probe", lambda: True)
    # One horus on PATH by default (no shadow); shadow tests override this.
    monkeypatch.setattr(doctor_machine, "_all_on_path", lambda name: [f"/usr/bin/{name}"])
    # No running dashboards by default — never probe the real host, and never let a
    # dashboard actually running on this machine leak a warn into unrelated tests.
    monkeypatch.setattr(doctor_machine, "_scan_running_dashboards", lambda: [])
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


def test_code_cli_present_ok(monkeypatch):
    _stub_ok(monkeypatch)

    findings = doctor_machine.machine_findings()

    assert any(f.level == "ok" and "VS Code CLI" in f.message for f in findings)


def test_code_cli_missing_warns(monkeypatch):
    _stub_ok(monkeypatch)
    monkeypatch.setattr(
        doctor_machine.shutil, "which",
        lambda cmd: None if cmd == "code" else f"/usr/bin/{cmd}",
    )

    findings = doctor_machine.machine_findings()

    warns = [f for f in findings if f.level == "warn"]
    assert any("VS Code" in f.message and "launch destination" in f.message for f in warns)


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


def test_shadow_install_warns_on_multiple_horus(monkeypatch):
    _stub_ok(monkeypatch)
    monkeypatch.setattr(
        doctor_machine, "_all_on_path",
        lambda name: [
            r"C:\\Python312\\Scripts\\horus.exe",
            r"C:\\Users\\User\\.local\\bin\\horus.exe",
        ],
    )

    findings = doctor_machine.machine_findings()

    warns = [f for f in findings if f.level == "warn"]
    assert any("multiple `horus` executables" in f.message for f in warns)
    # Names the winner (first on PATH) and the shadowed copy.
    msg = next(f.message for f in warns if "multiple" in f.message)
    assert r"C:\\Python312\\Scripts\\horus.exe" in msg
    assert ".local" in msg


def test_shadow_install_ok_on_single_horus(monkeypatch):
    _stub_ok(monkeypatch)  # already stubs a single-entry _all_on_path

    findings = doctor_machine.machine_findings()

    assert any(f.level == "ok" and "single `horus`" in f.message for f in findings)
    assert not any("multiple `horus`" in f.message for f in findings)


def test_shadow_install_finding_none_when_no_horus(monkeypatch):
    monkeypatch.setattr(doctor_machine, "_all_on_path", lambda name: [])
    assert doctor_machine._shadow_install_finding() is None


def test_all_on_path_dedupes_and_orders(tmp_path, monkeypatch):
    # Two real dirs on PATH, each with an executable `horus`; a third PATH entry
    # repeats the first dir (must not double-count).
    d1, d2 = tmp_path / "a", tmp_path / "b"
    for d in (d1, d2):
        d.mkdir()
        exe = d / "horus"
        exe.write_text("#!/bin/sh\n")
        exe.chmod(0o755)
    monkeypatch.setattr(doctor_machine.sys, "platform", "linux")
    monkeypatch.setenv("PATH", os.pathsep.join([str(d1), str(d2), str(d1)]))

    found = doctor_machine._all_on_path("horus")

    assert found == [str(d1 / "horus"), str(d2 / "horus")]


def test_stale_dashboard_warns(monkeypatch):
    _stub_ok(monkeypatch)
    monkeypatch.setattr(doctor_machine, "installed_disk_version", lambda: "0.0.29")
    monkeypatch.setattr(
        doctor_machine, "_scan_running_dashboards",
        lambda: [{"app": "horus-dashboard", "version": "0.0.25", "pid": 4242, "port": 8771}],
    )

    findings = doctor_machine.machine_findings()

    warns = [f for f in findings if f.level == "warn"]
    msg = next((f.message for f in warns if "old build" in f.message), "")
    assert "v0.0.25" in msg and "v0.0.29" in msg
    assert "8771" in msg and "kill 4242" in msg


def test_current_dashboard_does_not_warn(monkeypatch):
    _stub_ok(monkeypatch)
    monkeypatch.setattr(doctor_machine, "installed_disk_version", lambda: "0.0.29")
    monkeypatch.setattr(
        doctor_machine, "_scan_running_dashboards",
        lambda: [{"app": "horus-dashboard", "version": "0.0.29", "pid": 4242, "port": 8765}],
    )

    findings = doctor_machine.machine_findings()

    assert not any("old build" in f.message for f in findings)


def test_dashboard_ahead_of_install_does_not_warn(monkeypatch):
    # A dev checkout whose running build is *newer* than the install metadata is not
    # stale in the harmful sense (mirrors selfupdate.build_state's "disk newer" rule).
    _stub_ok(monkeypatch)
    monkeypatch.setattr(doctor_machine, "installed_disk_version", lambda: "0.0.25")
    monkeypatch.setattr(
        doctor_machine, "_scan_running_dashboards",
        lambda: [{"app": "horus-dashboard", "version": "0.0.29", "pid": 4242, "port": 8765}],
    )

    assert doctor_machine._stale_dashboard_findings() == []


def test_stale_dashboard_silent_without_install_metadata(monkeypatch):
    # Bare checkout: no install to compare a running build against — never warn.
    monkeypatch.setattr(doctor_machine, "installed_disk_version", lambda: None)
    monkeypatch.setattr(
        doctor_machine, "_scan_running_dashboards",
        lambda: [{"app": "horus-dashboard", "version": "0.0.25", "pid": 4242, "port": 8771}],
    )

    assert doctor_machine._stale_dashboard_findings() == []


def test_scan_running_dashboards_dedupes_by_pid(monkeypatch):
    # The same process answering on two probed ports counts once.
    def fake_identity(url):
        return {"app": "horus-dashboard", "version": "0.0.29", "pid": 7}

    monkeypatch.setattr(doctor_machine.companion, "dashboard_identity", fake_identity)

    found = doctor_machine._scan_running_dashboards(ports=[8765, 8766])

    assert len(found) == 1
    assert found[0]["pid"] == 7


def test_scan_running_dashboards_skips_dead_ports(monkeypatch):
    monkeypatch.setattr(doctor_machine.companion, "dashboard_identity", lambda url: None)

    assert doctor_machine._scan_running_dashboards(ports=[8765, 8766]) == []


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
