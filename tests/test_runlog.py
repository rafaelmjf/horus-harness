"""Per-session run-log tee and the tail read/follow helpers."""

import json
from datetime import datetime

from horus import runlog


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def test_run_log_path_sanitizes_session_id(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    path = runlog.run_log_path("weird/../id:with spaces")
    assert path.parent == runlog.run_log_path("x").parent  # can't escape logs/runs/
    assert path.name == "weird-..-id-with-spaces.log"  # separators neutralized, dots kept


def test_run_events_path_sanitizes_session_id(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    path = runlog.run_events_path("weird/../id:with spaces")
    assert path.parent == runlog.run_events_path("x").parent
    assert path.name == "weird-..-id-with-spaces.jsonl"


def test_append_event_writes_start_and_result_jsonl(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)

    runlog.append_event(
        "sess-1",
        "start",
        agent="fake",
        account="work",
        project="/proj",
        pid=123,
        argv={"prompt": "hello"},
    )
    runlog.append_event("sess-1", "result", status="exited", rc=0, ended_at=runlog.utc_iso())

    lines = runlog.run_events_path("sess-1").read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines]
    assert [event["event"] for event in events] == ["start", "result"]
    assert events[0]["session_id"] == "sess-1"
    assert events[0]["agent"] == "fake"
    assert events[1]["status"] == "exited"
    assert events[1]["rc"] == 0
    for event in events:
        stamp = datetime.fromisoformat(event["ts"])
        assert stamp.tzinfo is not None
        assert event["ts"].endswith("+00:00")


def test_run_writes_start_and_result_events(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus.cli import main

    rc = main(["run", "hello there", "--agent", "fake", "--path", str(tmp_path)])

    assert rc == 0
    capsys.readouterr()
    events = runlog.read_events("fake-session")
    assert [event["event"] for event in events] == ["start", "result"]
    assert events[0]["agent"] == "fake"
    assert events[0]["project"] == tmp_path.resolve().as_posix()
    assert events[0]["argv"]["prompt"] == "hello there"
    assert events[1]["status"] == "exited"


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
