---
status: shipped
priority: high
readiness: ready
autonomy: eligible
readiness_reason: "A live false trigger identified the exact conflicting skill text, the owner clarified the intended delegation-only boundary, and the negative/positive trigger probes are concrete."
created: 2026-07-24
created_by: codex
vision_facet: "Delegation calibration"
tier: small
type: bug
parallel: safe
phase: converge
surface: "horus/skills.py (_EXECUTION_SKILL), tests/test_skills.py, projected horus-execution skills"
shipped_pr: 407
shipped_sha: 5a0a67f
---

# horus-execution-general-plan-false-trigger — ordinary planning enters the worker-supervision workflow

## Why — live incident, 2026-07-24

In `fabric-metadata-driven-medallion`, the owner asked:

> do we need a proper plan or are you good to start?

Codex treated that ordinary implementation-planning question as a
`horus-execution` trigger, announced the skill, read the execution supervisor
prompt, and proposed creating `.horus/execution.md`. The owner corrected the
boundary: **`horus-execution` is for dispatching/supervising work performed by
other agents, not for making a general implementation plan.**

The false trigger interrupted the product discussion with delegation ceremony
that had no worker, handoff, or supervision job to do. It also risked creating a
Horus execution artifact for a standalone CLI/TUI project plan that needed only
ordinary in-session reasoning.

## Contract defect

The bundled skill currently invites this behavior in two places:

- Its description says to use it when the user “asks to split a feature into
  phases”.
- `## When to use it` repeats “The user asks to divide a substantial feature
  into phases.”

Those phrases match ordinary planning language even when the user has not asked
for a worker, subagent, dispatch, handoff, model separation, or supervision.
Later text says not to enter merely because work spans phases, but that negative
instruction arrives only after the overly broad trigger has already loaded the
skill.

This regresses the owner-invoked delegation boundary recorded in
`review-session-control-calibration`: ordinary building, fixing, reviewing, or
planning must not load delegation machinery; only an explicit request about
delegation or a worker/subagent plan does.

## What to change

- Define `horus-execution` as the supervisor workflow for work that is actually
  delegated/dispatched to one or more other agent sessions.
- Remove generic “split/divide a feature into phases” language from the
  description and trigger list.
- Add an explicit negative trigger near the top: requests for a plan, phased
  implementation, sequencing, estimation, or “are you ready to start?” do not
  invoke this skill unless they also request another agent/worker/subagent,
  dispatch, handoff, model separation, or supervision.
- Keep resuming an already-active delegated execution plan and reviewing an
  existing worker handoff as valid triggers.
- Align the `execution_recommendation: plan-execution` wording so it denotes a
  worker/supervisor execution plan, not any multi-step task. Ordinary phased
  work remains direct and needs no `.horus/execution.md`.
- Refresh both Claude and Codex projected skill copies from the single
  `horus/skills.py` source.

Do not introduce a new general-planning skill or artifact as part of this fix.
Native agent planning remains the default.

## Acceptance

- Negative cold-context probe: “Do we need a proper plan or are you good to
  start?” does **not** load `horus-execution`, run `horus execution prompt`, or
  propose `.horus/execution.md`.
- Negative cold-context probe: “Split this implementation into four phases”
  stays ordinary inline planning when no other-agent intent is present.
- Positive cold-context probe: “Delegate this implementation to two workers and
  supervise the phases” loads `horus-execution`.
- Positive resume probe: an existing delegated `.horus/execution.md` or worker
  handoff still loads the supervision workflow.
- Tests lock the delegation-only trigger wording in the canonical skill and
  verify both projected copies match it.
- Full suite green on the exact SHA.

## Source

Owner-attended Codex conversation in `fabric-metadata-driven-medallion`,
2026-07-24. No `.horus/execution.md` was created there.
