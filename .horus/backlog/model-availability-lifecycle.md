---
status: open
priority: medium
tier: sonnet
type: feature
created: 2026-07-12
created_by: overseer
parallel: true
surface: capabilities.toml (priors schema), horus/cli.py (capabilities render)
shipped:
---

# Track model availability / lifecycle — don't invest in soon-to-retire models

**Owner point (2026-07-12):** models get retired on a schedule (the owner saw a ChatGPT
UI notice that a model will be **dropped 2026-07-23**). A model near end-of-life is a
poor place to sink exploratory dispatches or ranking weight — "probably not worth
gathering data right now." The roster must know a model's availability.

## Scope

- Extend the `capabilities.toml` prior schema with optional, back-compatible lifecycle
  fields: `available` (bool, default true) and `retires_at` (date, optional).
- `capabilities --models`/`--matrix` **flags** a model that is retired or retiring soon
  (e.g. within N days of `retires_at`) — a clear visual marker, not a removal.
- **Gate downstream logic:** `explore-undersampled-models` must not recommend exploring
  a soon-to-retire model; `model-ranking-synthesis` must down-weight / exclude it. Both
  read these fields.
- Lifecycle data is owner/agent-maintained (same hand-edited channel as pricing), and is
  a natural part of the periodic model-research refresh pass — populate `retires_at` when
  a provider announces it.

## Feeds

`model-ranking-synthesis` (availability gate) and `explore-undersampled-models` (don't
explore dead-ends). Same schema-extension pattern as the shipped
price/capability/researched_at fields (#167) — keep back-compat.

## Verification

A fixture with `retires_at` in the past renders a retired flag; one retiring within the
window renders a warning flag; a model without the fields is unchanged (back-compat);
exit code unaffected. CI green.
