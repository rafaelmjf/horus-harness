---
title: "TUI fleet projection sync"
status: shipped
priority: now
tier: sonnet
parallel: unsafe
type: feature
surface: horus/terminal_tui.py, horus/projection_sync.py
created: 2026-07-15
created_by: owner
shipped_pr: 240
shipped_sha: 470db96
---

# TUI fleet projection sync

Make cross-project Claude/Codex projection drift visible from the terminal
cockpit after a large Horus shipping campaign. Render the existing
`projection_sync.sync_state` result for every registered local project; do not
create another comparison or update path.

## Acceptance

- Home shows a Projection Sync entry with a stale/unknown project count.
- A dedicated screen lists each project and its Claude/Codex status relative to
  the installed CLI.
- When the registered `horus-agent` curator workspace is available, the screen
  can launch it with a bounded prompt naming the stale projects and requiring
  fetch/branch/PR discipline in each target repository.
- The screen is read-only until the owner deliberately launches the curator;
  it never mass-writes dirty target worktrees.
- Narrow and wide TUI renderers expose the same canonical report.

## Execution

Inline, Sonnet-class scoped implementation. Live calibration: Sonnet 5 is the
scoped-implementation lead with 27/31 measured clean datums and a clean recent
streak. Verify with required CI plus a live TUI frame probe.
