---
status: open
priority: medium
tier: sonnet
created: 2026-07-12
created_by: owner-session
parallel: exclusive
surface: horus/dashboard.py, horus/assets/vendor/xterm/
---

# Claude Code rendering in the webapp terminal: cheap levers, honest ceiling

**[improvement]** Claude Code's Ink-based TUI re-renders large screen regions per
streaming chunk; xterm.js-family terminals (ours, VS Code's) turn that into flicker
and scrambled frames, while codex's ratatui TUI does differential cell updates and
looks fine in the same viewer. Documented upstream (anthropics/claude-code #18084,
#1913). Anthropic is shipping fixes: differential renderer, `CLAUDE_CODE_NO_FLICKER`
alt-screen mode (#41965 — has scrollback trade-offs, do NOT force it), and
synchronized output (DEC private mode 2026), which eliminates flicker **when the
terminal supports mode 2026**.

## Levers in our control (small, bounded)

1. **Upgrade the vendored xterm.js** (`horus/assets/vendor/xterm/`, vendored 2026-06-26,
   pre-`@xterm`-scope package; `grep -c 2026 xterm.js` → 0, so no synchronized-output
   support). Vendor current `@xterm/xterm` + `@xterm/addon-fit`; verify the new bundle
   handles mode 2026 (grep for it) so Claude's sync-output path actually engages.
2. **On-device renderer check** (owner-only): DOM vs canvas renderer legibility at
   phone DPR — pending from the ux-hardening card's verification gate.
3. Do NOT set `CLAUDE_CODE_NO_FLICKER` globally — it destroys scrollback (#41965);
   re-evaluate per upstream releases.

## Honest ceiling

Beyond these, parity with codex closes upstream (Anthropic's renderer work), not in
`dashboard.py`. Don't chase it here.

## Context: account-split workaround (no build)

Claude mobile app has no multi-account switching across emails (claude-code #36151,
#36017). Zero-build split for the owner: Claude app stays on personal (remote
control), claude.ai in a mobile **browser** holds work simultaneously (separate
session jar). The horus terminal's structural advantage stands regardless: accounts
live server-side, phone is a dumb viewer.

Related: [[mobile-terminal-interaction-regression]], [[mobile-terminal-ux-hardening]].
