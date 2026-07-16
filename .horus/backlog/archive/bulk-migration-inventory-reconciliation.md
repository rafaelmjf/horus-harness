---
status: shipped
priority: high
tier: sonnet
created: 2026-07-15
type: feature
parallel: safe
surface: horus/doctor_machine.py, bundled dispatch/migration skills, new horus/verify_inventory.py (or equivalent helper)
shipped_pr: 254
shipped_sha: b94099e
---

# Bulk-migration inventory reconciliation (empty-walk-is-an-error)

Three of the four Drive-to-Git migrations relied on copying a source tree into a repo.
Twice a directory walk **silently returned empty for a non-empty directory** (a flaky
`gio list` on a large `Assets/` folder), which would have dropped all 24 archived PBIX
files. It was caught only because a manual staged-count vs produced-count reconciliation
disagreed. The general lesson outlives Drive: any bulk copy/migration must reconcile
counts + sizes both directions, and a walk that yields zero for a container known to be
non-empty must be treated as a failure to retry, not as "empty."

## Acceptance

- A reusable reconciliation helper compares a source manifest (path, size) against the
  produced/committed set both directions and reports: source-not-produced,
  produced-not-source, and size mismatches — with a non-zero exit on any discrepancy.
- The helper is byte/encoding-robust (e.g. names containing `§`, spaces, unicode) and
  compares by a stable key, not shell-quoted strings.
- An "empty result for a container expected to be non-empty" is an explicit error state
  the caller must handle (retry), not a silently-accepted empty set.
- The dispatch/migration skills document reconcile-by-count-and-size as a required step
  before declaring any bulk copy complete, and reference this helper.
- Tests cover a clean 1:1 reconcile, a dropped-file case, an extra-file case, a
  size-mismatch case, and a non-ASCII filename set.

## Boundaries

- Generic file-tree reconciliation; no Google-Drive/gvfs-specific code in the harness
  (that stays an agent-side staging technique). This solves the *verification* gap, not
  the transport.
- Advisory/observable: it reports and exits non-zero; it does not auto-fix or re-copy.
