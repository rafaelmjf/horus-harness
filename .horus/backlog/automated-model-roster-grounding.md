---
status: shelved
shelved_on: 2026-08-01
priority: medium
readiness: shaping
readiness_reason: "Direction is clear (automate roster freshness from external + shared sources instead of manual bumps) but the sources, the trust/provenance model, and how a fetched signal folds into the priors are all unshaped. Needs a research + scoping pass before any is Ready."
created: 2026-07-29
created_by: owner
vision_facet: "Delegation calibration"
tier: medium
type: research
parallel: safe
surface: "horus/datums.py (PRIORS_SEED + staleness check), horus/capabilities.toml, horus/cli.py (capabilities render), research"
---

# automated-model-roster-grounding — keep the model roster fresh from external + shared sources, not manual bumps

## Why

The delegation-calibration model roster (tiers, prices, capability notes) ships as a
dated seed (`PRIORS_SEED` in `horus/datums.py`, `researched_at` per row) with a
14-day staleness tripwire: once the freshest `researched_at` is >14 days old the CLI
warns "model-roster priors are N days old — consider refreshing". The only remedy today
is a **manual re-verify + date bump** — which the owner has decided not to rely on
(2026-07-29): a periodic hand-edit is exactly the kind of ceremony that rots and blocks
CI without anyone actually re-checking the data.

The tripwire fired on 2026-07-29 (seed dated 2026-07-14) and hard-failed CI via
`test_capabilities_models_cli_default_seed_is_fresh`. That test is now
`xfail(strict=False)` referencing this card, so it self-heals when the seed is
refreshed or this direction lands — but the underlying reliance on manual refresh is
the real debt this card owns.

## Intended outcome (broad — scope before committing)

The roster stays trustworthy **without a human periodically re-typing dates**. Freshness
is maintained by grounding the priors in two evidence streams the owner named:

1. **External benchmark platforms** — reputable third-party leaderboards/graders as a
   standings signal (supersedes the retired `benchmark-platforms-grounding`, whose
   re-open condition was "canonical model rows are clean and a ranking decision
   demonstrably needs external grounding"). Determine platforms from live research, not
   a hardcoded list; capture provenance (platform, board, as-of date).
2. **Other users' experience** — shared/aggregated datums from other operators' real
   runs, so a single solo owner's thin, task-selected datum set is not the only measured
   input. This is a NEW dimension (no existing card); it raises its own trust, privacy,
   and provenance questions and is a non-trivial part of the scope.

The manual seed remains the honest fallback until an automated stream is trustworthy —
this card does not remove the seed, it removes the *reliance* on hand-refreshing it.

## Open questions / to explore

- Which external platforms are trustworthy, and how their standings map onto our tiers.
- What "other users' experience" concretely is: a shared datum format? an opt-in
  aggregation? how provenance and privacy are handled for a currently solo-owner product
  (multi-human collaboration is a standing non-goal — square that).
- How a fetched/aggregated signal folds into `PRIORS_SEED`/`capabilities.toml` without
  fabricating a `researched_at` the system never actually verified.
- Whether the 14-day tripwire stays (retuned) or is replaced by "last successful
  automated grounding" freshness once a stream exists.
- Interaction with the existing measured-datum spine and `delegation-rubric` — external
  signals are priors, measured datums remain the ground truth; never let a leaderboard
  override a measured result.

## Non-goals

- Not fabricating freshness (bumping `researched_at` without a real re-check).
- Not a live always-on external monitoring feed — grounding is evidence-first and
  periodic/triggered, consistent with the Vision's "continuous external monitoring" out-of-scope.
- Not removing the manual seed fallback.

## Source

Owner decision 2026-07-29, prompted by the model-roster staleness tripwire hard-failing
CI during a test-fixture de-rot pass. Supersedes (re-opens with broader scope) the retired
`.horus/backlog/archive/benchmark-platforms-grounding.md`. Related: `dispatch-workflow-comparative-study`,
the `delegation-rubric` / `dispatch-decision` / `execution-decision` skills, and the
`x4-model-harness-plane` branch.
