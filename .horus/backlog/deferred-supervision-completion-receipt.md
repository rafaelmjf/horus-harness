---
status: open
priority: low
tier: medium
created: 2026-07-15
vision_facet: "Delegation calibration"
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

## Reviews

- 2026-07-16 — Owner session split kernel from trimmings. The kernel — one
  deterministic completion state (`delivery-ready|blocked|failed|unknown`) backed by
  process status plus pushed SHA/PR/continuity receipt — moved INTO the
  [[attachable-detached-worker-run]] campaign, since it is Horus-specific delivery
  semantics no native platform will ship. What remains here is deferred until one
  real campaign runs on the detached primitive: the `active|on-completion`
  supervision-timing taxonomy, the embedded account usage-close snapshot, and the
  richer TUI/JSON receipt surface — their right shape is unproven and native
  completion/notification transports may cover part by then. Priority high→low.
- 2026-07-16 — First real detached campaign reactivated the correctness kernel.
  Two one-attempt workers pushed PRs #257/#258 and both merged cleanly, but the
  persisted rows report `exit=crashed`, session `status=stale`, delivery
  `blocked`, and `runtime_seconds=null` despite launch/completion timestamps and
  pushed PR/SHA evidence. Fix that terminal-state/runtime/delivery truth first;
  keep `active|on-completion` taxonomy and richer receipt UI deferred. Priority
  low→high.
- 2026-07-16 — Correctness kernel shipped in PR #261 at
  `cb1bbf077da7304b89de040493a831c1b12c885d`. The tmux runner PID now remains
  authoritative while its adapter child exits, and deterministic + live
  private-socket probes prove reconciliation cannot overwrite the clean receipt
  or runtime. Remaining scope is only the still-unproven supervision-timing
  taxonomy, embedded usage-close convenience, and richer receipt UI. Status
  claimed→open; priority high→low.
