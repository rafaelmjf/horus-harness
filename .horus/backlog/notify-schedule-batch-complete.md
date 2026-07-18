---
status: open
priority: medium
created: 2026-07-19
vision_facet: "Autonomous dispatch"
phase: converge
tier: sonnet
type: feature
parallel: safe
created_by: agent
surface: horus/notify.py (a batch-complete event) + horus/schedule.py (batch/group tagging + last-one-out detection)
---

# notify-schedule-batch-complete — a real "the schedule finished" signal, not a timer guess

**Why (owner-specified in the away-mode drill, 2026-07-19):** the owner wants, at
the END of an away-mode batch, exactly ONE Telegram message saying the schedule
completed, then to open Mission Control and read the outcomes. Today `horus notify`
fires only on failures (delivery-failed / usage-band / supervise-gate /
dispatch-launch-failed) plus an opt-in per-run `success` ping — there is NO
aggregate "all dispatches in this batch are done" signal. The 2026-07-19 light
drill had to fake it with a fixed-time `notify escalate` scheduled at +19m, which
says "the window elapsed", NOT "all legs actually finished" — misleading if a leg
runs long or dies.

## How

- Let a set of scheduled dispatches share a **batch/group id** (a tag written into
  the units at `schedule run`/`schedule dispatch` time). No new state store —
  reconstruct membership + completion from the existing systemd unit state the way
  `schedule status` already does (fired/active/failed), so it survives reboot.
- When the LAST member of a batch reaches a terminal state, emit ONE new
  `schedule-batch-complete` notify event (enabled by default) whose message
  summarizes per-leg outcome (✓/✗/blocked) and points at Mission Control. Fire it
  exactly once (idempotent — a re-run/among-races must not double-send).
- If a leg never terminates within a bound, the completion message says so
  (partial/timed-out), never a false "all green".

## Acceptance

- Arming a batch of N dispatches yields exactly one `schedule-batch-complete`
  message after the Nth finishes, summarizing each leg's real outcome.
- Idempotent: no duplicate completion message across retries/overlap.
- A hung/failed leg is reported as such in the summary, not silently dropped.
- `notify show` lists the new event; with no sink it is a silent no-op like every
  other event.

## Non-goals

- Not a live progress feed / heartbeat (that is `worker-progress-heartbeat`); this
  is a single terminal summary.
- Not a replacement for the andon escalations — failures still escalate
  immediately; this only adds the batch-done rollup.
