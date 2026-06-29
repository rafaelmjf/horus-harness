"""Git/GitHub integration helper for Horus workflow policy.

Performs the policy's integration flow (stage → commit → push → PR → merge)
via git/gh subprocesses.  ALL subprocess calls go through the module-level
``_run`` function so tests can monkeypatch it without hitting real git or GitHub.

Supported integration modes (``policy["integration"]``):
- ``local-only``         — stage + commit; no push, no PR.
- ``direct-push``        — stage + commit + ``git push origin HEAD``.
- ``branch-pr-review``   — feature branch + push + ``gh pr create``; no auto-merge.
- ``branch-pr-automerge``— same as review, then ``gh pr merge --auto --merge``.

When ``policy["commit"] == "manual"`` the helper skips staging/committing and
proceeds with whatever is already at HEAD.  This is intentional: the caller
takes responsibility for having prepared a commit; Horus just handles the
push/PR part.  The same simplification applies across all non-local-only modes.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from horus import config as _config

# Keep git/gh children from flashing a console when the caller (e.g. the
# console-less dashboard server) spawns them on Windows. See gitstate._NO_WINDOW.
_NO_WINDOW = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if sys.platform == "win32" else {}


# ---------------------------------------------------------------------------
# Thin subprocess runner — monkeypatched in tests
# ---------------------------------------------------------------------------

def _run(cmd: list[str], cwd: Any) -> subprocess.CompletedProcess:
    """Run *cmd* in *cwd* and return the CompletedProcess.

    Never raises; a non-zero returncode signals failure to the caller.
    """
    return subprocess.run(  # noqa: S603
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        **_NO_WINDOW,
    )


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IntegrationResult:
    mode: str           # the integration mode used
    committed: bool
    branch: str | None
    pushed: bool
    pr_url: str | None
    merged: bool
    detail: str         # human-readable summary
    ok: bool            # overall success flag


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug(text: str) -> str:
    """Convert *text* into a short kebab-case branch-name slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug[:48] or "change")


def _default_branch(root: Path) -> str:
    """Determine the default remote base branch, falling back to 'main'."""
    result = _run(["git", "symbolic-ref", "refs/remotes/origin/HEAD"], root)
    if result.returncode == 0:
        ref = result.stdout.strip()
        # refs/remotes/origin/main → main
        parts = ref.split("/")
        if len(parts) >= 1:
            return parts[-1]
    return "main"


