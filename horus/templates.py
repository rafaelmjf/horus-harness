"""Templates for files created by `horus init`.

The managed instruction block is the single source of the shared-instructions
content. The only intended difference between the `AGENTS.md` and `CLAUDE.md`
copies is the cross-reference line naming the *other* file; see
``instructions.normalize_block`` which accounts for that when checking drift.
"""

from __future__ import annotations

from horus.versioning import MIN_CLI_VERSION

BLOCK_BEGIN = "<!-- HORUS:BEGIN shared-instructions -->"
BLOCK_END = "<!-- HORUS:END shared-instructions -->"

# Bump whenever _SHARED_BODY changes. Blocks written before the marker existed
# parse as None and count as older than any versioned block, so `upgrade-project`
# refreshes them; a block *newer* than the installed CLI is left alone (the CLI is
# what's outdated — never offer a downgrade as a "refresh").
BLOCK_VERSION = 12

_SHARED_BODY = """## Horus Project Continuity

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
- A `next_prompt` is an orientation handoff: the previous session's account of where the
  work stood, for a fresh session to read before acting. Author it so that session can
  fetch/verify and read the minimum context. Do not author consent instructions into it —
  what a session may do is set by its launch permission posture, which the agent CLI
  enforces, not by prose the model can reinterpret. A release may be suggested with
  concrete reasons, but never chained as a next step: it is its own decision, taken with
  the owner, after continuity is current.
- Review optional local recovery notes in `.horus/sessions/` when they exist and
  contain context that is not yet durable elsewhere.
- Review fleeting worker/subagent notes in `.horus/temp/` when an execution plan
  is active; distill only the durable results upward.
- If this project instead has `project.md` / `roadmap.md` / `features.md` /
  `decisions.md` / `history.md` and no `PRD.md`, it is on the older six-lane
  structure — read those lanes directly (each stays in its lane); migrating to
  `PRD.md` is a separate, opt-in step and does not happen automatically.

Continuity is a checkpoint at context boundaries, not a transaction log for every card.
One universal rule, with no granularity setting to configure per machine, per project, or
per session: git branches, commits, pushed refs, and PRs preserve every delivery between
boundaries, and canonical `.horus/` prose is consolidated once at a real boundary — a
pause, session end, agent/account/machine handoff, release, or a dispatch that needs
durable context.

Delivery safety is independent of that and never relaxes: branches, commits, pushed refs,
PRs, deterministic gates, and worker receipts remain durable. Before dispatch, pin the task
and base SHA in the brief; if Horus reports pending continuity, either checkpoint it or
carry the relevant delta explicitly. Workers record delivery facts — the SHA, the PR, what
the gate actually emitted — never a verdict on their own work; the supervisor independently
reproduces the deterministic signal and owns canonical continuity.

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

- **A session's context is chosen at launch; its authority is the permission posture.**
  A launch loads exactly one of: nothing (fresh — open and type), the authored handoff
  (resume), or one card's scope. There is deliberately no session "mode" describing how
  much process to perform: that was prose a model could reinterpret, it cost a turn at
  launch to deliver, and it could contradict the handoff it wrapped. What a session may
  actually do is the permission posture, enforced by the agent CLI itself.
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
- **Authorize the exact worker envelope before spending.** Agent-initiated delegation
  first proves a concrete context, parallelism, or lower-tier dividend exceeds the
  brief/review/gate/merge/closure tax; default inline when unclear. An owner may instead
  direct dispatch to spend expiring isolated-account capacity or protect supervisor
  context. Before every implementation-worker launch, show the exact agent, concrete
  model, effort, account, current usage/reset evidence (with source/freshness), bounded
  task, maximum attempts, expected dividend or owner override, and verification gate;
  obtain explicit approval for that envelope. Changing model, account, effort, task
  scope, or attempt allowance requires new approval — never silently fall back. After
  completion, report actual model/account/effort/runtime/attempt/outcome and start/end
  usage; show a percentage-point delta only for fresh same-window isolated readings
  without tracked overlap, otherwise label it unknown or confounded. Never predict a
  per-task usage percentage, auto-route from cost, poll continuously, or add a second
  model call solely for accounting. Record the execution-mode choice only in an
  existing durable handoff/card, never in a new continuity artifact made just for it.
- **Accounts get isolated config dirs; same-dir concurrency is advised, not blocked.**
  Give every account its own isolated `CLAUDE_CONFIG_DIR` (Claude) / `CODEX_HOME`
  (Codex) so distinct accounts never share credentials/state. Two agent CLIs
  *cold-starting simultaneously* on one dir can race on its JSON (observed once,
  2026-07-16, pre-isolation); settled sessions coexist safely, as Claude Code and Codex
  natively allow. So `horus run` prints an advisory note naming the live peer when a
  launch shares a config dir, then proceeds — it no longer refuses (relaxed 2026-07-18).
  The real cost to weigh is the shared rate-limit budget, not corruption.

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

- Keep this shared Horus-managed block aligned with the matching block in `{other}`.
- Agent-specific instructions may live outside the Horus-managed block."""


def shared_block(other_file: str) -> str:
    """Return the full managed block (markers included) cross-referencing ``other_file``."""
    return (
        f"{BLOCK_BEGIN}\n<!-- horus-block-version: {BLOCK_VERSION} -->\n"
        f"{_SHARED_BODY.format(other=other_file)}\n{BLOCK_END}"
    )


def instruction_file(title: str, other_file: str, agent_notes_heading: str) -> str:
    """A fresh AGENTS.md / CLAUDE.md containing the managed block plus an agent-notes stub."""
    return (
        f"# {title}\n\n"
        f"{shared_block(other_file)}\n\n"
        f"## {agent_notes_heading}\n\n"
        "- Keep the project lightweight and shaped around current user needs.\n"
    )


