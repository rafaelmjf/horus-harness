---
date: 2026-07-14T22:50:25
agent: claude
account: personal
environment: host
project: horus-harness
status: complete
summary: "Made continuity freshness a required server-side merge gate and removed local command-string false positives."
---

# required server-side continuity freshness gate

## Summary

Fixed both directions of the migrated defect: queued GitHub auto-merge could
bypass an advisory continuity workflow, while the local PreToolUse hook could
block a worker prompt that merely mentioned the merge command.

## Key Points

- Added `closure.pr_diff_freshness`: source/product changes relative to a fetched
  base ref must include canonical PRD (or v2 lane) continuity; continuity-only
  PRs remain valid and an unreadable base fails closed.
- Added `close --check --base-ref` as the canonical workflow entry point.
- Removed every advisory fallback from `.github/workflows/continuity.yml`; the
  `freshness` job now returns the real gate status.
- Replaced raw substring matching with shell tokenization: actual commands at the
  start or after `&&`/`;`/newlines are recognized, while quoted prompt text and
  malformed shell strings pass through.
- Verified branch protection previously required only Python 3.12/3.13 pytest;
  this session adds `freshness` as a required context before merge.
- Gate: 1,446 tests passed, including PR-diff, matcher, CLI, and workflow
  regressions. A temporary stale auto-merge PR after landing is the live proof.
- Archived the two oldest already-distilled session notes locally after the
  deterministic hygiene signal reported 14 active notes; 12 remain.

## Next

- After live stale-auto-merge proof, ask the owner before starting
  `close-commit-output-contradicts-success`.
