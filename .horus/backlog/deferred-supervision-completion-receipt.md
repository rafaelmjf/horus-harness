---
status: open
priority: high
tier: sonnet
created: 2026-07-15
type: feature
parallel: unsafe
surface: horus/cli.py, horus/registry.py, horus/delivery.py, horus/datums.py, horus/terminal_tui.py, bundled dispatch/execution skills
---

# Deferred supervision and completion receipt

Dispatch mode and supervision timing are separate decisions. A bounded worker may be
actively watched and bounced in the launching session, or left to complete before a
fresh supervisor spends context on verification. Today that choice is implicit, and a
process exit alone does not give a cold supervisor one compact decision signal.

Record `active` versus `on-completion` supervision without turning Horus into a router.
For deferred review, project the mechanical outcome, delivery receipt, and target
account's close-usage snapshot so an owner can decide whether to launch another bounded
worker before paying the acceptance-review cost.

## Acceptance

- A dispatched session records `supervision: active|on-completion` independently from
  `inline-here|dispatched-worker|dispatched-plan`; skills and prompts treat it as a
  lifecycle choice, not a model/account recommendation.
- On worker exit Horus exposes one deterministic state: `delivery-ready`, `blocked`,
  `failed`, or `unknown`, backed by process status plus pushed SHA/PR/continuity receipt.
  `delivery-ready` is explicitly not acceptance or permission to merge.
- The completion receipt includes a fresh machine-local usage snapshot for the worker's
  isolated account, or labels it unknown/stale. No account reading is committed to a
  project repository.
- TUI and a scriptable CLI/JSON surface show session ID, project, supervision timing,
  outcome, pushed SHA/PR when present, and usage-close freshness without parsing prose.
- A fresh supervisor can observe required CI/live gates and close the datum later;
  independent work may be launched after explicit owner approval, while dependency
  gates still require acceptance rather than mere completion.
- Tests prove that no completion state auto-selects a model/account, auto-launches the
  next phase, auto-merges a PR, or treats a worker report as verification evidence.

## Boundaries

- Prefer existing registry, run-event, delivery-receipt, and datum fields; add only the
  minimum machine-local state needed for a cold supervisor.
- Owner-provided usage remains a valid override when native telemetry is incomplete.
- Notifications and automatic chains are separate future decisions; this card provides
  the deterministic signal they would consume.

