"""`horus init` - scaffold `.horus/` continuity and managed instruction blocks.

Never clobbers existing files. Creates what is missing; for existing
`AGENTS.md` / `CLAUDE.md` it only *injects* the managed block (with confirmation),
leaving all other content untouched.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import NamedTuple

from horus import backlog, config, frontmatter, native_hooks, skills, templates
from horus.continuity import HORUS_DIR, SESSIONS_DIR, TEMP_DIR
from horus.instructions import extract_block

# Session summaries are ignored via a .gitignore co-located inside .horus/,
# keeping a tracked .gitkeep so the directory travels with the repo.
GITIGNORE_RULES = (
    "sessions/*.md",
    "!sessions/.gitkeep",
    "sessions/archive/",
    "temp/*",
    "!temp/.gitkeep",
    ".consolidated-to",
    "backlog/.claim.lock",
)
GITIGNORE_BLOCK = "\n".join(GITIGNORE_RULES) + "\n"

# (filename, document title, the *other* file it cross-references, agent-notes heading)
_INSTRUCTION_FILES = (
    ("AGENTS.md", "Agent Instructions", "CLAUDE.md", "Codex Notes"),
    ("CLAUDE.md", "Claude Code Instructions", "AGENTS.md", "Claude Notes"),
)


class Action(NamedTuple):
    status: str  # "created" | "exists" | "updated" | "skipped"
    message: str


def _confirm(prompt: str, *, assume_yes: bool, no_input: bool) -> bool:
    if assume_yes:
        return True
    if no_input or not sys.stdin.isatty():
        return False
    try:
        answer = input(f"{prompt} [y/N] ").strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")


def _write_if_missing(path: Path, content: str, label: str) -> Action:
    if path.exists():
        return Action("exists", f"{label} already present")
    path.write_text(content, encoding="utf-8")
    return Action("created", f"created {label}")


def init_project(
    project_root: Path,
    *,
    assume_yes: bool = False,
    no_input: bool = False,
    with_skills: bool = True,
    with_hooks: bool = True,
    skill_targets: tuple[str, ...] = ("claude", "codex"),
) -> list[Action]:
    actions: list[Action] = []
    today = date.today().isoformat()

    hdir = project_root / HORUS_DIR
    hdir.mkdir(parents=True, exist_ok=True)
    (hdir / SESSIONS_DIR).mkdir(parents=True, exist_ok=True)
    (hdir / TEMP_DIR).mkdir(parents=True, exist_ok=True)

    # Structure detection, never-clobber: a project that already carries PRD.md
    # (structure v3) never gets the six lanes; a project already on the six lanes
    # (structure v2, marked by project.md) keeps scaffolding those, unchanged; a
    # truly fresh project gets the v3 PRD.md + sessions/ shape. Migrating an
    # existing v2 project to v3 is a separate, opt-in step (not `init`'s job).
    is_v3 = (hdir / frontmatter.PRD_FILE).is_file()
    is_v2 = not is_v3 and (hdir / "project.md").is_file()

    if is_v3:
        actions.append(
            Action("exists", f"{HORUS_DIR}/{frontmatter.PRD_FILE} already present (structure v3)")
        )
        actions.append(
            _write_if_missing(hdir / "README.md", templates.readme_md_v3(), f"{HORUS_DIR}/README.md")
        )
        actions.append(_ensure_backlog_dir(hdir, today))
    elif is_v2:
        actions.append(
            _write_if_missing(hdir / "README.md", templates.readme_md(), f"{HORUS_DIR}/README.md")
        )
        actions.append(
            _write_if_missing(
                hdir / "project.md",
                templates.project_md(project_root.name, today),
                f"{HORUS_DIR}/project.md",
            )
        )
        actions.append(
            _write_if_missing(
                hdir / "roadmap.md",
                templates.roadmap_md(today),
                f"{HORUS_DIR}/roadmap.md",
            )
        )
        actions.append(
            _write_if_missing(
                hdir / "features.md",
                templates.features_md(today),
                f"{HORUS_DIR}/features.md",
            )
        )
        actions.append(
            _write_if_missing(
                hdir / "execution.md",
                templates.execution_md(today),
                f"{HORUS_DIR}/execution.md",
            )
        )
        actions.append(
            _write_if_missing(
                hdir / "decisions.md",
                templates.decisions_md(),
                f"{HORUS_DIR}/decisions.md",
            )
        )
        actions.append(
            _write_if_missing(
                hdir / "history.md",
                templates.history_md(today),
                f"{HORUS_DIR}/history.md",
            )
        )
    else:
        actions.append(
            _write_if_missing(hdir / "README.md", templates.readme_md_v3(), f"{HORUS_DIR}/README.md")
        )
        actions.append(
            _write_if_missing(
                hdir / frontmatter.PRD_FILE,
                templates.prd_md(project_root.name, today),
                f"{HORUS_DIR}/{frontmatter.PRD_FILE}",
            )
        )
        actions.append(_ensure_backlog_dir(hdir, today))

    actions.append(
        _write_if_missing(
            hdir / SESSIONS_DIR / ".gitkeep",
            "",
            f"{HORUS_DIR}/{SESSIONS_DIR}/.gitkeep",
        )
    )
    actions.append(
        _write_if_missing(
            hdir / TEMP_DIR / ".gitkeep",
            "",
            f"{HORUS_DIR}/{TEMP_DIR}/.gitkeep",
        )
    )

    actions.append(_ensure_gitignore(hdir))

    for filename, title, other, notes_heading in _INSTRUCTION_FILES:
        actions.append(
            _ensure_instruction_file(
                project_root / filename,
                title=title,
                other=other,
                notes_heading=notes_heading,
                assume_yes=assume_yes,
                no_input=no_input,
            )
        )

    if with_skills:
        for sa in skills.install_skills(project_root, targets=skill_targets):
            actions.append(Action(sa.status, sa.message))

    if with_hooks:
        # Install the native hooks here so onboarding commits the complete projection
        # set at once — hook files written by a later `upgrade-project` pass used to
        # land untracked, confronting the next session with unexplained files.
        for target in skill_targets:
            for install in native_hooks.HOOK_INSTALLERS.get(target, ()):
                ha = install(project_root)
                actions.append(Action(ha.status, ha.message))

    if config.register_project(project_root):
        actions.append(Action("updated", "registered project in ~/.horus/config.toml"))
    else:
        actions.append(Action("exists", "project already in ~/.horus/config.toml"))

    return actions


def _ensure_backlog_dir(hdir: Path, today: str) -> Action:
    """Card-per-file backlog is the fleet standard: scaffold `.horus/backlog/`
    with a starter card so a fresh project's backlog dir is never silently
    empty. Never-clobber: only writes the starter card when the dir has no
    cards yet — an already-populated backlog/ (this project's own, or one a
    prior `init` already seeded) is left untouched."""
    bdir = hdir / backlog.BACKLOG_DIR
    bdir.mkdir(parents=True, exist_ok=True)
    if any(bdir.glob("*.md")):
        return Action("exists", f"{HORUS_DIR}/{backlog.BACKLOG_DIR}/ already has card(s)")
    starter = bdir / "first-card.md"
    starter.write_text(templates.starter_backlog_card(today), encoding="utf-8")
    return Action("created", f"created {HORUS_DIR}/{backlog.BACKLOG_DIR}/{starter.name}")


def _ensure_gitignore(horus_dir_path: Path) -> Action:
    path = horus_dir_path / ".gitignore"
    if not path.exists():
        path.write_text(GITIGNORE_BLOCK, encoding="utf-8")
        return Action("created", f"created {HORUS_DIR}/.gitignore ignoring session summaries and temp notes")
    text = path.read_text(encoding="utf-8")
    lines = {line.strip() for line in text.splitlines()}
    missing = [rule for rule in GITIGNORE_RULES if rule not in lines]
    if not missing:
        return Action("exists", f"{HORUS_DIR}/.gitignore already ignores session summaries and temp notes")
    sep = "" if text.endswith("\n") or text == "" else "\n"
    path.write_text(text + sep + "\n".join(missing) + "\n", encoding="utf-8")
    return Action("updated", f"{HORUS_DIR}/.gitignore: added missing temp/session ignore rules")


def _ensure_instruction_file(
    path: Path,
    *,
    title: str,
    other: str,
    notes_heading: str,
    assume_yes: bool,
    no_input: bool,
) -> Action:
    if not path.exists():
        path.write_text(
            templates.instruction_file(title, other, notes_heading),
            encoding="utf-8",
        )
        return Action("created", f"created {path.name} with managed block")

    text = path.read_text(encoding="utf-8")
    if extract_block(text).found:
        return Action("exists", f"{path.name} already has the managed block")

    if not _confirm(
        f"{path.name} exists without a Horus managed block. Inject it?",
        assume_yes=assume_yes,
        no_input=no_input,
    ):
        return Action(
            "skipped",
            f"{path.name} exists without managed block (left untouched; rerun with --yes to inject)",
        )

    sep = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    path.write_text(text + sep + templates.shared_block(other) + "\n", encoding="utf-8")
    return Action("updated", f"{path.name}: injected managed block")
