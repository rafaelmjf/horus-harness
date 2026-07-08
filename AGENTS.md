# Agent Instructions

> **PRD-structure prototype (2026-07-03) — overrides the lane instructions in the
> managed block below.** This repo's `.horus/` is now **`PRD.md` + `sessions/`**:
> read `.horus/PRD.md` before substantial work (vision, backlog, shipped, rules);
> `project.md`/`roadmap.md` are frontmatter-only shims for the tooling; retired
> lanes live in `.horus/archive/`. Closure = update PRD backlog/shipped + shim
> frontmatters + a session note (`horus session new`), then
> `horus close --commit --push`. Run `horus consolidate` at most once and ignore
> its lane-routing warnings — do not restore the six-lane split.

<!-- HORUS:BEGIN shared-instructions -->
<!-- horus-block-version: 6 -->
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

- **Reproduce the gate; never trust the report.** Before calling work done, observe a
  deterministic signal yourself: rerun the check locally, or watch a *required* CI
  check go green on the exact commit — plus one live probe of the changed surface.
  A confident "tests pass" in prose is not evidence, whoever wrote it.
- **Bound each step to a green, committed-and-pushed checkpoint**, so there is always a
  clean resume point and nothing half-finished stranded only on this machine.
- **Put safety in the code, not the reviewer.** Guards and invariants prevent the
  dangerous class of bug; review — human or model — misses things, so it is a help, not
  a guarantee.
- **Ground token-intensive actions before spending.** Before an action that fans out
  many subagents or otherwise burns a large amount of tokens (multi-agent workflows,
  broad research sweeps, whole-repo re-reads, adversarial verification passes), first
  state why the cheaper path (a direct search, a single agent, a targeted read) is
  insufficient, size the spend to the task, and — unless already authorized for this
  session — get the user's confirmation. Thoroughness is a dial, not a default: match
  it to the question, and prefer the lightest tool that answers it.

Version floor (check before writing `.horus/`):

- **An outdated `horus` CLI can silently regress this project to the retired six-lane
  structure.** Before running any state-mutating `horus` command (`init`,
  `upgrade-project`, `consolidate`, `close`, `reconcile`, `session new`, `infer`,
  `distill-history`), confirm the installed CLI is new enough: run `horus --version`
  and compare it to `horus_min_version` in `.horus/PRD.md` frontmatter (fall back to
  `0.0.26` if this project predates that stamp).
- If the installed version is **below** the floor — or `horus` errors that a
  subcommand you need does not exist — **STOP.** Do not scaffold or write `.horus/`.
  Tell the user to upgrade first (`uv tool install --force --python 3.12
  horus-harness`) and re-launch. A read-only `horus resume` / reading `.horus/` by
  hand is fine; only *writes* are gated.

Instruction synchronization:

- Keep this shared Horus-managed block aligned with the matching block in `CLAUDE.md`.
- Agent-specific instructions may live outside the Horus-managed block.
<!-- HORUS:END shared-instructions -->

## Codex Notes

- Prefer small, explicit edits.
- Keep the project lightweight and shaped around current user needs.
