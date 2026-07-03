"""Per-session run-log tee and the tail read/follow helpers."""

from horus import runlog


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def test_run_log_path_sanitizes_session_id(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    path = runlog.run_log_path("weird/../id:with spaces")
    assert path.parent == runlog.run_log_path("x").parent  # can't escape logs/runs/
    assert path.name == "weird-..-id-with-spaces.log"  # separators neutralized, dots kept


def test_runlog_buffers_lines_until_bound(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    log = runlog.RunLog()
    log.line("before-id")
    assert log.path is None  # nothing written yet — no id, no file
    log.bind("sess-1")
    log.line("after-id")
    log.bind("other-id")  # second bind is a no-op; the log stays on the first id
    text = runlog.run_log_path("sess-1").read_text(encoding="utf-8")
    assert text == "before-id\nafter-id\n"


def test_runlog_swallows_filesystem_errors(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    logs = tmp_path / "home" / ".horus" / "logs"
    logs.parent.mkdir(parents=True)
    logs.write_text("a file where the log dir should be", encoding="utf-8")
    log = runlog.RunLog()
    log.bind("sess-1")
    log.line("must not raise")  # logging never breaks the run


def test_read_from_is_incremental_and_tolerates_missing_file(tmp_path):
    path = tmp_path / "s.log"
    assert runlog.read_from(path, 0) == ("", 0)  # not written yet
    path.write_text("one\n", encoding="utf-8")
    text, offset = runlog.read_from(path, 0)
    assert text == "one\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write("two\n")
    text, offset = runlog.read_from(path, offset)
    assert text == "two\n"
    assert runlog.read_from(path, offset) == ("", offset)


def test_follow_emits_then_stops_after_terminal_quiet_window(tmp_path, monkeypatch):
    path = tmp_path / "s.log"
    path.write_text("first\n", encoding="utf-8")

    clock = {"t": 0.0}
    monkeypatch.setattr(runlog.time, "monotonic", lambda: clock["t"])
    monkeypatch.setattr(runlog.time, "sleep", lambda _s: clock.update(t=clock["t"] + 0.5))

    emitted: list[str] = []
    offset = runlog.follow(
        path, 0, emit=emitted.append, is_terminal=lambda: True, quiet_seconds=2.0
    )
    assert emitted == ["first\n"]  # existing content streamed through
    assert offset == path.stat().st_size  # stopped only after draining the file
    assert clock["t"] >= 2.0  # waited out the quiet window, no real sleeping
