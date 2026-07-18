---
status: shipped
priority: low
created: 2026-07-18
vision_facet: "Dashboard / cockpit"
phase: converge
tier: sonnet
type: feature
parallel: safe
created_by: owner
surface: horus/config.py (launch defaults), horus/terminal_tui.py (launch target), horus/terminal_sessions.py (tmux target/window), the `d` Defaults pane
shipped_pr: 332
shipped_sha: aeaf7367f501a5b64a08acbbbe3e00c504b58cae
---

# tui-launch-session-new-window-default — Defaults option: launch sessions in a new window

**Why (owner, 2026-07-18):** launching a session from `horus tui` currently **takes over the
terminal** — you can `Ctrl-b d` detach back to the TUI, but the session and the TUI share one
window. On **desktop**, being able to launch a session into a **new window by default** (TUI
stays put, session opens beside it) is useful — multiple terminal windows is the natural
desktop workflow. Make it a **Defaults** option (how sessions launch), alongside the existing
launch posture / continuity granularity in the `d` pane.

## The desktop / mobile tension (owner, 2026-07-18)

- **Desktop:** a new window per session is good — parallel windows, TUI stays live.
- **Mobile:** a new window is likely *worse*; the existing **attach/detach** flow (one window,
  `Ctrl-b d` back to the TUI, re-attach) fits a phone better.

So the option should be **platform-aware**: default to new-window on desktop where a real window
manager / multi-window terminal exists, and keep attach/detach on mobile (narrow / SSH-into-tmux
contexts). Decide (in-card) whether this is one tri-state default (`new-window` | `takeover` |
`auto`) with `auto` resolving per platform, or a plain toggle that is simply ignored on mobile.

## How (stays TUI-thin — existing rule)

- A new launch Default in `config.load_launch_defaults()` + a row in the `d` Defaults pane
  (same pattern as posture / continuity granularity).
- Reuse the existing session-target machinery — `--target` and the Horus-managed tmux session
  (`terminal_sessions`) already distinguish `current` vs a managed tmux session/viewer. "New
  window" = spawn/attach the managed session in a new terminal window (the `_spawn_watcher` /
  native-window path already opens terminals) rather than taking over the current one.
- No new session/state path; the option only chooses an existing launch target.

## Acceptance

- A Defaults row toggles how a TUI-launched session opens; on desktop, "new window" opens the
  session beside the TUI (TUI stays live) instead of taking over.
- Mobile / no-window-manager contexts fall back to the attach/detach behavior, never a broken
  new-window attempt (the platform-aware resolution).
- A live probe on desktop confirms the new-window launch; the default is byte-identical to
  today when unset.

## Non-goals

- Not a new terminal multiplexer or window manager — reuse the existing tmux/native-window
  target machinery.
- No change to the mobile Termius → `horus tui` → attach/detach entry (that stays the reliable
  phone path per the Rules).
