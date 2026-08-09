---
state: open
priority: high
created: 2026-08-09
---

# backlog-model — group work by something people actually understand

## The problem

Work is grouped by **facet**: a term with no plain meaning, backed by a definition-of-done contract authored at audit level. The evidence says the concept is not understood rather than too expensive. The field is filled on nearly every card across the fleet — 18 of 18 on one project, 10 of 10 on another — but filled with **ad-hoc labels those projects' own vision never defines**. Only one project in nine has a facet table, and only that one has ever been audited. Five of seven cards here route around the requirement via an escape hatch, including a confirmed bug and a finished investigation, neither of which is exploratory in any sense.

Cards are also fragments. Nothing states what a group of them is *for*, so a session's conclusions land as scattered prose in rules, in a card's review section, or nowhere.

## What we are building

**Two kinds, both in plain language.** Cards are pieces of work. Topics group them and state, in prose a reader with no context can follow, the problem being solved and what the finished thing should look like — the same reading contract a refined card already gets, one altitude up.

Topics live in `.horus/topics/`, outside the backlog, so they cannot enter a readiness queue or be mistaken for dispatchable work. They carry priority for ordering but never readiness. Some have no members: a direction stated but not yet broken down, or a question already answered.

Opening a topic runs a **scoped evaluation** — what the product already does here, where the gaps are, what could follow — rather than opening one card. That unit is small enough to actually invoke, which whole-project audits never were.

Facets are untouched for now: topics ship alongside them, and retirement is its own later decision once the fleet shows whether topics emerge on their own.

## How it was decided (2026-08-09)

Three options were weighed. **Keep facets and relax the requirement** was cheapest but created no home for decisions. **Replace facets with free-form tags** solved authoring but lost the only thing a definition of done buys — convergence being judgeable, which is what once caught a facet reading "converged" while the surface behind it went entirely unused. **Topics as an emergent rung with promotion** was chosen: a topic that accumulates real delivery can later earn a definition of done and graduate.

Two arguments settled it. A detector nobody feeds protects nothing, and five of seven cards bypass the facet gate. And the vision already describes promotion — exploratory work is expected to lack a definition of done "until it earns one" — it simply had no lower rung to graduate from.

Deliberately not added: a third kind for recorded decisions. A topic with no members already is one, and the extra type only announced what the structure shows.

Still open: whether the facet field is eventually dropped from cards, whether topics may span projects (`account-isolation` is genuinely fleet-wide), and how a settled topic differs on screen from one merely awaiting cards.
