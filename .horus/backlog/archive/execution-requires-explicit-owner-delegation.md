---
status: shipped
priority: high
readiness: ready
autonomy: attended
readiness_reason: "Two live false-trigger variants exposed both an authorization gap and a substrate-routing gap. The owner set the categorical boundaries, the negative and positive probes are concrete, and this behavioral contract needs owner review before merge."
created: 2026-07-29
created_by: owner
topic: delegation-calibration
tier: small
type: bug
parallel: safe
surface: "horus/skills.py (execution-decision, horus-consolidate, horus-execution), tests/test_skills.py, projected Claude/Codex skills; native Codex collaboration boundary; related artifact-refresh lifecycle"
shipped_pr: 437
shipped_sha: 240075e
---

# execution-requires-explicit-owner-delegation — authorization and substrate must both be explicit

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

## Second variant — native Codex subagents were routed into Horus workers

Later in the same `fabric-build` campaign, after the direct implementation was
green, the owner asked whether Codex should run the E2E itself or whether the
project could already test with lower models, similar to the earlier Claude
Haiku/Sonnet drill.

Codex loaded `execution-decision`, read `horus capabilities --models`, checked
separate Claude account capacity, and proposed a `horus run` envelope using
Haiku on `claude-work`. That was internally consistent with the skill text, but
it answered a different question. The owner meant **Codex's native
`spawn_agent` capability inside the current supervising session**, without
necessarily switching provider, CLI session, or account.

The current vocabulary makes that mistake easy:

- `execution-decision` describes one “subagents substrate” containing both
  native subagents and `horus run` workers;
- its only delegated mode is `subagent-plan`;
- the emitted contract then always requires an external agent/model/account/
  usage envelope and routes through `horus-execution` / `execution.md`.

Those are different execution substrates with different costs and semantics:

| Substrate | Session/account | Coordination |
|---|---|---|
| Native Codex subagent | child of the current Codex supervisor; normally the same account/runtime | Codex collaboration tools; bounded task and supervisor synthesis |
| Horus worker | tracked external agent-CLI session; may select another provider/model/account/worktree | `horus run`, usage/account envelope, receipts, and optionally `horus-execution` |

An explicit request to “use a subagent” authorizes delegation, but **does not
authorize changing substrate, provider, account, or session topology**. When the
owner names Codex's own spawning capability or same-session agents, Horus worker
routing is out of scope. When “lower model” is ambiguous, ask which substrate
they mean before reading account usage or proposing a dispatch envelope.

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
- Treat native Codex subagents and Horus external workers as separate modes.
  Native subagents use the current session's collaboration substrate and do not
  imply `horus run`, account switching, `execution.md`, or Horus usage routing.
- Delegation authorization is substrate-bounded. “Spawn a native Codex
  subagent” is not permission to launch Claude/another account; “dispatch this
  through Horus on another account” is the explicit external-worker case.
- If the owner asks about “lower models” or “subagents” without identifying the
  substrate and the answer would change provider/account/session topology, ask
  one clarification question before routing.
- Cost grounding still applies to native fan-out, but it must use the native
  collaboration contract rather than manufacturing a Horus worker envelope.

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
- Native-subagent probe: “use Codex's own agent spawning in this supervising
  session” may recommend or launch a native Codex child, but does not load
  `horus-execution`, create `execution.md`, inspect another account's usage, or
  propose `horus run`.
- External-worker probe: “run this through Horus on the Claude work account”
  uses the calibrated model/account/usage consent envelope and the tracked
  worker flow.
- Ambiguous-substrate probe: “can lower models test this?” asks whether the owner
  means native Codex children or a Horus-managed external worker before changing
  provider/account/session topology.
- Canonical `horus-consolidate` and `horus-execution` text plus both Claude/Codex
  projections carry the categorical authorization boundary; the canonical
  `execution-decision` text and its projections carry the substrate split.
  Edited bundled skill versions are bumped.
- Tests lock the negative and positive wording, and the full suite is green on
  the exact SHA.

## Related

- Shipped predecessor: `backlog/archive/horus-execution-general-plan-false-trigger.md`
  (#407).
- Stale projection lifecycle: `backlog/skill-drift-surfacing-and-refresh.md`.
- Live consumer at incident time:
  `fabric-build/.agents/skills/horus-consolidate` v15 and
  `fabric-build/.agents/skills/horus-execution` v14.
