"""Tests for the session/process registry."""

import json
import subprocess
import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from horus import datums, delivery, registry as registry_mod, runlog
from horus.adapters import FakeAdapter, SpawnSpec
from horus.registry import Registry, SessionRecord, is_recent, process_alive, track


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


def test_future_registry_fields_are_ignored_and_preserved_on_known_updates(tmp_path):
    reg = _reg(tmp_path)
    reg.path.write_text(
        '{"sessions":{"future":{"session_id":"future","agent":"codex",'
        '"project":"/proj","status":"exited","future_signal":"keep-me"}}}\n',
        encoding="utf-8",
    )

    got = reg.get("future")
    assert got is not None and got.status == "exited"

    reg.upsert(got)
    persisted = json.loads(reg.path.read_text(encoding="utf-8"))
    assert persisted["sessions"]["future"]["future_signal"] == "keep-me"


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


def test_reconcile_prefers_jsonl_result_event(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    reg = _reg(tmp_path)
    reg.upsert(_rec(session_id="done-by-log", pid=os.getpid(), status="running"))
    # A conflicting legacy log must not override the structured sidecar.
    log = runlog.run_log_path("done-by-log")
    log.parent.mkdir(parents=True)
    log.write_text("RESULT failed — session done-by-log (account work)\n", encoding="utf-8")
    runlog.append_event("done-by-log", "result", status="exited", rc=0, ended_at=runlog.utc_iso())

    changed = reg.reconcile()

    assert [r.session_id for r in changed] == ["done-by-log"]
    got = reg.get("done-by-log")
    assert got.status == "exited"
    assert got.returncode == 0


def test_reconcile_persists_delivery_completion_when_result_newly_discovered(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    reg = _reg(tmp_path)
    reg.upsert(_rec(
        session_id="delivery-result", project="/project", pid=os.getpid(), status="running",
        delivery_expected=True, dispatch_base_sha="base",
    ))
    datums.DatumStore.default().record_launch(datums.Datum(session_id="delivery-result", agent="fake"))
    runlog.append_event("delivery-result", "result", status="exited", rc=0, ended_at=runlog.utc_iso())
    evidence = delivery.DeliveryEvidence(
        True, "2026-07-16T10:00:00+00:00", branch="worker/test", head_sha="base",
        pushed_sha="base", local_changes=False, continuity_closed=False,
        head_beyond_base=False, pushed_beyond_base=False,
    )
    monkeypatch.setattr(registry_mod.delivery, "capture_delivery_evidence", lambda *_args, **_kwargs: evidence)

    changed = reg.reconcile()

    assert [record.session_id for record in changed] == ["delivery-result"]
    result = reg.get("delivery-result")
    assert result.status == "exited" and result.delivery_status == "no-op"
    assert result.delivery_branch == "worker/test" and result.delivery_checked_at == evidence.checked_at
    event = runlog.read_events("delivery-result")[-1]
    assert event["delivery_status"] == "no-op" and event["delivery_branch"] == "worker/test"
    datum = datums.DatumStore.default().get("delivery-result")
    assert datum.delivery_status == "no-op" and datum.delivery_checked_at == evidence.checked_at


def test_reconcile_falls_back_to_legacy_result_line(tmp_path, monkeypatch):
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


# --- recency (default-view de-emphasis for horus sessions) -------------------

def test_is_recent_true_within_horizon_false_beyond_it():
    now = datetime.now(timezone.utc)
    fresh = _rec(updated_at=(now - timedelta(hours=1)).isoformat(timespec="seconds"))
    old = _rec(updated_at=(now - timedelta(hours=48)).isoformat(timespec="seconds"))
    assert is_recent(fresh, now=now) is True
    assert is_recent(old, now=now) is False


def test_is_recent_fails_open_on_unparseable_timestamp():
    assert is_recent(_rec(updated_at="not-a-timestamp")) is True
    assert is_recent(_rec(updated_at="")) is True


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


# --- `--resume` id translation ----------------------------------------------
#
# `horus sessions` / `horus tail` show the HORUS id; `--resume` needs the AGENT
# conversation id. Passing the visible one died in 2s with rc=1 and no text
# (observed 2026-07-27 resuming a drill worker), so both forms are accepted.

def test_resume_translates_the_horus_id_operators_actually_see(tmp_path):
    reg = _reg(tmp_path)
    reg.upsert(_rec(session_id="horus-1", agent_session_id="agent-1"))

    res = reg.resolve_resume_id("horus-1")

    assert res.agent_session_id == "agent-1"
    assert res.known
    assert "horus session id" in res.note and "agent-1" in res.note


def test_resume_passes_an_agent_id_through_without_comment(tmp_path):
    reg = _reg(tmp_path)
    reg.upsert(_rec(session_id="horus-1", agent_session_id="agent-1"))

    res = reg.resolve_resume_id("agent-1")

    assert res.agent_session_id == "agent-1"
    assert res.known
    assert res.note == ""  # nothing to explain — it was already the right form


def test_a_failed_resume_attempt_cannot_feed_its_own_bad_id_back(tmp_path):
    """The regression that makes lookup ORDER load-bearing.

    A failed `--resume horus-1` registers a NEW row whose `agent_session_id` is the
    bad horus id it was given. Scanning agent ids before row keys would match that
    self-inflicted row and hand `horus-1` straight back to the adapter — the exact
    silent failure again, now permanently.
    """
    reg = _reg(tmp_path)
    reg.upsert(_rec(session_id="horus-1", agent_session_id="agent-1"))
    # The wreckage of the failed attempt, exactly as run_executor records it.
    reg.upsert(_rec(session_id="horus-2", agent_session_id="horus-1", status="failed"))

    res = reg.resolve_resume_id("horus-1")

    assert res.agent_session_id == "agent-1"


def test_resume_id_unknown_to_horus_passes_through_with_a_note(tmp_path):
    """Never refuse: an agent session Horus never tracked is still resumable."""
    reg = _reg(tmp_path)
    reg.upsert(_rec(session_id="horus-1", agent_session_id="agent-1"))

    res = reg.resolve_resume_id("never-seen")

    assert res.agent_session_id == "never-seen"
    assert not res.known
    assert "not a session id Horus has tracked" in res.note
    assert "horus sessions --all" in res.note


def test_resume_row_without_an_agent_id_says_so_rather_than_guessing(tmp_path):
    reg = _reg(tmp_path)
    reg.upsert(_rec(session_id="horus-1", agent_session_id=None))
    # Blank it explicitly: `_record` back-fills a missing key with the horus id, so the
    # only way to hold "no agent id" is an empty value.
    raw = json.loads((tmp_path / "registry.json").read_text())
    raw["sessions"]["horus-1"]["agent_session_id"] = ""
    (tmp_path / "registry.json").write_text(json.dumps(raw))

    res = reg.resolve_resume_id("horus-1")

    assert res.agent_session_id == "horus-1"  # passed through, not invented
    assert "never recorded an agent session id" in res.note


def test_legacy_row_where_both_ids_coincide_needs_no_translation(tmp_path):
    reg = _reg(tmp_path)
    reg.upsert(_rec(session_id="same-id", agent_session_id="same-id"))

    res = reg.resolve_resume_id("same-id")

    assert res.agent_session_id == "same-id"
    assert res.note == ""


def test_a_failed_resume_names_the_id_it_used(tmp_path, monkeypatch, capsys):
    """"failed" alone reads as a crashed worker rather than a rejected argument —
    the expensive misreading inside a scheduled supervise loop. The id must be named."""
    from horus import run_executor
    from horus.adapters import FakeAdapter

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    project = tmp_path / "proj"
    project.mkdir()

    class RejectingFake(FakeAdapter):
        """An agent that refuses the resume id, as `claude --resume <bad id>` does."""
        def __init__(self) -> None:
            super().__init__(script=[{"event": "result", "ok": False}])

    monkeypatch.setattr(run_executor.adapters, "get_adapter", lambda _agent: RejectingFake())
    request = run_executor.RunRequest(
        session_id="51345678-1234-1234-1234-123456789abc", agent="fake", project=project,
        prompt="continue", account=None, posture="default", model=None, effort=None,
        worker=False, resume="agent-xyz", dispatch_base_sha=None, dispatch_pending=0,
    )

    rc = run_executor.execute(request)
    out = capsys.readouterr().out

    assert rc == 1
    assert "resumed with agent session id agent-xyz" in out
    assert "horus sessions --all" in out
