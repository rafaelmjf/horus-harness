---
status: open
priority: medium
created: 2026-07-24
created_by: owner
readiness: shaping
readiness_reason: "The owner deliberately parked the attended experiment until fully available; the target campaign, explicit authority boundaries, and adoption evidence must be chosen without predesigning the agent's implementation."
phase: explore
type: feature
vision_facet: "Autonomous dispatch"
---

# intent-preserving-goal-campaign — bind the spirit, let a frontier agent choose the form

## Why

Horus currently asks cards and refinement to specify much of the work's
**form** before an agent acts: decomposition, proposed mechanisms, execution
contracts, readiness checks, and verification plans. That discipline was useful
for bounded workers, but frontier models are increasingly capable of holding a
long-running goal, discovering the right implementation while working, and
recovering from failed approaches. Pre-solving the form may now duplicate their
judgment, anchor them to stale guesses, and turn the backlog into a toll booth.

The owner primarily cares that the **spirit** of pending work is cleared:

- the real problem and why it matters;
- the outcome that should become true;
- observable evidence that it is true;
- explicit constraints where the owner has strong knowledge or opinions.

The owner generally does **not** want an early implementation idea to bind the
agent merely because it was written into a card. The experiment asks whether a
frontier goal can preserve intent more faithfully by choosing, revising,
combining, or discarding implementation forms while it works.

## The distinction to test

### Spirit — binding

- Problem, motivation, and intended outcome.
- Observable definition of done.
- Explicit owner decisions, exclusions, and safety/compatibility constraints.
- Authority and timing dispositions such as Gated, Deferred, or Attended until
  the owner changes them.

### Form — advisory by default

- Proposed solution and architecture.
- Task decomposition and ordering.
- Commands, filenames, surfaces, and implementation steps.
- Candidate tests or probes when they prescribe a mechanism rather than the
  observable result.

For legacy cards, test this interpretation order:

1. explicit owner decision or constraint;
2. observable outcome;
3. problem statement;
4. proposed approach and implementation detail.

A lower rung cannot override a higher one. If a materially different form
satisfies the higher rungs, it may satisfy the card without implementing its
original proposal.

## Primary experiment

When the owner is fully available, run one attended frontier-model `/goal`
campaign over a coherent real slice — the Autonomous dispatch facet is the
leading candidate, with a bounded bug cluster as an alternative.

The goal should:

- Read existing cards as an intent map and evidence, not a mandatory checklist.
- Choose its own working sequence and revise it just in time.
- Combine cards when one solution satisfies several spirits.
- Replace or discard proposed forms when evidence supports a better route.
- Implement safe, reversible work rather than stopping for a speculative
  pre-execution design review.
- Ask the owner only when work changes product direction, crosses an explicit
  constraint, or needs irreversible/external authority.
- Keep each delivered increment green, pushed, and reviewable under the repo's
  existing branch/PR and exact-SHA verification rules.
- Reconcile affected cards afterward as satisfied, subsumed, still valuable,
  or blocked by one genuine decision.

A candidate goal:

```text
Materially advance the selected facet toward its Definition of Done. Read the
existing cards as evidence of intended outcomes, not mandatory implementation
plans. Preserve explicit owner constraints and current authority/timing
boundaries, but choose, combine, replace, or discard proposed forms as the
investigation warrants. Implement safe, reversible work autonomously and verify
every delivered increment. Ask only when a decision would change product
direction, cross an explicit owner constraint, or require irreversible/external
authority. Keep green work in pushed, reviewable checkpoints. At completion,
reconcile every affected card by whether its spirit was satisfied, remains
valuable, or was superseded.
```

## Alternatives deliberately not required up front

### Pre-execution implementation cards

The model could first write an owner-reviewable execution slate. This may be a
useful trust-calibration fallback, but making it mandatory is itself another
conservative preflight: it asks the model to freeze and prove its form before
pursuing the outcome. Test it only if the direct campaign fails because the
owner cannot evaluate or steer the work with sufficient confidence.

If used, candidate cards remain a provisional map. Approval confirms that the
intent, constraints, decomposition, and verification are credible; it does not
freeze the proposed implementation. A step deserves a durable card only when it
is independently valuable, independently verifiable, useful for parallel
dispatch, or must survive beyond the current run.

### Bulk rewrite of existing cards

Do not migrate the backlog before the experiment. Touch a card only when the
campaign uses or reconciles it. If the pattern proves valuable, later card
templates and refinement guidance may explicitly separate intent, locked
constraints, suggested form, and evidence.

### Another autonomous-refinement subsystem

Do not build a readiness harvester, new orchestration layer, or card factory
before testing whether Goal mode plus existing durable cards already supplies
the needed autonomy.

## Evidence and verdict

Judge the experiment by outcomes rather than plan prediction:

- meaningful facet or bug progress delivered;
- spirits satisfied without implementing obsolete forms;
- unnecessary owner interruptions;
- rework or false starts caused by insufficient constraints;
- deterministic gates that caught a real mistake;
- whether one solution honestly subsumed multiple cards;
- whether the final backlog became more truthful and easier to resume;
- whether any missing pre-execution ceremony would actually have prevented a
  failure.

Converge on the intent-preserving contract if the campaign delivers useful,
verified work with fewer artificial gates and an honest final reconciliation.
Revise it if the model needs a lighter preview or clearer locked constraints.
Drop it if form freedom repeatedly loses card intent, hides product decisions,
or creates more rework than the removed process costs.

## Open decisions

- Which real campaign is the first probe: Autonomous dispatch or a bounded bug
  cluster?
- Which external or irreversible actions remain owner-gated for that run?
- May the attended goal merge approved PRs, or stop at independently verified
  reviewable checkpoints?
- What amount of owner steering still counts as materially more autonomous?
- If the experiment succeeds, which existing card/refinement/dispatch
  instructions need the smallest durable change?

## Non-goals

- No unattended first run; the owner explicitly wants to be fully available.
- No claim that all implementation detail is optional: explicit owner
  constraints and externally observable contracts remain binding.
- No automatic override of Gated, Deferred, or Attended dispositions.
- No requirement to implement every card in a facet.
- No new session mode, scheduler, orchestration plane, or card lifecycle.

## Source

Owner discussion, 2026-07-24: frontier models may be constrained by a process
calibrated for weaker or isolated workers; backlog work has a binding “spirit”
and a revisable “form”; Goal mode should be tested as the agent-owned adaptive
loop, with Horus retaining authority boundaries, durable checkpoints, and
deterministic evidence.
