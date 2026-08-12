"""Agent skills Horus ships and scaffolds into projects.

Like ``templates.py``, skill content lives here as strings — it ships in the wheel
with zero package-data/build config and is written into repos by ``horus init`` /
``horus skill install``.

Skills are the in-app, context-aware counterpart to the deterministic ``horus`` CLI
routines. The CLI commands (``horus consolidate`` / ``horus distill-history``) only
see the files; a skill runs *inside* the active agent session, so it also sees the
live conversation context — the work and decisions that aren't on disk yet. The
skill calls the CLI for the deterministic signals, then applies judgement.

Versioning: each skill carries a ``horus-skill-version`` marker. ``horus doctor`` and
the routine commands compare the installed marker to the bundled one so a shipped
skill update can be detected (the same propagation problem as the managed blocks).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

from horus.continuity import Finding

# Project-scope install locations (relative to the repo root). User scope swaps the
# repo root for the home directory.
CLAUDE_SKILLS_SUBDIR = ".claude/skills"
CODEX_SKILLS_SUBDIR = ".agents/skills"
TARGET_SUBDIRS = {
    "claude": CLAUDE_SKILLS_SUBDIR,
    "codex": CODEX_SKILLS_SUBDIR,
}
_VERSION_RE = re.compile(r"horus-skill-version:\s*(\d+)")


# Who a bundled skill is FOR. Every skill here is projected into managed projects,
# so an unlabelled one gets read as being for the project it lands in.
AUDIENCE_PROJECT = "project"  # operates on the project it is invoked in (the default)
AUDIENCE_HORUS = "horus"  # operates on Horus's own source; only valid in this repo


class Skill(NamedTuple):
    name: str
    version: int
    content: str
    audience: str = AUDIENCE_PROJECT

    def rel_path(self, *, target: str = "claude") -> str:
        return f"{TARGET_SUBDIRS[target]}/{self.name}/SKILL.md"


def is_horus_repo(project_root: Path) -> bool:
    """True when ``project_root`` is the horus-harness checkout itself.

    Keyed on the skill generator, because that is precisely what an
    ``AUDIENCE_HORUS`` skill exists to operate on — a consumer project has the
    projected ``SKILL.md`` copies but never the module that writes them.
    """
    return (project_root / "horus" / "skills.py").is_file()


def bundled_for(project_root: Path, *, user: bool = False) -> tuple[Skill, ...]:
    """The bundled skills that belong in this project — the ONE roster.

    Install, staleness and doctor/TUI state all read this, so a skill withheld
    from a project is never then reported missing from it. User scope is left
    unfiltered: it is a deliberate machine-wide install by the owner, not a
    projection into a project that cannot use the skill.
    """
    if user or is_horus_repo(project_root):
        return SKILLS
    return tuple(s for s in SKILLS if s.audience == AUDIENCE_PROJECT)


class SkillAction(NamedTuple):
    status: str  # "created" | "updated" | "exists" | "skipped"
    message: str


# Per-agent install states of a bundled skill. These four are the canonical
# statuses both `skill_findings` (doctor/nudge prose) and the read-only TUI skills
# viewer speak — one detection path, so the viewer renders these directly instead
# of re-parsing the prose findings (Terminal-TUI-stays-thin).
SKILL_INSTALLED = "installed"  # present at the bundled version
SKILL_OUTDATED = "outdated"  # present at an older version
SKILL_MISSING = "missing"  # bundled but not installed
SKILL_UNVERSIONED = "unversioned"  # present without a version marker (customized)


class SkillState(NamedTuple):
    """Structured install state of one bundled skill for one agent target.

    The single detection projection behind both ``skill_findings`` and the TUI
    skills viewer — no new scanning; it reuses ``skill_path`` / ``installed_version``
    / ``SKILLS`` exactly as the doctor findings do.
    """

    target: str  # "claude" | "codex"
    name: str
    bundled_version: int
    installed_version: int | None  # None when missing or unversioned
    status: str  # one of the SKILL_* constants above

    @property
    def refresh_command(self) -> str:
        """The one canonical refresh command for this target (never auto-run)."""
        return f"horus upgrade-project --apply --target {self.target}"


# --------------------------------------------------------------------------- #
# Bundled skill content
# --------------------------------------------------------------------------- #

_CONSOLIDATE_SKILL = """\
---
name: horus-consolidate
description: >-
  Consolidate a project's Horus continuity (`.horus/`) — a light backlog-hygiene
  pass over the single `PRD.md` file
  (size vs the character budget, stale frontmatter, undistilled optional recovery notes,
  duplicate or lingering-done backlog items). Use this whenever
  reaching a real continuity boundary in a repo that has a `.horus/`
  directory; when the user says "consolidate", "wrap up", "update continuity",
  "tidy the roadmap"/"tidy the backlog", or "close out"; before an
  agent/account/machine change, dispatch, pause, release, or end; or whenever
  `.horus/` looks like it's drifted. Prefer this over
  editing `.horus/` ad hoc, because it runs `horus consolidate` for precise
  signals first and applies consistent routing rules.
---

<!-- horus-skill-version: 20 -->

# Consolidate Horus continuity

You are running *inside* the working session, so you have something the `horus`
CLI does not: the **live context of what just happened** — decisions made, work
shipped, things discussed but not yet written to `.horus/`. Use that. The CLI sees
only the files and git; you see the conversation too. Fold both in.

`horus consolidate` inspects `.horus/` and reports the signals for whichever
structure the project uses — follow the matching section below.

## PRD-structure projects (v3 — `.horus/PRD.md` present)

`PRD.md` is the **one maintained continuity file**: frontmatter (`status`,
`current_focus`, `next_action`, `next_prompt`, `execution_recommendation`,
`last_updated`) plus Vision / Backlog / Shipped / Rules sections. `sessions/`
contains optional, local/gitignored recovery notes; `temp/` contains fleeting
worker handoff notes.

### Two jobs — do not conflate them

- **Continuity close (at a real boundary, bounded):** fold this campaign's delta into
  `PRD.md` and refresh the frontmatter handoff fields.
- **Backlog hygiene (small, do it whenever `horus consolidate` flags it):** trim
  the file back under the line cap, delete done items, split duplicate titles.
  Mechanical — no need to wait for an explicit "pay down continuity debt" ask
  the way v2's backlog pass does; a v3 PRD drifts fast if hygiene waits.

### The dashboard contract — keep these current at EVERY close

The shared reader (`resolve_focus`) is PRD-first, so `current_focus`,
`next_action`, `next_prompt`, and `execution_recommendation` must live in
`PRD.md` frontmatter (not a shim). `horus close --check` fails while any of
them is stale or empty.

### Steps

1. **Get the deterministic signals.** Run `horus consolidate` (optionally
   `--path <repo>`). On a v3 project it reports **backlog-hygiene signals
   only** — no lane-routing/overlap warnings, because there are no lanes to
   route between:
   - **Size vs the ~60,000-char budget** — warns past 45,000, more urgently past
     60,000, and names the driving section by characters. Characters, not lines:
     a line count measures shape, not what a fresh agent pays to read the file.
     Per-section entry contracts fire alongside it — `## Shipped` entries over
     ~400 chars (one line per capability, details in git history) and `## Rules`
     entries over ~600 (concise rules, NOT a log; route dated incident narratives
     to `.horus/archive/history.md`). Fix by trimming, never by unwrapping
     hard-wrapped bullets: that reclaims lines while removing nothing.
   - **Stale frontmatter** — when a recovery note exists, `last_updated` older than
     its date means the note may still contain undistilled context. Refresh the
     content and bump the date.
   - **Undistilled recovery notes** — more than a dozen files directly in
     `sessions/` (excluding `README.md` and `archive/`). Move older ones to
     `sessions/archive/` (local, git-ignored, doesn't count against the cap).
   - **Duplicate backlog titles** — two `## Backlog` items whose bold
     `**Title**` text matches case-insensitively. Merge or rename one.
   - **Lingering done items** — a backlog item checked `[x]` or prefixed
     `DONE`/`Done:`. Delete the item; a `**Result … PASS**` note continuing a
     still-open item is not itself a done marker, leave those.
   - **Topic standings (advisory)** — groups active and shipped cards by their
     free-form `topic:` slug and reports open/shipped counts. Blank topics remain
     visible as `Unsorted`; prefer an existing topic before minting a new one.

2. **Read `PRD.md`**, any relevant `temp/*.md` handoff notes, and the newest
   `sessions/*.md` recovery note only when one exists.

3. **Record this campaign, in `PRD.md` only** (never source, `AGENTS.md`, or
   `CLAUDE.md`):
   - Fold capabilities shipped *this session* into `## Shipped` as **one line
     each** — not a paragraph; detail lives in git history and optional recovery notes.
   - Add or update `## Backlog` items for new or changed open work. Cards carry an
     optional free-form `topic:` slug; prefer joining an existing topic and leave a
     genuinely ungrouped card blank so it remains visible under `Unsorted`. Give a
     new/next-touched card one testable acceptance line (EARS-lite: "when X, the
     tool should Y").
   - Add any newly load-bearing invariant to `## Rules`, concise and
     current-state only (not a dated log — git history and optional recovery
     notes carry rationale when needed).
   - Refresh the frontmatter handoff fields and bump `last_updated`. Author
     `next_prompt` as orientation and nothing more: where the work stood, and the
     minimum context a fresh session should read before acting. Do NOT write consent
     instructions into it — what a session may do is set by its launch permission
     posture, which the agent CLI enforces; a consent paragraph here is prose the
     model can reinterpret, and it contradicts a session launched to work directly.
     A release may be suggested with concrete reasons but never chained as "then
     release": it is its own decision, taken with the owner, after continuity is
     current. **When the owner did not explicitly request delegation in this
     conversation, write**
     `execution_recommendation: "continue-as-is — <why>"`
     **regardless of the next task's breadth, phase count, or number of surfaces.
     Never infer delegation from how big the work looks** — breadth may shape an
     inline plan, but it never grants authority to stand up a supervisor/worker
     workflow. The field records an owner-authorized execution choice; it is not a
     task-size classifier. **Setting this field is
     not a trigger for `execution-decision`.** Invoke that skill only when the
     owner explicitly asks whether or how to delegate the next task. If invoked,
     apply its need-first rubric and use `"plan-execution — <why>"` only for work
     whose concrete context, parallelism, or price dividend exceeds the fixed
     supervisor tax (then create/update `execution.md` before implementation).
     Cross-project scope, multiple phases, and calibration goals are not
     dividends by themselves. Do not sell supervisor review as the safeguard
     (reproduce the gate / bound checkpoints / safety-in-code are the durable
     ones).
   - When a `temp/` worker handoff note exists, treat it as evidence, not
     truth: review the diff/tests yourself, then fold the accepted facts into
     `PRD.md` and update `execution.md` if a phase completed.
   - Apply the recovery test: create a local `sessions/` note only when PRD/backlog
     plus git/PR state cannot resume incomplete work, a dirty tree, an unresolved
     investigation, or an agent/account handoff. Do not create one as ceremony.

4. **Apply backlog hygiene** for whatever Step 1 flagged. This is normally
   small enough to fold into the same close — don't let the file blow the cap
   before acting on the warning.

5. **Verify.** Run `horus close --check` — it must pass. **A green PR is not a landed
   PR** — that output names your own unmerged remote branches; read that line rather
   than skimming it. A branch left open goes stale enough that merging it later
   reverts work. One `consolidate`
   pass at most per close; don't chase every signal to zero (a duplicate title
   you've deliberately kept apart, for instance, is fine to leave).

### Boundaries

- **Never invent** status, dates, versions, or decisions. When intent is
  unclear, leave the content and flag it for the user rather than guessing.
- Edits are confined to `.horus/**`. This is continuity maintenance, not a
  coding task.
- Bump `last_updated` in `PRD.md` frontmatter if it isn't already today.
- Recovery notes are gitignored and never substitute for durable state before a
  machine change; push the branch and put required context in PRD/cards/a brief.

"""


_DISTILL_HISTORY_SKILL = """\
---
name: horus-distill-history
description: >-
  Compress a large, raw project log (a long `docs/HISTORY.md`, `CHANGELOG.md`, or an
  oversized history archive) down to the curated "bumps in the road" worth carrying
  forward — the problems that bit the project and the durable lessons they forced.
  The curated result lives in
  `.horus/archive/history.md`, with any still-load-bearing rule folded into `PRD.md`'s
  `## Rules`. Use this
  whenever onboarding Horus into a long-running project with a big changelog; when
  the user says "distill the history", "compress the changelog", "the history file
  is too long", or "summarize the project log"; or when the curated history has grown
  into a timeline instead of a lesson set. Runs `horus distill-history` first for the
  source-log location and size.
---

<!-- horus-skill-version: 4 -->

# Distill project history

Turn a verbose log into the high-signal subset worth carrying forward. You are not
writing a timeline — you are keeping only what a future agent would otherwise have
to re-learn the hard way.

## PRD-structure projects (v3 — `.horus/PRD.md` present)

The curated target is **`.horus/archive/history.md`** — in this structure history is
retired-lane material, not an actively maintained file (`PRD.md`'s `## Rules` section
is the *current*-state surface; this archive is the *why* behind it, same idea as
`decisions.md` + `history.md` in v2, just no longer live lanes).

1. **Locate the source.** Run `horus distill-history` (optionally `--path <repo>` /
   `--source <file>`) for the source log it found. Its `.horus/history.md missing`
   line is a known false note on v3 projects — the deterministic pre-pass predates
   the archive convention and doesn't look in `.horus/archive/` yet; ignore that
   line and check `.horus/archive/history.md`'s current size yourself.

2. **Read the source log** in full (or in chunks if very large).

3. **Apply the signal test** to every entry: keep a real
   problem plus the durable lesson/design change it forced; drop routine noise,
   version bumps, and anything already captured as a `PRD.md` `## Rules` entry
   (cross-reference instead of duplicating).

4. **Write the curated subset** into `.horus/archive/history.md` (create the
   `archive/` directory if this is the first distillation): short, deduplicated
   "bumps in the road", each pairing the problem with the lesson. Not a timeline.

5. **Promote load-bearing lessons.** If a lesson amounts to an invariant the
   project must keep obeying (not just "this happened once"), also add a
   concise one-liner to `PRD.md`'s `## Rules` — that's the surface a cold
   reader actually checks day to day.

6. **Forward open work, don't drop it.** Roadmap-shaped material (backlog,
   "next session", planned-but-not-done) isn't history — note it for the user
   to fold into `PRD.md`'s `## Backlog` rather than silently dropping it. (This
   skill edits history/archive material, so flag it; don't edit `## Backlog`
   here.)

