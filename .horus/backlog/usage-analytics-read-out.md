---
status: open
priority: medium
created: 2026-07-20
created_by: owner
last_refined: 2026-07-20
readiness: shaping
readiness_reason: "The steering questions the analytics must answer, the snapshot-history retention, and the render surface (CLI vs TUI vs dashboard) are undecided."
phase: converge
type: feature
vision_facet: "Accounts & isolation"
---

# usage-analytics-read-out — from point-in-time percentages to steering answers

## Why

Usage today is honest but momentary: the pushed statusline reading per
account, with source and age. Steering decisions need shallow history: which
account has slack before arming a batch, when do windows reset relative to
scheduled dispatches, what did the last away-batch actually consume. The
readings are already being recorded (`horus usage record` cache, datums);
nothing renders them over time. Owner named this family directly ("better
analytics on usage").

## Intended outcome

Before arming an envelope or scheduling a batch, one read-out answers the
slack/reset/consumption questions from recorded history — no new polling, no
estimation, honoring the existing rule that usage comes from the surface the
app pushes.

## Broad boundaries

Read-only over already-captured readings; extend capture retention only if
refinement decides history is too thin. Non-goals: NO new polling of any
endpoint; no per-task cost estimation (explicitly forbidden by the delegation
rules); no auto-routing decisions derived from the analytics — it informs the
owner/agent, never selects.

## Open decisions for backlog-refine

- The 3-5 concrete steering questions v1 must answer.
- Whether current snapshot retention suffices or capture needs a history file.
- Render surface: `horus usage` flag, TUI pane, dashboard panel — or all three
  from one shared read-out (the read-out-shared-by-all-surfaces pattern).

## Source

`.horus/research/2026-07-20-roadmap-branches-rebaseline.md`, owner verdict
section (candidate families).
