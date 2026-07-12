---
date: 2026-07-12T18:48:40
agent: claude
account: personal
environment: host
project: horus-harness-wt-fix-codex-usage-account-scope
status: completed
summary: "Corrected Codex rate-limit scope and added stale-window protection."
---

# Fix Codex usage account scope

## Summary

Fixed `horus usage check` so project-scoped context stays local while 5h/weekly
limits use the newest account-wide Codex rollout. Expired reset windows now display
as stale rather than current capacity.

## Key Points

- `usage_snapshot.py` already used the account-global Codex reader, so no change was needed.
- Added CLI coverage for a stale project snapshot versus a newer account snapshot, plus a stale-window guard test.
- Verified `uv run pytest -q` (1220 passed) and live `uv run horus usage check --path .`.

## Next

- Push this branch, open the requested PR against `main`, and wait for required CI; do not merge.
