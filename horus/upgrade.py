"""Refresh project-local Horus projections from the installed CLI version."""

from __future__ import annotations

import shutil
import tempfile
from contextlib import nullcontext
from pathlib import Path
from typing import NamedTuple

from horus import native_hooks, skills, templates
from horus.instructions import block_version, extract_block, replace_block


class UpgradeAction(NamedTuple):
    status: str  # "would-update" | "updated" | "exists" | "created" | "skipped"
    message: str


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
    if instructions:
        actions.extend(_upgrade_instructions(project_root, apply=apply))
    if skills_:
        actions.extend(_upgrade_skills(project_root, apply=apply, targets=targets))
    if hooks:
        actions.extend(_upgrade_hooks(project_root, apply=apply, targets=targets))
    return actions


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
                actions.append(UpgradeAction("created", f"created {filename} with current managed block"))
            else:
                actions.append(UpgradeAction("would-update", f"would create {filename} with current managed block"))
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
            actions.append(UpgradeAction("updated", f"{filename}: refreshed managed block"))
        else:
            actions.append(UpgradeAction("would-update", f"would refresh {filename} managed block"))
    return actions


def _upgrade_skills(project_root: Path, *, apply: bool, targets: tuple[str, ...]) -> list[UpgradeAction]:
    actions: list[UpgradeAction] = []
    for target in targets:
        for skill in skills.SKILLS:
            if apply:
                a = skills.write_skill(skill, project_root, target=target)
                actions.append(UpgradeAction(a.status, a.message))
                continue
            path = skills.skill_path(skill, project_root, target=target)
            if not path.exists():
                actions.append(UpgradeAction("would-update", f"would create {skill.rel_path(target=target)}"))
                continue
            current = skills.installed_version(path.read_text(encoding="utf-8"))
            if current is None:
                actions.append(UpgradeAction("skipped", f"{skill.name} ({target}): present without a version marker"))
            elif current < skill.version:
                actions.append(UpgradeAction("would-update", f"would update {skill.name} ({target}) v{current} -> v{skill.version}"))
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
    if target == "codex":
        installers = (
            native_hooks.install_codex_usage_hook,
            native_hooks.install_codex_merge_hook,
            native_hooks.install_codex_guard_hook,
        )
    elif target == "claude":
        installers = (
            native_hooks.install_claude_usage_hook,
            native_hooks.install_claude_merge_hook,
            native_hooks.install_claude_guard_hook,
        )
    else:
        return actions
    for install in installers:
        a = install(root)
        status = a.status
        if not apply and status in ("created", "updated"):
            status = "would-update"
        actions.append(UpgradeAction(status, _retarget_message(a.message, root, project_root)))
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