def project_md(project_name: str, date: str) -> str:
    return f"""---
project: {project_name}
status: planning
current_focus: "Describe the immediate focus here."
last_updated: {date}
---

# {project_name}

One-paragraph description of what this project is. If the repo already has a
README or status doc, distill the essentials here (see `.horus/README.md`).

## Current Shape

What the project looks like right now.

## Boundaries

What is intentionally out of scope.
"""


def roadmap_md(date: str) -> str:
    return f"""---
status: active
current_focus: "Describe the current focus here."
next_action: ""
next_prompt: ""
execution_recommendation: "continue-as-is"
last_updated: {date}
---

# Roadmap

## Now

- [ ] First task.

## Later

- [ ] Deferred task.
"""


def backlog_pointer_block() -> str:
    """The PRD's `## Backlog` section body once cards are the fleet standard:
    a thin pointer to `.horus/backlog/`, not an inline list. Shared by the
    fresh v3 scaffold (`prd_md`) and the inline-Backlog -> cards migration
    (`horus backlog migrate`), so both land on identical wording."""
    return (
        "Prioritized open work lives in `.horus/backlog/` — one card per item "
        "(`status`/`priority`/`type` in frontmatter; `type` defaults to `task` "
        "when unstated). Run `horus backlog list` to see it, `horus backlog "
        "claim <name>` to start one, and `horus backlog ship <name> --pr N --sha "
        "SHA` after merge. This section is a pointer, not a list."
    )


def prd_md(project_name: str, date: str) -> str:
    return f"""---
status: active
current_focus: "Blank Horus scaffold; no project truth has been inferred yet."
next_action: "Wait for the first concrete use case; infer only when existing docs already carry useful project truth."
next_prompt: "Resume {project_name}. Read .horus/PRD.md and ground the first real backlog candidate in repository or owner evidence; summarize what you found and ask permission before writing or implementing it."
execution_recommendation: "continue-as-is"
horus_min_version: {MIN_CLI_VERSION}
last_updated: {date}
---

# {project_name} — PRD

The one maintained continuity file. Structure: **PRD.md + sessions/**. This file
carries vision, prioritized backlog, shipped ledger, and load-bearing rules; the
tooling reads its frontmatter directly (dashboard NEXT box, `horus resume`, the
merge freshness gate — see `resolve_focus`).

## Vision

What this project is, its shape, and its boundaries. A paragraph or two, plus an
explicit **out of scope** list once the project has one.

## Backlog

{backlog_pointer_block()}

## Shipped

One line per capability; details live in git history.

## Rules (load-bearing)

The invariants that constrain new work.

- **<rule in a few words>** — <terse why>.

## Structure contract

- **This file** carries vision, shipped, rules, and a thin pointer to the backlog.
  Keep it under ~250 lines: new shipped items are one line; shipped backlog cards
  move to `.horus/backlog/archive/` with `status: shipped` plus PR/SHA provenance;
  new work (including bugs) gets its own card in `.horus/backlog/`.
- **`sessions/`**: optional local recovery notes (`horus session new`), used only
  when durable PRD/backlog/git/PR state cannot fully resume the work. They are
  gitignored; distilled notes move to `sessions/archive/` (local).
- **Frontmatter:** this file carries `current_focus` / `next_action` /
  `next_prompt` / `execution_recommendation` / `last_updated` — the tooling reads
  them PRD-first (`resolve_focus`); no shims are needed.
- **Closure:** at a configured continuity boundary, update this file's frontmatter +
  backlog/shipped, add a recovery note only if the durable-state test fails, then
  `horus close --commit --push`. One `horus consolidate` pass at most; do not chase
  warnings.
"""


def features_md(date: str) -> str:
    return f"""---
status: active
last_updated: {date}
---

# Features — capability ledger

Complete **capabilities** (shippable packages), status-tracked. A feature is a
shippable unit of behaviour, not a task — bug fixes, corrections, and chores live
in `roadmap.md` and never appear here. The action points to build a planned or
in-progress feature live in `roadmap.md`; the *why* behind a shipped one is in
`decisions.md` / `history.md`.

Status: **Shipped** · **In progress** · **Planned**

## Shipped

| Capability | Since | Notes |
|---|---|---|

## In progress

| Capability | Notes |
|---|---|

## Planned

| Capability | Notes |
|---|---|
"""


