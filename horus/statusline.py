"""Portable Claude Code status line — the shipped default, no per-machine setup.

The owner's reference was a Linux-only `~/.claude/statusline.sh` (GNU `date`, `jq`,
bash, `/tmp`, `hostname -s`) — un-shippable on macOS/Windows. This renders the same
three rows in pure Python so a fresh install on any of the three OSes gets the same
display by pointing each account's ``settings.json`` at ``horus statusline``:

    "statusLine": { "type": "command", "command": "horus statusline" }

Rows (a row that would be empty is skipped, so it degrades cleanly):
  1. ``user@host:cwd`` (``~`` for ``$HOME``) │ model
  2. ``ctx`` / ``5h`` / ``7d`` meters — bar + percent + ``↻ reset``
  3. ``⎇ branch`` │ ``PR #<n> <review_state>``

The CLI wrapper (``horus statusline``) also RECORDS the pushed ``rate_limits`` into
the shared usage cache in-process, collapsing the bash script's background job +
per-account throttle — Horus's 60s cache makes a throttle pointless. It must never
corrupt the status line: any bad/absent input prints nothing and exits 0.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

# ANSI — matched to the reference script so the shipped default looks identical.
_DIM = "\033[00;90m"
_RESET = "\033[00m"
_GREEN = "\033[01;32m"
_BLUE = "\033[01;34m"
_CYAN = "\033[00;36m"
_YELLOW_B = "\033[00;33m"
_MAGENTA = "\033[00;35m"
_SEP = f"{_DIM}│{_RESET}"

BAR_WIDTH = 8
_BAR_FILLED = "█"
_BAR_EMPTY = "░"


def _pct_color(pct: int) -> str:
    if pct >= 80:
        return "\033[01;31m"   # red
    if pct >= 50:
        return "\033[01;33m"   # yellow
    return "\033[01;32m"       # green


def _as_pct(value: object) -> int | None:
    """Floor a numeric percentage to an int; None for anything non-numeric."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _epoch(value: object, fmt: str) -> str | None:
    """Format a unix-epoch-seconds reset (the shape the statusline pushes) in local
    time. None for a non-numeric/invalid value."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).astimezone().strftime(fmt)
    except (OSError, OverflowError, ValueError):
        return None


def _week_reset(value: object) -> str | None:
    """``%b %-d`` without the GNU-only ``%-d`` (Windows strftime rejects it)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        dt = datetime.fromtimestamp(float(value), tz=timezone.utc).astimezone()
    except (OSError, OverflowError, ValueError):
        return None
    return f"{dt.strftime('%b')} {dt.day}"


def _meter(label: str, pct: int, reset: str | None) -> str:
    """``label ███░░░░░ 42% ↻ 18:19`` — bar rounds up so a non-zero reading never
    renders as an empty bar."""
    pct = max(0, pct)
    filled = min(BAR_WIDTH, (pct * BAR_WIDTH + 99) // 100)
    bar = _BAR_FILLED * filled + _BAR_EMPTY * (BAR_WIDTH - filled)
    out = f"{_DIM}{label} {_pct_color(pct)}{bar} {pct:3d}%{_RESET}"
    if reset:
        out += f" {_DIM}↻ {reset}{_RESET}"
    return out


def _dget(obj: object, *keys: str) -> object:
    """Safe nested dict get: returns None if any level is missing/not a dict."""
    for key in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def git_branch(work_dir: str) -> str | None:
    """Current branch of ``work_dir`` via git, or None (not a repo / no git / detached)."""
    try:
        result = subprocess.run(
            ["git", "-C", work_dir, "--no-optional-locks", "symbolic-ref", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    branch = result.stdout.strip()
    return branch or None


def _row1(payload: dict, *, home: Path, user: str, host: str) -> str | None:
    cwd = _dget(payload, "cwd")
    if not isinstance(cwd, str) or not cwd:
        cwd = str(home)
    try:
        shown = "~" + cwd[len(str(home)):] if cwd.startswith(str(home)) else cwd
    except (TypeError, ValueError):
        shown = cwd
    row = f"{_GREEN}{user}@{host}{_RESET}:{_BLUE}{shown}{_RESET}"
    model = _dget(payload, "model", "display_name")
    if isinstance(model, str) and model:
        row += f" {_SEP} {_CYAN}{model}{_RESET}"
    return row


def _row2(payload: dict) -> str | None:
    segments: list[str] = []
    ctx = _as_pct(_dget(payload, "context_window", "used_percentage"))
    if ctx is not None:
        segments.append(_meter("ctx", ctx, None))
    five = _as_pct(_dget(payload, "rate_limits", "five_hour", "used_percentage"))
    if five is not None:
        segments.append(_meter("5h", five, _epoch(_dget(payload, "rate_limits", "five_hour", "resets_at"), "%H:%M")))
    week = _as_pct(_dget(payload, "rate_limits", "seven_day", "used_percentage"))
    if week is not None:
        segments.append(_meter("7d", week, _week_reset(_dget(payload, "rate_limits", "seven_day", "resets_at"))))
    return f" {_SEP} ".join(segments) if segments else None


_PR_COLORS = {
    "approved": "\033[01;32m",
    "changes_requested": "\033[01;31m",
    "draft": _DIM,
}


def _row3(payload: dict, *, branch_of: Callable[[str], str | None]) -> str | None:
    parts: list[str] = []
    work_dir = _dget(payload, "workspace", "current_dir") or _dget(payload, "cwd")
    if isinstance(work_dir, str) and work_dir and Path(work_dir).is_dir():
        branch = branch_of(work_dir)
        if branch:
            parts.append(f"{_YELLOW_B}⎇ {branch}{_RESET}")
    pr_number = _dget(payload, "pr", "number")
    if isinstance(pr_number, (int, str)) and not isinstance(pr_number, bool) and str(pr_number):
        state = _dget(payload, "pr", "review_state")
        color = _PR_COLORS.get(state, _MAGENTA) if isinstance(state, str) else _MAGENTA
        seg = f"{color}PR #{pr_number}{_RESET}"
        if isinstance(state, str) and state:
            seg += f" {_DIM}{state}{_RESET}"
        parts.append(seg)
    return f" {_SEP} ".join(parts) if parts else None


def render(
    payload: object,
    *,
    home: Path | None = None,
    user: str = "",
    host: str = "",
    branch_of: Callable[[str], str | None] = git_branch,
) -> str:
    """Render the (up to) three status rows for a statusline payload.

    Returns the rows joined by newlines — each row Claude Code renders as its own
    line. Any row that would be empty is omitted. Returns ``""`` for a payload that
    is not a dict, so a bad/absent input prints nothing."""
    if not isinstance(payload, dict):
        return ""
    home = home or Path.home()
    rows = [
        _row1(payload, home=home, user=user, host=host),
        _row2(payload),
        _row3(payload, branch_of=branch_of),
    ]
    return "\n".join(r for r in rows if r)
