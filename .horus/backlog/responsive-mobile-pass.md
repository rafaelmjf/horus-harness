---
status: open
priority: medium
tier: sonnet
created: 2026-07-11
parallel: exclusive
surface: horus/dashboard.py, horus/templates.py
---

# Responsive mobile pass

A proper responsive pass over the dashboard for mobile browsers — layout,
touch targets, and the accounts/sessions/project views currently tuned for
desktop widths. Distinct from `pwa-installable` (installability) and
`mobile-terminal-interaction-regression` (a functional bug in the in-app
terminal on mobile) — this card is pure CSS/markup responsiveness.

`parallel: exclusive` — touches `horus/dashboard.py` + `horus/templates.py`
broadly; do not run concurrently with the other mobile-web-app-bundle cards
without checking overlap first.
