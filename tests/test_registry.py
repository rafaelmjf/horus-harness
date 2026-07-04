"""Tests for the session/process registry."""

import subprocess
import sys
import os
from pathlib import Path

from horus import runlog
from horus.adapters import FakeAdapter, SpawnSpec
from horus.registry import Registry, SessionRecord, process_alive, track


def _reg(tmp_path) -> Registry:
    return Registry(tmp_path / "registry.json")


def _rec(session_id="s1", **kw) -> SessionRecord:
    base = dict(session_id=session_id, agent="claude", project="/proj", pid=os.getpid(), status="running")
    base.update(kw)
    return SessionRecord(**base)


# --- persistence / CRUD ------------------------------------------------------

def test_upsert_persists_and_survives_reload(tmp_path):
    reg = _reg(tmp_path)
    reg.upsert(_rec(session_id="abc", account="work"))

    fresh = Registry(tmp_path / "registry.json")  # simulate a restart
    got = fresh.get("abc")
    assert got is not None and got.account == "work" and got.status == "running"
    assert got.updated_at  # stamped on upsert


def test_timestamps_are_aware_utc(tmp_path):
    # Transcripts are UTC, rollout filenames local; the registry must be the
    # unambiguous clock. Legacy rows were naive local time.
    from datetime import datetime

    reg = _reg(tmp_path)
    reg.upsert(_rec(session_id="abc"))
    reg.set_status("abc", "exited", returncode=0)
    stamp = reg.get("abc").updated_at
    assert datetime.fromisoformat(stamp).tzinfo is not None
    assert stamp.endswith("+00:00")


def test_upsert_is_idempotent_by_session_id(tmp_path):
    reg = _reg(tmp_path)
    reg.upsert(_rec(session_id="abc", status="running"))
    reg.upsert(_rec(session_id="abc", status="exited"))
    assert len(reg.all()) == 1
    assert reg.get("abc").status == "exited"


def test_set_status_and_remove(tmp_path):
    reg = _reg(tmp_path)
    reg.upsert(_rec(session_id="abc"))
    assert reg.set_status("abc", "failed", returncode=1) is True
    assert reg.set_status("missing", "failed") is False
    got = reg.get("abc")
    assert got.status == "failed" and got.returncode == 1
    assert reg.remove("abc") is True and reg.get("abc") is None


def test_missing_file_reads_empty(tmp_path):
    assert Registry(tmp_path / "nope.json").all() == []


# --- liveness / reconcile ----------------------------------------------------

def _finished_pid() -> int:
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


def test_process_alive_self_and_dead():
    import os

    assert process_alive(None) is False
    assert process_alive(-1) is False
    assert process_alive(os.getpid()) is True       # this very process
    assert process_alive(_finished_pid()) is False  # a process that ran to completion


def test_reconcile_marks_dead_running_records(tmp_path):
    reg = _reg(tmp_path)
    reg.upsert(_rec(session_id="dead", pid=_finished_pid(), status="running"))
    reg.upsert(_rec(session_id="noproc", pid=None, status="running"))
    reg.upsert(_rec(session_id="done", pid=999999, status="exited"))  # terminal: untouched

    changed = reg.reconcile()
    by_id = {r.session_id: r for r in changed}
    assert by_id["dead"].status == "stale"
    assert by_id["noproc"].status == "stale"
    assert "done" not in by_id
    assert reg.get("done").status == "exited"


def test_reconcile_marks_result_event_completion(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    reg = _reg(tmp_path)
    reg.upsert(_rec(session_id="done-by-log", pid=os.getpid(), status="running"))
    log = runlog.run_log_path("done-by-log")
    log.parent.mkdir(parents=True)
    log.write_text("hello\nRESULT exited — session done-by-log (account work)\n", encoding="utf-8")

    changed = reg.reconcile()

    assert [r.session_id for r in changed] == ["done-by-log"]
    assert reg.get("done-by-log").status == "exited"


def test_prune_drops_only_terminal(tmp_path):
    reg = _reg(tmp_path)
    reg.upsert(_rec(session_id="run", status="running"))
    reg.upsert(_rec(session_id="ex", status="exited"))
    removed = reg.prune()
    assert removed == ["ex"]
    assert {r.session_id for r in reg.all()} == {"run"}


# --- bridge from the adapter -------------------------------------------------

def test_from_session_requires_id():
    from horus.adapters.base import AgentSession
    try:
        SessionRecord.from_session(AgentSession(agent="claude", project_dir=Path("/p")))
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_track_registers_from_a_fake_run(tmp_path):
    reg = _reg(tmp_path)
    run = FakeAdapter(session_id="fk-1").spawn(SpawnSpec(prompt="hi", project_dir=Path("/proj"), account="rafa"))
    events = list(track(reg, run))

    assert events  # events still flow through to the caller
    rec = reg.get("fk-1")
    assert rec is not None
    assert rec.agent == "fake" and rec.account == "rafa"
    assert rec.status == "exited"  # final status recorded after the stream ended
