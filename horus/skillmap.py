"""Read-only skill map: every agent skill installed on this machine, across scopes.

The pain this addresses: the same skill ends up installed N times across projects ×
accounts × user scope with no visibility ("which instructions/skills are active here,
for this agent?"). This module only *observes* — it never installs, syncs, or deletes.

Scopes scanned (all machine-local):

- ``project`` — each registered project's ``.claude/skills/`` + ``.agents/skills/``.
  These are the only entries visible cross-machine (they travel with the repo).
- ``user`` — the ambient ``~/.claude/skills/`` and ``$CODEX_HOME/skills`` (default
  ``~/.codex/skills``) directories every non-isolated session loads.
- ``account`` — each Horus-managed isolated login dir's ``skills/``
  (``~/.horus/accounts/<agent>-<alias>``), which replaces the user scope when a
  session runs under that account.

Identity: skills are grouped by directory name (the slug agents trigger on) — the
same name in two scopes is the same skill for presence purposes. Provenance splits
in two: **Horus-bundled** names (``skills.SKILLS``) get version/staleness verdicts
against the installed CLI; everything else is **foreign** — presence + location only,
never judged (Horus cannot know a third-party skill's latest version).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from horus import config, skills

_DESCRIPTION_RE = re.compile(r"^description:\s*(.+)$", re.MULTILINE)
_DESCRIPTION_MAX = 160


@dataclass(frozen=True)
class SkillInstance:
    name: str            # directory slug — the grouping identity
    path: str            # SKILL.md location
    scope: str           # "project" | "user" | "account"
    agent: str           # "claude" | "codex"
    owner: str           # project name / account alias; "" for user scope
    version: int | None  # horus-skill-version marker, when present
    description: str     # frontmatter description (truncated), or ""


def _read_meta(skill_md: Path) -> tuple[int | None, str]:
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None, ""
    version = skills.installed_version(text)
    description = _frontmatter_description(text[:4096])
    if len(description) > _DESCRIPTION_MAX:
        description = description[: _DESCRIPTION_MAX - 1] + "…"
    return version, description


def _frontmatter_description(head: str) -> str:
    """The frontmatter ``description:`` value, following a YAML block scalar
    (``>-``/``|`` etc. — the common shape in SKILL.md files) onto its indented
    continuation lines. Inline values are returned as-is."""
    m = _DESCRIPTION_RE.search(head)
    if not m:
        return ""
    value = m.group(1).strip()
    if value not in (">", ">-", ">+", "|", "|-", "|+"):
        return value.strip("\"'")
    lines = []
    for line in head[m.end():].splitlines()[1:]:
        if line.strip() and not line.startswith((" ", "\t")):
            break  # next top-level frontmatter key (or ---) ends the scalar
        if not line.strip():
            break  # first blank line is plenty for a summary
        lines.append(line.strip())
    return " ".join(lines)


def _scan_dir(base: Path, *, scope: str, agent: str, owner: str) -> list[SkillInstance]:
    """Every ``<base>/<name>/SKILL.md`` as one instance. Missing/unreadable → []."""
    instances: list[SkillInstance] = []
    try:
        entries = sorted(p for p in base.iterdir() if p.is_dir())
    except OSError:
        return instances
    for entry in entries:
        skill_md = entry / "SKILL.md"
        if not skill_md.is_file():
            continue
        version, description = _read_meta(skill_md)
        instances.append(SkillInstance(
            name=entry.name, path=str(skill_md), scope=scope, agent=agent,
            owner=owner, version=version, description=description,
        ))
    return instances


def _codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))


def scan_machine() -> list[SkillInstance]:
    """Every skill instance visible on this machine (registered projects + ambient
    user scope + Horus-managed account dirs). Read-only; never raises for a broken
    location — it just contributes nothing."""
    instances: list[SkillInstance] = []

    for project in config.load_projects():
        root = Path(project)
        if not root.is_dir():
            continue  # registered on another machine
        for agent, subdir in (("claude", skills.CLAUDE_SKILLS_SUBDIR), ("codex", skills.CODEX_SKILLS_SUBDIR)):
            instances.extend(_scan_dir(root / subdir, scope="project", agent=agent, owner=root.name))

    instances.extend(_scan_dir(Path.home() / ".claude" / "skills", scope="user", agent="claude", owner=""))
    instances.extend(_scan_dir(_codex_home() / "skills", scope="user", agent="codex", owner=""))

    for alias, path in sorted(config.load_account_config_dirs().items()):
        instances.extend(_scan_dir(Path(path) / "skills", scope="account", agent="claude", owner=alias))
    for alias, path in sorted(config.load_account_codex_homes().items()):
        instances.extend(_scan_dir(Path(path) / "skills", scope="account", agent="codex", owner=alias))

    return instances


def instance_verdict(instance: SkillInstance, *, bundled_versions: dict[str, int] | None = None) -> str:
    """Per-instance verdict: ``current``/``stale``/``unmarked`` for Horus-bundled
    names, ``foreign`` for everything else."""
    versions = bundled_versions if bundled_versions is not None else bundled_skill_versions()
    latest = versions.get(instance.name)
    if latest is None:
        return "foreign"
    if instance.version is None:
        return "unmarked"
    return "current" if instance.version >= latest else "stale"


def bundled_skill_versions() -> dict[str, int]:
    return {s.name: s.version for s in skills.SKILLS}


def skill_map(instances: list[SkillInstance] | None = None) -> list[dict]:
    """Group instances by skill name for rendering/reporting.

    Each group: ``name``, ``bundled``, ``latest`` (bundled version or None),
    ``description`` (first non-empty), ``instances`` (with per-instance ``verdict``),
    ``stale`` (count), ``scopes`` (sorted unique scope names). Sorted bundled-first,
    then by name.
    """
    if instances is None:
        instances = scan_machine()
    versions = bundled_skill_versions()
    groups: dict[str, list[SkillInstance]] = {}
    for inst in instances:
        groups.setdefault(inst.name, []).append(inst)

    result = []
    for name in sorted(groups):
        members = groups[name]
        verdicts = [instance_verdict(i, bundled_versions=versions) for i in members]
        description = next((i.description for i in members if i.description), "")
        result.append({
            "name": name,
            "bundled": name in versions,
            "latest": versions.get(name),
            "description": description,
            "instances": [
                {**vars(i), "verdict": v} for i, v in zip(members, verdicts)
            ],
            "stale": sum(1 for v in verdicts if v in ("stale", "unmarked")),
            "scopes": sorted({i.scope for i in members}),
        })
    result.sort(key=lambda g: (not g["bundled"], g["name"]))
    return result
