---
status: open
priority: medium
tier: sonnet
created: 2026-07-11
parallel: safe
surface: horus/dashboard.py
---

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

Fix is a one-line CSS scope (give the refresh button its own class, or add
an opacity:1 override scoped to it) — did not fold into the
`responsive-mobile-pass` PR since it's a functional bug, not a layout one,
mirroring how `mobile-terminal-interaction-regression` stays a separate card
from that same PR's scope.

`parallel: safe` — one-line CSS fix, low overlap risk with other
`horus/dashboard.py` cards, but check current in-progress claims on that
file first per the parallel-safety gate.
