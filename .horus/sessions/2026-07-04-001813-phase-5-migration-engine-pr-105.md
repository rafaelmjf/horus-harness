---
date: 2026-07-04T00:18:13
agent: codex
account: personal
environment: host
project: horus-harness
status: in-progress
summary: "Phase 5 migration engine PR 105"
---

# Phase 5 migration engine PR 105

## Summary

Resumed the v3-tooling execution plan as supervisor after `git fetch --all --prune`
and branch/upstream verification. PR #104 was still open with no review decision, so
it was not merged. Implemented Phase 5 directly on `feat/v3-migration-engine` and
opened PR #105.

## Key Points

- Added `horus upgrade-project --structure prd` as an opt-in six-lane to PRD+sessions
  migration path, separate from the existing projection refresh default.
- Migration generates `.horus/PRD.md`, moves existing v2 lane files into
  `.horus/archive/` without rewriting their bytes, preserves `sessions/` and `temp/`,
  and leaves an `Agent-polish TODO` marker in the generated PRD.
- Apply mode refuses before writing when the target git tree is dirty or behind its
  upstream after `git fetch --all --prune`.
- Reproduced gates: `uv run pytest tests/test_cli.py -q` (79 passed) and
  `uv run pytest -q` (711 passed).
- Rehearsed on a scratch clone of `agentic-gym-coach`: dry-run/apply succeeded; all six
  archived lane files compared byte-identical to the original HEAD contents. The first
  rehearsal exposed checked roadmap item continuation text leaking into Backlog; fixed
  it and reran the suite + scratch rehearsal.

## Next

- Rafa visually accepts/merges PR #104 if the dashboard detail page is good.
- Review/merge PR #105, then mark phases 4 and 5 accepted in `.horus/execution.md`.
- Run Phase 6: migrate `agentic-gym-coach` and `agentic-ttrpg`, polish generated PRDs,
  rerun the cold-reader quiz + `close --check`/dashboard gates, then release v0.0.21.