def execution_md(date: str) -> str:
    return f"""---
status: idle
current_feature: ""
supervisor_tier: frontier
worker_tier: standard
continuity_tier: economy
delegation_basis: ""
last_updated: {date}
---

# Execution Plan

Fluid, optional plan for the currently active roadmap item. Replace this when
the next substantial feature starts; distill finished work into `roadmap.md`,
`features.md`, `decisions.md`, and `history.md` rather than preserving this as a
timeline.

## Delegation decision (volume × ambiguity × runtime)

Delegation is a judgment call, not a default. Decide on implementation **volume** and
**ambiguity**, then weigh what delegation buys on *this* runtime:

| Situation | Approach |
|---|---|
| High volume, low ambiguity, clear gate (scaffolding, repetitive edits, mechanical refactor) | Delegate, then reproduce the gate (deterministic signal + one runtime probe) |
| Integrity/security-sensitive (guarded writes, schema, auth) | Delegate is fine — keep an independent review + reproduce the gate |
| Small, ambiguous/exploratory, or debugging | Stay inline — orchestration overhead and judgment loss dominate |
| Work where the *user* is the real reviewer (visual/UI) | Delegate the build; the user's eyeball is the gate |

Runtime matters: separate worker tiers may add a price dividend, while a single-model
runtime may buy only context hygiene. Read the live calibration data rather than naming
models in this durable template. Record the call per phase in `delegation_basis`.
Review is not a safety guarantee — the durable safeguards are to
reproduce the gate, bound each pass to a green committed checkpoint, and put safety in
the code (guards), not the reviewer. Reproducing the gate means observing a
deterministic signal yourself — a *required* CI check green on the worker's exact
commit counts as reproduction of the test gate; rerun locally only when no required
check covers it — plus one live probe of the changed runtime surface. Never accept a
phase on the handoff note's claims.

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

`worker_agent` marks which agent CLI runs a delegated phase: `native` (the
supervisor's own subagents — the default) or a named CLI (`claude`, `codex`) for a
cross-agent worker. Spawn a cross-agent worker as a one-shot tracked session:

    horus run --agent codex --account <alias> --path . "<phase brief - point it at the handoff note>"

The review contract does not change with the worker agent: review the diff and the
handoff note, then reproduce the gate (deterministic signal + one runtime probe). A
cross-vendor worker shares no
conversation history with the supervisor, which also makes it an honest cold reader
of `.horus/` continuity.

## Active Phases

| phase | status | difficulty | mode | worker_tier | worker_agent | delegation_basis | handoff_note | review |
|---|---|---|---|---|---|---|---|---|
| 1A | planned | S2 | direct-or-delegate | standard-if-delegated | native | why delegation is worth/not worth it here | `.horus/temp/1A.md` | frontier |

## Worker Handoff Contract

Implementation workers should write a brief note in `.horus/temp/` when a phase
finishes. Keep it factual and reviewable:

- changed files / behavior;
- the gate: one command the supervisor can rerun verbatim, its expected output, and
  the pre-existing failure baseline (what was already red before the phase started);
- risks or follow-ups;
- suggested durable `.horus/` updates.

No proof narratives — the gate command and the CI check speak; prose claims are not
reviewed. The supervisor reviews the diff and the handoff, then updates the durable
continuity (`PRD.md` on a PRD-structure project; the lanes on six-lane).

Useful commands:

- `horus execution prompt --target codex` prints a supervisor prompt shaped for
  Codex subagents/custom agents.
- `horus execution prompt --target claude` prints the Claude Code equivalent.
- `horus execution handoff 1A` creates `.horus/temp/1A.md` for a worker note
  (`--agent codex` to label a cross-agent worker).
- `horus run --agent codex --path . "<prompt>"` spawns a one-shot tracked Codex
  worker (`--account <alias>` for an isolated `CODEX_HOME`).
"""


def execution_supervisor_prompt(
    *,
    target: str,
    project: str,
    next_action: str,
    execution_recommendation: str,
    execution_status: str,
    current_feature: str,
    prd_structure: bool,
) -> str:
    """Return a target-aware prompt for supervising a phased execution plan."""
    if target == "claude":
        native = (
            "Use Claude Code project subagents when the phase can be bounded. Prefer "
            "a frontier model for planning/review, a standard model for implementation "
            "phases, and an economy model only for mechanical continuity updates. "
            "Claude may make a different direct-vs-delegated call than Codex; record "
            "the local rationale in delegation_basis. "
            "When the user is testing model separation, this is mandatory: do not "
            "implement the delegated phase in the supervisor context."
        )
    elif target == "codex":
        native = (
            "Use Codex subagents or project custom agents when the phase can be bounded. "
            "Codex custom agents may live under .codex/agents/; steer model and reasoning "
            "effort per phase instead of hard-coding global defaults. Codex may make a "
            "different direct-vs-delegated call than Claude; record the local rationale "
            "in delegation_basis. When the user is "
            "testing model separation, this is mandatory: do not implement the delegated "
            "phase in the supervisor context."
        )
    else:
        native = (
            "Use native subagents/workers when the phase can be bounded. Resolve the "
            "frontier/standard/economy tiers locally for the active agent. When the "
            "planning agent chooses delegation, record the local rationale in "
            "delegation_basis. When the user is testing model separation, this is "
            "mandatory: do not implement the delegated phase in the supervisor context."
        )

    focus_label = "PRD NEXT" if prd_structure else "Roadmap NEXT"
    continuity_read = (
        "Read `.horus/PRD.md` and `.horus/execution.md`. Lazy-load only relevant "
        "backlog cards or local handoff notes."
        if prd_structure
        else "Read `.horus/project.md`, `.horus/roadmap.md`, `.horus/features.md`,\n"
        "`.horus/decisions.md`, `.horus/history.md`, and `.horus/execution.md`."
    )

    return f"""Horus execution supervisor prompt

Project: {project}
Target agent: {target}
{focus_label}: {next_action or "(not set)"}
Execution recommendation: {execution_recommendation or "(not set)"}
Execution status: {execution_status or "(unknown)"}
Current feature: {current_feature or "(not set)"}

{continuity_read}

Supervisor workflow:

1. Confirm whether the project's `execution_recommendation` (PRD.md frontmatter on a
   PRD-structure project, roadmap.md on six-lane) still applies.
2. If it says `plan-execution`, first decide whether execution planning is actually
   warranted for this agent/runtime. Decide on implementation volume × ambiguity:
   delegate high-volume/low-ambiguity/clear-gate work; stay inline for small,
   ambiguous, exploratory, or debugging work. Weigh what delegation buys here — a
   frontier supervisor + cheaper worker tiers gain context hygiene AND a cheaper tier,
   a single strong model gains mostly context hygiene (higher bar to delegate).
3. For each phase, record mode (`direct`, `delegated`, or `test-delegation`),
   worker tier if delegated, and `delegation_basis` (volume/ambiguity + what delegation
   buys on this runtime). `worker_tier` alone is only a tier hint, not a cost
   justification. Review is not a safety guarantee: reproduce the gate yourself, bound
   each pass to a green committed checkpoint, and put safety in the code, not the review.
4. Delegate only bounded phases. Keep the supervisor on planning, review, final
   acceptance, and durable `.horus/` updates.
   If the user is testing model separation and no native worker/subagent is available,
   stop and report that the workflow test cannot proceed faithfully here.
5. Instruct each worker to write a handoff note under `.horus/temp/` using
   `horus execution handoff <phase>` before returning — including the gate command,
   its expected output, and the pre-existing failure baseline. No proof narratives.
6. Accept a phase on deterministic signals only: the required CI check green on the
   worker's exact commit (rerun the gate locally only when no required check covers
   it) plus one runtime probe you drive yourself. Review the diff and handoff note
   for scope, not as evidence that the work works.
7. Distill durable outcomes into PRD.md (PRD-structure) or
   roadmap/features/decisions/history (six-lane) at closure; keep
   `.horus/execution.md` fluid and replace it for the next substantial item.

Native projection:

{native}

Worker handoff contract:

- changed files and behavior;
- tests run and result;
- risks, assumptions, or follow-ups;
- suggested durable `.horus/` updates.
"""


