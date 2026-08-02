"""Refresh project-local Horus projections from the installed CLI version."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from contextlib import nullcontext
from datetime import date
from pathlib import Path
from typing import NamedTuple

from horus import frontmatter, initialize, native_hooks, skills, templates, versioning
from horus.instructions import block_version, extract_block, replace_block


class UpgradeAction(NamedTuple):
    status: str  # "would-update" | "updated" | "exists" | "created" | "skipped" | "error"
    message: str
    path: str | None = None




def upgrade_project(
    project_root: Path,
    *,
    apply: bool = False,
    targets: tuple[str, ...] = ("claude", "codex"),
    hooks: bool = True,
    skills_: bool = True,
    instructions: bool = True,
) -> list[UpgradeAction]:
    actions: list[UpgradeAction] = []
    actions.extend(_upgrade_generated_state(project_root, apply=apply))
    if instructions:
        actions.extend(_upgrade_instructions(project_root, apply=apply))
        actions.extend(_upgrade_min_version_stamp(project_root, apply=apply))
    if skills_:
        actions.extend(_upgrade_skills(project_root, apply=apply, targets=targets))
    if hooks:
        actions.extend(_upgrade_hooks(project_root, apply=apply, targets=targets))
    return actions


def _upgrade_generated_state(project_root: Path, *, apply: bool) -> list[UpgradeAction]:
    """Ignore generated continuity state and untrack legacy marker files.

    Older projects may have committed a checkpoint marker before it became local
    state.  The marker necessarily changes at every checkpoint, so keeping it in
    the index makes the cleanliness hook report the write it just caused.
    """
    hdir = project_root / ".horus"
    if not hdir.is_dir():
        return []

    ignore_path = hdir / ".gitignore"
    existing = ignore_path.read_text(encoding="utf-8") if ignore_path.is_file() else ""
    lines = {line.strip() for line in existing.splitlines()}
    missing = [rule for rule in initialize.GITIGNORE_RULES if rule not in lines]
    tracked = [
        f".horus/{rule}"
        for rule in initialize.GITIGNORE_RULES
        if not rule.startswith(("!", "sessions/", "temp/"))
        and _git(project_root, "ls-files", "--error-unmatch", f".horus/{rule}") is not None
    ]

    actions: list[UpgradeAction] = []
    if missing:
        if apply:
            action = initialize._ensure_gitignore(hdir)
            actions.append(UpgradeAction("updated", action.message, ".horus/.gitignore"))
        else:
            actions.append(UpgradeAction(
                "would-update",
                f"would add generated-state ignore rule(s): {', '.join(missing)}",
                ".horus/.gitignore",
            ))
    else:
        actions.append(UpgradeAction("exists", ".horus/.gitignore ignores generated continuity state"))

    if tracked:
        if apply:
            result = _git(project_root, "rm", "--cached", "-f", "--", *tracked)
            status = "updated" if result is not None else "error"
            message = (
                f"stopped tracking generated continuity state: {', '.join(tracked)}"
                if result is not None else
                f"could not stop tracking generated continuity state: {', '.join(tracked)}"
            )
            actions.append(UpgradeAction(status, message, tracked[0]))
        else:
            actions.append(UpgradeAction(
                "would-update",
                f"would stop tracking generated continuity state: {', '.join(tracked)}",
                tracked[0],
            ))
    return actions


def _upgrade_min_version_stamp(project_root: Path, *, apply: bool) -> list[UpgradeAction]:
    """Ensure `.horus/PRD.md` records `horus_min_version` >= the current floor.

    This is how an existing v3 project acquires (or raises) the structure-version
    stamp when the user upgrades — the pairing repo-side data for both the agent
    preflight (Lever A) and the CLI gate (`cli._enforce_version_floor`, Lever B).
    Fresh scaffolds already carry it from `templates.prd_md`; v2 projects (no PRD.md)
    are left alone.
    """
    prd = frontmatter.prd_path(project_root)
    if not prd.is_file():
        return []
    text = prd.read_text(encoding="utf-8")
    current = frontmatter.parse(text).front_matter.get(versioning.MIN_VERSION_KEY, "").strip()
    floor = versioning.MIN_CLI_VERSION
    if current and versioning.is_at_least(current, floor):
        return [UpgradeAction("exists", f".horus/{frontmatter.PRD_FILE} {versioning.MIN_VERSION_KEY} is current ({current})")]
    verb = "would raise" if current else "would add"
    if not apply:
        return [UpgradeAction(
            "would-update",
            f"{verb} .horus/{frontmatter.PRD_FILE} {versioning.MIN_VERSION_KEY} -> {floor}",
            f".horus/{frontmatter.PRD_FILE}",
        )]
    new_text = _set_frontmatter_key(text, versioning.MIN_VERSION_KEY, floor)
    if new_text == text:
        return [UpgradeAction("skipped", f".horus/{frontmatter.PRD_FILE} has no frontmatter; cannot stamp {versioning.MIN_VERSION_KEY}")]
    prd.write_text(new_text, encoding="utf-8")
    return [UpgradeAction(
        "updated",
        f".horus/{frontmatter.PRD_FILE}: set {versioning.MIN_VERSION_KEY} -> {floor}",
        f".horus/{frontmatter.PRD_FILE}",
    )]


def _set_frontmatter_key(text: str, key: str, value: str) -> str:
    """Replace ``key``'s line inside the leading `---` frontmatter, or insert it just
    before the closing fence. Returns ``text`` unchanged when there is no frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    close = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if close is None:
        return text
    new_line = f"{key}: {value}"
    for i in range(1, close):
        stripped = lines[i].lstrip()
        if stripped.startswith(f"{key}:") and not stripped.startswith("#"):
            lines[i] = new_line
            break
    else:
        lines.insert(close, new_line)
    trailing = "\n" if text.endswith("\n") else ""
    return "\n".join(lines) + trailing


