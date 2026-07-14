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

## Final workflow decision

- The terminal approach is now intentionally split by viewer, not by session substrate:
  browser xterm remains functional, while native iOS Termius over Tailscale is the reliable
  phone viewer. Both reach the same Horus-managed tmux sessions through `horus tui`.
- The owner confirmed the native Termius TUI flow renders, scrolls, and supports multiple
  sessions; tmux prefix/navigation is acceptable for now, with UX improvements deferred
  until repeated use reveals a concrete problem.
- iOS Shortcuts exposed no Termius actions, and Termius gates automatic startup snippets
  behind Pro. The generic `ssh://` + manual-snippet flow was rejected as worse than simply
  opening Termius and entering `horus tui`; a server-side forced-command endpoint would be
  disproportionate complexity for this comfort feature. The chosen entry remains
  `Termius → connect → horus tui`.
- No explicit post-v0.0.52 web-launch → Termius attach/detach result was recorded in the
  session, so that single owner runtime gate remains the honest next step before orphan reaping.

## Checkpoints (auto-harvested)

- `56bc69f` feat: host web-launched sessions in managed tmux (#212)
- `00cb710` chore: release v0.0.52 (#213)
- `48c6286` Update Horus continuity (closure)

- `5babd32` Update Horus continuity (closure)

- `b13bbb9` chore: close PR 215 & 214 post-merge; update Horus continuity
  Both PRs merged and verified by owner. Shipped backlog card tmux-mouse-scroll-and-tui-launch-defaults with PR #215 merge SHA. Updated PRD.md frontmatter to reflect both PRs merged and ready for release cut. Trimmed Shipped section to keep PRD.md under line cap.
  Owner verification: wheel scroll works (scoped to session), global tmux mouse off, launch-defaults screen functional with five choices. Tests green, installed-package probe passed.
- `22a88e1` fix: update shipped backlog card to reflect PR #215 merged and owner verification
  Replace stale 'PR open, awaiting review' text with accurate ship record: PR #215 merged at 86f433bce2a1b9e71cf103ea1eba4ea476ffc03d. Record owner live verification gates: TUI-launched session wheel scroll working (scoped to session), global tmux mouse off, launch-defaults screen with five choices functional.
- `6c195da` Merge pull request #216 from rafaelmjf/chore/close-pr-215
  chore: close PR 215 & 214 post-merge; update Horus continuity
