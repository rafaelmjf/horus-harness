"""Tests for the frozen LaunchBackend seam and its only concrete impl, LocalBackend.

These pin the contract: LocalBackend is a behavior-preserving wrapper around the
attended local launcher (`horus.launch.launch_interactive`), it rejects non-local
targets honestly (native-Windows is an explicit gap), and the four seam operations
map to real local primitives — no silent fallback, no fake session.
"""

import pytest

from horus import backend, launcher, registry, terminal_sessions
from horus.backend import (
    Handle,
    LaunchBrief,
    LaunchFailed,
    LocalBackend,
    UnsupportedOperation,
    UnsupportedTarget,
)
from horus.registry import Registry
from horus.launch import LaunchResult


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def test_local_backend_satisfies_the_protocol():
    # runtime_checkable Protocol: the concrete backend is an instance of the seam.
    assert isinstance(LocalBackend(), backend.LaunchBackend)


def test_default_brief_targets_local():
    brief = LaunchBrief(project_dir="/tmp/p")
    assert brief.target == backend.LOCAL and brief.agent == "claude"


def test_launch_wraps_interactive_and_tracks_running_session(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    captured = {}

    def fake_open(argv, cwd, env=None):
        captured["argv"] = argv
        return 4242

    monkeypatch.setattr(launcher, "open_terminal", fake_open)
    monkeypatch.setattr(registry, "process_alive", lambda pid: pid == 4242)

    handle = LocalBackend().launch(LaunchBrief(project_dir=tmp_path, agent="fake", account="demo"))

    assert isinstance(handle, Handle)
    assert handle.backend == "local" and handle.meta["pid"] == 4242
    # Same registry side effect as launch_interactive — no behavior change.
    recs = Registry.default().all()
    assert len(recs) == 1
    assert recs[0].status == "running" and recs[0].session_id == handle.session_id
    assert "--session-id" in captured["argv"]


def test_launch_failure_raises_launchfailed(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    with pytest.raises(LaunchFailed) as exc:
        LocalBackend().launch(LaunchBrief(project_dir=tmp_path, agent="nope"))
    assert "nope" in str(exc.value)
    assert Registry.default().all() == []  # nothing tracked on failure


def test_local_backend_accepts_managed_local_launch_function(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    captured = {}

    def fake_managed(**kwargs):
        captured.update(kwargs)
        return LaunchResult(
            True,
            kwargs["agent"],
            tmp_path,
            session_id="managed-session",
            pid=4242,
            target_ref="horus-managed",
        )

    handle = LocalBackend(launch_fn=fake_managed).launch(
        LaunchBrief(project_dir=tmp_path, agent="codex")
    )
    assert captured["agent"] == "codex"
    assert handle.meta == {"pid": 4242, "target_ref": "horus-managed"}


def test_launch_rejects_native_windows_as_an_explicit_gap(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    called = {"n": 0}
    monkeypatch.setattr(backend.launch, "launch_interactive", lambda **_: called.update(n=1))

    with pytest.raises(UnsupportedTarget) as exc:
        LocalBackend().launch(LaunchBrief(project_dir=tmp_path, target=backend.NATIVE_WINDOWS))

    assert "native-windows" in str(exc.value) and "gap" in str(exc.value)
    assert called["n"] == 0  # rejected before touching the launcher — no silent fallback


def test_launch_rejects_unknown_remote_target_without_fallback(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    called = {"n": 0}
    monkeypatch.setattr(backend.launch, "launch_interactive", lambda **_: called.update(n=1))

    with pytest.raises(UnsupportedTarget) as exc:
        LocalBackend().launch(LaunchBrief(project_dir=tmp_path, target="native-posix"))

    assert "remote backend" in str(exc.value) and "No silent fallback" in str(exc.value)
    assert called["n"] == 0


def test_status_maps_registry_record(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    monkeypatch.setattr(launcher, "open_terminal", lambda argv, cwd, env=None: 4242)
    monkeypatch.setattr(registry, "process_alive", lambda pid: pid == 4242)

    be = LocalBackend()
    handle = be.launch(LaunchBrief(project_dir=tmp_path, agent="fake"))
    assert be.status(handle).state == "running"


def test_status_unknown_when_no_record(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    st = LocalBackend().status(Handle(backend="local", session_id="ghost"))
    assert st.state == "unknown"


def test_stream_is_honestly_unsupported_for_attended_local_sessions():
    with pytest.raises(UnsupportedOperation):
        # stream() returns a generator lazily, so force it.
        list(LocalBackend().stream(Handle(backend="local", session_id="x")))


def test_stop_terminates_pid_and_marks_exited(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    monkeypatch.setattr(launcher, "open_terminal", lambda argv, cwd, env=None: 4242)
    monkeypatch.setattr(registry, "process_alive", lambda pid: pid == 4242)

    killed = {}
    monkeypatch.setattr(backend, "_terminate_process", lambda pid: killed.setdefault("pid", pid))

    be = LocalBackend()
    handle = be.launch(LaunchBrief(project_dir=tmp_path, agent="fake"))
    be.stop(handle)

    assert killed["pid"] == 4242
    assert Registry.default().get(handle.session_id).status == "exited"


def test_stop_without_pid_is_a_noop_terminate(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    monkeypatch.setattr(backend, "_terminate_process", lambda pid: (_ for _ in ()).throw(AssertionError))
    # No pid in meta -> no terminate call, still marks the (absent) record best-effort.
    LocalBackend().stop(Handle(backend="local", session_id="x"))


def test_stop_managed_handle_kills_tmux_session(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    stopped = []
    monkeypatch.setattr(
        terminal_sessions,
        "stop_session",
        lambda session_id, reg=None: stopped.append((session_id, reg)),
    )
    store = Registry.default()
    be = LocalBackend(reg=store)
    be.stop(
        Handle(
            backend="local",
            session_id="managed-session",
            meta={"pid": 4242, "target_ref": "horus-managed"},
        )
    )
    assert stopped == [("managed-session", store)]


def test_handle_ownership_is_guarded():
    with pytest.raises(backend.BackendError):
        LocalBackend().status(Handle(backend="omnigent", session_id="x"))


def test_seam_does_not_import_omnigent():
    # The optional Omnigent backend must never become a Horus dependency.
    import sys

    assert not any("omnigent" in mod.lower() for mod in sys.modules), (
        "importing horus.backend must not pull in any Omnigent module"
    )
