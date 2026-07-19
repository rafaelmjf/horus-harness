"""The aggregate `schedule-batch-complete` signal.

Membership is reconstructed from `--batch`-tagged scheduled units; per-leg completion
+ outcome come from the ledger→datum join (a detached worker is done only when its
datum is terminal, not when its timer fired). Every external reader is stubbed so
nothing here touches systemd, the network, or the real datum store.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from horus import batch, cli, notify, schedule
from horus.datums import Datum


class _Store:
    def __init__(self, by_session):
        self._by = by_session

    def get(self, session_id):
        return self._by.get(session_id)


def _datum(session_id, **over):
    base = dict(session_id=session_id, completed_at="2026-07-19T02:00:00Z")
    base.update(over)
    return Datum(**base)


def _sched(id_, *, card, fired, batch_id="B"):
    cmd = ("python", "-m", "horus", "run", "p", "--card", card, "--batch", batch_id)
    return schedule.Schedule(id=id_, description=f"dispatch {card}",
                             when="2026-07-19 01:00:00", command=cmd, fired=fired)


def _stub(monkeypatch, *, schedules, ledger, tmp):
    monkeypatch.setattr(batch.activity.schedule, "availability",
                        lambda: schedule.Availability(True, "ok"))
    monkeypatch.setattr(batch.activity.schedule, "load_all", lambda: schedules)
    monkeypatch.setattr(batch.activity.envelope, "load_all",
                        lambda: [type("E", (), {"name": "away", "merge_authority": False})()])
    monkeypatch.setattr(batch.activity.envelope, "read_ledger", lambda name: ledger)
    monkeypatch.setattr(batch.config, "config_dir", lambda: tmp)


def _capture_escalations(monkeypatch):
    sent = []
    monkeypatch.setattr(
        batch.notify, "escalate",
        lambda esc, **kw: sent.append(esc) or notify.EscalationResult(sink="telegram", delivered=True),
    )
    return sent


def test_batch_of_reads_the_tag():
    assert batch.batch_of(_sched("a", card="c", fired=True, batch_id="away7")) == "away7"
    plain = schedule.Schedule(id="x", description="d", when="w", command=("python", "-m", "horus", "warmup"))
    assert batch.batch_of(plain) is None


def test_report_not_all_done_while_a_leg_is_still_running(monkeypatch, tmp_path):
    scheds = [_sched("a", card="c1", fired=True), _sched("b", card="c2", fired=True)]
    ledger = [
        {"ts": "1", "card": "c1", "session_id": "s1"},
        {"ts": "2", "card": "c2", "session_id": "s2"},
    ]
    store = _Store({"s1": _datum("s1", delivery_status="delivery-ready"),
                    "s2": _datum("s2", completed_at=None)})  # worker still running
    _stub(monkeypatch, schedules=scheds, ledger=ledger, tmp=tmp_path)
    rep = batch.report("B", store=store)
    assert len(rep.members) == 2
    assert rep.finished_count == 1 and rep.all_done is False


def test_emit_fires_exactly_once_when_the_last_leg_finishes(monkeypatch, tmp_path):
    scheds = [_sched("a", card="c1", fired=True), _sched("b", card="c2", fired=True)]
    ledger = [{"ts": "1", "card": "c1", "session_id": "s1"},
              {"ts": "2", "card": "c2", "session_id": "s2"}]
    store = _Store({"s1": _datum("s1", delivery_status="delivery-ready", delivery_pr_number=1),
                    "s2": _datum("s2", delivery_status="blocked")})
    sent = _capture_escalations(monkeypatch)
    _stub(monkeypatch, schedules=scheds, ledger=ledger, tmp=tmp_path)
    r1 = batch.emit_if_complete("B", Path("/repo"), store=store)
    assert r1 is not None and len(sent) == 1
    assert sent[0].event == notify.SCHEDULE_BATCH_COMPLETE
    assert "c1" in sent[0].summary and "c2" in sent[0].summary  # per-leg roll-up
    # Idempotent: a re-fire / race / deadline overlap sends nothing more.
    assert batch.emit_if_complete("B", Path("/repo"), store=store) is None
    assert len(sent) == 1


def test_emit_waits_until_every_leg_is_terminal(monkeypatch, tmp_path):
    scheds = [_sched("a", card="c1", fired=True), _sched("b", card="c2", fired=True)]
    ledger = [{"ts": "1", "card": "c1", "session_id": "s1"}]  # c2 has no run yet
    store = _Store({"s1": _datum("s1", delivery_status="delivery-ready")})
    sent = _capture_escalations(monkeypatch)
    _stub(monkeypatch, schedules=scheds, ledger=ledger, tmp=tmp_path)
    assert batch.emit_if_complete("B", Path("/repo"), store=store) is None
    assert sent == []  # not the last one out — no signal


def test_deadline_backstop_reports_a_hung_leg_as_timed_out(monkeypatch, tmp_path):
    scheds = [_sched("a", card="c1", fired=True), _sched("b", card="c2", fired=True)]
    ledger = [{"ts": "1", "card": "c1", "session_id": "s1"}]  # c2 never finished
    store = _Store({"s1": _datum("s1", delivery_status="delivery-ready")})
    sent = _capture_escalations(monkeypatch)
    _stub(monkeypatch, schedules=scheds, ledger=ledger, tmp=tmp_path)
    r = batch.emit_if_complete("B", Path("/repo"), deadline=True, store=store)
    assert r is not None and len(sent) == 1
    assert "INCOMPLETE" in sent[0].summary and "timed out" in sent[0].summary


def test_no_members_no_signal(monkeypatch, tmp_path):
    _stub(monkeypatch, schedules=[], ledger=[], tmp=tmp_path)
    assert batch.emit_if_complete("ghost", Path("/repo"), store=_Store({})) is None


def test_schedule_batch_complete_is_a_default_event_marked_not_a_warning():
    assert notify.SCHEDULE_BATCH_COMPLETE in notify.DEFAULT_EVENTS  # enabled by default
    esc = notify.Escalation(event=notify.SCHEDULE_BATCH_COMPLETE, project="p", summary="done")
    assert esc.body().startswith("✓")  # a rollup, not a ⚠ nag


def test_runrequest_batch_survives_the_payload_roundtrip():
    from horus.run_executor import RunRequest
    req = RunRequest(
        session_id="s", agent="claude", project=Path("."), prompt="p", account=None,
        posture="full-auto", model=None, effort=None, worker=True, resume=None,
        dispatch_base_sha=None, dispatch_pending=0, batch="away7",
    )
    assert RunRequest.from_payload(req.payload()).batch == "away7"


def test_cmd_notify_batch_check_reports_incomplete_without_sending(monkeypatch, capsys):
    rep = batch.BatchReport(batch_id="B", members=[
        batch.BatchMember("a", "d", "c1", None, True),
        batch.BatchMember("b", "d", "c2", None, False),
    ])
    monkeypatch.setattr(cli.batch, "report", lambda bid: rep)
    monkeypatch.setattr(cli.batch, "emit_if_complete", lambda bid, root, deadline=False: None)
    rc = cli.cmd_notify_batch_check(argparse.Namespace(batch="B", deadline=False, path="."))
    assert rc == 0
    assert "1/2 legs finished" in capsys.readouterr().out
