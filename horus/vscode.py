"""Static VS Code task projection — the one-keypress tier of "launch in VS Code".

`horus vscode-task` writes a `.vscode/tasks.json` with generic, secret-free tasks
that start the agent in the integrated terminal seeded with `horus resume` (the
continuity handoff): open the folder (e.g. via the dashboard's VS Code launch
destination), press Ctrl+Shift+B, and claude picks up where the last session left
off. Deliberately NOT the auto-run tier (`runOn: folderOpen` needs VS Code's
per-folder "Allow Automatic Tasks" trust gate plus a machine-local launch spec
for account env and prompt — deferred); accounts stay ambient here, which is
what keeps the file free of secrets and safe to commit.

Ownership: `.vscode/` is a user surface, not a Horus one. Horus only creates the
file when it's absent, and offboard only removes a byte-identical file it wrote.
An existing tasks.json is never merged into or overwritten — VS Code's jsonc
(comments, trailing commas) makes safe rewriting a non-goal — so the caller
prints the snippet for the user to add by hand instead.
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

# The resume commands run through the task's shell, so `$(horus resume)` resolves
# at run time from the repo's committed `.horus/` lanes — nothing machine- or
# session-specific is baked into the file. POSIX sh and PowerShell (VS Code's
# Windows default) share this substitution syntax; classic cmd.exe does not.
TASKS_JSON = """\
{
  // Written by `horus vscode-task`. Safe to edit — Horus never rewrites an
  // edited tasks.json (it only updates/removes its own unedited versions).
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Horus: resume Claude session",
      "detail": "Start claude in the integrated terminal, seeded with this repo's .horus continuity handoff",
      "type": "shell",
      "command": "claude \\"$(horus resume)\\"",
      "group": { "kind": "build", "isDefault": true },
      "presentation": { "reveal": "always", "panel": "dedicated", "focus": true },
      "problemMatcher": []
    },
    {
      "label": "Horus: fresh Claude session",
      "detail": "Start claude in the integrated terminal, unseeded",
      "type": "shell",
      "command": "claude",
      "presentation": { "reveal": "always", "panel": "dedicated", "focus": true },
      "problemMatcher": []
    },
    {
      "label": "Horus: resume Codex session",
      "detail": "Start codex in the integrated terminal, seeded with this repo's .horus continuity handoff",
      "type": "shell",
      "command": "codex \\"$(horus resume)\\"",
      "presentation": { "reveal": "always", "panel": "dedicated", "focus": true },
      "problemMatcher": []
    },
    {
      "label": "Horus: fresh Codex session",
      "detail": "Start codex in the integrated terminal, unseeded",
      "type": "shell",
      "command": "codex",
      "presentation": { "reveal": "always", "panel": "dedicated", "focus": true },
      "problemMatcher": []
    }
  ]
}
"""

# Byte-exact earlier generations of the file above. A tasks.json matching any of
# these is still *ours* (unedited), so write_tasks may upgrade it in place and
# remove_tasks may delete it; anything else has user edits and is theirs now.
_PREVIOUS_TASKS_JSON: tuple[str, ...] = (
    """\
{
  // Written by `horus vscode-task`. Safe to edit — Horus never rewrites an
  // existing tasks.json (offboard removes it only if byte-identical).
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Horus: resume Claude session",
      "detail": "Start claude in the integrated terminal, seeded with this repo's .horus continuity handoff",
      "type": "shell",
      "command": "claude \\"$(horus resume)\\"",
      "group": { "kind": "build", "isDefault": true },
      "presentation": { "reveal": "always", "panel": "dedicated", "focus": true },
      "problemMatcher": []
    },
    {
      "label": "Horus: resume Codex session",
      "detail": "Start codex in the integrated terminal, seeded with this repo's .horus continuity handoff",
      "type": "shell",
      "command": "codex \\"$(horus resume)\\"",
      "presentation": { "reveal": "always", "panel": "dedicated", "focus": true },
      "problemMatcher": []
    }
  ]
}
""",
)

# Keyboard shortcuts are a *user-level* VS Code surface (keybindings.json has no
# per-workspace variant), so Horus can't project them into the repo — the CLI
# prints this snippet for the user to paste instead. Ctrl+Shift+B already runs
# the default build task (resume Claude) without any of this.
KEYBINDINGS_SNIPPET = """\
{ "key": "ctrl+alt+r", "command": "workbench.action.tasks.runTask", "args": "Horus: resume Claude session" },
{ "key": "ctrl+alt+n", "command": "workbench.action.tasks.runTask", "args": "Horus: fresh Claude session" }\
"""


def _is_horus_file(text: str) -> bool:
    return text == TASKS_JSON or text in _PREVIOUS_TASKS_JSON


class TaskAction(NamedTuple):
    status: str  # "created" | "up-to-date" | "kept" | "removed" | "absent"
    message: str


def tasks_path(project_root: Path) -> Path:
    return project_root / ".vscode" / "tasks.json"


def write_tasks(project_root: Path) -> TaskAction:
    """Create `.vscode/tasks.json` when absent; upgrade in place when it's an
    unedited earlier Horus generation.

    A foreign/edited file is kept untouched (`status="kept"`) — the caller shows
    the snippet for a manual merge instead.
    """
    path = tasks_path(project_root)
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if text == TASKS_JSON:
            return TaskAction("up-to-date", f"{path} already current")
        if text in _PREVIOUS_TASKS_JSON:
            path.write_text(TASKS_JSON, encoding="utf-8")
            return TaskAction("updated", f"updated {path} (unedited Horus tasks, older generation)")
        return TaskAction("kept", f"{path} exists and isn't Horus's — left untouched; add the task manually")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TASKS_JSON, encoding="utf-8")
    return TaskAction("created", f"created {path}")


def remove_tasks(project_root: Path) -> TaskAction:
    """Offboard counterpart: remove tasks.json only if it's an unedited Horus
    generation (a user-edited file is theirs now); prune an emptied `.vscode/`."""
    path = tasks_path(project_root)
    if not path.exists():
        return TaskAction("absent", "no .vscode/tasks.json")
    if not _is_horus_file(path.read_text(encoding="utf-8")):
        return TaskAction("kept", f"{path} was edited — kept (not Horus's to remove)")
    path.unlink()
    if path.parent.is_dir() and not any(path.parent.iterdir()):
        path.parent.rmdir()
    return TaskAction("removed", f"removed {path}")
