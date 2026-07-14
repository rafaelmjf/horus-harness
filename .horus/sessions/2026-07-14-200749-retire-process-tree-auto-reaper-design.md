---
date: 2026-07-14T20:07:49
agent: codex
account: personal
environment: host
project: horus-harness
status: closed
summary: "Preserved the guarded process-tree design, closed PR #231 unmerged, and owner-retired the card in favor of exact-handle manual cleanup."
---

# retire process-tree auto-reaper design

## Summary

Reviewed the completed design-only pass for automatic process-tree orphan handling.
The owner judged its cross-platform containment and termination machinery too costly
and risky for the observed incident rate, and accepts manual cleanup when needed.

## Key Points

- Closed draft PR #231 without merging any implementation.
- Preserved the complete proposal under `backlog/archive/process-tree-orphan-reap.md`
  with `status: retired`, the decision rationale, and a concrete promotion trigger.
- Kept exact-handle manual cleanup as current policy; automatic reaping should return
  only if incidents become frequent or manual recovery becomes burdensome.

## Next

- Await owner confirmation before claiming `project-machine-requirements`, the only
  remaining card currently promoted for implementation.
