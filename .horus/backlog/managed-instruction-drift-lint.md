---
status: shelved
shelved_on: 2026-08-01
priority: medium
created: 2026-07-24
last_refined: 2026-07-28
refine_passes: 1
created_by: claude
readiness: shaping
readiness_reason: "The reference-extraction rule (which tokens in the managed block count as CLI-surface claims) and where the lint runs (doctor vs consolidate vs a standalone check) are undecided; refine before build."
phase: explore
type: feature
vision_facet: "Introspection & self-improvement"
---

# managed-instruction-drift-lint — deterministically catch managed prose that references a removed CLI surface

## Why — grounded in a recorded incident, not speculation

The 2026-07-20 product audit's sharpest self-criticism, stated twice: improvements
don't propagate (126 stale skill installs fleet-wide) and "drift detection relies on
the owner noticing." The concrete harm already occurred this cycle — stale managed
prose taught a **deleted** knob (the removed "session mode"/granularity setting)
across the fleet before anyone caught it. The `skill-audit` skill checks *skill*
text against the live surface, but it is owner-invoked, per-skill, manual, and
deliberately carries no staleness advisory. The one surface most likely to rot
undetected — the **Horus-managed instruction block dual-installed into every
project's CLAUDE.md / AGENTS.md** — has no deterministic guard at all. This is the
repo's own rule ("put safety in the code, not the reviewer") applied to its own prose.

## Rough shape

- A read-only advisory lint that extracts CLI-surface claims from the managed block
  (and optionally PRD `## Rules`): `horus <cmd>`, `<cmd> --<flag>`, subcommand names.
- Cross-checks each against the live command registry (the same source `horus --help`
  renders from) — flags references to commands/flags that no longer exist.
- Emits `[warn]` advisories only; never edits prose, never blocks. Natural homes to
  weigh at refinement: `horus doctor`, a `horus consolidate` signal, or a standalone
  `horus lint-prose`. Autonomous-safe (zero blast radius) — good away-mode/librarian food.
- Scoped to *dangling references* (deterministic, high-precision). Semantic drift
  ("the prose describes behavior that changed") stays explicitly out — that's the
  subjective audit's job, not a lint's.

## Open questions

- Extraction precision: how to tell a genuine CLI claim from an illustrative or
  historical mention without a flood of false positives (allowlist? fenced-block only?).
- Should it also lint the *skill* registry surface, or leave that to `skill-audit` to
  avoid overlap? (Recommendation: managed-block + Rules only; hand skills to skill-audit.)
- Fleet scope: lint only this repo's block, or every project carrying the managed block?
  (The propagation harm is fleet-wide, but fleet-walking is a bigger, separate build.)

## Non-goals

- No auto-editing or auto-refreshing prose (that is `skill-drift-surfacing-and-refresh`).
- No semantic/behavioral drift judgment — dangling references only.
- No new blocking gate; advisory exit only.
- No duplication of `skill-audit`'s per-skill manual review.

## Source

Wildcard run 2026-07-24, grounded on the 2026-07-20 pathfinder rebaseline
(product audit Introspection facet + routed self-detection gap) and the recorded
"deleted-knob taught fleet-wide" incident. Related: `skill-drift-surfacing-and-refresh`,
`skill-audit` (skill), `skill-self-calibration-probe`, `close-check-unclassified-cards-advisory`.
