---
status: retired
priority: medium
tier: sonnet
type: feature
created: 2026-07-12
created_by: overseer
parallel: true
surface: horus/cli.py (capabilities render), capabilities.toml (priors), delegation-rubric
shipped:
---

> Retired 2026-07-14 (owner triage): current datums are sparse, uneven, and selected
> for different task shapes, so a cost + clean-rate ordering would imply false
> precision. Re-open only after canonical rows and enough comparable evidence exist;
> the current data table plus agent judgment remains the decision surface.

# Model ranking synthesis — a grounded "current ranking" for the decision matrix

**Owner ask (2026-07-12):** the roster data exists but the conclusions are hard to see
at a glance — the matrix should carry a **summary that displays the current ranking**.
Ranking is a real judgment, so it gets its own card, shipped in two stages.

## v1 (decided now — the easy approach first)

Rank from data we ALREADY hold, transparently:
- **cost** (`price_in`/`price_out` from `capabilities.toml`) and
- **our own datum-trust** (clean-rate over closed datums).
Render a short ranking summary under the table. Build it as a **scaffold**: labeled
sections/fields for the richer signals below, left empty in v1, so the refinement
populates rather than restructures. **Display-only — never auto-picks or auto-routes**
(the hard boundary the whole `capabilities`/matrix surface holds).

## Refinement (later — the richer signals to ground the ranking)

Synthesize, per model:
- **official stated use** (provider's model-card strengths),
- **3rd-party benchmark standings** — see `benchmark-platforms-grounding`,
- **community / web research** on real-world user experience,
- **our delegation datums** (already in v1),
- an owner-editable **subjective notes** section (the owner's lived experience),
- gated by **availability/lifecycle** — see `model-availability-lifecycle` (a
  soon-to-retire model shouldn't rank high regardless of price/capability).

Each signal is a source with provenance; the ranking shows WHY, not just an order.

## Depends on / feeds

Reads the table + proper names from `model-name-normalization-and-datum-migration`.
Consumes `benchmark-platforms-grounding` + `model-availability-lifecycle` at
refinement. Pairs with `explore-undersampled-models` (a ranking built only on
exploited data is survivorship-biased — see that card).

## Verification

v1: matrix summary prints a cost+trust ranking with visible inputs; `--stdout` carries
a structured `ranking` block; boundary test still asserts no pick/route field. CI green.
