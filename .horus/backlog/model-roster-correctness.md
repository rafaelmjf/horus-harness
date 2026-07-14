---
status: open
priority: high
tier: sonnet
type: bug
created: 2026-07-12
created_by: overseer
parallel: safe
surface: horus/datums.py, tests/test_datums.py, ~/.horus/capabilities.toml
---

# Reconcile canonical model roster rows, prices, and lifecycle provenance

> Prioritized 2026-07-14 (owner triage): this is correctness, not ranking work. The
> live roll-up currently renders priced owner priors on generic `gpt-5.6` separately
> from 4/4 clean Sol and 3/3 clean Terra datum rows with no priors or prices. Fix the
> identity join before doing more model research or releasing the current feature batch.

## Current facts

- OpenAI's 2026-07-09 GA material names canonical IDs and prices:
  `gpt-5.6-sol` $5/$30, `gpt-5.6-terra` $2.50/$15, and
  `gpt-5.6-luna` $1/$6 per MTok. `gpt-5.6` aliases Sol.
- Measured datums already prove the harness reaches the Sol and Terra canonical names;
  Luna remains unmeasured, which is honest and must not be filled with guessed outcomes.
- The original availability card's unnamed 2026-07-23 retirement is not actionable
  provenance. Record lifecycle facts only when the provider/model/date are explicit.

## Required slice

1. Replace the generic GPT-5.6 owner-prior/seed row with Sol, Terra, and Luna rows so
   priors join measured datums under the same canonical names. Preserve the existing
   generic row's caution/guard on Sol; author Terra/Luna tiers conservatively from
   sourced role descriptions, not invented quality claims.
2. Update the owner-maintained local prior with the same sourced prices and a fresh
   provenance date. Keep `gpt-5.5` only if its retained-row rationale remains explicit.
3. Accept optional `available` / `retires_at` owner-prior fields and render a clear
   lifecycle marker when present; missing fields stay unchanged. Do not populate an
   availability date without a specific source.
4. Keep the hard boundary: display data only. No ranking, benchmark synthesis,
   exploratory auto-recommendation, dashboard tab, auto-pick, or auto-route.

## Verification

- `capabilities --models --stdout` has exactly one row each for Sol, Terra, and Luna;
  Sol/Terra rows combine their existing datums with the correct prices and no generic
  duplicate survives.
- Lifecycle fixtures cover retired, retiring-soon, and absent fields without changing
  exit status or introducing a routing field. Full CI green plus a live matrix probe.
