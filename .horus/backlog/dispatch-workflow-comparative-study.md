---
status: open
priority: medium
readiness: shaping
readiness_reason: "Focus sharpened (owner, 2026-07-23): the capability + use case are settled; the live question is how to make continuity PROPORTIONAL so it isn't expensive ceremony under concurrent dispatch. Starting-point findings recorded below; still needs the external comparison sweep."
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

## Sharpened focus (owner, 2026-07-23)

The dispatch **capability and use case are settled** (see Findings): structured
dispatch earns its place through separate-account token pools, independent reviewable
PRs, and durable cross-session state — none of which native subagents or loose
goal-mode provide. **The live research question is narrower: how do we adapt
*continuity* so it stays proportional to durable value instead of becoming expensive
ceremony under concurrent dispatch?** Everything else in this card is supporting
context for that question.

## Motivation

Today's `tabi-triage-1` run (agentic-travel-guide) exercised the full loop end to
end: scope cards → multi-account dispatch (`horus run`, worktree isolation) →
`--expect-delivery` PRs → owner review → merge → continuity consolidation, with a
pre-merge freshness gate throughout. It worked, but the seams (usage gating, 3-way
continuity conflicts when workers each rewrite `PRD.md`, per-PR gate dancing) are
worth checking against prior art rather than only iterating in isolation.

## Findings (starting point — lived from the `tabi-triage-1` run, 2026-07-23)

Grounded in actually running the structured dispatch (3 cards → 3 accounts → 3 PRs →
review → merge → deploy), not theory.

### Settled: capability + use case (not the open question)

- **Placement on a ceremony-vs-leverage spectrum.** Native subagents (Claude
  `Agent`/Codex): concurrent but **one account/token pool**, ephemeral, results
  return to the supervisor — cheap, fast, in-session. Loose goal-mode: lowest
  ceremony, no parallelism/isolation, single agent. Structured dispatch: separate
  **account token pools** (ran codex-personal + claude-personal + claude-work at
  once — impossible on one account), **independent reviewable PRs**, **durable
  provenance/state across sessions**.
- **They compose, they don't compete.** Structured layer = backbone across accounts
  and time; subagent layer = fan-out within a session (e.g. reviewing the 3 PRs
  could itself have been 3 review subagents). Use structured dispatch specifically
  when work needs real parallel capacity, unattended runs, or a durable audit trail.
- **For a small batch, the lighter tool often wins.** These 3 cards were
  self-contained; native subagents-in-worktrees would arguably have sufficed. The
  full machinery justified itself here through token-pool multiplication and
  durability — *not* because the tasks needed the scaffolding. Ceremony that doesn't
  buy leverage is pure tax.

### The crux: continuity cost scaled with concurrency, not with durable value

The expensive part of the run was continuity, and the cost driver is specific:

- **Every worker independently rewrote the shared `PRD.md` frontmatter + Shipped
  ledger** → **3-way merge conflicts** on the single source-of-truth file; the
  supervisor hand-reconciled all three.
- **The pre-merge gate fired per-PR**, forcing per-branch continuity freshening and a
  per-PR reconciliation pass ("gate dancing").
- Net: the **narrative-continuity tax was paid N times** (once per worker) plus a
  reconciliation pass — for a batch that warranted **one** narrative update.

**The clue is in what *didn't* conflict:** the per-card files (one file per unit)
merged cleanly; only the shared narrative prose (`PRD.md`) conflicted. So continuity
cost is proportional to **how much shared mutable narrative each worker touches** —
and native subagents pay ~zero continuity cost precisely because they persist
nothing. The design target is to capture nearly all of continuity's durable value
(auditability, cross-session legibility, provenance) at close to the subagent's
*marginal* cost — i.e., cost should track durable value, not worker count.

### Design directions to test (hypotheses, not decisions)

1. **Workers emit append-only, per-unit delivery receipts** (stamp their own card /
   a `## Delivery` block / a `.horus/temp/` file) and **never edit shared narrative**
   (PRD frontmatter/Shipped). Conflict-free by construction — each writes its own
   file/section. (This is what the supervisor ended up doing by hand; formalize it.)
2. **Narrative synthesis is one supervisor pass at the *batch* boundary**, not
   per-PR. The gate should recognize a `--batch` dispatch and require narrative
   freshness **once at batch close**, not per leg.
3. **Dashboard/frontmatter fields become supervisor-authored only**; the merge gate
   accepts worker branches carrying "delivery facts only" and defers narrative.
4. **Lean on the existing continuity-granularity knob** (`handoff`/`delivery`/
   `manual`): dispatched workers should run at a *delivery-receipt* granularity with
   narrative batched at handoff. The knobs may already exist — the gap is that
   workers currently author narrative at all.

### Non-negotiable

- Don't "fix" this by dropping continuity: its durability/auditability is the exact
  thing that separates structured dispatch from ephemeral subagents — the value, not
  the tax. The goal is **proportionality**, not removal.

## Research questions

- **Capacity / rate-limit awareness:** how do other agent-orchestration systems
  detect and gate on provider limits (Anthropic/OpenAI usage, token budgets) before
  dispatching? Live API vs snapshot vs none? (Directly informs the sibling bug.)
- **Dispatch & isolation:** how do others fan work across accounts/models and isolate
  concurrent workers (worktrees, containers, clones, sandboxes)?
- **Continuity / memory (the crux):** how do comparable systems persist project state
  across sessions *without* the "every worker rewrites the shared state file" conflict
  we hit today? Look specifically at append-only/event-sourced logs, per-branch or
  per-task receipts, CRDT-style mergeable state, and supervisor-only-synthesis
  patterns — which of these keep continuity cost proportional to durable value rather
  than to worker count?
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
