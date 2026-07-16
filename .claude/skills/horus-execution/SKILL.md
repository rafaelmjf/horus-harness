---
name: horus-execution
description: >-
  Supervise an optional Horus phased execution plan from `.horus/execution.md`.
  Use this when the project's `execution_recommendation` (in `PRD.md` on a v3
  project, `roadmap.md` on a v2 project) says `plan-execution`, when the user
  asks to split a feature into phases, spawn implementation workers/subagents,
  prepare worker handoff notes, or review worker output before continuing to
  the next phase. It keeps `.horus/execution.md` fluid, uses `.horus/temp/` for
  fleeting worker notes, and distills durable outcomes back into `PRD.md` (v3)
  or roadmap/features/decisions/history (v2) at closure.
---

<!-- horus-skill-version: 13 -->

# Horus execution supervision

This skill is for the supervisor agent. It coordinates a bounded implementation
plan without turning `.horus/` into a transcript or a second issue tracker.

## When to use it

- `roadmap.md` has `execution_recommendation: "plan-execution - ..."` or similar.
- The user asks to divide a substantial feature into phases.
- The user is explicitly testing or requesting supervisor/worker model separation.
- A phase should be delegated to a native worker/subagent and reviewed before the
  next phase starts.
- A worker returned a note under `.horus/temp/` that needs supervisor review.

## Confirm delegation already earned its cost

Before creating `execution.md` or a worker handoff, apply `execution-decision` and
its shared rubric. Define the bounded unit and require a concrete dividend that
exceeds the fixed brief/review/gate/merge/closure tax. Do not enter this workflow
merely because work spans projects or phases, or to collect a model datum.

| Situation | Approach |
|---|---|
| High volume, low ambiguity, clear gate (scaffolding, repetitive edits, mechanical refactor with tests) | Delegate, then reproduce the gate. Buys context hygiene + (on a tiered runtime) a cheaper implementation model. |
| Integrity/security-sensitive surface (guarded writes, schema, auth) | Delegating is fine, but keep an independent review *and* reproduce the gate yourself. |
| Small, or ambiguous/exploratory, or debugging/investigation | Stay inline — orchestration overhead and judgment loss dominate. |
| Work where the *user* is the real reviewer (visual/UI) | Delegate the build; the user's eyeball is the gate, not a code-read. |

Runtime matters — name the actual context, parallelism, or price dividend in
`delegation_basis`, using live calibration data for model selection. If no concrete
benefit remains after the task is bounded, stay inline and do not create the plan.
An explicit owner direction to spend expiring isolated-account capacity or protect
supervisor context is also a valid basis when labelled honestly.

## Obtain exact-envelope approval before every worker launch

Before invoking a native subagent or `horus run`, show the owner the exact agent,
concrete model, effort, account alias, current usage/reset evidence with source and
freshness, bounded phase, maximum attempts, expected dividend or owner-directed
override, and verification gate. Wait for explicit approval. A different model,
account, effort, scope, or an attempt beyond the allowance requires renewed approval;
never silently fall back after a provider or capacity failure.

The **concrete model** in that envelope is the exact provider-executable
selector passed to `--model` — not the calibration key. A Horus calibration
key (`sonnet-5`, `haiku-4.5`) documents which model ran for calibration
history but is not itself a valid Claude Code `--model` argument; `claude`
rejects it before any work starts. Name the alias (`sonnet`) or full selector
(`claude-sonnet-5`) in the envelope, and `horus run` also rejects a bare
calibration key before creating a worktree or session. If the executable
selector changes, that is a different envelope and needs renewed approval.

At completion, run `horus datum report` for mechanically captured model/account/
effort/runtime/attempt/outcome and start/end usage evidence. Report a percentage-point
delta only when the report calls fresh same-window isolated readings unconfounded;
otherwise preserve its unknown/confounded label. Do not predict task usage, poll
continuously, or make an extra model call solely for accounting.

If workers overlap on the same provider account, disclose before launch that Horus
cannot attribute the shared percentage change to either worker. Serialize them or use
isolated account aliases when per-worker attribution matters; when throughput matters
more, parallelize and label the readings `concurrent/confounded`.

