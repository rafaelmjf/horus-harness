"""Best-effort git signals for a project directory.

Deterministic freshness layer for the dashboard/CLI — same family as `doctor`
and `close`. No implicit network: behind/ahead come from refs already on disk
(as of the last fetch). Any non-repo, missing dir, or git failure yields None /
partial data and never raises.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

# Unit separator: safe field delimiter for `git log --format` (never in a subject).
_US = "\x1f"
# Windows: keep each git child from flashing a console window. The dashboard makes
# many git calls per refresh, so without this a refresh strobes terminals.
_NO_WINDOW = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if sys.platform == "win32" else {}


def git_state(root: Path, *, timeout: float = 3.0) -> dict[str, Any] | None:
    """Git overview for ``root``, or None if it isn't a work tree.

    Keys: branch, commit{hash,rel,subject}, dirty(bool), upstream(str|None),
    behind(int|None), ahead(int|None), remote_url(str|None).
    """
    def run(*args: str) -> str | None:
        try:
            r = subprocess.run(
                ["git", "-C", str(root), *args],
                capture_output=True, text=True, timeout=timeout, **_NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return r.stdout if r.returncode == 0 else None

    # One status call yields branch, upstream, ahead/behind, AND dirty, and doubles
    # as the work-tree gate (non-zero outside a repo). Collapsing the old 7 git
    # subprocesses to 3 matters most on Windows, where process spawn dominates.
    status = run("status", "--porcelain=v2", "--branch")
    if status is None:
        return None

    branch = "?"
    upstream: str | None = None
    behind = ahead = None
    dirty = False
    for line in status.splitlines():
        if line.startswith("# branch.head "):
            head = line[len("# branch.head "):].strip()
            branch = head if head and head != "(detached)" else "?"
        elif line.startswith("# branch.upstream "):
            upstream = line[len("# branch.upstream "):].strip() or None
        elif line.startswith("# branch.ab "):
            parts = line[len("# branch.ab "):].split()
            try:  # format: "+<ahead> -<behind>"
                ahead = int(parts[0].lstrip("+"))
                behind = int(parts[1].lstrip("-"))
            except (IndexError, ValueError):
                pass
        elif line and not line.startswith("#"):
            dirty = True  # any non-header line is a changed/untracked entry

    commit: dict[str, str] = {}
    last = run("log", "-1", f"--format=%h{_US}%cr{_US}%s")
    if last:
        parts = last.strip().split(_US)
        if len(parts) == 3:
            commit = {"hash": parts[0], "rel": parts[1], "subject": parts[2]}

    remote = run("remote", "get-url", "origin")
    return {
        "branch": branch,
        "commit": commit,
        "dirty": dirty,
        "upstream": upstream,
        "behind": behind,
        "ahead": ahead,
        "remote_url": remote.strip() if remote else None,
    }


def summary(state: dict[str, Any] | None) -> str:
    """One-line text summary (for the CLI peer). Empty string if not a repo."""
    if not state:
        return ""
    bits = [state["branch"]]
    if state["commit"].get("rel"):
        bits.append(state["commit"]["rel"])
    if state["upstream"] is None:
        bits.append("no upstream")
    else:
        if state["behind"]:
            bits.append(f"behind {state['behind']}")
        if state["ahead"]:
            bits.append(f"ahead {state['ahead']}")
    if state["dirty"]:
        bits.append("uncommitted")
    return " · ".join(bits)


if __name__ == "__main__":  # tiny self-check against this repo
    s = git_state(Path(__file__).resolve().parent.parent)
    assert s and s["branch"], "expected a repo state here"
    print(summary(s))
