---
status: open
priority: medium
created: 2026-07-20
created_by: owner
last_refined: 2026-07-20
readiness: shaping
readiness_reason: "Index shape (frontmatter? naming convention? generated list?), render surfaces, and whether receipts gain lifecycle states are undecided."
phase: converge
type: feature
vision_facet: "PO lifecycle"
---

# research-receipts-surfacing — receipts as first-class citizens, not stray .md files

## Why

The PO-lifecycle chain runs on dated receipts (`.horus/research/`,
`.horus/audits/`) — the 2026-07-20 calibration run alone produced three. They
are the interfaces between pathfinder steps and the evidence base for
convergence decisions, yet nothing lists, links, or resurfaces them: a week
later they are invisible unless someone remembers the filename. The owner
named this gap directly ("these pathfinder researches at the moment exist
just as .md files").

## Intended outcome

Receipts are discoverable where the owner works: listable (CLI), visible per
project (TUI/dashboard), and referenced from the PRD or cards they fed — so a
convergence decision can cite its evidence base without archaeology.

## Broad boundaries

Surface and index what exists; do not change what receipts ARE (committed
markdown, no runtime service — consistent with the parked fleet-recall-plane
wildcard, which stays parked). Non-goals: no receipt database; no semantic
search (that is the parked S2 wildcard's PoC, separate); no new authoring
ceremony on skills that write receipts beyond, at most, a naming/frontmatter
convention.

## Open decisions for backlog-refine

- Minimal index mechanism: filename convention + a generated list, or light
  frontmatter on receipts?
- Which surfaces render it in v1 (CLI list, TUI pane, dashboard panel).
- Whether receipts carry a consumed-by/feeds pointer (audit ↔ scan ↔ tree
  chains) or stay flat.

## Source

`.horus/research/2026-07-20-roadmap-branches-rebaseline.md`, owner verdict
section (candidate families).
