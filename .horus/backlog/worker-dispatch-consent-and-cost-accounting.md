---
status: open
priority: high
tier: sonnet
created: 2026-07-16
type: feature
parallel: unsafe
surface: shared AGENTS.md/CLAUDE.md managed block, .agents/skills/delegation-rubric, execution-decision, dispatch-decision, horus-execution, horus/datums.py, horus/run_executor.py, horus/cli.py
---

# Explicit worker dispatch consent and cost accounting

A supervised worker campaign silently rerouted from an isolated Claude work account
to high-effort Codex Terra on the ambient overseer account. The implementation landed,
but four sequential worker runs plus supervision consumed about thirty percentage
points of the shared Codex window. Need-first routing existed, yet the in-project path
did not require an exact model/account proposal or bind approval to an attempt envelope.

## Acceptance

- Before any Claude or Codex implementation worker is launched, the supervisor shows
  the exact agent, concrete model, effort, account, current usage/reset evidence,
  bounded task, attempt allowance, expected dispatch dividend, and verification gate;
  explicit owner approval binds that envelope.
- Changing model, account, task scope, or authorized attempts requires renewed owner
  approval. No silent provider/model/account fallback.
- Agent-initiated dispatch still proves a context, parallelism, or price dividend.
  Owner-directed dispatch may explicitly optimize expiring account capacity or protect
  supervisor context even when feature economics alone would stay inline.
- The shared managed block, delegation rubric, execution/dispatch decision skills, and
  Horus execution skill carry one vendor-neutral contract so Claude and Codex
  supervisors behave the same.
- Worker completion mechanically reports model, account, effort, runtime, attempts,
  outcome, and comparable start/end usage readings. Show an observed percentage delta
  only when the same window is fresh and unconfounded; otherwise label it unknown or
  shared-account/confounded.
- Campaign closure can render the per-worker breakdown without manual UUID archaeology.
- Tests cover exact-envelope consent text, owner-directed overrides, fallback
  reapproval, same-account/confounded readings, and Claude/Codex projection parity.

## Boundaries

- Do not predict per-task percentage consumption or auto-route from a cost score.
  Historical ranges may be added later only after enough isolated comparable runs.
- Keep Horus data/advisory-only: it records and displays; the owner authorizes and the
  execution plane launches.
- Minimize overhead: no extra model call for accounting, no continuous usage polling,
  and no duplicate full-suite gate when exact-commit CI or one harness-owned gate exists.

## Reviews

- 2026-07-16 — Field failure makes this the next high-priority process feature. Finish
  the already-accepted worker-lifecycle campaign inline first; do not dispatch this
  card's implementation before its own consent contract exists.
