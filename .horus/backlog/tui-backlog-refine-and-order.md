---
status: open
priority: high
created: 2026-07-18
vision_facet: "PO lifecycle"
phase: explore
tier: opus
type: feature
parallel: safe
created_by: owner
surface: new backlog-refine step (pathfinder-adjacent skill or new last step), horus/backlog.py (order field + writer), horus/backlog_tree.py, horus/terminal_tui.py (trigger from the backlog pane), horus/cli.py
---

# tui-backlog-refine-and-order — groom + order the backlog into a schedulable plan

**Why (owner, 2026-07-18):** when the backlog grows large, the owner wants to trigger a
refinement pass *from the TUI* that goes through the backlog, refines each card, and
produces a **meaningful execution order** so the scheduler can run cards in that order.
Today nothing does this: `horus backlog` has only list/migrate/claim/ship/review (no
refine, no order), and pathfinder's last step (`scope-cards`) *populates cards from a
chosen direction* — it does not refine + order an existing backlog. So this is a **new
capability** (the owner's items 5–6), not an invoke of an existing step. Confirmed
2026-07-18.

## Two halves (may be one command or two)

1. **Refine** — go through open cards and sharpen each toward self-sufficiency (context
   / concrete how / acceptance / non-goals), the way `scope-cards` makes a fresh session
   able to pick a card up cold. Reuse `scope-cards`'s card-quality bar; the difference is
   the *input* is the existing backlog, not a chosen branch.
2. **Order** — produce an explicit execution order across the refined cards (respecting
   `depends-on`, `branch` grouping, priority, and parallel/surface collision stamps) so
   the scheduler can consume it. Cards are **filename-sorted today with no order field**,
   so ordering needs either an explicit `order:` frontmatter field (+ a writer + a
   backlog_tree/consumer that honors it) or another durable ordering artifact. Decide
   in-card; prefer the smallest machine-readable thing the scheduler can read.

## How (to design in-card)

- The refine pass is LLM-backed (it grooms prose), so it belongs in a **skill** (a new
  pathfinder last step, or a standalone `backlog-refine` skill) invoked from the TUI —
  the TUI opens one of the agent CLIs behind it, consistent with how launches work. The
  TUI trigger is thin; the skill does the grooming. Advisory + owner-gated like the other
  pathfinder steps: it proposes card edits + an order, the owner approves.
- The ordering output must be **deterministic and machine-readable** so
  [[tui-toggle-card-into-scheduler]] and the scheduler can consume it without re-running
  an LLM.
- Batch mode (owner's item 6): refine all cards in a row until cancelled or a meaningful
  execution order is reached — a resumable pass, not a single blocking call.

## Acceptance (draft — refine before actioning)

- From the backlog pane, one action triggers a refine+order pass; it never silently
  rewrites cards — every change is owner-approved (pathfinder-style).
- The result is a durable, machine-readable execution order the scheduler can read
  without an LLM in the loop.
- Ordering respects depends-on / branch / priority / parallel-collision stamps.
- Existing cards without the new order field keep their current (filename-sorted)
  behavior — no forced migration.

## Non-goals

- Not an auto-router: it proposes an order; the owner approves and the scheduler executes.
- Not the scheduler-arming toggle itself (that is [[tui-toggle-card-into-scheduler]]).
- No new orchestration runtime; Horus stays the memory/planning plane.

## Notes

Pulled forward from the items 5–7 TUI list (2026-07-18). Decoupled from the first
autonomous-scheduler test, which runs on hand-picked cards and does NOT depend on this
step. Pairs with [[tui-toggle-card-into-scheduler]].

**The ordering artifact has a second producer (skills-review session, 2026-07-19):**
`scope-cards` is instructed to "inherit the branch order" from the owner-approved
`roadmap-branches` roadmap, but with no durable field the approved order evaporates at
write time — cards land filename-sorted and an owner decision is silently lost. So
whatever this card chooses (an `order:` frontmatter field + writer, or another durable
artifact) must be writable by BOTH producers — the refine pass here and `scope-cards`
at scoping time — and consumable by the scheduler/[[tui-toggle-card-into-scheduler]]
without an LLM in the loop. Decide once, here; `scope-cards` (which now owns the
dispatchable-card contract, v3) then adopts the same field rather than inventing a
rival. Deliberately NOT built ahead of this card: a field with no consumer is ceremony
(the boundary rule), so the decision and the first consumer should land together.
