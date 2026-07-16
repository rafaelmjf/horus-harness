---
status: open
priority: low
tier: sonnet
created: 2026-07-16
vision_facet: "Delegation calibration"
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
