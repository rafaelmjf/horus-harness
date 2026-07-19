"""The autonomous-dispatch activity join (`horus schedule status`).

Pure join + glyph logic over stubbed readers; the live join over real ledgers +
datums is exercised by the PR's runtime probe.
"""

from __future__ import annotations

import argparse

from horus import activity, cli, envelope, schedule
from horus.datums import Datum


class _Store:
    """A minimal datum store keyed by session id."""
    def __init__(self, by_session: dict[str, Datum]):
        self._by = by_session

    def get(self, session_id: str) -> Datum | None:
        return self._by.get(session_id)


def _datum(session_id: str, **over) -> Datum:
    base = dict(session_id=session_id, completed_at="2026-07-18T00:00:00Z")
    base.update(over)
    return Datum(**base)


# --- glyph precedence: failure before success, unknown never a false tick ------

def test_glyph_pending_when_no_datum():
    glyph, label = activity.outcome_glyph(None)
    assert glyph == activity.ARMED and "pending" in label


def test_glyph_running_when_not_completed():
    glyph, _ = activity.outcome_glyph(_datum("s", completed_at=None))
    assert glyph == activity.ARMED


def test_glyph_delivered_and_clean_are_ticks():
    assert activity.outcome_glyph(_datum("s", delivery_status="delivery-ready"))[0] == activity.OK
    assert activity.outcome_glyph(_datum("s", outcome="clean"))[0] == activity.OK


def test_glyph_failure_signals_are_crosses():
    for kw in (
        {"delivery_status": "failed"},
        {"delivery_status": "blocked"},
        {"exit": "crashed"},
        {"exit": "usage-death"},
        {"outcome": "died"},
        {"outcome": "void"},
        {"outcome": "bounced"},
    ):
        assert activity.outcome_glyph(_datum("s", **kw))[0] == activity.FAIL, kw


def test_glyph_failure_wins_over_a_delivered_status():
    # A run that delivered but whose agent outcome is 'bounced' reads as a failure,
    # not a false tick.
    glyph, _ = activity.outcome_glyph(_datum("s", delivery_status="delivery-ready", outcome="bounced"))
    assert glyph == activity.FAIL


def test_glyph_noop_and_unknown():
    assert activity.outcome_glyph(_datum("s", delivery_status="no-op"))[0] == activity.NOOP
    # Completed with no readable delivery/outcome signal → unknown, never ✓.
    glyph, label = activity.outcome_glyph(_datum("s", delivery_status="unknown"))
    assert glyph == activity.UNKNOWN and "unknown" in label


# --- collect(): join ledger rows to datum outcomes, newest first ---------------

def test_collect_joins_and_orders_newest_first(monkeypatch):
    monkeypatch.setattr(activity.schedule, "availability", lambda: schedule.Availability(False, "not linux"))
    monkeypatch.setattr(activity.envelope, "load_all", lambda: [type("E", (), {"name": "trip"})()])
    monkeypatch.setattr(activity.envelope, "read_ledger", lambda name: [
        {"ts": "2026-07-18T00:01:00+00:00", "card": "older", "account": "claude-work", "session_id": "a"},
        {"ts": "2026-07-18T00:05:00+00:00", "card": "newer", "account": "claude-work", "session_id": "b"},
    ])
    store = _Store({
        "a": _datum("a", delivery_status="delivery-ready"),
        "b": _datum("b", delivery_status="failed"),
    })
    act = activity.collect(limit=10, store=store)
    assert act.armed == []  # systemd unavailable → armed band empty, recent still works
    assert [r.card for r in act.ran] == ["newer", "older"]  # newest first
    assert act.ran[0].glyph == activity.FAIL and act.ran[1].glyph == activity.OK


def test_collect_respects_limit(monkeypatch):
    monkeypatch.setattr(activity.schedule, "availability", lambda: schedule.Availability(False, "x"))
    monkeypatch.setattr(activity.envelope, "load_all", lambda: [type("E", (), {"name": "e"})()])
    monkeypatch.setattr(activity.envelope, "read_ledger", lambda name: [
        {"ts": f"2026-07-18T00:0{i}:00+00:00", "card": f"c{i}", "account": "x", "session_id": str(i)}
        for i in range(5)
    ])
    act = activity.collect(limit=2, store=_Store({}))
    assert len(act.ran) == 2 and act.ran[0].glyph == activity.ARMED  # no datum → pending


def test_cli_schedule_status_json(monkeypatch, capsys):
    monkeypatch.setattr(activity, "collect", lambda limit=10: activity.Activity(
        armed=[],
        ran=[activity.RanItem("2026-07-18T00:05:00+00:00", "newer", "claude-work", "b", activity.OK, "delivered")],
    ))
    assert cli.cmd_schedule_status(argparse.Namespace(limit=10, stdout=True)) == 0
    out = capsys.readouterr().out
    assert '"card": "newer"' in out and '"glyph"' in out


# --- a FIRED dispatch reports its OUTCOME, not just "fired" --------------------

def _sched(id_: str, *, card: str | None, fired: bool) -> schedule.Schedule:
    command = ("python", "-m", "horus", "run", "p", "--card", card) if card else ("python", "-m", "horus", "warmup")
    return schedule.Schedule(id=id_, description="d", when="2026-07-19 01:29:00", command=command, fired=fired)


