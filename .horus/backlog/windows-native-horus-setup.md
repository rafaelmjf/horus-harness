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

## Findings — Windows machine setup run, 2026-07-20 (owner-attended)

The premise "the install is stale" was **false**: it was already 0.0.73, matching
the repo. What was actually wrong was everything around it. Done and verified this
session on the owner's Windows 11 box:

- **Shadowed binary** — a `pip`-installed `horus-harness` 0.0.1 sat in
  `Python312\Scripts` behind the uv shim. `doctor machine` caught it unprompted
  with the right fix. Uninstalled.
- **Accounts** — none existed (`account: null` on every session, auto-generated
  aliases). Now `claude-personal` + `codex-personal` aliased and isolated from the
  live logins, and `claude-work` provisioned + mapped (awaiting one login).
- **Statusline** — was a hand-rolled PowerShell script, so `rate_limits` were never
  recorded and usage was permanently empty **with no error**. Now `horus statusline`
  in ambient `~/.claude` and both isolated accounts.
- **Repos** — workspace consolidated to `C:\Users\Rafa\projects`; horus-harness,
  fabric-metadata-driven-medallion, pbi-ecosystem cloned there and the `projects`
  list repointed.

**Native-Windows capability inventory** (probed, not inferred):

- *Works native:* full CLI core, launch-in-new-window, the TUI (ships a `_WinPty`),
  dashboard/app, tkinter mascot, hooks via Git Bash, statusline + usage recording,
  account isolation, worktrees, `gh`, VS Code tasks, foreground `horus run`.
- *Degrades:* `terminal_sessions.tmux_available()` is hard-`False` on `nt`, so no
  persistent managed sessions, no cross-viewer attach; `--target tmux` and detached
  workers fall back to the current TTY / a new window.
- *Unavailable:* `horus schedule` (needs `systemd --user` timers) — so the whole
  scheduled-dispatch + supervise loop is Linux-only here. `native-windows` as a
  *remote* target stays a deliberate documented gap.
- WSL2 (Ubuntu) **is installed** on this machine, so the tmux/scheduler path is
  available without changing anything if the owner wants it.

This answers the "which features degrade" half of the card. The remaining open
question is the recommendation itself (native vs WSL vs app) — and the owner's
usage so far is local-project work on this machine, not autonomous dispatch, which
points at native-Windows-is-fine, but that is a judgment to confirm, not a finding.

## Source

In-session, 2026-07-20 (owner-flagged as intended next focus). Grounding: the
tmux-persistence rule (Linux/macOS/WSL only) and the three-OS Distribution facet
in `.horus/PRD.md`. Findings section from the attended setup run the same day.
