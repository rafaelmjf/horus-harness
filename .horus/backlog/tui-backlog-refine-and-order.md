---
status: open
priority: high
readiness: ready
autonomy: attended
readiness_reason: "Gate satisfied — `backlog-readiness-disposition` shipped and is archived, and the card itself named that as the only precondition ('then this becomes Ready—Attended'). Attended because this is the owner-facing interactive refinement flow. Surfaced by the 2026-07-26 backlog-librarian receipt (L1): it had been sitting Gated on already-delivered work."
created: 2026-07-18
last_refined: 2026-07-19
vision_facet: "PO lifecycle"
phase: explore
tier: high
type: feature
parallel: safe
created_by: owner
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

## Reviews

- 2026-07-26 — **Gated → Ready / attended.** Surfaced by the backlog-librarian receipt
  (L1): `depends-on: backlog-readiness-disposition` resolved to an archived card with
  `status: shipped`, while this card's own reason named that as the only precondition
  ("Land backlog-readiness-disposition tooling first; then this becomes Ready—Attended").
  So a **high-priority** card had been sitting blocked on already-delivered work.
  Dependency removed and readiness minted as the card itself specified. Attended, not
  eligible: this is the owner-facing interactive refinement flow, so owner presence is
  the point. Re-check scope before scheduling — it is `tier: high`.

### 2026-07-27 — Rafael Figueiredo (agent)
Verdict: implemented — order field + consumers + launch trigger

Delivered on branch feat/backlog-order-and-refine-launch. Three decisions worth recording. (1) DEVIATION from the acceptance line '`horus doctor` warns on duplicate order values': card-level backlog hygiene lives in `backlog.hygiene_findings`, which rides `consolidate` and `close --check` — doctor does NOT call it. Wiring hygiene into doctor to honour the wording literally would have made doctor emit every existing card warning (~37 Unclassified/shaping notices here), far outside this card. Owner approved landing it in hygiene_findings PLUS `horus backlog list`, which is where a broken sequence is actually noticed. (2) `order` sequences WITHIN a readiness queue, not across the whole backlog: every renderer prints per queue, so a cross-queue sequence could not be displayed at all — and the plan that matters is the sequence of schedulable cards. The card's stated key nests inside the existing queue index: (queue, order missing?, order, priority-rank, priority, name). (3) NO `set_order` writer, despite `surface` naming one. There is no `set_readiness` writer either — the attended pass edits card frontmatter directly, and a writer with no caller is exactly the ceremony this card warned about. Evidence the producer half was already real: `windows-native-horus-setup` has carried `order: 20` since a 2026-07-21 refine pass, and nothing had ever consumed it. Owner addition beyond the original scope: the pass now starts from live delivery state (open PRs, unmerged remote branches, continuity freshness) because bug PRs opened by other sessions make a backlog picture wrong — embedded deterministically in the prompt AND added as step 0 of the skill (v5 to v6).
