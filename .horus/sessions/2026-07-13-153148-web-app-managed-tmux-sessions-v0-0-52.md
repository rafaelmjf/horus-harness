---
date: 2026-07-13T15:31:48
agent: codex
account: personal
environment: host
project: horus-harness
status: closed
summary: "web app managed tmux sessions v0.0.52"
---

# web app managed tmux sessions v0.0.52

## Summary

Extended the v0.0.51 managed-tmux default across the Horus web app and shipped
v0.0.52. A web-launched browser or native terminal now views the same persistent
session that `horus tui` can attach, closing the split between launch surfaces.

## Key Points

- In-app project, account quick-launch, and brainstorm flows now create the agent in
  unique managed tmux on supported runtimes, then attach xterm.js through the existing
  PTY stream. Phone launch width seeds tmux itself, preserving the first-paint geometry.
- Web-requested native terminal windows also attach to managed tmux. Native Windows,
  missing tmux, nested tmux, and `HORUS_TERMINAL_TARGET=current` retain the prior direct
  PTY/window behavior; scripted `horus open` semantics remain unchanged.
- Browser/native viewer creation is transactional: if attachment fails after tmux is
  created, Horus kills the new session instead of stranding it. The browser close action
  ends the managed tmux session and updates its registry row.
- A real dashboard `process_launch` probe used the fake adapter plus actual tmux and PTY:
  it opened `tab=pty-1` at 47x24, rendered the pane, registered `launch_target=tmux`, and
  explicit close removed tmux and recorded `exited`. No Claude/Codex tokens were spent.
- Focused tests passed 275; the post-bump suite passed 1,288. PR #212 merged at
  `56bc69f`; release PR #213 merged at `00cb710`. v0.0.52 published, three-OS install
  smoke passed, and hosted deploy reports 0.0.52 while `/` remains gated with 403.

## Next

- Owner launches from the web app, then attaches to that same session from Termius →
  `horus tui` → Sessions. On PASS, return to orphan-process reaping; keep the broader
  terminal UX backlog card deferred until real usage makes its scope clearer.