7. **Freeze the source**, don't delete it: add a one-line "superseded —
   curated in `.horus/archive/history.md`" pointer at the top of its body
   (below any YAML front matter) so the two don't drift.

### Boundaries

- Only compress what the log records — **never invent** incidents, dates, or causes.
- Edit `.horus/archive/history.md`, at most a one-line addition to `PRD.md`'s
  `## Rules`, and the one-line pointer on the source log; nothing else.

"""


_INFER_SKILL = """\
---
name: horus-infer
description: >-
  Bootstrap or refresh a project's Horus continuity (`.horus/`) by distilling the
  project's own canonical docs — README, status/roadmap files, CLAUDE.md/AGENTS.md,
  and linked docs — into `.horus/`: the PRD-structure `PRD.md` skeleton (Vision /
  Backlog / Shipped / Rules). Use this when setting Horus up in an existing repo that already has useful docs;
  when the user says "set up horus here", "bootstrap the .horus files", "populate
  the continuity", "infer the project state", or "fill in the backlog/roadmap from
  our docs". A blank scaffold is valid until a real use case or evidenced docs exist.
  Runs `horus infer` first to find canonical docs and empty/placeholder sections.
---

<!-- horus-skill-version: 8 -->

# Infer Horus continuity from the project's docs

Most repos already encode their state in prose (a README, a status doc, a roadmap).
This distills that into `.horus/` as the single concise source of "what is this and
what's next" — pointing at the canonical docs rather than copying them, so the two
never drift.

`horus infer` reports which structure the project uses — follow the matching
section below.

Do not invoke inference merely because `horus init` produced blank placeholders.
With no useful source truth and no concrete user request, leave the scaffold blank.

## PRD-structure projects (v3 — `.horus/PRD.md` present)

1. **Get the signals.** Run `horus infer` (optionally `--path <repo>`). It lists
   the canonical docs to distill from and which `PRD.md` skeleton sections
   (Vision / Backlog / Shipped / Rules) are missing or still placeholder text.
   **Registration is separate from continuity.** A cloned `.horus/` directory is
   repo-local continuity, not machine-local fleet registration. If the signals say
   the project is not visible in the Horus fleet/TUI, run the named `horus init
   <path>` remedy before treating onboarding as done.

2. **Read the canonical docs and follow their pointers** — README → status/roadmap →
   CLAUDE.md/AGENTS.md → linked docs like `docs/*.md`. Build a real model of the
   project before writing anything.

3. **Distill into `PRD.md`**, one file, each section concise:
   - Frontmatter: `status`, `current_focus`, `next_action`, `next_prompt`,
     `execution_recommendation`, `last_updated`.
   - `## Vision` — what the project is, its shape, and explicit out-of-scope
     boundaries:
     - **Why this exists.** The originating problem, who it was built for, and — if
       the project was forked, split, or pivoted — what it inherited **on purpose**
       and what that inheritance is for. A reader must be able to tell deliberate
       inheritance from legacy without asking.
     - **Surfaces and audiences.** Once a project has more than one entry point,
       name each and say who it serves (human operator, agent, CI, consumer). When
       the product *is* an interface, this is load-bearing: an unlabelled surface
       will be mistaken for the contract.
   - `## Backlog` — retain the thin pointer. Create one
     `.horus/backlog/<slug>.md` card per evidenced open item, with
     `status`/`priority`/`type` frontmatter; do not create a starter card.
   - `## Shipped` — **one line per capability**, not a paragraph; the deep
     detail lives in git history, not here.
   - `## Rules` — durable, current invariants only (not a dated log — if the
     docs describe *why* a rule exists or a superseded alternative, that
     rationale belongs in git history, an optional recovery note when needed, or
     `.horus/archive/`, not `PRD.md`).

4. **Don't duplicate.** Where a canonical doc stays the deep reference (e.g. a
   detailed architecture doc), point at it from `PRD.md` instead of copying it
   wholesale. Keep the whole file well under the ~60,000-char budget — `horus
   consolidate` will start warning past 235.

5. **Mark superseded docs — only when truly superseded.** If a doc's "current
   state / next steps" role now lives in `PRD.md`, add a one-line pointer at
   its top. But if `PRD.md` merely *distills* a doc that stays the canonical
   deep reference, add no pointer. Ask before substantially rewriting any
   source doc.

### Boundaries

- When intent is genuinely unclear (real status, priorities, what shipped vs
  planned), **ask the user** rather than guess. Never invent decisions, dates,
  or versions — `## Rules` in particular: only record an invariant the docs
  actually state; leave it thin rather than manufacturing one.
- When a project is a fork, split, or pivot, ask the owner for "why this exists"
  rather than distilling it from inherited docs.
- Edit scope is `.horus/PRD.md`, plus — with care and consent — a one-line
  pointer atop a superseded source doc.

"""


_EXECUTION_SKILL = """\
---
name: horus-execution
description: >-
  Supervise a Horus execution plan for work actually delegated/dispatched to one
  or more other agent sessions. Use this ONLY when the owner explicitly requested
  delegation in this conversation — workers/subagents, dispatch, handoff, model
  separation, or supervision — or when resuming an already-active delegated plan
  or reviewing an existing worker handoff (their authorization happened when that
  plan was created). An `execution_recommendation: plan-execution` field is NOT on
  its own a reason to load this skill: it records an owner-authorized choice, it
  never grants a new one, and a stale field with no active plan is stale intent.
  Never infer delegation from a task's breadth, phase count, or number of
  surfaces. It keeps `.horus/execution.md` fluid, uses
  `.horus/temp/` for fleeting worker notes, and distills durable outcomes back
  into `PRD.md` at closure.
---

<!-- horus-skill-version: 17 -->

# Horus execution supervision

This skill is for the supervisor agent. It coordinates work actually delegated
or dispatched to other agent sessions without turning `.horus/` into a
transcript or a second issue tracker.

## Invocation boundary

Requests for a plan, phased implementation, sequencing, estimation, or “are
you ready to start?” do **not** invoke this skill unless they also request
another agent/worker/subagent, dispatch, handoff, model separation, or
supervision. Those requests remain ordinary inline planning and do not create
`.horus/execution.md`.

`execution_recommendation: plan-execution` denotes a worker/supervisor execution
plan whose work is actually delegated or dispatched to other agent sessions. It
does not denote an ordinary multi-step task; ordinary phased work remains direct
and needs no `.horus/execution.md`.

**The field is a record, never a fresh authorization.** It says the owner once
authorized delegation for a specific plan; it cannot authorize the next one. So
`plan-execution` sitting in frontmatter with **no active execution plan** and no
explicit owner delegation request in *this* conversation is **stale intent** —
say so and continue inline, rather than reading it as permission to load this
skill, run `horus execution prompt`, or propose `.horus/execution.md`.

## Two substrates, and delegation authorization is bounded to the one asked for

A request to delegate authorizes delegation on the substrate the owner named. It
does **not** authorize changing provider, account, or session topology.

| Substrate | Session / account | Coordination |
|---|---|---|
| **Native subagent** (Claude's Task/Agent tool, Codex's own agent spawning) | a child of the current supervising session; normally the same account and runtime | the agent CLI's own collaboration tools — a bounded task and supervisor synthesis. **No `horus run`, no account switching, no `execution.md`, no Horus usage routing, and this skill is not involved.** |
| **Horus external worker** | a tracked external agent-CLI session that may select another provider/model/account/worktree | `horus run`, the usage/account consent envelope, receipts, and this skill |

"Use a native subagent for this" is therefore **not** permission to launch
another provider or spend another account's budget. "Dispatch this through Horus
on the <account> account" is the explicit external-worker case. If the owner says
"subagent" or asks about "lower models" without naming the substrate, and the
answer would change provider/account/session topology, **ask one clarification
question before** reading another account's usage or proposing a dispatch
envelope. Cost grounding still applies to native fan-out — via the agent CLI's
own contract, never by manufacturing a Horus worker envelope for it.

## When to use it

- The owner explicitly requests another agent/worker/subagent, dispatch,
  handoff, model separation, or supervision for bounded work **through Horus**.
- The owner is explicitly testing or requesting supervisor/worker model separation.
- An already-active delegated execution plan needs to resume — the authorization
  happened when the plan was created, so the owner need not restate it each turn.
- An existing worker handoff under `.horus/temp/` needs supervisor review.

Not on this list, deliberately: an `execution_recommendation` field on its own, a
broad or multi-surface task, a long phase list, and a native subagent the owner
asked for inside this session.

## Confirm delegation already earned its cost

Before creating `execution.md` or a worker handoff, apply the delegation rubric below.
Load the `execution-decision` skill itself only if the owner asked how or whether to
delegate — being inside this workflow is not on its own a reason to load it. Define the
bounded unit and require a concrete dividend that exceeds the fixed
brief/review/gate/merge/closure tax. Do not enter this workflow merely because work
spans projects or phases, or to collect a model datum.

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

1. **Read the continuity.** Read `.horus/PRD.md` (vision/backlog/shipped/rules +
   the frontmatter handoff fields) and `execution.md`. Review relevant
   `.horus/temp/*.md` handoff notes only when an execution plan is active.

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

## Boundaries

- Do not force `execution.md` onto small single-agent tasks.
- Do not delegate just because a table has `worker_tier: standard`; require an explicit
  `delegation_basis` or keep the work direct.
- Do not commit `.horus/temp/` worker notes; they are local, fleeting evidence.
- Do not trust worker notes blindly. Verify the diff and test result before updating
  durable lanes.
- Do not store secrets or full transcripts in `.horus/`.
"""


_DELEGATION_RUBRIC_SKILL = """\
---
name: delegation-rubric
description: >-
  Shared, data-backed reference for the two delegation-decision skills
  (`execution-decision` and `dispatch-decision`). It encodes ONE calibration +
  verification rubric: how to read `horus capabilities --models` (measured
  datums + owner priors from the empirical spine), turn a task shape into a mode
  + model-tier recommendation, and dial verification depth by how proven that
  tier is. NOT invoked on its own — the two decision skills load it so the logic
  lives in one place and a model re-tag (new datums) propagates to both flows.
  Advisory only: it EMITS a recommendation the agent applies; it never
  auto-selects a model or auto-routes a dispatch.
---

<!-- horus-skill-version: 12 -->

# Delegation rubric — shared calibration + verification logic

Single source of truth for the delegation-decision framework. Both
`execution-decision` (in-project — native subagent or Horus worker) and `dispatch-decision`
(cockpit, multi-project sessions substrate) LOAD this file and apply the steps
below. They differ only in their substrate and their mode vocabulary; the
calibration ladder and the verification logic are identical and live *here* — so
a model re-tag in the datums moves both flows at once, and the same tier-trust
sets BOTH the model pick AND how hard to verify.

## Hard boundary (do not cross)

This rubric is **advisory**. It produces a recommendation — mode + tier +
verification depth — that the agent reads and APPLIES. Nothing here auto-selects
a model, auto-routes a dispatch, or spends. `horus capabilities` stays
data-only: there is no `--for`/pick mode and you must not add one. Orchestration
is ceded to execution planes; Horus stays the memory plane that measures and
displays (drift trigger: `research/omnigent.md`).

## Precondition — prove delegation has a dividend

Before reading the model roster, define the bounded work unit and name what a
separate worker actually buys: context the current session avoids loading, useful
parallelism, or lower-tier savings. Compare that with the fixed tax of briefing,
reviewing, observing the gate, merging, and closing continuity.

**Delegation raises total cost — it is a time/capacity/parallelism lever, never a
cost saver** (measured 2026-07-17, `research/2026-07-17-delegation-cost-finding.md`).
A cheaper worker does not mean cheaper work: a fresh worker re-pays cold-start
context on every card while an inline session amortizes one compounding context,
verification runs twice, and a single account captures no parallelism. That is why
the tax above is fixed rather than proportional to the task.

