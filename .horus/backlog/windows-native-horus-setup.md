---
status: open
priority: high
created: 2026-07-20
created_by: owner
last_refined: 2026-07-20
readiness: shaping
readiness_reason: "Exploratory — the alternatives (WSL2 / native Windows / native app) are not yet assessed against the recent TUI features; owner-flagged as intended next focus, promote to Ready after a refine pass."
phase: explore
type: spike
vision_facet: "Distribution"
---

# windows-native-horus-setup — the best way to run horus on Windows, given the TUI's recent growth

## Why

The owner has horus installed on their Windows machine but it has been **stale for
a while**, and the last several releases added a lot of **TUI** capability that may
not be cleanly Windows-native — most of it assumes tmux, which horus only uses for
managed/persistent sessions on **Linux/macOS/WSL** (native Windows keeps the direct
host: no managed tmux, so no session persistence, no cross-viewer attach, no
`horus open --target`). The owner wants to know, exploratorily, what the right
Windows setup actually is before sinking time into either upgrading in place or
changing surfaces.

## Intended outcome

A clear recommended Windows setup for the owner (and documentable for other
Windows users), backed by an explicit list of which recent TUI features work
native, which degrade, and which need WSL — plus a decision on whether to invest
in native-Windows TUI parity or steer Windows users to WSL and/or the native app.

## Broad boundaries

An investigation that lists and assesses the alternatives, not an implementation.
The candidates to weigh:

- **WSL2** — full Linux parity: tmux persistence, managed sessions, every TUI
  feature works; cost is the WSL layer and the Windows/Linux filesystem boundary,
  and GUI/native-app things live on the Windows side.
- **Native Windows (Windows Terminal / PowerShell)** — the CLI is a three-OS
  target and runs; the question is exactly which TUI features degrade (tmux
  persistence, attach, cross-viewer) versus fail versus work fine (the `fcntl`
  lazy-import and Git-Bash hook path already exist). Enumerate this concretely.
- **Native app on Windows** — cross-links `native-app-account-launch-spike`:
  possibly the best Windows path is the desktop app rather than the TUI at all.
- **Git Bash / MSYS** middle ground (hooks already run through Git Bash on
  Windows) — is there partial tmux/persistence there, or not worth it.

First step regardless: get the stale install current (version floor;
`uv tool install --force --refresh --python 3.12`, never `uv tool upgrade
--reinstall`) so the assessment runs against real current behavior.

Non-goals: not committing to native-Windows TUI feature parity as an outcome (that
is one possible conclusion, not the premise); no new Windows-only runtime.

## Open decisions for backlog-refine

- The recommended default setup, and whether it differs for "owner's machine"
  vs "any Windows user."
- Invest in native-Windows TUI parity, or explicitly steer Windows to WSL / the
  app and document the native-Windows TUI as best-effort.
- Whether this stays one exploratory card or splits into (a) the stale-install
  upgrade + compat inventory and (b) any parity work that inventory justifies.

## Source

In-session, 2026-07-20 (owner-flagged as intended next focus). Grounding: the
tmux-persistence rule (Linux/macOS/WSL only) and the three-OS Distribution facet
in `.horus/PRD.md`.
