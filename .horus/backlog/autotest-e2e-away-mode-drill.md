---
status: open
priority: high
readiness: deferred
readiness_reason: "Deferred until after 2026-07-29 (owner, 2026-07-21) — run then as the attended away-mode drill, when weekly account capacity supports the multi-account run. Leg roster in Reviews."
created: 2026-07-19
last_refined: 2026-07-21
vision_facet: "Autonomous dispatch"
phase: converge
tier: medium
type: chore
parallel: safe
created_by: agent
surface: a repeatable owner-run away-mode e2e DRILL (machine-local schedules + Telegram), not product code
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

## Reviews

- 2026-07-19 — **Both `depends-on` gaps landed (v0.0.68):**
  `schedule-supervise-resolve-target-at-fire-time` (#346, deferred `supervise --card`)
  and `notify-schedule-batch-complete` (#347). This card is now RUNNABLE. A real
  single-leg partial ran the same day (`init-scaffolds-project-ci` → claude-personal,
  batch `real-drill-1`): armed worker + deferred supervisor, session-closed style,
  real PR #349, one real batch-complete Telegram — proving the mechanics end-to-end.
  What remains for the FULL drill: 3-account legs + the 2 Telegram block/unblock bridge
  taps + autonomous supervise **+merge** (envelope `--allow-merge` + probe). Deferred
  until the **weekly window resets** (claude/work was at 92% weekly) so the multi-account
  run has capacity.
- 2026-07-21 — **Deferred to after 2026-07-29** (owner, refine pass): re-gated from the
  vague "weekly reset" to a specific date — run then as the attended away-mode drill when
  capacity supports the multi-account run. **Leg roster started:**
  `verify-guidance-long-running-services` is one confirmed real always-green leg (tagged
  this pass); still need ~2 more small always-green legs — candidates to body-check when
  arming: `audit-advisory-interval`, `backlog-default-list`. `codex-identity-guard` was
  explicitly **excluded** (safety-critical, ships on its own merits). Satisfied
  `depends-on` (both landed v0.0.68) removed from frontmatter.
- 2026-07-26 — **Sibling exercise in `fabric-build`, and the question this drill should
  actually answer.**

  *Cross-reference (not a completion tag).* `fabric-build/.horus/backlog/lower-model-e2e-drill.md`
  is an active sibling: point a lower-capability model at the repo and have it build a
  workspace end to end. It is **Ready/attended and mid-arc, not finished** — runs 1–2
  surfaced **seven real defects, all fixed and merged** (its PRs #15–#22, suite 82 → 107),
  the test workspace has been reset to its 8-item baseline, and that project's
  `next_action` is "Rerun `lower-model-e2e-drill` run 3". Nothing was ever tagged here;
  this Review is the first link between the two. **Evidence worth borrowing: a drill of
  this shape pays for itself in defects found.** Note it exercises a different axis
  (can a weaker model follow the route?) than this card (does the unattended
  dispatch→supervise→merge loop hold?).

  *What this drill should test, from the 2026-07-26 retrospective.* An unattended loop
  that day **would have shipped `codex-identity-guard` (#404) as done**: required CI was
  green on the exact SHA, freshness passed, and the worker's report was honest and
  accurate — yet the fix was incomplete, because `pty_host.py` held a second copy of the
  same guard that the card's `surface:` list never named. Every gate this loop possesses
  would have said yes. What caught it was a supervisor probing a *different* surface
  before a release, which is not a reproducible gate.

  So the drill's real readiness question is: **can the loop detect work that passes every
  gate but is incomplete?** If it cannot, the honest posture stays verify-and-escalate
  (already the default) rather than granting `--allow-merge`. Worth arming one leg
  specifically as a *known* partial fix and seeing whether supervision catches it.
- 2026-07-26 (leg roster erosion) — **Ordinary progress is consuming this drill's
  candidate legs; arm it before more go.** The roster needs 3 small always-green legs and
  has **1 confirmed** (`verify-guidance-long-running-services`). The two candidates named
  in the 2026-07-21 pass were `audit-advisory-interval` and `backlog-default-list` — and
  `backlog-default-list` **shipped this same day** (PR #408), so it is gone as a leg.

  That is a structural dynamic worth seeing, not a one-off: this drill is *fed by* exactly
  the small, low-risk, always-green cards that any productive session naturally clears
  first. The better the throughput, the faster the drill's payload disappears. Two
  consequences: (a) `verify-guidance-long-running-services` must NOT be implemented early
  — it is payload, not free work, and this session nearly took it; (b) the remaining leg
  slots should be **chosen and reserved now**, while candidates still exist, rather than
  discovered empty on 2026-07-29.

  Body-check candidates from the current backlog when arming — and prefer cards whose
  value is mostly *as* a drill leg, so reserving them costs nothing.

  **Reserving a leg is an OPERATION, not a sentence (2026-07-27).** "Chosen and reserved
  now" above had no mechanism, so the reservation lived only in prose — and a wildcard run
  found the consequence: `verify-guidance-long-running-services` was the single card
  `is_autonomous_candidate()` returned, i.e. the deterministic selector was aiming an
  unattended loop at the one card that must not be built. Prose in this card had zero
  effect on that card's machine-readable state.

  So: **to reserve a leg, set that card `readiness: deferred` with a `readiness_reason`
  naming the release trigger** (`released when the drill is armed and this leg is used or
  dropped, or when the drill is abandoned`). Deferred already means "deliberately inactive
  until an explicit trigger or owner review" and is already excluded from
  `is_autonomous_candidate()`, so no new field, state, or code is needed — a reserved leg
  simply stops being selectable. Un-reserving is the same edit in reverse.

  Expect the eligible pool to read **0** while legs are reserved. That is the honest
  number, not a problem to fix by promoting something.
