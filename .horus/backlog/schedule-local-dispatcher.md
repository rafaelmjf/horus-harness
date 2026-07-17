---
status: open
priority: medium
created: 2026-07-17
tier: sonnet
type: feature
parallel: unsafe
phase: explore
created_by: owner
surface: new `horus schedule` subcommand; horus/cli.py (parser + handler); new horus/schedule.py; wraps horus run (horus/run_executor.py); crontab or systemd-timer backed
---

# schedule-local-dispatcher — a first-class local one-shot/cron dispatcher for `horus run`

**Why (owner, 2026-07-17):** the owner wants to schedule a card's worker to launch later
on *this machine* (never cloud). Today there is no scheduler: `horus run` is immediate, so
scheduling means a hand-rolled crontab wrapper (used in the 2026-07-17 dogfood that shipped
`PR #287`). That wrapper hard-codes account/model/worktree/log paths, must self-remove its
own cron line for a one-shot, and needs a clean env — fragile and unshareable. Part of the
`vision-branch-x3-scheduling-and-autonomous-execution` divergence.

## Idea

A `horus schedule` verb that registers a future `horus run` on this machine:

- `horus schedule --at <RFC3339|"5:30 tomorrow"> [run-args...]` — one-shot (default; a card
  is done once, so **non-recurring is the default**).
- `horus schedule --cron "<expr>" [run-args...]` — recurring, opt-in.
- `horus schedule list` / `horus schedule cancel <id>` — inspect/cancel.
- Backed by the OS scheduler (crontab or a systemd `--user` timer with `Persistent=true`
  so a slot missed while suspended still fires). One-shots self-clean after firing.
- Passes through the full `horus run` surface (`--account`, `--model`, `--effort`,
  `--worker`, `--worktree`, `--expect-delivery`, `--path`). Local time in, converts to the
  scheduler's expected TZ.
- Writes a per-schedule log path and records the schedule in a machine-local registry
  (never in git / never in `fleet.toml`).

## Acceptance

- `horus schedule --at ...` launches the equivalent `horus run` at the target time on this
  machine, one-shot, self-cleaning; `horus schedule list` shows it beforehand and it is gone
  after firing.
- The launched worker is attachable + worktree-isolated by default (see
  `unattended-dispatch-attachable-worktree-defaults`).
- No cloud dependency; nothing machine-specific leaks into git.

## Open questions

- crontab vs systemd `--user` timer as the default backend (suspend-survival argues systemd).
- Where the schedule registry lives under `~/.horus/` and how `horus sessions`/dashboard
  surface a *pending* (not-yet-launched) schedule.
- Does this stay a thin wrapper, or grow a small daemon? (Keep it wrapper-thin; a daemon
  edges toward the out-of-scope orchestration plane — see the branch card.)

## Notes

- Depends conceptually on `unattended-dispatch-attachable-worktree-defaults` for its launch
  defaults. Shares `horus/cli.py` with the other branch cards (hence `parallel: unsafe`).
