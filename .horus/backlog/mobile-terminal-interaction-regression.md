---
status: folded-in
priority: high
tier: sonnet
created: 2026-07-11
parallel: exclusive
surface: horus/dashboard.py, horus/pty_host.py, horus/pty_session.py
folded_into: mobile-terminal-ux-hardening
---

> **FOLDED IN (2026-07-12) → `mobile-terminal-ux-hardening.md`** (symptom 2), but
> kept as the **distinct** root-cause track: the diagnosis session determined this is
> the exposed-mode / Cloudflare-Access / same-origin POST-path family, **not** the
> sizing/lifecycle cluster the redesign targets, and it did not reproduce in the
> headless sizing harness (no auth gate there). Investigate the `/pty/input` POST
> path on the exposed host separately. History kept for provenance. See
> `docs/terminal-mobile-desktop-diagnosis.md` §4.

# Mobile terminal accepts no input on the hosted/mobile app

**[bug]** The in-app terminal (`target=='app'`, `pty_host.host.start` path) accepts
no keyboard input on the hosted/mobile dashboard, though it worked days ago. Prime
suspects, in rough recency order: the exposed-mode/Cloudflare-Access commits
(`662f155`, `e4fb8fd`) and the rejected-input change (`36412bf`) — any of these
could have broken the input event path (same-origin POST guard, SSE/keystroke
wiring, or an access-gate check firing on the PTY input route). Reproduce on the
hosted/exposed dashboard specifically; the desktop/local `horus app` terminal is
not confirmed broken and may be a useful differential.

`parallel: exclusive` — shares `horus/dashboard.py`, `horus/pty_host.py`,
`horus/pty_session.py` surface with any other card touching the in-app terminal;
do not run concurrently with `pwa-installable` or `responsive-mobile-pass` without
checking overlap first.
