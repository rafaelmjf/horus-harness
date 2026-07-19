---
name: backlog-refine
description: >-
  Refine and disposition an existing backlog with the owner when cards need
  readiness review, concrete execution contracts, ordering, or an honest current
  picture. Use when the owner says "refine the backlog", "groom these cards",
  "what is actually ready", "order the backlog", or after `scope-cards` has
  produced shaping drafts. Manual and owner-gated; never runs autonomously and
  never silently rewrites cards.
---

<!-- horus-skill-version: 1 -->

# backlog-refine — picture first, decisions second, Ready last

This skill owns the **single execution-ready card contract**. It turns existing
cards — including `scope-cards` shaping drafts — into honest Ready, Shaping,
Gated, or Deferred state. The TUI may launch this flow later; the LLM judgment and
owner decisions remain here.

## Hard boundary

- Manual only. Never invoke from an autonomous worker or scheduler.
- Advisory first. Present every decision-bearing change and obtain the owner's
  verdict before writing it.
- Read card bodies, Reviews, PRD Vision/Shipped/Rules, and relevant receipts. A
  frontmatter lint is not refinement.
- Use LLM judgment first and deterministic checks second. A missing field may be
  by design; a clean schema does not make a weak card valuable.

## 1. Present the backlog picture before any questions

Start with the literal heading **“Here is our current picture”** and include:

1. the product direction in 2–3 lines;
2. every Vision facet and active `vision-branch-*` umbrella, each with a short
   goal/description;
3. item counts for each facet/branch split by readiness and priority;
4. the proposed work queues: Ready—Autonomous eligible, Ready—Attended,
   Shaping, Gated, Deferred, and Unclassified.

Do not ask card questions before this picture. Read the content of every open card,
including umbrellas and exploratory children, before classifying the portfolio.

## 2. Judge, then ask only what remains undecided

For each card, decide from the evidence whether it is still valuable, aligned,
phase-appropriate, self-sufficient for its job, and correctly dispositioned. Skip
clean cards and questions the evidence already answers. Batch only truly mechanical
fixes whose values are unambiguous.

For every pending owner decision, present one card at a time in this strict shape:

```text
Card <N>/<decision-card-count> — <slug>
Problem: <why the current card cannot be finalized>
Proposed direction: <LLM recommendation and evidence>
Current state: <readiness/priority/dependencies and relevant branch/facet>
Decision: <one sentence naming the choice>
```

Use the harness's native structured picker when available. Offer 2–3 mutually
exclusive choices; put the recommended choice first and mark it **(Recommended)**.
Every option description states its exact durable consequence: fields/body changed,
dependency or trigger recorded, queue entered, and what later unblocks it. Preserve
the picker's free-text Other option. When no structured picker exists, render the
same choices as `1`–`3` plus `4. Type anything`, then wait for the answer.

## 3. Readiness and autonomy contract

`status` remains lifecycle state. Readiness is orthogonal:

```yaml
readiness: ready | shaping | gated | deferred
readiness_reason: "required for shaping, gated, and deferred"
autonomy: eligible | attended  # required only when readiness: ready
```

- **Ready** — decision-complete now; a fresh agent can implement and independently
  verify it from PRD + card. `eligible` means it may be scheduled when an approved
  envelope authorizes it, never that it must be. `attended` means owner presence is
  required during execution or verification.
- **Shaping** — active owner/LLM work remains: brainstorm, research, scoping,
  refinement, review, or an exploratory evidence pass. The reason names that next
  action and expected disposition.
- **Gated** — a named dependency, event, or evidence source must arrive first. The
  reason names it; use `depends-on` as well when the gate is another card.
- **Deferred** — deliberately inactive until an explicit trigger or owner review.
- Missing `readiness` is **Unclassified** for compatibility. Never infer Ready and
  never schedule it; route it through this skill. Do not auto-rewrite a repository.

`phase: explore | converge` and `priority` remain orthogonal. Priority means
importance when active. A decision-complete exploration probe may be Ready; an
umbrella is never a scheduler execution unit.

## The execution-ready card contract (single authority)

A Ready card carries `status`, `priority`, `tier` (`low | medium | high |
frontier`), `vision_facet` or an explicit speculative `branch`, `phase`, `created`,
`created_by`, `surface`, `parallel: safe | exclusive`, `readiness: ready`, and
`autonomy`. It also carries:

- **Why** — durable context and market/own-use position;
- **How** — concrete protocol or first implementation steps;
- **Acceptance** — deterministic gate on the exact SHA plus a named live probe and
  expected result; an explore probe instead names the cheapest test and its explicit
  adopt/promote/drop verdict;
- **Non-goals** — bounded exclusions;
- **Source** — receipt, vision branch, owner decision, or observed gap;
- `depends-on` and sparse `order` when sequencing is decision-bearing.

Second-order findings are never fabricated. Scope the evidence-gathering probe and
state how later findings will be carded.

## 4. Apply approved state

Write only approved diffs. Record consequential owner demote/defer/retire/rescope
verdicts under `## Reviews`. Set `last_refined: YYYY-MM-DD` only after the card body
was actually reviewed, including an approved no-change verdict. Remove obsolete
fields rather than carrying rival readiness models.

When ordering is requested, respect `depends-on`, branch grouping, priority, and
`surface`/`parallel` collisions. Propose sparse integer `order` values with gaps of
10; explain whenever a constraint forced a position. Unordered cards stay in the
unsequenced pool. Ordering is owner-approved planning, never auto-routing.

End with the updated picture and the exact remaining pending decisions. Do not
dispatch, schedule, implement, or invoke pathfinder unless the product direction
itself became the unresolved question.

## v2 six-lane projects (fallback)

Read `project.md`, `roadmap.md`, `features.md`, `decisions.md`, and `history.md` in
their existing lanes. Present the same picture and interactive decisions, then
deepen approved roadmap entries inline. The readiness words remain an advisory
classification when the legacy roadmap has no frontmatter; do not migrate the
project or invent card files. Owner gating and the execution-ready content bar are
unchanged.
