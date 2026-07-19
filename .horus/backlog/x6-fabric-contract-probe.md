---
status: open
priority: medium
created: 2026-07-20
created_by: owner
last_refined: 2026-07-20
readiness: shaping
readiness_reason: "The probe is live (refresh delivered 2026-07-20; owner using fabric in production), but the evidence bar — what observations count, where findings land, and what triggers the tier verdict — is undecided."
phase: explore
type: research
branch: vision-branch-x6-workflow-selection-compatibility
---

# x6 — fabric as the live contract-sufficiency probe

## Why

The X6 convergence criterion requires at least one real Horus project to
exercise the compatibility hypothesis. `fabric-metadata-driven-medallion` is
the strongest candidate found: a production Fabric ingestion project that
already lives on the **session contract only** (no `.horus/backlog/`; prose
backlog inside PRD.md) and already ran the artifact-ownership contest once
(its own `PROJECT_STATUS.md` frozen 2026-06-25 in favor of `.horus/`, reason:
no double-bookkeeping). It predates Horus, was previously not worth adapting
(machine conflicts, Horus immaturity), and the owner now uses it in production
— the "actual game" the engine is being built for (data/BI work with fewer SWE
formalities).

## Intended outcome

Field evidence on **contract sufficiency**, not workflow-swap: does the
session-contract tier deliver full resume/cockpit value for a production BI
project across machines and over weeks of active use? Specifically: does
active use ever *pull* toward cards (dispatchable units, scheduled runs — the
dispatch tier earning its keep in BI-land), or does tier 1 suffice
indefinitely? Either answer is evidence `x6-continuity-contract-declaration`
and the umbrella disposition need.

## Broad boundaries

The probe is observational: use fabric normally, record what the contract did
and didn't cover. The 0.0.73 artifact refresh was delivered 2026-07-20
(upgrade-project + skill projections + stale six-lane banner fix, via fabric's
own PR flow). Early non-goals: never install a foreign workflow bundle here
(production project — the swap experiment gets a disposable repo or
pbi-ecosystem later); no forcing cards onto fabric to "test" the dispatch tier
— the pull has to be real.

## Open decisions for backlog-refine

- What counts as a probe observation and where it lands (fabric's PRD Reviews?
  this card? a dated receipt here?).
- Probe duration / review cadence before the evidence feeds the umbrella
  disposition.
- Whether pbi-ecosystem, once active, becomes a second tier-1 probe or the
  swap-experiment host.

## Source

Raw `vision-branch-x6-workflow-selection-compatibility` card +
`.horus/research/2026-07-20-x6-boundary-inventory.md`; owner direction
2026-07-20 ("refresh horus there and start actively using as probe").