def brainstorm_prompt(
    *,
    project: str,
    topic: str,
    vision: str,
    backlog: str,
    rules: str,
    note_path: str,
) -> str:
    """Seed prompt for a scoped brainstorm session.

    Minimal context by design: the PRD's vision/backlog/rules and the topic — no
    session notes, no archive, no six-lane lanes. The output contract writes a
    structured implementation-plan draft to ``note_path`` under ``.horus/temp/``
    and never edits PRD.md (the orchestrator/consolidate owns continuity).
    """
    def _block(text: str, empty: str) -> str:
        text = (text or "").strip()
        return text if text else empty

    vision_block = _block(vision, "(no Vision section recorded in PRD.md)")
    backlog_block = _block(backlog, "(no Backlog section recorded in PRD.md)")
    rules_block = _block(rules, "(no Rules section recorded in PRD.md)")

    return f"""Brainstorm session for the {project} project.

You are seeding a focused ideas/brainstorm on ONE topic. Deliberately minimal
context is loaded below — the project's PRD vision, backlog, and rules. Do NOT
read `.horus/sessions/`, `.horus/archive/`, or the full history; stay scoped to
the topic and the context here. Read other repo code only if the topic needs it.

## Topic

{topic}

## PRD — Vision

{vision_block}

## PRD — Backlog

{backlog_block}

## PRD — Rules (load-bearing)

{rules_block}

## Your task

Think hard about the topic against the vision, backlog, and rules above, then
produce a structured implementation-plan DRAFT — not a final decision, a draft
for a human to review. Cover:

- **Goal** — one paragraph on what solving this topic delivers and why it fits
  the vision (or where it strains a rule, called out explicitly).
- **Phases** — an ordered breakdown of the work into bounded phases.
- **Risks** — what could go wrong, load-bearing rules it touches, unknowns.
- **Suggested gates** — the deterministic signal(s) that would prove each phase
  done (tests, a runtime probe, a required CI check).
- **Proposed backlog lines** — one-line backlog entries, in the PRD's style,
  ready for a human to paste into the Backlog.

## Output contract (strict)

- Write the draft to `{note_path}` (create `.horus/temp/` if needed).
- Do NOT edit `.horus/PRD.md` or any other `.horus/` file — continuity is owned
  by the consolidate/orchestrator step, which reviews your draft separately.
- Do NOT commit anything. Leave the note uncommitted for review.
- When the note is written, summarize what you drafted and stop.
"""


def execution_handoff_note(
    *,
    phase: str,
    title: str,
    date: str,
    agent: str,
    model_tier: str,
    prd_structure: bool = False,
) -> str:
    if prd_structure:
        durable = """- PRD.md backlog:
- PRD.md shipped:
- PRD.md rules:
- execution.md:"""
    else:
        durable = """- roadmap.md:
- features.md:
- decisions.md:
- history.md:
- execution.md:"""
    return f"""---
phase: {phase}
title: "{title}"
date: {date}
agent: {agent}
model_tier: {model_tier}
status: in-progress
---

# Phase {phase} Handoff

## Scope

- Assigned phase:
- Out of scope:

## Changed Files

-

## Behavior

-

## Gate

- Command (the supervisor reruns this verbatim):
- Expected output:
- Pre-existing failure baseline (already red before this phase): none known
- Last run result: not run yet

## Risks / Follow-ups

-

## Suggested Durable Horus Updates

{durable}
"""


def history_md(date: str) -> str:
    return f"""---
status: active
last_updated: {date}
---

# History — bumps in the road & decision rationale

Curated, durable context: the problems that bit us and the lessons that shaped the
design, plus the **rationale behind the rules** in `decisions.md` (which stays
concise — the *why* and the dead ends live here). **Not** a timeline and **not** open
issues (those live in `roadmap.md`). Compress a large existing changelog into this
curated subset with `horus distill-history`.

## Bumps in the road

## Decision rationale
"""


