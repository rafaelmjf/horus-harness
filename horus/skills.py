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
# so an unlabelled one gets read as being for the project it lands in — which is how
# `product-audit` spent months telling 20 consumer repos to audit Horus (#462).
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

<!-- horus-skill-version: 19 -->

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
   - **Convergence read-out (phase-aware, advisory)** — maps each active backlog
     card onto a `## Vision` facet via its `vision_facet` frontmatter. Reports
     facets with open work, facets with no open cards (converged or untouched —
     judge each against that facet's stated definition of done), and a separate
     **exploratory** bucket (`phase: explore` cards, exempt from the facet-link
     requirement because their job is to discover, not converge). It *warns* when a
     `converge`-phase card has no `vision_facet` (the reactive/off-vision smell) or
     names a facet absent from the Vision. Act on a warn by linking the card, setting
     `phase: explore`, fixing the facet name — or, when exploration has genuinely
     proven out a new direction, **promoting it into a new Vision facet** (the facet
     set is a living hypothesis; the roadmap breathes divergence→convergence).

2. **Read `PRD.md`**, any relevant `temp/*.md` handoff notes, and the newest
   `sessions/*.md` recovery note only when one exists.

3. **Record this campaign, in `PRD.md` only** (never source, `AGENTS.md`, or
   `CLAUDE.md`):
   - Fold capabilities shipped *this session* into `## Shipped` as **one line
     each** — not a paragraph; detail lives in git history and optional recovery notes.
   - Add or update `## Backlog` items for new or changed open work. New/changed
     backlog **cards** carry a `vision_facet` (which Vision facet they advance) and,
     for exploratory PoCs, `phase: explore`; a `converge` card that can name neither
     is either off-vision (drop/rescope) or should be `phase: explore`. Give a
     new/next-touched `converge` card one testable acceptance line (EARS-lite:
     "when X, the tool should Y").
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

<!-- horus-skill-version: 2 -->

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
3. Resolve each `depends-on` and `branch` value against both active and archived
   names. Split comma-separated dependency values; preserve the spelling shown
   in the source.
4. Determine last touch with targeted `git log -1 --format=%cs --
   <card-path>` calls plus the two card dates. A shallow clone or missing git
   history is unknown, not stale.
5. Build overlap candidates cheaply. Include exact normalized titles, and
   near-title pairs that share a `vision_facet` or `branch` plus at least two
   meaningful title terms. Add pairs where one card explicitly names the other.
   Rank exact titles, explicit mentions, same branch, then same facet; keep the
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


_PRODUCT_AUDIT_SKILL = """\
---
name: product-audit
description: >-
  Periodic evidence-first INWARD alignment analysis of THIS project: read its
  delivered code and features against its own Vision — facets where the project
  defines them, the Vision's own claims where it does not — and report where the
  product actually stands: what drifted, what is on track, what is done. Use
  when `horus close` / `horus consolidate` print the product-audit staleness
  advisory, or when the owner asks "audit the product" or "where do we stand".
  Analysis and
  suggestions ONLY — it decides nothing: facet/branch verdicts belong to the
  convergence step (paired with a market-scan receipt), card proposals to
  scope-cards, and every archive/improve/ready decision to backlog-refine.
  The receipt lands dated under `.horus/audits/`.
---

<!-- horus-skill-version: 5 -->

# Product audit — the inward evidence step (analysis, never verdicts)

You are auditing **the project you are invoked in**, against **its own** Vision —
never the tooling that shipped this skill. `.horus/PRD.md` in this repository is
the subject; if you find yourself reading the surfaces of the harness that
installed this file instead of this project's, you have the wrong subject. The
CLI supplied only the deterministic trigger (the staleness advisory); you supply
the judgment. This audit is the INWARD half of the evidence base: its receipt
pairs with a market-scan receipt to feed the owner's convergence decisions. It
suggests; it never prunes, cards, or edits the Vision — and it does not issue
demote/defer/retire verdicts of its own (that "prune, never grow" verdict machine
decided too early and was retired; do not revive it).

**Initial stamp:** if no receipt exists under `.horus/audits/` for the stamped
audit, treat this run as the first real audit: widen every "since the last
audit" question to the whole live surface instead of the stamp window.

## Pin the subject before gathering evidence

1. **The Vision's units.** Use the facet table in `PRD.md` if the project has
   one; else the distinct `vision_facet` values carried by its backlog cards;
   else the Vision's own structural claims (its differentiators, product
   boundary, and out-of-scope lines). Say in the receipt which of the three you
   used — a project without facets is audited against what its Vision actually
   claims, never against a roster you invented for it.
2. **The reference surfaces** — where a delivered surface WOULD be mentioned in
   *this* project if anything used it: its entry points (CLI verbs, API routes,
   exported modules), user- and agent-facing docs, CI config, tests, examples.
   Derive them from the repository; name them in the receipt so the next audit
   reuses the list.
3. **The overlap sources** (for evidence 2 below) — 3-6 named upstreams whose
   releases could subsume something this project delivers: the platform it
   builds on, the ecosystem's dominant tools, a direct competitor. Read them
   from the Vision, the Rules, or the previous receipt; if undeclared, ask the
   owner to name them, and record them in the receipt so they are declared from
   then on. Do NOT open-endedly sweep the web for candidates — a bounded, named,
   reusable list is the contract. Special case: when the project under audit is
   itself an agent harness or agent-facing tooling, those sources are the agent
   CLIs' own changelogs.

## Evidence (gather, not recall)

1. **Usage.** Which surfaces did the owner *demonstrably* use since the last
   audit? Evidence: `.horus/` artifacts, git history, machine-local state, a
   short owner interview — plus grepping the reference surfaces pinned above
   for surfaces nothing references. A command referenced only by its own
   implementation counts as unreferenced — but programmatically-wired plumbing
   greps false-negative; treat the grep as a signal, never a verdict. No usage
   telemetry, ever.
2. **Native overlap.** What have the pinned overlap sources shipped since the
   stamp that overlaps a surface this project delivers? Check their changelogs
   and release notes; cite version and date for every claim.
3. **Ceremony.** Which rituals were skipped, rubber-stamped, or nagged? A step
   everyone bypasses is evidence against the step, not the people.

## The receipt — fixed spine, written for a no-context reader

`.horus/audits/<YYYY-MM-DD>-product.md`. The structure is deliberately
semi-deterministic: multiple non-deterministic runs must converge to the same
core reading, so that a summary that "feels off" to the owner is itself a
drift signal pointing at the inputs. Write every section for a reader with
NO prior context — plain-language explanations first; insider terms and PR
numbers only as supporting references. Sections, in order:

1. **What this document is** — the decides-nothing contract, two lines.
2. **The product, in plain terms** — the delivered thesis as it stands NOW
   (not the Vision text restated), including structural findings the window
   produced.
3. **The Vision's units — ONE consolidated table**: unit | in plain terms |
   standing (with evidence) | distance to done | drift? | open/shipped card
   counts. One row per unit, using whichever ladder rung you pinned above; do
   not split roster and detail into separate structures.
4. **Vision branches — same consolidated form** (branch | in plain terms |
   standing | open question), when the backlog carries vision-branch
   umbrellas. Omit the section entirely when it does not.
5. **Per-unit detail** — definition of done restated where the project states
   one, what concretely stands, distance, drift called out separately; depth
   matches the previous accepted receipt for this project, not a bullet skim.
6. **Triage** — three explicit buckets: done or almost done / on track /
   drifted.
7. **Ceremony observations.**
8. **Routed suggestions table** — every suggestion names the step that
   decides it (backlog-refine | convergence step | scope-cards | existing
   card). Nothing is decided in this receipt.

In an interactive session, paste the receipt's formatted content into the
terminal — the owner reviews it in the reply, not by opening the file. End by
offering: dive deeper into ONE named topic from the receipt, or proceed.

## Close the audit

- Update the PRD stamp `last_product_audit: <horus version> <YYYY-MM-DD>`
  only after the owner accepts the receipt. The stamp belongs to the project
  being audited — write it into *this* repository's `PRD.md`, whatever project
  that is. It records that this project was audited, so a real audit here must
  never be left unstamped.
- Suggestions land through their routed step — never act on them here.
- **Anti-ceremony guard:** read the previous receipt; if it and this audit
  are both all-aligned with no suggestions, recommend lengthening the audit
  interval — and note that the interval should weigh releases AND elapsed
  days (releases alone nag during rapid iteration).

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

<!-- horus-skill-version: 2 -->

# Process retrospective — bounded, evidence-first

You are examining how one campaign or episode went, not auditing the Horus
product (that's `product-audit`, periodic and prune-only) and not closing
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
overhead of running it. If not, recommend demoting or retiring it via
`product-audit`.

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
  skill. For the whole product surface use `product-audit`; for one
  campaign's execution use `process-retrospective`.
---

<!-- horus-skill-version: 5 -->

# Skill audit — one skill's text vs reality

**Scope: Horus's own bundled skills, in the horus-harness repo.** This audits
skills whose source is `horus/skills.py`, so it is not installed into managed
projects — a consumer project has the projected `SKILL.md` copies but not the
generator that writes them, and a verdict there would have nowhere to land.
Auditing a target project's *own* skills is not supported yet.

You are auditing the *text* of one skill against how the world and its real
runs actually behaved. This is distinct from `product-audit` (the whole
product surface, prune-only, can never propose growth) and
`process-retrospective` (one campaign incident). This skill's whole purpose
is amendment — its verdict set includes the one thing product-audit forbids:
proposing better text.

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


_MARKET_SCAN_SKILL = """\
---
name: market-scan
description: >-
  Owner-invoked, evidence-first market/competitive research for a NEW idea or a
  PIVOT — the outward twin of product-audit (which looks inward). Use when the
  owner says "market scan", "research the landscape", "who else does this", "is
  this space taken", or when starting or redirecting a project. Frames the
  problem as a Jobs-To-Be-Done hypothesis, tears down 3-6 real competitors with
  fetched evidence, drafts a PR-FAQ-style vision paragraph, and caps market
  sizing to one line. Defaults to a SHALLOW sweep of the top public results and
  then asks the owner whether to go deeper; it never escalates depth on its own.
  Advisory only: it PROPOSES Vision text and
  candidate backlog cards in a dated receipt under `.horus/research/`; it never
  auto-writes the Vision or auto-creates cards. Not continuous monitoring.
---

<!-- horus-skill-version: 8 -->

# Market scan — look outward, propose, never auto-apply

You are researching the world OUTSIDE the repo — the market, competitors, prior
art — to inform a new idea or a pivot. product-audit prunes what Horus already
is; this scans what the world already offers, so the owner can decide where to
go. The output is a dated receipt that FEEDS the PRD Vision and the backlog; it
does not change them.

## Frame it to the intent — build-vs-adopt OR market-gap (ask, don't assume)

The SAME competitor evidence answers two different questions, and the owner's
intent decides which verdict you summarize toward. Do NOT default to the outward
adoption frame silently:

- **deepen-own-use** (personal/internal tool; audience = the owner) → read the
  scan as **build-vs-adopt**: per capability, is there something external with
  *more value* the owner should adopt or compose, or is it worth building/keeping?
  Here a green/yellow/red *saturation* verdict is the WRONG yardstick — a
  commoditized primitive is often table-stakes to adopt underneath, not a reason
  to stop. The verdict is a per-capability build / adopt / compose call.
- **broaden-adoption** (reach new users) → read it as the classic **market-gap**:
  prior-art, differentiation, is-the-space-taken.
- **both** → keep both verdicts side by side.

When `pathfinder` invokes this skill it passes the pinned intent + shipped/vision
brief confirmed with the owner at its Step 0; honor it. Standalone — or whenever
the owner has not confirmed the intent THIS session (an intent pre-declared in
args or a stored prompt is a proposal) — ASK before spending: present the three
options plus a free-text alternative.

## Depth: shallow by default, deeper only when the owner asks

**The default pass is a shallow sweep** — search the top public results for the
space, open only what the teardown grid actually needs, and cite the URLs. That is
usually enough to decide a product direction, and it is cheap enough to just do.

Before starting, state in one short block: the intent (deepen-own-use |
broaden-adoption | both), the trigger (new-idea | pivot), the problem/space in one
sentence, and the competitors you already know. Then run the shallow pass.

**After the shallow pass, report what you found and ASK whether the owner wants
more depth** — naming what a deeper pass would add (more competitors, primary
sources, pricing/changelog verification) and what it would cost. Go deeper only on
an explicit yes.

Never escalate depth on your own initiative, and do not invoke any long-running or
"deep research" mode unless the owner explicitly asks for it by name — a shallow
sweep plus an honest offer is the contract.

## Bake in exactly the outward trio (+ one capped check)

1. **JTBD hypothesis** — "When [situation], I want [motivation], so I can
   [outcome]", plus the current alternatives people use. A skill cannot run real
   interviews, so frame this explicitly as a hypothesis to validate, not a
   finding.
2. **Competitive teardown** — 3-6 named competitors in a grid: does-well / gap /
   positioning / price, each row backed by a fetched URL. Search the top results,
   open the pages a row actually depends on, and cite them; an uncited row is a
   guess and must be labelled as one rather than filled in.
3. **PR-FAQ vision paragraph** — a one-paragraph "if we build this, the headline
   is…" plus 3-5 hard FAQ questions (why now, why us, biggest risk). This feeds
   the PRD Vision almost verbatim.

Plus a **market-size sanity** line — ONE sentence ("big enough / already
saturated?"). Hard-cap it; never let it become a spreadsheet.

**Branch-check variant (scoped):** when the scan targets ONE direction/branch gap
rather than the whole product, a bounded variant is legitimate: competitive
teardown + intent-framed verdict + sources only — skip the JTBD hypothesis and
the PR-FAQ paragraph, and say in the receipt header that it is a scoped branch
check (precedent: the 2026-07-17 X3 scan). Never use the variant for a
whole-product re-baseline.

## Write the receipt (dated, committed, mirrors `.horus/audits/`)

`.horus/research/<YYYY-MM-DD>-<slug>.md`, one page:

```
# Market scan: <idea/pivot> — <YYYY-MM-DD>
Intent: deepen-own-use | broaden-adoption | both
Trigger: new-idea | pivot
Problem / JTBD (hypothesis): "When ___, I want ___, so I can ___"
Current alternatives: [list + links]
Competitive teardown:
  | Competitor | Does well | Gap | Positioning | Evidence (URL) |
Verdict (match to intent):
  - broaden-adoption → Prior-art verdict: green (gap) | yellow | red (saturated)
  - deepen-own-use  → Build-vs-adopt: per capability, build/keep | adopt | compose
Vision draft (PR-FAQ, 1 para): ...
Open questions / hard FAQ: [3-5]
Market-size sanity: <one line>
Candidate backlog items:
  - <candidate> — rationale, from which gap/assumption
Sources: [every URL opened, one per line]
```

Format rules (owner calibration 2026-07-20): write for a reader with no
project context; render the teardown as ONE consolidated table (a lane column
when the scan spans several spaces); mark rows resting on roundup/aggregator
articles as *(secondary)* and name what a deeper pass would verify. When the
owner picked ONE intent but the other frame is cheap to derive from the same
teardown, offer it — both verdicts from one teardown is the proven shape. In
an interactive session, paste the receipt's formatted content into the
terminal; the owner reviews it in the reply, not by opening the file.

**End every scan with the follow-up offer:** dive deeper into ONE named topic
from the receipt (a teardown row, the market-size line, a verdict cell) or
proceed to the next step. Depth stays owner-pulled, never pushed.

## Hand off — propose, the owner disposes

- The **Vision draft** + **verdict** (prior-art or build-vs-adopt, per intent) are written to be distilled into
  `PRD.md`'s Vision by `horus-consolidate` — you do not edit the Vision here.
- Each **candidate backlog item** becomes a candidate card the owner may accept,
  sourced to a specific gap/assumption. New exploratory directions enter as
  `phase: explore` cards; a proven direction can later be promoted into a Vision
  facet (the convergence read-out in `horus consolidate`).
- Advisory only: never auto-write the Vision, never auto-create cards.

## Composable (standalone or as a pathfinder step)

Inputs are a trigger + a one-line problem statement; outputs are the receipt
path, the Vision draft, and the candidate cards. Keep those clean so a larger
re-baseline flow can call this as one step and feed the receipt into
`roadmap-branches` (the divergence tree of alternative roadmaps).

## Deliberately omit

Wardley mapping; a full Lean Canvas (an optional appendix at most); multi-
interview JTBD (label it a hypothesis instead); continuous monitoring / scraping
(the always-on SaaS category, out of scope); any mandatory-invocation or
red-flags ceremony.

"""


_ROADMAP_BRANCHES_SKILL = """\
---
name: roadmap-branches
description: >-
  Build the DIVERGENCE TREE for a project: from a pinned position brief (inward)
  and a market-scan receipt (outward), propose MULTIPLE alternative roadmaps —
  one branch per direction over existing + new items, each with a market-position
  line, a numbered ordered roadmap, and a convergence criterion — plus 1-2
  speculative branches for directions the Vision does not hold yet. Step 3 of the
  pathfinder flow, also owner-invocable standalone ("what directions could we
  take", "show me alternative roadmaps", "build the branch tree"). Re-justifies
  the EXISTING backlog against the pinned intent with explicit push-back — it
  never inherits cards uncritically. Advisory: emits a dated receipt under
  `.horus/research/`; the owner picks branches; it never edits the Vision, never
  creates cards, never reorders the backlog.
---

<!-- horus-skill-version: 9 -->

# roadmap-branches — the divergence tree, not a merged roadmap

You are producing the **divergent** half of the breathing loop: a tree of
alternative roadmaps the owner chooses between. The single most important rule:
**never collapse the tree into one merged roadmap** — merging is the owner's
convergence decision, and pre-merging it destroys exactly the choice this skill
exists to surface.

**The worked example of a good run is
`.horus/research/2026-07-17-roadmap-branches-convergence-test.md`** (this repo).
Read it before writing. It is the shape to reproduce: a flowing position read-out,
four real branches over eight facets, and push-back that names cards.

## Where BRANCHES come from — never the backlog

A branch is a DIRECTION, and directions do not come from the card list. Build them
from:

1. **Facet definition-of-done vs delivered code** — what the facet promises against
   what exists. Never stale, needs no external evidence, richest source.
2. **The owner's real friction** — what is slow, manual, or repeated by hand in
   recent actual use. A direction here often has ZERO cards; that means it was
   invisible to the backlog, not that it is unimportant.
3. **The audit and market receipts** — especially adopt/compose verdicts and
   anything the evidence contradicts.
4. **The Vision's out-of-scope list** — hypotheses, re-testable against fresh usage.

The backlog is read for exactly one purpose: to disposition it against the branches
once they exist (section 6). **A branch whose roadmap is mostly existing cards is a
grooming pass wearing a branch's clothes**; if every branch reads that way, say so
and route the owner to `backlog-refine` instead of shipping the tree.

## Inputs (gather, do not re-derive)

- **The pinned intent** — deepen-own-use | broaden-adoption | both. If it was not
  handed to you (standalone invocation), ASK the owner; never assume.
- **The position brief** — SHIPPED / VISION+audience / OPEN facet coverage. If
  missing, build it now: read `## Vision` (or note the facet table's ABSENCE),
  the active backlog cards with their `vision_facet`/`phase` stamps, `## Shipped`,
  and run `horus consolidate` for the deterministic convergence read-out.
- **The market-scan receipt** (`.horus/research/`) — the outward evidence. If none
  exists, say the tree is inward-only and offer to run `market-scan` first; do not
  quietly substitute your own untested market beliefs.
- **Prior branch-tree receipts** — a re-baseline consumes its predecessors: carry
  forward unresolved branches, unscoped imports, and owner verdicts recorded there,
  re-justified against the CURRENT intent. Never blindly inherited, never silently
  dropped, and never re-derived as if fresh.

## The deliverable — one dated receipt, fixed template

Write `.horus/research/<YYYY-MM-DD>-roadmap-branches-<slug>.md` with exactly these
sections, then STOP for the owner to pick:

1. **Where we are.** **Narrative prose, walking every facet**, each with a
   life-stage judgment — converged (DoD met) / built-but-unproven / active frontier
   / steady-state — and an honest one-line overall position at the end. **Not
   bullets, not a table; a fresh reader must understand the project's situation
   without the conversation.** This section is where full facet coverage lives, and
   it is why the tree itself does not need a branch per facet. Cite a fresh
   product-audit for the underlying evidence rather than re-deriving its numbers,
   but write the position in your own prose — a citation is not a read-out.
2. **Where the market is.** Distilled FROM the receipt (cite it): the landscape in
   shells, then ONE verdict, then the risks. **State each fact exactly once** — if
   a point appears in two sections, delete one.
3. **The tree.** A small ASCII tree: root = the position in two lines, one child per
   branch (speculative ones last), each naming its facet target — or `no facet yet`
   — plus a one-word posture tag (primary/secondary/filler/park is the
   *recommendation*, not a decision).
   **Produce a branch only where there is a real direction.** Branches carry a facet
   target; facets do not generate branches. Fewer branches than facets is normal and
   correct: a converged or steady-state facet needs no branch (say so in section 1),
   and two facets sharing one direction share one branch. Four branches over eight
   facets is a good tree; eight branches padded to cover the table is not.
4. **The branches.** For EACH branch:
   - **Thesis** — why this direction, argued through the pinned intent. **Open it in
     plain terms**: what actually goes wrong today as the owner experiences it, and
     what is different afterwards, before any module, protocol or command appears.
     A reader who has never opened the codebase must be able to say what hurts and
     what would change. Mechanism belongs in the roadmap items below, not here.
   - **Market position** — the required line: "*this exists already but misses X;
     you already have Y but still miss Z; therefore these items*". Market evidence
     appears INSIDE every branch, not only in section 2.
   - **Numbered roadmap** — ordered items mixing existing cards and new proposals,
     each naming whether it is an existing card (with its readiness) or new. Every
     item carries enough depth that `scope-cards` can populate a card without new
     thinking: why, the concrete how (a protocol, a first step), suspected weak
     points, and non-goals. A second-order item (work that depends on findings that
     do not exist yet) is named as such: "findings become their own cards".
   - **Convergence criterion** — when is this branch done, plus a rough cost.
   - **Implied Vision edits** — the facet DIFF this branch entails:
     add / rename / retire / promote-proven-exploration against a NAMED existing
     facet, with draft definition-of-done text for adds/rescopes. Never a
     wholesale table rewrite. **Advancing a facet includes shrinking it** — a branch
     may propose rescoping, retiring an unused feature, or reducing scope to what is
     proven; name these as defer/retire candidates routed to the convergence pass,
     which decides them. This skill never does.
5. **Speculative branches / wildcards (1-2, more when the owner asks).**
   Directions with NO current facet, derived from position + market + intent:
   the gap it names, the idea, the cheapest PoC, why it fits the intent, the
   risk — and, as prominently as the promise, the EXPLICIT converge/drop criterion
   ("converges if …; dropped if …", where dying cheap is a valid success). The tree
   is incomplete without at least one, and **at least one candidate must RE-TEST the
   Vision's out-of-scope list** — an out-of-scope line is a hypothesis too. When a
   candidate's drop criterion is a single cheap read-only check, RUN IT and report
   the answer rather than proposing it.
6. **Recommendation, held loosely.** Primary / secondary / filler / park across the
   branches, one paragraph of reasoning, then the existing-card push-backs
   summarized — each named card with its disposition and reason. The owner reorders
   freely.

Format rules: no-context-reader prose; consolidated tables only for genuinely
enumerable material (the backlog disposition); in an interactive session paste the
receipt content into the terminal; end with the owner pick gate PLUS a
dive-deeper-into-one-named-topic-or-proceed offer. Owner metaphors are examples to
test against, never canon to echo. **Length is not a proxy for depth** — the worked
example is ~330 lines and says more than twice that would.

## Three disciplines that make the tree trustworthy

- **Disposition the backlog AFTER the branches exist, never before.** Every open
  card either earns its place inside an already-formed branch or gets explicit
  push-back (demote / defer / retire candidate, argued through the intent). Doing
  this first is how this skill produces grooming instead of directions.
- **Claims discipline.** Every "X is missing / weak / better" names its
  comparison baseline: what exists today, and why it is insufficient for the
  intent. No claim without its baseline. Verify a card still exists and a number is
  still true before repeating it from a prior receipt.
- **Every candidate exits with a disposition.** Anything considered — market-receipt
  candidates, prior-tree branches, existing cards — either lands in a branch or is
  dropped WITH the stated reason. Silent omission is the failure mode.

## Onboarding fork

If the position brief found NO `## Vision` facet table, section 1 describes the
state without facets, and each branch's "implied Vision edits" instead proposes the
*initial* facet set and offers to stamp existing cards with a `vision_facet` — that
offer IS the assisted onboarding, no separate migration.

## Hand off

The owner picks one or more branches (or amends the tree). The chosen branch —
its numbered roadmap, item depth, and implied Vision edits — is the input
`scope-cards` consumes. Owner verdicts at this gate that rescope, demote, or
re-prioritize an EXISTING card must be recorded in that card's `## Reviews` when
the decision lands (`scope-cards` writes them) — a verdict that lives only in a
receipt or the conversation does not bind future planning runs. You never edit
the Vision, never create cards, never reorder the backlog yourself.

## Deliberately omit

- No auto-pick and no single merged roadmap — divergence is the deliverable.
- No new web research — consume the market-scan receipt; if it is missing or
  stale, say so and offer the scan instead of improvising evidence.
- No execution planning (that is `execution-decision` / `horus-execution`).

"""


_SCOPE_CARDS_SKILL = """\
---
name: scope-cards
description: >-
  Turn an owner-approved roadmap branch or equivalent direction into aligned,
  high-level backlog drafts that preserve enough context for a later refinement
  session. Use after `roadmap-branches`, or standalone when the owner says
  "scope this direction", "draft cards for this branch", or "turn this vision
  branch into cards". This is the SHAPING step, not final readiness: it never
  makes cards dispatchable or grooms an existing backlog. Advisory and
  owner-gated; only approved drafts and Vision/card diffs are written.
---

<!-- horus-skill-version: 8 -->

# scope-cards — from a chosen branch to aligned shaping drafts

You are transcribing an approved direction into cards that pass one bar:

> **The shaping test: a fresh owner+agent refinement session, given only
> `PRD.md`, the source receipt/vision branch, and this draft, understands why the
> item exists, what outcome it seeks, its broad boundaries, and which decisions
> remain — without the originating conversation.**

This skill shapes a branch; `backlog-refine` later decides readiness and owns the
single execution-ready card contract. Do not collapse those jobs back together.

## Input

One chosen branch from a `roadmap-branches` receipt, a raw `vision-branch-*` card,
or an owner-approved direction of equivalent depth. Read the branch thesis,
position/evidence, numbered roadmap, convergence criterion, Vision diffs, and
push-back verdicts. If the direction itself is ambiguous, do not silently invent
it: show the missing decision and resolve it with the owner or route it back to
`roadmap-branches`.

## Output — the shaping-draft contract

Every proposed card carries:

- frontmatter sufficient to place it: `status: open`, `priority`, `created`,
  `created_by`, `phase`, `type`, the named `vision_facet` or speculative
  `branch`, and `readiness: shaping` with a concrete `readiness_reason` naming
  the unresolved refinement work;
- **Why** — the branch reasoning and market/own-use position, not a generic title;
- **Intended outcome** — what would be different if the item proved worthwhile;
- **Broad boundaries** — the likely shape plus explicit early non-goals, without
  pretending the implementation protocol is decided;
- **Open decisions** — questions `backlog-refine` must settle before Ready;
- **Source** — receipt path/branch name or raw owner vision-branch card.

Do NOT invent final `tier`, `surface`, `parallel`, `autonomy`, dependency order,
implementation steps, supervisor acceptance, or live probes. Preserve a field
only when the source already decides it; otherwise leave it for `backlog-refine`.
An umbrella remains a thin unit-level thesis with ordered proposed children and a
convergence criterion; it is not an execution card.

**Second-order items are never pre-invented:** when work depends on findings that
do not exist yet, shape the evidence-gathering item and state that approved
findings may become later drafts. Do not fabricate findings or their fixes.

## Alongside the shaping drafts, propose the branch's edits

- **Existing-card diffs** — the demote / defer / retire push-back the branch made,
  as explicit per-card proposals (field change or archival, with the reason).
- **Vision facet diff** — exact replacement definition-of-done text per touched
  facet (add / rename / rescope / retire), never a wholesale table rewrite.
- **Vision-branch umbrella** — when the direction spans multiple cards and should
  be judged as a unit, draft or refresh a thin `vision-branch-*` umbrella (thesis,
  exists-vs-gaps map, proposed child order, convergence criterion) and stamp each
  child `branch: <umbrella-name>`. Never mirror child status into the umbrella.

## Gate, then write

Present all shaping drafts, existing-card diffs, and Vision edits as concrete
options plus a free-text alternative. Format the proposal set per the owner's
2026-07-20 calibration: ONE consolidated table with an explicit
**Existing / New** column per row (a diff to an existing card is never
visually confusable with a new draft), `phase` visible per row, no-context
prose, pasted into the terminal in an interactive session. The set MUST
include **wildcards** — explicitly divergent `phase: explore` ideas beyond the
branch's numbered items (agent-found ones welcome), each stating its
converge/drop criterion as prominently as its promise; a proposal set with
only convergent drafts is incomplete. End with a
dive-deeper-into-one-item-or-proceed offer. Let the owner approve, amend, or drop each item individually. Only
then write approved items. Owner rejections
and rescopes of existing cards land in that card's `## Reviews`; a verdict
that lives only in conversation does not bind future planning. Anything
unapproved stays unwritten.

## Deliberately omit

- No backlog-wide grooming or Ready verdict — invoke `backlog-refine`.
- No implementation, dispatch, or execution planning.
- No new receipt — the branch receipt plus the written cards are the trace.
- No detailed fields invented merely to make a shaping draft look complete.

"""


_BACKLOG_REFINE_SKILL = """\
---
name: backlog-refine
description: >-
  Refine and disposition an existing backlog with the owner when cards need
  readiness review, concrete execution contracts, ordering, or an honest current
  picture. Use when the owner says "refine the backlog", "groom these cards",
  "what is actually ready", "order the backlog", or after `scope-cards` has
  produced shaping drafts. Manual and owner-gated; never runs autonomously and
  never silently rewrites cards.
---

<!-- horus-skill-version: 8 -->

# backlog-refine — picture first, decisions second, Ready last

This skill owns the **single execution-ready card contract**. It turns existing
cards — including `scope-cards` shaping drafts — into honest Ready, Shaping,
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
2. every Vision facet and active `vision-branch-*` umbrella, each with a short
   goal/description;
3. item counts for each facet/branch split by readiness and priority;
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

`phase: explore | converge` and `priority` remain orthogonal. Priority means
importance when active. A decision-complete exploration probe may be Ready; an
umbrella is never a scheduler execution unit.

## The execution-ready card contract (single authority)

A Ready card carries `status`, `priority`, `tier` (`low | medium | high |
frontier`), `vision_facet` or an explicit speculative `branch`, `phase`, `created`,
`created_by`, `surface`, `parallel: safe | exclusive`, `readiness: ready`, and
`autonomy`. It also carries:

- **Why** — durable context and market/own-use position;
- **How** — concrete protocol or first implementation steps;
- **Acceptance** — deterministic gate on the exact SHA plus a named live probe and
  expected result; an explore probe instead names the cheapest test and its explicit
  adopt/promote/drop verdict;
- **Non-goals** — bounded exclusions;
- **Source** — receipt, vision branch, owner decision, or observed gap;
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

When ordering is requested, respect `depends-on`, branch grouping, priority, and
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
dispatch, schedule, implement, or invoke pathfinder unless the product direction
itself became the unresolved question.

"""


_PATHFINDER_SKILL = """\
---
name: pathfinder
description: >-
  Owner-invoked, guided divergence→convergence re-baseline of a project's
  direction — the thin WORKFLOW that sequences individually-invocable steps: pin
  the intent (deepen own-use vs broaden adoption vs both; triage backlog-POLISH
  requests out to the grooming pass — the full chain is for direction changes),
  pin a position brief (`horus consolidate` read-out), gather the inward
  evidence (`product-audit` where the project has one, else shipped-vs-used with
  the owner), scan the market (`market-scan`, shallow by default),
  build the divergence tree of alternative roadmaps (`roadmap-branches`), then
  shape the chosen branch into high-level drafts (`scope-cards`) and refine the
  approved drafts into execution-ready cards (`backlog-refine`). Works the SAME on a
  brand-new repo and a long-running one (it scouts the route ahead and reports;
  it never builds the road). Use when the owner says "pathfinder", "kickstart",
  "re-baseline", "where should this project go next", "reset the roadmap", or
  "onboard this project onto facets"; interactive by design — the owner and the
  LLM decide direction together, never unattended. Advisory and gated: every
  step hands the owner a proposal and each
  step is also callable standalone — pathfinder adds only sequencing, gates, and
  the receipts handoff; nothing is ever written without approval. Confirm a
  scope before any web work; the market step is shallow by default and offers more
  depth rather than assuming it. Not continuous monitoring.
---

<!-- horus-skill-version: 11 -->

# pathfinder — the re-baseline workflow (thin by design)

You are running the project's **breathing loop** once, on demand: research →
**divergence** (a tree of alternative roadmaps) → the owner picks → shaping drafts
→ refined backlog → later **convergence** (the `horus consolidate` read-out trims the fat).
You are a pathfinder: you **scout the route ahead and report it** — you do not
build the road. This runs the SAME whether the project is brand-new (no facet
table yet — the onboarding fork inside `roadmap-branches`) or years old (a genuine
re-baseline); the name is deliberately age-agnostic.

**Cross-step output convention (owner calibration, 2026-07-20):** every step's
receipt keeps a fixed semi-deterministic spine, uses consolidated tables for
enumerable material, is written for a reader with no project context, is
pasted into the terminal in an interactive session, cites sibling receipts
instead of restating them, and ends with a dive-deeper-into-one-named-topic-
or-proceed offer. The stable structure is the owner's drift detector: a
summary that feels off signals drift in the inputs that produced it.

v2 is **genuinely thin**: every stage is its own skill or CLI signal, and
pathfinder contributes NO analysis of its own — only the sequencing, the owner
gates between steps, and passing each step's receipt into the next. (v1 kept the
direction/card judgment inline and unstructured, and its output quality drifted;
the depth requirements now live in the step skills, where `skill-audit` can hold
each one against reality separately.)

This table is the contract: read it before running anything, so you know what each
step does, what it costs, and what it hands the next one. **Steps 0-2 spend nothing;
step 3 is the only web spend; every step gates on the owner.** A step listed only in
the prose below is a step that gets skipped — that is how step 7 was missed on
2026-07-31, when a run went 0-4, was rejected, and trailed off without ever stating
what had landed.

| The owner's question | Runs | What happens, in detail |
|---|---|---|
| **0 — Is this a re-baseline at all, and what for?** | pathfinder itself | **Triage before anything else.** If the *direction* is in question — drift, a pivot, a new opportunity, onboarding onto facets — this chain applies. If the direction holds and the backlog merely needs readiness, contracts, disposition or order, that is grooming: route it to `backlog-refine` standalone and say plainly that the full chain would be ceremony. Then pin the intent, **interactively**, because it steers both the research frame and the verdict criteria downstream: `deepen-own-use` (audience is the owner; evidence reads as build-vs-adopt per capability), `broaden-adoption` (evidence reads as market gap and differentiation), or both. An intent arriving in the invocation arguments, a stored `next_prompt`, or a scheduled brief is a **proposal, not a confirmation** — present the options and get a pick. Also settle here whether the owner wants a gate at every step (default) or one pre-authorized straight-through run. Produces no artifact; nothing else starts until the intent is confirmed. |
| **1 — Where are we?** | `horus consolidate` (read-out) | **Builds the pinned position brief, which every later step treats as a hard constraint.** Reads `## Vision` — or notes the facet table's absence, which switches the chain into its onboarding fork — plus the active backlog cards with their `vision_facet` and `phase` stamps, `## Shipped`, and the deterministic convergence read-out that maps cards onto facets. The brief states three things: what has shipped, what the Vision claims and for whom, and where facet coverage is open or thin. Its job is to stop later steps drifting into research about a project this is not. Costs nothing — no web, no fan-out. Gate: the owner confirms the brief before the chain continues. |
| **2 — What actually earned its keep?** | `product-audit` (or a shipped-vs-used pass with the owner) | **Gathers the inward half of the evidence base.** Drift is an inward symptom, so this runs before looking outward. Three evidence lines: which surfaces the owner *demonstrably* used since the last audit (from `.horus/` artifacts, git history, machine-local state, and grepping the project's own reference surfaces — never telemetry); what the declared upstream sources shipped that overlaps something this project delivers; and which rituals were skipped, rubber-stamped or nagged past, because a step everyone bypasses is evidence against the step. **It is analysis only — it never issues demote, defer or retire verdicts**, which belong to the convergence session; suggestions are routed to the step that owns each decision. Produces a dated receipt under `.horus/audits/`. Costs nothing. Gate: stop with the owner when the audit *changes* the brief; say so and proceed when it merely confirms it. |
| **3 — Where is the world?** | `market-scan` | **Gathers the outward half, read through the pinned intent.** Under `deepen-own-use` the yardstick is build / adopt / compose **per capability** — is something external more valuable than maintaining this ourselves — and a market-saturation verdict is explicitly the *wrong* instrument. Under `broaden-adoption` it is the classic prior-art and differentiation read. Produces a JTBD hypothesis (labelled a hypothesis, never a finding — a skill cannot run interviews), a competitive teardown of 3-6 named products with a fetched URL behind every row, a PR-FAQ vision paragraph, and a one-line market-size sanity check that is hard-capped. **This is the only step that spends web budget**, it runs a shallow sweep by default, and it offers more depth rather than escalating on its own. A fresh, still-valid receipt may be reused instead. Produces a dated receipt under `.horus/research/`. Gate: the owner reacts to the evidence. |
| **4 — Which directions could we take?** | `roadmap-branches` | **Produces the divergence tree — multiple alternative roadmaps, never one merged plan**, because merging is the owner's convergence decision and pre-merging destroys the choice this step exists to surface. Branches are DIRECTIONS, drawn from the gap between a facet's definition of done and the delivered code, from the owner's real friction (a direction with zero cards is a signal it was invisible to the backlog, not that it is unimportant), from the audit and market receipts, and from the Vision's out-of-scope lines treated as re-testable hypotheses. **The backlog is never the material branches are built from** — it is dispositioned against the branches once they exist, every card either earning a place or getting argued push-back. Full facet coverage lives in the receipt's narrative position read-out, **not in the branch list**: a branch is produced only where there is a real direction, so fewer branches than facets is normal and a converged facet needs none. Each branch's thesis opens in plain terms — what goes wrong today, what is different afterwards — before any mechanism, then carries a market-position line, a numbered roadmap deep enough for `scope-cards` to work from, a convergence criterion, and the facet diff it implies (which may propose shrinking a facet). Includes 1-2 speculative branches, at least one re-testing an out-of-scope declaration. Produces a dated receipt under `.horus/research/`. Gate: **the owner picks**, amends, or rejects the tree. |
| **5 — What high-level work does the chosen branch imply?** | `scope-cards` | **Shapes the picked branch into aligned high-level Shaping drafts** — enough context preserved that a later refinement session does not re-think the direction, but deliberately *not* execution-ready cards. Marks each draft as existing or new, carries the branch's Vision facet diff and any push-back diffs against existing cards, and requires wildcards to state their converge-or-drop criteria. Owner verdicts from step 4 that rescope or demote an existing card are written into that card's `## Reviews` here, because a verdict living only in a receipt does not bind future planning runs. Gate: the owner approves per item, and only approved drafts are written. |
| **6 — What is genuinely ready, waiting, or still undecided?** | `backlog-refine` | **The only step that makes a card execution-ready.** Runs picture-first and interactively: a walkthrough per card — problem background, proposed solution, verdict — with decisions taken strictly one at a time. Sets final readiness and autonomy, writes the concrete execution contract, records disposition for what is not proceeding, and applies the owner-approved order. Only cards passing its single execution-ready contract come out Ready. This is also the **standalone door**: an owner who wants grooming without a direction change invokes this directly and skips the chain entirely. Gate: interactive throughout; nothing is silently rewritten. |
| **7 — What landed, and what stays unapplied?** | pathfinder itself | **Closes the run — the step most likely to be skipped, because it produces no artifact of its own.** State what was actually written through the normal paths (approved cards, card edits, Vision diffs), and name everything the owner deferred as **explicitly not applied**, so nothing is left ambiguously half-decided. Then stop. **Convergence — trimming the fat once usage evidence has accumulated — is a SEPARATE session**, driven by the `horus consolidate` read-out, and is never chained off the end of this one. Re-run pathfinder only when a real re-baseline is needed again, not on a schedule and not because a bundle looks stale. |

**Receipts are the interfaces**: the market receipt and the branch-tree receipt
live under `.horus/research/`, and the card drafts land as files — so the chain
can pause at any gate and resume in a later session, and any step can be invoked
standalone without the workflow.

## Hard boundary — advisory, gated, never auto-applied

- **Never auto-apply.** Every step hands the owner a proposal; Vision and backlog
  are the load-bearing artifacts and git is the reversal path.
- **Gate at every step by default.** The owner may pre-authorize a
  straight-through run at Step 0; the intermediate gates then collapse into ONE
  final review of the whole package (tree + chosen-branch drafts) — but nothing
  (Vision text, cards, card edits) is ever WRITTEN without explicit approval.
- **Facet changes are always a DIFF** against the existing set (the rule lives in
  `roadmap-branches`: add / rename / retire / promote against a named facet);
  never a wholesale Vision replacement, so a re-run does not thrash continuity.

## Step 0 — pin the intent BEFORE anything (never assume it)

**Triage first: is this a re-baseline at all?** Two owner needs arrive wearing
similar words, and they take different-size tools:

- **Re-baseline** — the *direction* is in question (drift, a pivot, a new
  opportunity, onboarding onto facets). That is this chain.
- **Backlog polish** — the direction holds; existing cards need readiness,
  concrete execution contracts, disposition, or order. Invoke `backlog-refine`
  standalone. Running the full chain for a grooming need is ceremony — route it
  out and say so.

`scope-cards` owns high-level branch shaping; `backlog-refine` alone owns final
execution readiness. Do not merge the two contracts.

A re-baseline has more than one legitimate goal, and the goal steers the whole
run — the research frame AND the verdict criteria. Do NOT default to one silently:

- **deepen-own-use** — make it more useful for the owner's own stated goals
  (audience = the owner). Research reads as **build-vs-adopt** per capability,
  NOT market saturation.
- **broaden-adoption** — reach new users. Research reads as market gap /
  prior-art / differentiation.
- **both** — run the outward scan but summarize through both lenses.

**Confirm interactively, even when the intent arrives pre-declared.** An intent
carried in args, a stored `next_prompt`, or a scheduled brief is a PROPOSAL, not
a confirmation — present the options above plus a free-text alternative and get
the owner's pick before launching any machinery. (Calibration: the 2026-07-17
convergence-test run treated a pre-pinned intent as settled and skipped the ask.)

The pinned intent travels into every step: the envelope statement, the
`market-scan` framing, the `roadmap-branches` theses, the `scope-cards` context,
and `backlog-refine` readiness decisions. Also settle here whether the owner wants per-step gates
(default) or a pre-authorized straight-through run.

## Before you spend — confirm the token envelope

Step 3 goes to the web (Steps 1–2 are no-spend). Before it, state: the intent
(from Step 0), the trigger (re-baseline | onboarding), the project in one line,
and the directions you already suspect. `market-scan` then runs a SHALLOW sweep of
the top public results by default and asks the owner afterwards whether to go
deeper — so a normal Step 3 needs no depth negotiation up front, and depth is
never escalated without an explicit request. A fresh, still-valid receipt
may be reused instead of a new scan — say so explicitly and get a nod; that nod
carries the owner's reaction to the evidence, so it REPLACES Step 3's STOP (do
not re-gate reused evidence — calibration 2026-07-17). If the owner only wants
the inward pass, skip the scan and let `roadmap-branches` mark its tree
inward-only.

## The flow

1. **Position brief (no spend).** Read `## Vision` (or note the facet table's
   absence), the active cards with their `vision_facet`/`phase` stamps, and
   `## Shipped`; run `horus consolidate` for the deterministic convergence
   read-out. Write the pinned brief — SHIPPED / VISION + audience (per Step 0) /
   OPEN facet coverage — a HARD CONSTRAINT passed into every later step so the
   research stays anchored to what the project already is and who it is for.
   STOP for the owner to confirm the brief (unless straight-through).
2. **Inward audit (no spend).** Drift — pathfinder's own trigger — is an inward
   symptom, so gather the inward evidence before looking outward. Where the
   project has an inward-audit skill (`product-audit` on horus-harness), run it —
   or reuse its receipt when one is fresh. Everywhere else the generic form is a
   short shipped-vs-used pass WITH the owner: walk `## Shipped` (or the features
   ledger) asking what was actually used since the last re-baseline and which
   rituals became ceremony — pathfinder elicits, it does not analyze. Fold the
   answers into the brief; they become `roadmap-branches`' push-back evidence and
   any demote/defer/retire verdicts flow through the normal advisory paths. STOP
   with the owner when the audit changes the brief (skip the stop when it
   confirms it — say so and proceed).
3. **`market-scan`** with the intent + brief, under the confirmed envelope. Its
   dated receipt is the outward evidence. STOP for the owner to react (already
   satisfied when the receipt was reused under the envelope nod — proceed).
4. **`roadmap-branches`** consuming the brief + receipt (+ prior branch-tree
   receipts when they exist) → the branch-tree
   receipt: per-facet position, market shells → verdict → risk, one branch per
   direction (each with a market-position line, a numbered roadmap, a convergence
   criterion, implied Vision edits), 1-2 speculative branches, explicit
   push-back on existing cards, and a held-loosely recommendation. The
   **Onboarding fork** lives there: no facet table → propose the initial facet
   set and offer to stamp existing cards. STOP: the owner picks branch(es).
5. **`scope-cards`** on the chosen branch → aligned high-level Shaping drafts +
   the branch's Vision facet diff + existing-card push-back diffs. The owner
   approves per item; only approved drafts are written.
6. **`backlog-refine`** over the approved drafts and affected existing backlog →
   picture-first interactive decisions, final readiness/autonomy, concrete
   execution contracts, disposition, and owner-approved order. Only Ready cards
   pass its single execution-ready contract.
7. **Hand off.** Approved cards and edits are in place via the normal paths;
   anything the owner deferred stays unapplied — say so. Later, **convergence is
   a separate session**: usage evidence accumulates, the `horus consolidate`
   read-out trims the fat; re-run pathfinder only when a real re-baseline is
   needed again.

## Deliberately omit

- No new CLI subcommand, module, roles, or multi-file ceremony — the
  deterministic signals already exist; pathfinder is pure sequencing over them.
- No analysis inside pathfinder itself — depth belongs to the step skills where
  it can be audited and calibrated one skill at a time.
- No token estimate beyond stating the depth — `market-scan` owns the actual
  fan-out, and it defaults to a shallow sweep before offering more depth.
- No continuous monitoring (that always-on category is out of scope).

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
  (mode/account/tier/depth), `backlog-refine`/`scope-cards`/`pathfinder`/`roadmap-branches`
  (ready-gate), and the `horus envelope`/`schedule`/`run`/`supervise`/`notify`
  commands; it never re-implements them. Advisory and owner-gated at EVERY step:
  it proposes, the owner confirms each gate. It never selects a model, routes an
  account, or launches anything without the explicit consent envelope. Not
  continuous monitoring; single-machine, non-recurring dispatch only.
---

<!-- horus-skill-version: 5 -->

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
Deferred, and vision-branch umbrellas are not unattended candidates. If the
direction holds but the card is thin or Unclassified, STOP and route it through
`backlog-refine`. If the direction itself is unclear, use the full `pathfinder`
chain (`roadmap-branches` → `scope-cards` → `backlog-refine`). A fresh unattended
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


_WILDCARD_SKILL = """\
---
name: wildcard
description: >-
  Owner-invoked (or scheduled) AUTONOMOUS divergence skill that proposes NEW MOVES to
  advance the vision — the safe autonomous sibling of pathfinder. It draws ideas from the
  gap between each Vision facet's definition of done and the code that actually exists,
  from the owner's real friction in recent use, and from outside the project — never from
  the backlog, which it reads only to avoid duplicating. It emits ALL valid moves RANKED
  high→low, each one BUILDABLE and SELF-SUFFICIENT: a fresh agent could start it without
  asking the owner anything, because every execution choice it depends on has already been
  made and stated. Strictly ADDITIVE: it never proposes dropping, archiving, pruning or
  deferring anything — those are backlog-refine and convergence decisions.
  Safe to run unattended because every output is a proposal the owner disposes of — it
  never sets direction, never implements, never edits the backlog.
  Use when the owner says "run wildcard", "surprise me with an opportunity", "what am I
  missing", or schedules an away-mode discovery job. NOT autonomous convergence (direction
  stays owner-gated via pathfinder) and NOT a card factory (cards are drafted only on
  request, for ideas the owner picks).
---

<!-- horus-skill-version: 7 -->

# wildcard — autonomous divergence → ranked, buildable vision-advancing moves

**Status: v5 (2026-07-31, from the run-3 failure).** This SKILL.md and its `.agents/`
twin ARE the source — there is no generator for this skill yet, so they are edited
directly and kept byte-identical. Registering it in `horus/skills.py` (version wiring +
install verification) is the dedicated-session step the `wildcard` backlog card drives.

## Purpose — move the vision FORWARD

`wildcard` exists to propose **new moves that advance the vision**: a facet closer to its
definition of done, or a `vision-branch-*` direction closer to being promoted into a facet.
Divergence here means *finding the next thing worth building or proving*.

Two properties make an idea worth emitting, and they are the whole skill:

- **BUILDABLE** — its substance is a change to code or prose, or a fully specified probe.
  Something an agent could execute.
- **SELF-SUFFICIENT** — a fresh agent could start it without asking the owner anything,
  because every choice its execution depends on has already been made *inside the idea*.

Anything failing either property is not an idea, it is an agenda item. See the
self-sufficiency bar below — it is the primary gate, and the one this version exists for.

**Never propose dropping, archiving, deprioritising, pruning, retiring, or deferring
anything.** Those are subtractive decisions and they belong to `backlog-refine` (per-card
disposition) and the convergence step (facet and branch verdicts) — never here. A run whose
output is mostly "stop doing X" has failed, however well-evidenced: it spent a divergence
pass on work another skill owns. If a subtraction is genuinely the obvious move, note it in
one line at the end and route it, then get back to proposing forward moves.

## Grounding — where ideas come from (NEVER the backlog)

Four sources, in this order. **The backlog is not one of them.** Existing cards and
`vision-branch-*` umbrellas are read for ONE purpose: to avoid duplicating something already
carded. They are never the well ideas are drawn from.

This is the correction v5 exists for. Four consecutive revisions fixed the *shape* of the
output while the procedure still said "diverge over the branches" — so every run obediently
produced backlog triage, and the fallback grounding ("the live session's context plus the
backlog") was the recency-anchoring failure mode written in as an approved path. Ideas do
not come from the project's own bookkeeping. If an idea can be traced to a card, it is
almost certainly triage wearing an idea's clothes.

1. **Facet DoD vs delivered code — always available, never stale.** Take each Vision facet's
   definition of done and go read what actually exists in the repo. The gap between the two
   is the richest source there is, it needs no external evidence, and it cannot go out of
   date. Start here on every run.
2. **The owner's real friction — highest signal when present.** What was slow, manual,
   surprising, repeated by hand, or annoying in recent actual use of the product? Session
   context and recent continuity are legitimate evidence *of friction*; the move is the
   capability that removes it, not a note about the friction. (The one output this skill
   ever produced that the owner judged good — the `backlog-librarian` capability — has this
   shape.)
3. **Outside the project — opt-in, scope-confirmed.** What do comparable tools, agent-CLI
   changelogs, or the wider ecosystem now make possible that this project has not absorbed?
   This costs web work: confirm the scope with the owner before spending it, and skip it
   silently in an unattended run rather than escalating.
4. **A previous pathfinder run's artifacts — context, not the well.** Position brief,
   product-audit receipt, market-scan receipt, roadmap-branches tree. Useful for what the
   project already concluded; they are background, and never the thing being paraphrased.

**Disclose dates; never refuse on age.** State the date of every artifact you leaned on and
let the reader judge what that is worth. Do NOT add a freshness threshold and do NOT refuse
to run because an artifact looks old: staleness here is subjective and hard to pin down, so
it is left to the reader's interpretation (owner, 2026-07-31) — and a preemptive gate where
nothing has been shown to fail contradicts the PRD's controls ladder. Source 1 never goes
stale, so a run is always possible.

## What it is / hard boundaries

- **Advisory, owner-gated.** Emits ranked *proposals*. NEVER sets direction, NEVER
  implements, NEVER creates/edits cards until the owner picks one.
- **Safe to run unattended** because every output is a proposal the owner disposes of —
  nothing is written, so the blast radius is zero. The safety comes from
  proposal-not-mutation, **not** from emitting only one item.
- Ranked ideas, not a flood of drafted cards: full card drafts happen on request only.
- **Additive only.** Every proposal builds, proves, or unlocks something. Dropping,
  archiving, pruning, deprioritising and deferring are `backlog-refine` and convergence
  decisions; proposing them here is out of contract, not merely low-value.

## The self-sufficiency bar — the primary gate

**An idea is ready to emit only if a fresh agent could build it without asking the owner
anything.**

If the idea's execution depends on a choice — where something lives, which of two shapes it
takes, what the field is called, what the threshold is — **make the choice, state it, and
give the one-line reason.** Do not hand the choice back.

This is not a style preference, it is the difference between a proposal and a meeting. The
owner disagreeing with a stated choice is a cheap and useful conversation, and it happens
*before* building. The owner being asked to settle three questions before anything can start
is the failure this bar exists to stop. **"Decide X, then build Y" is not an idea.** Neither
is anything whose real ask is a go-ahead.

Concretely, an idea fails this bar if:

- its `Do this` contains "decide", "settle", "define", "determine", "choose", or "agree";
- its substance is unblocking a card that is blocked *on owner decisions*;
- its `Change performed if accepted` describes an outcome ("a verdict recorded", "clarity
  on X", "the card becomes writable") rather than a named change to named things;
- a fresh agent reading it would have to come back with a question before writing anything.

When an idea is genuinely worth doing but genuinely needs the owner to choose first, that is
a real finding — write it as ONE routed line at the end (`needs an owner decision:` …), not
as a ranked proposal.

## Procedure

1. **Diverge — one lens at a time, over the GROUNDING SOURCES.** Generate ~5-7 candidate
   moves, each from a DISTINCT lens, working the sources above — facet-DoD gaps first, then
   friction, then outside. Vary the frame deliberately and do not let one frame's result
   shape the next. **Do not iterate over the backlog or the branch umbrellas**: that is what
   produced triage in every prior run. True branch isolation would need parallel subagents;
   that is a token-intensive fan-out requiring owner authorization under the delegation
   rule, so it is not the default. (Prior art for the isolated-frames + separate-critic
   structure: github.com/uditakhourii/adhd.)

2. **Make each candidate self-sufficient BEFORE ranking it.** For every candidate, list the
   choices its execution depends on and settle them now, with a reason each. A candidate you
   cannot settle is not ready — either do the reading that settles it, or drop it to the
   routed-line list. This step is where a triage item reveals itself: if settling the choices
   IS the whole idea, it was never a move.

3. **Critique and RANK — every valid idea survives.** Score each candidate and order them
   high→low. Do not discard a valid idea to manufacture a single winner. Drop a candidate
   only if it is genuinely invalid: already covered by an existing card or skill, factually
   wrong, or outside this project's scope. Say so in one line and move on — a long reject
   list is a symptom, not a deliverable.

   Rank on: how far it moves a facet or branch FORWARD · is the evidence real and cited ·
   is it cheap relative to what it unlocks · does it respect the PRD Rules. A candidate whose
   substance is a drop, archive, deprioritise or defer is **invalid here** — route it to
   `backlog-refine` in one line and rank it nowhere.

   **Three mandatory checks before ranking, all learned from failed runs:**
   - **Self-sufficiency check.** Apply the bar above to every candidate. This is the one
     that would have emptied run 3.
   - **Rules check.** Read `## Rules` in PRD.md and reject anything that contradicts one.
     A candidate proposing a new control where nothing has failed in the field violates the
     controls ladder ("never enforce preemptively") and is invalid, not merely low-ranked.
   - **Premise check.** For every field, flag, or convention the idea relies on, confirm
     what it *actually* means to the owner before building on it. A dated field may be a
     floor ("not before"), not a due date ("act on").

4. **Emit the ranked set — index first, then a scope block per idea.** A ranked table is an
   index, not the proposal: on its own it makes a decision, an experiment and a code change
   look like the same size of thing. Every idea therefore carries a scope block, so the
   owner can judge what they are agreeing to without asking a follow-up question.

   **The index table:** rank · **the action, as an imperative** · what it advances · `kind` ·
   effort.

   **Then, for EVERY idea, an action-first block. Lead with the two fields the owner
   actually needs, and keep them concrete:**

   - **Do this** — ONE imperative sentence naming the work. "Add X to Y so Z" or "Run A
     against B and record C". Not a topic, not a question, never "explore", "consider", or
     any of the decision verbs listed in the self-sufficiency bar.
   - **Change performed if accepted** — the concrete before→after. Name the files,
     commands, or behaviour that differ afterward, in terms someone could verify. This is
     the field that answers "what am I agreeing to", so it must survive one test: *could a
     fresh agent start work from this line alone?* If not, rewrite it.
   - **Choices already made** — the execution decisions this idea settles on the owner's
     behalf, one line each with its reason. This is what makes it buildable rather than a
     request for a go-ahead, and it is where the owner pushes back if they disagree.
   - **Why this advances the vision** — the named facet or branch, and which clause of its
     definition of done or convergence criterion moves. One sentence, cited.
   - **Size** — `kind` + effort. Kind must be one of: `code change` · `prose change` (docs,
     skills, continuity text) · `probe` (a bounded experiment, fully specified: the exact
     commands, what gets recorded, what it settles). **`decision` and `evidence read` are
     not emittable kinds** — an idea whose substance is either belongs in the routed line
     at the end.
   - **Not included** — one line, concrete. Name the adjacent thing a reader would assume
     comes along and does not ("does not touch the scheduler", never "out of scope: broader
     concerns").
   - **Risk** — one line: why it might not work, or cost more than it looks.

   Then a short rationale paragraph for the **top 2-3 only**.

   **Draft a full card only for an idea the owner picks**, and offer the honest
   alternative: if it is small and the owner is present, the PRD Rule "card what you won't do
   now; fix what you will" says do it now and skip the card. State per idea whether it wants
   a new card, belongs to an existing card (name it), or is a fix-now candidate.

### Worked example — the shape, and the failures to avoid

**Good** — buildable, and every execution choice already settled:

> **1 — Stamp per-card usage at dispatch close so `explore` cards can be judged on real
> use** · advances PO lifecycle · `code change` · one session
>
> - **Do this:** stamp the worker's start/end usage reading onto the card it delivered, at
>   the point `supervise` already writes its ship-stamp.
> - **Change performed if accepted:** `horus/supervise.py`'s ship-stamp path gains a
>   `usage_at_close` write to the delivered card's frontmatter; `horus/backlog.py` tolerates
>   and exposes the field; `explore`-phase cards start accumulating a real usage signal
>   where today they have none.
> - **Choices already made:** field name `usage_at_close` (mirrors the existing
>   `shipped_sha` naming); written at ship-stamp rather than a new hook (that path already
>   opens the card for write); stored as the raw reading, not a delta (deltas need a
>   same-window pair, which dispatch cannot guarantee).
> - **Why this advances the vision:** PO lifecycle's open frontier is
>   convergence-driven-by-usage, and `explore-converge-lifecycle` is Deferred *specifically*
>   waiting on "a real per-card usage signal" — this produces exactly that signal.
> - **Size:** `code change`, one session.
> - **Not included:** does not add the converge-or-drop advisory itself; does not touch the
>   usage cache and adds no polling.
> - **Risk:** dispatch is rare right now, so the signal accumulates slowly and may stay too
>   thin to judge anything for weeks.

**Bad — abstract.** Every line is a topic rather than an action, and no fresh agent could
start from it. This skill has produced all three; do not:

> - ~~**In scope:** clarify the branch's direction and gather the relevant evidence.~~
> - ~~**Deliverable:** a verdict recorded in the umbrella's Reviews.~~
> - ~~**Consequence:** the review becomes a short question; card count drops.~~

**Bad — the run-3 shape: a to-do list for the owner.** Every line here is concrete, cited
and honest, and it is still not an idea, because the work it names is the owner's:

> - ~~**Do this:** decide where the contract is declared (docs vs code constants vs README),
>   the exact field list per tier, and how tier names surface to users.~~
> - ~~**Change if accepted:** the card leaves `shaping` and becomes writable.~~

Three of run 3's five proposals had this shape. It passes every earlier check in this file —
it is specific, it cites its grounding, its scope block is fillable — and it fails the only
one that matters, because accepting it produces a meeting rather than a commit. The fix is
not to delete the idea: it is to **make the three choices, state them with reasons, and
propose the declaration itself.**

## Output

- A ranked index table of every valid idea (typically 3-6), plus the scope block for each,
  each citing its grounding and the facet or branch it advances.
- One routed line per item that is real but owner-gated (`needs an owner decision:` …),
  after the ranked set, never inside it.
- Full card drafts only on request, for the ideas the owner picks.
- If nothing clears the bar, say so and emit nothing — that is a valid result.

## Quality bar

- **A run that emits zero buildable ideas has failed.** Say so plainly rather than filling
  the set: an all-`decision` output is the exact failure of run 3, where three of five
  proposals asked the owner to choose something and none named a change an agent could make.
- Every emitted idea must be defensible on its own; ranking replaces rejection.
- **The action test: if `Change performed if accepted` would not let a fresh agent start
  work, the idea is not ready to emit.** An abstract deliverable ("a verdict recorded", "a
  finding", "clarity on X") means the idea is a topic, not a move.
- **The self-sufficiency test outranks all of the above** — see the bar above. An idea that
  is specific, cited and well-scoped still fails if building it requires the owner to decide
  something first.
- **Every idea must be additive.** If the ranked set is mostly subtraction, the run has
  failed and should be redone against the forward question.
- Cite grounding per idea, with the date of any artifact leaned on. Check each against the
  open backlog for duplication — that is the backlog's only role here.
- Obviousness **lowers a rank, it never excludes** — an obvious idea the owner has not
  acted on may simply be the right next move.
- Prefer ideas whose evidence already exists over ideas needing new investigation.

## Non-goals

- Not autonomous convergence — direction/roadmap choice stays owner-gated (pathfinder).
- Not autonomous implementation — a picked idea follows refine → approve → implement.
- **Not a pruning pass.** No drops, archives, retires, deprioritisations or deferrals;
  those are `backlog-refine`'s and convergence's authority.
- **Not a backlog triage pass.** Surfacing undecided, stale or blocked cards is
  `backlog-librarian` and `backlog-refine`; a run whose output could have been produced by
  reading the backlog alone has failed regardless of how good the items are.
- Not a card factory: ideas are ranked proposals; cards are drafted only on request.

## References

- Backlog: `wildcard` (refinement driver + the registration step), the four
  `vision-branch-*` umbrellas (duplication check only — not the idea source),
  `pathfinder-structured-outcome` (grounding substrate), `pathfinder` / `scope-cards` /
  `market-scan` (divergence machinery reused), `autotest-e2e-away-mode-drill` (safe
  autonomous-loop food — buildable wildcard ideas are candidate drill legs, which is only
  possible once ideas are executable work rather than owner decisions).
- Prior art: github.com/uditakhourii/adhd (isolated N-frame divergence + separate critic).
- Calibration: 2026-07-21 dry-run produced the `backlog-librarian` card (owner judged it
  good → v0/v1). **2026-07-28 audit (`.horus/audits/2026-07-28-skill-wildcard.md`) → v2:**
  three consecutive live runs produced zero branch-advancing ideas because the text stated
  no purpose and its example frames were all operational hygiene; and the mandated
  one-winner-plus-rejects output read as padding. Both fixed, plus the Rules and premise
  checks that would have caught the two rejected cards. **v2 → v3, same day, from the first
  v2 run:** the ranked table alone made a decision, an experiment and a code change look
  like the same size of thing, so the owner could not tell what any idea committed them to.
  Added the `Kind` taxonomy, the mandatory six-field scope block with an explicit
  out-of-scope list, a worked example, and a quality bar that treats an unfillable scope
  block as a signal the idea is not ready. **v3 → v4, same day, from the v3 run:** all six
  ideas were rejected. Two defects, one of them introduced by this skill's own v2 text —
  "promote-or-**drop**" in the Purpose and "a reason to drop it outright" in the lens list
  made four of six ideas subtractive, which is `backlog-refine`'s authority, not wildcard's;
  and the In-scope/Out-of-scope/Deliverable fields were abstract enough that the owner could
  not tell what any idea would actually change. v4 makes the skill strictly additive and
  replaces the scope block with an action-first one led by `Do this` and `Change performed if
  accepted`, gated by the action test. **v4 → v5, 2026-07-31, from the run-3 failure
  (`.horus/research/2026-07-31-wildcard-branch-divergence.md`):** run 3 was pinned to the
  branch umbrellas — the fix for runs 1-2's recency anchoring — and produced five items of
  backlog triage, which the owner judged "not wildcard worthy … scraping the backlog for
  undecided or stale cards, not novel features and ideas". **The diagnosis is that all four
  prior revisions fixed the FORM of the output and none touched where ideas come from**,
  while the procedure still said "diverge over the branches" and the documented fallback was
  "the session's context plus the backlog". By this skill's own `Kind` taxonomy run 3 emitted
  three `decision`, one `evidence read`, one `probe` — and zero code or prose changes, so
  nothing was executable, which is also why none could serve as away-mode drill legs. v5
  therefore (a) replaces the grounding with facet-DoD-vs-code, owner friction, and outside
  evidence, with the backlog demoted to a duplication check; (b) adds the **self-sufficiency
  bar** as the primary gate, on the owner's framing that an idea should be "ready to build
  without extra decisions rather than a 'go ahead'"; (c) makes `decision` and `evidence read`
  non-emittable kinds with a routed line for genuine owner-gated items; (d) adds
  `Choices already made` to the scope block; and (e) declines a staleness threshold on the
  owner's call that staleness is subjective and better disclosed than enforced.
"""


SKILLS: tuple[Skill, ...] = (
    Skill("horus-consolidate", 19, _CONSOLIDATE_SKILL),
    Skill("horus-distill-history", 4, _DISTILL_HISTORY_SKILL),
    Skill("horus-infer", 8, _INFER_SKILL),
    Skill("horus-execution", 17, _EXECUTION_SKILL),
    Skill("delegation-rubric", 12, _DELEGATION_RUBRIC_SKILL),
    Skill("execution-decision", 7, _EXECUTION_DECISION_SKILL),
    Skill("dispatch-decision", 5, _DISPATCH_DECISION_SKILL),
    Skill("fleet-curation", 2, _FLEET_CURATION_SKILL),
    Skill("backlog-librarian", 2, _BACKLOG_LIBRARIAN_SKILL),
    Skill("product-audit", 5, _PRODUCT_AUDIT_SKILL),
    Skill("process-retrospective", 2, _PROCESS_RETROSPECTIVE_SKILL),
    Skill("skill-audit", 5, _SKILL_AUDIT_SKILL, audience=AUDIENCE_HORUS),
    Skill("market-scan", 8, _MARKET_SCAN_SKILL),
    Skill("roadmap-branches", 9, _ROADMAP_BRANCHES_SKILL),
    Skill("scope-cards", 8, _SCOPE_CARDS_SKILL),
    Skill("backlog-refine", 8, _BACKLOG_REFINE_SKILL),
    Skill("pathfinder", 11, _PATHFINDER_SKILL),
    Skill("cockpit-autonomous-dispatch-contract", 5, _COCKPIT_DISPATCH_SKILL),
    Skill("launch-model-refresh", 2, _LAUNCH_MODEL_REFRESH_SKILL),
    Skill("horus-release", 1, _HORUS_RELEASE_SKILL, audience=AUDIENCE_HORUS),
    Skill("wildcard", 7, _WILDCARD_SKILL),
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
