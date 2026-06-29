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

<!-- horus-skill-version: 1 -->

# Horus execution supervision

This skill is for the supervisor agent. It coordinates a bounded implementation
plan without turning `.horus/` into a transcript or a second issue tracker.

## When to use it

- `roadmap.md` has `execution_recommendation: "plan-execution - ..."` or similar.
- The user asks to divide a substantial feature into phases.
- A phase should be delegated to a native worker/subagent and reviewed before the
  next phase starts.
- A worker returned a note under `.horus/temp/` that needs supervisor review.

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
   phases, status, difficulty, model tier, handoff note path, and review gate. Replace
   it when the next substantial roadmap item starts. Do not archive a timeline there.

4. **Delegate bounded phases only.** Ask native workers/subagents to implement one
   phase at a time. Use cheaper/faster tiers only for clear, narrow work; keep
   frontier-tier reasoning for architecture, risky review, and final acceptance.

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
  equivalent workers for narrow implementation phases.
- Codex: use subagents or project custom agents for bounded workers/reviewers when
  useful. Map frontier to strong/high-reasoning supervision, standard to worker
  implementation, and economy to mechanical continuity or formatting updates.

## Boundaries

- Do not force `execution.md` onto small single-agent tasks.
- Do not commit `.horus/temp/` worker notes; they are local, fleeting evidence.
- Do not trust worker notes blindly. Verify the diff and test result before updating
  durable lanes.
- Do not store secrets or full transcripts in `.horus/`.