def readme_md() -> str:
    return """# `.horus/` — project continuity

Horus keeps a concise, vendor-neutral record of project state here so any agent
(Claude, Codex, ...) can pick up continuity across machines — even without Horus
installed. Read this first.

- `project.md` — what this project is, current focus, shape, boundaries (overview + vision).
- `roadmap.md` — open **action points** (any type: feature work, bug fix, chore),
  pruned when done. The *what's next*, not a completed log.
- `features.md` — the **capability ledger**: complete packages tracked
  shipped / in-progress / planned. A capability, not a task — distinct from roadmap.
- `decisions.md` — concise **current rules**, grouped by topic. Not a dated log;
  superseded decisions are dropped and the rationale lives in `history.md`.
- `history.md` — curated bumps in the road (problems that bit us + the lessons) **and
  the rationale behind the decisions**. Relevant context, **not** a timeline and
  **not** open issues.
- `execution.md` — optional active execution plan for the current roadmap item:
  phase breakdown, model-tier routing, worker handoff notes, and review gates.
- `sessions/` — optional local recovery notes (gitignored; per-machine context for
  incomplete work or handoffs that is distilled into the files above when durable).
- `temp/` — gitignored scratch notes from implementation workers/subagents. These
  are fleeting handoffs for the supervisor, not durable project memory.

**This is the single concise source of "what is this, and what's next."** If the
project already has rich docs (README, a status/roadmap file, and anything they
point to), distill the essentials here and treat those as the source — do not
maintain two hand-written roadmaps that will drift. Mark a superseded doc as such
once its content lives here.

Keep each lane in its lane; run `horus consolidate` to route facts to the right
file, prune what's done, and distill recovery notes upward when present.

Durable state (`project.md` / `roadmap.md` / `features.md` / `decisions.md` /
`history.md` / `execution.md`) is committed and travels via git; optional recovery
notes and temp worker notes stay local per machine.

These files are scaffolded by `horus init` and maintained by the agents working in
this repo. A future `horus infer` will populate them automatically (LLM-based).
"""


def readme_md_v3() -> str:
    return """# `.horus/` — project continuity

Horus keeps a concise, vendor-neutral record of project state here so any agent
(Claude, Codex, ...) can pick up continuity across machines — even without Horus
installed. Read this first.

**Structure: PRD.md + sessions/.** One maintained file instead of a lane taxonomy.

- `PRD.md` — **the one maintained file**: vision, prioritized backlog (features and
  bugs in one list), shipped ledger (one line each), load-bearing rules. Its
  frontmatter (`current_focus` / `next_action` / `next_prompt` /
  `execution_recommendation` / `last_updated`) feeds the dashboard, `horus resume`,
  and the merge freshness gate directly — see `resolve_focus`.
- `sessions/` — optional local recovery notes (gitignored; incomplete work, dead
  ends, or handoff context not yet durable elsewhere). Distilled notes move to
  `sessions/archive/`.
- `temp/` — gitignored scratch notes from implementation workers/subagents; fleeting
  handoffs for the supervisor, not durable project memory.
- `execution.md` — optional, created only when a backlog item needs a phased plan
  (worker/subagent handoffs, review gates). Fluid: replaced when the next
  substantial item starts, not preserved as a timeline.

Keep PRD.md under ~250 lines: shipped ledger items are one line; card-backed work
is moved to `backlog/archive/` with `status: shipped` and PR/SHA provenance. At the
configured continuity boundary, closure = update PRD.md (frontmatter +
backlog/shipped), add a local recovery note only when durable state is insufficient,
then `horus close --commit --push`.
The default `handoff` granularity batches related deliveries until an agent/account/
machine change, dispatch, pause, release, or end. One `horus consolidate` pass at most;
do not chase warnings.

These files are scaffolded by `horus init` and maintained by the agents working in
this repo. `horus infer` can bootstrap PRD.md from existing docs (README, status
files) when they exist.
"""


def decisions_md() -> str:
    return """# Decisions — current rules

Durable rules in force, **grouped by topic** and kept concise: a few words of rule
plus a terse why. This is the *current* state, not a log — drop superseded decisions
(keep only the rule that won) and put the narrative rationale and dead ends in
`history.md`. Read top-to-bottom in a few seconds.

## <Topic>

- **<rule in a few words>** — <terse why>. ↳ history.md for the full rationale.
"""


def ci_workflow_yaml(*, has_lfs: bool, has_test_target: bool) -> str:
    """A minimal, opt-in CI gate for `horus init --ci`: a deterministic signal a
    freshly onboarded repo can reproduce (`horus doctor project`, plus `git lfs
    fsck` and a `make test` step when this repo's own state shows they apply).
    Generic by design — no per-language build matrices; a repo with no detected
    build step still gets a green doctor-only gate."""
    steps = [
        "      - uses: actions/checkout@v4\n"
        + ("        with:\n          lfs: true\n" if has_lfs else ""),
        "      - name: Install horus-harness\n        run: pip install horus-harness\n",
        "      - name: horus doctor project\n        run: horus doctor project --path .\n",
    ]
    if has_lfs:
        steps.append("      - name: git lfs fsck\n        run: git lfs fsck\n")
    if has_test_target:
        steps.append("      - name: make test\n        run: make test\n")
    steps_block = "\n".join(steps)
    return f"""name: horus-gate

# Minimal, opt-in CI gate scaffolded by `horus init --ci`: a deterministic signal to
# reproduce instead of trusting a prose "tests pass" report. This repo owns the file
# from here — edit or remove it freely.

on:
  pull_request:
  push:
    branches: [main]

jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
{steps_block}"""


def session_summary(
    *,
    title: str,
    date: str,
    project: str,
    agent: str,
    account: str,
    environment: str,
) -> str:
    return f"""---
date: {date}
agent: {agent}
account: {account}
environment: {environment}
project: {project}
status: in-progress
summary: "{title}"
---

# {title}

## Summary

What this session set out to do and what happened.

## Key Points

- ...

## Next

- ...
"""