- If the benefit is unclear or does not plausibly exceed that tax, stay inline and
  stop the routing analysis before selecting a model.
- Cross-project scope, multiple phases, and a desire to collect calibration data are
  not dividends by themselves.
- Decide per bounded unit, not once for an entire campaign. An integrated long-running
  session may be the cheapest place for cross-project judgment because it already
  holds the context that handoffs would discard.
- Never manufacture work or a worker solely to earn a datum.
- An explicit owner direction may instead optimize expiring isolated-account
  capacity or protect supervisor context. Label that as the dispatch basis; do not
  pretend it is a feature-economics dividend.

## Step 1 — Read the calibration data

Run `horus capabilities --models` (add `--stdout` for JSON). It is data only and
names no model to pick. Per model it reports:

- **`tier`** (owner prior) — the role the owner assigns: design/ambiguity/verify
  gate, scoped-impl lead, mechanical, frontier, codex, …
- **`clean_count` / `quality_datums`** (measured) — quality rate over only
  `clean` / `nudged` / `bounced`; `died_count` and `void_count` stay visible
  separately and never lower that denominator. `closed_datums` / `total_datums`
  still show how many runs were reviewed and seen overall.
- **`last_outcomes`** (measured, most-recent first) — the recent track record:
  quality outcomes only (`clean` / `nudged` / `bounced`).
- **`strength` / `caution` / `guard`** (owner priors, free text) — `caution` and
  `guard` are HARD constraints on how the model may be used.

It also prints a **vendor-neutral tier map** below the ladder: each capability
point — `low | medium | high | frontier` — with the model EACH provider fields
there (Claude and Codex/GPT), the effort that rides with it, and whether that
model is `measured` (has local datums) or still a `prior`. A card/envelope
`tier:` names one of these points, never a vendor. This is the map you pick a
provider *within* — the tier is the capability requirement; the provider is a
separate choice made at Step 6 from capacity + owner choice.

Counts are not task-shape evidence by themselves. Read recent matching outcomes and
their notes, and keep measured datums distinct from explicit owner observations. If a
native usage signal is incomplete, stale, or temporarily lifted, an owner-provided
reading may override it for this decision; label the source rather than pretending the
telemetry was complete.

## Step 2 — Read the task shape (four axes)

- **Ambiguity** — is the goal + acceptance crisp, or exploratory/underspecified?
- **Volume** — a small localized change, or high-volume / repetitive work?
- **Runtime surface** — pure logic (tests are the gate), or a runtime/visual
  surface (server, UI, CLI UX) a human must eyeball?
- **Scope clarity** — are the files / blast-radius known and fenceable, or
  open-ended?

## Step 3 — Tier-trust ladder (data, not hardcode)

Trust is READ from the live data, never pinned to a model name or a count copied into
this skill:

- **Proven** = many `clean` closed datums with a clean recent `last_outcomes`
  streak. Trust it on work matching its `tier`.
  Well-matched proven work is the strongest delegation candidate.
- **Unproven** = 0–few quality datums. Prefer it ONLY on well-matched, scoped work
  where a clean gate will catch a miss — you are calibrating it, so the win is
  the datum as much as the output. Never hand an unproven tier a large/loose
  task.
- **Owner flags gate the pick.** A `caution` or `guard` is a hard constraint —
  read it before matching. A token-headroom guard, for example, takes the model
  off the table when the best available usage evidence says the ceiling is near.
- **Keep older-but-capable models in the roster.** A prior-frontier model
  does not stop being capable the day a newer model ships — it may still be the strongest AND
  cheapest fit for scoped/mechanical work. Don't drop a model from the ladder on
  recency alone: pick by capability-for-the-task, not by release date, and keep
  gathering datums on it so the ladder reflects measured reality instead of
  assumption.
- **Match tier to shape** (this mirrors the managed-block model-tier rule; the
  data tells you which concrete model fills each role now and how proven it is):
  design / ambiguity / the verify gate → the live design tier; most scoped
  implementation → the live scoped-implementation tier; mechanical verifiable
  sweeps → the live mechanical tier, never as the judgment gate.
- **Name the tier as a capability point, not a vendor.** Step 4 emits a
  vendor-neutral tier (`low|medium|high|frontier`); the neutral-tier map from
  Step 1 shows which provider models sit there. Do NOT let the label pick the
  vendor — a card tagged `medium` is not a "Sonnet card", it is a scoped-impl
  card that Sonnet *or* the equivalent Codex model can take. Which provider
  actually runs is decided at Step 6 from live capacity + owner choice.

## Step 4 — Shape → mode + tier

The mode *vocabulary* belongs to the consuming skill; the shared axis is:

- Small / ambiguous / exploratory / debugging → **stay inline** (orchestration
  overhead + judgment loss dominate; delegation buys little).
- High-volume / low-ambiguity / clear gate / fenceable scope → **delegate** to
  the best-matched tier from Step 3, then reproduce the gate.
- Large AND multi-phase / spans surfaces → **delegate as a phased plan only when**
  the phases are independently fenceable and the named context or parallelism
  dividend exceeds the supervisor tax; otherwise keep the integrated campaign inline.
- Runtime/visual surface where the *user* is the real reviewer → delegate the
  build, but the gate is the owner's eyeball, not a code read.

Pick the tier from Step 3: prefer a proven tier on matched work; an unproven
tier only on scoped work with a clean gate; respect every `caution` / `guard`.

## Step 5 — Verification depth, dialed by the SAME tier-trust

The pick and the verification are two ends of one lever: the less proven the
tier you chose, the harder you verify — because you are calibrating it.
Verification means **observing a deterministic gate you did NOT author** — never
re-running the worker's own narrative, never trusting a "tests pass" prose
claim, whoever wrote it.

- **Reproduction ≠ re-running the suite.** A *required* CI check green on the
  exact commit reproduces the test gate — don't re-run what it already covers.
  Reproduction is a deterministic signal you observe yourself.
- **Proven + gate green → just observe** the gate and move on. No line-by-line
  re-read; the diff review is for scope/risk, not as evidence it works.
- **Unproven → verify more:** observe the gate AND add one independent probe of
  the changed surface. You're building the datum, so spend a little more to
  trust the result — then close the loop with `horus datum close` so the next
  decision is better calibrated.
- **Runtime / visual surface → default to asking the OWNER** to eyeball it. A
  mocked test blesses nonexistent flags; only a live drive of the real surface
  counts. Self-probe only when the owner is away AND has pre-authorized it for
  this session.
- Each consuming skill adds its substrate-specific gate (in-project: run the
  gate at the phase boundary; overseer: observe required CI green on the merge
  SHA). The dial above is the same in both.

## Step 6 — Bind dispatch to explicit owner consent

Before any implementation worker is launched, present one exact consent envelope:

- agent and concrete model (not only a tier), effort, and account alias. This is
  where the neutral tier from Step 4 resolves to ONE provider+model: present the
  candidates the neutral-tier map lists at that point (Claude and Codex), gated
  by each account's live `horus usage check`, and let the owner pick. Never
  default to the Claude candidate because the tier label used to be a Claude
  name — capacity + owner choice decides, not the label;
- current usage and reset evidence for that account, including source and freshness;
- bounded task, maximum attempts, expected dispatch dividend or owner-directed
  capacity/context override, and the deterministic verification gate.

The **concrete model** is the exact selector the target CLI will execute, which
is not always the same string as the Horus calibration key that names it in
history. Horus's calibration keys use a dotted `family-major[.minor]` shape;
Claude Code's own `--model` flag instead accepts a bare family alias or a full
dash-separated selector — the calibration-key spelling looks exact but Claude
Code rejects it before any work starts. `horus run` rejects a known
calibration-only Claude label before creating a worktree or session as a
backstop, but the envelope should already name the executable selector.

Wait for explicit owner approval of that envelope. Approval does not authorize a
different model, account, effort, task scope, or another attempt. Ask again before
any such change — including a corrected provider selector for the same intended
model; a provider failure never permits silent fallback. This approval is
the execution plane's responsibility—Horus records and displays evidence but never
authorizes, selects, or launches by itself.

Do not predict a per-task usage percentage. At completion, use the mechanically
captured start/end readings and `horus datum report`; show a delta only when Horus
labels fresh same-window isolated readings unconfounded. Otherwise report the actual
readings as unknown or confounded. Do not poll continuously or make another model call
for accounting. Runtime is a weak proxy for task size — 362s for a ten-step release
chain versus 481s for a two-line guidance edit, same model and effort (2026-08-01) —
so never read wall-clock as a measure of how much work a dispatch did.

Parallel workers on the same provider account trade attribution for throughput. State
that trade-off in the consent envelope: serialize or use isolated account aliases when
per-worker usage matters; otherwise accept `concurrent/confounded` readings.

## Step 7 — Emit the recommendation

Emit three things for the agent to APPLY (never auto-apply them):

- **mode** — in the consuming skill's vocabulary,
- **tier** — a concrete model, chosen from the data + shape,
- **verification depth** — observe-only vs observe+probe vs owner-eyeball, with
  the one deterministic gate you'll observe named explicitly.

For a dispatched mode, also emit the complete consent envelope from Step 6 and
state `awaiting owner approval`; never launch as part of the recommendation.

**When the mode is a dispatched one** (anything that spawns a tracked *external*
worker rather than staying in this session — `dispatched-worker`/`dispatched-plan`
in `dispatch-decision`'s vocabulary, `horus-worker` in `execution-decision`'s;
`native-subagent` is NOT one, since it neither leaves the account nor pays the
tracked-worker tax),
also name the expected **dispatch dividend**: the context/detail the overseer
avoids by not implementing this inline, weighed against the fixed supervisor
tax every dispatch pays regardless of size — brief + review + gate + merge +
reinstall + datum/continuity close. Recommend dispatch only when the savings
plausibly exceed that tax, OR when parallelism / protecting the overseer's own
context was the explicit named benefit — say which one. `horus capabilities
--models`'s per-model cost glance (`dividend +P/~N/-Neg · oversight median: …`,
from `horus datum close --dividend`/`--oversight` — see `horus/datums.py`) is
the measured record of how that judgment actually played out on past
dispatches of this tier; read it as the closest thing to evidence before
naming the expected dividend. This stays advisory prose only, same hard
boundary as everything else here: no auto-scored dividend, no auto-routing —
the harness only ever RECORDS the closed `--dividend` judgment after the fact,
it never predicts or picks one up front.

Always show the live data and owner evidence that drove it, clearly labelled. The
agent decides and acts; you advise.

"""

# Shape -> tier-role mapping (the rubric's Step 3/4 essence) and tier-trust ->
# verification-depth dial (Step 5), as structured data. This is the single source
# `horus capabilities --matrix` reads to render the ladder — the CLI command joins
# these tables with the live roll-up from `datums.build_model_rollup` rather than
# forking a third copy of the rubric's logic. Keep this in sync with the prose
# above when either changes; the two describe the same mapping.
DELEGATION_SHAPE_TIERS: list[dict[str, str]] = [
    {
        "shape": "novel",
        "tier_role": "design / ambiguity / verify gate",
        "description": "Ambiguous, exploratory, or design work — also the verify gate.",
    },
    {
        "shape": "scoped-impl",
        "tier_role": "scoped-impl lead",
        "description": "Most scoped implementation work — clear gate, fenceable scope.",
    },
    {
        "shape": "mechanical",
        "tier_role": "mechanical",
        "description": "Mechanical, verifiable sweeps — never the judgment gate.",
    },
]

DELEGATION_VERIFICATION_DIAL: list[dict[str, str]] = [
    {
        "tier_trust": "proven",
        "verification": "observe-CI",
        "description": "Proven tier + gate green -> just observe the gate.",
    },
    {
        "tier_trust": "unproven",
        "verification": "CI+probe",
        "description": "Unproven tier -> observe the gate AND add one independent probe.",
    },
    {
        "tier_trust": "runtime",
        "verification": "owner-eyeball",
        "description": "Runtime/visual surface -> default to asking the owner to eyeball it.",
    },
]


_EXECUTION_DECISION_SKILL = """\
---
name: execution-decision
description: >-
  Decide HOW to execute an in-project task: recommend `inline` vs
  `native-subagent` (a child of THIS session, same account) vs `horus-worker` (a
  tracked external agent-CLI session that may use another provider/model/account),
  plus a model tier and a verification depth. Owner-invoked only: use this ONLY
  when the owner explicitly
  asks whether or how to delegate, hand work to a worker/subagent, or prepare a
  delegated execution plan. Do not trigger it for ordinary feature/fix planning,
  merely because `execution_recommendation` needs setting, or because the agent
  wonders whether delegation might help; stay inline without loading it. It reads
  live calibration data (`horus capabilities --models`) through the shared
  delegation rubric. Advisory: it EMITS a recommendation you apply — it never
  auto-selects a model or auto-spawns a worker. For cross-project cockpit dispatch
  use `dispatch-decision` instead.
---

<!-- horus-skill-version: 7 -->

# Execution decision (in-project)

You are choosing how to execute the NEXT in-project unit of work. This skill is
the thin in-project consumer of the shared rubric — it adds the in-project mode
vocabulary and one substrate note, nothing else. It pairs with
`horus-execution`, which supervises a **Horus worker** plan once you've decided
to delegate to one.

