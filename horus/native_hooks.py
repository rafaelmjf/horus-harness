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
_HORUS_USAGE_GUARD_MARKER = "horus usage guard"
_HORUS_CHECKPOINT_MARKER = "horus checkpoint --hook"

# Claude's shell surface is two tools: Bash everywhere, plus a PowerShell tool that
# agents prefer on Windows. A "Bash"-only matcher silently skips every shell guard
# there (field-observed in fabric, 2026-07-08), so Claude shell matchers must cover
# both — matchers are regex on the tool name. Codex keeps its own single-tool matcher.
SHELL_TOOL_NAMES = ("Bash", "PowerShell")
SHELL_TOOL_MATCHER = "|".join(SHELL_TOOL_NAMES)


# Committed hook files reach every machine and collaborator the repo does, including
# ones without Horus installed — there a bare `horus …` command errors on every single
# tool call. The guards below turn a missing (or dead-on-import) CLI into a silent
# no-op; `horus doctor machine` / the dashboard stay the visible "hooks installed but
# CLI unavailable" signal. Guard invariant: every Horus hook signals decisions via
# stdout JSON and exits 0, so forcing exit 0 can never mask a real block/deny — keep
# it that way (an exit-code-2 hook would be swallowed by these guards).

def _guard_posix(command: str) -> str:
    # Valid under `sh -c` (macOS/Linux) and Git Bash — the shells Claude Code runs
    # hook commands through (Windows falls back to PowerShell only when Git Bash is
    # absent) and the POSIX path for Codex `command` entries.
    return f"{command} || exit 0"


def _guard_windows(command: str) -> str:
    # Codex runs `commandWindows` through PowerShell, where `||` is PS7-only syntax;
    # Get-Command is the PS 5.1-safe presence probe, and the trailing `exit 0`
    # silences a CLI that exists but crashes.
    return f"if (Get-Command horus -ErrorAction SilentlyContinue) {{ {command} }}; exit 0"


def _codex_hook_command(threshold: float) -> dict[str, Any]:
    # The `horus` console script is the one spelling that works on every machine
    # these committed hook files reach (uv puts it on PATH); interpreter-prefixed
    # forms (`python3 -m` / `py -m`) need horus importable in the ambient python,
    # which the uv tool env's isolation prevents. `commandWindows` differs only in
    # guard syntax (PowerShell), not in spelling.
    command = f"horus usage check --path . --threshold {threshold:g} --hook"
    return {
        "type": "command",
        "command": _guard_posix(command),
        "commandWindows": _guard_windows(command),
        "timeout": 30,
        "statusMessage": "Checking Horus usage",
    }


def _codex_merge_hook_command() -> dict[str, Any]:
    return {
        "type": "command",
        "command": _guard_posix("horus close --hook"),
        "commandWindows": _guard_windows("horus close --hook"),
        "timeout": 30,
        "statusMessage": "Checking Horus closure",
    }


def _codex_guard_hook_command() -> dict[str, Any]:
    return {
        "type": "command",
        "command": _guard_posix("horus guard-host --hook"),
        "commandWindows": _guard_windows("horus guard-host --hook"),
        "timeout": 30,
        "statusMessage": "Checking Horus host safety",
    }


def _codex_usage_guard_hook_command() -> dict[str, Any]:
    command = "horus usage guard --target codex --hook"
    return {
        "type": "command",
        "command": _guard_posix(command),
        "commandWindows": _guard_windows(command),
        "timeout": 30,
        "statusMessage": "Checking Horus usage guard",
    }


