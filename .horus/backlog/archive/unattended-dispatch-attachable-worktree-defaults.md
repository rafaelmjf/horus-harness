---
status: shipped
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
shipped_pr: 294
shipped_sha: a13dc22
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

## Reviews

- 2026-07-17 — **Built; all three open questions answered, two by item 0's shape.**
  (1) *Preset flag vs implication:* `--unattended` (already introduced by
  `standing-dispatch-envelope`) implies the bundle — tmux + detach + `--worker <agent>`
  + `auto/<card>` worktree. Explicit flags win; attended `horus run` untouched.
  (2) *Auto-worktree naming:* the free-text case does not exist — `--unattended` requires
  `--envelope`, which requires `--card`, so a card slug is always present. Branch is
  `auto/<card>` (worktree `<repo>-wt-auto-<card>`): the `auto/` prefix means `git branch`
  says at a glance what was machine-dispatched during a trip, and it cannot collide with
  a branch the owner cut for the same card. (3) *Config-dir guard with two unattended runs
  on one account:* **no change needed** — the existing guard already refuses the second
  live process on a config dir, which is the correct invariant. Live-probed: dispatching
  to the account this session runs under prints the documented own-dir share note and
  proceeds. New refusal: `--unattended` needs a worker-capable agent (claude/codex), since
  unattended dispatch IS worker dispatch.
- 2026-07-17 — **Dogfooding this card found three defects in `standing-dispatch-envelope`
  (shipped ~1h earlier, PR #293), all invisible to its 38 unit tests.** (a) `envelope
  create --account claude-personal` was accepted though the real aliases are
  `personal`/`work` — a typo'd alias created an envelope that silently never matched, so
  an owner could leave for six days with nothing ever dispatching. Unknown aliases now
  refuse at create. (b) Unknown capacity refused even at `usage_floor=0`, i.e. when no
  guarantee was asked for; since the live OAuth usage read returns **no signal** on this
  machine, an away envelope would have refused *every* dispatch. Fail-closed now binds
  only the bound actually set. (c) `envelope create` printed "unknown capacity refuses"
  even at floor 0. Lesson worth carrying: the envelope's failure mode is silent
  over-refusal, and only a real dispatch surfaces it.
- 2026-07-17 — **Runtime gate reproduced (owner-approved probe envelope, 1 attempt).**
  Real claude/sonnet-5 worker on `personal`, 0m09s, outcome void (probe, not a task — kept
  out of the quality denominator). Observed: `auto/<card>` branch accepted by git, sibling
  worktree created, worker reported its own branch+cwd from inside it, registry row
  `launch_target=tmux target_ref=horus-864d7ec4-018 is_attachable=True`, main checkout
  untouched, and a second dispatch refused by `attempts-per-card 1/1`. Probe envelope,
  worktree, and branch removed after. Not driven live: `horus attach` itself — the run
  finished in 9s; attachability rests on the registry contract (`launch_target`+`target_ref`),
  which is the pre-existing consumer that TUI-launched sessions already use.
