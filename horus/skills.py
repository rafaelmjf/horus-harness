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


class Skill(NamedTuple):
    name: str
    version: int
    content: str

    def rel_path(self, *, target: str = "claude") -> str:
        return f"{TARGET_SUBDIRS[target]}/{self.name}/SKILL.md"


class SkillAction(NamedTuple):
    status: str  # "created" | "updated" | "exists" | "skipped"
    message: str


# --------------------------------------------------------------------------- #
# Bundled skill content
# --------------------------------------------------------------------------- #

_CONSOLIDATE_SKILL = """\
---
name: horus-consolidate
description: >-
  Consolidate a project's Horus continuity (`.horus/`) so each lane stays in its
  lane — route shipped work into the features ledger, prune done/stale roadmap
  items, distill session notes into the durable files, and de-duplicate facts that
  drifted across roadmap.md and features.md. Use this whenever wrapping up or
  closing out a work session in a repo that has a `.horus/` directory; when the user
  says "consolidate", "wrap up", "update continuity", "tidy the roadmap", or "close
  out"; right after shipping a capability (to move it from roadmap to features); or
  whenever the `.horus/` lanes look like they've drifted. Prefer this over editing
  the `.horus/` files ad hoc, because it runs `horus consolidate` for precise signals
  first and applies consistent routing rules.
---

<!-- horus-skill-version: 8 -->

# Consolidate Horus continuity

You are running *inside* the working session, so you have something the `horus`
CLI does not: the **live context of what just happened** — decisions made, work
shipped, things discussed but not yet written to `.horus/`. Use that. The CLI sees
only the files and git; you see the conversation too. Fold both in.

## Two jobs — do not conflate them

This skill spans two sizes of work. **Do the per-session close every time; do the
backlog pass only when the user asks for it.** Conflating them is why lanes drift:
the per-session part gets half-done because the backlog looks huge.

- **Per-session close (always, bounded):** capture *this* session and make the
  dashboard reflect it. Small and complete — only this session's delta plus the
  dashboard fields below. Steps 3–4.
- **Backlog consolidation (occasional, opt-in):** distill the *accumulated* old
  sessions, move historical done-items into features, split long-standing overlaps.
  A large, separate pass — run it only on an explicit "pay down continuity debt" /
  "consolidate the backlog" request. Step 5. The signals will report a big backlog
  (many done items / undistilled sessions); that pressure is for *this* job, not the
  per-session close — **do not try to clear it every time.**

## The dashboard contract — keep these current at EVERY close

The dashboard renders exactly these as the project's *current* state and never
infers them. If this session moved the project, each must reflect it before you
finish:

- `project.md` → `current_focus` (frontmatter): the one-line "where things are now".
- `roadmap.md` → `next_action` (the single NEXT) and `next_prompt` (the resume prompt).
- `roadmap.md` → `execution_recommendation`: analyze the NEXT and say whether to
  continue directly or prepare `execution.md` + worker/subagents.
- `roadmap.md` → the checkbox states behind the progress bar (mark what this session did).
- `features.md` → a row for anything **shipped this session** (Planned/In-progress → Shipped).
- `execution.md` → active phase status and supervisor/worker handoff state, when this
  session was part of a phased execution plan.
- `last_updated` frontmatter on every lane you touched (bump to today).

`horus close --check` is the gate: it fails (non-zero) while any of these is stale,
so closure isn't done until it passes. It also backs a pre-merge CI check.

## Steps

1. **Get the deterministic signals.** Run `horus consolidate` (optionally
   `--path <repo>`). It reports file-only candidates: roadmap↔features overlaps,
   done-but-unshipped items, session summaries to distill, missing lanes. Leads, not
   gospel — and most belong to the backlog job (Step 5), not this close.

2. **Read the lanes.** Read `.horus/project.md`, `roadmap.md`, `features.md`,
   `decisions.md`, `history.md`, optional `execution.md`, and the newest
   `sessions/*.md` / `temp/*.md` handoff notes. If `docs/routines.md` exists it
   holds the full routing contract; otherwise this skill is authoritative.

3. **Per-session close — record this session** (`.horus/**` only; never source,
   `AGENTS.md`, or `CLAUDE.md`):

   - **Record fresh context.** Decisions, lessons/dead-ends, and capabilities shipped
     *this session* that aren't on disk yet. A decision splits in two: the **rule**
     (concise, under its topic) goes in `decisions.md`, dropping any rule it supersedes;
     the ***why*** and dead ends go in `history.md` ("Decision rationale"). Capabilities
     → a Shipped row in `features.md`. This is the content only you can supply — it's in
     the conversation, not the files.
   - **Update the dashboard contract** (the checklist above): refresh `current_focus`,
     `next_action`, `next_prompt`, the roadmap checkboxes for what you did, and bump
     `last_updated` on touched lanes. Author the next step for a *cold* reader — name
     it, point at `.horus/`.
   - **Recommend the execution mode for the NEXT.** Decide on implementation
     **volume × ambiguity**, not vibes: set `execution_recommendation:
     "continue-as-is — <why>"` for small, ambiguous/exploratory, debugging, or
     mostly-continuity work; set `"plan-execution — <why>"` for high-volume,
     low-ambiguity work with a clear gate (and create/update `execution.md` before
     implementation starts). The `<why>` must name what delegation buys *on this
     runtime* — a frontier supervisor + cheaper worker tiers (e.g. Opus + Sonnet/Haiku)
     gains context hygiene AND a cheaper tier; a single strong model (e.g. GPT-5.5)
     gains mostly context hygiene, so its bar is higher. Do not imply delegation is
     cheaper merely because a standard worker tier exists, and do not sell
     supervisor review as the safeguard (reproduce the gate / bound checkpoints /
     safety-in-code are the durable ones).
   - **When a worker handoff exists** in `.horus/temp/`, use it as evidence, not as
     truth: the supervisor reviews the diff/tests, then distills accepted facts into
     durable lanes and updates `execution.md`.

4. **Keep lanes pure.** No tasks in `features.md`; no shipped packages lingering in
   `roadmap.md`; no open issues in `history.md`; no changelog in `project.md`.
   `decisions.md` is **concise current rules grouped by topic, not a dated log** — if
   it has drifted into long dated entries, collapse superseded ones to the rule that
   won and move the rationale to `history.md` (backlog pass, Step 5). Keep `roadmap.md`
   on top/open action points; condense long completed lists. If `history.md` has grown
   into a verbatim log, that's a `horus-distill-history` job — flag it, don't fix it
   here. `execution.md` is fluid active coordination; archive or replace it when the
   roadmap item is done.

5. **Backlog consolidation — ONLY when explicitly asked.** Distill old `sessions/*.md`
   into the lanes then move them to `sessions/archive/` (local-only, excluded from the
   to-distill count — don't delete); remove stale `temp/*.md` handoff notes once
   reviewed; move historical done items into `features.md` and
   **prune** them from `roadmap.md`; **de-duplicate** roadmap↔features overlaps by
   keeping action points in `roadmap.md` and status in `features.md`, with a literal
   `→ features.md` / `action points → roadmap.md` cross-reference each way (that
   pointer is how `horus consolidate` knows a shared name is an *intentional* split,
   not a duplicate). Skip this entirely during a normal close.

6. **Verify.** Run `horus close --check` — it must pass (the dashboard is fresh). For
   a backlog pass, also re-run `horus consolidate`: an overlap clears only once split
   *and* cross-referenced; in-progress/planned items that legitimately live in both
   lanes keep appearing until they carry the pointer — **do not delete ledger rows or
   roadmap actions chasing zero.**

## Boundaries

- **Never invent** status, dates, versions, or decisions. When intent is unclear,
  leave the content and flag it for the user rather than guessing.
- Edits are confined to `.horus/**`. This is continuity maintenance, not a coding task.
- Bump `last_updated` front matter on lanes you change (if it isn't already today).
"""