def _link(monkeypatch, *, schedules, ledger, store):
    monkeypatch.setattr(activity.schedule, "availability", lambda: schedule.Availability(True, "ok"))
    monkeypatch.setattr(activity.schedule, "load_all", lambda: schedules)
    monkeypatch.setattr(activity.envelope, "load_all", lambda: [type("E", (), {"name": "away"})()])
    monkeypatch.setattr(activity.envelope, "read_ledger", lambda name: ledger)


def test_fired_outcomes_links_a_fired_dispatch_to_its_delivery(monkeypatch):
    """A fired schedule for card X links to the newest recorded dispatch of X, with the
    branch/PR/CI from its datum — durable receipts, never a self-report."""
    schedules = [_sched("aaa", card="my-card", fired=True)]
    ledger = [{"ts": "2026-07-19T01:30:00+00:00", "card": "my-card", "account": "claude-work", "session_id": "s1"}]
    store = _Store({"s1": _datum(
        "s1", delivery_status="delivery-ready", delivery_branch="away/my-card",
        delivery_pr_number=342, ci="pass",
    )})
    _link(monkeypatch, schedules=schedules, ledger=ledger, store=store)
    out = activity.fired_outcomes(schedules, store=store)
    assert "aaa" in out
    assert out["aaa"].glyph == activity.OK
    summary = activity.outcome_summary(out["aaa"])
    assert "PR #342" in summary and "CI pass" in summary


def test_fired_outcomes_skips_pending_and_cardless_schedules(monkeypatch):
    """A pending (not-yet-fired) timer and a cardless one (warmup/supervise) carry no
    delivery outcome to link — they stay absent, not a guessed ✓."""
    schedules = [
        _sched("pend", card="my-card", fired=False),   # not fired yet
        _sched("warm", card=None, fired=True),          # cardless
    ]
    ledger = [{"ts": "2026-07-19T01:30:00+00:00", "card": "my-card", "account": "x", "session_id": "s1"}]
    store = _Store({"s1": _datum("s1", delivery_status="delivery-ready")})
    _link(monkeypatch, schedules=schedules, ledger=ledger, store=store)
    assert activity.fired_outcomes(schedules, store=store) == {}


def test_outcome_summary_falls_back_to_branch_then_status():
    delivered = activity.RanItem("t", "c", "a", "s", activity.OK, "delivered", branch="away/c")
    assert activity.outcome_summary(delivered) == "delivered · branch away/c"
    blocked = activity.RanItem("t", "c", "a", "s", activity.FAIL, "delivery blocked")
    assert activity.outcome_summary(blocked) == "delivery blocked"


def test_collect_attaches_outcomes_to_fired_armed(monkeypatch):
    """collect() links each fired armed dispatch to its outcome so one read serves the
    CLI, TUI, and phone."""
    schedules = [_sched("aaa", card="my-card", fired=True)]
    ledger = [{"ts": "2026-07-19T01:30:00+00:00", "card": "my-card", "account": "claude-work", "session_id": "s1"}]
    store = _Store({"s1": _datum("s1", delivery_status="blocked")})
    _link(monkeypatch, schedules=schedules, ledger=ledger, store=store)
    act = activity.collect(limit=10, store=store)
    assert act.outcomes["aaa"].glyph == activity.FAIL
    assert "delivery blocked" in activity.outcome_summary(act.outcomes["aaa"])


def test_cli_schedule_status_renders_outcome_under_a_fired_entry(monkeypatch, capsys):
    fired = _sched("aaa", card="my-card", fired=True)
    outcome = activity.RanItem("t", "my-card", "claude-work", "s1", activity.OK, "delivered",
                               pr_number=342, ci="pass", branch="away/my-card")
    monkeypatch.setattr(activity, "collect", lambda limit=10: activity.Activity(
        armed=[fired], ran=[], outcomes={"aaa": outcome},
    ))
    assert cli.cmd_schedule_status(argparse.Namespace(limit=10, stdout=False)) == 0
    out = capsys.readouterr().out
    assert "fired" in out
    assert "PR #342" in out and "CI pass" in out  # the outcome, not just "fired"


def test_cli_schedule_list_shows_outcome_for_fired_entries(monkeypatch, capsys):
    """The phone `schedule` verb runs `schedule list` — it too shows the outcome, not
    just `fired`, for an away-mode owner reading it on their phone."""
    fired = _sched("aaa", card="my-card", fired=True)
    outcome = activity.RanItem("t", "my-card", "claude-work", "s1", activity.FAIL, "delivery blocked")
    monkeypatch.setattr(cli.schedule, "availability", lambda: schedule.Availability(True, "ok"))
    monkeypatch.setattr(cli.schedule, "load_all", lambda: [fired])
    monkeypatch.setattr(cli.activity, "fired_outcomes", lambda schedules: {"aaa": outcome})
    assert cli.cmd_schedule_list(argparse.Namespace(stdout=False)) == 0
    out = capsys.readouterr().out
    assert "fired" in out and "delivery blocked" in out
