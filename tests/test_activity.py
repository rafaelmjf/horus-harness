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
