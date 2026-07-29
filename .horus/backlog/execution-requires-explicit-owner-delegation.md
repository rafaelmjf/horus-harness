---
status: open
priority: high
readiness: ready
autonomy: attended
readiness_reason: "A second live false trigger exposed two exact instruction gaps. The owner set the categorical boundary, the negative and positive probes are concrete, and this behavioral contract needs owner review before merge."
created: 2026-07-29
created_by: owner
vision_facet: "Delegation calibration"
tier: small
type: bug
parallel: safe
phase: converge
surface: "horus/skills.py (horus-consolidate + horus-execution), tests/test_skills.py, projected Claude/Codex skills; related artifact-refresh lifecycle"
---

# execution-requires-explicit-owner-delegation — task breadth must never activate supervision

## Why — live recurrence, 2026-07-29

In `fabric-build`, the next ready card crossed SQL schema, a User Data Function,
11 notebook readers, pipeline definitions, install lifecycle, CLI safety
contracts, documentation, and a live probe. During continuity closure, Codex
changed:

```yaml
execution_recommendation: "continue-as-is ..."
```

to:

```yaml
execution_recommendation: "plan-execution — ... spans ... independently green pushed checkpoints"
```

The owner had not requested delegation, workers, subagents, handoffs, model
separation, or supervision. The recommendation was inferred solely from the
work's breadth.

When the owner then asked “what's the next step?”, Codex treated that field as a
trigger, loaded `horus-execution`, ran `horus execution prompt --target codex`,
and proposed creating `.horus/execution.md`. The owner asked why; Codex correctly
recognized that the backlog card plus ordinary branch checkpoints were sufficient.
No execution plan or worker was created.

Owner contract:

> Execution should be invoked only when I specify that the task should be delegated.

Large, multi-surface, multi-phase, or long-running work remains direct by default.
Those properties may affect an inline plan, but they do not grant authority to
create a supervisor/worker workflow.

## Why the previous fix did not hold

This is the same failure class as shipped
`horus-execution-general-plan-false-trigger` (#407), but it returned through a
different path:

1. The current `horus-consolidate` v15 text already says to default to
   `continue-as-is`, invoke `execution-decision` only when the owner explicitly
   asks about delegation, and not treat multiple phases as a dividend. The agent
   still inferred `plan-execution` from breadth, so “default” and the indirect
   decision-skill wording were not categorical enough at the point where the
   field is authored.
2. `fabric-build` had the current consolidate skill v15 but a stale projected
   `horus-execution` v14. That older trigger says to load whenever
   `execution_recommendation` says `plan-execution` and still lists splitting a
   substantial feature into phases. The canonical Horus skill is v15, but a
   source fix that has not reached a consumer project cannot protect that
   project.

The general detection/selection/integration problem for stale managed assets
already belongs to `skill-drift-surfacing-and-refresh`; do not duplicate that
architecture here. This card owns the delegation-only semantic contract and
records the stale-projection dependency as evidence that the refresh card matters.

## Contract to enforce

- `horus-consolidate` must say categorically: when the owner did not explicitly
  request delegation in this conversation, write
  `execution_recommendation: continue-as-is` regardless of task breadth, phase
  count, or number of surfaces. Never infer delegation.
- `horus-execution` must not treat `execution_recommendation: plan-execution`
  alone as fresh authorization. Initial invocation requires an explicit owner
  request for delegation/worker/subagent/dispatch/handoff/model separation/
  supervision.
- Resuming an already-active execution plan or reviewing an existing worker
  handoff remains valid because the owner authorization happened when that plan
  was created. The durable plan is continuation evidence, not a way to infer a
  new delegation.
- `execution_recommendation` records an owner-authorized execution choice; it is
  not a task-size classifier.
- Keep native inline planning artifact-free: no `.horus/execution.md` for
  ordinary sequencing, however large the task.

## Acceptance

- Negative cold-context probe: a broad card spanning six product surfaces, with
  no delegation request, consolidates to `continue-as-is` and a later “what's
  next?” does not load `horus-execution`, run `horus execution prompt`, or
  propose `.horus/execution.md`.
- Negative field probe: a stray/stale `plan-execution` recommendation with no
  active execution plan and no explicit owner delegation request is called out
  as stale intent, not treated as authorization.
- Positive cold-context probe: “delegate this task to a worker and supervise it”
  invokes the decision/execution flow.
- Positive resume probe: an existing owner-authorized active execution plan or
  worker handoff resumes without requiring the owner to restate the delegation
  on every turn.
- Canonical `horus-consolidate` and `horus-execution` text plus both Claude/Codex
  projections carry the categorical boundary; edited bundled skill versions are
  bumped.
- Tests lock the negative and positive wording, and the full suite is green on
  the exact SHA.

## Related

- Shipped predecessor: `backlog/archive/horus-execution-general-plan-false-trigger.md`
  (#407).
- Stale projection lifecycle: `backlog/skill-drift-surfacing-and-refresh.md`.
- Live consumer at incident time:
  `fabric-build/.agents/skills/horus-consolidate` v15 and
  `fabric-build/.agents/skills/horus-execution` v14.
