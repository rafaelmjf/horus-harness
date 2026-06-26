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
_HORUS_MERGE_MARKER = "horus close --hook"
_HORUS_GUARD_MARKER = "horus guard-host"


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


def _handler_has_marker(handler: Any, marker: str) -> bool:
    if not isinstance(handler, dict):
        return False
    command = str(handler.get("command", ""))
    command_windows = str(handler.get("commandWindows", handler.get("command_windows", "")))
    return marker in command or marker in command_windows


def _is_horus_usage_hook(handler: Any) -> bool:
    return _handler_has_marker(handler, _HORUS_USAGE_MARKER)


def _is_horus_merge_hook(handler: Any) -> bool:
    return _handler_has_marker(handler, _HORUS_MERGE_MARKER)


def _is_horus_guard_hook(handler: Any) -> bool:
    return _handler_has_marker(handler, _HORUS_GUARD_MARKER)


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


def _claude_merge_hook_command() -> dict[str, Any]:
    # PreToolUse gate on `gh pr merge`. The command itself inspects the tool call
    # (stdin) and only blocks a merge while the lanes are stale; everything else
    # passes. `python -m horus` so it doesn't depend on the console script on PATH.
    return {
        "type": "command",
        "command": "python -m horus close --hook",
    }


def _claude_guard_hook_command() -> dict[str, Any]:
    # PreToolUse gate that fires only inside a Horus-hosted PTY session (detected via
    # HORUS_HOSTED_SESSION in the inherited env); it blocks a Bash command that would
    # restart/kill the dashboard process hosting the session. No-op everywhere else.
    return {
        "type": "command",
        "command": "python -m horus guard-host --hook",
    }


def _merge_event_hook(
    hooks: dict[str, Any],
    event: str,
    handler: dict[str, Any],
    *,
    matcher: str = "",
    is_mine: Any = _is_horus_usage_hook,
) -> None:
    """Replace any prior Horus handler for ``event`` (matched by ``is_mine``) with
    ``handler``, under ``matcher``, with no duplicates."""
    groups = hooks.get(event)
    if not isinstance(groups, list):
        groups = []
    for group in groups:
        if isinstance(group, dict) and isinstance(group.get("hooks"), list):
            group["hooks"] = [h for h in group["hooks"] if not is_mine(h)]
    groups = [
        g for g in groups
        if not (isinstance(g, dict) and isinstance(g.get("hooks"), list) and not g["hooks"])
    ]
    groups.append({"matcher": matcher, "hooks": [handler]})
    hooks[event] = groups


def _claude_hooks_dict(project_root: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    path = project_root / ".claude" / "settings.json"
    data = _load_json(path)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        data["hooks"] = hooks
    return path, data, hooks


def _persist_hook(path: Path, data: dict[str, Any], label: str) -> HookAction:
    path.parent.mkdir(parents=True, exist_ok=True)
    new_text = json.dumps(data, indent=2) + "\n"
    old_text = path.read_text(encoding="utf-8") if path.exists() else None
    if old_text == new_text:
        return HookAction("exists", f"{label} already installed in {path}")
    path.write_text(new_text, encoding="utf-8")
    return HookAction("updated" if old_text is not None else "created", f"installed {label} in {path}")


def install_claude_usage_hook(project_root: Path, *, threshold: float = 90.0) -> HookAction:
    """Install/update Claude Code hooks for usage-driven closure.

    `UserPromptSubmit` is the primary trigger — it fires *before* the agent works on a
    new task, so an over-budget session closes instead of starting expensive work.
    `Stop` is kept as a secondary net (close between turns)."""
    path, data, hooks = _claude_hooks_dict(project_root)
    handler = _claude_hook_command(threshold)
    _merge_event_hook(hooks, "UserPromptSubmit", handler)
    _merge_event_hook(hooks, "Stop", handler)
    data["hooks"] = hooks
    return _persist_hook(path, data, "Claude usage hook")


def install_claude_merge_hook(project_root: Path) -> HookAction:
    """Install/update a Claude `PreToolUse` hook that gates `gh pr merge` on the
    closure freshness check — blocks the merge and diverts to consolidation when the
    dashboard lanes are stale. Matches the `Bash` tool; the command filters for the
    merge itself, so non-merge Bash calls pass straight through."""
    path, data, hooks = _claude_hooks_dict(project_root)
    _merge_event_hook(
        hooks, "PreToolUse", _claude_merge_hook_command(),
        matcher="Bash", is_mine=_is_horus_merge_hook,
    )
    data["hooks"] = hooks
    return _persist_hook(path, data, "Claude pre-merge closure hook")


def install_claude_guard_hook(project_root: Path) -> HookAction:
    """Install/update a Claude `PreToolUse` hook that stops a Horus-hosted PTY session
    from restarting/killing the dashboard process hosting it. Matches the `Bash` tool;
    the command no-ops unless run inside a hosted session (HORUS_HOSTED_SESSION), so a
    normal terminal is unaffected. Coexists with the usage + merge hooks (own marker)."""
    path, data, hooks = _claude_hooks_dict(project_root)
    _merge_event_hook(
        hooks, "PreToolUse", _claude_guard_hook_command(),
        matcher="Bash", is_mine=_is_horus_guard_hook,
    )
    data["hooks"] = hooks
    return _persist_hook(path, data, "Claude hosted-session guard hook")


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
