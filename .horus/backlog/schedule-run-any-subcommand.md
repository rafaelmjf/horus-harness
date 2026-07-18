---
status: open
priority: high
created: 2026-07-18
vision_facet: "Autonomous dispatch"
phase: converge
tier: sonnet
type: bug
parallel: safe
created_by: agent
surface: horus/cli.py (cmd_schedule_at command assembly + schedule-run parser help)
---

# schedule-run-any-subcommand — the scheduler can't arm a `supervise` (or `warmup`)

**Why (blocking defect found dogfooding the first autonomous-scheduler test,
2026-07-18):** the autonomous loop launches a worker now (`horus run --unattended
--detach`) and then schedules an INDEPENDENT supervisor to fire later
(`horus schedule run … -- supervise <id>`) to reproduce the gate + merge/close or
escalate. But `cmd_schedule_at` (horus/cli.py:1288) hardcodes the subcommand:

    command = (sys.executable, "-m", "horus", "run", *run_args)

So `horus schedule run --at +10m -- supervise <id>` builds `horus run supervise
<id>` — a WORKER with prompt "supervise" and a stray positional argparse rejects
(exit 2 → the OnFailure unit fires a launch-failed escalation). The scheduled
supervisor — the whole andon half of the loop — cannot be armed at all. The same
bug breaks the documented `horus schedule run … -- warmup` (cli.py help ~5023).

The PRD `next_action`, the Rule "A scheduled supervise needs its session id at
schedule time", and `tui-toggle-card-into-scheduler` all assume this works. Unit
tests missed it (they only parse an already-`run`-shaped command). Classic
"dogfooding found the previous item's defect, invisible to unit tests."

## How

- In `cmd_schedule_at`, if the first token after `--` names a real horus
  top-level subcommand, schedule `horus <run_args>` verbatim; else keep the
  backward-compatible `horus run <run_args>` (the prompt form). Derive the valid
  subcommand set from the LIVE parser (`sub.choices`) — stash it on the
  schedule-run subparser via `set_defaults(_horus_commands=…)` — so it never
  drifts as commands are added.
- Label: for a subcommand form use the joined non-flag tokens (e.g.
  "supervise 16fba944"); the prompt form keeps `_describe_run`.
- Update the schedule group description + the `run_args` help + the empty-args
  hint to say "any horus subcommand", not only `horus run`.

## Acceptance

- `horus schedule run --at +10m -- supervise <id>` writes a unit whose ExecStart
  is `… -m horus supervise <id>` (NOT `… run supervise …`).
- `horus schedule run --at +2h -- "<prompt>" --unattended --card c --envelope e`
  still builds `… -m horus run "<prompt>" …` and `schedule list` still shows the
  card (backward-compatible).
- `-- warmup` schedules `horus warmup`.
- New tests cover subcommand-passthrough vs prompt-prepend; existing
  schedule/supervise tests still pass; full suite green in CI.

## Non-goals

- Not changing what `horus supervise`/`horus run` themselves do.
- Not an allow-list of "which subcommands may be scheduled" — any real subcommand
  passes through; nonsense fails loudly at fire time exactly as a bad `run` would.
