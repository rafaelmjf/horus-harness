---
status: needs-decision
priority: low
tier: sonnet
created: 2026-07-11
parallel: exclusive
surface: horus/dashboard.py
---

# Manual usage-refresh button (needs-decision)

A manual "refresh usage" affordance in the dashboard's accounts strip/panel.

**Needs a scope decision before implementation:** a *real* refresh for Codex
means triggering an actual CLI turn (real token cost — Codex has no live usage
API, only last-observed rate limits from rollout events), whereas a *cheap*
refresh is just re-reading the existing cache/rollout files (no new cost, but
may not surface anything newer than what's already on disk). Claude's usage
already comes from a live OAuth call on every dashboard load (see
`usage-reset-inference`, shipped), so a manual refresh button there would be
close to a no-op. The owner must choose which of these (or both, distinguished
in the UI) before this card is implemented — do not build silently defaulting
to the expensive option.

`parallel: exclusive` — touches the same accounts-strip/panel rendering as
`usage-reset-inference` (shipped) and other mobile-web-app-bundle cards.
