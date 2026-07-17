---
status: open
priority: medium
created: 2026-07-17
vision_facet: "Dashboard / cockpit"
phase: converge
tier: sonnet
type: feature
parallel: safe
created_by: owner
surface: new `horus backlog --tree` projection (canonical), horus/terminal_tui.py renderer, horus/fleet_backlog.py (branch: key aware)
---

# tui-branch-tree-glance — the backlog as a tree, at a glance, on the phone

**Why (owner, 2026-07-17):** opening the mobile terminal TUI should give a
seconds-long read of where the project stands: vision-branch umbrellas with their
open cards beneath, plus the latest pathfinder/branch-tree receipts — enough context
to edit a card or dispatch work (dedicated session or horus-agent) without reading
the whole backlog.

## How (thin, per the TUI rule: render canonical primitives, never a second parser)

1. **One canonical projection first:** `horus backlog --tree [--json]` groups active
   cards by `branch:` umbrella (umbrella title + convergence line, children with
   status/priority/phase/tier), then by `vision_facet` for unbranched cards.
2. **TUI renders that projection** phone-width-first: collapsed umbrellas by default,
   expand on select; existing card-open/edit actions unchanged.
3. **Receipts shelf:** list `.horus/research/` newest-first (title + date) with
   read-only open — the pathfinder results are the receipts; no new artifact.

## Acceptance

- On a 40-col phone terminal, one screen shows every vision branch with its open
  children and counts; `horus backlog --tree` emits the same structure as JSON.
- Unknown/absent `branch:` keys degrade to today's flat view (forward-readable).

## Non-goals

- No kanban board/columns, no status workflow (agent-first boundary); no editing in
  the tree view beyond opening the existing card actions; no second backlog parser.