def _stage_and_commit(root: Path, message: str, files: list[str] | None) -> tuple[bool, str]:
    """Stage *files* (or ``-A``) and create a commit with *message*.

    Returns ``(success, detail)``.
    """
    stage_cmd = ["git", "add"] + (files if files else ["-A"])
    r = _run(stage_cmd, root)
    if r.returncode != 0:
        return False, f"git add failed: {r.stderr.strip()}"
    r = _run(["git", "commit", "-m", message], root)
    if r.returncode != 0:
        return False, f"git commit failed: {r.stderr.strip()}"
    return True, "committed"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def integrate(
    root: str | Path,
    *,
    message: str,
    files: list[str] | None = None,
    branch: str | None = None,
    title: str | None = None,
    body: str | None = None,
    policy: dict[str, str] | None = None,
) -> IntegrationResult:
    """Integrate a change from the working tree according to the workflow policy.

    Parameters
    ----------
    root:
        Repository root directory.
    message:
        Commit message (also used as PR title when *title* is not given).
    files:
        Specific files to stage; ``None`` stages everything (``git add -A``).
    branch:
        Feature-branch name.  Auto-generated from *message* when ``None`` and
        the mode requires a branch.
    title:
        PR title override.  Falls back to *message*.
    body:
        PR body / description.  Falls back to empty string.
    policy:
        Workflow policy dict.  When ``None`` the current config policy is used.

    Returns an ``IntegrationResult``; never raises for expected git/gh failures.
    """
    root = Path(root)
    if policy is None:
        policy = _config.load_workflow_policy()

    mode = policy.get("integration", _config.WORKFLOW_DEFAULTS["integration"])
    do_commit = policy.get("commit", _config.WORKFLOW_DEFAULTS["commit"]) == "auto"

    # -----------------------------------------------------------------------
    # local-only
    # -----------------------------------------------------------------------
    if mode == "local-only":
        if do_commit:
            ok, detail = _stage_and_commit(root, message, files)
            if not ok:
                return IntegrationResult(mode=mode, committed=False, branch=None,
                                         pushed=False, pr_url=None, merged=False,
                                         detail=detail, ok=False)
            return IntegrationResult(mode=mode, committed=True, branch=None,
                                     pushed=False, pr_url=None, merged=False,
                                     detail="committed locally", ok=True)
        return IntegrationResult(mode=mode, committed=False, branch=None,
                                 pushed=False, pr_url=None, merged=False,
                                 detail="commit is manual; nothing staged or committed", ok=True)

    # -----------------------------------------------------------------------
    # direct-push
    # -----------------------------------------------------------------------
    if mode == "direct-push":
        committed = False
        if do_commit:
            ok, detail = _stage_and_commit(root, message, files)
            if not ok:
                return IntegrationResult(mode=mode, committed=False, branch=None,
                                         pushed=False, pr_url=None, merged=False,
                                         detail=detail, ok=False)
            committed = True
        r = _run(["git", "push", "origin", "HEAD"], root)
        if r.returncode != 0:
            return IntegrationResult(mode=mode, committed=committed, branch=None,
                                     pushed=False, pr_url=None, merged=False,
                                     detail=f"git push failed: {r.stderr.strip()}", ok=False)
        return IntegrationResult(mode=mode, committed=committed, branch=None,
                                 pushed=True, pr_url=None, merged=False,
                                 detail="pushed to origin HEAD", ok=True)

    # -----------------------------------------------------------------------
    # branch-pr-review / branch-pr-automerge
    # -----------------------------------------------------------------------
    if mode in ("branch-pr-review", "branch-pr-automerge"):
        effective_branch = branch or f"horus/{_slug(message)}"
        pr_title = title or message
        pr_body = body or ""

        # Create and checkout the branch.
        r = _run(["git", "checkout", "-b", effective_branch], root)
        if r.returncode != 0:
            return IntegrationResult(mode=mode, committed=False, branch=effective_branch,
                                     pushed=False, pr_url=None, merged=False,
                                     detail=f"git checkout -b failed: {r.stderr.strip()}", ok=False)

        committed = False
        if do_commit:
            ok, detail = _stage_and_commit(root, message, files)
            if not ok:
                return IntegrationResult(mode=mode, committed=False, branch=effective_branch,
                                         pushed=False, pr_url=None, merged=False,
                                         detail=detail, ok=False)
            committed = True

        # Push the branch.
        r = _run(["git", "push", "-u", "origin", effective_branch], root)
        if r.returncode != 0:
            return IntegrationResult(mode=mode, committed=committed, branch=effective_branch,
                                     pushed=False, pr_url=None, merged=False,
                                     detail=f"git push failed: {r.stderr.strip()}", ok=False)

        # Create the PR.
        base = _default_branch(root)
        pr_cmd = [
            "gh", "pr", "create",
            "--base", base,
            "--head", effective_branch,
            "--title", pr_title,
            "--body", pr_body,
        ]
        r = _run(pr_cmd, root)
        if r.returncode != 0:
            return IntegrationResult(mode=mode, committed=committed, branch=effective_branch,
                                     pushed=True, pr_url=None, merged=False,
                                     detail=f"gh pr create failed: {r.stderr.strip()}", ok=False)
        pr_url = r.stdout.strip()

        if mode == "branch-pr-review":
            return IntegrationResult(mode=mode, committed=committed, branch=effective_branch,
                                     pushed=True, pr_url=pr_url, merged=False,
                                     detail=f"PR created: {pr_url}", ok=True)

        # branch-pr-automerge: request auto-merge.
        merge_cmd = ["gh", "pr", "merge", "--auto", "--merge", pr_url or effective_branch]
        r = _run(merge_cmd, root)
        if r.returncode != 0:
            return IntegrationResult(mode=mode, committed=committed, branch=effective_branch,
                                     pushed=True, pr_url=pr_url, merged=False,
                                     detail=f"gh pr merge --auto failed: {r.stderr.strip()}", ok=False)
        # gh pr merge --auto schedules the merge for when checks pass; it is not
        # merged immediately in most cases.  We reflect success but merged=False
        # with a clear detail note.
        return IntegrationResult(mode=mode, committed=committed, branch=effective_branch,
                                 pushed=True, pr_url=pr_url, merged=False,
                                 detail=f"auto-merge enabled for PR {pr_url}", ok=True)

    # Unknown mode — should not happen given validated config, but handle it.
    return IntegrationResult(mode=mode, committed=False, branch=None,
                             pushed=False, pr_url=None, merged=False,
                             detail=f"unknown integration mode: {mode!r}", ok=False)
