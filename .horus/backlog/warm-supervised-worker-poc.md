---
status: open
priority: medium
created: 2026-07-17
tier: opus
type: feature
parallel: safe
phase: explore
vision_facet: "Autonomous dispatch"
branch: vision-branch-x3-scheduling-and-autonomous-execution
created_by: owner
surface: PoC only — a supervisor loop that drives ONE resumable worker session across cards (horus/run_executor.py --resume, a new supervisor driver); no committed control plane until the PoC shows a dividend
---

# warm-supervised-worker-poc — one warm worker + a steering supervisor, not N cold headless ones

**Why (owner, 2026-07-17; from `research/2026-07-17-delegation-cost-finding.md`):** the measured
dominant cost of headless dispatch is **cold-start context reload paid N×** — each fresh worker
re-learns the codebase before writing a line, while an inline session amortizes one *compounding*
context across many cards. This card explores a delegation shape that keeps the unattended/
capacity-arbitrage benefit while killing that tax: launch **one** worker session that holds
context, and a **supervisor model that steers it** through cards sequentially (simulating the
owner), shipping several cards before one continuity closure. The worker is the "semi-inline"
model holding the main context once; the supervisor plays the role the owner played this session.

## Hypothesis to test (this is exploration, not a spec)

- A single warm worker + light-touch supervisor steering ships a batch of related cards on one
  codebase for **materially less total usage** than N cold headless workers, because the
  codebase-comprehension cost is paid once, not N times.
- It still delivers the delegation dividends that matter: **unattended** (owner away) and
  **capacity arbitrage** (spend an idle account), without the per-card cold-start penalty.
- Open: does the supervisor's steering overhead eat the savings? Is a cheaper/smaller supervisor
  model enough to steer, or must it match the worker? Where does continuity checkpoint — after
  the whole batch (like inline `handoff`), or per card?

## Rough shape (PoC, minimal)

- A supervisor driver holds the card list; the worker runs as a **resumable** session
  (`horus run --resume`). The supervisor feeds the worker one card, waits for delivery, runs the
  verification gate itself, then feeds the next card into the SAME session (warm context) with
  targeted steering/feedback — never a fresh process per card.
- Measure against the 2026-07-17 headless baseline: same/comparable cards, same account/model,
  compare 5h-window consumption and wall-time for the batch. Record honestly (per the delegation
  Rule — no estimated per-task percentages; confounding labelled).

## Acceptance (PoC gate — a measurement, not a product)

- A supervisor drives one warm worker session through ≥2 real related cards to merge, with the
  supervisor running the verification gate each card and continuity closing once at the end.
- A recorded comparison vs the headless-per-card baseline (5h-window Δ + wall-time) with an
  explicit verdict: warm-supervised is cheaper / same / worse, and by roughly how much
  (confounding labelled, not hand-waved).
- Conclusion recorded in `research/`; only THEN, if the dividend is real, propose a committed
  supervisor-driver surface as a separate owner-approved card.

## Non-goals / boundaries

- No committed orchestration control plane until the PoC proves a dividend (controls-ladder:
  don't build the mechanism before the evidence). This is a measurement PoC.
- Not the distributed execution plane (still out of Vision scope). Single machine, owner-approved,
  the same one-live-process-per-config-dir and merge-authority rules apply.
- Reuses `horus run --resume` + the existing verification gate; it does not reinvent `supervise`.
