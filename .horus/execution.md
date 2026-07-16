---
status: planned
current_feature: "Worker-lifecycle campaign: attachable detached one-shot workers + the delivery-evidence/completion kernel (backlog: attachable-detached-worker-run, carrying the kernels of worker-progress-heartbeat and deferred-supervision-completion-receipt per their 2026-07-16 reviews)."
supervisor_tier: unassigned
worker_tier: unassigned
delegation_basis: "Set per phase at execution time via execution-decision: phase 0 is design (stays with the supervising session); phases 1–2 are scoped implementation with deterministic gates once the schema is pinned — re-check live calibration then."
last_updated: 2026-07-16
---

# Execution Plan — worker-lifecycle campaign

Drafted 2026-07-16 in the session that re-scoped the three worker-lifecycle cards,
so the design constraints below carry that context to the executing session. Keep
this file fluid; statuses move as phases land. (Previous completed plan:
usage-limit survival kit, PR #115 — see git history of this file.)

## Why this shape

Three cards described one feature from three angles (liveness, progress, delivery).
Implemented independently they would produce three consecutive registry/run-log
schema changes and risk inconsistent state taxonomies. One campaign, one schema
design, kernel-only scope: the periodic stall timer and the receipt trimmings are
explicitly deferred (see the two demoted cards' Reviews).

## Design constraints (phase 0 output must satisfy these)

- **One worker-state model, three orthogonal dimensions**, designed together even
  where only partially implemented now:
  - *liveness*: `running | exited | failed | stale` (reconciliation-owned);
  - *delivery*: `delivery-ready | blocked | no-op | failed | unknown` — backed by
    process status plus pushed SHA/PR/continuity receipt; `delivery-ready` is never
    acceptance or permission to merge;
  - *progress*: schema reserves the dimension (a last-activity timestamp slot);
    the periodic heartbeat/stall classifier is deferred — one field later, not a
    migration.
- **A clean exit with zero delivery evidence when the brief expected some is
  surfaced as `no-op`, never bare success** — this is the failure-evidenced kernel
  (gvfs-parked worker, 2026-07-15 campaign) and is in scope NOW.
- Detached execution reuses the managed tmux runner + one-shot adapter contracts;
  no daemon, no second adapter path, no auto-resume/auto-merge/auto-launch on exit.
- Launcher/caller death (including a foreground caller's SIGTERM on timeout) never
  kills a dispatched worker — the observed incident this campaign exists to fix.
- Every tmux-touching test/probe uses a private socket (`tmux -S <path>`); reapers
  act only on positive registry confirmation (standing rules).

## Phases

| phase | status | scope | gate |
|---|---|---|---|
| 0 state model + schema | planned | registry/run-log fields for the three dimensions; parity map against current foreground `horus run` fields | design reviewed against the constraints above; no code ships without it |
| 1 detached attachable one-shot | planned | `horus run --worker … --detach` (or equivalent) on the managed tmux host; TUI attach/detach; natural-exit parity (status, rc, run log, datums, delivery facts); caller-death survival | full pytest + required CI green on the exact SHA + live probe: launch detached, kill the launcher, attach/detach, observe clean completion with parity fields recorded |
| 2 delivery-evidence + completion kernel | planned | `no-op` detection at exit; `delivery-ready|blocked|failed|unknown` exposed via sessions/CLI-JSON without prose parsing | tests for no-op, delivering, failed, unknown; live probe: a scripted worker that exits 0 delivering nothing must surface as `no-op` |

## Deferred (do not implement in this campaign)

Periodic heartbeat/stall timer; `active|on-completion` supervision taxonomy;
usage-close snapshot embedded in the receipt; richer TUI receipt surface. Gated on
one real campaign using the detached primitive + a check of native-platform
progress/notification signals at that time.
