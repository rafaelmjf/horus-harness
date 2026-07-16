---
status: shipped
priority: medium
tier: sonnet
created: 2026-07-16
type: feature
parallel: safe
surface: .agents/skills/process-retrospective, Claude/Codex skill projections, tests/test_skills.py
shipped_pr: 270
shipped_sha: 5cd7b4216183d166a3e20df4d3b8eafb4aeb3c57
---

# Evidence-first process retrospective skill

The owner repeatedly asks what should improve after a failure, near-miss, unexpectedly
long run, surprising usage movement, or supervision that felt inefficient. Generic
self-reflection is too vague and risks inventing ceremony; the reusable need is a
bounded retrospective grounded in the campaign's actual artifacts.

## Acceptance

- A shared `process-retrospective` skill triggers only on an explicit owner request or
  a concrete incident/cost anomaly, never automatically at every closure.
- It lazy-loads only relevant evidence: the active/completed execution plan, exact
  PR/CI state, datum/receipt, targeted log fragments, and owner observations.
- It separates inherent task cost, delegation tax, supervisor error, worker error,
  Horus/skill defect, and external failure; unknown/confounded evidence stays labelled.
- Before proposing work it checks existing Rules/cards and asks for the cheapest
  prevention rung: no-change, guidance clarification, deterministic signal, or hard
  guard. It reports recurring overhead and caps recommendations at three.
- It never estimates token consumption, launches another model, broadly rereads the
  repository, writes continuity/backlog, or changes process without owner approval.
- Accepted outcomes use existing PRD Rules/card Reviews/backlog entries; the skill
  creates no retrospective document or telemetry stream.
- Claude and Codex projections remain identical to the canonical source; focused skill
  tests and the skill validator pass.

## Boundaries

- This is event-driven execution/process analysis. `product-audit` remains periodic,
  Horus-product-focused, and prune-only; `horus-consolidate` remains continuity closure.
- Default inline and single-agent. Any research sweep, worker, or independent model
  evaluation needs a separately justified and approved envelope.
- Review after roughly three real uses; retire or demote it if it merely restates
  generic reasoning or adds more overhead than it removes.
