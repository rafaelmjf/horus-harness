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

from horus import config, infer, templates
from horus.continuity import COMMITTED_FILES, HORUS_DIR, SESSIONS_DIR
from horus.instructions import extract_block

# Session summaries are ignored via a .gitignore co-located inside .horus/,
# keeping a tracked .gitkeep so the directory travels with the repo.
GITIGNORE_MARKER = "sessions/*.md"
GITIGNORE_BLOCK = "sessions/*.md\n!sessions/.gitkeep\n"

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
    infer_sources: bool = True,
) -> list[Action]:
    actions: list[Action] = []
    today = date.today().isoformat()

    # Infer BEFORE creating anything, so we mine the project's pre-existing files
    # (README, roadmap, CLAUDE.md, ...) and not Horus's own fresh scaffold.
    inferred = infer.infer(project_root) if infer_sources else None
    if inferred and inferred.has_content():
        actions.append(
            Action("info", f"inferred from {', '.join(inferred.sources)} ({len(inferred.tasks)} task(s))")
        )

    hdir = project_root / HORUS_DIR
    hdir.mkdir(parents=True, exist_ok=True)
    (hdir / SESSIONS_DIR).mkdir(parents=True, exist_ok=True)

    actions.append(
        _write_if_missing(
            hdir / "project.md",
            templates.project_md(
                project_root.name,
                today,
                description=inferred.description if inferred else "",
                status=inferred.status if inferred else "planning",
                current_focus=inferred.current_focus if inferred else "",
                sources=inferred.sources if (inferred and inferred.has_content()) else None,
            ),
            f"{HORUS_DIR}/project.md",
        )
    )
    actions.append(
        _write_if_missing(
            hdir / "roadmap.md",
            templates.roadmap_md(
                today,
                current_focus=inferred.current_focus if inferred else "",
                tasks=[(t.state, t.text, t.section) for t in inferred.tasks]
                if (inferred and inferred.tasks)
                else None,
            ),
            f"{HORUS_DIR}/roadmap.md",
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
            hdir / SESSIONS_DIR / ".gitkeep",
            "",
            f"{HORUS_DIR}/{SESSIONS_DIR}/.gitkeep",
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

    if config.register_project(project_root):
        actions.append(Action("updated", "registered project in ~/.horus/config.toml"))
    else:
        actions.append(Action("exists", "project already in ~/.horus/config.toml"))

    return actions


def _ensure_gitignore(horus_dir_path: Path) -> Action:
    path = horus_dir_path / ".gitignore"
    if not path.exists():
        path.write_text(GITIGNORE_BLOCK, encoding="utf-8")
        return Action("created", f"created {HORUS_DIR}/.gitignore ignoring session summaries")
    text = path.read_text(encoding="utf-8")
    lines = {line.strip() for line in text.splitlines()}
    if GITIGNORE_MARKER in lines:
        return Action("exists", f"{HORUS_DIR}/.gitignore already ignores session summaries")
    sep = "" if text.endswith("\n") or text == "" else "\n"
    path.write_text(text + sep + GITIGNORE_BLOCK, encoding="utf-8")
    return Action("updated", f"{HORUS_DIR}/.gitignore: added session-summary ignore rules")


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
