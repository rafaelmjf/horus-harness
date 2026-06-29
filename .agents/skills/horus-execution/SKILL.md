---
name: horus-execution
description: >-
  Supervise an optional Horus phased execution plan from `.horus/execution.md`.
  Use this when `roadmap.md` recommends `plan-execution`, when the user asks to
  split a feature into phases, spawn implementation workers/subagents, prepare
  worker handoff notes, or review worker output before continuing to the next phase.
  It keeps `.horus/execution.md` fluid, uses `.horus/temp/` for fleeting worker
  notes, and distills durable outcomes back into roadmap/features/decisions/history
  at closure.
---

<!-- horus-skill-version: 4 -->

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

## Deciding to delegate (volume × ambiguity × runtime)

Delegation — spinning a *separate* worker agent/session to implement a phase — is a
judgment call, not a default. Decide on implementation **volume** and **ambiguity**,
then weigh what delegation actually buys on *this* runtime:

| Situation | Approach |
|---|---|
| High volume, low ambiguity, clear gate (scaffolding, repetitive edits, mechanical refactor with tests) | Delegate, then reproduce the gate. Buys context hygiene + (on a tiered runtime) a cheaper implementation model. |
| Integrity/security-sensitive surface (guarded writes, schema, auth) | Delegating is fine, but keep an independent review *and* reproduce the gate yourself. |
| Small, or ambiguous/exploratory, or debugging/investigation | Stay inline — orchestration overhead and judgment loss dominate. |
| Work where the *user* is the real reviewer (visual/UI) | Delegate the build; the user's eyeball is the gate, not a code-read. |

Runtime matters — name it in `delegation_basis`:

- A frontier *supervisor* + cheaper *worker* tiers (e.g. Claude Opus + Sonnet/Haiku)
  gains **both** context hygiene and a cheaper tier, so its bar to delegate is lower.
- A single strong model (e.g. GPT-5.5 in Codex) gains **mostly context hygiene**, so its
  bar is higher — staying inline is often right unless the volume would flood the
  context window.

Be honest about review: in practice most supervisor reviews just confirm green, and a
review is **not** a safety guarantee. The durable safeguards are model-independent (the
working-discipline rules in the managed block): reproduce the gate yourself, bound each
pass to a green committed-and-pushed checkpoint, and put safety in the code (guards),
not the reviewer.

## Steps

1. **Read the lanes.** Read `.horus/project.md`, `roadmap.md`, `features.md`,
   `decisions.md`, `history.md`, and `execution.md`. Review relevant `.horus/temp/*.md`
   handoff notes only when an execution plan is active.

2. **Get the native prompt.** Run:

   ```bash
   horus execution prompt --target codex
   ```

   or:

   ```bash
   horus execution prompt --target claude
   ```

   Use the printed prompt as the supervisor frame for this project and agent.

3. **Plan or refresh `execution.md`.** Keep it current for the active roadmap item:
   phases, status, difficulty, mode, model tier, delegation basis, handoff note path,
   and review gate. Replace it when the next substantial roadmap item starts. Do not
   archive a timeline there.

   Execution is optional. The planning agent decides whether to use direct work,
   delegated work, or a model-separation test for the current agent/runtime. A phase's
   `worker_tier` is only the intended tier **if delegated**; it is not proof that
   delegation is cheaper. Fill `delegation_basis` with the actual reason: expected
   economics, risk isolation, context splitting, parallelism, or "not worth delegating".
   Different agents may reasonably choose differently.

4. **Delegate bounded phases only.** Ask native workers/subagents to implement one
   phase at a time. Use cheaper/faster tiers only for clear, narrow work; keep
   frontier-tier reasoning for architecture, risky review, and final acceptance.
   If the user is testing model separation, this is a hard gate: do not implement
   the delegated phase in the supervisor context. If a native worker/subagent cannot
   be spawned from the current environment, stop and tell the user that the test
   cannot proceed faithfully here.

5. **Require a handoff note.** Before a worker returns, create or ask it to create:

   ```bash
   horus execution handoff <phase>
   ```

   The worker fills `.horus/temp/<phase>.md` with changed files, behavior, tests,
   risks, and suggested durable Horus updates.

6. **Review, then continue.** The supervisor reviews the diff, tests, and handoff
   note. If accepted, update the phase status in `execution.md`, ask the user before
   proceeding to the next phase when appropriate, and distill durable results at
   closure with `horus-consolidate`.

## Native mapping

- Claude Code: use project subagents for bounded worker/reviewer roles when useful.
  Keep Opus/frontier-equivalent work on supervision and review; use Sonnet/standard-
  equivalent workers for narrow implementation phases. Claude's cost/latency/review
  tradeoffs may differ from Codex; record the local rationale.
- Codex: use subagents or project custom agents for bounded workers/reviewers when
  useful. Map frontier to strong/high-reasoning supervision, standard to worker
  implementation, and economy to mechanical continuity or formatting updates. Codex's
  cost/latency/review tradeoffs may differ from Claude; record the local rationale.

When the goal is to validate the workflow itself, "delegated" means a distinct worker
agent/session/model actually did the implementation and left a handoff note. A handoff
note written by the supervisor after doing the work does not satisfy the workflow test.

## Boundaries

- Do not force `execution.md` onto small single-agent tasks.
- Do not delegate just because a table has `worker_tier: standard`; require an explicit
  `delegation_basis` or keep the work direct.
- Do not commit `.horus/temp/` worker notes; they are local, fleeting evidence.
- Do not trust worker notes blindly. Verify the diff and test result before updating
  durable lanes.
- Do not store secrets or full transcripts in `.horus/`.
