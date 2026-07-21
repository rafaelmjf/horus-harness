---
status: open
priority: medium
created: 2026-07-21
created_by: owner
last_refined: 2026-07-21
readiness: shaping
readiness_reason: "A real design card: the manifest/bundle format, directory layout, which chain steps emit what, and back-compat with the existing dated receipts are all open. Agree the structure before implementing across the chain skills."
phase: explore
type: feature
vision_facet: "PO lifecycle"
---

# pathfinder-structured-outcome — refine the pathfinder chain to emit one structured, addressable per-run outcome

## Why — owner, 2026-07-21

The pathfinder chain (`pathfinder` → `product-audit` → `market-scan` →
`roadmap-branches` → `scope-cards` → `backlog-refine`) currently drops its artifacts as
**ad hoc dated receipts** scattered across `.horus/research/` and `.horus/audits/`.
Nothing ties one run's artifacts together, so a run is not an addressable unit. This
blocks:

- **`wildcard`** — needs to load "the previous pathfinder run" as a coherent evidence
  set (its stated prerequisite).
- **re-runs / resumption** — no clean way to resume, or to compare against a prior run.
- **review + traceability** — which cards came from which run, off which evidence.

The owner wants the chain refined so it produces a **structured outcome**: a coherent,
addressable per-run bundle rather than loose receipts.

## Rough shape (open — this is the design question)

- A **per-run identity** (id/date) that groups a run's artifacts: the position brief,
  `product-audit` receipt, `market-scan` receipt, `roadmap-branches` divergence tree,
  `scope-cards` drafts, and the resulting cards.
- A **manifest** enumerating the run's artifacts + metadata (intent pinned, dates,
  freshness, branch chosen, cards minted) so a consumer (wildcard, the owner, a future
  run) loads the set without guessing.
- The chain steps write into the run's structure rather than dropping standalone
  receipts — or keep the receipts and add a manifest that references them (a back-compat
  choice, see below).

## Open decisions

- **Directory-per-run** (`.horus/research/pathfinder-<date>/…`) vs a **manifest file**
  that references the existing dated receipts in place.
- Which steps are mandatory vs optional in a run (a run may skip `market-scan`, etc.) and
  how the manifest represents a partial run.
- Back-compat with the dated receipts already on disk.
- How much this touches each chain skill's text vs a shared helper/convention.
- Pure `.horus/` convention vs any `horus` run/bundle tooling.

## Non-goals

- Not changing what each step *does* (audit/scan/branches logic stays) — only how a
  run's outputs are structured and grouped.
- Not auto-running the chain — `pathfinder` stays owner-invoked/attended.

## Source

In-session, 2026-07-21 — elevated from the `wildcard` prerequisite note into a proper
card at owner request. Related: `wildcard` (primary consumer; depends on this),
`pathfinder`, `product-audit`, `market-scan`, `roadmap-branches`, `scope-cards`,
`backlog-refine`. Skill targets: `.claude/skills/pathfinder` (+ the chain skills).
