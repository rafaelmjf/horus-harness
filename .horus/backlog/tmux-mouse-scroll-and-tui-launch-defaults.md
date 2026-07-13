---
status: claimed
priority: now
tier: sonnet
created: 2026-07-13
type: bug
parallel: exclusive
surface: horus/terminal_sessions.py, horus/terminal_tui.py, horus/config.py
---

> **PR #215 open, awaiting owner review/merge** (commit `37bbd55`). Run
> `horus backlog ship tmux-mouse-scroll-and-tui-launch-defaults --pr 215 --sha
> 37bbd55efb40cec7e48c7f3277d2750ffc727292` once it merges — do not ship before
> merge (this repo's convention; a card must not carry shipped provenance while
> its PR is still open).

# tmux mouse scroll fix + TUI launch-defaults screen

**[bug]** Owner-reported: launching a live Codex session from `horus tui`, mouse-wheel
up recalled Codex input/history instead of scrolling terminal scrollback, causing
accidental commands and interrupts. `terminal_sessions.launch_tmux` created and
attached a Horus-owned tmux session but never enabled tmux mouse handling for it, so
wheel input reached the agent as raw terminal escape sequences.

Bundled with a related capability requested in the same session: a home-level
Defaults screen in `horus tui` for the launch permission posture new TUI launches
start with (until now there was no way to change it without a CLI/dashboard flag).

Fix: session-scoped `tmux set-option -t <session> mouse on` right after
`new-session` (never `-g`/global), with kill+cleanup on configuration failure;
`config.toml`'s new `[launch]` table (`posture`, default `"default"`) applied to
fresh/resume/card-resume TUI launches via a new `d`-key Defaults screen.

[tier: sonnet implementation, inline] — bounded bug fix + one small screen, no
open design ambiguity; direct implementation matched the scope.
