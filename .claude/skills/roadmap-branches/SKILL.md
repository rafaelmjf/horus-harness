---
name: roadmap-branches
description: >-
  Build the DIVERGENCE TREE for a project: from a pinned position brief (inward)
  and a market-scan receipt (outward), propose MULTIPLE alternative roadmaps —
  one branch per direction over existing + new items, each with a market-position
  line, a numbered ordered roadmap, and a convergence criterion — plus 1-2
  speculative branches for directions the Vision does not hold yet. Step 3 of the
  pathfinder flow, also owner-invocable standalone ("what directions could we
  take", "show me alternative roadmaps", "build the branch tree"). Re-justifies
  the EXISTING backlog against the pinned intent with explicit push-back — it
  never inherits cards uncritically. Advisory: emits a dated receipt under
  `.horus/research/`; the owner picks branches; it never edits the Vision, never
  creates cards, never reorders the backlog.
---

<!-- horus-skill-version: 9 -->

# roadmap-branches — the divergence tree, not a merged roadmap

You are producing the **divergent** half of the breathing loop: a tree of
alternative roadmaps the owner chooses between. The single most important rule:
**never collapse the tree into one merged roadmap** — merging is the owner's
convergence decision, and pre-merging it destroys exactly the choice this skill
exists to surface.

**The worked example of a good run is
`.horus/research/2026-07-17-roadmap-branches-convergence-test.md`** (this repo).
Read it before writing. It is the shape to reproduce: a flowing position read-out,
four real branches over eight facets, and push-back that names cards.

## Where BRANCHES come from — never the backlog

A branch is a DIRECTION, and directions do not come from the card list. Build them
from:

1. **Facet definition-of-done vs delivered code** — what the facet promises against
   what exists. Never stale, needs no external evidence, richest source.
2. **The owner's real friction** — what is slow, manual, or repeated by hand in
   recent actual use. A direction here often has ZERO cards; that means it was
   invisible to the backlog, not that it is unimportant.
3. **The audit and market receipts** — especially adopt/compose verdicts and
   anything the evidence contradicts.
4. **The Vision's out-of-scope list** — hypotheses, re-testable against fresh usage.

The backlog is read for exactly one purpose: to disposition it against the branches
once they exist (section 6). **A branch whose roadmap is mostly existing cards is a
grooming pass wearing a branch's clothes**; if every branch reads that way, say so
and route the owner to `backlog-refine` instead of shipping the tree.

## Inputs (gather, do not re-derive)

- **The pinned intent** — deepen-own-use | broaden-adoption | both. If it was not
  handed to you (standalone invocation), ASK the owner; never assume.
- **The position brief** — SHIPPED / VISION+audience / OPEN facet coverage. If
  missing, build it now: read `## Vision` (or note the facet table's ABSENCE),
  the active backlog cards with their `vision_facet`/`phase` stamps, `## Shipped`,
  and run `horus consolidate` for the deterministic convergence read-out.
- **The market-scan receipt** (`.horus/research/`) — the outward evidence. If none
  exists, say the tree is inward-only and offer to run `market-scan` first; do not
  quietly substitute your own untested market beliefs.
- **Prior branch-tree receipts** — a re-baseline consumes its predecessors: carry
  forward unresolved branches, unscoped imports, and owner verdicts recorded there,
  re-justified against the CURRENT intent. Never blindly inherited, never silently
  dropped, and never re-derived as if fresh.

## The deliverable — one dated receipt, fixed template

Write `.horus/research/<YYYY-MM-DD>-roadmap-branches-<slug>.md` with exactly these
sections, then STOP for the owner to pick:

1. **Where we are.** **Narrative prose, walking every facet**, each with a
   life-stage judgment — converged (DoD met) / built-but-unproven / active frontier
   / steady-state — and an honest one-line overall position at the end. **Not
   bullets, not a table; a fresh reader must understand the project's situation
   without the conversation.** This section is where full facet coverage lives, and
   it is why the tree itself does not need a branch per facet. Cite a fresh
   product-audit for the underlying evidence rather than re-deriving its numbers,
   but write the position in your own prose — a citation is not a read-out.
2. **Where the market is.** Distilled FROM the receipt (cite it): the landscape in
   shells, then ONE verdict, then the risks. **State each fact exactly once** — if
   a point appears in two sections, delete one.
3. **The tree.** A small ASCII tree: root = the position in two lines, one child per
   branch (speculative ones last), each naming its facet target — or `no facet yet`
   — plus a one-word posture tag (primary/secondary/filler/park is the
   *recommendation*, not a decision).
   **Produce a branch only where there is a real direction.** Branches carry a facet
   target; facets do not generate branches. Fewer branches than facets is normal and
   correct: a converged or steady-state facet needs no branch (say so in section 1),
   and two facets sharing one direction share one branch. Four branches over eight
   facets is a good tree; eight branches padded to cover the table is not.
4. **The branches.** For EACH branch:
   - **Thesis** — why this direction, argued through the pinned intent. **Open it in
     plain terms**: what actually goes wrong today as the owner experiences it, and
     what is different afterwards, before any module, protocol or command appears.
     A reader who has never opened the codebase must be able to say what hurts and
     what would change. Mechanism belongs in the roadmap items below, not here.
   - **Market position** — the required line: "*this exists already but misses X;
     you already have Y but still miss Z; therefore these items*". Market evidence
     appears INSIDE every branch, not only in section 2.
   - **Numbered roadmap** — ordered items mixing existing cards and new proposals,
     each naming whether it is an existing card (with its readiness) or new. Every
     item carries enough depth that `scope-cards` can populate a card without new
     thinking: why, the concrete how (a protocol, a first step), suspected weak
     points, and non-goals. A second-order item (work that depends on findings that
     do not exist yet) is named as such: "findings become their own cards".
   - **Convergence criterion** — when is this branch done, plus a rough cost.
   - **Implied Vision edits** — the facet DIFF this branch entails:
     add / rename / retire / promote-proven-exploration against a NAMED existing
     facet, with draft definition-of-done text for adds/rescopes. Never a
     wholesale table rewrite. **Advancing a facet includes shrinking it** — a branch
     may propose rescoping, retiring an unused feature, or reducing scope to what is
     proven; name these as defer/retire candidates routed to the convergence pass,
     which decides them. This skill never does.
5. **Speculative branches / wildcards (1-2, more when the owner asks).**
   Directions with NO current facet, derived from position + market + intent:
   the gap it names, the idea, the cheapest PoC, why it fits the intent, the
   risk — and, as prominently as the promise, the EXPLICIT converge/drop criterion
   ("converges if …; dropped if …", where dying cheap is a valid success). The tree
   is incomplete without at least one, and **at least one candidate must RE-TEST the
   Vision's out-of-scope list** — an out-of-scope line is a hypothesis too. When a
   candidate's drop criterion is a single cheap read-only check, RUN IT and report
   the answer rather than proposing it.
6. **Recommendation, held loosely.** Primary / secondary / filler / park across the
   branches, one paragraph of reasoning, then the existing-card push-backs
   summarized — each named card with its disposition and reason. The owner reorders
   freely.

Format rules: no-context-reader prose; consolidated tables only for genuinely
enumerable material (the backlog disposition); in an interactive session paste the
receipt content into the terminal; end with the owner pick gate PLUS a
dive-deeper-into-one-named-topic-or-proceed offer. Owner metaphors are examples to
test against, never canon to echo. **Length is not a proxy for depth** — the worked
example is ~330 lines and says more than twice that would.

## Three disciplines that make the tree trustworthy

- **Disposition the backlog AFTER the branches exist, never before.** Every open
  card either earns its place inside an already-formed branch or gets explicit
  push-back (demote / defer / retire candidate, argued through the intent). Doing
  this first is how this skill produces grooming instead of directions.
- **Claims discipline.** Every "X is missing / weak / better" names its
  comparison baseline: what exists today, and why it is insufficient for the
  intent. No claim without its baseline. Verify a card still exists and a number is
  still true before repeating it from a prior receipt.
- **Every candidate exits with a disposition.** Anything considered — market-receipt
  candidates, prior-tree branches, existing cards — either lands in a branch or is
  dropped WITH the stated reason. Silent omission is the failure mode.

## Onboarding fork

If the position brief found NO `## Vision` facet table, section 1 describes the
state without facets, and each branch's "implied Vision edits" instead proposes the
*initial* facet set and offers to stamp existing cards with a `vision_facet` — that
offer IS the assisted onboarding, no separate migration.

## Hand off

The owner picks one or more branches (or amends the tree). The chosen branch —
its numbered roadmap, item depth, and implied Vision edits — is the input
`scope-cards` consumes. Owner verdicts at this gate that rescope, demote, or
re-prioritize an EXISTING card must be recorded in that card's `## Reviews` when
the decision lands (`scope-cards` writes them) — a verdict that lives only in a
receipt or the conversation does not bind future planning runs. You never edit
the Vision, never create cards, never reorder the backlog yourself.

## Deliberately omit

- No auto-pick and no single merged roadmap — divergence is the deliverable.
- No new web research — consume the market-scan receipt; if it is missing or
  stale, say so and offer the scan instead of improvising evidence.
- No execution planning (that is `execution-decision` / `horus-execution`).

