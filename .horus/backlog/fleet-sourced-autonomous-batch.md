---
status: shelved
shelved_on: 2026-08-01
priority: medium
created: 2026-07-20
created_by: owner
last_refined: 2026-07-28
refine_passes: 2
readiness: shaping
readiness_reason: "Which project goes first, envelope bounds, batch size, and the task-finding pass in each target repo are undecided; refine before any dispatch."
topic: autonomous-dispatch
type: feature
---

# fleet-sourced-autonomous-batch — feed the loop from the fleet, trip-timed

## Why

The autonomous loop (envelope → scheduled run → independent supervision →
merge/escalate) is built and proven exactly once, then starved: this repo has
one Ready—Autonomous eligible card. The owner's verdict at the 2026-07-20
roadmap-branches gate widened the supply pool: low-ceremony personal fleet
projects — `agentic-gym-coach` and `agentic-travel-guide` named — hold real,
well-defined tasks that suit unattended execution. An upcoming owner trip
makes away-mode throughput timely. Guard inherited from the branch: tasks must
be real wants of those projects, never manufactured to feed the loop.

## Intended outcome

The loop consumes ≥3 real cards unattended across ≥2 fleet projects: tasks
found and refined Ready—Eligible in the target projects' own backlogs, armed
under bounded envelopes on this machine, supervised, merged via each repo's
policy, with the aggregate Telegram landing. Afterwards the loop's
"proven at volume" claim is evidence, not hope.

## Broad boundaries

Coordination lives here; task cards live in the target repos (second-order:
the task-finding pass's findings become cards THERE). The existing
`cockpit-autonomous-dispatch-contract` skill is the sequencer — this card adds
no new machinery. Non-goals: no new Horus features to enable it; no BI
projects (owner: post-trip); no relaxing the never-manufacture-work guard.

## Open decisions

- First target project and the task-finding session's shape. [session] — needs a working
  session in the target repo, not a refinement exchange.
- Envelope bounds per project (attempts, expiry, merge authority — likely
  verify+escalate-only first). [session] — and note it is downstream of the drill: whether
  `--allow-merge` is ever granted is what the drill decides.
- ~~Whether `autotest-e2e-away-mode-drill` runs before or as part of this batch.~~
  **Settled 2026-07-28: the drill runs FIRST, separately.** [refine] — the drill exists to
  answer whether the loop can detect work that passes every gate but is incomplete. Pointing
  a multi-project batch at real fleet repos before that answer exists is precisely the risk
  the drill was written to retire.

## Reviews

- 2026-07-28 — **high → medium; trip premise spent; drill ordering settled** (owner, refine
  pass). This card's urgency rested on "an upcoming owner trip makes away-mode throughput
  timely"; X3 records that trip as 2026-07-22 + 6 days, so it has passed and the urgency
  argument is spent. The underlying supply problem is structural, not seasonal — the loop
  still starves at 0 eligible cards — so the card is kept, not dropped, at medium. One of its
  three open decisions was resolved in the same exchange (drill first, separately); the other
  two are both `[session]`-class and downstream of the drill's verdict on merge authority.

## Source

`.horus/research/2026-07-20-roadmap-branches-rebaseline.md`, branch C + owner
verdict section.
