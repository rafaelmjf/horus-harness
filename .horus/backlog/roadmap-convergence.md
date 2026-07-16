---
status: open
priority: medium
tier: sonnet
created: 2026-07-16
type: feature
parallel: safe
surface: PRD.md (Vision facets + Structure contract), backlog card template/frontmatter, new thin skill (or fold into horus-consolidate)
depends-on: vision-expansion decision (continuity-layer → repo-local product owner); see product-naming
---

# roadmap-convergence — a healthy backlog that converges toward the Vision, with a DoD

Today the backlog grows ad hoc: items land only when a bug is hit or a need is felt, with no
structural tie to the Vision and no explicit "done." The gap (research receipt:
`.horus/research/2026-07-16-po-capabilities.md`) is that every serious roadmap tool (BMAD,
spec-kit, Kiro, task-master, Cline) separates a stable north-star doc from a volatile backlog
and derives the backlog FROM it. Horus already has that split (PRD Vision/Rules vs Backlog
cards) — it's missing the **link**, the **done-line**, and a **convergence read-out**.

**Ethos guard:** ~2 lines per card + 1 line per Vision facet + one advisory skill. Keep DoD at
the *instruction* rung (a line in the card), not a gate, unless a real failure earns promotion
(controls-climb-a-ladder). Do NOT fragment the one-PRD invariant.

## Acceptance (scoped minimal subset — steal 3, leave the rest)

- **Per Vision facet: a one-line measurable definition of done** — so "converged" is a
  stateable condition, not a vibe (the lightest possible "constitution").
- **Per backlog card: one testable acceptance line (EARS-lite: "when X, the tool should Y")
  + a one-line link to which Vision facet it advances.** A card that can state neither is
  parked — the "Ready" gate that stops off-vision, reactive-only cards from accreting. Extend
  the card frontmatter/template + Structure contract accordingly.
- **Frame Backlog explicitly as "the gap between Vision and Shipped"** in the PRD, so an
  empty/closing backlog against stated Vision-DoD *is* the definition of converged.
- **A thin skill (`horus-converge`, or fold into `consolidate`):** reads Vision facets + DoD
  + Shipped, emits per-facet a one-line coverage verdict (converged / partial-with-open-cards
  / uncovered-no-cards), and flags cards with no vision link and vision facets with no cards
  (the reactive-backlog smell). Advisory only — no auto-editing.
- Deliberately OMITS: agent-persona zoos (BMAD), per-feature multi-file spec trees (spec-kit
  6 files / Kiro triad), JSON task DB + complexity-scoring LLM passes + MCP (task-master),
  pre-impl architecture gates and formal INVEST checklists.

## Notes

- Lower-risk than `market-scan` (fully in-repo, no outward data, no token-heavy composition) —
  a candidate to build first.
- Gated on the vision-expansion decision; idea-ledger card until that lands.
