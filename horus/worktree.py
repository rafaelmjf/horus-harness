"""Git worktree plumbing for ``horus run --worktree <branch>``.

The orchestration pilot's first manual footgun: spinning up a per-worker git
worktree by hand before each ``horus run``. This module turns that into a flag.

Convention (pinned): a worktree for ``<branch>`` lives at
``<repo-parent>/<repo-name>-wt-<branch-slug>`` — a sibling of the repo, never
nested inside it. Create-or-reuse: an existing worktree of *this* repo at that
path is reused as-is; anything else there is a polite refusal. No auto-cleanup
in this slice — remove stale worktrees with ``git worktree remove`` by hand.

Best-effort by the same rules as :mod:`horus.gitstate`: git failures surface as
:class:`WorktreeError` with a user-facing message, never a raw traceback.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Windows: keep each git child from flashing a console window (matches gitstate).
_NO_WINDOW = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if sys.platform == "win32" else {}


class WorktreeError(Exception):
    """A worktree could not be created or reused — carries a message for the user."""


@dataclass(frozen=True)
class WorktreeResult:
    path: Path        # the worktree directory the session should run in
    branch: str       # the branch checked out there
    created: bool     # True if we created it now, False if an existing one was reused


def branch_slug(branch: str) -> str:
    """Filesystem-safe slug for a branch name (``feat/run-worktree`` -> ``feat-run-worktree``)."""
    slug = re.sub(r"[^a-z0-9]+", "-", branch.lower()).strip("-")
    return slug or "worktree"


def _git(root: Path, *args: str, timeout: float = 30.0) -> subprocess.CompletedProcess:
    """Run a git command in ``root``. Raises :class:`WorktreeError` if git is
    absent or the invocation itself blows up (not on a non-zero return code —
    callers decide what a non-zero code means)."""
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, timeout=timeout, **_NO_WINDOW,
        )
    except FileNotFoundError as exc:  # git not installed
        raise WorktreeError("git is not available on PATH — cannot manage worktrees.") from exc
    except (OSError, subprocess.SubprocessError) as exc:
        raise WorktreeError(f"git worktree command failed: {exc}") from exc


def worktree_path(repo: Path, branch: str) -> Path:
    """The pinned target path for ``branch`` — a sibling of the repo root."""
    top = _repo_toplevel(repo)
    return top.parent / f"{top.name}-wt-{branch_slug(branch)}"


def _repo_toplevel(repo: Path) -> Path:
    """The work-tree root for ``repo``, refusing a bare repo or a non-repo path."""
    bare = _git(repo, "rev-parse", "--is-bare-repository")
    if bare.returncode != 0:
        raise WorktreeError(f"{repo} is not a git repository — worktrees need one.")
    if bare.stdout.strip() == "true":
        raise WorktreeError(f"{repo} is a bare git repository — cannot run a session there.")
    top = _git(repo, "rev-parse", "--show-toplevel")
    if top.returncode != 0 or not top.stdout.strip():
        raise WorktreeError(f"{repo} is not inside a git work tree — worktrees need one.")
    return Path(top.stdout.strip())


def _registered_worktrees(repo: Path) -> set[Path]:
    """Resolved paths git currently tracks as worktrees of ``repo`` (incl. the main one)."""
    listing = _git(repo, "worktree", "list", "--porcelain")
    paths: set[Path] = set()
    if listing.returncode != 0:
        return paths
    for line in listing.stdout.splitlines():
        if line.startswith("worktree "):
            try:
                paths.add(Path(line[len("worktree "):].strip()).resolve())
            except OSError:
                pass
    return paths


def _branch_exists(repo: Path, branch: str) -> bool:
    return _git(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}").returncode == 0


def ensure_worktree(repo: Path, branch: str) -> WorktreeResult:
    """Create or reuse the pinned worktree for ``branch`` and return where it lives.

    - Missing branch is created from the current HEAD (``git worktree add -b``).
    - An existing worktree of this repo at the target path is reused untouched.
    - A target path that exists but is *not* a worktree of this repo, a bare
      repo, or a non-git ``repo`` all raise :class:`WorktreeError` with a
      message meant to be shown verbatim to the user.
    """
    top = _repo_toplevel(repo)  # validates git / non-bare up front
    target = top.parent / f"{top.name}-wt-{branch_slug(branch)}"
    resolved_target = target.resolve() if target.exists() else target

    if target.exists():
        if resolved_target in _registered_worktrees(repo):
            return WorktreeResult(path=target, branch=branch, created=False)  # reuse
        raise WorktreeError(
            f"{target} already exists and is not a worktree of this repo — "
            "refusing to touch it. Remove it or pick another branch."
        )

    add_args = ["worktree", "add"]
    if _branch_exists(repo, branch):
        add_args += [str(target), branch]
    else:
        add_args += ["-b", branch, str(target)]  # new branch off current HEAD
    result = _git(repo, *add_args)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip() or "git worktree add failed"
        raise WorktreeError(f"could not create worktree at {target}: {detail}")
    return WorktreeResult(path=target, branch=branch, created=True)
