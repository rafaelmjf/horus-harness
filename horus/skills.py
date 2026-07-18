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
  Consolidate a project's Horus continuity (`.horus/`). On a PRD-structure (v3)
  project this is a light backlog-hygiene pass over the single `PRD.md` file
  (line-count vs the cap, stale frontmatter, undistilled optional recovery notes,
  duplicate or lingering-done backlog items). On a six-lane (v2) project it
  routes shipped work into the features ledger, prunes done/stale roadmap
  items, distills session notes into the durable files, and de-duplicates
  facts that drifted across roadmap.md and features.md. Use this whenever
  reaching a real continuity boundary in a repo that has a `.horus/`
  directory; when the user says "consolidate", "wrap up", "update continuity",
  "tidy the roadmap"/"tidy the backlog", or "close out"; before an
  agent/account/machine change, dispatch, pause, release, or end; or whenever
  `.horus/` looks like it's drifted. Prefer this over
  editing `.horus/` ad hoc, because it runs `horus consolidate` for precise
  signals first and applies consistent routing rules.
---

<!-- horus-skill-version: 12 -->

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
   - **Line count vs the ~250-line cap** — warns past 235, more urgently past
     250. Fix by trimming: one-line `## Shipped` entries, deleted done backlog
     items (git remembers them, no need to keep them around).
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
   - Refresh the frontmatter handoff fields and bump `last_updated`. Apply
     `execution-decision`'s need-first rubric for `execution_recommendation`:
     `"continue-as-is — <why>"`
     for small/ambiguous/exploratory/debugging work, `"plan-execution — <why>"`
     for high-volume low-ambiguity work with a clear gate (create/update
     `execution.md` before implementation starts). The `<why>` must name the
     concrete context, parallelism, or price dividend and show that it exceeds
     the fixed supervisor tax. Cross-project scope, multiple phases, and
     calibration goals are not dividends by themselves. Do not sell supervisor
     review as the safeguard (reproduce the gate / bound checkpoints /
     safety-in-code are the durable ones).
   - When a `temp/` worker handoff note exists, treat it as evidence, not
     truth: review the diff/tests yourself, then fold the accepted facts into
     `PRD.md` and update `execution.md` if a phase completed.
   - Apply the recovery test: create a local `sessions/` note only when PRD/backlog
     plus git/PR state cannot resume incomplete work, a dirty tree, an unresolved
     investigation, or an agent/account handoff. Do not create one as ceremony.

4. **Apply backlog hygiene** for whatever Step 1 flagged. This is normally
   small enough to fold into the same close — don't let the file blow the cap
   before acting on the warning.

5. **Verify.** Run `horus close --check` — it must pass. One `consolidate`
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

## v2 six-lane projects (fallback)

No `.horus/PRD.md` — the project still uses the six lanes (`project.md`,
`roadmap.md`, `features.md`, `decisions.md`, `history.md`) plus `sessions/`
and `temp/`. `horus consolidate` reports lane-routing signals for this
structure unchanged from before.

### Two jobs — do not conflate them

This skill spans two sizes of work. **Do the continuity close at real boundaries; do the
backlog pass only when the user asks for it.** Conflating them is why lanes drift:
the per-session part gets half-done because the backlog looks huge.

- **Continuity close (bounded):** capture the campaign delta and make the
  dashboard reflect it. Small and complete — only this session's delta plus the
  dashboard fields below. Steps 3–4.
- **Backlog consolidation (occasional, opt-in):** distill the *accumulated* old
  sessions, move historical done-items into features, split long-standing overlaps.
  A large, separate pass — run it only on an explicit "pay down continuity debt" /
  "consolidate the backlog" request. Step 5. The signals will report a big backlog
  (many done items / undistilled sessions); that pressure is for *this* job, not the
  continuity close — **do not try to clear it every time.**

### The dashboard contract — keep these current at EVERY close

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

### Steps

1. **Get the deterministic signals.** Run `horus consolidate` (optionally
   `--path <repo>`). It reports file-only candidates: roadmap↔features overlaps,
   done-but-unshipped items, optional recovery notes to distill, missing lanes. Leads, not
   gospel — and most belong to the backlog job (Step 5), not this close.

2. **Read the lanes.** Read `.horus/project.md`, `roadmap.md`, `features.md`,
   `decisions.md`, `history.md`, optional `execution.md`, relevant `temp/*.md`
   handoffs, and the newest `sessions/*.md` recovery note only when one exists. If
   `docs/routines.md` exists it holds the full routing contract; otherwise this skill
   is authoritative.

