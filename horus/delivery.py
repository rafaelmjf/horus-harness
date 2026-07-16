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
from datetime import datetime, timezone
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

DELIVERY_STATUSES = frozenset({"delivery-ready", "blocked", "no-op", "failed", "unknown"})


@dataclass(frozen=True)
class DeliveryEvidence:
    """Captured machine facts for the Phase 2 completion classifier.

    The ``*_beyond_base`` values are intentionally transient classifier inputs;
    the flat registry/datum fields retain the underlying facts for later display.
    """

    inspectable: bool
    checked_at: str
    branch: str | None = None
    head_sha: str | None = None
    pushed_sha: str | None = None
    pr_number: int | None = None
    local_changes: bool | None = None
    continuity_closed: bool | None = None
    head_beyond_base: bool | None = None
    pushed_beyond_base: bool | None = None

    def fields(self) -> dict[str, object]:
        return {
            "delivery_branch": self.branch,
            "delivery_head_sha": self.head_sha,
            "delivery_pushed_sha": self.pushed_sha,
            "delivery_pr_number": self.pr_number,
            "delivery_local_changes": self.local_changes,
            "delivery_continuity_closed": self.continuity_closed,
            "delivery_checked_at": self.checked_at,
        }


def classify_delivery(
    status: str, *, delivery_expected: bool, dispatch_base_sha: str | None, evidence: DeliveryEvidence,
) -> str:
    """Classify delivery using only liveness, explicit intent, base, and facts.

    ``delivery-ready`` is evidence for review, never acceptance or merge authority.
    A missing base or probe uncertainty fails safely to ``unknown``.
    """
    if status == "running" or not delivery_expected or not dispatch_base_sha or not evidence.inspectable:
        return "unknown"
    remote = evidence.pushed_beyond_base is True
    local = evidence.local_changes is True
    if status == "exited":
        if remote:
            return "delivery-ready"
        if local:
            return "blocked"
        return "no-op"
    if status in {"failed", "stale"}:
        if remote or local:
            return "blocked"
        return "failed"
    return "unknown"


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


def _checked_git(root: Path, *args: str) -> tuple[bool, str]:
    """Run one git query while retaining whether a negative answer was knowable."""
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(root), *args], capture_output=True, text=True,
            timeout=_GIT_TIMEOUT, **_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return False, ""
    return result.returncode == 0, result.stdout.strip()


def _is_beyond_base(root: Path, base: str, candidate: str) -> bool | None:
    """Whether ``candidate`` is a descendant of, but not equal to, ``base``."""
    if candidate == base:
        return False
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(root), "merge-base", "--is-ancestor", base, candidate],
            capture_output=True, text=True, timeout=_GIT_TIMEOUT, **_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode == 0:
        return True
    if result.returncode == 1:  # a known non-descendant, not a probe failure
        return False
    return None


def _pushed_tip_checked(root: Path, branch: str) -> tuple[bool, str | None]:
    """Return ``(inspectable, pushed tip)``; an absent remote branch is knowable."""
    ok, tracked = _checked_git(root, "rev-parse", "-q", "--verify", "@{upstream}")
    if ok:
        return True, tracked or None
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(root), "ls-remote", "origin", f"refs/heads/{branch}"],
            capture_output=True, text=True, timeout=_GIT_TIMEOUT, **_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return False, None
    if result.returncode != 0:
        return False, None
    parts = result.stdout.split()
    return True, parts[0] if parts else None


def capture_delivery_evidence(
    project_dir: str | Path, *, dispatch_base_sha: str | None, session_end: datetime | None = None,
) -> DeliveryEvidence:
    """Capture delivery facts without classifying or inferring user intent."""
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    root = Path(project_dir)
    if not root.is_dir():
        return DeliveryEvidence(False, checked_at)
    state = gitstate.git_state(root)
    if not state or state.get("detached"):
        return DeliveryEvidence(False, checked_at)
    branch = state.get("branch")
    if not isinstance(branch, str) or not branch or branch == "?":
        return DeliveryEvidence(False, checked_at)
    head_ok, head = _checked_git(root, "rev-parse", "HEAD")
    if not head_ok or not head:
        return DeliveryEvidence(False, checked_at, branch=branch)
    pushed_ok, pushed_tip = _pushed_tip_checked(root, branch)
    # Existing time correlation prevents two attempts sharing a branch from both
    # receiving its latest remote commit.  If its ancestry cannot be read, retain
    # the known pushed tip rather than inventing a different attribution.
    pushed_sha = _pushed_sha(root, branch, session_end=session_end) if pushed_tip else None
    pushed_sha = pushed_sha or pushed_tip
    head_beyond = _is_beyond_base(root, dispatch_base_sha, head) if dispatch_base_sha else None
    pushed_beyond = (
        _is_beyond_base(root, dispatch_base_sha, pushed_sha)
        if dispatch_base_sha and pushed_sha else False if dispatch_base_sha else None
    )
    # Completion evidence cannot attribute a PR just because it shares a
    # branch: its head must be the same commit attributed to this run.  The
    # legacy receipt intentionally retains its branch-match fallback.
    pr = integration.pr_for_branch(root, branch, head_sha=pushed_sha, exact_head=True) if pushed_sha else None
    # A clean rewrite/non-descendant is still local evidence.  ``head_beyond``
    # distinguishes legitimate descendants from a known non-descendant, but
    # either non-base HEAD differs from the dispatched starting point.
    local_changes = bool(state.get("dirty")) or head != dispatch_base_sha
    inspectable = bool(dispatch_base_sha and pushed_ok and head_beyond is not None and pushed_beyond is not None)
    return DeliveryEvidence(
        inspectable, checked_at, branch=branch, head_sha=head, pushed_sha=pushed_sha,
        pr_number=pr.get("number") if pr else None, local_changes=local_changes,
        continuity_closed=_continuity_closed(root), head_beyond_base=head_beyond,
        pushed_beyond_base=pushed_beyond,
    )


def delivery_receipt(
    project_dir: str | Path, *, dispatch_base_sha: str | None = None,
    session_end: datetime | None = None,
) -> DeliveryReceipt | None:
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

    With a known ``dispatch_base_sha`` only work BEYOND that base counts as this
    session's delivery: a branch resting exactly at its dispatch base carries the
    base's own commits — including a closure-shaped HEAD when the base itself was a
    continuity-closure commit — which a worker that never committed did not produce.
    Without a base the legacy best-effort facts are returned unchanged.
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

        head_beyond: bool | None = None
        if dispatch_base_sha:
            head_ok, head = _checked_git(root, "rev-parse", "HEAD")
            head_beyond = _is_beyond_base(root, dispatch_base_sha, head) if head_ok and head else None
            if head_beyond is not True and not state.get("dirty"):
                # The branch never advanced past the dispatched base — this session
                # delivered nothing; do not attribute the base's own commits to it.
                return DeliveryReceipt(branch=branch)

        pushed_sha = _pushed_sha(root, branch, session_end=session_end)
        if dispatch_base_sha:
            if pushed_sha and _is_beyond_base(root, dispatch_base_sha, pushed_sha) is not True:
                # A pushed tip at/behind base predates this run — not its delivery.
                pushed_sha = None
            # No branch-match PR fallback here: only a commit beyond base is this run's.
            pr = integration.pr_for_branch(root, branch, head_sha=pushed_sha) if pushed_sha else None
            # A closure-shaped commit is this run's only when the branch advanced past base.
            continuity_closed = _continuity_closed(root) if head_beyond is True else False
        else:
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
