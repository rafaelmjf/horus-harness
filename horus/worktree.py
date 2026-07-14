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


def primary_checkout(path: Path) -> Path:
    """The PRIMARY checkout for the git work tree at ``path``.

    A linked worktree (e.g. one ``horus run --worktree`` created) resolves back
    to the repo's main checkout — the acceptance-cleanup fix for
    `datum close --card`: a datum's ``project`` field records wherever the run
    actually executed, which is the WORKTREE path when ``--worktree`` was used,
    but the delivered backlog card lives in the primary checkout's own
    `.horus/backlog/` and must be stamped there even after the worktree is
    later removed.

    ``git worktree list --porcelain`` always lists the main working tree first,
    regardless of which worktree the command is run from or what naming
    convention created it (see the git docs) — so this works for a worktree
    made by hand outside :func:`ensure_worktree`'s own ``-wt-<slug>`` scheme.
    Returns ``path`` itself (resolved) when it isn't a git work tree at all, or
    when it already IS the primary checkout — so callers can call this
    unconditionally on any ``datum.project`` without a prior "is this a
    worktree?" check.
    """
    resolved = path.resolve()
    try:
        r = subprocess.run(
            ["git", "-C", str(resolved), "worktree", "list", "--porcelain"],
            capture_output=True, text=True, timeout=10.0, **_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return resolved
    if r.returncode != 0:
        return resolved
    for line in r.stdout.splitlines():
        if line.startswith("worktree "):
            try:
                return Path(line[len("worktree "):].strip()).resolve()
            except OSError:
                return resolved
    return resolved


@dataclass(frozen=True)
class WorktreeRemoval:
    removed: bool
    detail: str


def remove_if_merged(primary: Path, worktree_path: Path, *, timeout: float = 30.0) -> WorktreeRemoval:
    """Remove a linked worktree + its branch, but ONLY when the branch looks
    merged — never a destructive default.

    "Merged" is either signal already trusted elsewhere in Horus (see
    ``gitstate.git_state``'s ``own_upstream_gone``): the branch's own upstream
    shows ``[gone]`` (GitHub deleted it post-merge), or its tip is an ancestor
    of the fetched default branch. Runs ``git worktree remove`` from the
    PRIMARY checkout — removing from inside the worktree itself would delete
    the process's own cwd out from under it.
    """
    if not worktree_path.exists():
        return WorktreeRemoval(removed=False, detail=f"{worktree_path} does not exist — nothing to remove")

    branch_result = _git(worktree_path, "rev-parse", "--abbrev-ref", "HEAD", timeout=timeout)
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None
    if not branch or branch == "HEAD":
        return WorktreeRemoval(
            removed=False,
            detail=f"{worktree_path} is not on a branch (detached HEAD) — refusing to remove",
        )

    track = _git(worktree_path, "for-each-ref", "--format=%(upstream:track)", f"refs/heads/{branch}", timeout=timeout)
    merged = track.returncode == 0 and "[gone]" in track.stdout

    if not merged:
        default = _git(primary, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD", timeout=timeout)
        default_branch = default.stdout.strip().rsplit("/", 1)[-1] if default.returncode == 0 and default.stdout.strip() else None
        if default_branch:
            check = _git(primary, "merge-base", "--is-ancestor", branch, f"origin/{default_branch}", timeout=timeout)
            merged = check.returncode == 0

    if not merged:
        return WorktreeRemoval(
            removed=False,
            detail=f"branch {branch!r} at {worktree_path} does not look merged yet — leaving the worktree in place",
        )

    remove = _git(primary, "worktree", "remove", str(worktree_path), timeout=timeout)
    if remove.returncode != 0:
        detail = (remove.stderr or remove.stdout or "git worktree remove failed").strip()
        return WorktreeRemoval(removed=False, detail=f"could not remove worktree {worktree_path}: {detail}")

    branch_del = _git(primary, "branch", "-D", branch, timeout=timeout)
    note = "" if branch_del.returncode == 0 else f" (branch {branch!r} left in place: {(branch_del.stderr or branch_del.stdout).strip()})"
    return WorktreeRemoval(removed=True, detail=f"removed worktree {worktree_path} and branch {branch!r}{note}")


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
