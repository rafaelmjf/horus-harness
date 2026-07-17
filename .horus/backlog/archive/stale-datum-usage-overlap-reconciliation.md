---
status: shipped
priority: medium
tier: sonnet
created: 2026-07-16
vision_facet: "Delegation calibration"
type: bug
parallel: safe
surface: horus/datums.py, horus/session_registry.py
shipped_pr: 304
shipped_sha: 393bf3e
---

# Stale datum usage-overlap reconciliation

An old tracked run whose datum never received `completed_at` can overlap every later
run on the same account forever, making sequential workers look concurrent and
permanently confounding otherwise attributable usage evidence.

## Evidence

- Run `ed9395d1-338f-455a-b3ec-978a74fa884a` launched on the work account on
  2026-07-15, has no datum completion, and now has a stale registry row with its
  original PID. Later sequential work-account attempts all reported generic tracked
  overlap even though they did not overlap one another.

## Acceptance

- Usage reports name the exact overlapping peer run IDs and effective intervals
  instead of only saying that another tracked worker overlapped.
- Positive terminal registry/run-event evidence can bound or backfill a missing
  datum completion without treating mere absence, a stale registry, or a dead PID
  alone as proof of the worker's outcome.
- Genuinely live or ambiguous incomplete peers continue to confound attribution;
  unresolved legacy rows have an explicit owner/supervisor remediation path and are
  never silently auto-closed.
- A positively reconciled legacy run no longer poisons all future isolated-account
  readings, while real interval overlap remains confounded.
- Tests cover terminal evidence with missing datum completion, a genuinely running
  peer, missing/ambiguous evidence, and sequential retry attempts whose intervals do
  and do not overlap.
