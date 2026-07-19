---
status: open
priority: high
readiness: gated
readiness_reason: "Land backlog-readiness-disposition tooling first; then this becomes Ready—Attended."
created: 2026-07-18
last_refined: 2026-07-19
vision_facet: "PO lifecycle"
phase: explore
tier: high
type: feature
parallel: safe
created_by: owner
depends-on: backlog-readiness-disposition
surface: horus/backlog.py (readiness/order fields + writer), horus/backlog_tree.py, horus/terminal_tui.py (thin trigger from the backlog pane), horus/cli.py
---

# tui-backlog-refine-and-order — groom + order the backlog into a schedulable plan

**Why (owner, 2026-07-18):** when the backlog grows large, the owner wants to trigger a
refinement pass *from the TUI* that goes through the backlog, refines each card, and
produces a **meaningful execution order** so the scheduler can run cards in that order.
The attended LLM contract now exists in the standalone `backlog-refine` skill:
picture first, pending decisions through a structured picker, and final readiness.
What remains missing is the thin TUI/CLI launch surface plus machine-readable
readiness and ordering consumers. `horus backlog` still has only
list/migrate/claim/ship/review and no refine/order action.

## Two halves (may be one command or two)

1. **Launch refinement** — invoke the bundled `backlog-refine` skill in an attended
   agent session. The skill owns the interaction and execution-ready contract; the TUI
   owns only launch/resume affordances and rendering the resulting state.
2. **Order** — produce an explicit execution order across the refined cards (respecting
   `depends-on`, `branch` grouping, priority, and parallel/surface collision stamps) so
   the scheduler can consume it. **DECIDED (owner, 2026-07-19 polish session): sparse
   `order:` integers in card frontmatter** (gaps of 10 — insert at 15 without
   renumbering), chosen over a single ordered manifest (dangling names, hot-file
   conflicts, breaks card self-sufficiency) and over priority-as-order (buckets are not
   a sequence). Semantics: consumer sort key is `(order missing?, order, priority-rank,
   filename)` — unordered cards form the unsequenced pool AFTER ordered ones, so
   existing cards keep today's behavior with zero migration. `backlog.py` parses the
   field; list/tree honor the sort; `doctor` warns (not errors) on duplicate values.
   Both producers write the same field: this refine pass across the whole backlog, and
   `scope-cards` stamping an owner-approved branch order at transcription time.

## How (to design in-card)

- The TUI opens one of the agent CLIs with `backlog-refine`, consistent with other
  launches. It does not duplicate the product picture, readiness judgment, picker
  contract, or owner gates in Python.
- The ordering output must be **deterministic and machine-readable** so
  [[tui-toggle-card-into-scheduler]] and the scheduler can consume it without re-running
  an LLM.
- Batch mode (owner's item 6): refine all cards in a row until cancelled or a meaningful
  execution order is reached — a resumable pass, not a single blocking call.

## Acceptance (firmed 2026-07-19 — order design decided above)

- From the backlog pane, one action triggers a refine+order pass; it never silently
  rewrites cards — every change is owner-approved (pathfinder-style).
- Approved order lands as sparse `order:` ints; `backlog.py` parses the field and
  list/tree render the sequence via the sort key `(order missing?, order,
  priority-rank, filename)` — no LLM in the consumer loop.
- The proposed ordering respects depends-on / branch / priority / parallel-collision
  stamps, and says so per card when a constraint forced a position.
- Cards without `order:` keep today's behavior (unsequenced pool after ordered ones)
  — no forced migration; `horus doctor` warns on duplicate order values.
- Gate: full suite green on the exact SHA. Probe: in a repo with 3+ stamped cards,
  `horus backlog list` shows them in `order:` sequence ahead of unstamped cards;
  remove one stamp and the card drops to the pool.

## Non-goals

- Not an auto-router: it proposes an order; the owner approves and the scheduler executes.
- Not the scheduler-arming toggle itself (that is [[tui-toggle-card-into-scheduler]]).
- No new orchestration runtime; Horus stays the memory/planning plane.

## Notes

Pulled forward from the items 5–7 TUI list (2026-07-18). Decoupled from the first
autonomous-scheduler test, which runs on hand-picked cards and does NOT depend on this
step. Pairs with [[tui-toggle-card-into-scheduler]].

**Ordering ownership after the calibration (2026-07-19):** `scope-cards` preserves a
branch's proposed order only as shaping context. `backlog-refine` owns the approved
execution order and will write sparse `order:` values once this card supplies the
machine-readable field and consumers. The scheduler consumes that durable state without
an LLM in its loop. The field and first consumer still land together; a parser-only
field would be ceremony.