3. **Continuity close — record the campaign delta** (`.horus/**` only; never source,
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
   - **Recommend the execution mode for the NEXT.** Apply `execution-decision`'s
     need-first rubric: set `execution_recommendation:
     "continue-as-is — <why>"` for small, ambiguous/exploratory, debugging, or
     mostly-continuity work; set `"plan-execution — <why>"` for high-volume,
     low-ambiguity work with a clear gate (and create/update `execution.md` before
     implementation starts). The `<why>` must name the concrete dividend on this
     runtime — context avoided, useful parallelism, or lower-tier savings — and show
     that it exceeds the fixed supervisor tax. Cross-project scope, multiple phases,
     and calibration goals are not dividends by themselves. Do not sell supervisor
     review as the safeguard (reproduce the gate / bound checkpoints / safety-in-code
     are the durable ones).
   - **When a worker handoff exists** in `.horus/temp/`, use it as evidence, not as
     truth: the supervisor reviews the diff/tests, then distills accepted facts into
     durable lanes and updates `execution.md`.
   - **Use a recovery note only when needed.** If durable lanes + git/PR state cannot
     resume incomplete work, a dirty tree, an unresolved investigation, or a handoff,
     write a local `sessions/` note. Otherwise skip it.

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

### Boundaries

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
  oversized history archive) down to the curated "bumps in the road" worth carrying
  forward — the problems that bit the project and the durable lessons they forced.
  On a PRD-structure (v3) project the curated result lives in
  `.horus/archive/history.md`, with any still-load-bearing rule folded into `PRD.md`'s
  `## Rules`; on a six-lane (v2) project it's `.horus/history.md` directly. Use this
  whenever onboarding Horus into a long-running project with a big changelog; when
  the user says "distill the history", "compress the changelog", "the history file
  is too long", or "summarize the project log"; or when the curated history has grown
  into a timeline instead of a lesson set. Runs `horus distill-history` first for the
  source-log location and size.
---

<!-- horus-skill-version: 3 -->

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

3. **Apply the signal test** to every entry — same test as v2 below: keep a real
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

## v2 six-lane projects (fallback)

No `.horus/PRD.md` — the curated target is `.horus/history.md` directly, as before.

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

### Boundaries

- Only compress what the log records — **never invent** incidents, dates, or causes.
- Edit `.horus/history.md` (and the one-line pointer on the source log); nothing else.
"""


_INFER_SKILL = """\
---
name: horus-infer
description: >-
  Bootstrap or refresh a project's Horus continuity (`.horus/`) by distilling the
  project's own canonical docs — README, status/roadmap files, CLAUDE.md/AGENTS.md,
  and linked docs — into `.horus/`: the PRD-structure `PRD.md` skeleton (Vision /
  Backlog / Shipped / Rules) on a v3 project, or the six-lane structure on a v2
  project. Use this when setting Horus up in an existing repo that already has useful docs;
  when the user says "set up horus here", "bootstrap the .horus files", "populate
  the continuity", "infer the project state", or "fill in the backlog/roadmap from
  our docs". A blank scaffold is valid until a real use case or evidenced docs exist.
  Runs `horus infer` first to find canonical docs and empty/placeholder sections.
---

<!-- horus-skill-version: 4 -->

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

2. **Read the canonical docs and follow their pointers** — README → status/roadmap →
   CLAUDE.md/AGENTS.md → linked docs like `docs/*.md`. Build a real model of the
   project before writing anything.

