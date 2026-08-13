---
status: recorded
type: discussion
topic: backlog-model
created: 2026-08-09
created_by: owner
recorded_at: 2026-08-09
session: 9c536fc0
priority: medium
parallel: safe
---

# Topics over facets — how work should be grouped

> **Archived 2026-08-13.** The decision this card recorded shipped in #506 (`9ee4e53`) — free-form
> `topic:` is the grouping model and facets are retired. Its own open question ("what status is a
> discussion card born in?") is now answered: `recorded` has no terminal readiness, so an active
> discussion card trips the Unclassified gate forever. Resolution (owner): discussion cards are
> **transient** — record → distill into Vision/Rules/Shipped → archive. This card is that archive
> step; its reasoning is preserved here and the rule lives in the Vision's agent-structure boundary.

**A discussion card: a decision and its reasoning, with no work planned.** It exists because
this reasoning had nowhere else to live — it is not a task, it does not belong to one card,
and consolidation would otherwise have recorded only the conclusion. This card is also the
first instance of the thing it proposes, so its own shape is part of the proposal.

## The problem

Cards must name a `vision_facet` from a closed set defined in the Vision, and each facet
carries a definition of done authored at product-audit level. That is a heavy contract to
satisfy at the moment a card is created, which is the moment of maximum uncertainty: "what
is this about" is answerable immediately, "what is the definition of done for the direction
this belongs to" often is not.

**The evidence is in the backlog itself.** Five of seven open cards are `phase: explore` —
the flag that exempts a card from the facet-link requirement. Two of those five are not
exploratory in any real sense: `codex-isolated-config-leak` is a confirmed bug with an
owner-chosen remedy, and `openwiki-graphify-value-benchmark` has a finished verdict. They
are `explore` because the facet contract was the wrong shape for them, not because they are
exploring anything. `phase: explore` has become the escape hatch.

A second gap surfaced the same day from the opposite direction. A session produces **units
of understanding** — decisions, findings, verdicts — while the backlog stores **units of
intended work**. Cross-cutting decisions with no parent card have no home, so they land as
scattered prose in `## Rules`, a card's `## Verdict`, or `next_prompt`, or they are lost.
This was already carded twice on 2026-07-20/21 (`decision-doc-skill`,
`research-receipts-surfacing`) and both were shelved on 08-01; the recurrence is the signal.

## Options considered

1. **Keep facets, relax the requirement.** Cheapest. But it does not create a home for
   decisions, and it leaves `phase: explore` doing a job it is not shaped for.
2. **Replace facets with free-form topics.** Solves authoring cost. Cost: a facet's
   definition of done is what makes convergence *judgeable* — it is what caught the
   Dashboard facet reading "converged" while the hosted dashboard went entirely unused.
   Free-form topics can only report *has cards / has no cards*, which is that exact
   ambiguity.
3. **Topics as an emergent rung below facets, with promotion.** Topics are created at
   consolidate by a ledger check; a topic that accumulates real delivery earns a definition
   of done and graduates to a facet.

## Where it landed (2026-08-09, owner)

**Option 3, with topics emerging at each `consolidate` rather than at product-audit.** Some
topics carry work cards; some carry only a discussion card, recording a conclusion with no
future work planned.

Two arguments settled it.

The objection to dropping facets was that convergence stops being judgeable — but **a
detector nobody feeds is not protecting anything**, and 5 of 7 cards bypass it. The tooling
also degrades gracefully: `product-audit` reads delivered code against *"facets where the
project defines them, the Vision's own claims where it does not."*

And the Vision already describes the promotion mechanism — *"exploratory work is expected to
lack a facet/DoD until it earns one or is dropped"*, *"directions that prove out are
promoted into new facets"*. What was missing was a **lower rung to graduate from**.
`phase: explore` was doing that job as a boolean when what is needed is a grouping: five
cards marked "not yet a facet" says nothing about which of them are about the same thing.

`consolidate` is the right moment to mint topics because it is the only point where an agent
holds the whole session — the same reason that routine exists at all.

## Open questions — not decided

- **What status is a discussion card born in?** It is done at creation: nothing shipped,
  nothing to schedule. If it lands `open` it inflates every readiness count and trips the
  Unclassified gate. This card deliberately tests `status: recorded` to find out what the
  current tooling does with an unknown terminal state.
- **Do discussion cards share the board with work cards?** If they share columns, the board
  stops answering "what do I pick up next".
- **Does `vision_facet` stay required for `converge` cards**, making topics additive and
  breaking nothing — or does it go, which means the convergence read-out needs rethinking
  first?

## The rule to write in from the start

**Bias hard toward joining an existing topic.** If every consolidate can mint one, there
will be one topic per session and the grouping will mean nothing. The ledger check is "what
fits" first and "create" only when genuinely nothing does. `backlog-librarian` is the right
tool for the periodic merge pass.

## Related

- `decision-doc-skill` (shelved) — the format half of this problem: *"identify the problem →
  analyse the options with consequences → land a recommended solution."* This card follows
  that shape deliberately.
- `research-receipts-surfacing` (shelved) — the surfacing half: receipts *"exist just as .md
  files"* and are invisible a week later.

## Source

Owner conversation, 2026-08-09, session `9c536fc0`, arising from a dashboard/board mockup
review. No work is planned from this card.
