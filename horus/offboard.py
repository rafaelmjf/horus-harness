"""Cleanly remove Horus from a project — the inverse of `init`/`upgrade-project`.

Offboarding strips the *projected* Horus artifacts (the AGENTS/CLAUDE managed block,
the bundled skills, and the native Claude/Codex hooks) and unregisters the project from
the local registry. The durable `.horus/` lanes are **kept by default** — they are the
project's committed memory and survive in git — and only removed under an explicit
``purge`` opt-in.

Like `upgrade_project`, this reports actions; ``apply=False`` is a dry run that lists
what *would* be removed without touching anything.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import NamedTuple

from horus import config, native_hooks, skills, vscode
from horus.instructions import extract_block, remove_block


class OffboardAction(NamedTuple):
    status: str  # "would-remove" | "removed" | "absent" | "kept"
    message: str


_INSTRUCTION_FILES = ("AGENTS.md", "CLAUDE.md")


def offboard_project(
    project_root: Path,
    *,
    apply: bool = False,
    purge: bool = False,
    targets: tuple[str, ...] = ("claude", "codex"),
) -> list[OffboardAction]:
    """Remove Horus's projected artifacts (+ registry entry) from ``project_root``.

    ``purge`` additionally deletes the ``.horus/`` lanes. ``apply=False`` is a dry run.
    """
    actions: list[OffboardAction] = []
    actions.extend(_remove_managed_blocks(project_root, apply=apply))
    actions.extend(_remove_skills(project_root, apply=apply, targets=targets))
    actions.extend(_remove_hooks(project_root, apply=apply, targets=targets))
    actions.extend(_remove_vscode_tasks(project_root, apply=apply))
    actions.append(_unregister(project_root, apply=apply))
    actions.append(_handle_horus_dir(project_root, apply=apply, purge=purge))
    return actions


def _remove_managed_blocks(project_root: Path, *, apply: bool) -> list[OffboardAction]:
    actions: list[OffboardAction] = []
    for filename in _INSTRUCTION_FILES:
        path = project_root / filename
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if not extract_block(text).found:
            continue
        if apply:
            new_text, _ = remove_block(text)
            path.write_text(new_text, encoding="utf-8")
            actions.append(OffboardAction("removed", f"removed Horus managed block from {filename}"))
        else:
            actions.append(OffboardAction("would-remove", f"would remove Horus managed block from {filename}"))
    return actions


def _remove_skills(project_root: Path, *, apply: bool, targets: tuple[str, ...]) -> list[OffboardAction]:
    actions: list[OffboardAction] = []
    for target in targets:
        for skill in skills.SKILLS:
            skill_dir = skills.skill_path(skill, project_root, target=target).parent
            if not skill_dir.exists():
                continue
            rel = skill.rel_path(target=target).rsplit("/", 1)[0]
            if apply:
                shutil.rmtree(skill_dir, ignore_errors=True)
                actions.append(OffboardAction("removed", f"removed {rel}"))
            else:
                actions.append(OffboardAction("would-remove", f"would remove {rel}"))
        if apply:
            # Tidy now-empty parents (.claude/skills, .agents/skills) — but never the
            # whole .claude/.agents dir if it still holds other content.
            _prune_empty_dirs(project_root, target)
    return actions


def _prune_empty_dirs(project_root: Path, target: str) -> None:
    subdir = skills.TARGET_SUBDIRS[target]  # e.g. ".claude/skills"
    parts = Path(subdir).parts
    for depth in range(len(parts), 0, -1):
        d = project_root.joinpath(*parts[:depth])
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()


def _remove_hooks(project_root: Path, *, apply: bool, targets: tuple[str, ...]) -> list[OffboardAction]:
    actions: list[OffboardAction] = []
    specs = {
        "claude": (native_hooks.claude_settings_path, native_hooks.remove_claude_hooks, "Claude"),
        "codex": (native_hooks.codex_hooks_path, native_hooks.remove_codex_hooks, "Codex"),
    }
    for target in targets:
        spec = specs.get(target)
        if spec is None:
            continue
        path_fn, remove_fn, label = spec
        if apply:
            action = remove_fn(project_root)
            if action.status != "absent":
                actions.append(OffboardAction("removed", action.message))
        elif native_hooks.file_has_horus_hooks(path_fn(project_root)):
            actions.append(OffboardAction("would-remove", f"would remove Horus {label} hooks from {path_fn(project_root)}"))
    return actions


def _remove_vscode_tasks(project_root: Path, *, apply: bool) -> list[OffboardAction]:
    """Remove the `horus vscode-task` tasks.json — only when it's an unedited Horus
    generation (an edited file is the user's now; vscode.remove_tasks keeps it)."""
    path = vscode.tasks_path(project_root)
    if not path.exists():
        return []
    if apply:
        action = vscode.remove_tasks(project_root)
        if action.status == "removed":
            return [OffboardAction("removed", action.message)]
        return []  # kept (user-edited) — not Horus's to report on
    if vscode._is_horus_file(path.read_text(encoding="utf-8")):
        return [OffboardAction("would-remove", f"would remove {path}")]
    return []


def _unregister(project_root: Path, *, apply: bool) -> OffboardAction:
    registered = config._as_key(project_root) in config.load_projects()
    if not registered:
        return OffboardAction("absent", "project is not in the local registry")
    if apply:
        config.unregister_project(project_root)
        return OffboardAction("removed", "unregistered project from the local registry")
    return OffboardAction("would-remove", "would unregister project from the local registry")


def _handle_horus_dir(project_root: Path, *, apply: bool, purge: bool) -> OffboardAction:
    horus_dir = project_root / ".horus"
    if not horus_dir.is_dir():
        return OffboardAction("absent", "no .horus/ directory present")
    if not purge:
        return OffboardAction("kept", ".horus/ kept (the durable memory) — re-run with purge to delete it")
    if apply:
        shutil.rmtree(horus_dir, ignore_errors=True)
        return OffboardAction("removed", "deleted .horus/ (purge) — the project's Horus memory is gone")
    return OffboardAction("would-remove", "would delete .horus/ (purge) — irreversible")
