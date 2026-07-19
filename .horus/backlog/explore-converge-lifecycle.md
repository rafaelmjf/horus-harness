---
status: open
priority: medium
created: 2026-07-16
vision_facet: "PO lifecycle"
tier: medium
type: feature
parallel: safe
surface: PRD.md (Vision divergence framing), backlog card frontmatter (phase marker), horus-consolidate skill (phase-aware read-out)
depends-on: roadmap-convergence (supplies the convergence-side machinery)
---

# explore-converge-lifecycle — a roadmap that breathes (divergence → convergence)

A backlog that only ever *converges toward a frozen first vision* is too rigid — it
suppresses the healthy exploration a real product needs. The honest path (owner, 2026-07-16):
**research → divergence** (ideas explored as PoCs, some outside the initial vision) **→ usage
→ convergence** (drop / trim / rescope toward a consistent product; directions that prove out
are promoted into *new* Vision facets). This very repo is the worked example (six-lane →
consolidated PRD/backlog; features dropped and rescoped as usage revealed what mattered).

This is the **divergence-side** counterpart to `roadmap-convergence` (which supplies the
convergence machinery: per-facet DoD, per-card acceptance + vision link, the read-out). Both
compose into one breathing loop; the phase model below makes exploration a first-class,
default part of the roadmap rather than an off-book detour.

## Acceptance (scoped)

- **Card phase marker:** optional frontmatter `phase: explore | converge` (default `converge`
  for product work). An `explore` card is a deliberate PoC/probe — it is **exempt from the
  "Ready" gate**: it may legitimately have no `vision_facet` and no testable acceptance line
  yet, because its job is to discover, not to converge.
- **Convergence is usage-triggered, not scheduled.** An `explore` card converges when real
  usage promotes it — it gains a `vision_facet` + a DoD line (moving to `converge`), or a new
  Vision facet is created for the direction it proved out, or it is dropped/archived. The
  Vision facet set is a **living hypothesis**, explicitly allowed to grow this way.
- **Phase-aware read-out (folds into `horus-consolidate`, shared with roadmap-convergence):**
  reports per-facet convergence AND a separate **exploratory** bucket; flags `explore` cards
  that have accrued usage but not yet converged (the "time to converge or drop" signal), and
  never flags an `explore` card for missing a facet/DoD.
- Advisory only — it surfaces the phase state; the owner promotes, rescopes, or drops.
- Deliberately OMITS: stage-gate ceremony, mandatory PoC templates, any rule that forbids
  work outside the current facet set (that would defeat divergence).

## Notes

- **Mostly DELIVERED alongside `roadmap-convergence` Phase B (2026-07-16):** the `phase:
  explore|converge` marker, the Ready-gate exemption, and the exploratory bucket in the
  `horus consolidate` read-out all ship. **Remaining:** the usage-ripeness flag ("explore
  card with usage but not yet converged") is deferred — it needs a usage signal we do not
  yet capture per-card; today converge-or-drop stays owner judgment. Keep this card open for
  that piece.
- Reframes, doesn't replace, `roadmap-convergence`: convergence stays exactly as scoped; this
  card adds the explore phase and the promotion/drop dynamic around it.
