---
title: "[bug] Server-side auto-merge bypasses the continuity freshness gate"
status: open
priority: high
tier: sonnet
parallel: safe
type: bug
surface:
  - .github/workflows/continuity.yml
  - horus/cli.py
created: 2026-07-12
created_by: overseer
migrated_from: rafaelmjf/horus-agent
---

# Server-side auto-merge bypasses the continuity freshness gate

Migrated from horus-agent during its fleet-curator consolidation.

`gh pr merge --auto` queues the real merge on GitHub, so the local pre-merge
hook never sees it. The current CI continuity workflow is advisory, which lets
server-side merges land while project continuity is stale. The same local hook
also matches command text containing `gh pr merge`, so it over-fires on prompts
that merely mention a merge.

Move the real invariant to a required PR check that server-side auto-merge cannot
skip. Keep a precise local fast-feedback signal, but do not infer a merge action
from arbitrary command-string substrings. Verify both directions: stale
continuity blocks queued auto-merge, while a worker prompt mentioning the command
does not block.
