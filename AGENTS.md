# Agent Instructions

> **PRD structure v3 (2026-07-15).** This repo's durable continuity is `PRD.md` +
> card-backed `.horus/backlog/`; retired lanes live in `.horus/archive/`. Local
> `sessions/` notes are optional recovery buffers, not required closure output.
> Closure = update durable PRD/card state, add a note only if that state plus git/PR
> cannot resume the work, then `horus close --commit --push`. Run `horus consolidate`
> at most once and do not restore the six-lane split.

<!-- HORUS:BEGIN shared-instructions -->
<!-- horus-block-version: 9 -->
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
- Review optional local recovery notes in `.horus/sessions/` when they exist and
  contain context that is not yet durable elsewhere.
- Review fleeting worker/subagent notes in `.horus/temp/` when an execution plan
  is active; distill only the durable results upward.
- If this project instead has `project.md` / `roadmap.md` / `features.md` /
  `decisions.md` / `history.md` and no `PRD.md`, it is on the older six-lane
  structure — read those lanes directly (each stays in its lane); migrating to
  `PRD.md` is a separate, opt-in step and does not happen automatically.

Continuity is a checkpoint at context boundaries, not a transaction log for every
card. The shared continuity setting (CLI/hooks/TUI, optionally overridden for every
machine/CI by `continuity_granularity` in project frontmatter) controls narrative granularity:

- `handoff` (**default**) batches related deliveries in one uninterrupted session;
  checkpoint before an agent/account/machine change, dispatch, pause, release, or end.
- `delivery` performs the older strict checkpoint after every merged card/PR.
- `manual` waits for an explicit checkpoint but keeps pending-state warnings visible.

Delivery safety never changes with that setting: branches, commits, pushed refs, PRs,
deterministic gates, and worker receipts remain durable. Before dispatch, pin the task
and base SHA in the brief; if Horus reports pending continuity, either checkpoint it or
carry the relevant delta explicitly. Workers record delivery facts; the supervisor owns
canonical continuity.

At a continuity boundary, invoke the `horus-consolidate` skill and fold in the whole
campaign's context:

- Write a concise local recovery note under `.horus/sessions/` only when the
  durable state is not enough to resume: incomplete work, a dirty tree, an
  unresolved investigation, or an agent/account handoff before PRD.md is ready.
  Scaffold it with `horus session new "<title>" --agent <claude|codex>` and write
  the missing recovery context. Skip it when PRD.md, backlog cards, git, and the
  PR/worker receipt already make the next session recoverable.
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
- Local recovery notes are gitignored and do not travel between machines. Before a
  machine change, put required context in durable PRD/backlog state, a pushed branch,
  or an explicit dispatch brief.
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
- **Fetch first, branch for features, PR to merge.** At session start, sync with the
  remote (`git fetch --all --prune`) before trusting local refs or continuity prose.
  Implement on a feature branch and land it via PR; do not commit straight to the
  default branch unless the project's workflow policy or the user explicitly allows
  it (continuity closure commits follow that same policy).
- **Prove delegation pays before selecting a worker.** Define the bounded unit and
  name the concrete dividend — context avoided, useful parallelism, or lower-tier
  savings — before choosing a model or execution plane. Compare it with the fixed
  brief/review/gate/merge/closure tax; cross-project scope, multiple phases, and
  calibration goals alone do not justify delegation. Default inline when the benefit
  is unclear. Record the choice only in an existing durable handoff or backlog item;
  do not create a card or rewrite continuity solely to document execution mode.

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

## Releasing horus-harness

- **Invariant: publish a new version → update the hosted app.** Publishing a release
  (three-file bump → tag → `gh release create` → PyPI publish) does NOT update the
  hosted dashboard at `horus.rafaelfigueiredo.com` — it runs a pinned install that only
  advances on an explicit upgrade + `systemctl restart`. So the LAST step of every
  release is to run **`scripts/deploy-hosted.sh`** (upgrades the pinned uv-tool install
  with an index refresh, restarts `horus-dashboard.service`, verifies `/health` +
  that `/` still 403s). This is the instruction rung; a self-hosted-runner/webhook
  automation is the eventual hard guarantee (see `.horus` backlog).
- Upgrade horus with `uv tool install --force --refresh`, never `uv tool upgrade
  --reinstall` — the latter re-reads uv's cached index and silently stays on the old
  version (observed 0.0.30→0.0.31).
