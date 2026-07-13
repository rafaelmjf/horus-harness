---
date: 2026-07-13T15:02:27
agent: codex
account: personal
environment: host
project: horus-harness
status: closed
summary: "managed tmux default terminal host v0.0.51"
---

# managed tmux default terminal host v0.0.51

## Summary

Closed the mobile-terminal investigation by making Horus-managed tmux the default
host for TUI-launched sessions on supported runtimes. Shipped and deployed v0.0.51;
the broader terminal UX card remains deliberately deferred until the owner has more
usage evidence.

## Key Points

- The automatic target is now tmux whenever it is installed and Horus is not already
  inside tmux. Native Windows, missing tmux, and nested tmux fall back to the current
  terminal; `HORUS_TERMINAL_TARGET=current|tmux` remains an explicit override.
- Session lists distinguish `attachable` managed-tmux sessions from `original terminal
  only` processes. Non-attachable rows no longer expose misleading Attach/Close actions;
  Horus cannot safely retrofit a persistent terminal around an already-running process.
- Kept scripted `horus open --target window|current|tmux` semantics unchanged. This
  avoids silently changing automation while the interactive TUI gains persistence.
- Live tmux capture showed two managed sessions as attachable and the pre-existing
  Codex session as original-terminal-only. Focused tests passed 28/28; the post-bump
  full suite passed 1,280 tests.
- PR #210 merged at `174105c`; release PR #211 merged at `d628780`. v0.0.51 published,
  three-OS install smoke passed (including native Windows and macOS), and the hosted
  service reports 0.0.51 while `/` remains gated with 403.

## Next

- Owner performs one fresh TUI launch outside tmux, detaches, and reattaches it from
  Sessions. On PASS, return to orphan-process reaping. Do not create the deferred
  terminal UX backlog card until more real usage clarifies it.

## Checkpoints (auto-harvested)

- `174105c` feat: make managed tmux the default terminal host (#210)
- `d628780` chore: release v0.0.51 (#211)
- `c7bb534` Update Horus continuity (closure)
