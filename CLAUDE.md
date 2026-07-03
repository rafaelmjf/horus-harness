# Claude Code Instructions

> **PRD structure v3 (2026-07-03).** This repo's `.horus/` is **`PRD.md` +
> `sessions/`** and the managed block below is PRD-native (block v3, tooling reads
> PRD frontmatter directly — no shims). Retired v2 lanes are preserved in
> `.horus/archive/`; do not restore the six-lane split.

<!-- HORUS:BEGIN shared-instructions -->
<!-- horus-block-version: 3 -->
## Horus Project Continuity

This repository uses `.horus/` for project continuity.

**You — the agent in this session — maintain `.horus/`, filling it from the context
you hold in this conversation.** The `horus` CLI only scaffolds templates and emits
deterministic signals/checks; it never parses files to write content for you, because
it cannot see this session. Update continuity by invoking the **`horus-consolidate`**
skill (it can see this conversation) and writing in what actually happened — decisions
and why, what shipped, dead ends, the next step.

Before substantial work, read `.horus/PRD.md` — the one maintained continuity file:

- Vision — what this project is, its shape, its boundaries.
- Backlog — prioritized open work (the *what's next*), features and bugs together.
- Shipped — one line per capability; details live in git history.
- Rules — concise current rules, grouped by topic (not a log).
- Frontmatter carries `current_focus` / `next_action` / `next_prompt` /
  `execution_recommendation` / `last_updated`, read PRD-first by the dashboard,
  `horus resume`, and the merge freshness gate.
- Review recent local session summaries in `.horus/sessions/` when available.
- Review fleeting worker/subagent notes in `.horus/temp/` when an execution plan
  is active; distill only the durable results upward.
- If this project instead has `project.md` / `roadmap.md` / `features.md` /
  `decisions.md` / `history.md` and no `PRD.md`, it is on the older six-lane
  structure — read those lanes directly (each stays in its lane); migrating to
  `PRD.md` is a separate, opt-in step and does not happen automatically.

After work that contributes to the project state, close the session by invoking the
`horus-consolidate` skill and folding in this session's context:

- Add a concise session summary under `.horus/sessions/` (scaffold with
  `horus session new "<title>"`, then write what actually happened — not just a date).
- Update PRD.md: refresh its frontmatter (`current_focus`, `next_action`,
  `next_prompt`, `execution_recommendation`, `last_updated`), move any work that
  shipped from Backlog to Shipped (one line), and record durable rules under Rules.
- Implementation workers may write brief phase handoff notes under `.horus/temp/`;
  the supervising agent reviews those notes and folds the durable outcome into PRD.md.
- `execution_recommendation` says whether the next step should use a phased
  execution plan (`.horus/execution.md` + worker/subagent handoffs) or continue as
  a direct single-agent task.
- `horus consolidate` / `horus close` are signal + verification only — you supply the
  content from the session; they never rewrite `.horus/` for you.
- Do not store secrets or full transcripts in `.horus/`.

Working discipline (every session, whether or not the work is delegated):

- **Reproduce the gate; never trust the report.** Re-run the build/tests/check yourself
  and watch it pass before calling work done — whether a worker did it or you did. A
  confident "tests pass" is not evidence.
- **Bound each step to a green, committed-and-pushed checkpoint**, so there is always a
  clean resume point and nothing half-finished stranded only on this machine.
- **Put safety in the code, not the reviewer.** Guards and invariants prevent the
  dangerous class of bug; review — human or model — misses things, so it is a help, not
  a guarantee.

Instruction synchronization:

- Keep this shared Horus-managed block aligned with the matching block in `AGENTS.md`.
- Agent-specific instructions may live outside the Horus-managed block.
<!-- HORUS:END shared-instructions -->

## Claude Notes

- Prefer planning before larger edits.
- Keep the project lightweight and shaped around current user needs.
