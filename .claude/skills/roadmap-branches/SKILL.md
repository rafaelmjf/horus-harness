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

<!-- horus-skill-version: 3 -->

# roadmap-branches — the divergence tree, not a merged roadmap

You are producing the **divergent** half of the breathing loop: a tree of
alternative roadmaps the owner chooses between. The single most important rule:
**never collapse the tree into one merged roadmap** — merging is the owner's
convergence decision, and pre-merging it destroys exactly the choice this skill
exists to surface.

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
- **Prior branch-tree receipts** (earlier trees under `.horus/research/`) — a
  re-baseline consumes its predecessors: carry forward unresolved branches,
  unscoped imports, and owner verdicts recorded there, re-justified against the
  CURRENT intent — never blindly inherited, never silently dropped. (Calibration
  2026-07-17: an owner rescope lived only in a prior receipt and a fresh run
  missed it entirely.)

## The deliverable — one dated receipt, fixed template

Write `.horus/research/<YYYY-MM-DD>-roadmap-branches-<slug>.md` with exactly these
sections, then STOP for the owner to pick:

1. **Where we are.** Narrative prose, per facet, each with a life-stage judgment —
   converged (DoD met) / built-but-unproven / active frontier / steady-state — and
   an honest one-line overall position at the end. Not bullets; a fresh reader must
   understand the project's situation without the conversation.
2. **Where the market is.** Distilled FROM the receipt (cite it): the landscape in
   shells, then ONE verdict, then the risks. **State each fact exactly once** — if
   a point appears in two sections, delete one.
3. **The tree.** A small ASCII tree: root = the position in two lines, one child
   per branch (including the speculative ones), each with its facet target and a
   one-word posture tag (primary/secondary/filler/park is the *recommendation*,
   not a decision).
4. **The branches.** For EACH branch:
   - **Thesis** — why this direction, argued through the pinned intent.
   - **Market position** — the required line: "*this exists already but misses X;
     you already have Y but still miss Z; therefore these items*". Market evidence
     appears INSIDE every branch, not only in section 2.
   - **Numbered roadmap** — ordered items mixing existing cards and new proposals.
     Every item carries enough depth that `scope-cards` can populate a card without
     new thinking: why, the concrete how (a protocol, a first step), suspected weak
     points, and non-goals. A second-order item (work that depends on findings that
     do not exist yet) is named as such: "findings become their own cards".
   - **Convergence criterion** — when is this branch done, plus a rough cost.
   - **Implied Vision edits** — the facet DIFF this branch entails:
     add / rename / retire / promote-proven-exploration against a NAMED existing
     facet, with draft definition-of-done text for adds/rescopes. Never a
     wholesale table rewrite.
5. **Speculative branches (1-2).** Directions with NO current facet, derived from
   position + market + intent: the gap it names, the idea, the cheapest PoC, why it
   fits the intent, the risk. These are the "imaginary visions" — the tree is
   incomplete without at least one. At least one candidate must RE-TEST the
   Vision's out-of-scope list against fresh usage evidence — an out-of-scope line
   is a hypothesis too. (Calibration: both 2026-07-17 runs missed the owner's
   strongest live direction, scheduled autonomous dispatch, because it sat behind
   an out-of-scope declaration neither run questioned.)
6. **Recommendation, held loosely.** Primary / secondary / filler / park across the
   branches, one paragraph of reasoning. The owner reorders freely.

## Three disciplines that make the tree trustworthy

- **Re-justify the existing backlog — inherit nothing.** Every open card either
  earns its place inside some branch or gets explicit push-back (demote / defer /
  retire candidate, with the reason argued through the intent). Merely ordering the
  inherited backlog is this skill's known failure mode.
- **Claims discipline.** Every "X is missing / weak / better" names its
  comparison baseline: what exists today, and why it is insufficient for the
  intent. No claim without its baseline.
- **Every candidate exits with a disposition.** Anything considered — market-
  receipt candidate items, prior-tree branches, existing cards — either lands in
  a branch or is dropped WITH the stated reason. Silent omission is the failure
  mode (calibration 2026-07-17: one run silently omitted a receipt candidate the
  sibling run had dropped with a reason).

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

## v2 six-lane projects (fallback)

No `.horus/PRD.md` — build the brief from `project.md` (vision) + `roadmap.md`
(open items) + `features.md` (shipped). There is no facet table, so branches state
their implied direction changes against `project.md`'s vision prose, and roadmap
items become proposed `roadmap.md` entries. The receipt, the tree, the re-justify
and claims disciplines, and the advisory boundary are unchanged.
