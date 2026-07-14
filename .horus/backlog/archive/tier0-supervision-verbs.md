---
title: "Tier-0 supervision verbs: merge-watch, reinstall-verify, acceptance cleanup"
status: shipped
priority: high
tier: sonnet
parallel: safe
type: task
surface: horus/cli.py, horus/datums.py (--card path resolution), install/reload path
created: 2026-07-14
created_by: overseer
shipped_pr: 221
shipped_sha: 8a3b4428e8f6538c07edc21e8fb7c322a7a75c33
---

# Tier-0 supervision verbs — eliminate the cockpit's mechanical tail as CLI one-shots

Dropped by the cockpit overseer 2026-07-14 (owner-directed: reduce process overhead BEFORE
re-pricing it to cheaper tiers — see cockpit card `mechanical-judgment-tier-split`, gated on
this). In the #218 acceptance, ~80% of frontier-tier overseer turns were mechanical
orchestration that should be deterministic one-shot commands (the pattern one-act acceptance
already proved). Three verbs, all agent-invoked, no daemon/watcher process:

1. **`horus merge-watch <sha|pr>`** — poll required checks on the exact SHA until settled,
   status-only output (one line per state change, not verbose CI logs), exit 0/1 on
   green/red. Replaces hand-rolled sleep-loop polling. The supervisor still reads the final
   state itself — this absorbs the waiting, not the observation.
2. **`horus reinstall --verify <marker>`** — the known-good sequence in one verb: `uv cache
   clean horus-harness` + `uv tool install --force --reinstall --python 3.12 <path>`, then
   grep the INSTALLED surface for the named marker and report found/absent. Encodes the
   uv stale-wheel footgun and the deploy≠reinstall lesson; candidate to also surface running
   dashboards that still need a restart.
3. **Acceptance cleanup** — fix `datum close --card` to resolve the card against the repo's
   PRIMARY checkout (not the run's worktree path; review already filed on
   `datum-supervisor-cost-envelope`), and optionally offer merged-worktree + branch removal
   as part of the same act.

Boundaries: one-shot verbs only — no daemon, no auto-router, no policy engine. Output lean
by default (status lines, not logs).

Acceptance: focused tests per verb; one live cycle on this machine (merge-watch a real PR,
reinstall-verify a real marker, card stamp lands on the primary checkout with worktree
cleaned); next cockpit acceptance tail runs in ≤3 supervisor commands.