## Two substrates — decide this BEFORE reading any usage data

"Delegate" is not one thing here. One repo and one working session can reach two
different substrates, with different costs and different consent requirements:

| | **Native subagent** | **Horus worker** |
|---|---|---|
| What it is | a child of THIS session (Claude's Task/Agent tool, Codex's own agent spawning) | a tracked external agent-CLI session (`horus run`) |
| Provider / account | normally the same runtime and the same account | may be another provider, model, account, or worktree |
| Coordination | the agent CLI's own collaboration contract; supervisor synthesizes | usage/account consent envelope, receipts, `horus-execution` / `execution.md` |
| Consent needed | the owner's request to use one | the full model/account/usage envelope, approved before launch |

**Delegation authorization is bounded to the substrate the owner named.** "Use a
subagent for this" authorizes a child of this session — it is **not** permission
to launch another provider or spend another account's budget. Only an explicit
external-worker request ("run this through Horus on the <account> account")
opens the `horus run` path.

So: if the owner says "subagent", or asks whether "lower models" could do
something, and has **not** identified the substrate — **ask one clarification
question first**, before reading another account's usage or drafting a dispatch
envelope. Answering the wrong substrate is the observed failure (2026-07-29): a
question about Codex's own agent spawning was answered with a Haiku-on-another-
account `horus run` proposal, which was internally consistent and still not what
was asked.

## Invocation boundary

An ordinary request to build, fix, review, or plan work authorizes inline work; it
does not authorize delegation and does not trigger this skill. Do not load this
skill merely to populate `execution_recommendation`, at every planning boundary,
or to validate an obvious inline choice. Load it only after the owner explicitly
asks whether/how to delegate, requests a worker/subagent, or requests a delegated
execution plan.

## Load the shared rubric first

Read **`../delegation-rubric/SKILL.md`** and apply its dividend precondition plus
seven steps (read the data, read the task shape, the tier-trust ladder,
shape→mode+tier, verification depth, bind consent, emit). Everything about reading
`horus capabilities --models` and dialing
verification by tier-trust lives there — do not restate or fork it here.

## Mode vocabulary (this skill's output for the rubric's Step 4 axis)

- **`inline`** — do it in this session. The rubric's "stay inline" case: small,
  or ambiguous/exploratory, or debugging. On a single-model runtime (no cheaper
  worker tier reachable) inline is also right unless volume would flood the
  context window — delegation then buys only context hygiene.
- **`native-subagent`** — hand a bounded task to a child of this session, and
  synthesize its result here. The rubric's "delegate" case when what delegation
  buys is **context hygiene**: high-volume, low-ambiguity, fenceable scope, clear
  gate, but no reason to leave this account or runtime. Uses the agent CLI's own
  collaboration contract — **no `horus run`, no account switching, no
  `execution.md`, and no Horus usage routing**. Cost grounding still applies, via
  that native contract rather than a manufactured worker envelope.
- **`horus-worker`** — delegate to a tracked external agent-CLI session (one
  phase at a time) via `horus-execution` / `execution.md`. Choose this only when
  the dividend actually requires *leaving this session*: a cheaper implementation
  tier, another account's capacity, a separate worktree, or time-shifted
  unattended work. Name the tier from the data, set `delegation_basis` to what
  the move buys, and bind the model/account/usage consent envelope before launch.

Feed the recommendation into `execution_recommendation`: **both `inline` and
`native-subagent` map to `continue-as-is`** — a native child is still this
session, so it needs no execution plan — and only `horus-worker` maps to
`plan-execution`, which then carries the `execution.md` phase's `worker_tier` /
`delegation_basis`. Writing `plan-execution` for a native subagent would invite a
later session to stand up worker machinery nobody authorized.

## In-project verification note (the substrate specialization of rubric Step 5)

CI has NOT run yet inside the session — there is no merge SHA to observe. So the
supervisor **RUNS the gate at the phase boundary** (the handoff note's one gate
command + one live probe of the changed surface) and **TRUSTS the code** —
reviews the diff for scope/risk, not line-by-line as evidence it works. Dial by
tier-trust exactly as the rubric says: a proven worker → run the gate once and
observe; an unproven worker → run the gate AND add an independent probe, then
`horus datum close` the run so the tier earns a real datum. A runtime/visual
surface still defaults to the owner's eyeball.

## Emit (advisory — you apply it, nothing here auto-runs)

`mode` (`inline` | `native-subagent` | `horus-worker`) + `tier` (a vendor-neutral capability point —
`low|medium|high|frontier` — resolved to a concrete provider+model only at the
consent envelope, from the neutral-tier map + live capacity,
never defaulted from the label) + `verification depth`
(observe-only | observe+probe | owner-eyeball,
with the gate command named). Name the **substrate** explicitly in the emit, so
the owner can see which one they are approving.

For `horus-worker`, include the exact agent/model/
effort/account/usage+reset/task/attempts/dividend-or-owner-override/gate consent
envelope, mark it awaiting explicit owner approval, and ask again on any
fallback or extra attempt. For `native-subagent`, emit the bounded task, the gate
you will run on its result, and the context dividend — **not** an account/usage
envelope, because no other account is being spent. Spawning the child, selecting
the model, and running the gate are all YOUR actions — this skill recommends, it
does not route.

"""


_DISPATCH_DECISION_SKILL = """\
---
name: dispatch-decision
description: >-
  Decide HOW to dispatch a unit of work from the multi-project cockpit on the
  sessions substrate: recommend `inline-here` vs `dispatched-worker` vs
  `dispatched-plan`, which ACCOUNT to route it to (away from the overseer
  account, gated on `horus usage check`), a model tier, and a verification
  depth. Use this when triaging cross-project work from an overseer/cockpit
  session — picking whether to do it here, hand it to a tracked `horus run`
  worker, or stand up a phased plan. It reads live calibration data (`horus
  capabilities --models`) through the shared delegation rubric. Advisory: it
  EMITS a recommendation you apply — it never auto-selects a model, auto-routes
  an account, or auto-spawns a worker. For choosing how to execute inside a
  single repo use `execution-decision` instead.
---

<!-- horus-skill-version: 5 -->

# Dispatch decision (cockpit / multi-project, sessions substrate)

Substrate: an overseer/cockpit session triaging work across many registered
projects, dispatching tracked sessions via `horus run --account <alias> --path
<repo>`. Work lands back via PR + CI. This skill is the thin cross-project
consumer of the shared rubric — it adds the dispatch mode vocabulary, account
routing, and one substrate note.

## Load the shared rubric first

Read **`../delegation-rubric/SKILL.md`** and apply its dividend precondition plus
seven steps. All calibration, consent-envelope, and verification-depth logic
live there; do not restate or fork it.

## Mode vocabulary (this skill's output for the rubric's Step 4 axis)

- **`inline-here`** — do it in the overseer session. The rubric's "stay inline"
  case (small / ambiguous / exploratory / debugging), plus integrated campaigns
  where the current session already holds context that a handoff would discard.
  Overseer usage is a cost to weigh, not a presumption that dispatch is better.
- **`dispatched-worker`** — one tracked `horus run` worker for a bounded,
  fenceable, clear-gate task. The rubric's "delegate" case.
- **`dispatched-plan`** — a phased plan (orchestrator > supervisor > worker, one
  worktree per worker) for large multi-phase work whose independently fenceable
  phases have a named context or parallelism dividend that exceeds the supervisor
  tax. Cross-project scope alone is insufficient.

Do not dispatch merely to collect a datum. Calibration is a useful by-product of
real work, never the reason to create a worker.

## Account routing (cockpit-specific, on top of the rubric)

- **Route away from the overseer account.** A dispatched worker runs on an
  ISOLATED account (a `horus account` alias → its own `CLAUDE_CONFIG_DIR` /
  `CODEX_HOME`), never the ambient overseer login — that keeps the overseer free
  AND, on a tiered setup, buys the cheaper-tier × separate-account double win.
