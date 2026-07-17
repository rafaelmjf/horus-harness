---
status: open
priority: medium
created: 2026-07-17
tier: opus
type: feature
parallel: safe
phase: converge
vision_facet: "Autonomous dispatch"
branch: vision-branch-x3-scheduling-and-autonomous-execution
created_by: owner
depends-on: schedule-local-dispatcher, standing-dispatch-envelope
surface: new .claude/skills/<name>/SKILL.md (+ .agents/skills mirror); references horus-agent/.horus/PRD.md to wire the loop; composes existing dispatch-decision / execution-decision / delegation-rubric / scope-cards skills
---

# cockpit-autonomous-dispatch-contract — a skill wiring discover→pick→scope→dispatch/schedule→supervise

**Why (owner, 2026-07-17):** all the pieces of the owner's loop exist as separate skills and
commands, but nothing ties them into one contract a cockpit session can follow to run
autonomous, scheduled, cross-account dispatch. The owner wants to open a horus-agent cockpit
session and say "check the backlog, pick something, scope it if needed, launch it (attachable,
right account, scheduled if asked), and schedule a supervisor to close it out or ping me". The
substrate rule is fixed: **harness owns capability / skills live in the harness**, and
horus-agent "never grows code" — so this is a *skill* (in horus-harness) that horus-agent's PRD
references. Part of the `vision-branch-x3-scheduling-and-autonomous-execution` divergence.

## Idea

A cockpit skill that sequences the existing machinery, owner-gated throughout:

1. **Discover** — `horus fleet --backlog --stdout` (or `--review`) to enumerate active cards
   across the fleet.
2. **Pick** — owner selects (or the skill proposes, ranked by priority).
3. **Ready-gate** — judge scope via the self-sufficiency test (converge card + `vision_facet`
   + testable acceptance + `surface`/`parallel`). If thin → route through `pathfinder` /
   `roadmap-branches` / `scope-cards` to make it dispatch-ready first.
4. **Decide** — `dispatch-decision` skill → mode + isolated **account** (gated on `horus usage
   check`, routed away from the overseer account) + tier→**model** + verification depth +
   a consent envelope. Flag "well-scoped-for-agent vs needs-owner-supervision" explicitly.
5. **Dispatch or schedule** — dispatch now, or `horus schedule --at ...` (this machine,
   non-recurring), **attachable + worktree by default**, under the chosen account
   (claude-personal / claude-work / codex-personal).
6. **Supervise** — schedule a `horus supervise` run to verify → merge → close, or escalate.
7. **Owner-consent gate** — nothing launches without the explicit envelope
   (agent + concrete model + account + effort + bounded task + acceptance gate + dividend),
   matching the existing hard boundary: cockpit modes never auto-rank, auto-dispatch, or
   choose a model.

## Acceptance

- A cockpit session, following this skill, can take a chosen card from discovery to a
  launched (or scheduled) attachable worker with a paired supervisor, producing the consent
  envelope for owner approval at the launch boundary.
- horus-agent's PRD references the skill as the cockpit's autonomous-dispatch entry point.
- The skill never selects a model, routes an account, or launches without owner approval.

## Open questions

- How much the skill *automates* vs *proposes* (default: proposes + owner confirms each gate).
- Whether it lives beside `dispatch-decision` or wraps it.
- How a scheduled supervisor's result loops back into the cockpit's next session.

## Notes

- Consumer of `schedule-local-dispatcher`, `unattended-dispatch-attachable-worktree-defaults`,
  and `supervise-verify-merge-close`; depends on the scheduler existing. `parallel: safe`
  (skill files, separate surface from the `horus/cli.py` cards).
