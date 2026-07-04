---
date: 2026-07-04T08:52:34
agent: claude
account: personal
environment: host
project: horus-harness
status: closed
summary: "v3 controls migrated and v0.0.21 release"
---

# v3 controls migrated and v0.0.21 release

## Summary

Continued the v3-tooling execution plan after fetching and verifying remote state.
Merged PR #104 and PR #105, migrated both control repos to the PRD+sessions structure,
refreshed their Horus projections, and prepared the v0.0.21 release bump.

## Key Points

- PR #104 merged after reproducing its worktree gate: `uv run pytest -q` in
  `/home/rafa/projects/hh-wt-phase4` passed 710 tests. Local branch deletion failed
  only because the phase-4 worktree still has the branch checked out.
- PR #105 merged after reproducing its gate on `main`: `uv run pytest -q` passed 711
  tests before the merge path, then 716 tests passed on merged `main`.
- `agentic-gym-coach` migrated and pushed at `56c6c60`; `agentic-ttrpg` migrated and
  pushed at `d870b15`. Both migrations created `.horus/PRD.md`, moved six old lanes
  into `.horus/archive/`, and preserved archived lane bytes exactly.
- Polished both generated PRDs, refreshed managed AGENTS/CLAUDE blocks and bundled
  project skills, then verified `horus resume` and `horus close --check` green for
  both repos. Dashboard `/projects-grid` and detail pages read the PRD NEXT/focus and
  no longer flag outdated artifacts after projection refresh.
- Release bump followed the three-file rule: `pyproject.toml`,
  `horus/__init__.py`, and `uv.lock` now say 0.0.21. Full suite rerun after the bump:
  716 passed.

## Next

Top ordinary backlog candidate is catalog niceties: badge private repos in the GitHub
catalog and add an "N ignored" affordance on the untracked fold.

## Summary

What this session set out to do and what happened.

## Key Points

- ...

## Next

- ...
