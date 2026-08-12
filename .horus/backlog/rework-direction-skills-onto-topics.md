---
status: open
priority: medium
readiness: deferred
autonomy: attended
created: 2026-08-12
created_by: owner
type: feature
topic: backlog-model
parallel: safe
tier: large
reactivate_after: after real use of the emergent topics/vision structure
surface: ".claude/skills/* (new topic-native direction skills)"
depends-on: retire-facets-for-topics
---

# rework-direction-skills-onto-topics — reintroduce direction-setting skills on the topic model, later

## Why (deferred on purpose)

`retire-facets-for-topics` deletes the entire facet-coupled skill suite outright —
`product-audit`, `roadmap-branches`, `scope-cards`, `market-scan`, `pathfinder`, `wildcard`,
`explore-converge-lifecycle` — because each encoded the facet definition-of-done and the
divergence→convergence ceremony that no longer exists, and rewriting seven skills onto a
brand-new, unproven model would be guessing.

The **capabilities** those skills provided are not all worthless; some are just mis-shaped for
the old model:

- **Inward audit** (was `product-audit`): read shipped code against the Vision seed + topic
  delivery claims, honestly.
- **Direction → cards** (was `scope-cards`): turn a chosen direction into aligned backlog drafts,
  now keyed on a `topic:` not a `vision_facet`/`branch`.
- **Outward research** (was `market-scan`): competitive/JTBD research that proposes seed edits +
  candidate topics, not a facet table.
- **Opportunity generation** (was `wildcard`): propose new moves from the gap between the seed
  and shipped code, and from owner friction — sourced from topics, not facet DoD.

Explicitly **not** coming back: the divergence-tree / convergence-ceremony workflow
(`roadmap-branches`, `pathfinder`) — the emergent Vision replaces the need for a scheduled
converge step.

## The bet

Use the emergent topics + emergent Vision for a while first. Only after real use do we know
which of these capabilities we actually miss, and what shape they should take on the new model —
so this is deliberately `deferred`, not `ready`. Reactivate when the emergent structure has
enough lived-in evidence to shape topic-native replacements without guessing.

## Acceptance (to refine when reactivated)
- Decide, from usage evidence, which retired capabilities to reintroduce and in what form.
- Any reintroduced skill is topic-native: no `vision_facet`, no facet DoD, no convergence step.

## Source
Owner decision 2026-08-12, alongside `retire-facets-for-topics`: retire now, rework after using
the emergent structure.
