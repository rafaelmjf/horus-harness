---
status: idle
current_feature: ""
supervisor_tier: frontier
worker_tier: standard
continuity_tier: economy
last_updated: 2026-06-29
---

# Execution Plan

Fluid, optional plan for the currently active roadmap item. Replace this when
the next substantial feature starts; distill finished work into `roadmap.md`,
`features.md`, `decisions.md`, and `history.md` rather than preserving this as a
timeline.

Current state: no active execution plan. The **GitHub onboarding + workflow policy**
feature completed on 2026-06-29 — all planned phases shipped and merged:

- Track A (A1–A4) + C-min — PR #37; C-full — PR #38; B — PR #39.
- See `features.md` (GitHub untracked-repo onboarding; Horus workflow policy +
  integration helper; Dashboard artifact-staleness badge) and decisions.md
  2026-06-29 "GitHub Onboarding + Workflow Policy".

Only the two **deferred refinements** remain as open roadmap items (optional): project
the `[workflow]` policy into the managed instruction block, and a per-project git-synced
policy override. Replace this file when the next substantial phased feature starts.

## Model Policy

Use tiers instead of hard-coded model names. Resolve them locally per agent,
account, and current model availability.

| tier | Intended use | Examples |
|---|---|---|
| economy | mechanical continuity updates, formatting, small docs from explicit notes | maintainer |
| standard | narrow implementation phases with tests | worker |
| frontier | planning, architecture, risky review, final acceptance | supervisor |

## Active Phases

| phase | status | difficulty | worker_tier | handoff_note | review |
|---|---|---|---|---|---|

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
