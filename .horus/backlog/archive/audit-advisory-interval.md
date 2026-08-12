---
status: shipped
priority: low
created: 2026-07-20
created_by: agent
last_refined: 2026-07-28
refine_passes: 2
readiness: shaping
readiness_reason: "RELEASED 2026-08-01 — the reservation is void: it was payload for `autotest-e2e-away-mode-drill`, which was retired today, and this card's own trigger said it releases when the drill is abandoned. Decision-complete and implementable: the interval formula is confirmed below as 10 releases AND 14 days."
topic: introspection-self-improvement
type: chore
shipped_pr: 484
shipped_sha: 464427c76f7603a9985f0faa99d8cfe9864fa7c9
---

# audit-advisory-interval — count releases AND days, not releases alone

## Why

The product-audit staleness advisory fired repeatedly within four days because
its interval counts releases only — and this project shipped 15 releases in 4
dogfooding days. Releases are a poor clock during rapid iteration; elapsed
time is a poor clock during idle stretches. The 2026-07-20 audit receipt's
ceremony section recorded the finding. Small, deterministic, code-only —
shaped as an early autonomous-eligible candidate.

## Intended outcome

The advisory fires when BOTH thresholds pass (e.g. ≥N releases AND ≥M days
since the stamp), so it nags neither during release bursts nor during long
quiet stretches — thresholds decided at refinement.

## Broad boundaries

Touches only the advisory condition reading `last_product_audit` (version +
date are already both in the stamp). Non-goals: no new stamp format; no
per-project configurability until someone needs it.

## Decisions settled (2026-07-28 refine pass, owner-approved)

- **N/M defaults: 10 releases AND 14 days.** [refine] — settled; the card's own candidate
  was adopted unchanged.
- **AND semantics**, not weighted-either. [refine] — settled; AND is what makes the advisory
  quiet during both release bursts and idle stretches, which is the whole point.
- **Autonomy mint: deferred by reservation, not decided.** [refine] — this card is drill
  payload, so it does not enter the eligible pool now. When its trigger releases it, it is
  `ready` + `eligible` under the drill's own bounded envelope.

Nothing remains that needs a working session; this card is implementable as written.

## Reviews

- 2026-07-28 — **Shaping → Deferred, reserved as drill leg 2** (owner, refine pass). The
  drill needs 3 small always-green legs and had 1 confirmed; this was the only surviving
  named candidate, since the other (`backlog-default-list`) shipped in #408. Reserved rather
  than minted eligible, because minting it would have put it in the path of an unattended
  run that could clear it and cost the drill a leg with one day's notice — the exact roster
  erosion the drill card documents. The interval formula was settled in the same exchange so
  the leg is decision-complete when armed.

## Source

`.horus/audits/2026-07-20-product.md` ceremony observations;
`.horus/research/2026-07-20-roadmap-branches-rebaseline.md` branch D item 4.
