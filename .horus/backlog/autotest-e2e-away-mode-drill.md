---
status: open
priority: high
created: 2026-07-19
vision_facet: "Autonomous dispatch"
phase: converge
tier: sonnet
type: chore
parallel: safe
created_by: agent
surface: a repeatable owner-run away-mode e2e DRILL (machine-local schedules + Telegram), not product code
depends-on: schedule-supervise-resolve-target-at-fire-time, notify-schedule-batch-complete
---

# autotest-e2e-away-mode-drill — the owner's fully-scheduled away-mode e2e test

**Why (owner-specified 2026-07-19):** the owner wants a single, repeatable drill
that proves the whole autonomous-dispatch experience end-to-end from the owner's
seat, with the session CLOSED. It is the acceptance test for the "Autonomous
dispatch" facet as the owner actually lives it. A light wiring-only variant ran
2026-07-19 (3 per-account fake runs + 2 block/unblock bridge gates + a time-based
completion ping); this card captures the FULL flow to run again, and only becomes
runnable once its two `depends-on` gaps land.

## The exact flow the owner described (the target)

1. An agent session arms N **fake cards** on the scheduler — 3 that dispatch one
   to each account (`claude-personal`, `claude-work`, `codex-personal`) + 2 that
   exercise the Telegram block/unblock bridge — and confirms they are scheduled.
2. Owner opens `horus tui` → **Mission Control (m)** and confirms the armed
   dispatches (+ envelope, if the run uses one) render correctly.
3. Owner returns, confirms, and **completely closes the session.**
4. The schedule **kicks in after close** and runs everything sequentially within a
   ~20-min window, INCLUDING autonomous supervise/merge on the 3 real-ish cards
   (this is the part the light variant could not do — see depends-on).
5. The two bridge cards push to Telegram: owner taps **unblock** on one (its card
   continues/ships) and **block** on the other (its shipping is cancelled).
6. When the batch is genuinely done, the owner gets ONE Telegram notification that
   the schedule completed (a real completion signal, not a fixed-time ping — see
   depends-on `notify-schedule-batch-complete`).
7. Owner opens the TUI → Mission Control → checks each dispatch's status/outcome
   glyph (incl. the two bridge outcomes) and confirms or denies the e2e passed.

## How (once the gaps land)

- Provide a thin, re-runnable driver (a documented command sequence or a small
  `horus`-composed helper — NOT a new orchestration engine) that arms the whole
  batch from one invocation, using a bounded standing envelope with `--allow-merge`
  for the real cards. It must schedule each worker AND its supervisor to fire after
  close (needs `schedule-supervise-resolve-target-at-fire-time`).
- Use trivial-but-real cards for the 3 account legs (each produces a tiny, always-
  green PR) so supervise has something real to verify + merge.
- The 2 bridge cards use `horus ask --option unblock --option block`; the driver
  branches on the answer (unblock → proceed/ship, block → cancel) and records the
  outcome where Mission Control surfaces it.
- Batch-complete notification via `notify-schedule-batch-complete`.

## Acceptance

- With the session CLOSED, all legs run within the window; Mission Control shows
  each leg's final outcome (incl. bridge unblock/block) and the two claude/codex
  merges landed autonomously (envelope `--allow-merge` + probe).
- The owner receives exactly one real "schedule completed" Telegram message after
  the last leg finishes (not a fixed-time guess).
- Re-runnable: a second run needs only re-arming, no code edits.

## Non-goals

- Not a CI/unit test (it spends real accounts + needs owner taps); it is an
  owner-run drill. Keep it out of the pytest suite.
- Not a new scheduler/orchestrator — compose existing `horus schedule`/`run`/
  `supervise`/`ask`/`notify` primitives only.
