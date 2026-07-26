---
status: open
priority: low
created: 2026-07-20
created_by: agent
last_refined: 2026-07-26
readiness: ready
autonomy: eligible
tier: small
parallel: safe
phase: converge
type: bug
vision_facet: "Continuity core"
surface: "the `backlog` subparser in horus/cli.py (default action when no subcommand is given) + its help text, tests/test_cli.py"
---

# backlog-default-list — `horus backlog` should default to `list`

## Why

Hit live during the 2026-07-20 calibration session: `horus backlog` with no
subcommand prints `error: pass a backlog subcommand (list|migrate|claim|ship|
review) or --tree` instead of doing the obvious thing. Every sibling read
surface (`horus sessions`, `horus status`) answers bare. Small, deterministic,
code-only — shaped deliberately as an early Ready—Autonomous eligible
candidate for the dispatch loop.

## Intended outcome

`horus backlog` bare = `horus backlog list`; help text updated; no behavior
change for explicit subcommands.

## Broad boundaries

One argparse default + tests. Non-goals: no changes to list's output format;
no new subcommands.

## Acceptance

- Bare `horus backlog` prints exactly what `horus backlog list` prints, exit 0.
- Explicit subcommands (`list`, `migrate`, `claim`, `ship`, `review`) and `--tree`
  are unchanged; the help text states the default.
- Gate: full suite green on the exact SHA. Probe: run bare `horus backlog` in this
  repo and confirm it lists rather than erroring.

## Source

Agent-found paper cut, 2026-07-20 session;
`.horus/research/2026-07-20-roadmap-branches-rebaseline.md` branch C item 1.

## Reviews

- 2026-07-26 — Refined with the owner. Confirmed `list` (not `--tree`) as the bare
  default: it matches how `horus sessions` and `horus status` answer bare, and the
  tree stays an explicit opt-in. Minted **Ready / autonomy: eligible**, tier small,
  `parallel: safe`. No surface collision with anything else in the queue.
