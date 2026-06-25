"""Native app hook installation helpers.

The first supported hook target is Codex. Codex can run command hooks at turn
boundaries, so Horus installs a small Stop hook that checks local usage telemetry
and prints a closure nudge only when a threshold is crossed.
"""

from __future__ import annotations

import json
import re
import tempfile
import time
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


# --------------------------------------------------------------------------- #
# Claude Code
# --------------------------------------------------------------------------- #

def _claude_hook_command(threshold: float) -> dict[str, Any]:
    # Claude runs the command via the shell; `python -m horus` avoids depending on
    # the `horus` console script being on the hook shell's PATH.
    return {
        "type": "command",
        "command": f"python -m horus usage check --target claude --hook --threshold {threshold:g}",
    }


def _merge_event_hook(hooks: dict[str, Any], event: str, handler: dict[str, Any]) -> None:
    """Replace any prior Horus usage handler for ``event`` with ``handler`` (no dupes)."""
    groups = hooks.get(event)
    if not isinstance(groups, list):
        groups = []
    for group in groups:
        if isinstance(group, dict) and isinstance(group.get("hooks"), list):
            group["hooks"] = [h for h in group["hooks"] if not _is_horus_usage_hook(h)]
    groups = [
        g for g in groups
        if not (isinstance(g, dict) and isinstance(g.get("hooks"), list) and not g["hooks"])
    ]
    groups.append({"matcher": "", "hooks": [handler]})
    hooks[event] = groups


def install_claude_usage_hook(project_root: Path, *, threshold: float = 90.0) -> HookAction:
    """Install/update Claude Code hooks for usage-driven closure.

    `UserPromptSubmit` is the primary trigger — it fires *before* the agent works on a
    new task, so an over-budget session closes instead of starting expensive work.
    `Stop` is kept as a secondary net (close between turns)."""
    claude_dir = project_root / ".claude"
    path = claude_dir / "settings.json"
    data = _load_json(path)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        data["hooks"] = hooks

    handler = _claude_hook_command(threshold)
    _merge_event_hook(hooks, "UserPromptSubmit", handler)
    _merge_event_hook(hooks, "Stop", handler)
    data["hooks"] = hooks

    claude_dir.mkdir(parents=True, exist_ok=True)
    new_text = json.dumps(data, indent=2) + "\n"
    old_text = path.read_text(encoding="utf-8") if path.exists() else None
    if old_text == new_text:
        return HookAction("exists", f"Claude usage hook already installed in {path}")
    path.write_text(new_text, encoding="utf-8")
    return HookAction("updated" if old_text is not None else "created", f"installed Claude usage hook in {path}")


# --------------------------------------------------------------------------- #
# Per-session closure sentinel (fire the closure injection once per session)
# --------------------------------------------------------------------------- #

# Re-arm window: after firing, stay quiet for this long, then allow firing again.
# Prevents a within-turn loop without permanently suppressing a long session.
REARM_SECONDS = 1800.0


def _sentinel_path(session_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id or "unknown")[:80]
    return Path(tempfile.gettempdir()) / f"horus-closure-{safe}"


def closure_already_fired(session_id: str, *, rearm_seconds: float = REARM_SECONDS) -> bool:
    """True if closure fired for this session within the re-arm window."""
    path = _sentinel_path(session_id)
    try:
        last = float(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False
    return (time.time() - last) < rearm_seconds


def mark_closure_fired(session_id: str) -> None:
    try:
        _sentinel_path(session_id).write_text(f"{time.time():.0f}", encoding="utf-8")
    except OSError:
        pass
