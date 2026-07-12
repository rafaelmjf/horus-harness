---
date: 2026-07-12T18:52:09
agent: claude
account: personal
environment: host
project: horus-harness-wt-feat-dashboard-reload
status: complete
summary: "Implemented the dashboard reload and app-child respawn path; PR pending."
---

# dashboard reload path

## Summary

Implemented the scoped dashboard reload path on `feat-dashboard-reload`.

## Key Points

- `horus dashboard --reload` identifies a Horus backend through `/health`, terminates it, and starts current installed code on the same host/port. `/health` now reports `exposed`, so an exposed backend restarts with `--exposed`; the Cloudflared tunnel is untouched.
- `horus app` now polls its own dashboard child and respawns it after a crash or kill. It never takes ownership of a dashboard it merely adopted.
- Stale-build/self-update copy now names `horus dashboard --reload` as the non-blocking action after an install/version change.
- Added CLI, lifecycle, health, and nudge tests. `uv run pytest -q` passed: 1221 passed.
- Live probe on port 8871: `/sessions` served `reload-probe: BEFORE`, then a markup edit plus `uv run horus dashboard --port 8871 --reload` served `reload-probe: AFTER`; PID changed `3716581 -> 3717323`. The temporary marker and probe server were removed.

## Next

- PR #175 is open against `main` (not merged). After rebasing onto then-current `origin/main`, required CI on `daab63c` passed: freshness, pytest (3.12), and pytest (3.13).
