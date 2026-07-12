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

> **DEFINITIVE FINDING (2026-07-13, headless end-to-end repro):** with the whole
> stack proven correct (smallest-wins registry, epoch handshake, lazy reset —
> v0.0.42; PTY verified 38×34 via TIOCGWINSZ), **Claude Code paints a ~80-col
> minimum regardless of PTY size** — welcome banner, status line, paragraphs all
> overflow a 38-col phone grid (mid-word wraps + orphan right-edge glyphs).
> **codex at the same 38 cols in the same viewer renders clean.** Also: Claude's
> trust prompt never repaints on SIGWINCH (painted once at spawn size), and
> post-trust Claude runs alt-screen + DEC 2026. Repro harness:
> scratchpad phone-shot.mjs pattern — local ungated dashboard + real agent
> session + phone-emulated CDP screenshots. Remaining options are product
> decisions: (B) 80-col floor + horizontal pan on phone for claude sessions,
> (C) per-agent min-cols (codex keeps native fit), (D) claude-on-phone via the
> Claude app / remote control and webapp terminal for codex+monitoring,
> (E) upstream issue / newer claude versions. Decide before building.
>
> **OWNER COUNTER-DATUM (2026-07-13 ~00:20, investigate FIRST):** a session
> launched from the **accounts menu** (ambient, home dir — in-app terminal,
> since the hosted service is headless) rendered WELL on the phone, while
> project-card sessions looked broken. Hypothesis: claude at 38 cols is
> *conditionally* fine when the phone is the SOLE viewer from birth (its claim
> lands before claude's first paint), and the ~80-col overflow is limited to
> fixed-width elements (welcome banner, statusline) + anything painted before
> the claim. If confirmed, the practical fix may be much cheaper than pan/floor:
> a spawn-size hint from the launching client (so claude's first paint already
> targets the phone grid), or simply documenting the "launch from the phone,
> view solo" recipe. Reproduce with the headless phone harness (session note 2026-07-13:
> `phone-shot.mjs`) comparing sole-viewer-from-birth vs late-attach.

**[improvement]** Claude Code's Ink-based TUI re-renders large screen regions per
streaming chunk; xterm.js-family terminals (ours, VS Code's) turn that into flicker
and scrambled frames, while codex's ratatui TUI does differential cell updates and
looks fine in the same viewer. Documented upstream (anthropics/claude-code #18084,
#1913). Anthropic is shipping fixes: differential renderer, `CLAUDE_CODE_NO_FLICKER`
alt-screen mode (#41965 — has scrollback trade-offs, do NOT force it), and
synchronized output (DEC private mode 2026), which eliminates flicker **when the
terminal supports mode 2026**.

## Levers in our control (small, bounded)

1. ~~**Upgrade the vendored xterm.js**~~ **DONE (2026-07-12):** vendored
   `@xterm/xterm` 6.0.0 + `@xterm/addon-fit` (mode-2026 synchronized output
   confirmed in the bundle; same UMD globals; full CDP harness green). Same
   session also fixed the on-phone scramble root cause: compact-mode
   `fontSize: 16` (iOS zooms the page on focusing an input under 16px — xterm's
   helper textarea carries the cell font, shearing the grid) and moved scroll
   containment onto `.xterm-viewport` (the actual scroller) with
   `touch-action: none` on the host.
2. **On-device check** (owner-only): legibility + touch-scroll behavior at phone
   DPR after the 6.0.0/fontSize/containment deploy — pending owner.
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
