---
status: shipped
priority: high
created: 2026-07-18
vision_facet: "Autonomous dispatch"
phase: converge
tier: sonnet
type: bug
parallel: safe
created_by: owner
branch: vision-branch-x3-scheduling-and-autonomous-execution
surface: horus/schedule.py (systemd unit generation), horus/notify.py (a launch-failure event), horus/cli.py (notify hook entrypoint)
shipped_pr: 315
shipped_sha: 712544207b636c46df0ab6506f256f4117cca286
---

# scheduled-dispatch-launch-failure-escalates — don't die silently in the journal

**Why (owner, 2026-07-18, surfaced by the X3 e2e rehearsal):** a scheduled
`horus run --unattended` that fails **before it launches a worker** currently dies
only in `journalctl` — nothing reaches the owner. Observed twice during the rehearsal:
(1) a malformed pass-through command → argparse `error: unrecognized arguments` exited
2 in the service journal; (2) the old config-dir guard refused with exit 2 (since
relaxed). In the away case (trip 2026-07-22) this means a day's dispatch can quietly
no-op where nobody is looking — the exact failure mode the andon/notify channel exists
to prevent, but it only covers *post-delivery* supervise gates, not *pre-launch* death.

## Concrete design

The scheduled `systemd --user` service should escalate on ANY non-zero launch exit,
uniformly (argparse errors exit before the Python handler runs, so an in-handler
`try/except` cannot catch them — the escalation must live at the unit level):

- `horus schedule` writes an `OnFailure=horus-sched-<id>-notify.service` (or an
  `ExecStopPost=` guarded on `$EXIT_STATUS`) into the generated unit. The failure unit
  runs `horus notify escalate --event dispatch-launch-failed --card <card> --detail
  "<journal tail / exit code>"` (a new machine-local escalation entrypoint).
- Add a `notify` event `DISPATCH_LAUNCH_FAILED` (defaults ON, like the other actionable
  events). `notify.escalate` stays best-effort and never raises (existing rule).
- The escalation names the card, the exit code, and `journalctl --user -u <unit>` to
  inspect — enough for the owner to act from their phone.

## Acceptance

- A scheduled dispatch whose `horus run` exits non-zero before launch fires a Telegram
  (or configured sink) escalation naming the card + exit code; verified by scheduling a
  deliberately-malformed dispatch and watching it escalate instead of dying silently.
- No sink configured ⇒ behaves exactly as today (no escalation, no failure).
- A successful launch never escalates.

## Non-goals

- Not a retry/backoff mechanism — escalate, don't auto-retry (the owner decides).
- Does not change the post-delivery supervise/andon path (already covered).
