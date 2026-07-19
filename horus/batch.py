"""One aggregate "the schedule batch finished" signal for away-mode.

The owner arms a set of dispatches, closes the session, and wants exactly ONE push
when the whole batch is done — then opens Mission Control to read the outcomes.
`horus notify` fires only on failures plus an opt-in per-run success ping; there is
no aggregate "all legs are done" signal. The 2026-07-19 light drill faked it with a
fixed-time ping that said "the window elapsed", not "all legs actually finished".

This module adds the real signal, daemon-free and reusing state that already exists:

- **Membership** is the set of scheduled dispatches tagged with the same ``--batch``
  id (the tag rides in each unit's ExecStart, reconstructed from systemd like
  `schedule status` does — no new state store, survives reboot).
- **Per-leg outcome + completion** comes from :func:`activity.fired_outcomes` (the
  envelope-ledger → datum join), so a DETACHED worker — whose systemd unit exits at
  launch, long before the worker finishes — is "done" only when its run's datum is
  terminal, never merely because the timer fired.
- **Trigger** is the last worker's own completion (it knows its ``--batch`` id), so the
  signal fires exactly when the Nth leg finishes — plus a deadline backstop command
  for a leg that never terminates.
- **Idempotent** via an atomic sentinel file, so races/retries/the deadline overlap
  never double-send.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from horus import activity, config, notify, schedule
from horus.datums import DatumStore


@dataclass(frozen=True)
class BatchMember:
    schedule_id: str
    description: str
    card: str | None
    outcome: activity.RanItem | None   # the resolved run outcome, or None if unresolved
    done: bool                          # the worker reached a terminal datum


@dataclass(frozen=True)
class BatchReport:
    batch_id: str
    members: list[BatchMember]

    @property
    def all_done(self) -> bool:
        return bool(self.members) and all(m.done for m in self.members)

    @property
    def finished_count(self) -> int:
        return sum(1 for m in self.members if m.done)


def batch_of(sched: schedule.Schedule) -> str | None:
    """The ``--batch`` id tagged into a scheduled dispatch's command, or None."""
    cmd = list(sched.command)
    if "--batch" in cmd:
        i = cmd.index("--batch")
        if i + 1 < len(cmd):
            return cmd[i + 1]
    return None


def report(batch_id: str, *, store: DatumStore | None = None) -> BatchReport:
    """Reconstruct a batch's membership + per-leg completion from durable state.

    A member is *done* only when its worker's run reached a terminal datum outcome
    (delivered / blocked / no-op / …) — never merely because its timer fired, since a
    detached worker runs on well after its unit exits."""
    members_scheds = [s for s in activity._armed() if batch_of(s) == batch_id]
    outcomes = activity.fired_outcomes(members_scheds, store=store)
    members: list[BatchMember] = []
    for s in members_scheds:
        oc = outcomes.get(s.id)
        # `⧗` (ARMED) means dispatched-but-pending/running; a real terminal outcome is
        # any other glyph. Absent from `outcomes` ⇒ not fired / no run yet ⇒ not done.
        done = oc is not None and oc.glyph != activity.ARMED
        members.append(BatchMember(
            schedule_id=s.id, description=s.description,
            card=activity._schedule_card(s), outcome=oc, done=done,
        ))
    return BatchReport(batch_id=batch_id, members=members)


def _sentinel_path(batch_id: str) -> Path:
    return config.config_dir() / "batch-complete" / f"{batch_id}.done"


def _claim_once(batch_id: str) -> bool:
    """Atomically claim the right to emit this batch's completion. Returns True to the
    single caller that created the sentinel, False to every other (races/retries/the
    deadline backstop overlapping the last-one-out)."""
    path = _sentinel_path(batch_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return False
    os.close(fd)
    return True


def _escalation(batch_id: str, root: Path, rep: BatchReport, *, deadline: bool) -> notify.Escalation:
    legs: list[str] = []
    for m in rep.members:
        label = m.card or m.schedule_id
        if m.done and m.outcome is not None:
            legs.append(f"{m.outcome.glyph} {label}: {activity.outcome_summary(m.outcome)}")
        else:
            legs.append(f"{activity.UNKNOWN} {label}: did not finish (timed out)")
    if deadline and not rep.all_done:
        head = (f"schedule batch {batch_id} INCOMPLETE at deadline — "
                f"{rep.finished_count}/{len(rep.members)} finished")
    else:
        head = f"schedule batch {batch_id} finished — {len(rep.members)} dispatch(es)"
    return notify.Escalation(
        event=notify.SCHEDULE_BATCH_COMPLETE,
        project=root.name,
        summary=head + "\n" + "\n".join(legs),
        inspect="horus schedule status  (open Mission Control for the outcomes)",
        actions=(("Schedule", "schedule"), ("Sessions", "sessions")),
    )


def emit_if_complete(
    batch_id: str, root: Path, *, deadline: bool = False, store: DatumStore | None = None
) -> notify.EscalationResult | None:
    """Emit the single ``schedule-batch-complete`` signal, once, when the batch is done.

    Returns the escalation result if this call emitted, else None. Without ``deadline``
    it fires only once every member is terminal (the last worker's completion triggers
    it); with ``deadline`` it is the backstop — it fires even with unfinished legs,
    reporting them as timed-out rather than a false all-green. The atomic sentinel makes
    it exactly-once no matter how many workers/backstops call it."""
    rep = report(batch_id, store=store)
    if not rep.members:
        return None
    if not rep.all_done and not deadline:
        return None
    if not _claim_once(batch_id):
        return None
    return notify.escalate(_escalation(batch_id, root, rep, deadline=deadline))
