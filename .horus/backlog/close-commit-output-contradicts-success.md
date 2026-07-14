---
title: "[bug] close --commit --push reports stale action after succeeding"
status: claimed
priority: medium
tier: sonnet
parallel: safe
type: bug
surface:
  - horus/cli.py
  - horus/closure.py
created: 2026-07-13
created_by: overseer
migrated_from: rafaelmjf/horus-agent
---

# close --commit --push reports stale action after succeeding

Migrated from horus-agent during its fleet-curator consolidation.

Repeatedly reproduced: `horus close --commit --push` commits and pushes, yet
prints pre-commit dirty/stale warnings and ends with “Action needed.” The output
describes the tree before the command's own successful mutation.

Make success and failure visually unambiguous. For an acting close, either defer
the freshness verdict until after commit/push or suppress the pre-action warning
and render the recomputed final state. The gate is a dirty continuity repo:
successful output names the checkpoint and contains no stale/action-needed tail.
