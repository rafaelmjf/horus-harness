---
title: "Remote-authoritative fleet review + optional TUI curator entry"
status: claimed
priority: now
tier: sonnet
parallel: exclusive
type: feature
surface:
  - horus/fleet_review.py
  - horus/cli.py
  - horus/terminal_tui.py
  - horus/skills.py
created: 2026-07-14
created_by: user
---

# Remote-authoritative fleet review + optional TUI curator entry

Keep horus-agent as a thin, Git-synchronized fleet-curator workspace for
multi-machine use, while placing every reusable behavior in horus-harness.

## Acceptance

- `horus fleet --review` discovers the shared path-free manifest, fetches local
  clones, and reads `origin/<default>` through Git objects without pulling or
  changing a target worktree.
- The result names remote shipped continuity separately from local working state,
  includes active backlog and capability summaries from the remote PRD/cards, and
  flags source commits newer than the remote continuity commit.
- A manifest project missing locally uses authenticated, read-only GitHub access
  when available and degrades to an explicit unavailable row when it is not.
- JSON and human output share one canonical data model; there is no ranking,
  auto-archive, auto-dispatch, or model selection.
- The TUI keeps direct project launch as the default, adds an explicit Fleet
  Review screen rendered from the same model, and can start the registered
  `workspace_role: fleet-curator` project as an ordinary resume launch.
- Bundle a concise `fleet-curation` workflow skill that requires owner approval
  before cross-project continuity cleanup and routes source work into the target
  project's normal branch/PR workflow.

## Execution

Inline Sonnet-shaped implementation: the data contract needs to stay coherent
across CLI and TUI, while the surfaces themselves are bounded. Gate with targeted
unit tests, the full suite, a live `horus fleet --review` probe, and an owner TUI
eyeball after merge/install.
