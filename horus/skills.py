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
  Consolidate a project's Horus continuity (`.horus/`). On a PRD-structure (v3)
  project this is a light backlog-hygiene pass over the single `PRD.md` file
  (line-count vs the cap, stale frontmatter, undistilled session notes,
  duplicate or lingering-done backlog items). On a six-lane (v2) project it
  routes shipped work into the features ledger, prunes done/stale roadmap
  items, distills session notes into the durable files, and de-duplicates
  facts that drifted across roadmap.md and features.md. Use this whenever
  wrapping up or closing out a work session in a repo that has a `.horus/`
  directory; when the user says "consolidate", "wrap up", "update continuity",
  "tidy the roadmap"/"tidy the backlog", or "close out"; right after shipping a
  capability; or whenever `.horus/` looks like it's drifted. Prefer this over
  editing `.horus/` ad hoc, because it runs `horus consolidate` for precise
  signals first and applies consistent routing rules.
---

<!-- horus-skill-version: 9 -->

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
(one note per session) and `temp/` (fleeting worker handoff notes) are
**unchanged** from six-lane projects.

### Two jobs — do not conflate them

- **Per-session close (always, bounded):** fold this session's delta into
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
   - **Stale frontmatter** — `last_updated` older than the newest `sessions/`
     note date. Refresh the content and bump the date.
   - **Undistilled session notes** — more than a dozen files directly in
     `sessions/` (excluding `README.md` and `archive/`). Move older ones to
     `sessions/archive/` (local, git-ignored, doesn't count against the cap).
   - **Duplicate backlog titles** — two `## Backlog` items whose bold
     `**Title**` text matches case-insensitively. Merge or rename one.
   - **Lingering done items** — a backlog item checked `[x]` or prefixed
     `DONE`/`Done:`. Delete the item; a `**Result … PASS**` note continuing a
     still-open item is not itself a done marker, leave those.

2. **Read `PRD.md`**, the newest `sessions/*.md` note, and any `temp/*.md`
   handoff notes awaiting review.

3. **Record this session, in `PRD.md` only** (never source, `AGENTS.md`, or
   `CLAUDE.md`):
   - Fold capabilities shipped *this session* into `## Shipped` as **one line
     each** — not a paragraph; detail lives in git history and session notes.
   - Add or update `## Backlog` items for new or changed open work.
   - Add any newly load-bearing invariant to `## Rules`, concise and
     current-state only (not a dated log — that's what `sessions/` and git
     history are for).
   - Refresh the frontmatter handoff fields and bump `last_updated`. Same
     judgment as v2 for `execution_recommendation`: `"continue-as-is — <why>"`
     for small/ambiguous/exploratory/debugging work, `"plan-execution — <why>"`
     for high-volume low-ambiguity work with a clear gate (create/update
     `execution.md` before implementation starts). The `<why>` must name what
     delegation actually buys *on this runtime* — a frontier supervisor +
     cheaper worker tiers gains context hygiene AND a cheaper tier; a single
     strong model gains mostly context hygiene, so its bar is higher. Do not
     sell supervisor review as the safeguard (reproduce the gate / bound
     checkpoints / safety-in-code are the durable ones).
   - When a `temp/` worker handoff note exists, treat it as evidence, not
     truth: review the diff/tests yourself, then fold the accepted facts into
     `PRD.md` and update `execution.md` if a phase completed.

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

## v2 six-lane projects (fallback)

No `.horus/PRD.md` — the project still uses the six lanes (`project.md`,
`roadmap.md`, `features.md`, `decisions.md`, `history.md`) plus `sessions/`
and `temp/`. `horus consolidate` reports lane-routing signals for this
structure unchanged from before.

### Two jobs — do not conflate them

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
  project. Use this when setting Horus up in an existing repo that already has docs;
  when the user says "set up horus here", "bootstrap the .horus files", "populate
  the continuity", "infer the project state", or "fill in the backlog/roadmap from
  our docs"; or right after `horus init` left placeholder content. Runs `horus infer`
  first to find the canonical docs and the empty/placeholder sections.
---

<!-- horus-skill-version: 3 -->

# Infer Horus continuity from the project's docs

Most repos already encode their state in prose (a README, a status doc, a roadmap).
This distills that into `.horus/` as the single concise source of "what is this and
what's next" — pointing at the canonical docs rather than copying them, so the two
never drift.

`horus infer` reports which structure the project uses — follow the matching
section below.

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
   - `## Backlog` — open action points as a prioritized list, bold **title**
     per item, bugs marked `[bug]`, ops chores `[ops]`.
   - `## Shipped` — **one line per capability**, not a paragraph; the deep
     detail lives in git history, not here.
   - `## Rules` — durable, current invariants only (not a dated log — if the
     docs describe *why* a rule exists or a superseded alternative, that
     rationale belongs in a `sessions/` note or `.horus/archive/`, not `PRD.md`).

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

<!-- horus-skill-version: 8 -->

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

4. **Delegate bounded phases only.** Ask native workers/subagents to implement one
   phase at a time. Use cheaper/faster tiers only for clear, narrow work; keep
   frontier-tier reasoning for architecture, risky review, and final acceptance.
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
   that the work works. If accepted, update the phase status in `execution.md`, ask
   the user before proceeding to the next phase when appropriate, and distill
   durable results at closure with `horus-consolidate`.

## Native mapping

- Claude Code: use project subagents for bounded worker/reviewer roles when useful.
  Keep Opus/frontier-equivalent work on supervision and review; use Sonnet/standard-
  equivalent workers for narrow implementation phases. Claude's cost/latency/review
  tradeoffs may differ from Codex; record the local rationale.
- Codex: use subagents or project custom agents for bounded workers/reviewers when
  useful. Map frontier to strong/high-reasoning supervision, standard to worker
  implementation, and economy to mechanical continuity or formatting updates. Codex's
  cost/latency/review tradeoffs may differ from Claude; record the local rationale.
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

<!-- horus-skill-version: 3 -->

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

## Step 1 — Read the calibration data

Run `horus capabilities --models` (add `--stdout` for JSON). It is data only and
names no model to pick. Per model it reports:

- **`tier`** (owner prior) — the role the owner assigns: design/ambiguity/verify
  gate, scoped-impl lead, mechanical, frontier, codex, …
- **`clean_count` / `closed_datums` / `total_datums`** (measured) — how many
  runs closed `clean` out of how many closed and seen total.
- **`last_outcomes`** (measured, most-recent first) — the recent track record:
  `clean` / `nudged` / `bounced` / `died`.
- **`strength` / `caution` / `guard`** (owner priors, free text) — `caution` and
  `guard` are HARD constraints on how the model may be used.

## Step 2 — Read the task shape (four axes)

- **Ambiguity** — is the goal + acceptance crisp, or exploratory/underspecified?
- **Volume** — a small localized change, or high-volume / repetitive work?
- **Runtime surface** — pure logic (tests are the gate), or a runtime/visual
  surface (server, UI, CLI UX) a human must eyeball?
- **Scope clarity** — are the files / blast-radius known and fenceable, or
  open-ended?

## Step 3 — Tier-trust ladder (data, not hardcode)

Trust is READ from the data, never pinned to a model name:

- **Proven** = many `clean` closed datums with a clean recent `last_outcomes`
  streak (today: `sonnet-5`, 10 clean). Trust it on work matching its `tier`.
  Well-matched proven work is the strongest delegation candidate.
- **Unproven** = 0–few datums (today: `haiku-4.5` = 0; `opus-4.8` / `fable-5` /
  `gpt-5.6` / `gpt-5.5` ≈ 1 each). Prefer it ONLY on well-matched, scoped work
  where a clean gate will catch a miss — you are calibrating it, so the win is
  the datum as much as the output. Never hand an unproven tier a large/loose
  task.
- **Owner flags gate the pick.** A `caution` or `guard` is a hard constraint —
  read it before matching. Live example: `gpt-5.6` carries *"token-hungry —
  needs tightly-scoped task + explicit stopping point + budget headroom"* and
  *"do not dispatch near usage ceiling"* → fine for a crisp scoped task with
  headroom; a poor fit for a large/loose task; off the table near the usage
  ceiling.
- **Keep older-but-capable models in the roster.** A prior-frontier model
  (yesterday's `gpt-5.5`/`sonnet-4.6`-style predecessor) does not stop being
  capable the day a newer model ships — it may still be the strongest AND
  cheapest fit for scoped/mechanical work. Don't drop a model from the ladder on
  recency alone: pick by capability-for-the-task, not by release date, and keep
  gathering datums on it so the ladder reflects measured reality instead of
  assumption.
- **Match tier to shape** (this mirrors the managed-block model-tier rule; the
  data tells you which concrete model fills each role now and how proven it is):
  design / ambiguity / the verify gate → the design tier (`opus-4.8`); most
  scoped implementation → the scoped-impl lead (`sonnet-5`); mechanical
  verifiable sweeps → the mechanical tier (`haiku-4.5`) — never as the judgment
  gate.

## Step 4 — Shape → mode + tier

The mode *vocabulary* belongs to the consuming skill; the shared axis is:

- Small / ambiguous / exploratory / debugging → **stay inline** (orchestration
  overhead + judgment loss dominate; delegation buys little).
- High-volume / low-ambiguity / clear gate / fenceable scope → **delegate** to
  the best-matched tier from Step 3, then reproduce the gate.
- Large AND multi-phase / spans surfaces → **delegate as a phased plan**.
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

## Step 6 — Emit the recommendation

Emit three things for the agent to APPLY (never auto-apply them):

- **mode** — in the consuming skill's vocabulary,
- **tier** — a concrete model, chosen from the data + shape,
- **verification depth** — observe-only vs observe+probe vs owner-eyeball, with
  the one deterministic gate you'll observe named explicitly.

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

Always show the data that drove it (e.g. *"sonnet-5: 10 clean, tier=scoped-impl
lead → matched"*). The agent decides and acts; you advise.

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

<!-- horus-skill-version: 1 -->

# Execution decision (in-project, subagents substrate)

Substrate: one repo, one working session, with native subagents / `horus run`
workers available. You are choosing how to execute the NEXT in-project unit of
work. This skill is the thin in-project consumer of the shared rubric — it adds
the in-project mode vocabulary and one substrate note, nothing else. It pairs
with `horus-execution`, which supervises the plan once you've decided to
delegate.

## Load the shared rubric first

Read **`../delegation-rubric/SKILL.md`** and apply its six steps (read the data,
read the task shape, the tier-trust ladder, shape→mode+tier, verification depth,
emit). Everything about reading `horus capabilities --models` and dialing
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

`mode` (`inline` | `subagent-plan`) + `tier` (a concrete model from the data) +
`verification depth` (observe-only | observe+probe | owner-eyeball, with the
gate command named). Show the calibration that drove it. Spawning the subagent,
selecting the model, and running the gate are all YOUR actions — this skill
recommends, it does not route.

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

<!-- horus-skill-version: 1 -->

# Dispatch decision (cockpit / multi-project, sessions substrate)

Substrate: an overseer/cockpit session triaging work across many registered
projects, dispatching tracked sessions via `horus run --account <alias> --path
<repo>`. Work lands back via PR + CI. This skill is the thin cross-project
consumer of the shared rubric — it adds the dispatch mode vocabulary, account
routing, and one substrate note.

## Load the shared rubric first

Read **`../delegation-rubric/SKILL.md`** and apply its six steps. All of the
calibration-data reading and the verification-depth dial live there; do not
restate or fork it.

## Mode vocabulary (this skill's output for the rubric's Step 4 axis)

- **`inline-here`** — do it in the overseer session. The rubric's "stay inline"
  case (small / ambiguous / exploratory / debugging). Note the cost: it spends
  the overseer account's context and usage on implementation — the whole point
  of the cockpit is to keep that account free to oversee, so the bar for
  `inline-here` is HIGHER than for `execution-decision`'s `inline`.
- **`dispatched-worker`** — one tracked `horus run` worker for a bounded,
  fenceable, clear-gate task. The rubric's "delegate" case.
- **`dispatched-plan`** — a phased plan (orchestrator > supervisor > worker, one
  worktree per worker) for large multi-phase work. The rubric's "delegate as a
  phased plan" case.

## Account routing (cockpit-specific, on top of the rubric)

- **Route away from the overseer account.** A dispatched worker runs on an
  ISOLATED account (a `horus account` alias → its own `CLAUDE_CONFIG_DIR` /
  `CODEX_HOME`), never the ambient overseer login — that keeps the overseer free
  AND, on a tiered setup, buys the cheaper-tier × separate-account double win.
- **Gate the target account on `horus usage check`** (`--target claude|codex`
  for the worker's agent). If the chosen account is near a closure threshold,
  pick another isolated account or hold the dispatch — and heed the rubric's
  `guard` flags (e.g. `gpt-5.6` "do not dispatch near usage ceiling"). This is a
  check you OBSERVE, not an auto-throttle.

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
(which isolated alias, or "hold — usage") + `tier` (a concrete model from the
data) + `verification depth` (observe-CI | observe-CI+probe | owner-eyeball).
Show the calibration + the usage-check result that drove it. Selecting the
account, spawning the worker, and observing CI are all YOUR actions — this skill
recommends; `horus` never auto-routes a dispatch (the hard boundary:
`research/omnigent.md`).

## v2 six-lane projects (fallback)

Structure-agnostic: this skill operates at the cockpit level across projects and
reads live `horus` data + the task shape, not any `.horus/` lane file. v2 and v3
projects are dispatched identically.
"""


SKILLS: tuple[Skill, ...] = (
    Skill("horus-consolidate", 9, _CONSOLIDATE_SKILL),
    Skill("horus-distill-history", 3, _DISTILL_HISTORY_SKILL),
    Skill("horus-infer", 3, _INFER_SKILL),
    Skill("horus-execution", 8, _EXECUTION_SKILL),
    Skill("delegation-rubric", 3, _DELEGATION_RUBRIC_SKILL),
    Skill("execution-decision", 1, _EXECUTION_DECISION_SKILL),
    Skill("dispatch-decision", 1, _DISPATCH_DECISION_SKILL),
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
