"""`horus doctor machine` — the one set of checks to run when the app won't open.

Continuity/instruction doctor sections (see `continuity.py`, `instructions.py`) assume
the CLI and its host machine already work. During a live two-machine test every failure
that actually happened was invisible to those sections: the CLI itself dead on import, a
committed hook erroring on every tool call, or the dashboard refusing to start. This
module is read-only (never mutates anything) and checks the machine-level causes: is the
`horus` console script on PATH, does the running interpreter meet the installed dist's
floor, do committed hook commands resolve, is Tk present, is the VS Code `code` CLI
available, is `gh` authenticated.
"""

from __future__ import annotations

import importlib.metadata
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from horus import native_hooks
from horus.continuity import Finding
from horus.selfupdate import _python_floor

_DIST_NAME = "horus-harness"
_GH_AUTH_TIMEOUT = 5.0


def _console_script_finding() -> Finding:
    if shutil.which("horus") is None:
        return Finding(
            "fail",
            "`horus` console script not found on PATH — committed hook files will error "
            "on every tool call until horus is installed (`uv tool install horus-harness`) "
            "or the hooks are removed (`horus offboard --apply`)",
        )
    return Finding("ok", "`horus` console script on PATH")


def _dist_requires_python(dist_name: str = _DIST_NAME) -> str | None:
    """The installed dist's Requires-Python metadata, or None (e.g. a bare checkout
    with no installed dist). Isolated so tests can monkeypatch it without needing a
    real installed package."""
    try:
        return importlib.metadata.metadata(dist_name).get("Requires-Python")
    except importlib.metadata.PackageNotFoundError:
        return None


def _interpreter_floor_finding() -> Finding | None:
    requires_python = _dist_requires_python()
    if not requires_python:
        return None  # no installed dist (bare checkout) — nothing to compare against
    floor = _python_floor(requires_python)
    if floor is None:
        return None
    floor_str = f"{floor[0]}.{floor[1]}"
    running = sys.version_info[:2]
    if running < floor:
        running_str = f"{running[0]}.{running[1]}"
        return Finding(
            "warn",
            f"running interpreter {running_str} is below horus-harness's requires-python "
            f"floor {floor_str} — `uv tool install`/`upgrade` will silently resolve old "
            f"releases against this interpreter; fix with "
            f"`uv tool install --force --python {floor_str} horus-harness`",
        )
    return Finding("ok", f"interpreter {running[0]}.{running[1]} satisfies requires-python >={floor_str}")


def _iter_hook_commands(data: dict) -> list[str]:
    """Every `type: command` hook's `command` string in a Claude settings.json / Codex
    hooks.json-shaped dict (see `native_hooks.py` for the schema)."""
    commands: list[str] = []
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return commands
    for groups in hooks.values():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            handlers = group.get("hooks")
            if not isinstance(handlers, list):
                continue
            for handler in handlers:
                if not isinstance(handler, dict) or handler.get("type") != "command":
                    continue
                command = handler.get("command")
                if isinstance(command, str) and command.strip():
                    commands.append(command)
    return commands


def _hook_command_findings(root: Path) -> list[Finding]:
    """Fail for each installed hook command whose executable token doesn't resolve.
    Silent (no findings) when the project has no native hook configs installed."""
    findings: list[Finding] = []
    commands: list[str] = []
    for path in (native_hooks.claude_settings_path(root), native_hooks.codex_hooks_path(root)):
        if not path.is_file():
            continue
        commands.extend(_iter_hook_commands(native_hooks._load_json(path)))

    if not commands:
        return findings

    unresolved = []
    for command in commands:
        try:
            token = shlex.split(command)[0]
        except ValueError:
            continue  # unparsable command string — not this check's job to flag
        if shutil.which(token) is None:
            unresolved.append(command)

    if unresolved:
        for command in unresolved:
            findings.append(Finding("fail", f"hook command not resolvable on PATH: {command!r}"))
    else:
        findings.append(Finding("ok", f"{len(commands)} hook command(s) resolvable"))
    return findings


def _tkinter_probe() -> bool:
    """Import probe for tkinter, isolated so tests can monkeypatch it without needing a
    real Tk installation."""
    try:
        import tkinter  # noqa: F401
    except Exception:
        return False
    return True


def _tk_finding() -> Finding:
    if _tkinter_probe():
        return Finding("ok", "tkinter available")
    return Finding(
        "warn",
        "tkinter not available — the mascot/companion needs it; the dashboard still works",
    )


def _code_cli_finding() -> Finding:
    """Presence probe for the VS Code CLI — the launch-in-VS-Code dashboard
    destination shells out to ``code`` (``shutil.which`` covers the per-OS forms:
    ``code`` on POSIX, ``code.cmd`` on Windows via PATHEXT)."""
    if shutil.which("code") is None:
        return Finding(
            "warn",
            "`code` (VS Code CLI) not found on PATH — the dashboard's open-in-VS-Code "
            "launch destination needs it; other launch targets are unaffected",
        )
    return Finding("ok", "`code` (VS Code CLI) on PATH")


def _gh_auth_finding() -> Finding:
    if shutil.which("gh") is None:
        return Finding("warn", "`gh` not found on PATH — GitHub onboarding/catalog features need it")
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=_GH_AUTH_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return Finding("warn", "`gh auth status` could not be run — GitHub onboarding/catalog features need it")
    if result.returncode != 0:
        return Finding("warn", "`gh` not authenticated (run `gh auth login`) — GitHub onboarding/catalog features need it")
    return Finding("ok", "`gh` authenticated")


def machine_findings(root: Path | None = None) -> list[Finding]:
    """Machine-level `horus doctor` findings: is this the machine, not the project,
    getting in the way. Read-only — never mutates anything."""
    findings: list[Finding] = [_console_script_finding()]

    floor_finding = _interpreter_floor_finding()
    if floor_finding is not None:
        findings.append(floor_finding)

    if root is not None:
        findings.extend(_hook_command_findings(root))

    findings.append(_tk_finding())
    findings.append(_code_cli_finding())
    findings.append(_gh_auth_finding())
    return findings
