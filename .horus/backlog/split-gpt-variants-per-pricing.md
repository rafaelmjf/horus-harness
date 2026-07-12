---
status: open
priority: medium
tier: sonnet
type: feature
created: 2026-07-12
created_by: overseer
parallel: true
surface: ~/.horus/capabilities.toml (owner priors), research
shipped:
---

# One roster row per GPT-5.6 variant (Sol / Terra / Luna) — distinct pricing

**Owner point (2026-07-12):** GPT-5.6 ships as distinct variants with DIFFERENT pricing
(Sol / Terra / Luna), so a single `gpt-5.6` roster row hides the price difference that
matters for the price-for-capability filter. Split it into one prior row per variant.

## Scope (mostly data + a small research step)

- Replace the single `[models."gpt-5.6"]` prior with per-variant rows using the proper
  canonical names the `model-name-normalization` card established:
  - `gpt-5.6-sol`  — $5 in / $30 out (from the 2026-07-12 pricing pass)
  - `gpt-5.6-terra` — $2.50 in / $15 out (the value variant)
  - `gpt-5.6-luna` — **pricing unknown — research pass needed** (do NOT fabricate)
  each with its own `capability_note`, `researched_at`, and (per
  `model-availability-lifecycle`) availability.
- **Owner input still needed:** the exact reachable `horus run --model <?>` alias for
  each variant, so a *datum* keyed to a dispatch matches the prior row. Priors can list
  all variants regardless; datums only accrue for the ones actually dispatched.
- Fold the Luna pricing + any correction into the next web-research pass (same source
  discipline as #167: platform/provider pricing pages, provenance recorded).

## Relationship

Uses canonical variant naming from `model-name-normalization-and-datum-migration`
(shipped #168). Feeds `model-ranking-synthesis` (variant-level cost comparison) and is
gated by `model-availability-lifecycle` (a retiring variant shouldn't rank).

## Verification

`capabilities.toml` parses with the three variant rows; `capabilities --models`/
`--matrix` renders each with its own price; a dispatch to a confirmed variant alias
produces a datum keyed to the same name. CI green.
