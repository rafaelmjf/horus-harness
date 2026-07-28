"""Explicit fast-forward sync — the remedy half of the fetch-first rule.

Fetch-first already fires deterministically at session start
(:mod:`horus.fetchcheck`), but the *remedy* was hand-typed: three surfaces printed
``git pull --ff-only`` for the owner to copy. A session on 2026-07-21 read
continuity 5 commits stale and never saw cards other sessions had left, because
detecting behind-N and acting on it were separate manual steps.

This closes that gap without breaking the hook contract. Hooks advise and ask,
never override, so nothing here runs implicitly: the owner invokes ``horus sync``.
It fast-forwards only when that is unambiguously safe — clean tree, no local
commits, strictly behind — and otherwise refuses with the reason, never mutating
the work tree to force an outcome.

``git merge --ff-only`` is the operation rather than ``git pull``: the fetch has
already happened, so merging the already-fetched upstream ref avoids a second
network round-trip and cannot silently create a merge commit.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

# Decision outcomes. ``current`` and ``synced`` are successes; ``refused`` means
# the caller must resolve something first and nothing was touched.
CURRENT = "current"
SYNCED = "synced"
REFUSED = "refused"

_NO_WINDOW = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if sys.platform == "win32" else {}


def plan(state: dict[str, Any] | None) -> tuple[str, str]:
    """Decide what to do from a :func:`horus.gitstate.git_state` mapping.

    Pure decision, no side effects, so the refusal matrix is testable without a
    repo. Returns ``(outcome, reason)`` where outcome is CURRENT, SYNCED (meaning
    *safe to fast-forward*, not yet done) or REFUSED.
    """
    if not state:
        return REFUSED, "not a git work tree"
    if state.get("detached"):
        return REFUSED, "HEAD is detached — check out a branch first"
    upstream = state.get("upstream")
    if not upstream:
        return REFUSED, "no upstream for the current branch — nothing to sync from"

    behind = state.get("behind") or 0
    ahead = state.get("ahead") or 0

    if behind == 0:
        if ahead:
            return CURRENT, f"already current with {upstream} ({ahead} local commit(s) not pushed)"
        return CURRENT, f"already current with {upstream}"

    # Behind, so a sync is wanted. Everything below is a reason it is not safe.
    if state.get("dirty"):
        return REFUSED, (
            f"{behind} commit(s) behind {upstream}, but the working tree has uncommitted "
            "changes — commit or stash them first"
        )
    if ahead:
        return REFUSED, (
            f"branch has diverged from {upstream} ({ahead} ahead, {behind} behind) — "
            "a fast-forward is impossible; rebase or merge deliberately"
        )
    return SYNCED, f"fast-forwarding {behind} commit(s) to {upstream}"


def fast_forward(root: Path, upstream: str, *, timeout: float = 30.0) -> tuple[bool, str]:
    """Run the fast-forward merge. Returns ``(ok, message)``."""
    try:
        r = subprocess.run(
            ["git", "-C", str(root), "merge", "--ff-only", upstream],
            capture_output=True, text=True, timeout=timeout, **_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"git merge failed to run: {exc}"
    if r.returncode != 0:
        # Never discard stderr on the command whose result drives the outcome.
        detail = (r.stderr or r.stdout or "").strip().splitlines()
        return False, detail[-1] if detail else f"git merge --ff-only exited {r.returncode}"
    return True, (r.stdout or "").strip()
