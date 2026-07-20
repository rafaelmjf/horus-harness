---
status: open
priority: low
created: 2026-07-20
created_by: agent
last_refined: 2026-07-20
readiness: shaping
readiness_reason: "Small deterministic change; refinement confirms the exact interval formula and mints autonomy."
phase: converge
type: chore
vision_facet: "Introspection & self-improvement"
---

# audit-advisory-interval — count releases AND days, not releases alone

## Why

The product-audit staleness advisory fired repeatedly within four days because
its interval counts releases only — and this project shipped 15 releases in 4
dogfooding days. Releases are a poor clock during rapid iteration; elapsed
time is a poor clock during idle stretches. The 2026-07-20 audit receipt's
ceremony section recorded the finding. Small, deterministic, code-only —
shaped as an early autonomous-eligible candidate.

## Intended outcome

The advisory fires when BOTH thresholds pass (e.g. ≥N releases AND ≥M days
since the stamp), so it nags neither during release bursts nor during long
quiet stretches — thresholds decided at refinement.

## Broad boundaries

Touches only the advisory condition reading `last_product_audit` (version +
date are already both in the stamp). Non-goals: no new stamp format; no
per-project configurability until someone needs it.

## Open decisions for backlog-refine

- The N/M defaults (candidate: 10 releases AND 14 days).
- AND vs weighted-either semantics.
- Autonomy mint: eligible under which envelope bounds.

## Source

`.horus/audits/2026-07-20-product.md` ceremony observations;
`.horus/research/2026-07-20-roadmap-branches-rebaseline.md` branch D item 4.