def migration_git_safety(project_root: Path) -> str | None:
    if _git(project_root, "rev-parse", "--is-inside-work-tree") != "true":
        return None
    if _git(project_root, "fetch", "--all", "--prune") is None:
        return "git fetch --all --prune failed; refusing structure migration"
    dirty = _git(project_root, "status", "--porcelain")
    if dirty:
        return "working tree is dirty; commit or stash before structure migration"
    upstream = _git(project_root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if not upstream:
        return None
    counts = _git(project_root, "rev-list", "--left-right", "--count", f"HEAD...{upstream}")
    if not counts:
        return None
    ahead_s, behind_s = (counts.split() + ["0", "0"])[:2]
    try:
        behind = int(behind_s)
    except ValueError:
        behind = 0
    if behind:
        return f"branch is behind {upstream} by {behind} commit(s); pull before structure migration"
    return None


def _git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _upgrade_instructions(project_root: Path, *, apply: bool) -> list[UpgradeAction]:
    specs = (
        ("AGENTS.md", "Agent Instructions", "CLAUDE.md", "Codex Notes"),
        ("CLAUDE.md", "Claude Code Instructions", "AGENTS.md", "Claude Notes"),
    )
    actions: list[UpgradeAction] = []
    for filename, title, other, notes_heading in specs:
        path = project_root / filename
        desired_block = templates.shared_block(other)
        if not path.exists():
            if apply:
                path.write_text(templates.instruction_file(title, other, notes_heading), encoding="utf-8")
                actions.append(UpgradeAction("created", f"created {filename} with current managed block", filename))
            else:
                actions.append(UpgradeAction("would-update", f"would create {filename} with current managed block", filename))
            continue

        text = path.read_text(encoding="utf-8")
        current = extract_block(text)
        if not current.found:
            actions.append(UpgradeAction("skipped", f"{filename} has no Horus managed block; rerun `horus init --yes` to inject"))
            continue
        # Direction guard: a block NEWER than this CLI means the CLI is what's
        # outdated (e.g. an old installed tool reading a freshly pulled repo).
        # Refreshing would silently downgrade it — refuse and point at self-update.
        current_version = block_version(current.raw or "")
        if current_version is not None and current_version > templates.BLOCK_VERSION:
            actions.append(UpgradeAction(
                "skipped",
                f"{filename} managed block (v{current_version}) is newer than this CLI "
                f"(v{templates.BLOCK_VERSION}) — upgrade horus-harness instead of refreshing",
            ))
            continue
        new_text = replace_block(text, desired_block)
        if new_text == text:
            actions.append(UpgradeAction("exists", f"{filename} managed block is current"))
            continue
        if apply:
            path.write_text(new_text, encoding="utf-8")
            actions.append(UpgradeAction("updated", f"{filename}: refreshed managed block", filename))
        else:
            actions.append(UpgradeAction("would-update", f"would refresh {filename} managed block", filename))
    return actions


def _upgrade_skills(project_root: Path, *, apply: bool, targets: tuple[str, ...]) -> list[UpgradeAction]:
    actions: list[UpgradeAction] = []
    for target in targets:
        for skill in skills.bundled_for(project_root):
            if apply:
                a = skills.write_skill(skill, project_root, target=target)
                actions.append(UpgradeAction(a.status, a.message, skill.rel_path(target=target)))
                continue
            path = skills.skill_path(skill, project_root, target=target)
            if not path.exists():
                actions.append(UpgradeAction(
                    "would-update",
                    f"would create {skill.rel_path(target=target)}",
                    skill.rel_path(target=target),
                ))
                continue
            current = skills.installed_version(path.read_text(encoding="utf-8"))
            if current is None:
                actions.append(UpgradeAction("skipped", f"{skill.name} ({target}): present without a version marker"))
            elif current < skill.version:
                actions.append(UpgradeAction(
                    "would-update",
                    f"would update {skill.name} ({target}) v{current} -> v{skill.version}",
                    skill.rel_path(target=target),
                ))
            else:
                actions.append(UpgradeAction("exists", f"{skill.name} ({target}): up to date (v{current})"))
    return actions


def _upgrade_hooks(project_root: Path, *, apply: bool, targets: tuple[str, ...]) -> list[UpgradeAction]:
    actions: list[UpgradeAction] = []
    for target in targets:
        ctx = nullcontext(project_root) if apply else _temporary_hook_state(project_root)
        with ctx as root:
            actions.extend(_upgrade_hook_target(root, project_root=project_root, target=target, apply=apply))
    return actions


def _upgrade_hook_target(root: Path, *, project_root: Path, target: str, apply: bool) -> list[UpgradeAction]:
    actions: list[UpgradeAction] = []
    installers = native_hooks.HOOK_INSTALLERS.get(target)
    if installers is None:
        return actions
    rel_path = ".claude/settings.json" if target == "claude" else ".codex/hooks.json"
    for install in installers:
        a = install(root)
        status = a.status
        if not apply and status in ("created", "updated"):
            status = "would-update"
        actions.append(UpgradeAction(status, _retarget_message(a.message, root, project_root), rel_path))
    return actions


def _temporary_hook_state(project_root: Path):
    class _TempHookState:
        def __enter__(self) -> Path:
            self._tmpdir = tempfile.TemporaryDirectory(prefix="horus-upgrade-")
            tmp = Path(self._tmpdir.name)
            for rel in (".codex/hooks.json", ".claude/settings.json"):
                src = project_root / rel
                if src.exists():
                    dst = tmp / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
            return tmp

        def __exit__(self, *exc_info) -> None:
            self._tmpdir.cleanup()

    return _TempHookState()


def _retarget_message(message: str, old_root: Path, new_root: Path) -> str:
    return message.replace(str(old_root), str(new_root))
