---
status: shipped
priority: medium
tier: sonnet
created: 2026-07-16
vision_facet: "PO lifecycle"
type: feature
parallel: safe
surface: PRD.md (Vision facets + Structure contract), backlog card template/frontmatter, new thin skill (or fold into horus-consolidate)
relates-to: explore-converge-lifecycle (divergence-side counterpart, shares the read-out)
shipped_pr: 282
shipped_sha: 026d94c
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
- **Per `converge`-phase card: one testable acceptance line (EARS-lite: "when X, the tool
  should Y") + a `vision_facet` link.** A converge card that can state neither is parked —
  the "Ready" gate that stops off-vision, reactive-only cards from accreting. **Phase-aware:**
  `explore`-phase cards are exempt (they discover, not converge — see
  `explore-converge-lifecycle`). DECIDED: `vision_facet` links applied to all existing cards
  now; the acceptance line is required going-forward on new/next-touched converge cards (not a
  full retrofit). Extend the card template + Structure contract accordingly.
- **Frame Backlog explicitly as "the gap between Vision and Shipped"** in the PRD, so an
  empty/closing backlog against stated Vision-DoD *is* the definition of converged.
- **Read-out folded into `horus-consolidate`** (DECIDED — not a standalone skill; cheapest
  rung, runs at the consolidation/grooming boundary): reads Vision facets + DoD + Shipped +
  each card's `vision_facet`/phase, emits per-facet a one-line coverage verdict (converged /
  partial-with-open-cards / uncovered-no-cards) plus a separate **exploratory** bucket, and
  flags off-vision converge cards (missing facet/DoD) and explore cards ripe to converge or
  drop. Advisory only — no auto-editing.
- Deliberately OMITS: agent-persona zoos (BMAD), per-feature multi-file spec trees (spec-kit
  6 files / Kiro triad), JSON task DB + complexity-scoring LLM passes + MCP (task-master),
  pre-impl architecture gates and formal INVEST checklists.

## Notes

- **Phase A DONE (2026-07-16, PRD-only):** 7 Vision facets + DoD lines defined in PRD Vision;
  breathing divergence→convergence model added; all 13 cards stamped with `vision_facet`.
- **Phase B DONE (2026-07-16):** `Card.vision_facet`/`phase` parsing (`horus/backlog.py`);
  `routines.convergence_findings` phase-aware read-out wired into `horus consolidate`;
  `horus-consolidate` skill v12 documents it; Structure-contract convention added; tests in
  `test_backlog.py`/`test_routines.py`/`test_skills.py`. Live-probed via `horus consolidate`.
- Both phases delivered — ready to `horus backlog ship` after the PR merges. `market-scan`
  is the remaining PO-lifecycle card.
