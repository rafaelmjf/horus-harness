---
status: open
priority: medium
created: 2026-07-17
tier: sonnet
type: feature
parallel: unsafe
phase: converge
vision_facet: "Autonomous dispatch"
branch: vision-branch-x3-scheduling-and-autonomous-execution
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
- **Capacity-pull trigger (kanban pull, novel per the 2026-07-17 scan):**
  `--when-capacity <account> [--threshold N%]` fires when the account's usage window
  resets / drops below the threshold (checked via `horus usage check` at coarse
  intervals or at reset timestamps — no continuous polling), so free capacity PULLS
  the next ready card instead of the owner pushing dispatches. Stretch goal for the
  away-mode kit; one-shot `--at` ships first.

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

- **Build-vs-adopt (scan 2026-07-17):** native scheduling now ships three ways
  (session cron tools w/ 7-day expiry, Claude Desktop scheduled tasks, cloud
  Routines) — none can route isolated accounts, produce `horus run`
  receipts/datums, or set the attachable+worktree posture, which is exactly the
  wrapper this card builds. Keep the cron/systemd backend thin; anything that is
  "just scheduling" will be subsumed natively.
- Depends conceptually on `unattended-dispatch-attachable-worktree-defaults` for its launch
  defaults. Shares `horus/cli.py` with the other branch cards (hence `parallel: unsafe`).

## Reviews

- 2026-07-17 — **Built (`horus schedule run|list|cancel`); all three open questions
  answered by measurement, not preference.** (1) *crontab vs systemd:* **systemd --user**,
  and specifically **on-disk unit files, not `systemd-run`**. Probed live: transient units
  live in `/run/user/<uid>/systemd/transient` — RAM — so a reboot silently erases every
  pending dispatch, which over a six-day trip is one kernel update away. On-disk +
  `enable` + `Persistent=true` survives reboot and catches up a slot missed while
  suspended. `at`/`atd` are not installed here. (2) *Where the registry lives:* **nowhere —
  systemd owns it.** The unit files under `~/.config/systemd/user` are the record, and
  `list` reads them plus systemd's live view; a parallel JSON registry would just drift
  from the timers that actually fire (cf. the repo's "never a second parser/state path"
  rule). (3) *Thin wrapper or daemon:* **wrapper**, per the scan — this module owns no
  scheduling logic, only unit writing/reading, and passes the whole `horus run` surface
  through untouched. `--cron` and `--when-capacity` remain unbuilt (one-shot ships first,
  as the card said).
- 2026-07-17 — **`loginctl` linger is the away-mode precondition nobody would have
  noticed.** Without it, user timers stop at logout — exactly the away condition. This
  machine has `Linger=yes` already; `schedule run` warns loudly when it is off, since a
  silently-never-firing schedule is the worst outcome of the whole kit.
- 2026-07-17 — **Three defects the live probe caught that 1800+ unit tests could not.**
  (a) `--at` must be a FLAG: as a positional, `argparse.REMAINDER` starts capturing at the
  next argument and swallowed this command's own `--describe` into the pass-through, so
  the scheduled dispatch fired into `horus run: error: unrecognized arguments`. The card's
  original `--at` spelling was right and the "improvement" to a positional broke it.
  (b) The alias guard from PR #297 refused `--agent fake --account personal`: the fake
  adapter has no config dir, login or rate-limit pool, so its `--account` is a free-text
  label — resolution now binds only agents that HAVE accounts. (c) Reading "has it fired?"
  is a minefield: a one-shot's `LastTriggerUSecRealtime` reads EMPTY once elapsed,
  `ActiveState` still reads `active` right after firing, and Persistent's stamp file
  EXISTS from the moment the timer is enabled. The honest signals are `NextElapse` (set ⇒
  pending) and the stamp's **mtime** advancing to the trigger time (⇒ fired), which is
  what survives a reboot.
- 2026-07-17 — **Not yet proven end-to-end:** a scheduled dispatch composed with
  `--unattended --envelope` (the actual away-mode path). The scheduler was probed with the
  fake adapter, and `--unattended` requires a worker-capable agent, so proving the
  composition costs a real worker launch — deliberately not spent without owner approval.
  Worth doing as the away-kit dogfood once `supervise-verify-merge-close` lands.