Be honest about review: in practice most supervisor reviews just confirm green, and a
review is **not** a safety guarantee. The durable safeguards are model-independent (the
working-discipline rules in the managed block): reproduce the gate yourself, bound each
pass to a green committed-and-pushed checkpoint, and put safety in the code (guards),
not the reviewer.

Reproducing the gate means observing a **deterministic signal** yourself, not
re-doing the worker's verification. A *required* CI check green on the worker's exact
commit counts as reproduction of the test gate — do not rerun the suite locally when
a required check already covers it. What always stays yours: **one live probe of the
changed runtime surface** (mocked tests bless nonexistent flags; a screenshot or one
real command run is the floor). Never accept a phase on the handoff note's claims.

## Orchestrating parallel supervisors (orchestrator > supervisor > worker)

When two or more features can run in parallel, a lean orchestrator session can
coordinate multiple feature-supervisor sessions (proven 2026-07-04: three features,
two vendors, two cheap bounces, orchestrator wrote no feature code):

- **The orchestrator implements nothing.** It plans `execution.md`, routes, bounces,
  and accepts. Its hands touch only git mechanics (commit/PR for read-only-.git
  workers), gate commands, and continuity on main. Feature supervisors own
  implementation and drive their own runtime gates.
- **One git worktree per worker** for same-repo parallelism; spawn each with
  `horus run --path <worktree> --watch`. Only the orchestrator edits `.horus/` on main.
- **Posture matrix:** a branch-owning claude worker needs `--posture full-auto` — the
  default posture stalls headless waiting for permission grants and exits 0 with zero
  diffs, a false "completed". A codex worker runs `auto-edit` with a read-only `.git`,
  so the orchestrator owns its commit/push/PR.
- **Briefs carry fences and a sandbox-runnable gate.** Name what each worker must not
  touch (the other workers' surfaces + PRD.md). Codex sandboxes may lack network:
  give a gate the worker can actually run (compileall + targeted tests) or state that
  the orchestrator's gate run is the first full-suite pass.
- **Bounce protocol:** on a failed signal, resume the same worker session
  (`horus run --resume <id>`) with the exact failure output — its context is intact
  and the fix is cheap. Do not fix a worker's phase in the orchestrator context.
- **Merge sequencing:** with non-strict required checks, two individually green PRs
  can land a red main (semantic conflict between phases). After each merge in a
  batch, watch main's push CI before arming the next PR. Cross-phase test glue after
  both phases are accepted is orchestrator mechanics, not a new phase.
- Acceptance per feature is the standard contract: required CI green on the exact
  commit + the handoff gate command run once by the accepting tier + the user's
  eyeball for visual surfaces.

## Steps

1. **Read the continuity.** On a PRD-structure (v3) project, read `.horus/PRD.md`
   (vision/backlog/shipped/rules + the frontmatter handoff fields) and
   `execution.md`. On a six-lane (v2) project, read `.horus/project.md`,
   `roadmap.md`, `features.md`, `decisions.md`, `history.md`, and `execution.md`.
   Either way, review relevant `.horus/temp/*.md` handoff notes only when an
   execution plan is active — that directory is unchanged across both structures.

2. **Get the native prompt.** Run:

   ```bash
   horus execution prompt --target codex
   ```

   or:

   ```bash
   horus execution prompt --target claude
   ```

   Use the printed prompt as the supervisor frame for this project and agent.

3. **Plan or refresh `execution.md`.** Keep it current for the active backlog/roadmap
   item: phases, status, difficulty, mode, model tier, delegation basis, handoff note
   path, and review gate. Replace it when the next substantial item starts. Do not
   archive a timeline there.

   Execution is optional. The planning agent decides whether to use direct work,
   delegated work, or a model-separation test for the current agent/runtime. A phase's
   `worker_tier` is only the intended tier **if delegated**; it is not proof that
   delegation is cheaper. Fill `delegation_basis` with the actual reason: expected
   economics, risk isolation, context splitting, parallelism, or "not worth delegating".
   Different agents may reasonably choose differently.

4. **Authorize, then delegate bounded phases only.** Present the exact consent
   envelope above and wait for explicit owner approval. Then ask native
   workers/subagents to implement one
   phase at a time. Read live tier roles and measured evidence from
   `horus capabilities --models`; use lower-cost tiers only for clear, narrow work
   and reserve stronger reasoning tiers for work whose ambiguity actually needs them.
   If the user is testing model separation, this is a hard gate: do not implement
   the delegated phase in the supervisor context. If a native worker/subagent cannot
   be spawned from the current environment, stop and tell the user that the test
   cannot proceed faithfully here.

   A phase can also be marked for a **cross-agent worker** (`worker_agent: codex` or
   `claude` instead of the default `native`). Spawn it as a one-shot tracked session:

   ```bash
   horus run --agent codex --account <alias> --path . "<phase brief — point it at the handoff note>"
   ```

   The prompt must be self-contained: the worker shares no conversation history with
   the supervisor, so hand it the phase scope, the handoff-note path to fill, and the
   gate to run. `--account` selects an isolated `CODEX_HOME`/`CLAUDE_CONFIG_DIR`
   mapping (`horus account --set-codex-home` / `--set-dir`); omit it for the default
   login. The review contract is unchanged: review the diff and the handoff note,
   then reproduce the gate (deterministic signal + one runtime probe).

5. **Require a handoff note.** Before a worker returns, create or ask it to create:

   ```bash
   horus execution handoff <phase>
   ```

   The worker fills `.horus/temp/<phase>.md` with changed files, behavior, **the
   gate** (one command the supervisor can rerun verbatim, its expected output, and
   the pre-existing failure baseline), risks, and suggested durable Horus updates.
   No proof narratives — the gate command and the CI check speak.

6. **Accept on signals, then continue.** Accept a phase on deterministic signals
   only: the required CI check green on the worker's exact commit (rerun the gate
   locally only when no required check covers it) plus one runtime probe you drive
   yourself. Review the diff and handoff note for scope and risk, not as evidence
   that the work works. For a phase that bulk-copies or migrates files, the gate
   must include a count-and-size reconcile (`horus verify-inventory`) before
   acceptance — a walk returning empty for a known non-empty source is a retry, not
   a pass. If accepted, update the phase status in `execution.md`, ask the user
   before proceeding to the next phase when appropriate, and distill durable
   results at closure with `horus-consolidate`.

