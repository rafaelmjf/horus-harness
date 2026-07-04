"""Emergency git state-save for the usage-limit survival kit.

Fired by the ``PreToolUse`` usage guard when the 5-hour window is nearly exhausted
(≥97%), so a worker that dies at the limit does not leave uncommitted code stranded.
Two modes, chosen by context — and the choice is load-bearing:

- **Worker context** (a linked git worktree, or the ``HORUS_RUN_WORKER`` env marker
  set by ``horus run --worker``): the branch is disposable, so rescue-commit the
  *full* tree (``git add -A``) to the current branch and best-effort ``git push``.
  Product code is safe because the branch is throwaway and reviewed before merge.

- **Main checkout**: never touch the user's index, HEAD, or working tree. Snapshot
  only ``.horus/**`` into a **rescue ref** (``refs/horus/rescue/<UTC>``) built with a
  *temporary* index (``GIT_INDEX_FILE``). Nothing is staged, checked out, or reset;
  no push. The snapshot is recoverable via the ref, invisible to normal git status.

Best-effort throughout: any git failure is reported in the result, never raised.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

RESCUE_PREFIX = "horus rescue:"
RESCUE_REF_NAMESPACE = "refs/horus/rescue"


class RescueResult(NamedTuple):
    mode: str              # "worker" | "main" | "skipped"
    ref: str | None        # branch (worker) or rescue ref (main); None when nothing saved
    committed: bool
    pushed: bool | None    # worker push outcome; None when a push was not attempted
    detail: str            # human-readable summary for the injected context


def _git(root: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 (fixed argv, no shell)
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        env=env,
    )


def _in_git_repo(root: Path) -> bool:
    r = _git(root, "rev-parse", "--is-inside-work-tree")
    return r.returncode == 0 and r.stdout.strip() == "true"


def is_worker_context(root: Path) -> bool:
    """True when the checkout is a disposable worker tree — safe to rescue-commit whole.

    Two independent signals: the ``HORUS_RUN_WORKER`` env marker exported by
    ``horus run --worker`` (deterministic), and linked-worktree detection (the git
    dir differs from the common dir) as the fallback for sessions not launched via
    ``horus run``."""
    if os.environ.get("HORUS_RUN_WORKER") == "1":
        return True
    gd = _git(root, "rev-parse", "--absolute-git-dir")
    cd = _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if gd.returncode != 0 or cd.returncode != 0:
        return False
    try:
        return Path(gd.stdout.strip()).resolve() != Path(cd.stdout.strip()).resolve()
    except OSError:
        return False


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _current_branch(root: Path) -> str:
    r = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    return r.stdout.strip() if r.returncode == 0 else "HEAD"


def _commit_env(root: Path) -> dict[str, str]:
    """Environment for a rescue commit — inject a fallback identity only when the
    repo has none configured, so the rescue never fails for lack of user.email."""
    env = dict(os.environ)
    email = _git(root, "config", "user.email").stdout.strip()
    if not email:
        env.setdefault("GIT_AUTHOR_NAME", "Horus")
        env.setdefault("GIT_AUTHOR_EMAIL", "horus@localhost")
        env.setdefault("GIT_COMMITTER_NAME", "Horus")
        env.setdefault("GIT_COMMITTER_EMAIL", "horus@localhost")
    return env


def rescue_worker(root: Path, *, session_id: str | None = None) -> RescueResult:
    """Rescue-commit the full worktree to the current branch, then best-effort push."""
    ts = _timestamp()
    branch = _current_branch(root)
    subject = f"{RESCUE_PREFIX} {ts} worker {session_id or branch}"
    env = _commit_env(root)
    _git(root, "add", "-A", env=env)
    # --no-verify: never let a client-side pre-commit hook wedge an emergency save.
    commit = _git(root, "commit", "--no-verify", "-m", subject, env=env)
    committed = commit.returncode == 0
    if not committed:
        return RescueResult("worker", branch, False, None, f"nothing to rescue on branch {branch} (clean tree)")
    push = _push_worker_branch(root, branch, env)
    pushed = push.returncode == 0
    if pushed:
        detail = f"rescue-committed the full worktree to branch {branch} and pushed it"
    else:
        detail = (
            f"rescue-committed the full worktree to branch {branch}; push FAILED "
            f"({push.stderr.strip() or 'unknown error'}) — the commit is local only"
        )
    return RescueResult("worker", branch, True, pushed, detail)


def _push_worker_branch(root: Path, branch: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Push the rescue commit, best-effort. A bare ``git push`` fails when the branch
    has no upstream — which is exactly a fresh ``git worktree add -b`` worker branch,
    the kit's primary "died before it ever pushed" case — so fall back to an explicit
    ``git push -u origin <branch>`` (or ``origin HEAD`` when detached). A missing origin
    or auth failure is still tolerated; the caller reports it in ``detail``."""
    push = _git(root, "push", env=env)
    if push.returncode == 0:
        return push
    if branch and branch != "HEAD":
        return _git(root, "push", "-u", "origin", branch, env=env)
    return _git(root, "push", "origin", "HEAD", env=env)


def rescue_main(root: Path, *, session_id: str | None = None) -> RescueResult:
    """Snapshot ``.horus/**`` to a rescue ref via a temporary index.

    The user's index (``.git/index``), HEAD, and working tree are left byte-identical:
    the whole operation runs against a throwaway ``GIT_INDEX_FILE`` and ends in a
    plain ``update-ref``. No checkout, no reset, no push."""
    ts = _timestamp()
    ref = f"{RESCUE_REF_NAMESPACE}/{ts}"
    if not (root / ".horus").is_dir():
        return RescueResult("main", None, False, None, "no .horus/ directory to rescue")

    tmp = Path(tempfile.mkdtemp(prefix="horus-rescue-idx-"))
    env = _commit_env(root)
    env["GIT_INDEX_FILE"] = str(tmp / "index")
    try:
        add = _git(root, "add", "-A", "--", ".horus", env=env)
        if add.returncode != 0:
            return RescueResult("main", None, False, None, f"git add failed: {add.stderr.strip()}")
        wt = _git(root, "write-tree", env=env)
        if wt.returncode != 0 or not wt.stdout.strip():
            return RescueResult("main", None, False, None, f"write-tree failed: {wt.stderr.strip()}")
        tree = wt.stdout.strip()

        subject = f"{RESCUE_PREFIX} {ts} .horus continuity snapshot"
        args = ["commit-tree", tree, "-m", subject]
        head = _git(root, "rev-parse", "HEAD")
        if head.returncode == 0 and head.stdout.strip():
            args += ["-p", head.stdout.strip()]
        ct = _git(root, *args, env=env)
        if ct.returncode != 0 or not ct.stdout.strip():
            return RescueResult("main", None, False, None, f"commit-tree failed: {ct.stderr.strip()}")
        commit = ct.stdout.strip()

        ur = _git(root, "update-ref", ref, commit)
        if ur.returncode != 0:
            return RescueResult("main", None, False, None, f"update-ref failed: {ur.stderr.strip()}")
        return RescueResult("main", ref, True, None, f"snapshotted .horus/ to {ref} (index/HEAD/worktree untouched)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def emergency_rescue(root: Path, *, session_id: str | None = None) -> RescueResult:
    """Dispatch to the worker or main-checkout rescue based on context."""
    root = Path(root)
    if not _in_git_repo(root):
        return RescueResult("skipped", None, False, None, "not a git repository — no state-save performed")
    if is_worker_context(root):
        return rescue_worker(root, session_id=session_id)
    return rescue_main(root, session_id=session_id)
