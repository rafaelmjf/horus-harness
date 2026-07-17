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
surface: horus/cli.py (run parser + cmd_run gate logic ~:1073-1087); horus/terminal_sessions.py (is_attachable :55-57, launch_detached_run :231-278); horus/worktree.py
---

# unattended-dispatch-attachable-worktree-defaults — make scheduled/detached runs attachable + isolated by default

**Why (owner, 2026-07-17):** the owner expects a dispatched worker to be **attachable**,
like TUI-launched sessions (tmux underneath), so they can inspect or manually intervene.
But `horus run` defaults to `--target current` (`horus/cli.py` run parser), which runs in
the caller's process and is **not** attachable — `is_attachable` is true only when
`launch_target == "tmux"` with a `target_ref` (`horus/terminal_sessions.py:55-57`). The
2026-07-17 dogfood hit exactly this: the cron-launched worker registered in `horus sessions`
and did real work, but was never `horus attach`-able because the wrapper used the default
foreground target. Separately, an unattended worker in a shared checkout can collide with a
concurrent session (branch switch under its feet), so `--worktree` should be default too.
Part of the `vision-branch-x3-scheduling-and-autonomous-execution` divergence.

## Idea

Give unattended dispatch a safe default posture without changing attended `horus run`:

- A `horus run --unattended` preset (or have `horus schedule`/`--detach` imply it) that sets
  `--target tmux --detach --worker <agent> --worktree <auto-branch>` together, so every
  scheduled/detached run is **attachable** (`horus attach horus-<id>`) and **worktree-isolated**.
- Auto-derive a worktree branch slug from the card/task when `--worktree` is not given, using
  the existing `horus/worktree.py` path convention (`<repo>-wt-<slug>`).
- Keep the current explicit-flag behaviour intact; this only adds a convenience + safe default
  for the unattended path. Attended `horus run` (foreground) is unchanged.

## Acceptance

- A scheduled/`--unattended` dispatch is attachable via `horus attach <prefix>` and runs in a
  sibling worktree, leaving the main checkout (and any concurrent session there) untouched.
- Running `horus run` with no unattended flags behaves exactly as today.

## Open questions

- Preset flag name (`--unattended`) vs making `horus schedule`/`--detach` imply the bundle.
- Auto-worktree branch naming when derived from a card slug vs a free-text task.
- Interaction with the config-dir conflict guard (`horus/cli.py:894-937`) when two unattended
  runs target the same account.

## Notes

- This is the direct fix for the gap the dogfood exposed. Complements `schedule-local-dispatcher`
  (which would set these defaults for scheduled runs). Shares `horus/cli.py` → `parallel: unsafe`.