_DISTILL_HISTORY_SKILL = """\
---
name: horus-distill-history
description: >-
  Compress a large, raw project log (a long `docs/HISTORY.md`, `CHANGELOG.md`, or an
  oversized `.horus/history.md` archive) down to the curated "bumps in the road" that
  belong in Horus's `history.md` — the problems that bit the project and the durable
  lessons they forced. Use this whenever onboarding Horus into a long-running project
  with a big changelog; when the user says "distill the history", "compress the
  changelog", "the history file is too long", or "summarize the project log"; or when
  `.horus/history.md` has grown into a timeline instead of a curated lesson set. Runs
  `horus distill-history` first for the source-log location and size.
---

<!-- horus-skill-version: 2 -->

# Distill project history

Turn a verbose log into the high-signal subset worth carrying forward. You are not
writing a timeline — you are keeping only what a future agent would otherwise have
to re-learn the hard way.

## Steps

1. **Locate + size the source.** Run `horus distill-history` (optionally
   `--path <repo>` / `--source <file>`). It reports the source log it found and the
   current `history.md` size, so the compression target is explicit.

2. **Read the source log** in full (or in chunks if very large).

3. **Apply the signal test** to every entry:
   - **Keep** — a real problem the project hit *and* the durable lesson or design
     change it forced. The kind of thing that prevents a repeat mistake.
   - **Drop** — routine changelog noise, version-bump entries, resolved-and-now-
     irrelevant incidents, and anything already captured as a rule in `decisions.md`
     (cross-reference it instead of duplicating).

   - If the source *already* contains a curated/highlights section plus a raw
     archive, treat the highlights as just more input — re-derive across the whole
     log and merge, rather than copying the existing summary verbatim.

4. **Write the curated subset** into `.horus/history.md`: short, deduplicated
   "bumps in the road", each pairing the problem with the lesson. Aim for a scannable
   set (roughly a dozen or two high-signal entries), not a line-for-line rewrite —
   if you're keeping most of the log, you're not distilling. Not a timeline, not open
   issues.

5. **Forward open work, don't drop it.** If the log contains roadmap-shaped material
   (backlog, "next session", planned-but-not-done), that's not history — note it for
   the user to fold into `roadmap.md` rather than silently dropping it. (This skill
   edits `history.md`, so flag it; don't edit `roadmap.md` here.)

6. **Freeze the source**, don't delete it: add a one-line "superseded — curated in
   `.horus/history.md`" pointer at the top of its body (just below any YAML front
   matter, so the front matter stays first) so the two don't drift.

## Boundaries

- Only compress what the log records — **never invent** incidents, dates, or causes.
- Edit `.horus/history.md` (and the one-line pointer on the source log); nothing else.
"""


