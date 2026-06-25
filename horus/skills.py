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

<!-- horus-skill-version: 1 -->

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
   exists, it holds the full routing contract.

3. **Apply the routing rules**, editing **`.horus/**` only** (never source files,
   never `AGENTS.md`/`CLAUDE.md`):

   - **Ship → ledger.** For each done roadmap action point that completed a
     shippable capability, close it in `roadmap.md` and add/update the matching row
     in `features.md` (move Planned/In-progress → Shipped; stamp the version if the
     repo records one, else leave blank). Capture anything shipped *this session*
     that isn't on disk yet.
   - **De-duplicate across lanes.** Where the same item sits in both `roadmap.md`
     and `features.md`, keep the *action points* in `roadmap.md` and the *capability
     status* in `features.md`, each pointing at the other. No fact in two places.
   - **Prune.** Drop done/obsolete roadmap items — they live in features/history/git
     now. A roadmap is "what's next", not a completed log.
   - **Distill sessions.** Fold durable content from `sessions/*.md` into the lanes
     (a decision → `decisions.md`, a lesson → `history.md`, a shipped thing →
     `features.md`), then remove or mark the distilled summary.
   - **Record fresh context.** Decisions, lessons, and shipped capabilities from the
     current session that belong in the lanes but aren't written yet — add them.

4. **Keep lanes pure.** No tasks in `features.md`; no shipped packages lingering in
   `roadmap.md`; no open issues in `history.md`; no changelog in `project.md`.

5. **Verify.** Re-run `horus consolidate` — the candidates it flagged should now be
   resolved. Running the skill again on a clean tree should change nothing.

## Boundaries

- **Never invent** status, dates, versions, or decisions. When intent is unclear,
  leave the content in place and flag it for the user rather than guessing.
- Edits are confined to `.horus/**`. This is continuity maintenance, not a coding
  task — do not continue editing source as part of it.
- Bump `last_updated` front matter on lanes you change.
"""


SKILLS: tuple[Skill, ...] = (
    Skill("horus-consolidate", 1, _CONSOLIDATE_SKILL),
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