- **Gate the target account on `horus usage check`** (`--target claude|codex`
  for the worker's agent). If the chosen account is near a closure threshold,
  pick another isolated account or hold the dispatch — and heed the rubric's
  `guard` flags. This is a check you OBSERVE, not an auto-throttle. When native
  telemetry is incomplete or temporarily lifted, accept a current owner-provided
  reading as the routing signal and label that override explicitly.
- An owner may explicitly choose an account to spend capacity before its reset or
  protect the overseer context. This supplies the dispatch basis, but does not waive
  the exact-envelope approval or authorize a silent fallback.

## Overseer verification note (the substrate specialization of rubric Step 5)

Dispatched work lands via **PR + CI**, so the deterministic gate already exists
remotely: **OBSERVE the required CI check green on the merge SHA** — roughly one
`gh` call (`gh pr checks` / the run conclusion on the head SHA). Do NOT re-run
the suite locally; a required check green on the exact commit already reproduces
the test gate. Dial by tier-trust as the rubric says: a proven worker → observe
CI green and accept; an unproven worker → observe CI green AND drive one live
probe of the changed runtime surface (a mocked green never blesses a runtime
flag), then `horus datum close` the run. A runtime/visual surface still defaults
to the owner's eyeball.

## Emit (advisory — you apply it, nothing here auto-runs)

`mode` (`inline-here` | `dispatched-worker` | `dispatched-plan`) + `account`
(which isolated alias, or "hold — usage") +
`tier` (a vendor-neutral capability point — `low|medium|high|frontier` —
resolved to a concrete provider+model only in the consent envelope, from the
neutral-tier map + the target account's live capacity,
never defaulted from the label) + `verification depth` (observe-CI |
observe-CI+probe | owner-eyeball). Show the calibration + usage/reset evidence that
drove it. The account and the provider are the SAME decision here: a `medium` card
can run on Claude (Sonnet) or the equivalent Codex model — pick the one whose
isolated account has capacity, don't let the old vendor-named label choose. For
either dispatched mode, present the full consent envelope from the rubric and
stop for explicit owner approval. Any changed model/account/effort/scope or additional attempt requires a new
approval; provider errors never authorize fallback. Selecting the account, spawning
the worker, and observing CI are all YOUR actions — this skill recommends; `horus`
never auto-routes a dispatch (the hard boundary: `research/omnigent.md`).

"""


_FLEET_CURATION_SKILL = """\
---
name: fleet-curation
description: >-
  Review and clean a portfolio of Horus projects from a fleet-curator workspace.
  Use when the user asks what remains valuable across projects, wants stale or
  obsolete backlog archived, wants a project placed on hold, or explicitly opens
  Fleet Review in the TUI. Reads the remote-authoritative horus fleet --review
  digest first, keeps remote shipped truth separate from local work, and requires
  owner approval before changing target-project continuity.
---

<!-- horus-skill-version: 2 -->

# Fleet curation

This is an occasional portfolio-maintenance workflow, not an overseer required for
ordinary delivery. Direct project sessions remain the default.

## Review

1. Fetch the curator workspace, verify its branch against origin, and run
   `horus fleet --review`. Treat REMOTE SHIPPED TRUTH as canonical. Treat LOCAL
   WORKING STATE as a separate warning/provenance layer; never silently combine it
   with remote continuity or pull a target worktree.
2. Use the shared manifest only for project identity and lifecycle. Project code,
   PRD, backlog, capability ledger, and closure stay in the target repository.
3. Read a target PRD/card only after selecting that project. Judge value from the
   owner's current workflow and already-shipped capability; do not manufacture a
   score, ranking, model choice, or automatic archive plan.
4. Present a concise recommendation with explicit buckets: continue now, defer
   until a named trigger, retire because shipped/obsolete/no consumer, or keep as
   optional history. Ask the owner before applying target-project changes.

## Apply an approved cleanup

1. Enter each approved target repository separately. Fetch all remotes, verify the
   current branch against origin/default, read its PRD, and honor its instructions
   and CLI version floor.
2. Continuity-only cleanup may archive complete cards with rationale and update the
   PRD/status. Preserve card content and provenance. Never delete history merely to
   make a queue small.
3. Any source implementation leaves curator mode: use the target project's normal
   execution decision, feature branch, deterministic gate, PR, and continuity close.
4. Keep each repository at a green committed-and-pushed checkpoint. Do not make a
   cross-repo mega-commit, auto-dispatch work, or change external infrastructure
   without separate owner authority.

## Close

Record only durable fleet-level decisions in the curator workspace. Do not copy
project facts into it. Refresh its PRD and add a local recovery note only if needed,
then push the checkpoint; the
next review should be reproducible from the manifest plus target remotes.
"""


_BACKLOG_LIBRARIAN_SKILL = """\
---
name: backlog-librarian
description: >-
  Produce one autonomous, zero-blast-radius hygiene digest for a card-backed
  Horus backlog. Use when the owner asks to inspect, clean up, or maintain a
  growing backlog; asks for duplicates, stale cards, broken cross-links,
  satisfied dependencies, or contradictory readiness/status; says "run the
  backlog librarian"; or schedules an unattended backlog-hygiene review. Reads
  every active card, proposes exact owner-reviewable actions in a dated receipt,
  and never edits, archives, claims, reprioritizes, or ships cards.
---

<!-- horus-skill-version: 3 -->

# Backlog librarian — one advisory hygiene digest

Maintain the existing set; do not create product direction. This is the curate
half of autonomous PO hygiene: a bounded review artifact, never autonomous
backlog mutation.

## Hard boundary

- Write exactly one receipt under
  `.horus/audits/<YYYY-MM-DD>-backlog-librarian.md`. If that path exists, use
  `-2`, `-3`, and so on; never overwrite a prior run.
- Print the complete receipt in the response too. A scheduled run therefore
  leaves both a tracked artifact and the normal run log.
- Never edit `PRD.md` or a card; never archive, claim, reprioritize, schedule,
  notify, commit, push, open/merge a PR, or implement a proposal. The caller or
  existing dispatch substrate owns delivery of the receipt.
- No web research, embeddings service, subagents, or extra model call. One
  bounded analysis pass over repository evidence only.

## Fixed defaults

- **Stale:** no evidenced touch for 8 weeks (56 days).
- **Suggested cadence:** one owner-authorized run every 4 weeks. This skill
  never arms its own schedule or recurring timer.
- **Touch date:** newest valid date among the card's `last_refined`, its latest
  git commit, and `created` (fallback). Do not treat a PRD mention or this
  librarian's own receipt as a card touch.
- **Semantic budget:** read every active card once, but semantically compare at
  most 25 candidate pairs after the cheap prefilter below. Report truncation and
  the selection rule if more than 25 pairs qualify.

An owner may explicitly override threshold or pair cap for one run; record the
override in Run facts. Do not invent persistent configuration.

## Evidence pass

1. Honor the repository instructions: fetch and verify the working branch
   against its remote before trusting local state. Read `PRD.md`, then run the
   read-only `horus consolidate` and `horus backlog --tree --json` signals.
2. Inventory every active `.horus/backlog/*.md` card. Read its complete
   frontmatter and body exactly once. Inventory archived card names plus
   lifecycle/provenance fields only; read an archived body only when an active
   card explicitly links to it and the relationship needs disambiguation.
3. Resolve each `depends-on` value against both active and archived
   names. Split comma-separated dependency values; preserve the spelling shown
   in the source.
4. Determine last touch with targeted `git log -1 --format=%cs --
   <card-path>` calls plus the two card dates. A shallow clone or missing git
   history is unknown, not stale.
5. Build overlap candidates cheaply. Include exact normalized titles, and
   near-title pairs that share a `topic` plus at least two
   meaningful title terms. Add pairs where one card explicitly names the other.
   Rank exact titles, explicit mentions, then same topic; keep the
   first 25. Only now compare their full intent, outcome, boundaries, and source.

## Findings — evidence, never guesses

Classify only findings supported by a quoted field or a short body paraphrase:

- **Duplicate / overlap:** exact duplicate, one card subsumes the other, or two
  cards collide materially. Similar vocabulary alone is not a finding.
- **Stale:** the 56-day rule passed. Suggest review/defer/retire, never infer
  obsolescence from age.
- **Links:** dangling `depends-on`/`branch`; an explicit blocker or umbrella
  relationship described in prose but absent from structured fields; or a
  cross-link that names no existing active/archive card. Do not demand
  reciprocal links.
- **Satisfied dependency:** `depends-on` resolves to an archived shipped card
  (or other unambiguous shipped provenance), while the active card still
  presents it as a gate. Propose removing the dependency and re-evaluating
  readiness; do not claim the dependent card is ready.
- **State contradiction:** include deterministic readiness findings, terminal
  lifecycle states lingering in the active directory, Ready cards that still
  describe an unresolved gate, non-Ready cards without an actionable reason,
  and gated/deferred reasons contradicted by resolved repository evidence.

Use confidence `high|medium|low`. Omit low-confidence semantic suspicions from
the action list; place them in `Needs owner interpretation`. If two cards are
distinct, say why and do not report them as hygiene debt.

## Receipt

Write these sections in order:

1. `# Backlog librarian — <YYYY-MM-DD>`
2. `## Summary` — active/archive counts, finding counts by category, and one
   sentence naming the highest-value review.
3. `## Proposed actions` — table: ID | category | card(s) | evidence | exact
   proposed card diff/action | confidence. Concrete diffs are proposals only.
4. `## Needs owner interpretation` — bounded ambiguous cases, or `None`.
5. `## Clean checks` — explicitly name categories with no findings so silence is
   distinguishable from a skipped check.
6. `## Run facts` — threshold, effective date, branch/SHA, card counts, pair
   count/cap/truncation, commands/signals used, and evidence limitations.
7. `## Boundary` — “Advisory only; no cards or continuity were changed.”

Keep one row per underlying issue; cross-reference a row instead of duplicating
it across categories. Sort actionable rows: state contradiction, satisfied
dependency, broken link, duplicate/overlap, stale. If there are no actions,
still emit the receipt with a clean summary.

## Scheduling posture

A scheduled invocation is an ordinary unattended `horus run` whose prompt says
to use `backlog-librarian`; it remains subject to the existing exact account /
model / effort / envelope approval and usage gates. The receipt is the only
authorized work product. Do not add a daemon, recurrence engine, or librarian-
specific scheduler. Four weeks is guidance for the owner when arming a one-shot
run, not authority for this skill to arm the next one.

"""


_PROCESS_RETROSPECTIVE_SKILL = """\
---
name: process-retrospective
description: >-
  Bounded, evidence-first retrospective on how one campaign/episode was
  executed or supervised — not what Horus should build. Use only on an
  explicit owner request ("what should we do differently", "why did that take
  so long") or a concrete incident: failure, near-miss, unexpectedly long run,
  surprising usage/cost movement, or inefficient supervision. Never fires at
  every closure. Lazy-loads only that incident's evidence (execution plan,
  exact PR/CI state, datum/receipt, targeted log fragments, owner
  observations), attributes cost across inherent/delegation-tax/supervisor-
  error/worker-error/Horus-defect/external-failure, checks existing PRD Rules
  and backlog cards first, then recommends the cheapest control rung
  (no-change, guidance clarification, deterministic signal, hard guard),
  capped at three. Advisory only — never estimates tokens, launches another
  model, rereads the repo, or writes continuity itself; accepted outcomes
  land in existing Rules/card Reviews/backlog, never a new document or
  telemetry stream.
---

<!-- horus-skill-version: 3 -->

# Process retrospective — bounded, evidence-first

You are examining how one campaign or episode went, not auditing the whole Horus
product and not closing
continuity (that's `horus-consolidate`). This skill never runs on its own —
only on an explicit owner ask or a concrete incident.

## When this fires

- The owner explicitly asks what should improve, why something took long, or
  what happened in a specific episode.
- A concrete incident: a failure, a near-miss, an unexpectedly long run, a
  surprising usage/cost movement, or supervision that felt inefficient.
- **Never** at every closure, and never as a standing habit — that is exactly
  the generic self-reflection ceremony this skill exists to avoid.

## Scope the incident before reading anything

Name the bounded campaign/episode under review and the specific question
being asked. Do not widen this into a review of the whole project.

## Lazy-load only the relevant evidence

Pull only what this one incident needs:

- The relevant `.horus/execution.md` phase, if the work was delegated.
- Exact PR/CI state for the affected commit (`gh pr checks`, merge-watch
  history).
- The datum/receipt for the run(s) in question (`horus datum report`).
- Targeted log fragments (the failing command's actual output, the relevant
  tmux pane) — not a full log tail or a repo-wide re-read.
- The owner's own observations already in this conversation.

Do not broadly reread the repository or open unrelated files "for context."

## Attribute cost honestly — six buckets

Classify what happened. Label anything you cannot pin down as
unknown/confounded rather than guessing:

1. **Inherent task cost** — the work was always this big or this hard.
2. **Delegation tax** — brief/review/gate/merge/close overhead paid regardless
   of who executed.
3. **Supervisor error** — a wrong call by the supervising agent/session.
4. **Worker error** — the delegated agent/session got it wrong.
5. **Horus/skill defect** — a bug or gap in `horus` itself or a bundled skill.
6. **External failure** — provider outage, rate limit, infra flake.

Never estimate token consumption or launch another model call to
investigate; reason only from the evidence already gathered.

## Check existing coverage before proposing anything

Before recommending anything new, check whether `.horus/PRD.md` Rules, open
backlog cards, or an existing skill's stated boundary already cover this
finding. If it's already covered, say so and stop there — don't recreate a
rule that exists.

## Recommend the cheapest rung, capped at three

For each surviving finding, propose the cheapest control that would have
caught or prevented it, cheapest first:

1. **No-change** — inherent cost or a one-off external failure; no rung is
   warranted.
2. **Guidance clarification** — a prose fix (CLAUDE.md/AGENTS.md, a skill's
   own boundary section).
3. **Deterministic signal** — an observable check (a warning, a CLI signal, a
   gate someone watches).
4. **Hard guard** — code that blocks the dangerous class of mistake outright.

Never jump straight to a hard guard without stating why the cheaper rungs are
insufficient — start with instructions and promote only after an observed
field failure. Cap the whole retrospective at **three recommendations**,
ranked by leverage; more than three is a sign the incident needs splitting or
the analysis is padding out generic reasoning.

## Land the outcome — no new artifacts

- Every recommendation is advisory: present it and stop. A process change
  needs explicit owner approval before anything is touched.
- On approval, land the accepted outcome in an **existing** surface: a
  `## Rules` line in `PRD.md`, a backlog card, or a card Review — never a new
  retrospective document, log, or telemetry stream.
- Do not write continuity or backlog entries as part of running this skill;
  recording durable state is `horus-consolidate`'s job at the next boundary.
  This skill proposes; the owner or the next consolidation pass records.

## Stay inline

Default to inline, single-agent analysis. A worker, another model call, or an
independent forward-test to run or validate this retrospective needs its own
separately named and approved envelope — running a retrospective is not by
itself grounds for delegating.

## Review this skill itself

After roughly three real uses, check whether it produced findings that were
actually new — not a restatement of generic reasoning — and cheaper than the
overhead of running it. If not, recommend demoting or retiring it to the owner.

"""


_SKILL_AUDIT_SKILL = """\
---
name: skill-audit
description: >-
  On-demand, evidence-first audit of ONE skill's text against reality: does
  every command/flag/path it references still match the live surface, where
  did real runs have to improvise around vague or missing instructions, and
  which of its internal steps became ceremony. Owner-invoked only ("audit the
  X skill", "test this skill", "improve this skill from that run") — there is
  deliberately no staleness advisory. Verdicts are revise (with the exact
  replacement text, owner-approved) / demote / defer / retire / no-change;
  the outcome lands in a dated `.horus/audits/` receipt. Never auto-edits a
  skill. A whole-product review is out of scope; for one campaign's execution
  use `process-retrospective`.
---

<!-- horus-skill-version: 6 -->

# Skill audit — one skill's text vs reality

**Scope: Horus's own bundled skills, in the horus-harness repo.** This audits
skills whose source is `horus/skills.py`, so it is not installed into managed
projects — a consumer project has the projected `SKILL.md` copies but not the
generator that writes them, and a verdict there would have nowhere to land.
Auditing a target project's *own* skills is not supported yet.

You are auditing the *text* of one skill against how the world and its real
runs actually behaved. This is distinct from `process-retrospective` (one
campaign incident). This skill's whole purpose is amendment: proposing better
text for one named skill.

## When this fires

- The owner asks to audit, test, or improve a specific skill.
- A real run just exposed the skill's instructions failing: the agent had to
  improvise, a referenced surface didn't exist, a step was ambiguous.
- **Never** on a schedule. There is no deterministic trigger by design;
  propose one only after un-audited skill drift causes an observed field
  failure (the control ladder, applied to itself).

## Scope: one skill per audit

Name the skill under audit before reading anything. Do not widen into a
sweep of the whole bundled set — that is a series of audits, each bounded.

## Questions (evidence, not recall)

**Start with the invocation count.** `horus skill usage [--since YYYY-MM-DD]` reports
how often every bundled skill was actually invoked, zeroes included. A zero is a
finding, not a gap in the data — but read it honestly: it means *this owner, on this
machine, since the recorder was installed*, so a recently-installed recorder proves
nothing yet. It is evidence to weigh, never a verdict on its own.

1. **Fidelity.** Check every claim the skill's text makes against the live
   surface: commands and flags against `horus --help` / `horus <cmd> --help`,
   file paths and structure against the actual repo, named integration points
   against the code. Every mismatch is a finding — skills are instruction-ware
   and drift silently as the product moves.
2. **Executability.** Run the skill for real on a genuine trigger, or replay
   its most recent real run from the receipt/conversation. Log every place
   the executing agent improvised, interpreted ambiguity, fell back, or
   skipped ahead. Each improvisation is a missing or vague sentence in the
   skill — the gap is in the text, not the agent.
3. **Internal ceremony.** Which of the skill's own steps were skipped or
   rubber-stamped across recent invocations? A step every run bypasses is
   evidence against the step.

## Verdicts — five, because amendment is the point

Per finding: **revise** (propose the exact replacement text as a diff — the
owner approves before anything is edited), **demote** (weaker rung),
**defer** (revisit with the reason), **retire** (propose removal — the owner
acts), or **no-change**.

Applying an approved revise to a bundled skill means editing its constant in
`horus/skills.py` and bumping that skill's version marker, landed by PR like
any product change. Never edit the projected `SKILL.md` copies directly —
they are regenerated and the edit would be silently overwritten.

## Close the audit

- Write the receipt: `.horus/audits/<YYYY-MM-DD>-skill-<name>.md` — one page,
  never a transcript: verdict table (finding | verdict | one-line evidence),
  defers with reasons, and for each revise a pointer to the applied version
  bump (or its pending state).
- This skill audits itself under exactly the same rules — when its own
  instructions needed improvising around, that is a finding here.

## Two invariants an audit must check first

- **A skill's DESCRIPTION is where an invocation boundary lives.** The body is read
  only after the load decision is already made, so a correct boundary section in the
  body cannot stop a false trigger. Corollary for tests over skill prose: assert on
  **whitespace-normalized** content, since hard-wrapping breaks a raw-substring
  assertion on reflow rather than on meaning.
- **Any edit bumps the skill version, always.** The version-aware install skips
  same-version content, so an unbumped text change leaves committed projections
  silently stale. `Skill(name, N, text)` and the `horus-skill-version: N` marker
  inside that text are two copies of one number; when they disagree every
  `upgrade-project` reports "updated" forever while doctor never goes green. Resync
  with `horus skill install --force` (from working-tree source); never hand-edit a
  projected `SKILL.md`.

## Boundaries

- Advisory only: nothing is edited, demoted, or retired without the owner's
  approval of the specific diff or proposal.
- One skill per invocation; no telemetry; no new trigger machinery.

"""


_BACKLOG_REFINE_SKILL = """\
---
name: backlog-refine
description: >-
  Refine and disposition an existing backlog with the owner when cards need
  readiness review, concrete execution contracts, ordering, or an honest current
  picture. Use when the owner says "refine the backlog", "groom these cards",
  "what is actually ready", or "order the backlog". Manual and owner-gated;
  never runs autonomously and
  never silently rewrites cards.
---

<!-- horus-skill-version: 9 -->

# backlog-refine — picture first, decisions second, Ready last

This skill owns the **single execution-ready card contract**. It turns existing
cards into honest Ready, Shaping,
Gated, or Deferred state. Two launch surfaces exist (`horus backlog refine` prints
the prompt; `o` on the TUI's backlog pane opens an attended session), and both
hand straight over to this skill: the LLM judgment and owner decisions live here.

## Hard boundary

- Manual only. Never invoke from an autonomous worker or scheduler.
- Advisory first. Present every decision-bearing change and obtain the owner's
  verdict before writing it.
- Read card bodies, Reviews, PRD Vision/Shipped/Rules, and relevant receipts. A
  frontmatter lint is not refinement.
- Use LLM judgment first and deterministic checks second. A missing field may be
  by design; a clean schema does not make a weak card valuable.

## 0. Reconcile against live delivery state before the picture

The cards alone cannot say what is still open work. Other sessions open bug PRs and
leave branches unmerged, so a card whose fix is already sitting on an open PR reads
as untouched — and `gh pr list` shows only OPEN PRs while nothing at all inspects
branches. Before the picture:

1. `git fetch --all --prune`, then read **open PRs** and **unmerged remote
   branches** (`horus close --check` names the branches; a launch through `horus
   backlog refine` / the TUI already embeds both in the prompt).
2. Name every card that an open PR, an unmerged branch, or already-merged work
   answers — in full or in part. A card covered by a merged delivery is a `ship`/
   archive candidate, not a refinement decision; a card sitting on an open PR is
   in flight and must not be re-scoped or re-minted as Ready underneath it.
3. If continuity is stale, consolidate first so the picture rests on current state
   rather than on the previous session's prose.

Report what you found before step 1's picture, so the owner sees the same ground
truth the classification rests on.

## 1. Present the backlog picture before any questions

Start with the literal heading **“Here is our current picture”** and include:

1. the product direction in 2–3 lines;
2. every topic with its open/shipped counts and a short description grounded in
   its cards;
3. item counts for each topic split by readiness and priority;
4. the proposed work queues: Ready—Autonomous eligible, Ready—Attended,
   Shaping, Gated, Deferred, and Unclassified.

Do not ask card questions before this picture. Read the content of every open card,
including umbrellas and exploratory children, before classifying the portfolio.

## 2. The pass — a per-card questionnaire, one card per screen

After the picture, go through the backlog card by card as a serial
questionnaire (owner-designed in the first live run, PR #355; two later runs
drifted from it, so the screen is specified literally below). Each stop is
ONE card rendered as one screen — this exact markdown shape, self-contained
in this skill (no external mockup exists):

    **<N>/<M> — <card-name>**

    ```
     Problem

       <the problem background the card is trying to solve, 1-2 lines>

     Solution

       <the card's proposed solution, 1 line>

     Verdict

       <the analysis verdict + one-phrase reason>
    ```

    1. <verdict as an actionable choice> (Recommended) — <exact consequence>
    2. <alternative> — <exact consequence>
    3. <alternative> — <exact consequence>
    4. Type anything

The card digest has ONE outer frame (the fenced block) and nothing else — no
inner table, no borders between sections; the three labelled sections are
separated by blank lines only (owner-confirmed render, 2026-07-20). With the
native structured picker available, the message carries the header + framed
digest and the picker carries options 1–3 — put the same spaced sections in
each option's preview (the preview box itself is the outer frame there, so no
fence inside) and SIZE the preview to fit its box: roughly a dozen short
lines; trim digest wording rather than letting the UI truncate. The picker's
own free-text Other replaces line 4. Option 1 is always the verdict turned
into an actionable choice, marked **(Recommended)**; 2–3 are the real
alternatives; every option states its exact durable consequence — fields/body
changed, dependency or trigger recorded, queue entered, what later unblocks
it.

Verdict vocabulary: keep as-is · keep, note <observation> · mint Ready
(eligible|attended) · move to <queue> (gate met / trigger satisfied) ·
retire candidate · defer with trigger <named> · decision — <what the owner
must choose>.

Strictly one card per exchange — one at a time, never batched: never several
cards in one picker call (the twice-corrected failure mode). Cards whose
verdict is a clean "keep as-is" may be grouped into a short skip-summary
between stops so the questionnaire only halts on cards with something to
decide — and the owner can pull any skipped card back into the questionnaire
by name.

Batch only truly mechanical fixes with unambiguous values (vocabulary
renames, `last_refined` stamps, pointer notes) into ONE clearly-labelled
approval at the end — never demotes, defers, retires, rescopes, acceptance
rewrites, or mints.

## 3. Readiness and autonomy contract

**`shelved` is a status, and a bug can never take it.** `shelved` means the owner
declined to DECIDE — distinct from `retired` (decided dead) and from `deferred`
(queued, which failed: 26 cards screened twice, none moved). A bug is a problem that
already arrived, so boxing one hides a known defect where no view surfaces it; the
close gate `fail`s on that combination. A bug judged unreal is `retire`d with a
reason. Read shelved cards with `horus backlog list --shelved`, never a directory
listing.


`status` remains lifecycle state. Readiness is orthogonal:

```yaml
readiness: ready | shaping | gated | deferred
readiness_reason: "required for shaping, gated, and deferred"
autonomy: eligible | attended  # required only when readiness: ready
```

- **Ready** — decision-complete now; a fresh agent can implement and independently
  verify it from PRD + card. `eligible` means it may be scheduled when an approved
  envelope authorizes it, never that it must be. `attended` means owner presence is
  required during execution or verification.
- **Shaping** — active owner/LLM work remains: brainstorm, research, scoping,
  refinement, review, or an exploratory evidence pass. The reason names that next
  action and expected disposition.
- **Gated** — a named dependency, event, or evidence source must arrive first. The
  reason names it; use `depends-on` as well when the gate is another card.
- **Deferred** — deliberately inactive until an explicit trigger or owner review.
- Missing `readiness` is **Unclassified** for compatibility. Never infer Ready and
  never schedule it; route it through this skill. Do not auto-rewrite a repository.

`topic` and `priority` remain orthogonal. Priority means importance when active.
A decision-complete evidence probe may be Ready.

## The execution-ready card contract (single authority)

A Ready card carries `status`, `priority`, `tier` (`low | medium | high |
frontier`), optional `topic`, `created`, `created_by`, `surface`,
`parallel: safe | exclusive`, `readiness: ready`, and
`autonomy`. It also carries:

- **Why** — durable context and market/own-use position;
- **How** — concrete protocol or first implementation steps;
- **Acceptance** — deterministic gate on the exact SHA plus a named live probe and
  expected result; an evidence probe also names its explicit adopt/drop verdict;
- **Non-goals** — bounded exclusions;
- **Source** — receipt, topic, owner decision, or observed gap;
- `depends-on` and sparse `order` when sequencing is decision-bearing.

Second-order findings are never fabricated. Scope the evidence-gathering probe and
state how later findings will be carded.

**`surface` is a HINT, never a boundary.** It is hand-written and unverified, so it
is routinely incomplete — an agent that treats it as the edge of the work will
faithfully leave the rest undone. Observed twice on 2026-07-26: `codex-identity-guard`
named `launch.py` and shipped as a HALF-FIX because `pty_host.py` held a second copy
of the same guard, and `project-registration-onboarding-gap` omitted the two files
carrying the guidance text it required. In both cases the worker did exactly as
briefed and CI was green.

So: write `surface` as the best-known starting point, and require the implementer to
**report any file it touched beyond that list, and why**. That reporting line is the
cheap control that works — the `project-registration` worker was briefed with it and
duly surfaced four files the card never named. Do not promote this to a gate: a
hand-written list cannot be mechanically verified as complete, and a check that
demanded it would only teach people to pad the field.

## 4. Apply approved state

Write only approved diffs. Record consequential owner demote/defer/retire/rescope
verdicts under `## Reviews`. Set `last_refined: YYYY-MM-DD` only after the card body
was actually reviewed, including an approved no-change verdict. Remove obsolete
fields rather than carrying rival readiness models.

When ordering is requested, respect `depends-on`, topic grouping, priority, and
`surface`/`parallel` collisions. Propose sparse integer `order` values with gaps of
10; explain whenever a constraint forced a position. Unordered cards stay in the
unsequenced pool. Ordering is owner-approved planning, never auto-routing.

`order` is consumed deterministically, with no LLM in the loop: `horus backlog list`,
`--tree`, and the TUI all sort on `(queue, order missing?, order, priority-rank,
name)`. So it sequences cards **within one readiness queue** — a repeated number
across two different queues is fine, two cards claiming the same number inside one
queue is a warned-about ambiguity. Only an integer counts; `order: soon` leaves the
card unsequenced. Write the value only where sequencing is decision-bearing: a
stamp on every card is noise that the next insert has to renumber around.

End with the updated picture and the exact remaining pending decisions. Do not
dispatch, schedule, or implement; when the product direction itself is unresolved,
stop and return that decision to the owner.

"""


_COCKPIT_DISPATCH_SKILL = """\
---
name: cockpit-autonomous-dispatch-contract
description: >-
  Owner-invoked cockpit WORKFLOW that sequences the full autonomous-dispatch loop
  from a portfolio cockpit session (horus-agent): discover fleet backlog → pick a
  card → ready-gate its scope → decide mode/account/model/verification →
  dispatch now or schedule it (attachable + worktree, right account) → schedule a
  `horus supervise` to verify/merge/close or escalate. Use when the owner opens a
  cockpit and says "check the backlog, pick something, launch it (scheduled if
  asked) and have a supervisor close it out or ping me", or says
  "autonomous dispatch", "run the away-mode loop", "schedule and supervise a card".
  A THIN sequencer over existing machinery — it composes `dispatch-decision`
  (mode/account/tier/depth), `backlog-refine` (ready-gate), and the `horus
  envelope`/`schedule`/`run`/`supervise`/`notify`
  commands; it never re-implements them. Advisory and owner-gated at EVERY step:
  it proposes, the owner confirms each gate. It never selects a model, routes an
  account, or launches anything without the explicit consent envelope. Not
  continuous monitoring; single-machine, non-recurring dispatch only.
---

<!-- horus-skill-version: 6 -->

# Cockpit autonomous-dispatch contract

The pieces of the owner's loop exist as separate commands and skills; this ties them
into ONE contract a cockpit session follows to run scheduled, cross-account dispatch
with independent supervision. It is a **sequencer**, not new capability: every step
is an existing command or skill, and every step is **owner-gated** — the skill
*proposes*, the owner *confirms*. It never auto-ranks, auto-routes an account,
selects a model, or launches without the explicit consent envelope. Substrate rule:
harness owns capability, this skill lives in horus-harness, and horus-agent (which
never grows code) references it as its autonomous-dispatch entry point.

Run it from a **cockpit** session (horus-agent), fetch-first. The away-mode kit it
drives: `horus envelope`, `horus schedule`, `horus run --unattended`,
`horus supervise`, `horus notify`.

## The contract — seven gates, each owner-confirmed

### 1. Discover
Enumerate active work across the fleet, remote-authoritative:
`horus fleet --backlog --stdout` (or `horus resume --preflight --fleet`). Note any
**parallel-delivery** signal it surfaces (open sibling PRs, live co-sessions,
unconsolidated merges) — a card already in flight is not a candidate.

### 2. Pick
The owner selects, or the skill *proposes* a ranking by `priority` then age. Never
auto-pick.

### 3. Ready-gate (is the card dispatch-ready?)
Judge the card against **the execution-ready card contract in `backlog-refine`** —
that section is the single authority; do not maintain a rival checklist here. A
candidate must be `readiness: ready` and `autonomy: eligible`; missing readiness is
Unclassified and never scheduler-eligible. `autonomy: attended`, Shaping, Gated,
Deferred cards are not unattended candidates. If the
direction holds but the card is thin or Unclassified, STOP and route it through
`backlog-refine`. If the direction itself is unclear, stop and return that decision
to the owner. A fresh unattended
worker gets only the card, so the final contract must already be durable.

### 4. Decide
Invoke **`dispatch-decision`** for the recommendation: `inline-here` vs
`dispatched-worker` vs `dispatched-plan`, an isolated **account** routed AWAY from the
overseer (gated on `horus usage check --account <alias>` — never the account running
this cockpit), a tier→**model**, a verification depth, and the consent-envelope shape.
State plainly whether the card is *well-scoped-for-an-agent* or *needs-owner-supervision*.
This skill emits the recommendation; it never selects the model or account itself.

### 5. Authorize the standing envelope (the hard gate)
Nothing unattended runs without a bounded, expiring envelope. Create it explicitly:

```
horus envelope create <name> --expires <date> \\
  --card <card> [--branch <vision-branch>] \\
  --account <alias> --tier <tier> --effort <effort> \\
  --usage-floor <pct> --max-attempts <n> --max-dispatches-per-day <n> \\
  [--allow-merge]        # OMIT for verify+escalate-only (the safe default)
```

`--allow-merge` is the ONLY thing that lets a later `horus supervise` merge unattended;
omit it and the loop verifies + escalates but never merges. The envelope BOUNDS only —
it never selects the card, account, or model. Show the owner the exact envelope
(agent + model + account + effort + bounded task + usage evidence + acceptance gate +
dividend) and get approval before creating it. `horus envelope revoke <name>` grounds
pending work instantly.

**Why the default is verify+escalate, and what a brief must name.** The away-mode
drill ran two legs and answered its own readiness question: every required check
passed on both while both overwrote PRD continuity, in a surface no card named.
`--allow-merge` was correctly withheld. A worker records delivery facts — the SHA,
the PR, what the gate emitted — never a verdict on its own work; the supervisor
owns canonical continuity. That failure mode is addressable by instruction: the same
model and effort left `.horus/` untouched across a ten-step release once the brief
named it a hard constraint. **So name the off-limits surfaces explicitly in every
brief.** An unstated expectation is not a worker defect — but one clean run shows a
model can follow a runbook once, not that unattended release is safe.

### 6. Dispatch or schedule
Launch now, or schedule a one-shot on THIS machine (never cloud, never recurring):

```
# now:
horus run --unattended --envelope <name> --card <card> --account <alias> \\
  --worktree auto/<card> --expect-delivery
# or later (away-mode):
horus schedule run --at '<+2h | 2026-07-22 09:00>' -- \\
  'run <card>' --unattended --envelope <name> --card <card> --account <alias> --expect-delivery
```

`--unattended` already implies the attachable + `auto/<card>` worktree posture. Away-mode
needs linger (`loginctl enable-linger $USER`) so timers fire logged-out.

### 7. Pair a supervisor
Schedule a `horus supervise` after the worker's expected finish — the independent
accept/escalate gate (required CI on the exact SHA + freshness + the live probe):

```
horus schedule run --at '<after the worker>' -- \\
  supervise --path <repo> '<session-or-pr>' --probe '<owner-authored live probe>'
```

`--probe` is REQUIRED for an authorized merge (owner-authored, machine-local — never a
committed command); without it supervise refuses to merge and escalates. On a red gate
it escalates through `horus notify` and halts scheduled dispatches that `depend-on` the
failed card. Verify the sink first: `horus notify show` / `horus notify test`.

## The loop back to the cockpit
A scheduled supervisor closes the loop without a human: on accept it merges + closes +
ships the card (so it drops out of step-1 discovery); on a problem it escalates via
`horus notify` and the next cockpit session sees the sibling via `horus resume` +
the parallel-delivery signal. Owner reads escalations on their phone; TUI + horus-agent
stay the work surface.

## Boundaries
- **Proposes, never performs.** Every gate above is presented for owner confirmation;
  the skill writes nothing and launches nothing on its own.
- **Never selects a model or routes an account** — that is `dispatch-decision`'s data
  and the owner's call; this skill only sequences.
- **Single machine, non-recurring.** Cloud dispatch and recurring timers are out of
  scope (the vision keeps the distributed execution plane out of scope).
- **Merge is opt-in** (`--allow-merge` on the envelope) and always gated behind a live
  probe; the default posture is verify + escalate only.

"""


_PUBLISH_OPENWIKI_SITE_SKILL = """\
---
name: publish-openwiki-site
description: >-
  Owner-invoked workflow for publishing, updating, checking, rolling back, or
  removing a project's generated OpenWiki visualizer on a durable hostname.
  Use when the owner says "publish this OpenWiki", "put the wiki on my site",
  "deploy the generated wiki", "update the published wiki", or wants to repeat
  the same OpenWiki deployment across several projects. Reuses an existing
  Cloudflare Tunnel + Access pattern when present, keeps the OpenWiki origin on
  loopback, creates an isolated deploy checkout and systemd service, and proves
  both the local graph API and authenticated public surface. Not for generating
  the OpenWiki content or for deploying a general web application.
---

<!-- horus-skill-version: 1 -->

# Publish an OpenWiki visualizer without rebuilding the deployment each time

This is a publication workflow, separate from OpenWiki generation. The generated
`openwiki/` directory is the content; OpenWiki's visualizer is the runtime. It serves
root-relative `/api/graph` and `/events`, so use one hostname and one loopback port per
project. Do not subpath-multiplex several wikis or build a static exporter unless the
owner explicitly chooses that different product.

## Contract

- **Private by default.** A generated repository wiki can expose architecture,
  operational details, and backlog context. Put a Cloudflare Access application in
  front of it unless the owner explicitly chooses public access.
- **Access before exposure.** Create and verify the Access application/policy before
  adding DNS or tunnel ingress. If the host already has an unprotected route, report
  it and stop before widening or relying on it.
- **Loopback stays loopback.** OpenWiki intentionally binds `127.0.0.1`. Never patch
  it to `0.0.0.0`; Cloudflare Tunnel maps the public hostname to the loopback origin.
- **One isolated deploy checkout.** Never serve a development worktree. Publish an
  exact pushed commit from a separate deploy checkout and update it fast-forward-only.
- **Secrets stay machine-local.** Never commit Cloudflare tokens, tunnel credentials,
  Access secrets, OpenWiki provider credentials, or authenticated curl cookies.
- **External mutations stay owner-scoped.** An explicit request to publish authorizes
  the named project/hostname. If hostname, audience, host, or source ref cannot be
  derived safely, pin that choice with the owner before changing Cloudflare, DNS, or
  systemd. An assessment-only request stops at a proposal.

## 1. Pin the publication record

Fetch first, then print one compact record and resolve every field before mutation:

```text
project slug:       <stable filesystem/systemd-safe slug>
source repository: <URL or absolute canonical checkout>
source ref/SHA:    <default branch or explicitly chosen branch; exact pushed SHA>
wiki directory:    <absolute deploy-checkout>/openwiki
deploy checkout:   <absolute path outside the development checkout>
hostname:          <one hostname dedicated to this wiki>
origin:            http://127.0.0.1:<fixed unused port>
service:           openwiki-<slug>.service
service user:      <non-root owner of the deploy checkout>
Access app/policy: <existing reusable policy or named new app>
tunnel/config:     <existing tunnel id and configuration authority>
OpenWiki binary:   <absolute path and pinned version>
```

Prefer the host's established layout and deployment convention. Read the target
project's deploy docs and the live tunnel configuration before proposing new paths.
On the owner's usual Horus host, sibling deployments such as Keiko and Tabi are
evidence for the pattern, not files to copy blindly.

## 2. Preflight the content and host

1. Run `git fetch --all --prune`. Require a clean source tree and a pushed source SHA.
2. Require `openwiki/`, `openwiki/index.md`, and `openwiki/.last-update.json`. Parse the
   latter and refuse publication unless `status` is `complete`.
3. Validate the wiki's frontmatter and relative links, and run `git diff --check`.
   Scan the publish set for credentials. Do not treat generated prose as a secret-scan
   exemption.
4. Resolve the OpenWiki version from the repository's pinned workflow/package config
   when available; otherwise use the installed version and record it. Bake the
   absolute executable path into systemd: the manager does not inherit an interactive
   shell's package-manager PATH.
5. Confirm the chosen port is unused in the foreground. OpenWiki tries later ports on
   collision, so `--port N` is not proof that it bound N. Publication requires the
   requested port exactly.
6. Inspect the existing Cloudflare Tunnel ingress and catch-all. Preserve every
   unrelated hostname and keep the final catch-all last.

## 3. Install the durable origin

Clone or refresh the deploy checkout at the pinned ref. Use a rendered systemd unit
with resolved absolute values—never install the placeholders below:

```ini
[Unit]
Description=OpenWiki visualizer (<project slug>)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=<service user>
WorkingDirectory=<absolute deploy checkout>
ExecStart=<absolute openwiki binary> visualize <absolute wiki directory> --port <port> --no-open
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Store the project-specific unit or an exact reconstruction runbook in the target
repository when that repository owns its deployment. Host registration and secrets
remain outside git. Install/enable the unit, then independently prove:

- `systemctl is-active` reaches `active`;
- the journal contains the OpenWiki startup banner and the exact requested
  `127.0.0.1:<port>` (a shifted port is a failed deployment);
- `GET /` returns HTML with OpenWiki's Content-Security-Policy;
- `GET /api/graph` returns JSON with a non-empty node set and the expected wiki root;
- `/events` opens as `text/event-stream` and can be closed cleanly.

Stop and account for every foreground/background probe. A process that merely started
is not verified.

## 4. Add the private public route

1. Create or reuse the Cloudflare Access application and its narrow allow policy.
   Prefer the owner's established identity policy. Where the tunnel supports origin
   Access-token validation ("Protect with Access" / required Access audience), enable
   it so a routing mistake cannot bypass the gate; report explicitly if unavailable.
2. From a clean unauthenticated client, prove the hostname is not yet serving the wiki.
3. Back up the exact live tunnel configuration, insert only this hostname before the
   catch-all, and map it to `http://127.0.0.1:<port>`.
4. Run `cloudflared tunnel ingress validate` and inspect the rule match before restart.
5. Create the DNS route for the existing tunnel, restart `cloudflared`, and prove it
   reaches `active` plus its expected connection/health journal signal.

Never create the DNS/tunnel route first and promise to add Access afterwards: that is a
real public exposure window.

## 5. Reproduce the publication gate

The publication is complete only when all of these are observed on the exact deployed
SHA:

1. local service `active` and exact-port journal banner;
2. local `/`, `/api/graph`, and `/events` probes pass;
3. tunnel configuration validates and `cloudflared` is healthy after restart;
4. a clean unauthenticated HTTPS request reaches the Access login/redirect, never a
   `200` OpenWiki page;
5. an authenticated browser reaches the hostname and renders the graph plus one
   Markdown page and one Mermaid diagram when the wiki contains one;
6. the deploy checkout's `git rev-parse HEAD` equals the recorded pushed SHA.

Return a receipt naming the URL, deployed SHA/ref, OpenWiki version, service/unit,
origin port, Access application/policy, tunnel rule, and each observed gate. Never call
an owner-observed browser pass green until the owner actually reports it.

## Updates

Regenerate OpenWiki through its own feature-branch/PR workflow first. After that change
lands, update the deployment checkout with fetch + fast-forward-only merge to the exact
approved SHA. The visualizer watches the wiki directory, but still verify its journal
reported a rebuild and reproduce `/api/graph` plus the authenticated live probe. Restart
only when the OpenWiki binary/unit changed or the watcher did not reload cleanly.

OpenWiki's inference-provider CI secret generates documentation; it does not grant host
deployment authority. Automatic post-merge deployment (webhook or self-hosted runner) is
a separate owner decision and must preserve the same exact-SHA and Access gates.

## Rollback and removal

- **Rollback content:** move the deploy checkout to a previously recorded good SHA,
  restart only if necessary, then reproduce the publication gate and record both SHAs.
- **Remove a site:** destructive and owner-confirmed. Resolve the exact service, hostname,
  DNS record, tunnel rule, Access app ownership, and deploy checkout first. Disable the
  service, remove only that hostname's route/DNS, validate/restart the tunnel, and verify
  the hostname no longer reaches an origin. Preserve shared Access policies and the shared
  tunnel unless the owner explicitly names them for removal.
"""


_LAUNCH_MODEL_REFRESH_SKILL = """\
---
name: launch-model-refresh
description: >-
  Owner-invoked refresh of the models the Horus TUI offers when launching a
  session (`[launch_models]` in config.toml, read by the launch form). On the
  owner's signal ("a new model shipped / became default", "refresh the launch
  models", "which older models are still supported"), an agent researches the
  VENDOR'S OWN model-deprecation docs (Anthropic for Claude, OpenAI for Codex),
  identifies which `--model` selectors are still Active (including older pinned
  versions the /model picker hides), proposes the config change for owner
  approval, then writes it. Evidence-first and owner-gated: it PROPOSES and,
  once approved, writes `config.set_launch_models(...)`; it never auto-runs,
  never polls, and never exposes a model past its retirement date. Sibling of
  `automated-model-roster-grounding` (that grounds calibration TIERS/PRICES from
  benchmarks; this grounds launch AVAILABILITY from vendor docs) — different data
  and sources, kept separate.
---

<!-- horus-skill-version: 2 -->

# launch-model-refresh — keep the TUI's launchable model list current from vendor docs

The Horus TUI launch form offers a `--model` selector per agent. The list comes from
`config.launch_models_for(<agent>)` (the `[launch_models]` table in
`~/.horus/config.toml`) when set, else the adapter's built-in default. This skill keeps
that owner-curated list current, because there is **no API that enumerates the
selectors a CLI accepts** — the trustworthy source is the vendor's own model docs, read
by an agent.

Owner-invoked only. Trigger on an explicit signal: a new model shipped or became the
default, a model is being retired, or "refresh the launch models". Never scheduled,
never auto-polled.

## 1. Research the vendor's model status (cite sources + an as-of date)

Per-vendor recipe (the sources differ in shape — do not assume one generic fetch):

- **Claude** — one authoritative table at
  `https://platform.claude.com/docs/en/docs/about-claude/model-deprecations`: each API
  model name with its state (Active / Legacy / Deprecated / Retired), deprecation date,
  and retirement date. Active + Legacy models are launchable; Deprecated are launchable
  but dated; Retired fail. The bare aliases (`opus`/`sonnet`/`haiku`/`fable` = latest)
  come from `https://code.claude.com/docs/en/model-config`.
- **Codex/OpenAI** — TWO pages, merged: the active list at
  `https://developers.openai.com/api/docs/models/all` (the `gpt-5.x` / `-codex` family)
  UNION the shutdown dates at `https://developers.openai.com/api/docs/deprecations`. A
  model with a shutdown date already in the past is effectively retired — exclude it.

Record, per selector: exact `--model` string, status, retirement/shutdown date,
recommended replacement. Fetch the page; never answer model status from memory.

## 2. Propose the config change (owner-gated — do NOT write yet)

Read the current list (`config.launch_models_for(<agent>)`, or the adapter default when
unset). Present a diff:

- **Add** — Active/Legacy selectors the owner is likely to want that are not yet listed
  (name the older pinned versions explicitly).
- **Drop** — anything now Retired, or past its shutdown date.
- **Flag** — Active-but-Deprecated selectors with a near retirement date (show the date),
  so the owner decides whether to keep them.

Do NOT dump every Active model — a vendor may list ~10. Propose a **curated subset**: the
latest-family aliases plus the specific versions the owner is comparing or has reason to
pin. The owner picks the final set. This curation is judgment and stays owner-gated.

## 3. Write only what the owner approved

Persist with `config.set_launch_models("<agent>", [<selectors>])` (an empty list removes
the override, reverting to the adapter default). Confirm the written list back, and note
the source URLs + the as-of date so the next refresh knows the baseline. Nothing else is
touched; the TUI picks up the new list on its next launch.

## Boundaries

- Owner-invoked and owner-gated at the write step; never auto-run, auto-poll, or
  auto-widen. Propose, then write what was approved.
- Never expose a selector past its retirement/shutdown date, and never guess a selector
  from memory — the vendor doc is the only source.
- Availability only. Calibration tiers/prices are `automated-model-roster-grounding`'s
  concern; do not touch `horus/datums.py` priors here.
- The list is the owner's curated subset for launching, not a mirror of every Active model.

"""

_HORUS_RELEASE_SKILL = """\
---
name: horus-release
description: >-
  Cut a horus-harness release end to end: the three-file version bump, the PR and
  its required checks, the tag and GitHub release, the PyPI publish, and — the step
  that is NOT implied by any of the others — `scripts/deploy-hosted.sh`, because
  publishing a version does NOT update the hosted dashboard. Use when the owner says
  "release", "cut a version", "publish", or "ship 0.0.x". Owner-gated: a release is
  its own decision, never chained onto the end of other work.
---

<!-- horus-skill-version: 1 -->

# horus-release — cut a version, and land it where people actually run it

## The invariant this skill exists for

**Publishing a version does NOT update the hosted app.** `horus.rafaelfigueiredo.com`
runs a *pinned* uv-tool install that only advances on an explicit upgrade plus a
service restart. A green publish workflow is therefore not a finished release — it is
a finished *publish*. The last action of every release is `scripts/deploy-hosted.sh`.

Nothing else in the chain implies that step, which is exactly why it needs writing down.

## Before you start

A release is its own decision, taken with the owner. Never chain it onto the end of
other work, and never treat "continuity is current" as authorization to cut one.

Confirm first: continuity is checkpointed, `main` is green, and the owner has said to
release *this* version.

## The chain

1. **Bump three files together** — `pyproject.toml`, `horus/__init__.py`, `uv.lock`.
   All three or none; a partial bump ships a package whose own `--version` lies.
2. **Rerun the tests locally**, then open the bump as a PR and let the *required*
   checks go green on the exact commit. `horus merge-watch <pr>` watches them with a
   bounded interval and timeout — do not hand-roll a polling loop.
3. **Merge**, then tag and `gh release create`.
4. **PyPI publish** — trusted publishing runs from the tag. Prove it landed: the
   package JSON *and* the simple index, not just a green job.
5. **`scripts/deploy-hosted.sh`** — refreshed install, `systemctl restart`,
   `/health` reporting the new version, and `/` still 403 behind Access. All four.

## Traps that have actually bitten

- **`uv tool install --force --refresh`, never `uv tool upgrade --reinstall`.** The
  latter re-reads uv's cached index and silently stays on the old version (observed
  0.0.30 -> 0.0.31).
- **`uv tool install horus-harness` without `--python 3.12`** silently resolves an
  ancient version below the floor. Compare `horus --version` with `uv run horus
  --version` when they disagree.
- **Project skills from prospective source before a release cut.** A bundled-skill fix
  reaches the fleet only through a RELEASE, so `upgrade-project --apply` run against
  the *installed* CLI installs the pre-fix version. Use `uv run horus skill install
  --force`, or repeat the projection after installing.
- **`0.1` is reserved** for the first version the owner considers stable enough to hand
  to someone else to test. Until then releases stay on `0.0.x` however structural the
  change — so do not read a patch bump as "small", and never propose `0.1` to signal
  architecture.

## Three OS targets

Windows, Linux and macOS. Claude and Codex projections move together, and each is
compared against the CLI, never against its peer.

## Boundaries

- Owner-gated at the release decision itself; the steps after that are mechanical.
- This skill does not automate any step and does not own `scripts/deploy-hosted.sh`.
- A self-hosted-runner/webhook that makes the deploy step a hard guarantee rather than
  an instruction is tracked in the backlog; until it exists, this text IS the guarantee.
"""


SKILLS: tuple[Skill, ...] = (
    Skill("horus-consolidate", 20, _CONSOLIDATE_SKILL),
    Skill("horus-distill-history", 4, _DISTILL_HISTORY_SKILL),
    Skill("horus-infer", 8, _INFER_SKILL),
    Skill("horus-execution", 17, _EXECUTION_SKILL),
    Skill("delegation-rubric", 12, _DELEGATION_RUBRIC_SKILL),
    Skill("execution-decision", 7, _EXECUTION_DECISION_SKILL),
    Skill("dispatch-decision", 5, _DISPATCH_DECISION_SKILL),
    Skill("fleet-curation", 2, _FLEET_CURATION_SKILL),
    Skill("backlog-librarian", 3, _BACKLOG_LIBRARIAN_SKILL),
    Skill("process-retrospective", 3, _PROCESS_RETROSPECTIVE_SKILL),
    Skill("skill-audit", 6, _SKILL_AUDIT_SKILL, audience=AUDIENCE_HORUS),
    Skill("backlog-refine", 9, _BACKLOG_REFINE_SKILL),
    Skill("cockpit-autonomous-dispatch-contract", 6, _COCKPIT_DISPATCH_SKILL),
    Skill("publish-openwiki-site", 1, _PUBLISH_OPENWIKI_SITE_SKILL),
    Skill("launch-model-refresh", 2, _LAUNCH_MODEL_REFRESH_SKILL),
    Skill("horus-release", 1, _HORUS_RELEASE_SKILL, audience=AUDIENCE_HORUS),
)


# --------------------------------------------------------------------------- #
# Install / inspect
# --------------------------------------------------------------------------- #

def _base_root(project_root: Path, *, user: bool) -> Path:
    return Path.home() if user else project_root


def _target_subdir(target: str) -> str:
    if target not in TARGET_SUBDIRS:
        raise ValueError(f"unknown skill target: {target}")
    return TARGET_SUBDIRS[target]


def skill_path(skill: Skill, project_root: Path, *, user: bool = False, target: str = "claude") -> Path:
    return _base_root(project_root, user=user) / _target_subdir(target) / skill.name / "SKILL.md"


def installed_version(text: str) -> int | None:
    m = _VERSION_RE.search(text)
    return int(m.group(1)) if m else None


def write_skill(
    skill: Skill,
    project_root: Path,
    *,
    user: bool = False,
    force: bool = False,
    target: str = "claude",
) -> SkillAction:
    """Write one skill, version-aware. Upgrades on a newer bundled version; leaves a
    same-or-unknown-version file untouched unless ``force`` (so we don't clobber user
    edits or downgrade)."""
    path = skill_path(skill, project_root, user=user, target=target)
    label = f"{skill.name} ({target}, {'user' if user else 'project'})"
    if path.exists():
        current = installed_version(path.read_text(encoding="utf-8"))
        if not force:
            if current is None:
                return SkillAction("skipped", f"{label}: present without a version marker (use --force to overwrite)")
            if current >= skill.version:
                return SkillAction("exists", f"{label}: up to date (v{current})")
        path.write_text(skill.content, encoding="utf-8")
        return SkillAction("updated", f"{label}: updated to v{skill.version}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(skill.content, encoding="utf-8")
    return SkillAction("created", f"created {skill.rel_path(target=target)}")


def install_skills(
    project_root: Path,
    *,
    user: bool = False,
    force: bool = False,
    targets: tuple[str, ...] = ("claude",),
) -> list[SkillAction]:
    return [
        write_skill(s, project_root, user=user, force=force, target=target)
        for target in targets
        for s in bundled_for(project_root, user=user)
    ]


def missing_or_stale(project_root: Path, *, target: str = "claude") -> list[Skill]:
    """Bundled skills not installed at project scope, or installed at an older version."""
    out: list[Skill] = []
    for skill in bundled_for(project_root):
        path = skill_path(skill, project_root, target=target)
        if not path.exists():
            out.append(skill)
            continue
        current = installed_version(path.read_text(encoding="utf-8"))
        if current is not None and current < skill.version:
            out.append(skill)
    return out


def skill_states(project_root: Path, *, targets: tuple[str, ...] = ("claude",)) -> list[SkillState]:
    """Structured per-(agent, skill) install state for project-scope skills.

    The single detection pass; ``skill_findings`` formats these into doctor/nudge
    prose and the TUI skills viewer renders them directly. No new scanning — it
    reuses ``skill_path`` / ``installed_version`` / ``SKILLS``.
    """
    states: list[SkillState] = []
    for target in targets:
        for skill in bundled_for(project_root):
            path = skill_path(skill, project_root, target=target)
            if not path.exists():
                states.append(SkillState(target, skill.name, skill.version, None, SKILL_MISSING))
                continue
            current = installed_version(path.read_text(encoding="utf-8"))
            if current is None:
                status = SKILL_UNVERSIONED
            elif current < skill.version:
                status = SKILL_OUTDATED
            else:
                status = SKILL_INSTALLED
            states.append(SkillState(target, skill.name, skill.version, current, status))
    return states


def skill_findings(project_root: Path, *, targets: tuple[str, ...] = ("claude",)) -> list[Finding]:
    """Doctor findings for project-scope skills — prose over ``skill_states``."""
    findings: list[Finding] = []
    for state in skill_states(project_root, targets=targets):
        name, target = state.name, state.target
        if state.status == SKILL_MISSING:
            findings.append(Finding("warn", f"{target} skill '{name}' not installed (run `{state.refresh_command}`)"))
        elif state.status == SKILL_UNVERSIONED:
            findings.append(Finding("warn", f"{target} skill '{name}' present without a version marker (inspect, then use `horus skill install --target {target} --force` if it is safe to overwrite)"))
        elif state.status == SKILL_OUTDATED:
            findings.append(Finding("warn", f"{target} skill '{name}' outdated (v{state.installed_version} < v{state.bundled_version}); run `{state.refresh_command}`"))
        else:
            findings.append(Finding("ok", f"{target} skill '{name}' installed (v{state.installed_version})"))
    return findings
