"""Refresh project-local Horus projections from the installed CLI version."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from contextlib import nullcontext
from datetime import date
from pathlib import Path
from typing import NamedTuple

from horus import frontmatter, native_hooks, skills, templates, versioning
from horus.instructions import block_version, extract_block, replace_block


class UpgradeAction(NamedTuple):
    status: str  # "would-update" | "updated" | "exists" | "created" | "skipped" | "error"
    message: str


V2_LANES = ("project.md", "roadmap.md", "features.md", "decisions.md", "history.md", "execution.md")


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
        actions.extend(_upgrade_min_version_stamp(project_root, apply=apply))
    if skills_:
        actions.extend(_upgrade_skills(project_root, apply=apply, targets=targets))
    if hooks:
        actions.extend(_upgrade_hooks(project_root, apply=apply, targets=targets))
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
        return [UpgradeAction("would-update", f"{verb} .horus/{frontmatter.PRD_FILE} {versioning.MIN_VERSION_KEY} -> {floor}")]
    new_text = _set_frontmatter_key(text, versioning.MIN_VERSION_KEY, floor)
    if new_text == text:
        return [UpgradeAction("skipped", f".horus/{frontmatter.PRD_FILE} has no frontmatter; cannot stamp {versioning.MIN_VERSION_KEY}")]
    prd.write_text(new_text, encoding="utf-8")
    return [UpgradeAction("updated", f".horus/{frontmatter.PRD_FILE}: set {versioning.MIN_VERSION_KEY} -> {floor}")]


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


def upgrade_structure_prd(project_root: Path, *, apply: bool = False) -> list[UpgradeAction]:
    """Opt-in v2 six-lane -> v3 PRD.md + sessions/ migration.

    The migration is intentionally conservative: the generated PRD is a deterministic
    collapse for current-state reading, while every old lane is moved byte-for-byte to
    `.horus/archive/` so no authored continuity is destroyed.
    """
    hdir = project_root / ".horus"
    if not hdir.is_dir():
        return [UpgradeAction("error", "no .horus/ directory (run `horus init` first)")]
    if (hdir / frontmatter.PRD_FILE).exists():
        return [UpgradeAction("exists", ".horus/PRD.md already present (structure v3)")]

    lanes = [name for name in V2_LANES if (hdir / name).is_file()]
    if not lanes:
        return [UpgradeAction("error", "no v2 lane files found to migrate")]
    required = {"project.md", "roadmap.md", "decisions.md"}
    missing_required = sorted(required - set(lanes))
    if missing_required:
        return [UpgradeAction("error", f"missing required v2 lane(s): {', '.join(missing_required)}")]

    archive = hdir / "archive"
    collisions = [name for name in lanes if (archive / name).exists()]
    if collisions:
        return [UpgradeAction("error", f"archive target already exists: {', '.join('.horus/archive/' + n for n in collisions)}")]

    if apply:
        safety = _migration_git_safety(project_root)
        if safety:
            return [UpgradeAction("error", safety)]

    prd_text = _build_prd(project_root.name, hdir)
    actions = [UpgradeAction("would-update", f"would create .horus/{frontmatter.PRD_FILE}")]
    actions.extend(UpgradeAction("would-update", f"would archive .horus/{name} -> .horus/archive/{name}") for name in lanes)
    actions.append(UpgradeAction("would-update", "would leave .horus/sessions/ and .horus/temp/ in place"))
    if not apply:
        return actions

    archive.mkdir(parents=True, exist_ok=True)
    (hdir / frontmatter.PRD_FILE).write_text(prd_text, encoding="utf-8")
    for name in lanes:
        (hdir / name).rename(archive / name)
    (hdir / "sessions").mkdir(exist_ok=True)
    (hdir / "temp").mkdir(exist_ok=True)
    return [
        UpgradeAction("created", f"created .horus/{frontmatter.PRD_FILE}"),
        *[UpgradeAction("updated", f"archived .horus/{name} -> .horus/archive/{name}") for name in lanes],
        UpgradeAction("exists", ".horus/sessions/ and .horus/temp/ preserved"),
    ]


def _migration_git_safety(project_root: Path) -> str | None:
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


def _build_prd(project_name: str, hdir: Path) -> str:
    project = frontmatter.parse((hdir / "project.md").read_text(encoding="utf-8"))
    roadmap = frontmatter.parse((hdir / "roadmap.md").read_text(encoding="utf-8"))
    features = frontmatter.parse((hdir / "features.md").read_text(encoding="utf-8")) if (hdir / "features.md").is_file() else None
    decisions = frontmatter.parse((hdir / "decisions.md").read_text(encoding="utf-8"))

    status = _fm(roadmap, "status") or _fm(project, "status") or "active"
    current_focus = _fm(roadmap, "current_focus") or _fm(project, "current_focus")
    last_updated = _fm(roadmap, "last_updated") or _fm(project, "last_updated") or date.today().isoformat()
    front = {
        "status": status,
        "current_focus": current_focus,
        "next_action": _fm(roadmap, "next_action"),
        "next_prompt": _fm(roadmap, "next_prompt"),
        "execution_recommendation": _fm(roadmap, "execution_recommendation") or "continue-as-is",
        "last_updated": last_updated,
    }
    front_text = "\n".join(f'{key}: "{_escape_fm(value)}"' for key, value in front.items())
    vision = _clean_body(project.body) or "Agent-polish TODO: distill the project vision from `.horus/archive/project.md`."
    backlog = _roadmap_backlog(roadmap.body)
    shipped = _features_shipped(features.body if features else "")
    rules = _clean_body(decisions.body) or "Agent-polish TODO: distill load-bearing rules from `.horus/archive/decisions.md`."
    return (
        f"---\n{front_text}\n---\n\n"
        f"# {project_name} — PRD\n\n"
        "> Agent-polish TODO: Review this generated PRD, tighten prose, and remove any stale migrated detail. "
        "The original six-lane files are preserved verbatim in `.horus/archive/`.\n\n"
        "## Vision\n\n"
        f"{vision}\n\n"
        "## Backlog\n\n"
        f"{backlog}\n\n"
        "## Shipped\n\n"
        f"{shipped}\n\n"
        "## Rules (load-bearing)\n\n"
        f"{rules}\n\n"
        "## Structure contract\n\n"
        "- **This file** carries vision, backlog, shipped, rules. Keep it under ~250 lines.\n"
        "- **Archive:** the pre-migration six-lane files live under `.horus/archive/` verbatim.\n"
        "- **Closure:** update PRD frontmatter + backlog/shipped + a session note, then `horus close --commit --push`.\n"
    )


def _fm(doc: frontmatter.Document, key: str) -> str:
    return str(doc.front_matter.get(key, "")).strip()


def _escape_fm(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _clean_body(body: str) -> str:
    lines = body.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and lines[0].lstrip().startswith("# "):
        lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def _roadmap_backlog(body: str) -> str:
    lines = _clean_body(body).splitlines()
    kept: list[str] = []
    skip_checked_indent: int | None = None
    skip_done_section = False
    for line in lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if stripped.startswith("## "):
            skip_done_section = "done" in stripped.lower()
            skip_checked_indent = None
            if not skip_done_section:
                kept.append("#" + stripped)
            continue
        if skip_done_section:
            continue
        is_list_item = stripped.startswith(("- ", "* ")) or (
            bool(stripped) and stripped[0].isdigit() and ". " in stripped[:6]
        )
        if skip_checked_indent is not None:
            if not stripped:
                continue
            if indent > skip_checked_indent and not is_list_item and not stripped.startswith("#"):
                continue
            skip_checked_indent = None
        if _is_checked_item(stripped):
            skip_checked_indent = indent
            continue
        unchecked = _unchecked_item_text(stripped)
        if unchecked is not None:
            marker = line[: len(line) - len(stripped)] + "- "
            kept.append(marker + unchecked)
            continue
        kept.append(line)
    text = _drop_empty_headings(kept).strip()
    if not text:
        return "Agent-polish TODO: distill open roadmap items from `.horus/archive/roadmap.md`."
    return text + "\n\nAgent-polish TODO: prune migrated backlog prose to the current open work."


def _is_checked_item(stripped: str) -> bool:
    low = stripped.lower()
    if low.startswith(("- [x]", "* [x]")):
        return True
    dot = low.find(". ")
    return dot > 0 and low[:dot].isdigit() and low[dot + 2 :].startswith("[x]")


def _unchecked_item_text(stripped: str) -> str | None:
    low = stripped.lower()
    if low.startswith(("- [ ]", "* [ ]")):
        return stripped[5:].strip()
    dot = low.find(". ")
    if dot > 0 and low[:dot].isdigit() and low[dot + 2 :].startswith("[ ]"):
        return stripped[dot + 5 :].strip()
    return None


def _drop_empty_headings(lines: list[str]) -> str:
    out: list[str] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("### "):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j >= len(lines) or lines[j].strip().startswith("### "):
                continue
        out.append(line)
    return "\n".join(out)


def _features_shipped(body: str) -> str:
    section = _section(_clean_body(body), "Shipped")
    rows: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if not cells or set(cells[0]) <= {"-", ":"} or cells[0].lower() == "capability":
                continue
            detail = " — ".join(cell for cell in cells[1:] if cell)
            rows.append(f"- **{cells[0]}**" + (f" — {detail}" if detail else ""))
            continue
        rows.append(line)
    if not rows:
        return "Agent-polish TODO: distill shipped one-liners from `.horus/archive/features.md`."
    return "\n".join(rows)


def _section(body: str, title: str) -> str:
    lines = body.splitlines()
    start: int | None = None
    for i, line in enumerate(lines):
        if line.strip().lower() == f"## {title.lower()}":
            start = i + 1
            break
    if start is None:
        return body
    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return "\n".join(lines[start:end]).strip()


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
    installers = native_hooks.HOOK_INSTALLERS.get(target)
    if installers is None:
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
