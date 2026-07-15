---
status: open
priority: high
tier: sonnet
created: 2026-07-15
type: feature
parallel: unsafe
surface: horus/cli.py, horus/terminal_sessions.py, horus/tmux_runner.py, horus/runlog.py, horus/registry.py, horus/terminal_tui.py
---

# Attachable detached one-shot worker runs

Campaign supervision exposed a gap between two proven paths. `horus run --worker`
has headless one-shot completion, logs, and datum capture but remains foreground.
`horus open --target tmux --detach` survives the launcher and is attachable from the
TUI, but starts an interactive session whose task completion is not a one-shot signal.

Unify those properties so an owner can leave a worker alone, attach only when it is
stuck or needs clarification, detach again, and still receive a deterministic process
result without killing and relaunching the worker context.

Concrete failure that motivates this: launching `horus run --worker` from a bounded
foreground caller (a supervisor tool call with a timeout) meant the caller's SIGTERM on
timeout **propagated to and killed the worker** — the first campaign launch died at ~2
min with a `stale-but-delivered` registry artifact pointing only at the base SHA. A
launcher/caller ending must never kill a dispatched worker; detached execution (below)
is the fix, and until it ships the foreground path should at minimum document that it is
attached and caller-fatal.

## Acceptance

- `horus run --worker <agent> --target tmux --detach ...` (or an equivalent explicit
  surface) returns after a durable registry handoff while the existing headless
  one-shot adapter continues inside a Horus-managed tmux session.
- The worker appears as attachable in the existing TUI/session surfaces; attach and
  detach never interrupt the worker, and manual input can clarify a blocked live run.
- Natural worker exit records the same normalized status, return code, run log, launch
  and completion datum, and delivery facts as foreground `horus run`.
- Launcher exit, TUI exit, viewer disconnect, machine-local dashboard restarts, and a
  **foreground caller's SIGTERM/timeout** do not kill the worker. Reconciliation
  distinguishes running, exited, failed, and stale (progress/`stalled` is tracked
  separately in [[worker-progress-heartbeat]]).
- Account isolation, posture, model/effort, pinned dispatch base, pending-continuity
  warning, emergency worker hooks, and usage preflight behave identically to foreground
  `horus run`; detached execution does not create a second adapter path.
- Tests cover detach persistence, attachability, manual attach/detach, clean completion,
  failure, stale-process reconciliation, and parity of log/datum/receipt capture.

## Boundaries

- Reuse the managed tmux runner and one-shot adapter contracts; do not add a daemon or
  remote execution control plane.
- A viewer is optional. "Attachable" describes recovery/control, not mandatory active
  supervision.
- Do not auto-resume, auto-merge, or auto-launch another worker from a process exit.

