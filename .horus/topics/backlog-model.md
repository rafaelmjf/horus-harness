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

## Rollout baseline — 2026-08-09

Seeded across five projects so the structure has real data to be judged on. **This is
the baseline, not evidence.** Seeding is prompted by definition; the pinned criterion
measures what happens *after* — on a project other than horus-harness, topics get
created or updated without being asked for, and at least one accumulates a second
member card.

| Project | Topics | Active cards linked | Ungrouped |
|---|---|---|---|
| agentic-travel-guide | 6 | 18 | 0 |
| agentic-gym-coach | 5 | 9 | 1 |
| horus-harness | 5 | 7 | 0 |
| fabric-utils | 4 | 12 | 0 |
| pbi-ecosystem | 3 | 16 | 2 |
| **total** | **23** | **62** | **3** |

`fabric-metadata-driven-medallion` was in the intended set and was **not seeded**: it
has zero cards, so it can produce no evidence either way.

Three independent projects were already grouping work informally before any of this,
which is the strongest support for the model: `agentic-travel-guide` and
`pbi-ecosystem` filled `vision_facet` with descriptive labels their own vision never
defines, and `agentic-gym-coach` encoded groups as *"track D"*, *"track G"*, *"track J"*
inside card titles because no field existed. The change is giving that a name and a
place, not introducing it.

One honest limit on the rollout: those repos run the installed CLI (0.0.81), which
predates `horus/topics.py`. Their topic files are readable by any agent and by the
planned page, but no `--tree` or `consolidate` read-out will show topics there until a
release ships. The evidence window therefore starts at that release, not today.

Also recorded because it is a live finding: `tooling` in pbi-ecosystem holds 11 of 18
active cards. An emergent tag can be too broad to state a single honest thesis for, and
that is a librarian problem, not something to silently split.
