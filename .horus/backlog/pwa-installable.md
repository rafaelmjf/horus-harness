---
status: open
priority: medium
tier: sonnet
created: 2026-07-11
parallel: exclusive
surface: horus/dashboard.py, horus/assets
---

# Make the dashboard installable as a PWA

Add `/manifest.json` + a service worker so the hosted dashboard can be installed
as a browser app on mobile/desktop. HTTPS is already satisfied by the Cloudflare
tunnel (exposed mode), so the remaining work is the manifest (icons, name,
start_url, display: standalone) and a minimal service worker (cache-first or
network-first shell, per the dashboard's read-mostly/async-panel contract —
must not cache stale account/session data past its TTL).

`parallel: exclusive` — touches `horus/dashboard.py` route registration; do not
run concurrently with `mobile-terminal-interaction-regression` or
`responsive-mobile-pass` without checking overlap first.