CLOSURE_PROMPT = """Closure ritual - make the dashboard reflect THIS session before ending it.
(For the full context-aware version, run the `horus-consolidate` skill — it sees this
conversation. This is the file-level checklist.)

The dashboard renders these fields as the project's *current* state and never infers
them — keep each current at every close:

1. Recovery test: if durable lanes + git/PR state cannot resume incomplete work,
   write a local note under .horus/sessions/ (`horus session new "<title>"
   --agent <claude|codex>`). Otherwise skip it.
2. project.md `current_focus` (frontmatter): refresh the one-line "where things are now".
3. roadmap.md, the two agent-authored fields + the checkboxes:
   - `next_action`: the single best next step, one imperative line.
   - `next_prompt`: a paste-into-a-fresh-session orientation prompt (cold reader: name
     the proposed step + point at .horus/), ending with a request for permission before
     execution. It may suggest a release with reasons, but must never order or chain one;
     require separate explicit release confirmation.
   - `execution_recommendation`: judge the NEXT on volume × ambiguity — `continue-as-is`
     for small/ambiguous/exploratory/debugging work, `plan-execution` for high-volume,
     low-ambiguity work with a clear gate. State what delegation buys on this runtime
     (context hygiene, and a cheaper tier only if the runtime has one); don't sell
     supervisor review as the safeguard.
   - tick the roadmap checkboxes for what this session did.
4. execution.md: when `execution_recommendation` is `plan-execution`, create/update
   the active phased plan before starting implementation, including a per-phase
   `delegation_basis`; otherwise leave it idle/unchanged.
5. features.md: add a Shipped row for any capability shipped this session.
6. execution.md: if there is an active phased plan, update phase/review status from
   accepted worker handoff notes in .horus/temp/.
7. decisions.md: record a durable decision as a concise rule under its topic (drop any
   rule it supersedes); put the rationale/dead-ends in history.md. Bump `last_updated`
   on lanes you touched.
8. Instructions: keep the AGENTS.md / CLAUDE.md shared blocks aligned
   (`horus doctor instructions` / `horus reconcile instructions`). Don't edit source as part of closure.

Verify: `horus close --check` must pass (it fails while any dashboard field above is stale).
Backlog cleanup (distilling old sessions, pruning historical done items, splitting overlaps)
is a SEPARATE pass — only when asked, not every close.
"""


CLOSURE_PROMPT_V3 = """Continuity boundary - fold the campaign once, when context is about to change.

1. Update PRD.md frontmatter, Backlog/Shipped, and any newly load-bearing rule.
2. Write a concise local recovery note under .horus/sessions/ only if PRD/backlog +
   git/PR state do not fully preserve incomplete work or handoff context.
3. Use the horus-consolidate skill for context-aware hygiene, then run
   `horus close --commit --push`.

Branches, PRs, deterministic gates, and commit/push checkpoints remain required between
boundaries. Resume/TUI keep any unconsolidated delivery commits visible until this close.
"""


# Two usage-closure injections, by hook event. The hook must never override an
# explicit user instruction or strand work local-only (see decisions.md / history.md
# "Usage hook overrode an explicit command + left work unpushed"). So:
#   - UserPromptSubmit -> ADVISORY: context only; do what the user asked (incl. push).
#   - Stop             -> PROMPT:   ask the user (close now vs push ahead), then wait.
# Both always reach the remote: closure uses `horus close --commit --push`, and any
# committed work must be pushed so another machine never resumes from stale state.

USAGE_CLOSURE_ADVISORY = (
    "[Horus usage advisory — context, not a command] Your 5-hour usage is {level} "
    "and you could be cut off soon. This note is background; the user's message is "
    "what you must act on. Carry out their request FULLY — and if it involves "
    "committing or finishing work, \"fully\" includes pushing committed work to its "
    "remote so nothing is stranded only on this machine. Do NOT replace or narrow "
    "their request with a continuity-only closure, and do NOT stop without doing what "
    "they asked. Afterwards you MAY briefly note the usage level and offer to run the "
    "closure ritual (the horus-consolidate skill to fold this session's context into "
    ".horus, then `horus close --commit --push`) so continuity is captured before any "
    "cut-off — but only if they want it."
)


USAGE_CLOSURE_PROMPT = (
    "[Horus usage check] Your 5-hour usage is {level} — you could be cut off "
    "mid-task. Do NOT unilaterally stop or force a closure. Instead, ASK the user how "
    "to proceed and then wait for their answer, offering two clear options: (a) run "
    "the closure ritual NOW — use the horus-consolidate skill (it can see THIS "
    "conversation, which a file-only script cannot) to fold the session's decisions, "
    "what shipped, dead ends, and the next step into .horus, then "
    "`horus close --commit --push`; or (b) push ahead with the current work for now. "
    "This check escalates by usage band, not on a timer: if the user already chose to "
    "push ahead at a lower level in this window, do not relitigate that choice — state "
    "the new level in one line and re-ask concisely. Whichever they choose, first make "
    "sure any committed work is actually pushed to its remote — leaving commits "
    "local-only risks resuming from stale state on another machine. If there is "
    "uncommitted work, say so when you ask, so the user can decide with that in mind."
)


USAGE_GUARD_ADVISORY = (
    "[Horus usage advisory — context, not a command] Your 5-hour usage is at "
    "{percent}% (resets {reset}) and the window could close mid-task. This is "
    "background: keep carrying out the user's request. But treat it as a cue to reach "
    "a safe checkpoint soon — commit and push work in progress so nothing is stranded "
    "only on this machine if you are cut off. Do NOT abandon or narrow the user's "
    "request, and do NOT force a closure."
)


