---
status: claimed
priority: high
tier: sonnet
type: bug
created: 2026-07-11
parallel: safe
surface: horus/dashboard.py, horus/terminal_tui.py, tests/test_dashboard.py, tests/test_terminal_sessions.py
---

> Prioritized 2026-07-14 (owner triage): confirmed, permanently user-invisible control
> with a one-line scoped CSS fix. Include in the high-value pre-release correctness
> batch immediately after model-roster reconciliation.
>
> Expanded by owner 2026-07-14: the TUI must also expose an explicit manual refresh
> command so cached account usage can be re-read without recreating the TUI frame.

# Accounts strip "refresh (cached)" button is invisible on every viewport

**[bug]** Found incidentally during the `responsive-mobile-pass` audit — not a
responsiveness issue (identical on desktop and mobile, same computed CSS
either way). The accounts strip's "refresh (cached)" button (shipped in PR
#150, `usage-refresh-button` card) reuses the `.icon-btn` class for
convenience. `.icon-btn` is `opacity:0` by default and only revealed via
`.alias-edit:hover .icon-btn` / `.alias-in:focus+.icon-btn` — a tiny
hover-to-reveal affordance designed for the inline alias-edit checkmark. The
refresh button isn't nested under `.alias-edit` and nothing else in
`_STYLE` sets its opacity back to 1, so it renders as a permanently invisible
23x23px box next to "Accounts" in the summary row (confirmed visually via a
Playwright screenshot at both desktop and phone widths — no button/icon
visible at all).

The web fix is a one-line CSS scope (give the refresh button its own class, or add
an opacity:1 override scoped to it). The TUI slice adds a visible key command that
re-reads the same cache-only usage source, refreshes the account list, and updates
the current frame without making a live provider request. This did not fold into the
`responsive-mobile-pass` PR since it's a functional bug, not a layout one,
mirroring how `mobile-terminal-interaction-regression` stays a separate card
from that same PR's scope.

## Verification

- Web Accounts-strip markup carries a scoped always-visible refresh class at desktop
  and phone widths; alias-edit buttons retain their hover/focus behavior.
- The TUI footer advertises the manual usage-refresh key on account-bearing screens;
  invoking it re-reads cache-only account usage, preserves a valid selection, reports
  success in-frame, and never calls live Claude/Codex usage endpoints.
- Focused dashboard/TUI tests, full CI, and live renderer probes pass.

`parallel: safe` — localized CSS and TUI input/state edits with no shared data-format
change, but check current in-progress claims on either implementation file first.
