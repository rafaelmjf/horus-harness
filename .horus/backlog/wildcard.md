---
status: open
priority: low
created: 2026-07-21
created_by: owner
last_refined: 2026-07-21
readiness: shaping
readiness_reason: "A 'fun to try' exploratory idea; the grounding (what steers the exploration), the quality bar, and the run substrate are unscoped. Explore before drafting the skill."
phase: explore
type: spike
vision_facet: "PO lifecycle"
depends-on: pathfinder-structured-outcome
---

# wildcard — an autonomous divergence skill that emits ONE reviewable card

## Why — owner, 2026-07-21

`pathfinder` is deliberately attended: direction-setting (convergence) is owner
territory. But this session's autonomy discussion suggests a safe autonomous sibling.
The principle we landed on: **autonomy is safe when the blast radius is bounded and
reversible — and a card is the ultimate bounded output** (nothing ships, nothing
changes, it's a reversible proposal). So the *divergence/discovery* step can run
unattended even though *convergence* and *implementation* cannot.

`wildcard` = autonomous pathfinder-divergence, minus convergence, minus implementation.
It runs on its own, explores, and produces ONE well-defined candidate card for the
owner to revise / approve / discard. **Nothing is implemented without owner approval** —
the output is a proposal, not a change.

This is literally `refine-autonomy-hardening-lens` applied to pathfinder: isolate the
one autonomizable step (divergence → a bounded-output card) from the intrinsic-attended
steps (direction, taste, shipping).

## Grounding — the pathfinder run (owner-decided, 2026-07-21)

Not free-roaming. `wildcard` is grounded on a **pathfinder run** — either a **fresh** one
(if the owner wants current evidence) or the **previous** run's saved artifacts. Every
pathfinder run already persists its evidence: the position brief, the `product-audit`
receipt, the `market-scan` receipt, and the `roadmap-branches` divergence tree (dated,
under `.horus/research/` and `.horus/audits/`). Wildcard reads that artifact set and
autonomously synthesises **ONE** opportunity worth a card — effectively an autonomous
"convergence into a single proposal" over pathfinder's divergence evidence, safe because
the output is a card, not a direction commitment.

**Fresh vs previous — the tradeoff:**

- **Previous run (default):** cheap, no re-gathering; risk is staleness — cite the
  artifacts' dates and flag when the run is old.
- **Fresh run:** current evidence, but re-runs the (autonomizable) evidence steps
  (`product-audit` / `market-scan`) at real token cost. Convergence and direction stay
  the owner's; only the evidence-gathering + single-proposal synthesis is autonomous.

Each emitted card cites the specific artifacts it was grounded in.

## Quality bar (open)

- Emit ONE evidence-grounded card per run, self-critiqued / ranked — resist dumping a
  flood of low-value cards.
- Each proposal cites its grounding (the gap / receipt / friction it came from).

## Why it's a good autonomous-loop candidate

Zero-blast-radius output makes it near-ideal food for the scheduled away-mode loop (cf.
`autotest-e2e-away-mode-drill`): a real autonomous job that pings the owner with a card
to review — exercising the dispatch infra with no merge risk. Fun *and* a safe exercise
of the autonomous substrate.

## Non-goals

- Not autonomous convergence — direction stays owner-gated, via `pathfinder`.
- Not autonomous implementation — the emitted card follows the normal
  refine → approve → implement path.

## Prerequisite — structured pathfinder run outcome (`pathfinder-structured-outcome`)

For wildcard to load a *coherent* set from "the previous pathfinder run," the artifacts
must be grouped by run. Today they land as **dated receipts** in `.horus/research/` and
`.horus/audits/` — not tied together. This is now its own card,
**`pathfinder-structured-outcome`** (refine the chain to emit an addressable per-run
bundle + manifest); wildcard `depends-on` it for the "previous run" path.

## Open questions

- Fresh vs previous default + staleness flagging (see Grounding).
- Run substrate (scheduled job vs on-demand); cadence + a bounded token budget per run.
- (Resolved) run-bundle/manifest is now its own card, `pathfinder-structured-outcome`.
- Overlap with `pathfinder` / `scope-cards` / `market-scan` — it reuses their divergence
  machinery but strips the attended gates; position so it is not a duplicate.

## Source

In-session, 2026-07-21 (owner idea — "could be fun to try and test to see what outcomes
we get"; grounding decided same session). Related: `pathfinder`, `scope-cards`,
`market-scan`, `refine-autonomy-hardening-lens`, `autotest-e2e-away-mode-drill`.

## Reviews

- 2026-07-21 — **Grounding decided** (owner): wildcard runs on a pathfinder run's saved
  artifacts (fresh or previous), not free-roaming — resolving the pure-wild-vs-grounded
  question toward grounded. Surfaced a likely prerequisite: a per-run artifact
  bundle/manifest so the previous run's evidence can be loaded coherently.
