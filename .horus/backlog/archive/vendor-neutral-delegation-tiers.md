---
status: shipped
priority: high
created: 2026-07-17
vision_facet: "Delegation calibration"
phase: converge
tier: sonnet
type: feature
parallel: safe
created_by: owner
surface: horus/datums.py (tier vocabulary + alias normalization), horus/capabilities.py, delegation-rubric/dispatch-decision/execution-decision skills, backlog card frontmatter (tier:), standing-dispatch-envelope tier-ceiling field
shipped_pr: 316
shipped_sha: 9d5fdafd300b517caf3344eeb69571bfcaaf4a3c
---

# vendor-neutral-delegation-tiers — tiers name capability, never a vendor

**Why (owner, 2026-07-17):** card `tier:` recommendations always name Claude models
(`sonnet`, `opus`), so delegation silently defaults to Claude — GPT/Codex workers are
never picked even where equivalent. The tier vocabulary must be vendor-neutral so the
provider choice is made at dispatch time from **available capacity + owner choice**,
never by the label. Land this BEFORE the first X3 scheduled dispatches: the standing
envelope's tier-ceiling field should already use neutral labels.

## Owner's initial equivalence mapping (prior, to validate)

| Neutral tier | Claude | Codex/GPT |
|---|---|---|
| **frontier** | Fable 5 | GPT-5.6-Sol (high) |
| **high** | Opus | GPT-5.6-Terra (high) |
| **medium** | Sonnet 5 | GPT-5.6-Terra (medium) |
| **low** | Haiku 4.5 | GPT-5.6-Luna (high) |

The mapping is an **owner prior** until validated — external benchmarks/leaderboards +
community experience first (the `external-priors-calibration` idea from the held-out
2026-07-17 tree: priors-first, own datums as residual), own datums as they accrue.
Effort level rides WITH the tier mapping (e.g. low = Luna on high effort), so a tier
names a capability point, not a bare model id.

## Acceptance

- Tier vocabulary `low | medium | high | frontier` is the canonical card/envelope
  value; existing model-named `tier:` values alias cleanly (no card migration wave).
- `horus capabilities --models` renders the per-provider mapping under each neutral
  tier with its evidence (prior vs measured); alias normalization actually joins
  variants (observed split: `sonnet-5` vs `claude-sonnet-5`, `fable` vs `fable-5`
  render as separate datum rows today).
- Dispatch/decision skills read the neutral tier and present the provider options
  within it (capacity-gated via `horus usage check`), owner picks — no vendor default,
  no auto-routing (existing rule unchanged).
- The standing-dispatch-envelope tier ceiling accepts neutral labels only.

## Non-goals

- No benchmark-scraping pipeline — external evidence is gathered one-shot per model
  generation, recorded as priors.
- No auto-selection; equivalence never overrides explicit owner choice.