USAGE_RESCUE_ADVISORY = (
    "[Horus emergency state-save] Your 5-hour usage is at {percent}% (resets "
    "{reset}) — very close to the cutoff. This tool call was NOT blocked. Horus has "
    "already performed an automatic state-save: {detail}. Wrap up promptly now: "
    "finish or safely park the current step, commit and push anything important, then "
    "run the closure ritual (the horus-consolidate skill, then "
    "`horus close --commit --push`) so continuity is captured before the window "
    "closes. If the automatic save above reported an error, commit your work "
    "manually right away."
)


CHECKPOINT_ADVISORY = (
    "[Horus checkpoint] This session is ending with {detail}. Working discipline is to "
    "bound each step to a committed-and-pushed checkpoint so nothing is stranded only "
    "on this machine — commit the work and push it (if the default branch is "
    "protected, put it on a branch and open a PR rather than force-pushing). "
    "`horus close --commit --push` captures continuity. This is a reminder, not a "
    "block."
)


CHECKPOINT_STOP_INSTRUCTION = (
    "[Horus checkpoint] You are stopping with work that is not yet checkpointed: "
    "{detail}. Before you stop, reach a committed-and-pushed checkpoint so nothing is "
    "stranded only on this machine: (1) commit the work; (2) push it to its remote — "
    "if the default branch is protected, put the work on a branch and open a PR rather "
    "than force-pushing to it; (3) if this is a real close, run the horus-consolidate "
    "skill to fold this session into `.horus/`, then `horus close --commit --push`. If "
    "you are deliberately leaving work uncommitted, tell the user why instead of "
    "silently stopping."
)


MERGE_CLOSURE_INSTRUCTION = (
    "This `gh pr merge` was blocked by Horus: the project's `.horus/` continuity "
    "lanes are stale, so the dashboard would not reflect this work once it lands on "
    "main. Closure authoring needs THIS session's context (decisions + why, what "
    "shipped, the next step) — which is gone after the merge — so the gate is "
    "pre-merge by design. Close the session FIRST, then merge: (1) run the "
    "horus-consolidate skill to fold this session's context into `.horus/**` (it uses "
    "`horus consolidate` for signals, but you supply what a file-only script can't "
    "see); (2) verify with `horus close --check` until it passes; (3) re-run the "
    "`gh pr merge`. Do not work around this by skipping the close."
)

HOSTED_RESTART_INSTRUCTION = (
    "This command was blocked by Horus: you are running inside Horus's own in-app "
    "PTY terminal, which is hosted *by the dashboard process* (HORUS_PTY_HOST_PID). "
    "The command would kill or restart that process — so it would tear down the very "
    "session you are in and lose any uncommitted work mid-task (this exact footgun is "
    "in history.md: 'an in-app agent restarted the app it was hosted in — and killed "
    "itself'). Do NOT restart or kill the Horus app from inside a hosted session. "
    "Instead: (1) commit your work so nothing is lost; (2) if you need the app "
    "restarted to see a code change, ask the user to restart Horus from OUTSIDE the "
    "dashboard (a normal terminal), or open a separate terminal that Horus does not "
    "host. Note: Python does not hot-reload, so a long-running dashboard keeps serving "
    "its old in-memory build until it is restarted from outside."
)

WORKER_GLOBAL_STATE_INSTRUCTION = (
    "This command was blocked by Horus because this is an unattended tracked worker "
    "(HORUS_RUN_WORKER=1) and the command would destructively remove user-global "
    "Horus/Claude/Codex state. A real worker once meant to clean an isolated probe but "
    "deleted ~/.horus/logs/runs instead. Create a dedicated isolated probe home first, "
    "pass that exact path explicitly to the probe, and clean only the directory the probe "
    "created. Never use broad cleanup against ~/.horus, ~/.claude, or ~/.codex from a worker."
)


CONSOLIDATE_PROMPT = """Consolidation routine - reshape .horus/ so each lane stays in its lane.
Act on the signals above. Edit .horus/** ONLY (not source, not AGENTS.md/CLAUDE.md).
Never invent status, dates, or versions; when intent is unclear, leave it and flag it.

1. Ship -> ledger: for each done roadmap action point that completed a shippable
   capability, close it in roadmap.md and add/update the matching row in features.md
   (Planned/In-progress -> Shipped; stamp the version if the repo records one, else blank).
2. De-duplicate across lanes: where the same item sits in both roadmap.md and
   features.md, keep the *action points* in roadmap.md and the *capability status* in
   features.md, each pointing at the other. No fact maintained in two places.
3. Prune: drop done/obsolete roadmap items (they live in features/history/git now).
   Keep roadmap focused on top/open action points; condense or archive long completed
   lists rather than letting them grow.
4. Distill sessions: fold durable content from sessions/*.md into the lanes, then
   move the distilled summary into sessions/archive/ (kept local, excluded from
   the to-distill count) rather than deleting it.
5. Decisions discipline: decisions.md is concise current rules grouped by topic — NOT
   a dated log. Collapse superseded decisions to the rule that won, and move the
   narrative rationale / dead ends to history.md (a "Decision rationale" section).
6. Keep lanes pure: no tasks in features.md; no shipped packages lingering in
   roadmap.md; no open issues in history.md; no changelog in project.md.

Re-run `horus consolidate` afterward; the candidates above should be resolved.
"""


