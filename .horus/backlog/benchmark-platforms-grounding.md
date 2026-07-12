---
status: open
priority: low
tier: sonnet
type: feature
created: 2026-07-12
created_by: overseer
parallel: true
surface: capabilities.toml (priors), horus/cli.py (capabilities render), research
shipped:
---

# Ground the ranking in 3rd-party benchmark platforms

**Owner ask (2026-07-12):** some people make their living grading models as independent
third parties. Their standings are a grounding signal our decision matrix should
consider — instead of leaning only on official model cards + our own thin datum set.

## Scope

1. **Research (agent, web) which reputable 3rd-party benchmark/leaderboard platforms to
   trust** — determine them from live research, do NOT hardcode a list from memory.
   Capture provenance (which platform, which board, as-of date).
2. **Wire benchmark standings in as a signal** for `model-ranking-synthesis` — a per-model
   benchmark field (or small block) in the priors, with the source + date. Treat as an
   input to the ranking, clearly attributed, not gospel.
3. Benchmark data is refreshed by the periodic model-research pass (same cadence + >14d
   staleness discipline as pricing), NOT scraped live by the CLI. Agent researches +
   writes; CLI reads.

## Feeds

`model-ranking-synthesis` (refinement signal). Complements cost (have it), our datums
(have them), official stated use, and owner subjective notes.

## Notes / caution

- Third-party benchmarks vary in rigor and can be gamed; record the source so the owner
  can weight or discount it. This is a grounding input, not an auto-decider — the
  display-only boundary still holds (nothing here auto-routes a model).

## Verification

A fixture prior carrying a benchmark field renders it with source+date in the matrix and
is consumable by the ranking; missing benchmark data degrades gracefully. CI green.
