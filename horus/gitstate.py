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


def _default_branch(run) -> str | None:
    """Short name of the remote's fetched default branch (e.g. "main"), read from
    on-disk refs only — never touches the network (the caller owns any fetch)."""
    symref = run("symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD")
    if symref:
        name = symref.strip()
        prefix = "origin/"
        if name.startswith(prefix):
            return name[len(prefix):]
    # origin/HEAD isn't always set (shallow clones, some CI checkouts) — fall back
    # to whichever conventional default ref actually exists locally.
    for candidate in ("main", "master"):
        if run("show-ref", "--verify", "--quiet", f"refs/remotes/origin/{candidate}") is not None:
            return candidate
    return None


def git_state(root: Path, *, timeout: float = 3.0) -> dict[str, Any] | None:
    """Git overview for ``root``, or None if it isn't a work tree.

    Keys: branch, commit{hash,rel,subject}, dirty(bool), upstream(str|None),
    behind(int|None), ahead(int|None), remote_url(str|None), detached(bool),
    own_upstream_gone(bool) — the checked-out branch's own upstream ref was deleted
    upstream (the merged-PR signature) — default_branch(str|None), and
    default_ahead/default_behind(int|None) — HEAD's divergence from the fetched
    ``origin/<default_branch>``, distinct from ``ahead``/``behind`` which track the
    branch's own (possibly different, possibly gone) upstream.
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
    detached = False
    upstream: str | None = None
    behind = ahead = None
    dirty = False
    for line in status.splitlines():
        if line.startswith("# branch.head "):
            head = line[len("# branch.head "):].strip()
            detached = head == "(detached)"
            branch = head if head and not detached else "?"
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

    own_upstream_gone = False
    if not detached and branch != "?":
        track = run("for-each-ref", "--format=%(upstream:track)", f"refs/heads/{branch}")
        own_upstream_gone = bool(track) and "[gone]" in track

    default_branch = _default_branch(run)
    default_ahead = default_behind = None
    if default_branch:
        counts = run("rev-list", "--left-right", "--count", f"HEAD...origin/{default_branch}")
        if counts:
            parts = counts.split()
            if len(parts) == 2:
                try:
                    default_ahead, default_behind = int(parts[0]), int(parts[1])
                except ValueError:
                    pass

    return {
        "branch": branch,
        "commit": commit,
        "dirty": dirty,
        "upstream": upstream,
        "behind": behind,
        "ahead": ahead,
        "remote_url": remote.strip() if remote else None,
        "detached": detached,
        "own_upstream_gone": own_upstream_gone,
        "default_branch": default_branch,
        "default_ahead": default_ahead,
        "default_behind": default_behind,
    }


def summary(state: dict[str, Any] | None) -> str:
    """One-line text summary (for the CLI peer). Empty string if not a repo.

    Branch/commit/dirty/own-upstream ahead-behind as before, plus the fleet-truth
    signals: a checkout on a merged-and-deleted branch is flagged ("upstream gone")
    rather than rendered as a plain, deceptively-normal branch name, and — when the
    checked-out branch differs from the fetched remote default (or HEAD is
    detached) — its ahead/behind divergence from ``origin/<default>`` is shown too.
    """
    if not state:
        return ""
    if state.get("detached"):
        bits = [f"detached@{state['commit'].get('hash') or '?'}"]
    else:
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
    if state.get("own_upstream_gone"):
        bits.append("⚠ upstream gone")
    default_branch = state.get("default_branch")
    if default_branch and (state.get("detached") or state["branch"] != default_branch):
        da, db = state.get("default_ahead"), state.get("default_behind")
        if da is not None and db is not None:
            bits.append(f"vs {default_branch}: +{da}/-{db}")
    if state["dirty"]:
        bits.append("uncommitted")
    return " · ".join(bits)


def staleness_hint(state: dict[str, Any] | None, *, threshold: int = 3) -> str:
    """"Continuity may be stale" hint, or "" when there's nothing to say.

    Only fires when the checked-out branch IS the fetched remote default and it is
    meaningfully behind origin — the working PRD/roadmap a reader is looking at may
    describe state that's since moved upstream. Advisory only: never parses or
    repairs the continuity prose itself, just points at consolidating.
    """
    if not state or state.get("detached"):
        return ""
    default_branch = state.get("default_branch")
    if not default_branch or state["branch"] != default_branch:
        return ""
    behind = state.get("behind") or 0
    if behind < threshold:
        return ""
    return (
        f"continuity may be stale — local {default_branch} is {behind} commit(s) "
        "behind origin; consider consolidating"
    )


if __name__ == "__main__":  # tiny self-check against this repo
    s = git_state(Path(__file__).resolve().parent.parent)
    assert s and s["branch"], "expected a repo state here"
    print(summary(s))
