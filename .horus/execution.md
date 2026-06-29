---
status: idle
current_feature: ""
supervisor_tier: frontier
worker_tier: standard
continuity_tier: economy
last_updated: 2026-06-29
---

# Execution Plan

Fluid, optional plan for the currently active roadmap item. Replace this when
the next substantial feature starts; distill finished work into `roadmap.md`,
`features.md`, `decisions.md`, and `history.md` rather than preserving this as a
timeline.

Current state: no active execution plan. The `horus-execution` pilot completed on
2026-06-29 (shipped incremental GitHub catalog refresh via one delegated worker phase;
findings distilled into decisions.md "Execution-Workflow Pilot"). The next roadmap NEXT
(fold the pilot's tuning findings into the skill + this template) is `continue-as-is`,
so it does not need a phased plan here. Replace this file when the next substantial
phased feature starts.

## Model Policy

Use tiers instead of hard-coded model names. Resolve them locally per agent,
account, and current model availability.

| tier | Intended use | Examples |
|---|---|---|
| economy | mechanical continuity updates, formatting, small docs from explicit notes | maintainer |
| standard | narrow implementation phases with tests | worker |
| frontier | planning, architecture, risky review, final acceptance | supervisor |

## Active Phases

| phase | status | difficulty | worker_tier | handoff_note | review |
|---|---|---|---|---|---|

## Worker Handoff Contract

Implementation workers should write a brief note in `.horus/temp/` when a phase
finishes. Keep it factual and reviewable:

- changed files / behavior;
- tests run and result;
- risks or follow-ups;
- suggested durable `.horus/` updates.

The supervisor reviews the diff and the handoff, then updates the durable lanes.

Useful commands:

- `horus execution prompt --target codex` prints a supervisor prompt shaped for
  Codex subagents/custom agents.
- `horus execution prompt --target claude` prints the Claude Code equivalent.
- `horus execution handoff 1A` creates `.horus/temp/1A.md` for a worker note.
