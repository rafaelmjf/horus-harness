---
status: open
priority: later
tier: sonnet
created: 2026-07-10
---

# Productionize `horus capabilities` (fleet capability catalog)

Prototype landed as **draft PR #139** (`horus/capabilities.py` + `capabilities`
subcommand): a read-only JSON index aggregating every registered project's
`.horus/PRD.md` Shipped ledger (best-effort six-lane fallback) plus, for
CLI-type projects, the extracted argparse subcommand tree. Held invariants:
read-only over sources, idempotent (no timestamps), no fetching,
self-contained, `note` field marks it generated. Agent-first — deliberately
**not** a link graph (that was `horus wiki`, draft PR #138, a separate
prototype held for its own keep/shape decision).

Decide-then-build once the spike is reviewed:

- **More surface extractors.** v1 only implements the CLI case
  (`_CLI_EXTRACTORS` registry, keyed by project name) with harness's own
  `horus` CLI as the sole entry. A **web** extractor (Flask/FastAPI route
  table, or the dashboard's own routes) and a **lib** extractor (package
  entry-points / public API surface) would extend the registry to
  non-CLI project types without touching aggregation.
- **Cross-project cross-referencing.** Currently `related_commands` only
  fires within a project that has its own registered CLI extractor (only
  horus-harness today). Once a second project registers an extractor, decide
  whether cross-referencing should stay per-project or extend fleet-wide.
- **Optional human-facing visualization**, built *on top of* the generated
  JSON (never replacing it as the source of truth) — a dashboard "Generate
  capabilities" action or a rendered browse page. Per the ladder rule, only
  if there's an observed pull for it; the JSON alone is the deliverable the
  agent-utility test was built to prove out.
- **Six-lane fallback has no live exercise.** Every currently-registered
  project is already on PRD-structure v3, so the `features.md` fallback path
  is only covered by a fixture test, not a real project. Revisit if/when a
  v2 project re-enters the registry.
