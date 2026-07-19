---
status: open
priority: low
created: 2026-07-20
created_by: agent
last_refined: 2026-07-20
readiness: shaping
readiness_reason: "Where the contract is declared (docs vs code constants vs README), the exact field list per tier, and how tier names surface to users are undecided; refine before writing."
phase: explore
type: research
branch: vision-branch-x6-workflow-selection-compatibility
---

# x6 — declare the continuity contract explicitly

## Why

The boundary inventory (`.horus/research/2026-07-20-x6-boundary-inventory.md`)
found that Horus's machine-read surface is deliberately small and already
funnels through named chokepoints: PRD frontmatter via `resolve_focus` (the
*session contract* — all that resume, dashboard, TUI, and routines consume) and
the backlog card frontmatter schema (the *dispatch contract* — scheduler
admission, `run --card`, the supervise ship-stamp), plus the closure
discipline. Everything else in `.horus/` is model-read prose — workflow policy.
Today that contract is implicit in `frontmatter.py`/`backlog.py`; naming it is
what turns "the engine's API" from an accident into a commitment, and is the
precondition for judging whether any external workflow could maintain it.

## Intended outcome

The contract exists as a named, citable declaration: which fields constitute
the session contract, which schema constitutes the dispatch contract, which
capability tier each unlocks (fabric is the live tier-1 exemplar — full
resume/cockpit value with no cards), and the boundary disciplines that keep the
option open (substrate modules never import workflow modules, `supervise` as
the one named exception; workflow-structure reads go through `resolve_focus` /
the `backlog` parser / `closure`). Future work — and any workflow-compatibility
verdict — can then reference the contract instead of re-deriving it.

## Broad boundaries

Likely a documentation-plus-guard shape: a declaration document (location open)
and possibly a cheap import-boundary check. Early non-goals: no selector,
profile schema, or compatibility adapter; no new runtime behavior; no
restructuring of `frontmatter.py`/`backlog.py` — this names what exists, it
does not redesign it.

## Open decisions for backlog-refine

- Declaration location: `.horus/` doc, repo docs, README section, or docstring
  canon in `frontmatter.py`/`backlog.py`?
- Is the import-boundary discipline worth a deterministic check (controls
  ladder: instruction first — has it ever been violated?), or prose only?
- Do tier names ("session contract" / "dispatch contract") become user-facing
  vocabulary in docs/doctor, or stay internal?

## Source

Raw `vision-branch-x6-workflow-selection-compatibility` card +
`.horus/research/2026-07-20-x6-boundary-inventory.md` (owner-reviewed
2026-07-20).
