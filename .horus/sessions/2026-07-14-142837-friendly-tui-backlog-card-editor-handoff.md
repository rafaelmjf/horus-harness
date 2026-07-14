---
date: 2026-07-14T14:28:37
agent: claude
account: personal
environment: host
project: horus-harness
status: closed
summary: "Diagnosed vi fallback as the broken-feeling card editor UX; friendly external-editor handoff shipped in PR #219 at b6f75ea."
---

# Friendly TUI backlog-card editor handoff

## Summary

Owner reported that backlog-card editing swallowed letters, would not close, and
printed `B` while scrolling. The TUI was correctly suspending itself, but with
VISUAL/EDITOR unset it silently launched modal `vi`; two leftover `.swp` files
corroborated interrupted vi sessions. Implemented a bounded UX fix on
`fix/tui-friendly-editor-fallback` at `cb87ace` and pushed it.

## Key Points

- Execution decision: inline, no worker. This was localized debugging; dispatch
  overhead would exceed the change, especially at the usage ceiling. Live model
  calibration showed sonnet-5 as the matched scoped tier (26/29 clean datums).
- Unix now prefers `nano` when no editor is configured, retaining `vi` only when
  nano is unavailable. VISUAL/EDITOR and Windows Notepad behavior remain intact.
- Before handoff Horus names the external editor and shows editor-specific keys
  to save/return; vi fallback now explains insert, `:wq`, and `:q!` explicitly.
- Gate reproduced locally: focused editor set 9 passed; full suite 1367 passed;
  live PTY probe displayed the guidance, opened real GNU nano, and Ctrl+X returned
  cleanly. The user's real-terminal eyeball remains the runtime acceptance gate.
- `horus backlog ship datum-supervisor-cost-envelope --pr 218 --sha 8dbb599...`
  corrected a pre-existing lingering-done continuity signal during consolidation.

## Next

- PR #219 merged at `b6f75ea`; required PR checks and merge-SHA CI passed on
  Python 3.12/3.13. Owner-check `e` on a real backlog card after install/release.
- `tui-capabilities-screen` and the pending release cut remain next afterward.