def _codex_checkpoint_hook_command() -> dict[str, Any]:
    # Stop-event gate: on session end, warns (default) when the working tree is dirty
    # or has unpushed commits. Same `horus` console-script spelling as every other
    # committed hook; POSIX + PowerShell guards keep it a silent no-op without the CLI.
    command = "horus checkpoint --hook"
    return {
        "type": "command",
        "command": _guard_posix(command),
        "commandWindows": _guard_windows(command),
        "timeout": 30,
        "statusMessage": "Checking Horus checkpoint",
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


def _is_horus_usage_guard_hook(handler: Any) -> bool:
    return _handler_has_marker(handler, _HORUS_USAGE_GUARD_MARKER)


def _is_horus_checkpoint_hook(handler: Any) -> bool:
    return _handler_has_marker(handler, _HORUS_CHECKPOINT_MARKER)


def _merge_codex_usage_hook(hooks: dict[str, Any], event: str, threshold: float) -> None:
    _merge_codex_stop_hook(hooks, event, _codex_hook_command(threshold), _is_horus_usage_hook)


def _merge_codex_stop_hook(
    hooks: dict[str, Any], event: str, handler: dict[str, Any], is_mine: Any
) -> None:
    """Replace any prior Horus handler (matched by ``is_mine``) for a Codex turn-boundary
    event with ``handler`` *in place*, appending a new group only when none is found.

    Position-stable on purpose: two Horus hooks can share one event (usage + checkpoint
    both live on ``Stop``), and a remove-then-append merge would reorder the groups on
    every re-run, so `upgrade-project` / projection-sync would report a perpetual
    "would-update". Preserves non-Horus hooks and drops groups left empty."""
    groups = hooks.get(event)
    if not isinstance(groups, list):
        groups = []
    inserted = False
    new_groups = []
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
            new_groups.append(group)
            continue
        kept = []
        for existing in group["hooks"]:
            if is_mine(existing):
                if not inserted:
                    kept.append(handler)
                    inserted = True
            else:
                kept.append(existing)
        if kept:
            group["hooks"] = kept
            new_groups.append(group)
    if not inserted:
        new_groups.append({"hooks": [handler]})
    hooks[event] = new_groups


def _merge_codex_pretooluse_hook(
    hooks: dict[str, Any],
    handler: dict[str, Any],
    *,
    is_mine: Any = _is_horus_merge_hook,
    matcher: str = "Bash",
) -> None:
    groups = hooks.setdefault("PreToolUse", [])
    if not isinstance(groups, list):
        groups = []

    inserted = False
    new_groups = []
    for group in groups:
        if not isinstance(group, dict):
            new_groups.append(group)
            continue
        handlers = group.get("hooks")
        if not isinstance(handlers, list):
            new_groups.append(group)
            continue
        # A prior handler sitting under a *different* matcher is dropped here and
        # re-homed below — otherwise a matcher fix never reaches repos scaffolded
        # under the old value (the group keeps its stale matcher forever).
        same_matcher = str(group.get("matcher", "")) == matcher
        kept = []
        for existing in handlers:
            if is_mine(existing):
                if same_matcher and not inserted:
                    kept.append(handler)
                    inserted = True
            else:
                kept.append(existing)
        if kept:
            group["hooks"] = kept
            new_groups.append(group)

    if not inserted:
        new_groups.append({"matcher": matcher, "hooks": [handler]})
    hooks["PreToolUse"] = new_groups


def install_codex_usage_hook(project_root: Path, *, threshold: float = 90.0) -> HookAction:
    """Install/update project-local Codex hooks for usage checks."""
    codex_dir = project_root / ".codex"
    path = codex_dir / "hooks.json"
    data = _load_json(path)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        data["hooks"] = hooks

    # UserPromptSubmit is the primary pre-task diversion; Stop is the safety net
    # between turns if the session crossed the threshold during the just-finished turn.
    _merge_codex_usage_hook(hooks, "UserPromptSubmit", threshold)
    _merge_codex_usage_hook(hooks, "Stop", threshold)
    data["hooks"] = hooks

    codex_dir.mkdir(parents=True, exist_ok=True)
    new_text = json.dumps(data, indent=2) + "\n"
    old_text = path.read_text(encoding="utf-8") if path.exists() else None
    if old_text == new_text:
        return HookAction("exists", f"Codex usage hook already installed in {path}")
    path.write_text(new_text, encoding="utf-8")
    return HookAction("updated" if old_text is not None else "created", f"installed Codex usage hook in {path}")


def install_codex_merge_hook(project_root: Path) -> HookAction:
    """Install/update a project-local Codex PreToolUse gate for `gh pr merge`."""
    codex_dir = project_root / ".codex"
    path = codex_dir / "hooks.json"
    data = _load_json(path)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        data["hooks"] = hooks

    _merge_codex_pretooluse_hook(hooks, _codex_merge_hook_command())
    data["hooks"] = hooks

    codex_dir.mkdir(parents=True, exist_ok=True)
    new_text = json.dumps(data, indent=2) + "\n"
    old_text = path.read_text(encoding="utf-8") if path.exists() else None
    if old_text == new_text:
        return HookAction("exists", f"Codex pre-merge closure hook already installed in {path}")
    path.write_text(new_text, encoding="utf-8")
    return HookAction("updated" if old_text is not None else "created", f"installed Codex pre-merge closure hook in {path}")


def install_codex_guard_hook(project_root: Path) -> HookAction:
    """Install/update a project-local Codex PreToolUse guard for hosted PTY sessions."""
    codex_dir = project_root / ".codex"
    path = codex_dir / "hooks.json"
    data = _load_json(path)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        data["hooks"] = hooks

    _merge_codex_pretooluse_hook(hooks, _codex_guard_hook_command(), is_mine=_is_horus_guard_hook)
    data["hooks"] = hooks

    codex_dir.mkdir(parents=True, exist_ok=True)
    new_text = json.dumps(data, indent=2) + "\n"
    old_text = path.read_text(encoding="utf-8") if path.exists() else None
    if old_text == new_text:
        return HookAction("exists", f"Codex hosted-session guard hook already installed in {path}")
    path.write_text(new_text, encoding="utf-8")
    return HookAction("updated" if old_text is not None else "created", f"installed Codex hosted-session guard hook in {path}")


def install_codex_usage_guard_hook(project_root: Path) -> HookAction:
    """Install/update a project-local Codex PreToolUse usage guard (empty matcher, so
    it fires on every tool call). Near the limit it injects an advisory; at the
    emergency threshold it performs a worker-aware emergency state-save — never denies."""
    codex_dir = project_root / ".codex"
    path = codex_dir / "hooks.json"
    data = _load_json(path)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        data["hooks"] = hooks

    _merge_codex_pretooluse_hook(
        hooks, _codex_usage_guard_hook_command(), is_mine=_is_horus_usage_guard_hook, matcher="",
    )
    data["hooks"] = hooks

    codex_dir.mkdir(parents=True, exist_ok=True)
    new_text = json.dumps(data, indent=2) + "\n"
    old_text = path.read_text(encoding="utf-8") if path.exists() else None
    if old_text == new_text:
        return HookAction("exists", f"Codex usage guard hook already installed in {path}")
    path.write_text(new_text, encoding="utf-8")
    return HookAction("updated" if old_text is not None else "created", f"installed Codex usage guard hook in {path}")


def install_codex_checkpoint_hook(project_root: Path) -> HookAction:
    """Install/update a project-local Codex Stop hook that, on session end, warns when
    the working tree is dirty or has unpushed commits (the committed-and-pushed
    checkpoint discipline, enforced not remembered). Warn-only; never blocks a stop."""
    codex_dir = project_root / ".codex"
    path = codex_dir / "hooks.json"
    data = _load_json(path)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        data["hooks"] = hooks

    _merge_codex_stop_hook(hooks, "Stop", _codex_checkpoint_hook_command(), _is_horus_checkpoint_hook)
    data["hooks"] = hooks

    codex_dir.mkdir(parents=True, exist_ok=True)
    new_text = json.dumps(data, indent=2) + "\n"
    old_text = path.read_text(encoding="utf-8") if path.exists() else None
    if old_text == new_text:
        return HookAction("exists", f"Codex checkpoint hook already installed in {path}")
    path.write_text(new_text, encoding="utf-8")
    return HookAction("updated" if old_text is not None else "created", f"installed Codex checkpoint hook in {path}")


# --------------------------------------------------------------------------- #
# Claude Code
# --------------------------------------------------------------------------- #

def _claude_hook_command(threshold: float) -> dict[str, Any]:
    # These hook files are committed and travel across machines, so the command
    # must be the `horus` console script (uv puts it on PATH everywhere): a bare
    # `python`/`python3 -m horus` needs horus importable in the *ambient* python,
    # which the uv tool env's isolation prevents — and Linux has no `python`.
    # (`python -m` only worked inside this repo because it prepends the cwd.)
    # Claude's hook schema has a single command string; the POSIX guard also covers
    # Windows because Claude runs hooks through Git Bash there.
    return {
        "type": "command",
        "command": _guard_posix(f"horus usage check --target claude --hook --threshold {threshold:g}"),
    }


def _claude_merge_hook_command() -> dict[str, Any]:
    # PreToolUse gate on `gh pr merge`. The command itself inspects the tool call
    # (stdin) and only blocks a merge while the lanes are stale; everything else
    # passes.
    return {
        "type": "command",
        "command": _guard_posix("horus close --hook"),
    }


def _claude_guard_hook_command() -> dict[str, Any]:
    # PreToolUse gate that fires only inside a Horus-hosted PTY session (detected via
    # HORUS_HOSTED_SESSION in the inherited env); it blocks a Bash command that would
    # restart/kill the dashboard process hosting the session. No-op everywhere else.
    return {
        "type": "command",
        "command": _guard_posix("horus guard-host --hook"),
    }


def _claude_usage_guard_hook_command() -> dict[str, Any]:
    # PreToolUse usage guard (empty matcher -> every tool call). Reads the cached
    # usage snapshot; near the limit it injects an advisory, and at the emergency
    # threshold it performs a worker-aware emergency state-save. It never denies a
    # tool call, so the exit-0 guard can never swallow a real block.
    return {
        "type": "command",
        "command": _guard_posix("horus usage guard --target claude --hook"),
    }


def _claude_checkpoint_hook_command() -> dict[str, Any]:
    # Stop-event gate. On session end it warns (default) when the working tree is dirty
    # or has unpushed commits — the committed-and-pushed checkpoint discipline as an
    # observed signal. Warn-only by default; never blocks a stop unless installed with
    # `--block` (reserved for repos that opt into hard enforcement).
    return {
        "type": "command",
        "command": _guard_posix("horus checkpoint --hook"),
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
    ``handler``, under ``matcher``, with no duplicates. A prior handler found under a
    different matcher is moved into a group carrying the desired one, so matcher fixes
    propagate to repos scaffolded under the old value."""
    groups = hooks.get(event)
    if not isinstance(groups, list):
        groups = []
    inserted = False
    new_groups = []
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
            new_groups.append(group)
            continue
        same_matcher = str(group.get("matcher", "")) == matcher
        kept = []
        for existing in group["hooks"]:
            if is_mine(existing):
                if same_matcher and not inserted:
                    kept.append(handler)
                    inserted = True
            else:
                kept.append(existing)
        if kept:
            group["hooks"] = kept
            new_groups.append(group)
    if not inserted:
        new_groups.append({"matcher": matcher, "hooks": [handler]})
    hooks[event] = new_groups


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
        matcher=SHELL_TOOL_MATCHER, is_mine=_is_horus_merge_hook,
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
        matcher=SHELL_TOOL_MATCHER, is_mine=_is_horus_guard_hook,
    )
    data["hooks"] = hooks
    return _persist_hook(path, data, "Claude hosted-session guard hook")


def install_claude_usage_guard_hook(project_root: Path) -> HookAction:
    """Install/update a Claude `PreToolUse` usage guard. Empty matcher, so it fires on
    every tool call — a single long turn cannot sail past the advisory. Near the limit
    it injects an advisory; at the emergency threshold it performs a worker-aware
    emergency state-save. It never denies a tool call. Coexists with the merge + host
    guard PreToolUse hooks (own marker)."""
    path, data, hooks = _claude_hooks_dict(project_root)
    _merge_event_hook(
        hooks, "PreToolUse", _claude_usage_guard_hook_command(),
        matcher="", is_mine=_is_horus_usage_guard_hook,
    )
    data["hooks"] = hooks
    return _persist_hook(path, data, "Claude usage guard hook")


def install_claude_checkpoint_hook(project_root: Path) -> HookAction:
    """Install/update a Claude `Stop` hook that, on session end, warns when the working
    tree is dirty or has unpushed commits — the committed-and-pushed checkpoint
    discipline enforced in tooling, not left to memory. Warn-only by default (a
    non-blocking notice); the command supports `--block` for repos that opt into hard
    enforcement, but the installed default never blocks a stop. Coexists with the usage
    Stop hook (own marker)."""
    path, data, hooks = _claude_hooks_dict(project_root)
    _merge_event_hook(
        hooks, "Stop", _claude_checkpoint_hook_command(), is_mine=_is_horus_checkpoint_hook,
    )
    data["hooks"] = hooks
    return _persist_hook(path, data, "Claude checkpoint hook")


# The full per-target hook set — the single list `init`, `upgrade-project`, and any
# other bulk installer should iterate so no surface gets a partial projection.
HOOK_INSTALLERS = {
    "claude": (
        install_claude_usage_hook,
        install_claude_merge_hook,
        install_claude_guard_hook,
        install_claude_usage_guard_hook,
        install_claude_checkpoint_hook,
    ),
    "codex": (
        install_codex_usage_hook,
        install_codex_merge_hook,
        install_codex_guard_hook,
        install_codex_usage_guard_hook,
        install_codex_checkpoint_hook,
    ),
}


# --------------------------------------------------------------------------- #
# Removal (offboarding) — strip Horus hook handlers, keep everything else
# --------------------------------------------------------------------------- #

def _is_any_horus_hook(handler: Any) -> bool:
    return (
        _is_horus_usage_hook(handler)
        or _is_horus_merge_hook(handler)
        or _is_horus_guard_hook(handler)
        or _is_horus_usage_guard_hook(handler)
        or _is_horus_checkpoint_hook(handler)
    )


def _strip_horus_hooks(hooks: dict[str, Any]) -> int:
    """Remove every Horus hook handler from a hooks dict in place (any event), drop
    groups left empty, and remove events left with no groups. Returns the count removed.
    Non-Horus hooks are preserved untouched."""
    removed = 0
    for event in list(hooks.keys()):
        groups = hooks.get(event)
        if not isinstance(groups, list):
            continue
        new_groups: list[Any] = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                new_groups.append(group)
                continue
            kept = [h for h in group["hooks"] if not _is_any_horus_hook(h)]
            removed += len(group["hooks"]) - len(kept)
            if kept:
                group["hooks"] = kept
                new_groups.append(group)
        if new_groups:
            hooks[event] = new_groups
        else:
            del hooks[event]
    return removed


def file_has_horus_hooks(path: Path) -> bool:
    """True if ``path`` (a Claude settings.json or Codex hooks.json) contains any Horus
    hook handler. Used for offboard dry-run reporting."""
    data = _load_json(path)
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return False
    for groups in hooks.values():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if isinstance(group, dict) and isinstance(group.get("hooks"), list):
                if any(_is_any_horus_hook(h) for h in group["hooks"]):
                    return True
    return False


def _remove_hooks_file(path: Path, label: str) -> HookAction:
    if not path.exists():
        return HookAction("absent", f"no {label} hooks file at {path}")
    data = _load_json(path)
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return HookAction("absent", f"no {label} hooks to remove in {path}")
    n = _strip_horus_hooks(hooks)
    if n == 0:
        return HookAction("absent", f"no Horus {label} hooks present in {path}")
    if not hooks:
        data.pop("hooks", None)  # leave other settings intact; drop only an emptied hooks map
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return HookAction("removed", f"removed {n} Horus {label} hook handler(s) from {path}")


def remove_claude_hooks(project_root: Path) -> HookAction:
    """Strip Horus hooks from ``.claude/settings.json`` (keeps non-Horus settings/hooks)."""
    return _remove_hooks_file(project_root / ".claude" / "settings.json", "Claude")


def remove_codex_hooks(project_root: Path) -> HookAction:
    """Strip Horus hooks from ``.codex/hooks.json`` (keeps non-Horus hooks)."""
    return _remove_hooks_file(project_root / ".codex" / "hooks.json", "Codex")


def claude_settings_path(project_root: Path) -> Path:
    return project_root / ".claude" / "settings.json"


def codex_hooks_path(project_root: Path) -> Path:
    return project_root / ".codex" / "hooks.json"


# --------------------------------------------------------------------------- #
# Per-session closure sentinel (fire the closure injection once per session)
# --------------------------------------------------------------------------- #

# Re-arm window: after firing, stay quiet for this long, then allow firing again.
# Prevents a within-turn loop without permanently suppressing a long session.
REARM_SECONDS = 1800.0
# The emergency state-save fires at most once per usage window (~5h) per session,
# so its re-arm spans the whole window rather than the short advisory re-arm.
RESCUE_REARM_SECONDS = 6 * 3600.0


def _sentinel_path(session_id: str, kind: str = "closure") -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id or "unknown")[:80]
    return Path(tempfile.gettempdir()) / f"horus-{kind}-{safe}"


def sentinel_fired(session_id: str, *, kind: str = "closure", rearm_seconds: float = REARM_SECONDS) -> bool:
    """True if the ``kind`` sentinel fired for this session within the re-arm window.

    A per-``kind`` marker keeps independent hooks from suppressing each other — the
    PreToolUse guard's advisory/rescue markers do not share the Stop hook's closure
    marker."""
    path = _sentinel_path(session_id, kind)
    try:
        last = float(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False
    return (time.time() - last) < rearm_seconds


def mark_sentinel_fired(session_id: str, *, kind: str = "closure") -> None:
    try:
        _sentinel_path(session_id, kind).write_text(f"{time.time():.0f}", encoding="utf-8")
    except OSError:
        pass


def closure_already_fired(session_id: str, *, rearm_seconds: float = REARM_SECONDS) -> bool:
    """True if closure fired for this session within the re-arm window."""
    return sentinel_fired(session_id, kind="closure", rearm_seconds=rearm_seconds)


def mark_closure_fired(session_id: str) -> None:
    mark_sentinel_fired(session_id, kind="closure")
