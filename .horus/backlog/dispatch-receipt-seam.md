---
status: open
priority: medium
readiness: shaping
readiness_reason: "Needs an owner design pass on the receipt's shape and where it binds in the envelope/supervise flow."
created: 2026-07-19
vision_facet: "Autonomous dispatch"
phase: converge
tier: medium
type: feature
parallel: safe
created_by: agent
surface: horus/envelope.py, horus/supervise.py (verification input), horus/run_executor.py (worker-side receipt emission), .horus/temp/ handoff notes
---

# dispatch-receipt-seam — the worker writes facts, the supervisor reproduces the signal

## Why

The managed block now states the contract — *workers record delivery facts (the SHA, the
PR, what the gate actually emitted) — never a verdict on their own work; the supervisor
independently reproduces the deterministic signal and owns canonical continuity* — but no
machinery enforces it. It is currently prose, which is the same failure class #368 was
about.

Two forces have to be held at once, and getting either wrong is expensive:

- **The implementing session must write the closure content.** It already holds the
  context. Owner's framing (2026-07-19): a supervisor that re-reads everything to
  consolidate is paying twice for context that already existed. This is *not* an argument
  about model tier — a worker may well be Opus or higher; it is about who already has the
  context loaded.
- **The supervisor must not trust that write as a verdict.** "Tests pass" from the session
  that wrote the code is precisely what the project's own discipline says not to trust.
  The supervisor observes the deterministic signal (required CI on the exact SHA, freshness,
  a live probe) and moves on — cheaply, without re-deriving context.

The seam between those is the design: **facts and pointers flow up; judgment does not.**

## Scope boundary

This is the *dispatch path only*. In an attended session the owner is the supervisor, so
the same session writes continuity when the owner says close. Do not generalize this into a
universal rule — an earlier framing did, and it was wrong.

There is also a real split to preserve, already in the managed block: a worker sees one
card, so it can honestly report delivery facts but cannot re-rank a backlog it never saw.
Canonical continuity (Vision, priorities, what this means for the roadmap) stays with the
supervisor.

## Open design questions (why this is Shaping, not Ready)

1. **Receipt shape.** Structured (JSON under `.horus/temp/` or the ledger) vs prose. It
   must be cheap for the worker to emit and cheap for the supervisor to read without
   opening a transcript.
2. **Where it binds.** `run_executor` on completion? The envelope, so an armed dispatch
   declares the receipt it owes? The existing `.horus/temp/` handoff-note path already
   carries some of this and should be reused rather than duplicated.
3. **What is structurally prevented.** Ideally the receipt has no field in which a verdict
   can be written — the guard should be in the shape, not in a reviewer noticing. That is
   the project's safety-in-code rule applied here.
4. **Interaction with the existing supervisor.** `horus supervise` already verifies on the
   exact SHA; this should feed it, not fork it.

## Acceptance

When a dispatched worker completes, it should emit a receipt of facts and pointers only,
and `horus supervise` should reach its verify/merge/close decision from the deterministic
signal plus that receipt — without reading the worker's transcript and without any path in
which the worker's own claim of success can substitute for the gate.

## Source

Deferred from #368 (`review-session-control-calibration` verdict) — the contract shipped as
managed-block prose; the machinery was consciously left unbuilt.
