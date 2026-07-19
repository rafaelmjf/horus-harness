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

from dataclasses import dataclass, field

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
    # Deterministic delivery detail from the datum, so a fired dispatch reports what
    # the worker DID (branch/PR/CI), not just that the timer ran. None where the
    # adapter/run never recorded it — never guessed.
    pr_number: int | None = None
    ci: str | None = None
    branch: str | None = None


@dataclass(frozen=True)
class Activity:
    armed: list[schedule.Schedule]
    ran: list[RanItem]
    # schedule.id -> outcome of the run a FIRED dispatch launched (by card, from
    # durable receipts). Absent for a schedule with no card or no recorded run.
    outcomes: dict[str, RanItem] = field(default_factory=dict)


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


def outcome_summary(item: RanItem) -> str:
    """A one-line delivery outcome for a fired dispatch: the status plus, when the run
    produced them, the PR + its CI (else the branch). Reused by `schedule status`,
    `schedule list`, and the TUI so all three read identically (the TUI-thin rule)."""
    parts = [item.status]
    if item.pr_number:
        parts.append(f"PR #{item.pr_number}")
        if item.ci:
            parts.append(f"CI {item.ci}")
    elif item.branch:
        parts.append(f"branch {item.branch}")
    return " · ".join(parts)


def _ledger_rows() -> list[dict]:
    """Every envelope-ledger dispatch row, newest first."""
    rows: list[dict] = []
    for env in envelope.load_all():
        rows.extend(envelope.read_ledger(env.name))
    rows.sort(key=lambda r: r.get("ts", ""), reverse=True)
    return rows


def _ran_item(row: dict, store: DatumStore) -> RanItem:
    session_id = row.get("session_id", "")
    datum = store.get(session_id) if session_id else None
    glyph, status = outcome_glyph(datum)
    return RanItem(
        ts=row.get("ts", ""),
        card=row.get("card", ""),
        account=row.get("account", ""),
        session_id=session_id,
        glyph=glyph,
        status=status,
        pr_number=datum.delivery_pr_number if datum else None,
        ci=datum.ci if datum else None,
        branch=datum.delivery_branch if datum else None,
    )


def _schedule_card(sched: schedule.Schedule) -> str | None:
    """The ``--card`` slug in a scheduled dispatch's command, or None (a supervise or
    warmup schedule carries no card, and so no delivery outcome to link)."""
    cmd = list(sched.command)
    if "--card" in cmd:
        i = cmd.index("--card")
        if i + 1 < len(cmd):
            return cmd[i + 1]
    return None


def fired_outcomes(
    schedules: list[schedule.Schedule], *, store: DatumStore | None = None
) -> dict[str, RanItem]:
    """Link each FIRED scheduled dispatch to the outcome of the run it launched, keyed
    by ``schedule.id``.

    The join is card → the newest envelope-ledger dispatch of that card → its datum,
    all durable on-disk receipts (never a worker self-report). A schedule with no card,
    or a card with no recorded dispatch, is absent from the map rather than guessed —
    the caller renders those as plain ``fired`` with no outcome line.
    """
    store = store or DatumStore.default()
    latest_by_card: dict[str, RanItem] = {}
    for row in _ledger_rows():  # newest-first: first seen per card is the latest
        card = row.get("card", "")
        if card and card not in latest_by_card:
            latest_by_card[card] = _ran_item(row, store)
    out: dict[str, RanItem] = {}
    for sched in schedules:
        if not sched.fired:
            continue
        card = _schedule_card(sched)
        if card and card in latest_by_card:
            out[sched.id] = latest_by_card[card]
    return out


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
    their datum outcome — newest first. Each FIRED armed dispatch is additionally
    linked to its own run outcome (``outcomes``), so a timer that ran reports what the
    worker delivered, not just that it fired.
    """
    store = store or DatumStore.default()
    ran = [_ran_item(r, store) for r in _ledger_rows()[:limit]]
    armed = _armed()
    return Activity(armed=armed, ran=ran, outcomes=fired_outcomes(armed, store=store))
