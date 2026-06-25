"""Native app hook installation helpers.

The first supported hook target is Codex. Codex can run command hooks at turn
boundaries, so Horus installs a small Stop hook that checks local usage telemetry
and prints a closure nudge only when a threshold is crossed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NamedTuple


class HookAction(NamedTuple):
    status: str
    message: str


_HORUS_USAGE_MARKER = "horus usage check"


def _codex_hook_command(threshold: float) -> dict[str, Any]:
    # Keep both POSIX and Windows command spellings. Codex will use the Windows
    # override on Windows and the portable command elsewhere.
    return {
        "type": "command",
        "command": f"python -m horus usage check --path . --threshold {threshold:g} --hook",
        "commandWindows": f"py -m horus usage check --path . --threshold {threshold:g} --hook",
        "timeout": 30,
        "statusMessage": "Checking Horus usage",
    }


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _is_horus_usage_hook(handler: Any) -> bool:
    if not isinstance(handler, dict):
        return False
    command = str(handler.get("command", ""))
    command_windows = str(handler.get("commandWindows", handler.get("command_windows", "")))
    return _HORUS_USAGE_MARKER in command or _HORUS_USAGE_MARKER in command_windows


def install_codex_usage_hook(project_root: Path, *, threshold: float = 90.0) -> HookAction:
    """Install/update a project-local Codex Stop hook for usage checks."""
    codex_dir = project_root / ".codex"
    path = codex_dir / "hooks.json"
    data = _load_json(path)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        data["hooks"] = hooks

    stop_groups = hooks.setdefault("Stop", [])
    if not isinstance(stop_groups, list):
        stop_groups = []

    for group in stop_groups:
        if not isinstance(group, dict):
            continue
        handlers = group.get("hooks")
        if not isinstance(handlers, list):
            continue
        kept = [h for h in handlers if not _is_horus_usage_hook(h)]
        if len(kept) != len(handlers):
            group["hooks"] = kept

    stop_groups = [
        group for group in stop_groups
        if not (isinstance(group, dict) and isinstance(group.get("hooks"), list) and not group["hooks"])
    ]
    stop_groups.append({"hooks": [_codex_hook_command(threshold)]})
    hooks["Stop"] = stop_groups
    data["hooks"] = hooks

    codex_dir.mkdir(parents=True, exist_ok=True)
    new_text = json.dumps(data, indent=2) + "\n"
    old_text = path.read_text(encoding="utf-8") if path.exists() else None
    if old_text == new_text:
        return HookAction("exists", f"Codex usage hook already installed in {path}")
    path.write_text(new_text, encoding="utf-8")
    return HookAction("updated" if old_text is not None else "created", f"installed Codex usage hook in {path}")
