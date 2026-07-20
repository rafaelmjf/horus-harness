---
status: open
priority: medium
created: 2026-07-20
created_by: agent
last_refined: 2026-07-20
readiness: shaping
readiness_reason: "Wildcard explore: fire-time resolution semantics and the comparison protocol against a clock-timed twin are undecided."
phase: explore
type: feature
vision_facet: "Autonomous dispatch"
---

# window-aware-scheduling — fire when budget exists, not when the clock says (wildcard)

## Why

Away-batches today fire at guessed clock times and can land in a drained
usage window; envelopes then refuse (unknown/insufficient capacity refuses by
rule), and the slot is wasted. Per-account window/reset readings are already
recorded from the pushed statusline surface. Divergent bet: a schedule entry
of the form "next window with ≥N% budget on account X" — resolved at fire
time against the cached reading — beats clock guessing for trip-time batches.

## Intended outcome

During a real away-batch, the window-aware entry demonstrably avoids a
window-starved run its clock-timed twin would have hit. **Converges** if it
prevents real starvation at least once without new failure modes; **dropped**
if windows prove too unpredictable or the cached readings too stale — leaving
clock+usage-floor (which already exists in envelopes) as the honest answer.

## Broad boundaries

Timing only, HARD boundary: this may decide *when* an already-owner-approved
dispatch fires, never *which* account, model, or card runs (auto-routing
stays forbidden). Builds on systemd timers + the existing usage cache; a
stale reading must degrade to refuse-or-clock-fallback, never to guessing.

## Open decisions for backlog-refine

- Semantics: one-shot re-arm loop vs a timer that re-checks on each elapse.
- Staleness threshold for trusting a cached reading at fire time.
- The twin-comparison protocol (how the converge/drop evidence is captured).

## Source

Agent wildcard at the 2026-07-20 scope-cards gate, owner-approved;
`.horus/research/2026-07-20-roadmap-branches-rebaseline.md` branch C context.
