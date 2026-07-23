---
status: open
priority: medium
readiness: shaping
readiness_reason: "Exploratory research; needs the comparison set + dimensions pinned before it produces a useful writeup. No code deliverable."
created: 2026-07-23
created_by: owner
last_refined: 2026-07-23
vision_facet: "Delegation calibration"
tier: medium
type: research
parallel: safe
surface: "comparative study — Horus dispatch/continuity/backlog workflow vs other existing agent-workflow systems; writeup, not code"
---

# dispatch-workflow-comparative-study — compare what we have vs other existing workflows

**Follow-up to [[codex-usage-stale-snapshot-gates-dispatch]].** That bug exposed
that a load-bearing part of our dispatch flow — provider capacity/usage gating — is
home-grown and fragile (a stale best-effort snapshot used as an authoritative gate).
That prompts the broader owner question: **is our overall agent-workflow well-shaped
against what else exists, or are we reinventing solved problems (and missing better
ideas)?**

## Motivation

Today's `tabi-triage-1` run (agentic-travel-guide) exercised the full loop end to
end: scope cards → multi-account dispatch (`horus run`, worktree isolation) →
`--expect-delivery` PRs → owner review → merge → continuity consolidation, with a
pre-merge freshness gate throughout. It worked, but the seams (usage gating, 3-way
continuity conflicts when workers each rewrite `PRD.md`, per-PR gate dancing) are
worth checking against prior art rather than only iterating in isolation.

## Research questions

- **Capacity / rate-limit awareness:** how do other agent-orchestration systems
  detect and gate on provider limits (Anthropic/OpenAI usage, token budgets) before
  dispatching? Live API vs snapshot vs none? (Directly informs the sibling bug.)
- **Dispatch & isolation:** how do others fan work across accounts/models and isolate
  concurrent workers (worktrees, containers, clones, sandboxes)?
- **Continuity / memory:** how do comparable systems persist project state across
  sessions, and how do they avoid the "every worker rewrites the shared state file"
  conflict we hit today?
- **Merge/verification discipline:** pre-merge gates, autonomous-vs-attended merge,
  who owns canonical state (supervisor vs worker).
- **Work-item model:** backlog cards + readiness/facet vs issues/kanban/task queues.

## Candidate comparison set (refine when claimed)

Native Claude Code / Codex orchestration (subagents, background tasks, workflows);
generic multi-agent frameworks and task-queue runners; CI-driven agent patterns;
and continuity/memory approaches in other agent stacks. Owner to confirm which are
worth a deep look before the sweep.

## Deliverable

A written comparison (matrix over the dimensions above + short prose) with:
- where Horus is ahead, at parity, or behind;
- concrete adopt/steal candidates (especially for capacity gating and shared-state
  conflict avoidance);
- explicit "leave as-is" calls where our approach is deliberately different.

## Boundaries

- Research/writeup only — no implementation in this card; findings spawn their own
  scoped cards.
- Time-box the sweep; breadth over exhaustiveness. Cite sources.
- Keep provider-specific limits factual (verify against current docs, don't guess).
