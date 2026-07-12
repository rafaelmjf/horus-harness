---
status: open
priority: medium
tier: sonnet
type: feature
created: 2026-07-12
created_by: overseer
parallel: true
surface: horus/dashboard.py
shipped:
---

# Dashboard tab: full model-roster research + table + refresh button

**Owner ask (2026-07-12):** keep the CLI concise (`concise-cli-matrix-output`) and put
the FULL picture in the dashboard — a section/tab where the latest research + the
complete table are displayed with more detail per model, plus a button to trigger the
research refresh via a headless agent run.

## Scope

- A new dashboard section/tab (`/models` or a tab on an existing page) rendering the
  full roster from `capabilities.toml` + `datums.json`: per model — tier, price
  (in/out), capability summary AND full note, `researched_at`, availability/lifecycle,
  datum record (clean/nudged/bounced/died counts + recent outcomes), owner subjective
  notes (when `model-ranking-synthesis` adds them), and the ranking once it exists.
- **Include a legend** for the datum outcome vocabulary (clean/nudged/bounced/died) so
  the detail view is self-explanatory (the reason it's pulled from the CLI table).
- **Refresh button → headless agent run.** A user-initiated button that launches a
  headless research agent to re-run the web-research pass and write updated priors.
  Route it through the existing **LaunchBackend seam** (do NOT invent a new launcher).
  This is USER-TRIGGERED and one-shot — NOT a scheduler/daemon (anti-drift boundary:
  the moment this wants a cron/auto-refresh, STOP; the >14d staleness nudge stays the
  passive signal, the button stays the active trigger).

## Boundaries / overlap

- Same file as `mobile-terminal-legibility` / `mobile-terminal-interaction-regression`
  (`dashboard.py`), but a DIFFERENT region (a new tab, not the xterm terminal) — additive,
  coordinate to avoid a merge clash but not mutually exclusive.
- Display + owner-triggered refresh only; nothing here auto-picks or auto-routes a model.

## Depends on / feeds

Reads the same sources as `capabilities --matrix`. Best after `concise-cli-matrix-output`
(clean CLI/dashboard split) and alongside `model-ranking-synthesis` (so the tab can show
the ranking). Availability + benchmark signals surface here as they land.

## Verification

The tab renders the full roster from fixture priors+datums; the outcome legend shows; the
refresh button launches a headless run through LaunchBackend (mock the backend in test)
and does NOT block the request; no auto/scheduled refresh exists. CI green + an overseer
live probe of the rendered tab.