CONSOLIDATE_PROMPT_V3 = """Consolidation routine (PRD structure) - a light backlog-hygiene pass over PRD.md.
Act on the signals above. Edit .horus/** ONLY (not source, not AGENTS.md/CLAUDE.md).
Never invent status, dates, or versions; when intent is unclear, leave it and flag it.

1. Size: keep PRD.md under the ~250-line cap - shipped entries are one line each.
   For card-backed work, run `horus backlog ship <name> --pr N --sha SHA`; it
   preserves the card under `backlog/archive/`. Delete only stale legacy/inline done items.
2. Freshness: refresh the frontmatter handoff fields (current_focus / next_action /
   next_prompt / execution_recommendation / last_updated) to reflect this session.
   `next_prompt` restores context and nothing more: it is the previous session's
   account of where the work stood, not a queue of commands and not a place to write
   consent instructions (what a session may do is its launch permission posture). It
   may recommend a release with reasons, but never chain one; a release is its own
   decision, taken with the owner, after continuity is current.
3. Backlog hygiene: de-duplicate backlog titles; move work that shipped to the
   Shipped section as a single line; append newly found bugs to the Backlog.
4. Distill sessions: fold durable content from sessions/*.md into PRD.md, then
   move the distilled note into sessions/archive/ (kept local, excluded from the
   to-distill count) rather than deleting it.
5. Temp notes: distill durable outcomes from .horus/temp/ worker handoff notes
   into PRD.md, then delete the notes (they are fleeting by contract).

One pass at most - act on the signals above, do not iterate warnings to zero.
"""


DISTILL_HISTORY_PROMPT = """Distill-history routine - compress a large log into the curated history.md subset.
Act on the signals above. Edit .horus/history.md (and freeze the source log); never
invent incidents - only compress what the log already records.

Signal test for each entry:
- KEEP: a real problem the project hit + the durable lesson/design change it forced.
- DROP: routine changelog/version-bump noise, resolved-and-irrelevant incidents,
  anything already captured as a rule in decisions.md (cross-reference instead).
- history.md is carried-forward context: NOT a timeline, NOT open issues (those are roadmap.md).

1. Read the source log identified above.
2. Write the high-signal "bumps in the road" into history.md (curated, deduplicated).
3. Mark the source log as superseded/frozen at the top - do not delete it.
"""


DISTILL_HISTORY_PROMPT_V3 = """Distill-history routine (PRD structure) - compress a large log into the curated .horus/archive/history.md subset.
Act on the signals above. Edit .horus/archive/history.md (and freeze the source log);
never invent incidents - only compress what the log already records.

Signal test for each entry:
- KEEP: a real problem the project hit + the durable lesson/design change it forced.
- DROP: routine changelog/version-bump noise, resolved-and-irrelevant incidents,
  anything already captured under PRD.md ## Rules (cross-reference instead).
- archive/history.md is carried-forward context: NOT a timeline, NOT open work
  (open work is the PRD.md Backlog).

1. Read the source log identified above.
2. Write the high-signal "bumps in the road" into .horus/archive/history.md
   (curated, deduplicated; create the file if this is the first distill).
3. Fold any still-load-bearing rule up into PRD.md ## Rules - the archive is
   background, PRD.md is what agents read every session.
4. Mark the source log as superseded/frozen at the top - do not delete it.
"""


INFER_PROMPT_V3 = """Infer routine - bootstrap/refresh PRD-structure continuity from the project's own docs.
Act on the signals above only when the repository already contains useful project
truth or the user explicitly asked for inference. A fresh blank scaffold is valid;
do not manufacture work merely to fill placeholders.

1. Read the canonical docs found above and follow their pointers (README -> status/
   roadmap -> CLAUDE.md/AGENTS.md -> linked docs). Build a model before writing.
2. Distill durable state into .horus/PRD.md:
   - frontmatter: current focus, next action/prompt, execution recommendation, date;
   - Vision: shape and explicit boundaries;
   - Backlog: keep the pointer in PRD.md and create one .horus/backlog/<slug>.md card
     per evidenced open item, with status/priority/type frontmatter;
   - Shipped: one line per evidenced capability;
   - Rules: concise current invariants only.
3. Do not create a starter card or infer an item solely because the backlog is empty.
4. Point to canonical deep references instead of copying them wholesale.
5. Add a one-line superseded pointer to a source doc only when PRD.md truly replaces
   its current-state role; ask before substantially rewriting source docs.
6. When intent is unclear, ask rather than guess. Never invent decisions, dates,
   priorities, versions, or shipped state.

Edit scope: .horus/PRD.md and .horus/backlog/** (plus, with care and consent, a
one-line pointer atop a genuinely superseded source doc).
"""


INFER_PROMPT_V2 = """Infer routine - bootstrap/refresh .horus/ by distilling the project's own docs.
Act on the signals above. The goal is a single concise source of "what is this and
what's next", distilled FROM the canonical docs - not a second copy of them.

1. If .horus/ doesn't exist yet, run `horus init` to scaffold the lanes first.
2. Read the canonical docs found above and follow their pointers (README -> status/
   roadmap -> CLAUDE.md -> linked docs like docs/*.md). Build a model of the project.
3. Distill into the lanes, each in its lane:
   - project.md - what it is, current shape, boundaries, current focus.
   - roadmap.md - open action points (what's next), grouped.
   - features.md - shipped / in-progress / planned capabilities.
   - decisions.md - durable decisions + reasoning, dated.
   - history.md - curated lessons / bumps in the road.
4. Don't duplicate: where a canonical doc stays the deep reference, point at it from
   .horus/ instead of copying it wholesale. Distill the essentials.
5. Mark superseded docs: if a doc's "current state / next steps" role now lives in
   .horus/, add a one-line pointer at its top (e.g. "Current state: see .horus/").
   Ask before substantially rewriting any source doc.
6. When intent is genuinely unclear (status, priorities), ask the user rather than
   guess. Never invent decisions, dates, or versions.

Edit scope: .horus/** (plus, with care and consent, a one-line pointer atop a
superseded source doc).
"""


# Backward-compatible name for callers that mean the retired six-lane prompt.
INFER_PROMPT = INFER_PROMPT_V2
