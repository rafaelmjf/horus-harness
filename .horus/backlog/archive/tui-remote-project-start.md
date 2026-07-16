---
status: shipped
priority: medium
tier: sonnet
created: 2026-07-15
type: feature
parallel: safe
surface: horus/terminal_tui.py, horus/github_catalog.py, horus/remote_start.py
shipped_pr: 257
shipped_sha: 6c870fa9e31806045ef8a109a24baefc71122bb1
---

# Start remote-only GitHub projects from the terminal TUI

The web dashboard and CLI already discover and start Horus-enabled GitHub projects,
but the terminal TUI lists only locally registered projects. A fresh machine therefore
cannot use the TUI as the complete project launcher until the owner runs `horus start`
out of band.

## Acceptance

- The TUI renders cached remote-only Horus projects without blocking its first paint.
- Selecting one reuses the existing workspace-root, clone, register, projection-refresh,
  and resume primitives; no second remote catalog or clone path is introduced.
- Private repositories continue to use authenticated `gh` access.
- Local, cloned-but-unregistered, remote-only, ignored, and unavailable states remain
  visibly distinct.
- A live terminal-frame probe proves clone/register/start on a disposable repository.

## Execution

Scoped TUI integration after the new repositories exist. The current migrations can
use `horus onboard` / `horus start`, so this is convenience rather than a prerequisite.
