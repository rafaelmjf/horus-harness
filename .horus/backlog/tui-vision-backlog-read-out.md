---
status: open
priority: medium
created: 2026-07-20
created_by: owner
last_refined: 2026-07-20
readiness: shaping
readiness_reason: "Which read-outs render (facet standings, branch tree, readiness queues), on which TUI pane, and what stays CLI-only are undecided."
phase: converge
type: feature
vision_facet: "Dashboard / cockpit"
---

# tui-vision-backlog-read-out — the cockpit shows direction, not just cards

## Why

The TUI (the owner's real cockpit, including phone) lists cards and queues,
but the *direction* layer — facet standings, vision-branch states, the
convergence read-out — lives only in `horus consolidate` text output and dated
receipt files. The 2026-07-20 audit rendered exactly the tables the owner
wants visible (facet | standing | distance | drift); today they evaporate
into `.horus/audits/`. Owner named this family directly ("better TUI visuals
for the backlog / vision analysis").

## Intended outcome

Opening a project in the TUI answers "where does this product stand and what
direction is active" at a glance — the same semi-deterministic tables the
audit/receipts produce, rendered live from PRD + cards, not from stale
receipt files.

## Broad boundaries

Render existing canonical primitives only (the TUI-stays-thin rule: no second
parser or state path — `backlog.py`, `frontmatter.py`, the consolidate
read-out functions). Non-goals: no editing from these views; no new analysis
computed only in the TUI; desktop-first is fine, phone-width follows the
existing responsive patterns.

## Open decisions for backlog-refine

- Scope of v1: facet table only, or facet + branch tree + readiness queues?
- Placement: project pane extension vs a dedicated view.
- Relationship to the two Gated TUI cards (`tui-backlog-refine-and-order`,
  `tui-toggle-card-into-scheduler`) — sibling, prerequisite, or independent.

## Source

`.horus/research/2026-07-20-roadmap-branches-rebaseline.md`, owner verdict
section (candidate families).
