"""Best-effort "what did this worker actually deliver" facts for a session that
ended non-cleanly.

``horus run`` / the registry only record the PROCESS outcome — nonzero exit
("failed"), or a dead/gone pid discovered on reconcile ("stale"). That collapses
two very different real incidents to the same bare word: a worker that pushed
green commits, opened a PR, and closed its own `.horus/` continuity before a
usage emergency killed the launcher process; and a worker that died having
delivered nothing at all. This module derives the DELIVERY facts, post-hoc, from
the session's own known project directory (its checked-out worktree/branch) —
Horus never tracked any of this live, so every probe here is a fresh git/gh
read against whatever is on disk right now.

Best-effort by construction: any missing directory, gone branch, detached HEAD,
or git/gh failure degrades to ``None``/absent facts rather than raising — a
delivery lookup must never crash `horus sessions`.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from horus import gitstate, integration

_NO_WINDOW = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if sys.platform == "win32" else {}

# Statuses a delivery receipt is worth checking for — a process outcome that
# might be hiding real delivered work. Deliberately narrow: "exited" already
# means a clean zero-code finish, nothing to reveal.
NONCLEAN_STATUSES = frozenset({"failed", "stale"})

# Matches this repo's own closure-commit convention (`closure.commit_continuity`'s
# default message, and every closure commit observed in git log), e.g. "Update
# Horus continuity (fleet truth + source attribution, PR #142)".
_CLOSURE_COMMIT_RE = re.compile(r"update horus continuity", re.IGNORECASE)
_GIT_TIMEOUT = 5.0
_CONTINUITY_LOG_DEPTH = 30

# How many of the pushed ref's own ancestor commits to consider when
# time-correlating a session's end to its delivery commit. Deep enough to reach
# past a killed-attempt-then-retry pair sharing one branch, shallow enough to
# stay a cheap local `git log`.
_ATTRIBUTION_LOG_DEPTH = 50


@dataclass(frozen=True)
class DeliveryReceipt:
    branch: str
    pushed_sha: str | None = None
    pr_number: int | None = None
    pr_url: str | None = None
    pr_state: str | None = None
    continuity_closed: bool = False

    @property
    def has_signal(self) -> bool:
        return bool(self.pushed_sha or self.pr_number or self.continuity_closed)


def _git(root: Path, *args: str, timeout: float = _GIT_TIMEOUT) -> str | None:
    try:
        r = subprocess.run(  # noqa: S603
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, timeout=timeout, **_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def _pushed_tip(root: Path, branch: str) -> str | None:
    """The branch's pushed tip, preferring the already-fetched tracking ref (no
    network) and falling back to a live ``ls-remote`` — the worktree may have
    been checked out without ``-u``, or the push happened from elsewhere."""
    tracked = _git(root, "rev-parse", "-q", "--verify", "@{upstream}")
    if tracked:
        return tracked
    remote = _git(root, "ls-remote", "origin", f"refs/heads/{branch}")
    if not remote:
        return None
    parts = remote.split()
    return parts[0] if parts else None


def _pushed_ancestors(root: Path, tip: str, *, depth: int = _ATTRIBUTION_LOG_DEPTH) -> list[tuple[str, datetime]]:
    """``(sha, committer-time)`` pairs for ``tip``'s own ancestry, most recent
    first — every entry here is genuinely on the remote (it's the pushed tip's
    own history), unlike the local branch, which could carry unpushed commits.
    Empty when the objects aren't locally available (e.g. ``tip`` came from a
    bare ``ls-remote`` in a worktree that never fetched it) — degrades to the
    plain-tip behavior rather than raising."""
    log = _git(root, "log", f"-n{depth}", "--format=%H %cI", tip)
    if not log:
        return []
    pairs: list[tuple[str, datetime]] = []
    for line in log.splitlines():
        sha, _, stamp = line.partition(" ")
        if not stamp:
            continue
        try:
            pairs.append((sha, datetime.fromisoformat(stamp)))
        except ValueError:
            continue
    return pairs


def _closest_to(pairs: list[tuple[str, datetime]], moment: datetime) -> str | None:
    """The sha whose commit time is nearest ``moment`` — the session's own
    recorded end time correlated against the delivery commit, so a killed
    attempt and its retry sharing one branch each resolve to their own commit
    instead of both collapsing onto the branch's current tip."""
    if not pairs:
        return None
    return min(pairs, key=lambda pair: abs((pair[1] - moment).total_seconds()))[0]


def _pushed_sha(root: Path, branch: str, *, session_end: datetime | None = None) -> str | None:
    """The delivery commit attributed to this session: the pushed tip by
    default, or — when ``session_end`` is known — whichever of the tip's own
    ancestor commits best correlates with the session's own window."""
    tip = _pushed_tip(root, branch)
    if tip is None or session_end is None:
        return tip
    matched = _closest_to(_pushed_ancestors(root, tip), session_end)
    return matched or tip


def _continuity_closed(root: Path) -> bool:
    """Whether a closure-shaped commit touched ``.horus/`` on this branch, most
    recent commits first — best-effort signal, not a guarantee closure ran."""
    subjects = _git(root, "log", f"-n{_CONTINUITY_LOG_DEPTH}", "--format=%s", "--", ".horus")
    if not subjects:
        return False
    return any(_CLOSURE_COMMIT_RE.search(line) for line in subjects.splitlines())


def delivery_receipt(project_dir: str | Path, *, session_end: datetime | None = None) -> DeliveryReceipt | None:
    """Best-effort delivery facts for the worktree/branch checked out at
    ``project_dir``. ``None`` when there's nothing to say — directory gone, not a
    git worktree, or a detached/unresolvable HEAD — callers fall back to the
    plain status in that case.

    A branch derives delivery facts on its own — imprecise when a killed attempt
    and its retry share one branch (and, in the common case, the same worktree),
    since both would otherwise resolve to whatever is currently at the tip.
    ``session_end`` (the session's own recorded end time) lets the pushed commit
    — and, transitively, the PR built on it — be time-correlated to THIS
    session's window instead of always the branch's current tip.
    """
    try:
        root = Path(project_dir)
        if not root.is_dir():
            return None
        state = gitstate.git_state(root)
        if not state or state.get("detached"):
            return None
        branch = state.get("branch")
        if not branch or branch == "?":
            return None

        pushed_sha = _pushed_sha(root, branch, session_end=session_end)
        pr = integration.pr_for_branch(root, branch, head_sha=pushed_sha)
        continuity_closed = _continuity_closed(root)

        return DeliveryReceipt(
            branch=branch,
            pushed_sha=pushed_sha,
            pr_number=pr.get("number") if pr else None,
            pr_url=pr.get("url") if pr else None,
            pr_state=pr.get("state") if pr else None,
            continuity_closed=continuity_closed,
        )
    except Exception:
        # Never let a delivery lookup take down `horus sessions` — degrade to
        # the plain status, same as an unknowable directory.
        return None


def render_receipt(status: str, receipt: DeliveryReceipt | None) -> str:
    """The ``<status>-but-delivered · pushed <sha> · PR #N · continuity closed``
    suffix, or "" when there's nothing delivered to report (a plain failure)."""
    if receipt is None or not receipt.has_signal:
        return ""
    bits = [f"{status}-but-delivered"]
    if receipt.pushed_sha:
        bits.append(f"pushed {receipt.pushed_sha[:8]}")
    if receipt.pr_number:
        bits.append(f"PR #{receipt.pr_number}")
    if receipt.continuity_closed:
        bits.append("continuity closed")
    return " · ".join(bits)
