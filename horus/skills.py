"""Agent skills Horus ships and scaffolds into projects.

Like ``templates.py``, skill content lives here as strings — it ships in the wheel
with zero package-data/build config and is written into repos by ``horus init`` /
``horus skill install``.

Skills are the in-app, context-aware counterpart to the deterministic ``horus`` CLI
routines. The CLI commands (``horus consolidate`` / ``horus distill-history``) only
see the files; a skill runs *inside* the Claude Code session, so it also sees the
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

# Project-scope install location (relative to the repo root). User scope swaps the
# repo root for the home directory.
SKILLS_SUBDIR = ".claude/skills"
_VERSION_RE = re.compile(r"horus-skill-version:\s*(\d+)")


class Skill(NamedTuple):
    name: str
    version: int
    content: str

    def rel_path(self) -> str:
        return f"{SKILLS_SUBDIR}/{self.name}/SKILL.md"


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

<!-- horus-skill-version: 2 -->

# Consolidate Horus continuity

You are running *inside* the working session, so you have something the `horus`
CLI does not: the **live context of what just happened** — decisions made, work
shipped, things discussed but not yet written to `.horus/`. Use that. The CLI sees
only the files and git; you see the conversation too. Fold both in.

## Steps

1. **Get the deterministic signals.** Run `horus consolidate` (optionally
   `--path <repo>`). It reports candidates it can detect from the files alone:
   roadmap↔features overlaps, done-but-unshipped roadmap items, session summaries to
   distill, and missing lanes. Treat these as leads, not gospel — verify each.

2. **Read the lanes.** Read `.horus/project.md`, `roadmap.md`, `features.md`,
   `decisions.md`, `history.md`, and any `sessions/*.md`. If `docs/routines.md`
   exists, it holds the full routing contract; if it's absent, the rules in this
   skill are authoritative.

3. **Apply the routing rules**, editing **`.horus/**` only** (never source files,
   never `AGENTS.md`/`CLAUDE.md`):

   - **Ship → ledger.** For each done roadmap action point that completed a
     shippable capability, close it in `roadmap.md` and add/update the matching row
     in `features.md` (move Planned/In-progress → Shipped; stamp the version if the
     repo records one, else leave blank). Capture anything shipped *this session*
     that isn't on disk yet.
   - **De-duplicate across lanes.** Where the same item sits in both `roadmap.md`
     and `features.md`, keep the *action points* in `roadmap.md` and the *capability
     status* in `features.md`. Make the split explicit with a cross-reference each
     way: put a literal `→ features.md` pointer in the roadmap item, and an `action
     points → roadmap.md` note on the features row. That pointer is the marker that
     the item was *intentionally* split (both `horus consolidate` and a future reader
     rely on it), not a leftover duplicate. No fact maintained in two places.
   - **Prune.** Drop done/obsolete roadmap items — they live in features/history/git
     now. A roadmap is "what's next", not a completed log.
   - **Distill sessions.** Fold durable content from `sessions/*.md` into the lanes
     (a decision → `decisions.md`, a lesson → `history.md`, a shipped thing →
     `features.md`), then remove or mark the distilled summary.
   - **Record fresh context.** Decisions, lessons, and shipped capabilities from the
     current session that belong in the lanes but aren't written yet — add them.

4. **Keep lanes pure.** No tasks in `features.md`; no shipped packages lingering in
   `roadmap.md`; no open issues in `history.md`; no changelog in `project.md`. If
   `history.md` has grown into a verbatim log/changelog rather than curated lessons,
   that's a `horus-distill-history` job — flag it rather than fixing it here.

5. **Verify.** Re-run `horus consolidate`. An overlap clears once you've split the
   item *and* added the cross-reference — the `→ features.md` / `→ roadmap.md` pointer
   is how the tool knows a shared name is an intentional split, not a duplicate. An
   in-progress or planned item that legitimately lives in both lanes is *expected* to
   keep appearing until it carries that pointer; do **not** delete ledger rows or
   roadmap actions chasing zero warnings. Only done/shipped items clear by being
   pruned from the roadmap. Running the skill again on a clean tree changes nothing.

## Boundaries

- **Never invent** status, dates, versions, or decisions. When intent is unclear,
  leave the content in place and flag it for the user rather than guessing.
- Edits are confined to `.horus/**`. This is continuity maintenance, not a coding
  task — do not continue editing source as part of it.
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


SKILLS: tuple[Skill, ...] = (
    Skill("horus-consolidate", 2, _CONSOLIDATE_SKILL),
    Skill("horus-distill-history", 2, _DISTILL_HISTORY_SKILL),
    Skill("horus-infer", 2, _INFER_SKILL),
)


# --------------------------------------------------------------------------- #
# Install / inspect
# --------------------------------------------------------------------------- #

def _base_root(project_root: Path, *, user: bool) -> Path:
    return Path.home() if user else project_root


def skill_path(skill: Skill, project_root: Path, *, user: bool = False) -> Path:
    return _base_root(project_root, user=user) / SKILLS_SUBDIR / skill.name / "SKILL.md"


def installed_version(text: str) -> int | None:
    m = _VERSION_RE.search(text)
    return int(m.group(1)) if m else None


def write_skill(skill: Skill, project_root: Path, *, user: bool = False, force: bool = False) -> SkillAction:
    """Write one skill, version-aware. Upgrades on a newer bundled version; leaves a
    same-or-unknown-version file untouched unless ``force`` (so we don't clobber user
    edits or downgrade)."""
    path = skill_path(skill, project_root, user=user)
    label = f"{skill.name} ({'user' if user else 'project'})"
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
    return SkillAction("created", f"created {skill.rel_path()}")


def install_skills(project_root: Path, *, user: bool = False, force: bool = False) -> list[SkillAction]:
    return [write_skill(s, project_root, user=user, force=force) for s in SKILLS]


def missing_or_stale(project_root: Path) -> list[Skill]:
    """Bundled skills not installed at project scope, or installed at an older version."""
    out: list[Skill] = []
    for skill in SKILLS:
        path = skill_path(skill, project_root)
        if not path.exists():
            out.append(skill)
            continue
        current = installed_version(path.read_text(encoding="utf-8"))
        if current is not None and current < skill.version:
            out.append(skill)
    return out


def skill_findings(project_root: Path) -> list[Finding]:
    """Doctor findings for project-scope skills."""
    findings: list[Finding] = []
    for skill in SKILLS:
        path = skill_path(skill, project_root)
        if not path.exists():
            findings.append(Finding("warn", f"skill '{skill.name}' not installed (run `horus skill install`)"))
            continue
        current = installed_version(path.read_text(encoding="utf-8"))
        if current is None:
            findings.append(Finding("warn", f"skill '{skill.name}' present without a version marker"))
        elif current < skill.version:
            findings.append(Finding("warn", f"skill '{skill.name}' outdated (v{current} < v{skill.version}); run `horus skill install`"))
        else:
            findings.append(Finding("ok", f"skill '{skill.name}' installed (v{current})"))
    return findings
