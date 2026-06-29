---
status: idle
current_feature: ""
supervisor_tier: frontier
worker_tier: standard
continuity_tier: economy
delegation_basis: ""
last_updated: 2026-06-29
---

# Execution Plan

Fluid, optional plan for the currently active roadmap item. Replace this when
the next substantial feature starts; distill finished work into `roadmap.md`,
`features.md`, `decisions.md`, and `history.md` rather than preserving this as a
timeline.

Current state: no active execution plan. The dashboard follow-up completed on
2026-06-29 and was distilled into the durable lanes:

- Phase 1A fixed GitHub Ignore/Unignore POST UX: trusted `owner/repo` validation +
  `303 Location: /#github-catalog` PRG, with tests.
- Phase 1A also exposed a workflow failure: the supervisor implemented delegated work.
  `horus-execution` v2 now makes real delegation mandatory when model separation is
  being tested.
- Phase 1B then validated the corrected workflow: a real standard-tier worker
  implemented `horus resume`, the dashboard/start integration, tests, and a handoff
  note; the frontier supervisor reviewed and accepted it.

Replace this file when the next substantial phased feature starts.

## Model Policy

Use tiers instead of hard-coded model names. Resolve them locally per agent,
account, and current model availability.

`worker_tier` is the intended tier **if** a phase is delegated; it is not a claim
that delegation is cheaper or mandatory. The planning agent must fill
`delegation_basis` with the reason to delegate or the reason to keep the work direct
for this agent/runtime. Different agents may reasonably choose differently.

| tier | Intended use | Examples |
|---|---|---|
| economy | mechanical continuity updates, formatting, small docs from explicit notes | maintainer |
| standard | narrow implementation phases with tests | worker |
| frontier | planning, architecture, risky review, final acceptance | supervisor |

## Active Phases

| phase | status | difficulty | mode | worker_tier | delegation_basis | handoff_note | review |
|---|---|---|---|---|---|---|---|

## Worker Handoff Contract

Implementation workers should write a brief note in `.horus/temp/` when a phase
finishes. Keep it factual and reviewable:

- changed files / behavior;
- tests run and result;
- risks or follow-ups;
- suggested durable `.horus/` updates.

**Supervisor brief convention (pilot finding 2026-06-29):** each worker brief states the
**known pre-existing test-failure baseline** so a worker does not misattribute an unrelated
red test to its own change. Current known-failing baseline:
`tests/test_config.py::test_workspace_root_defaults_and_round_trips` (non-portable
forward-slash path assertion on Windows; unrelated — a fix is queued as a separate task).

The supervisor reviews the diff and the handoff, then updates the durable lanes.

Useful commands:

- `horus execution prompt --target codex` prints a supervisor prompt shaped for
  Codex subagents/custom agents.
- `horus execution prompt --target claude` prints the Claude Code equivalent.
- `horus execution handoff <phase>` creates `.horus/temp/<phase>.md` for a worker note.
