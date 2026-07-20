---
status: open
priority: low
created: 2026-07-20
created_by: agent
last_refined: 2026-07-20
readiness: shaping
readiness_reason: "Wildcard explore: canary format and the diff-judging protocol are undecided; PoC on one skill before any generalization."
phase: explore
type: research
vision_facet: "Introspection & self-improvement"
---

# skill-self-calibration-probe — skills that notice their own drift (wildcard)

## Why

The 2026-07-20 audit's self-detection gap: product-audit drifted from owner
intent and only the owner's interruption caught it — the introspection facet
audits everything except its own alignment. Divergent bet: each bundled skill
carries 2-3 canary questions with contract-derived expected shapes; a
periodic (potentially autonomous) run replays them in a fresh session and
diffs the answers against the skill's contract, surfacing drift before an
owner has to feel it.

## Intended outcome

A replay on ONE skill catches a real contract violation cheaply.
**Converges** if the PoC catches something material (then canaries become
part of the skill-rewrite ritual); **dropped** if diffs are all noise —
ceremony risk is named upfront and the drop is a valid finding for the
introspection facet.

## Broad boundaries

PoC-first on `product-audit` v3 — today's calibration answers (the accepted
receipt structure, the decides-nothing contract, the routed-suggestions
rule) ARE the first canaries. Non-goals: no framework before one PoC verdict;
no auto-editing skills from a diff; no LLM-judge pipelines beyond a single
fresh-session replay.

## Open decisions for backlog-refine

- Canary format (in-skill section vs sidecar file) and who authors them.
- What counts as a "material" catch vs noise in the diff.
- Cadence and whether the replay is an autonomous-eligible task.

## Source

Agent wildcard at the 2026-07-20 scope-cards gate, owner-approved;
`.horus/audits/2026-07-20-product.md` (self-detection gap).