_INFER_SKILL = """\
---
name: horus-infer
description: >-
  Bootstrap or refresh a project's Horus continuity (`.horus/`) by distilling the
  project's own canonical docs — README, status/roadmap files, CLAUDE.md/AGENTS.md,
  and linked docs — into the clean six-lane structure. Use this when setting Horus up
  in an existing repo that already has docs; when the user says "set up horus here",
  "bootstrap the .horus files", "populate the continuity", "infer the project state",
  or "fill in the roadmap from our docs"; or right after `horus init` left placeholder
  lanes. Runs `horus infer` first to find the canonical docs and the empty lanes.
---

<!-- horus-skill-version: 2 -->

# Infer Horus continuity from the project's docs

Most repos already encode their state in prose (a README, a status doc, a roadmap).
This distills that into `.horus/` as the single concise source of "what is this and
what's next" — pointing at the canonical docs rather than copying them, so the two
never drift.

## Steps

1. **Get the signals.** Run `horus infer` (optionally `--path <repo>`). It lists the
   canonical docs to distill from and which `.horus/` lanes are missing or still hold
   `horus init` placeholders. If `.horus/` doesn't exist yet, run `horus init` first.

2. **Read the canonical docs and follow their pointers** — README → status/roadmap →
   CLAUDE.md → linked docs like `docs/*.md`. Build a real model of the project before
   writing anything.

3. **Distill into the lanes**, each in its lane:
   - `project.md` — what it is, current shape, boundaries, current focus.
   - `roadmap.md` — open action points (what's next), grouped.
   - `features.md` — shipped / in-progress / planned capabilities.
   - `decisions.md` — durable decisions + reasoning, dated.
   - `history.md` — curated lessons / bumps in the road (use `horus-distill-history`
     if there's a big log).
   - `execution.md` — optional active execution plan only if the canonical docs
     describe current phased/subagent work.

4. **Don't duplicate.** Where a canonical doc stays the deep reference, point at it
   from `.horus/` instead of copying it wholesale. The lanes are concise.

5. **Mark superseded docs — only when truly superseded.** If a doc's "current state /
   next steps" role now lives in `.horus/`, add a one-line pointer at its top. But if
   `.horus/` merely *distills* a doc that stays the canonical deep reference, add no
   pointer — just point at the doc from `.horus/`. Ask before substantially rewriting
   any source doc.

## Boundaries

- When intent is genuinely unclear (real status, priorities, what shipped vs planned),
  **ask the user** rather than guess. Never invent decisions, dates, or versions —
  `decisions.md` in particular: only record a decision the docs actually state with
  reasoning; leave it empty rather than manufacturing one.
- Edit scope is `.horus/**`, plus — with care and consent — a one-line pointer atop a
  superseded source doc.
"""


_EXECUTION_SKILL = """\
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
"""


SKILLS: tuple[Skill, ...] = (
    Skill("horus-consolidate", 8, _CONSOLIDATE_SKILL),
    Skill("horus-distill-history", 2, _DISTILL_HISTORY_SKILL),
    Skill("horus-infer", 2, _INFER_SKILL),
    Skill("horus-execution", 4, _EXECUTION_SKILL),
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
        for s in SKILLS
    ]


def missing_or_stale(project_root: Path, *, target: str = "claude") -> list[Skill]:
    """Bundled skills not installed at project scope, or installed at an older version."""
    out: list[Skill] = []
    for skill in SKILLS:
        path = skill_path(skill, project_root, target=target)
        if not path.exists():
            out.append(skill)
            continue
        current = installed_version(path.read_text(encoding="utf-8"))
        if current is not None and current < skill.version:
            out.append(skill)
    return out


def skill_findings(project_root: Path, *, targets: tuple[str, ...] = ("claude",)) -> list[Finding]:
    """Doctor findings for project-scope skills."""
    findings: list[Finding] = []
    for target in targets:
        for skill in SKILLS:
            path = skill_path(skill, project_root, target=target)
            if not path.exists():
                findings.append(Finding("warn", f"{target} skill '{skill.name}' not installed (run `horus upgrade-project --apply --target {target}`)"))
                continue
            current = installed_version(path.read_text(encoding="utf-8"))
            if current is None:
                findings.append(Finding("warn", f"{target} skill '{skill.name}' present without a version marker (inspect, then use `horus skill install --target {target} --force` if it is safe to overwrite)"))
            elif current < skill.version:
                findings.append(Finding("warn", f"{target} skill '{skill.name}' outdated (v{current} < v{skill.version}); run `horus upgrade-project --apply --target {target}`"))
            else:
                findings.append(Finding("ok", f"{target} skill '{skill.name}' installed (v{current})"))
    return findings