3. **Distill into `PRD.md`**, one file, each section concise:
   - Frontmatter: `status`, `current_focus`, `next_action`, `next_prompt`,
     `execution_recommendation`, `last_updated`.
   - `## Vision` — what the project is, its shape, and explicit out-of-scope
     boundaries.
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
   wholesale. Keep the whole file well under the ~250-line cap — `horus
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
- Edit scope is `.horus/PRD.md`, plus — with care and consent — a one-line
  pointer atop a superseded source doc.

## v2 six-lane projects (fallback)

No `.horus/PRD.md` — infer into the six lanes as before.

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

### Boundaries

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
  Use this when the project's `execution_recommendation` (in `PRD.md` on a v3
  project, `roadmap.md` on a v2 project) says `plan-execution`, when the user
  asks to split a feature into phases, spawn implementation workers/subagents,
  prepare worker handoff notes, or review worker output before continuing to
  the next phase. It keeps `.horus/execution.md` fluid, uses `.horus/temp/` for
  fleeting worker notes, and distills durable outcomes back into `PRD.md` (v3)
  or roadmap/features/decisions/history (v2) at closure.
---

<!-- horus-skill-version: 13 -->

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

## Confirm delegation already earned its cost

Before creating `execution.md` or a worker handoff, apply `execution-decision` and
its shared rubric. Define the bounded unit and require a concrete dividend that
exceeds the fixed brief/review/gate/merge/closure tax. Do not enter this workflow
merely because work spans projects or phases, or to collect a model datum.

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

1. **Read the continuity.** On a PRD-structure (v3) project, read `.horus/PRD.md`
   (vision/backlog/shipped/rules + the frontmatter handoff fields) and
   `execution.md`. On a six-lane (v2) project, read `.horus/project.md`,
   `roadmap.md`, `features.md`, `decisions.md`, `history.md`, and `execution.md`.
   Either way, review relevant `.horus/temp/*.md` handoff notes only when an
   execution plan is active — that directory is unchanged across both structures.

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

## v2 six-lane projects (fallback)

Everything above is structure-agnostic — phases, delegation judgment, handoff notes,
and `execution.md` itself work the same regardless of whether the project uses
`PRD.md` or the six lanes. The one structure-dependent step is reading the
continuity at the start (Step 1): a v2 project has no `PRD.md`, so read
`.horus/project.md`, `roadmap.md`, `features.md`, `decisions.md`, `history.md`, and
`execution.md` instead — the original six-lane reading list, unchanged. Distilling
durable results at closure (Step 6) likewise goes back to those lanes via
`horus-consolidate`'s v2 path rather than into `PRD.md`.

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

<!-- horus-skill-version: 9 -->

# Delegation rubric — shared calibration + verification logic

Single source of truth for the delegation-decision framework. Both
`execution-decision` (in-project, subagents substrate) and `dispatch-decision`
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
for accounting.

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

**When the mode is a dispatched one** (anything that spawns a tracked worker
rather than staying inline — `dispatched-worker`/`dispatched-plan` in
`dispatch-decision`'s vocabulary, `subagent-plan` in `execution-decision`'s),
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

## v2 six-lane projects (fallback)

This rubric is **structure-agnostic** — it reads live `horus capabilities
--models` data and the task shape, not any `.horus/` lane file — so v2
(six-lane) and v3 (`PRD.md`) projects consume it identically. Nothing here
changes with the continuity structure.
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
  Decide HOW to execute an in-project task on the Claude/Codex subagents
  substrate: recommend `inline` vs `subagent-plan`, a model tier, and a
  verification depth. Use this at the planning boundary of a feature or fix
  inside one repo — when `execution_recommendation` needs setting, when weighing
  whether to spawn an implementation subagent/worker, or before writing an
  `execution.md` phase plan. It reads live calibration data (`horus capabilities
  --models`) through the shared delegation rubric so the recommendation reflects
  the current datums. Advisory: it EMITS a recommendation you apply — it never
  auto-selects a model or auto-spawns a worker. For cross-project cockpit
  dispatch use `dispatch-decision` instead.
---

<!-- horus-skill-version: 4 -->

# Execution decision (in-project, subagents substrate)

Substrate: one repo, one working session, with native subagents / `horus run`
workers available. You are choosing how to execute the NEXT in-project unit of
work. This skill is the thin in-project consumer of the shared rubric — it adds
the in-project mode vocabulary and one substrate note, nothing else. It pairs
with `horus-execution`, which supervises the plan once you've decided to
delegate.

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
- **`subagent-plan`** — delegate to a bounded subagent / `horus run` worker (one
  phase at a time) via `horus-execution` / `execution.md`. The rubric's
  "delegate" and "delegate as a phased plan" cases: high-volume, low-ambiguity,
  fenceable scope, clear gate. Name the tier from the data and set
  `delegation_basis` to what delegation actually buys here (context hygiene, and
  on a tiered runtime a cheaper implementation tier).

Feed the recommendation into `execution_recommendation` (`continue-as-is` ≈
`inline`; `plan-execution` ≈ `subagent-plan`) and, when delegating, into the
`execution.md` phase's `worker_tier` / `delegation_basis`.

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

`mode` (`inline` | `subagent-plan`) + `tier` (a vendor-neutral capability point —
`low|medium|high|frontier` — resolved to a concrete provider+model only at the
consent envelope, from the neutral-tier map + live capacity,
never defaulted from the label) + `verification depth`
(observe-only | observe+probe | owner-eyeball,
with the gate command named). For `subagent-plan`, include the exact agent/model/
effort/account/usage+reset/task/attempts/dividend-or-owner-override/gate consent
envelope, mark it awaiting explicit owner approval, and ask again on any
fallback or extra attempt. Spawning the subagent, selecting the model, and running
the gate are all YOUR actions — this skill recommends, it does not route.

## v2 six-lane projects (fallback)

Structure-agnostic except where the recommendation lands: on a v3 project the
`execution_recommendation` field is in `PRD.md` frontmatter; on a v2 (six-lane)
project it's in `roadmap.md`. The decision logic, the shared rubric, and the
modes are identical.
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

<!-- horus-skill-version: 4 -->

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

## v2 six-lane projects (fallback)

Structure-agnostic: this skill operates at the cockpit level across projects and
reads live `horus` data + the task shape, not any `.horus/` lane file. v2 and v3
projects are dispatched identically.
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

<!-- horus-skill-version: 1 -->

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

## v2 six-lane projects (fallback)

The fleet-review command may report remote continuity unavailable for a project
that has no PRD yet. If that project is selected, read its remote
`project.md`/`roadmap.md`/`features.md` lanes explicitly and apply the same
remote-vs-local separation. Any approved cleanup follows that project's six-lane
closure rules; migration to PRD structure is separate and opt-in.

## Close

Record only durable fleet-level decisions in the curator workspace. Do not copy
project facts into it. Refresh its PRD and add a local recovery note only if needed,
then push the checkpoint; the
next review should be reproducible from the manifest plus target remotes.
"""


_PRODUCT_AUDIT_SKILL = """\
---
name: product-audit
description: >-
  Periodic evidence-first audit of the Horus product surface itself: which
  surfaces the owner actually used since the last audit, what Claude Code /
  Codex now cover natively, and which rituals became ceremony. Use when
  `horus close` / `horus consolidate` print the product-audit staleness
  advisory, or when the owner asks "audit the product", "what should we
  retire", or "is this feature still earning its keep". Advisory only: every
  verdict is demote / defer / retire / no-change — this audit can never
  propose new features, add telemetry, or auto-archive anything. Verdicts land
  in a dated one-page receipt under `.horus/audits/`.
---

<!-- horus-skill-version: 2 -->

# Product audit — prune, never grow

You are auditing Horus itself, not a target project. The CLI supplied only the
deterministic trigger (the staleness advisory); you supply the judgment.

**Initial stamp:** if no receipt exists under `.horus/audits/` for the stamped
audit (the stamp was set when the audit feature shipped, with no verdicts
behind it), treat this run as the first real audit: widen every "since the
last audit" question to the whole live surface instead of the stamp window.

## Questions (evidence, not recall)

1. **Usage.** Which Horus surfaces did the owner *demonstrably* use since the
   last audit? Evidence means shell history the owner shows you, `.horus/`
   artifacts, git history, and a short interview — plus grepping the
   integration points for surfaces nothing references. The canonical
   integration points to grep for `horus <cmd>` references: the managed
   blocks (`CLAUDE.md`/`AGENTS.md`), hook templates (`horus/native_hooks.py`
   and installed `.claude/settings.json`), the TUI (`horus/terminal_tui.py`),
   the dashboard, bundled skills (`.claude/skills/` / `.agents/skills/`), and
   `scripts/`. A registered command referenced only by its own implementation
   counts as unreferenced. Do NOT build or propose command-usage telemetry;
   the interview + integration-point grep is the current rung.
2. **Native overlap.** What have Claude Code and Codex shipped natively since
   the stamped version that overlaps a Horus surface? Check their changelogs /
   release notes. A surface a host app now covers is a demote/retire candidate.
3. **Ceremony.** Which rituals were skipped, rubber-stamped, or felt like
   ceremony? A step everyone bypasses is evidence against the step, not the
   people.

## Verdicts — the only four

Per finding: **demote** (weaker rung: instruction instead of code),
**defer** (revisit next audit, with the reason), **retire** (propose removal —
the owner acts; nothing auto-archives), or **no-change**. New features are out
of scope for this audit by construction.

## Close the audit

- Write the receipt: `.horus/audits/<YYYY-MM-DD>-product.md` — **one page,
  never a transcript**: a verdict table (finding | verdict | one-line
  evidence), with every defer carrying the reason the next audit needs to
  re-open it. Committed, so it travels between machines; the receipt is what
  makes defers recallable and the anti-ceremony guard checkable. (Owner
  approved per-audit receipt files 2026-07-16, superseding the original
  no-new-artifact rule.)
- Update the PRD frontmatter stamp: `last_product_audit: <installed horus
  version> <today YYYY-MM-DD>` (run `horus --version` for the version). The
  stamp stays the cheap pointer; the receipt holds the verdicts.
- Retire/demote proposals still land through the owner (backlog cards, PRD
  Rules) — the receipt records the verdict, it does not act on it.
- **Anti-ceremony guard:** read the previous receipt; if it and this audit
  are both all no-change, recommend the owner lengthen the audit interval
  (e.g. 10 releases / 60 days) — note it in the receipt.

## v2 six-lane projects (fallback)

The staleness advisory reads `PRD.md` frontmatter, so it never fires on a
six-lane project. The audit itself still applies: ask the same three questions,
use the same four verdicts, and record the stamp in `project.md` frontmatter so
it carries over when the project migrates to the PRD structure.
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

<!-- horus-skill-version: 1 -->

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

## v2 six-lane projects (fallback)

Structure-agnostic: the "check existing coverage" step reads whichever
continuity structure the project uses (`.horus/PRD.md` Rules/backlog on v3,
`decisions.md`/`roadmap.md` on v2), and the accepted outcome lands in that
project's live lanes instead of `PRD.md`. Scoping, lazy evidence load, the
six-bucket attribution, and the capped cheapest-rung recommendations apply
unchanged.
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

<!-- horus-skill-version: 1 -->

# Skill audit — one skill's text vs reality

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

## Boundaries

- Advisory only: nothing is edited, demoted, or retired without the owner's
  approval of the specific diff or proposal.
- One skill per invocation; no telemetry; no new trigger machinery.

## v2 six-lane projects (fallback)

Structure-agnostic: the receipt still lands in `.horus/audits/` (the
directory is independent of PRD structure), and the fidelity check compares
each skill's v2 fallback section against the six-lane layout the project
actually uses — a skill whose fallback describes lanes the project no longer
has is a revise finding.
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
  sizing to one line. Composes the deep-research harness for the evidence pass
  rather than reinventing search. Advisory only: it PROPOSES Vision text and
  candidate backlog cards in a dated receipt under `.horus/research/`; it never
  auto-writes the Vision or auto-creates cards. Not continuous monitoring.
---

<!-- horus-skill-version: 5 -->

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

## Before you spend — confirm the envelope

This skill fans out web research (it composes the `deep-research` harness), which
is a real token spend. Before any web work, state: the intent (deepen-own-use |
broaden-adoption | both), the trigger (new-idea | pivot), the problem/space in one
sentence, the competitors you already know, and the research depth — then get the
owner's confirmation. Match depth to the question; a light comparative sweep
usually beats a full adversarial report for a product decision.

## Bake in exactly the outward trio (+ one capped check)

1. **JTBD hypothesis** — "When [situation], I want [motivation], so I can
   [outcome]", plus the current alternatives people use. A skill cannot run real
   interviews, so frame this explicitly as a hypothesis to validate, not a
   finding.
2. **Competitive teardown** — 3-6 named competitors in a grid: does-well / gap /
   positioning / price, each row backed by a fetched URL. This is where
   `deep-research`'s fetch+verify does the work — invoke it, do not rebuild it.
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
Sources: [URLs from deep-research]
```

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

## v2 six-lane projects (fallback)

No `.horus/PRD.md` — run the scan the same way and write the same receipt under
`.horus/research/`. Feed the Vision draft into `project.md` and candidate items
into `roadmap.md` at the owner's discretion, following that project's six-lane
closure rules.
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

<!-- horus-skill-version: 3 -->

# roadmap-branches — the divergence tree, not a merged roadmap

You are producing the **divergent** half of the breathing loop: a tree of
alternative roadmaps the owner chooses between. The single most important rule:
**never collapse the tree into one merged roadmap** — merging is the owner's
convergence decision, and pre-merging it destroys exactly the choice this skill
exists to surface.

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
- **Prior branch-tree receipts** (earlier trees under `.horus/research/`) — a
  re-baseline consumes its predecessors: carry forward unresolved branches,
  unscoped imports, and owner verdicts recorded there, re-justified against the
  CURRENT intent — never blindly inherited, never silently dropped. (Calibration
  2026-07-17: an owner rescope lived only in a prior receipt and a fresh run
  missed it entirely.)

## The deliverable — one dated receipt, fixed template

Write `.horus/research/<YYYY-MM-DD>-roadmap-branches-<slug>.md` with exactly these
sections, then STOP for the owner to pick:

1. **Where we are.** Narrative prose, per facet, each with a life-stage judgment —
   converged (DoD met) / built-but-unproven / active frontier / steady-state — and
   an honest one-line overall position at the end. Not bullets; a fresh reader must
   understand the project's situation without the conversation.
2. **Where the market is.** Distilled FROM the receipt (cite it): the landscape in
   shells, then ONE verdict, then the risks. **State each fact exactly once** — if
   a point appears in two sections, delete one.
3. **The tree.** A small ASCII tree: root = the position in two lines, one child
   per branch (including the speculative ones), each with its facet target and a
   one-word posture tag (primary/secondary/filler/park is the *recommendation*,
   not a decision).
4. **The branches.** For EACH branch:
   - **Thesis** — why this direction, argued through the pinned intent.
   - **Market position** — the required line: "*this exists already but misses X;
     you already have Y but still miss Z; therefore these items*". Market evidence
     appears INSIDE every branch, not only in section 2.
   - **Numbered roadmap** — ordered items mixing existing cards and new proposals.
     Every item carries enough depth that `scope-cards` can populate a card without
     new thinking: why, the concrete how (a protocol, a first step), suspected weak
     points, and non-goals. A second-order item (work that depends on findings that
     do not exist yet) is named as such: "findings become their own cards".
   - **Convergence criterion** — when is this branch done, plus a rough cost.
   - **Implied Vision edits** — the facet DIFF this branch entails:
     add / rename / retire / promote-proven-exploration against a NAMED existing
     facet, with draft definition-of-done text for adds/rescopes. Never a
     wholesale table rewrite.
5. **Speculative branches (1-2).** Directions with NO current facet, derived from
   position + market + intent: the gap it names, the idea, the cheapest PoC, why it
   fits the intent, the risk. These are the "imaginary visions" — the tree is
   incomplete without at least one. At least one candidate must RE-TEST the
   Vision's out-of-scope list against fresh usage evidence — an out-of-scope line
   is a hypothesis too. (Calibration: both 2026-07-17 runs missed the owner's
   strongest live direction, scheduled autonomous dispatch, because it sat behind
   an out-of-scope declaration neither run questioned.)
6. **Recommendation, held loosely.** Primary / secondary / filler / park across the
   branches, one paragraph of reasoning. The owner reorders freely.

## Three disciplines that make the tree trustworthy

- **Re-justify the existing backlog — inherit nothing.** Every open card either
  earns its place inside some branch or gets explicit push-back (demote / defer /
  retire candidate, with the reason argued through the intent). Merely ordering the
  inherited backlog is this skill's known failure mode.
- **Claims discipline.** Every "X is missing / weak / better" names its
  comparison baseline: what exists today, and why it is insufficient for the
  intent. No claim without its baseline.
- **Every candidate exits with a disposition.** Anything considered — market-
  receipt candidate items, prior-tree branches, existing cards — either lands in
  a branch or is dropped WITH the stated reason. Silent omission is the failure
  mode (calibration 2026-07-17: one run silently omitted a receipt candidate the
  sibling run had dropped with a reason).

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

## v2 six-lane projects (fallback)

No `.horus/PRD.md` — build the brief from `project.md` (vision) + `roadmap.md`
(open items) + `features.md` (shipped). There is no facet table, so branches state
their implied direction changes against `project.md`'s vision prose, and roadmap
items become proposed `roadmap.md` entries. The receipt, the tree, the re-justify
and claims disciplines, and the advisory boundary are unchanged.
"""


_SCOPE_CARDS_SKILL = """\
---
name: scope-cards
description: >-
  Populate a chosen roadmap branch (or any approved direction) into fully
  SELF-SUFFICIENT backlog card drafts — frontmatter plus context, concrete how,
  acceptance, and non-goals — so a fresh agent session can pick any card up and
  start with the same understanding, needing nothing from the originating
  conversation. Step 4 of the pathfinder flow, also standalone ("scope this
  card", "populate cards for this direction"). Also drafts the branch's implied
  Vision facet edits and the demote/defer/retire diffs for existing cards the
  branch pushed back on. Advisory: presents every draft first; the owner approves
  per item; only approved items are written.
---

<!-- horus-skill-version: 2 -->

# scope-cards — from a chosen branch to a fresh-agent-ready backlog

You are transcribing an approved direction into cards that pass one bar:

> **The self-sufficiency test: a fresh agent session, given only `PRD.md` and this
> card, can start the work correctly — same understanding, no access to the
> conversation that produced it.**

## Input

One chosen branch from a `roadmap-branches` receipt (or an owner-approved
direction of equivalent depth). Each item needs why / how / suspected weak points /
non-goals already argued. **If an item arrives thin, do not silently invent the
missing depth** — flag it and resolve it with the owner (or send it back through
`roadmap-branches`) before drafting its card.

## Card draft template

Frontmatter: `status: open`, `priority`, `tier`, `vision_facet` (matched to a
`## Vision` table facet), `phase` (`converge` default; `explore` for divergent
bets), `created`. Body:

- **Why** — the context paragraph carrying the branch's reasoning, INCLUDING the
  market-position line ("exists but misses X / we have Y but miss Z"), so the card
  survives without the receipt.
- **How** — the concrete protocol or first step, specific enough to begin from.
- **Acceptance** — one testable line. `phase: explore` cards instead carry an exit
  line: the cheap PoC and the explicit verdict it must end in (adopt / promote /
  drop — dying cheap is a valid success).
- **Non-goals** — what this card deliberately does not do.
- **Source** — the receipt path + branch name.

**Second-order items are never pre-invented:** when work depends on findings that
do not exist yet (e.g. gap cards a verification probe will produce), scope the
probe card and state "each finding becomes its own card" —
do not fabricate the findings.

## Alongside the new cards, draft the branch's edits

- **Existing-card diffs** — the demote / defer / retire push-back the branch made,
  as explicit per-card proposals (field change or archival, with the reason).
- **Vision facet diff** — exact replacement definition-of-done text per touched
  facet (add / rename / rescope / retire), never a wholesale table rewrite.
- **Vision-branch umbrella** — when the direction spans multiple cards and should
  be judged as a unit (every `explore` direction; any branch the owner may later
  promote or drop whole), draft a thin `vision-branch-*` umbrella card (thesis,
  exists-vs-gaps map, ordered children, convergence criterion) and stamp each
  child `branch: <umbrella-name>`, per the PRD structure contract. Keep the
  umbrella thin — agents-first, minimal overhead; never mirror child status
  into it.

## Gate, then write

Present ALL drafts — new cards, existing-card diffs, Vision edits — as concrete
options plus a free-text alternative, and let the owner
approve, amend, or drop each item individually. Only then write the approved items: new cards as files
under `.horus/backlog/`, facet edits into `## Vision`, existing-card changes in
place. Owner rejections and rescopes of EXISTING cards are written into that
card's `## Reviews` at decision time — a verdict that lives only in a receipt or
the conversation does not bind future planning runs (calibration 2026-07-17).
Anything not approved stays unwritten; say so.

## Deliberately omit

- No implementation, no dispatch, no execution planning (`execution-decision` owns
  the execute-vs-delegate call; `horus-execution` owns phase plans).
- No new receipt — the branch receipt plus the written cards are the trace.
- No priority invention: inherit the branch order; the owner sets priorities.

## v2 six-lane projects (fallback)

No card files — each approved item becomes a `roadmap.md` entry carrying the same
depth inline (why / how / acceptance / non-goals, one compact block per item), and
Vision edits go to `project.md` prose at the owner's discretion, following that
project's six-lane closure rules. The self-sufficiency bar and the per-item owner
gate are unchanged.
"""


_PATHFINDER_SKILL = """\
---
name: pathfinder
description: >-
  Owner-invoked, guided divergence→convergence re-baseline of a project's
  direction — the thin WORKFLOW that sequences individually-invocable steps: pin
  the intent (deepen own-use vs broaden adoption vs both), pin a position brief
  (`horus consolidate` read-out), scan the market (`market-scan`, which composes
  `deep-research`), build the divergence tree of alternative roadmaps
  (`roadmap-branches`), then populate the chosen branch into self-sufficient
  cards (`scope-cards`). Works the SAME on a brand-new repo and a long-running
  one (it scouts the route ahead and reports; it never builds the road). Use
  when the owner says "pathfinder", "kickstart", "re-baseline", "where should
  this project go next", "reset the roadmap", or "onboard this project onto
  facets". Advisory and gated: every step hands the owner a proposal and each
  step is also callable standalone — pathfinder adds only sequencing, gates, and
  the receipts handoff; nothing is ever written without approval. Confirm a
  token envelope before any web work. Not continuous monitoring.
---

<!-- horus-skill-version: 4 -->

# pathfinder — the re-baseline workflow (thin by design)

You are running the project's **breathing loop** once, on demand: research →
**divergence** (a tree of alternative roadmaps) → the owner picks → a scoped
backlog → later **convergence** (the `horus consolidate` read-out trims the fat).
You are a pathfinder: you **scout the route ahead and report it** — you do not
build the road. This runs the SAME whether the project is brand-new (no facet
table yet — the onboarding fork inside `roadmap-branches`) or years old (a genuine
re-baseline); the name is deliberately age-agnostic.

v2 is **genuinely thin**: every stage is its own skill or CLI signal, and
pathfinder contributes NO analysis of its own — only the sequencing, the owner
gates between steps, and passing each step's receipt into the next. (v1 kept the
direction/card judgment inline and unstructured, and its output quality drifted;
the depth requirements now live in the step skills, where `skill-audit` can hold
each one against reality separately.)

| Step | Owner's question | Owned by |
|---|---|---|
| 0 | what is this re-baseline FOR? | pathfinder (intent gate) |
| 1 | where are we? | `horus consolidate` read-out → pinned brief |
| 2 | where is the world? | `market-scan` (composes `deep-research`) |
| 3 | which directions could we take? | `roadmap-branches` (the divergence tree) |
| 4 | what exactly do we do on the chosen one? | `scope-cards` (self-sufficient drafts) |

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
`market-scan` framing, the `roadmap-branches` theses, and the `scope-cards`
context paragraphs. Also settle here whether the owner wants per-step gates
(default) or a pre-authorized straight-through run.

## Before you spend — confirm the token envelope

Step 2 fans out web research. Before any web work, state: the intent (from Step
0), the trigger (re-baseline | onboarding), the project in one line, the
directions you already suspect, and the research depth — then get the owner's
confirmation. A light comparative sweep usually beats a full adversarial report
for a direction call. A fresh, still-valid receipt may be reused instead of a new
scan — say so explicitly and get a nod; that nod already carries the owner's
reaction to the evidence, so it REPLACES Step 2's STOP (do not re-gate reused
evidence — calibration 2026-07-17). If the owner only wants the inward pass,
skip the scan and let `roadmap-branches` mark its tree inward-only.

## The flow

1. **Position brief (no spend).** Read `## Vision` (or note the facet table's
   absence), the active cards with their `vision_facet`/`phase` stamps, and
   `## Shipped`; run `horus consolidate` for the deterministic convergence
   read-out. Write the pinned brief — SHIPPED / VISION + audience (per Step 0) /
   OPEN facet coverage — a HARD CONSTRAINT passed into every later step so the
   research stays anchored to what the project already is and who it is for.
   STOP for the owner to confirm the brief (unless straight-through).
2. **`market-scan`** with the intent + brief, under the confirmed envelope. Its
   dated receipt is the outward evidence. STOP for the owner to react (already
   satisfied when the receipt was reused under the envelope nod — proceed).
3. **`roadmap-branches`** consuming the brief + receipt (+ prior branch-tree
   receipts when they exist) → the branch-tree
   receipt: per-facet position, market shells → verdict → risk, one branch per
   direction (each with a market-position line, a numbered roadmap, a convergence
   criterion, implied Vision edits), 1-2 speculative branches, explicit
   push-back on existing cards, and a held-loosely recommendation. The
   **Onboarding fork** lives there: no facet table → propose the initial facet
   set and offer to stamp existing cards. STOP: the owner picks branch(es).
4. **`scope-cards`** on the chosen branch → fully populated self-sufficient card
   drafts + the branch's Vision facet diff + existing-card demote/defer/retire
   diffs. The owner approves per item; only approved items are written.
5. **Hand off.** Approved cards and edits are in place via the normal paths;
   anything the owner deferred stays unapplied — say so. Later, **convergence is
   a separate session**: usage evidence accumulates, the `horus consolidate`
   read-out trims the fat; re-run pathfinder only when a real re-baseline is
   needed again.

## Deliberately omit

- No new CLI subcommand, module, roles, or multi-file ceremony — the
  deterministic signals already exist; pathfinder is pure sequencing over them.
- No analysis inside pathfinder itself — depth belongs to the step skills where
  it can be audited and calibrated one skill at a time.
- No token estimate beyond stating the depth and getting confirmation — let
  `market-scan`/`deep-research` own the actual fan-out.
- No continuous monitoring (that always-on category is out of scope).

## v2 six-lane projects (fallback)

No `.horus/PRD.md` — the same sequence over the six-lane files: the brief comes
from `project.md`/`roadmap.md`/`features.md`, `roadmap-branches` states direction
changes against `project.md`'s vision prose, and `scope-cards` writes approved
items as `roadmap.md` entries, following that project's closure rules. The Step 0
intent gate, the pinned brief, and the advisory gate-at-every-step boundary are
unchanged.
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
  (mode/account/tier/depth), `scope-cards`/`pathfinder`/`roadmap-branches`
  (ready-gate), and the `horus envelope`/`schedule`/`run`/`supervise`/`notify`
  commands; it never re-implements them. Advisory and owner-gated at EVERY step:
  it proposes, the owner confirms each gate. It never selects a model, routes an
  account, or launches anything without the explicit consent envelope. Not
  continuous monitoring; single-machine, non-recurring dispatch only.
---

<!-- horus-skill-version: 1 -->

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
Judge scope with the self-sufficiency test: a `converge` card with a `vision_facet`,
one testable acceptance line, and `surface`/`parallel` stamps. If thin, STOP and route
through `pathfinder` → `roadmap-branches` → `scope-cards` to make it self-sufficient
first — a fresh unattended worker gets only the card, so the card must carry the whole
brief. `phase: explore` cards are not dispatch candidates.

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

## v2 six-lane projects (fallback)

The contract is structure-agnostic — it dispatches into a *target* repo whatever that
repo's continuity shape. On a v2 six-lane target the only differences are in steps 1
and 3: discovery reads the target's `roadmap.md` open action points instead of
`backlog/` cards, and the ready-gate judges a roadmap item's scope (does it name a
concrete surface + acceptance?) rather than a card's `vision_facet`/acceptance
frontmatter — routing a thin one through `scope-cards`, which writes it back as a
`roadmap.md` entry under that project's rules. Envelope, schedule, dispatch, supervise,
notify, and the owner-gated-at-every-step boundary are identical.
"""


_INLINE_BATCH_SESSION_SKILL = """\
---
name: inline-batch-session
description: >-
  The working posture for an INLINE-BATCH session: implement and ship several
  self-contained backlog cards in a row in one warm session, and HOLD every Horus
  continuity write (PRD edits, card status/archive, session notes, `close`) until a HARD
  boundary actually arrives — never on merely finishing the cards. Loaded automatically
  when a session is launched in `inline-batch` mode (it does not depend on the model
  remembering a rule). Keep following it whenever you ship multiple cards inline.
---

<!-- horus-skill-version: 2 -->

# Inline-batch session

You are in **inline-batch** mode: implement and ship several self-contained backlog cards
in a row in THIS one warm session (inline, no dispatch), and **hold all Horus continuity
ceremony until a hard boundary actually arrives**. This posture is loaded at launch so it
holds across every account and model — not left to memory.

Why: dispatching each card to a fresh worker re-pays a large cold-start context-reload cost
every time, and consolidating continuity between cards just churns prose the next card — or
the eventual release — rewrites. One warm session amortizes the codebase context; one
consolidation at the boundary captures them all. (Measured:
`research/2026-07-17-delegation-cost-finding.md`.)

## Every card — delivery safety (never deferred, never skipped)

- Branch → PR → **reproduce the required gate on the EXACT commit** (a required CI check
  green on that SHA) + **one live probe** of the changed surface → commit, push, merge.
- A merged PR is the durable delivery; git + the PR are the receipt, so it needs no
  continuity write to be safe. Safety lives in the gate, not in the prose.
- New work you spec mid-session gets a card FILE (it is the spec, and it travels in the
  PR) — but do not flip its `status:` or archive it yet (see below).

## Hold ALL continuity until a hard boundary

Defer every one of these — none is needed until a boundary actually arrives:

- `PRD.md` frontmatter / Shipped / Rules edits, and the ~250-line trim.
- `horus backlog ship` / card archiving and `status:` changes. (Solo inline needs no
  `claim` either — claiming only guards against parallel agents contending for a card.)
- Local `sessions/` notes and any `horus close`.

Between cards the entire state is pushed git + open/merged PRs. `horus close --check`'s
"delivery commits pending" line is a reminder, not a demand to close.

## What IS a hard boundary — and what is NOT

Consolidate ONLY when one of these actually happens:

- The owner **ends or pauses** the session.
- An **agent / account / machine handoff**.
- A **version release** of what you shipped — the natural consolidation point (below).
- A **dispatch** whose receiving agent needs the durable continuity to act. If the brief +
  base SHA already carry everything, the dispatch is not a boundary for continuity.

**NOT a boundary — never trigger the consolidation on these alone:** finishing the batch,
merging the last PR, writing a wrap-up message, or being asked a follow-up while more
queued work (e.g. a pending release) remains. **Do not manufacture a boundary:** if the
owner is still engaged and work is queued, keep continuity uncommitted and keep going.

## Align the consolidation with a release when one is near

If the cards you shipped are headed for a version release, fold the continuity into the
SAME pass as the release closure — write the final "released in vX" Shipped lines once.
Writing provisional "merged, not yet released" prose now and rewriting it at release is the
exact double-ceremony this mode exists to avoid.

## At the boundary (once)

Run the `horus-consolidate` skill and fold the whole batch in: refresh frontmatter, ship
every card (`horus backlog ship <card> --pr N --sha SHA`, which archives it), move each to
`## Shipped` (one line), record any newly load-bearing Rule, trim to the line cap, then
`horus close --commit --push`. One pass; do not chase warnings to zero.

## v2 six-lane projects (fallback)

Identical posture; the single boundary consolidation updates `roadmap.md` / `features.md` /
`decisions.md` instead of `PRD.md`, following that project's closure rules. The per-card
delivery-safety rungs and the hold-continuity-to-a-hard-boundary rule are unchanged.
"""


SKILLS: tuple[Skill, ...] = (
    Skill("horus-consolidate", 12, _CONSOLIDATE_SKILL),
    Skill("horus-distill-history", 3, _DISTILL_HISTORY_SKILL),
    Skill("horus-infer", 4, _INFER_SKILL),
    Skill("horus-execution", 13, _EXECUTION_SKILL),
    Skill("delegation-rubric", 9, _DELEGATION_RUBRIC_SKILL),
    Skill("execution-decision", 4, _EXECUTION_DECISION_SKILL),
    Skill("dispatch-decision", 4, _DISPATCH_DECISION_SKILL),
    Skill("fleet-curation", 1, _FLEET_CURATION_SKILL),
    Skill("product-audit", 2, _PRODUCT_AUDIT_SKILL),
    Skill("process-retrospective", 1, _PROCESS_RETROSPECTIVE_SKILL),
    Skill("skill-audit", 1, _SKILL_AUDIT_SKILL),
    Skill("market-scan", 5, _MARKET_SCAN_SKILL),
    Skill("roadmap-branches", 3, _ROADMAP_BRANCHES_SKILL),
    Skill("scope-cards", 2, _SCOPE_CARDS_SKILL),
    Skill("pathfinder", 4, _PATHFINDER_SKILL),
    Skill("cockpit-autonomous-dispatch-contract", 1, _COCKPIT_DISPATCH_SKILL),
    Skill("inline-batch-session", 2, _INLINE_BATCH_SESSION_SKILL),
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


def skill_states(project_root: Path, *, targets: tuple[str, ...] = ("claude",)) -> list[SkillState]:
    """Structured per-(agent, skill) install state for project-scope skills.

    The single detection pass; ``skill_findings`` formats these into doctor/nudge
    prose and the TUI skills viewer renders them directly. No new scanning — it
    reuses ``skill_path`` / ``installed_version`` / ``SKILLS``.
    """
    states: list[SkillState] = []
    for target in targets:
        for skill in SKILLS:
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
