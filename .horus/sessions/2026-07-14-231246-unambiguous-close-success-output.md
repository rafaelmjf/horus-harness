---
date: 2026-07-14T23:12:46
agent: codex
account: personal
environment: host
project: horus-harness
status: complete
summary: "Made acting close render one unambiguous recomputed final verdict instead of stale pre-action warnings followed by success."
---

# unambiguous close success output

## Summary

Fixed the repeatedly observed `horus close --commit --push` contradiction: the
command committed and pushed successfully but retained warnings describing the
tree before its own mutation.

## Key Points

- Acting close now runs `commit_continuity` first, then computes and prints the
  complete closure status exactly once.
- Non-acting `horus close` retains its existing read-only behavior.
- Residual hook edits, failed/unpushed checkpoints, and unsuccessful/no-op
  commits remain visible because the full final state is still recomputed.
- Added ordering/output unit regressions plus a real git + bare-origin test: a
  dirty continuity repo commits and pushes, names the checkpoint, contains no
  stale dirty/action-needed text, and finishes clean and synchronized.
- Verification: all targeted close tests passed; full suite passed with 1,447
  tests.

## Next

- After merge, ask the owner before claiming `project-machine-requirements`.

## Checkpoints (auto-harvested)

- `4d56b56` fix: report final close state after checkpoint
