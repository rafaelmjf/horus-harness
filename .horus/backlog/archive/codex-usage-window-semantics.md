---
status: retired
priority: low
readiness: deferred
readiness_reason: "RETIRED 2026-07-26 — folded into `codex-usage-stale-snapshot-gates-dispatch` by owner decision; that card now owns every wrong-usage-reading defect in this subsystem, labelling included."
last_refined: 2026-07-26
tier: medium
created: 2026-07-16
last_refined: 2026-07-19
topic: delegation-calibration
type: bug
parallel: safe
surface: horus/codex_usage.py, horus/usage_snapshot.py, horus/datums.py, horus/dashboard.py, horus/terminal_tui.py
---

# Codex usage-window semantics

Codex currently exposes a primary usage window whose reset can be about a week away,
while Horus labels the primary slot as `5h` and the secondary slot as `weekly`. It is
not yet clear whether the missing five-hour window is temporary upstream behavior or a
lasting contract change. The current owner understands the display, so avoid reactive
schema/UI churn until the provider behavior stabilizes.

## Acceptance

- Preserve the provider's reported primary/secondary percentages and reset timestamps
  without inventing a window duration.
- Once upstream behavior is stable, label a window `5h` or `weekly` only when the
  provider contract or the reset horizon supports that label; otherwise render a
  neutral `primary` / `secondary` label.
- Keep CLI, TUI, dashboard, usage checks, and datum snapshots aligned.
- Tests cover primary-only, dual-window, and changed/reset-horizon payloads.

## Boundaries

- This is display/telemetry correctness, not dispatch routing or a spend policy.
- Do not infer model cost or expected worker consumption from the window label.
- Revisit when Codex restores the five-hour window, documents a new stable contract,
  or the current label causes a real routing/owner error.

## Reviews

- 2026-07-16 — Deferred while upstream behavior is unsettled. The owner recognizes
  the current primary-window reading and does not need an urgent cosmetic correction.
- 2026-07-19 — Dispatched in the `away-batch-3` drill (codex-personal). The worker
  implemented a full 9-file neutral-label contract change, but (a) it never
  delivered — the codex dispatch was armed with a network-off sandbox posture, see
  `codex-delivery-dispatch-needs-full-auto` — and (b) it acted against this card's
  own guidance (no evidence upstream stabilized; still reactive churn). **Not
  adopted; card stays deferred.** Diff preserved out-of-band this session for the
  record. This card was a poor pick for autonomous dispatch precisely because it is
  a watch/deferred card, not a ready one.

- 2026-07-26 — **RETIRED. Folded into `codex-usage-stale-snapshot-gates-dispatch`.**
  Owner decision: one card should own every wrong-usage-reading defect in this
  subsystem, because the same readings feed both the display and the dispatch gate, and
  the split meant neither card owned the whole picture. This card's acceptance criteria
  (never invent a window duration; neutral `primary`/`secondary` labels unless the
  provider contract or reset horizon supports `5h`/`weekly`; tests over primary-only,
  dual-window and changed-horizon payloads) are copied into that card's Acceptance.

  The evidence that triggered the fold: on 2026-07-26 the same 82% reading was rendered
  as `weekly` by `horus usage all` and as `5h` by the worker datum path, for the same
  account at the same moment — an internal labelling disagreement, which is this card's
  exact subject and satisfies its own "the current label causes a real routing/owner
  error" reactivation trigger.

  Noted against the fold: this card's text deliberately scoped itself to display
  correctness and *not* dispatch routing, and the absorbing card had argued the two
  should stay separate. That boundary is deliberately given up.
