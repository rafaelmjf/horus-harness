---
status: open
priority: low
created: 2026-07-20
created_by: agent
last_refined: 2026-07-20
readiness: shaping
readiness_reason: "Trivial fix; needs only the refinement pass to confirm scope (default action + help text) and mint autonomy."
phase: converge
type: bug
vision_facet: "Continuity core"
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

## Open decisions for backlog-refine

- Confirm `list` (not `--tree`) is the wanted default.
- Autonomy mint: eligible under which envelope bounds.

## Source

Agent-found paper cut, 2026-07-20 session;
`.horus/research/2026-07-20-roadmap-branches-rebaseline.md` branch C item 1.
