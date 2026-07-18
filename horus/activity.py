"""Unified read-out of autonomous-dispatch activity: what is ARMED and what RAN.

The data is scattered across three readers *by design* — this module joins them,
it invents no new state:

- ``schedule.load_all()`` — armed/halted one-shot timers (the future).
- ``envelope.read_ledger()`` — what was DISPATCHED under each standing envelope
  (``{ts, card, account, session_id}``), but NOT the outcome.
- ``datums`` — the run OUTCOME, keyed by ``session_id`` (delivery_status / exit /
  agent outcome).

Joining on ``session_id`` lets the TUI Control pane, the phone (`notify listen`'s
`schedule` verb), and the dashboard render ONE view without any of them growing a
second parser (the TUI-thin rule). Read-only; an unknown outcome renders as unknown
(``?``), never a false ``✓``.
"""

from __future__ import annotations

from dataclasses import dataclass

from horus import envelope, schedule
from horus.datums import DatumStore, Datum

# Outcome glyphs — one column, stable meaning.
ARMED = "⧗"      # armed/running: will run, or dispatched and not yet resolved
OK = "✓"         # delivered / clean
FAIL = "✗"       # a failure signal was observed
NOOP = "•"       # ran, nothing to deliver
UNKNOWN = "?"    # completed but no outcome signal — never guessed as ✓


@dataclass(frozen=True)
class RanItem:
    ts: str
    card: str
    account: str
    session_id: str
    glyph: str
    status: str


@dataclass(frozen=True)
class Activity:
    armed: list[schedule.Schedule]
    ran: list[RanItem]


def outcome_glyph(datum: Datum | None) -> tuple[str, str]:
    """Map a run's datum to a ``(glyph, human status)``.

    Precedence is deliberately failure-before-success and unknown-safe: a completed
    run with no readable delivery/outcome signal is ``?``, never ``✓``.
    """
    if datum is None:
        return ARMED, "dispatched (pending)"
    if not datum.completed_at:
        return ARMED, "running"

    delivery = (datum.delivery_status or "unknown").lower()
    exit_ = (datum.exit or "").lower()
    outcome = (datum.outcome or "").lower()

    if delivery in {"failed", "blocked"}:
        return FAIL, f"delivery {delivery}"
    if exit_ in {"crashed", "usage-death"}:
        return FAIL, exit_
    if outcome in {"died", "void", "bounced"}:
        return FAIL, outcome
    if delivery == "delivery-ready" or outcome in {"clean", "nudged"}:
        return OK, outcome or "delivered"
    if delivery == "no-op":
        return NOOP, "no-op"
    return UNKNOWN, "completed (outcome unknown)"


def _armed() -> list[schedule.Schedule]:
    """Armed + halted scheduled dispatches, or empty where systemd is unavailable
    (the recent band still works cross-platform)."""
    if not schedule.availability().ok:
        return []
    try:
        return schedule.load_all()
    except schedule.ScheduleError:
        return []


def collect(*, limit: int = 10, store: DatumStore | None = None) -> Activity:
    """The armed dispatches and the last ``limit`` dispatched cards with outcomes.

    ``store`` is a test seam; production reads the default datum store. Recent rows
    come from the envelope ledgers (the record of what was dispatched) joined to
    their datum outcome — newest first.
    """
    store = store or DatumStore.default()
    rows: list[dict] = []
    for env in envelope.load_all():
        rows.extend(envelope.read_ledger(env.name))
    rows.sort(key=lambda r: r.get("ts", ""), reverse=True)

    ran: list[RanItem] = []
    for row in rows[:limit]:
        session_id = row.get("session_id", "")
        glyph, status = outcome_glyph(store.get(session_id) if session_id else None)
        ran.append(RanItem(
            ts=row.get("ts", ""),
            card=row.get("card", ""),
            account=row.get("account", ""),
            session_id=session_id,
            glyph=glyph,
            status=status,
        ))
    return Activity(armed=_armed(), ran=ran)