## Native mapping

- Claude Code or Codex: use native subagents for bounded worker/reviewer roles only
  when the recorded dividend pays for the handoff. Map live tier roles to the task
  shape; never pin durable guidance to current model names.
- Cross-agent (either supervisor): `worker_agent: codex`/`claude` phases run on the
  other CLI via `horus run --agent <cli>` — a one-shot exec session, registry-tracked.
  Because a cross-vendor worker shares no conversation history, it doubles as an
  honest cold reader of `.horus/` continuity (useful for resume probes).

When the goal is to validate the workflow itself, "delegated" means a distinct worker
agent/session/model actually did the implementation and left a handoff note. A handoff
note written by the supervisor after doing the work does not satisfy the workflow test.

## v2 six-lane projects (fallback)

Everything above is structure-agnostic — phases, delegation judgment, handoff notes,
and `execution.md` itself work the same regardless of whether the project uses
`PRD.md` or the six lanes. The one structure-dependent step is reading the
continuity at the start (Step 1): a v2 project has no `PRD.md`, so read
`.horus/project.md`, `roadmap.md`, `features.md`, `decisions.md`, `history.md`, and
`execution.md` instead — the original six-lane reading list, unchanged. Distilling
durable results at closure (Step 6) likewise goes back to those lanes via
`horus-consolidate`'s v2 path rather than into `PRD.md`.

## Boundaries

- Do not force `execution.md` onto small single-agent tasks.
- Do not delegate just because a table has `worker_tier: standard`; require an explicit
  `delegation_basis` or keep the work direct.
- Do not commit `.horus/temp/` worker notes; they are local, fleeting evidence.
- Do not trust worker notes blindly. Verify the diff and test result before updating
  durable lanes.
- Do not store secrets or full transcripts in `.horus/`.
