---
status: open
priority: low
created: 2026-07-21
created_by: owner
last_refined: 2026-07-21
readiness: shaping
readiness_reason: "Anticipatory design card for a regime (parallel multi-agent dev in one repo) that is not active yet; deliberately open-ended to explore options when it arrives. Escalate priority when parallel development actually starts."
phase: explore
type: spike
vision_facet: "Continuity core"
---

# concurrency-safe-continuity — make continuity hold up when multiple agents develop in parallel in one repo

## Why — anticipated, flagged 2026-07-21

The owner intends (soon-or-later) to run **multiple agents developing different features in
parallel in the same repo**. The current continuity design assumes a **linear** session
history — one "current" `current_focus`/`next_action`/`next_prompt`/`last_updated`. Parallel
agents produce a **DAG, not a line**: there is no single current state when several features
are in flight.

Predicted failure modes:

- **Every concurrent PR conflicts on `PRD.md` frontmatter** — each branch rewrites the same
  single-line fields; the first merges, the rest conflict. The occasional cross-machine
  hand-merge becomes a near-constant per-PR conflict.
- **The freshness gate manufactures the conflict** — if each branch must update continuity
  to pass `horus close --check`, every branch is forced to touch the hotspot. (The
  `close-check-unclassified-cards-advisory` bug is an early tremor of this.)
- **Backlog cards stay fine** (unique files, append-mostly) — that pattern is the model to
  extend, not abandon.

## Grounding — the principle already exists

CLAUDE.md already states the parallel-safe model: *workers record delivery facts
(SHA/PR/gate output), the supervisor owns canonical continuity, and canonical prose is
consolidated at a boundary.* The gap is that the current **format + gate** tempt/force every
feature branch to write canonical state anyway. This card is about **enforcing that
separation in the format**, not inventing a new principle.

## Intended outcome (open — explore when parallelism arrives)

A continuity model where N feature branches merge without fighting over shared continuity
files, while canonical `PRD.md` stays coherent — repo-local + serverless preserved.

## Candidate directions (sketches, NOT decisions)

- **Separate delivery-continuity from canonical-continuity:** feature branches carry
  delivery facts (in PR/commit/a per-stream note) and do NOT write canonical `PRD.md`
  frontmatter; a single consolidation pass (supervisor, at a boundary) folds them in.
- **Parallel-aware freshness gate:** gate the *consolidation* merge on canonical freshness,
  not every feature merge; check feature PRs for "carries delivery facts," not "rewrote PRD
  frontmatter."
- **DAG-shaped, append-friendly continuity:** per-stream handoff files (the card pattern)
  instead of one shared `next_prompt`; `Shipped` append-ordered rather than rewritten;
  "current state" as a composed view.

## Open questions / to explore

- Who/what owns the consolidation pass under parallelism (a dedicated supervisor session? a
  `horus consolidate` that merges N per-stream notes?).
- How much reuses the sequential fixes in `continuity-sync-friction` (this card is their
  design target, so they are not redone).
- Whether worktree isolation changes anything for the `.horus/` files specifically.

## Source

In-session process review, 2026-07-21 (owner flagged the coming parallel-multi-agent
regime). Related: `continuity-sync-friction` (sequential on-ramp),
`close-check-unclassified-cards-advisory` (early tremor). Research receipt
`.horus/research/2026-07-21-mobile-agent-session-access.md`.
