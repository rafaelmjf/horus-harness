"""Best-effort git signals for a project directory.

Deterministic freshness layer for the dashboard/CLI — same family as `doctor`
and `close`. No implicit network: behind/ahead come from refs already on disk
(as of the last fetch). Any non-repo, missing dir, or git failure yields None /
partial data and never raises.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

# Unit separator: safe field delimiter for `git log --format` (never in a subject).
_US = "\x1f"


def git_state(root: Path, *, timeout: float = 3.0) -> dict[str, Any] | None:
    """Git overview for ``root``, or None if it isn't a work tree.

    Keys: branch, commit{hash,rel,subject}, dirty(bool), upstream(str|None),
    behind(int|None), ahead(int|None), remote_url(str|None).
    """
    def run(*args: str) -> str | None:
        try:
            r = subprocess.run(
                ["git", "-C", str(root), *args],
                capture_output=True, text=True, timeout=timeout,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return r.stdout.strip() if r.returncode == 0 else None

    if run("rev-parse", "--is-inside-work-tree") != "true":
        return None

    commit: dict[str, str] = {}
    last = run("log", "-1", f"--format=%h{_US}%cr{_US}%s")
    if last:
        parts = last.split(_US)
        if len(parts) == 3:
            commit = {"hash": parts[0], "rel": parts[1], "subject": parts[2]}

    upstream = run("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    behind = ahead = None
    if upstream:
        counts = run("rev-list", "--left-right", "--count", f"{upstream}...HEAD")
        if counts:
            try:
                b, a = counts.split()
                behind, ahead = int(b), int(a)
            except ValueError:
                pass

    return {
        "branch": run("rev-parse", "--abbrev-ref", "HEAD") or "?",
        "commit": commit,
        "dirty": bool(run("status", "--porcelain")),
        "upstream": upstream,
        "behind": behind,
        "ahead": ahead,
        "remote_url": run("remote", "get-url", "origin"),
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
