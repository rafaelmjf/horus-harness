---
status: open
priority: high
created: 2026-07-19
vision_facet: "Autonomous dispatch"
phase: converge
tier: sonnet
type: feature
parallel: safe
created_by: agent
surface: horus/supervise.py (target resolution) + horus/schedule.py / horus/cli.py (a scheduled worker+supervisor pairing)
---

# schedule-supervise-resolve-target-at-fire-time — break the worker→supervise chicken-and-egg

**Why (blocking the fully-scheduled away-mode drill, 2026-07-19):** the autonomous
loop today is "launch the worker NOW (`horus run --unattended --detach` → returns a
session id) THEN `horus schedule run -- supervise <id>`" (see the Rule "A scheduled
supervise needs its session id at schedule time"). That means the WORKER cannot be
scheduled — it must run while the owner is still present — so an owner who wants to
arm everything and THEN close the session cannot get autonomous supervise+merge on
scheduled work. `horus supervise` resolves only a concrete session-id/prefix or a
PR, neither of which exists before the worker launches. `autotest-e2e-away-mode-drill`
needs both worker and supervisor armed to fire AFTER close.

## How

- Teach `horus supervise` to accept a **deferred target** that resolves at fire
  time, not schedule time: e.g. `supervise --card <name>` / `--branch auto/<card>`
  resolves to the most-recent matching worker session (or its PR) in the registry
  when the supervisor actually runs. Refuse ambiguous/none with a clear escalation
  (never guess), preserving "never trust a self-report".
- Merge authority must survive this path: a deferred target that resolves to a real
  session with a pinned dispatch base keeps `--allow-merge` + `--probe` semantics
  (a bare PR-ref stays verify+escalate-only, per the existing Rule).
- Offer a paired arming so the drill is one step, not hand-wired: e.g.
  `horus schedule dispatch --card X --account Y --envelope E --at +Am --supervise-at +Bm`
  writes the worker timer AND a supervisor timer whose target is the deferred
  card/branch selector. Keep it thin over `schedule`/`run`/`supervise` — no new
  state store; systemd owns the timers as today.

## Acceptance

- A worker dispatch and its supervisor can BOTH be scheduled before either runs;
  with the session closed, the worker fires, then the supervisor resolves that
  worker's session/PR by card/branch and verifies → merges (envelope-authorized) or
  escalates — no session id known at arm time.
- Ambiguous/no-match resolution escalates (andon), never merges the wrong thing.
- Existing id/PR-targeted supervise paths and their tests are unchanged.

## Non-goals

- Not relaxing the acceptance gate (still required CI on the exact resolved head
  SHA + freshness + probe before any merge).
- Not a cross-machine dispatch/registry — single machine, systemd `--user` timers.
