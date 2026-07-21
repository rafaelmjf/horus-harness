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

## The sharp design question (open): what steers it?

A spectrum:

- **Pure wild** — free-roaming "surprise me" ideation. Fun, serendipitous, but low
  hit-rate / backlog-spam risk.
- **Signal-grounded** — mines real signals (backlog gaps, audit findings,
  shipped-vs-used drift, recurring friction in receipts, a market-scan receipt) and
  proposes an opportunity the owner wouldn't have prioritised. Higher value, less "wild."
- Likely: **signal-grounded with a wild-card streak** — ground each proposal in
  evidence so the card is discovery, not noise.

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

## Open questions

- Grounding (above); run substrate (scheduled job vs on-demand); cadence + a bounded
  token budget per run.
- Overlap with `pathfinder` / `scope-cards` / `market-scan` — it reuses their divergence
  machinery but strips the attended gates; position so it is not a duplicate.

## Source

In-session, 2026-07-21 (owner idea — "could be fun to try and test to see what outcomes
we get"). Related: `pathfinder`, `scope-cards`, `market-scan`,
`refine-autonomy-hardening-lens`, `autotest-e2e-away-mode-drill`.
