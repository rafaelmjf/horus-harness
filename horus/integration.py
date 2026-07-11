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

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from horus import config as _config
from horus.continuity import Finding

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


def _has_required_checks(root: Path, base: str) -> bool:
    """True when the base branch demands required status checks — the one case where
    an immediate merge would skip gates auto-merge would have waited for.

    Errs toward False: on free-plan private repos the protection API is unavailable
    (protection can't be configured there at all), which is exactly the fallback
    class — and a wrong False self-corrects because GitHub refuses the direct merge
    of a protected branch anyway."""
    r = _run(
        ["gh", "api", f"repos/{{owner}}/{{repo}}/branches/{base}/protection/required_status_checks"],
        root,
    )
    return r.returncode == 0


# Head-branch prefix `integrate()` generates for its feature branches; the
# open-PR nudge below keys on it, so keep the two in sync.
HORUS_BRANCH_PREFIX = "horus/"
_PR_LIST_TIMEOUT = 5.0


def open_horus_prs(root: str | Path, *, timeout: float = _PR_LIST_TIMEOUT) -> list[dict[str, str]] | None:
    """Open PRs from Horus-created branches (head ``horus/…``), or ``None`` when
    the answer is unknowable (no ``gh``, unauthenticated, no GitHub remote,
    timeout).

    Best-effort read-only probe behind the "continuity PR still open" nudge:
    when a repo's GitHub "Allow auto-merge" setting is off, ``integrate()``'s
    auto-merge request fails or silently never fires, and the PR sits OPEN with
    the continuity stranded on its branch. Never raises.
    """
    if not (Path(root) / ".git").exists():  # covers dirs and worktree files
        return None
    try:
        r = subprocess.run(  # noqa: S603
            ["gh", "pr", "list", "--state", "open", "--json", "headRefName,url,title"],
            cwd=str(Path(root)),
            capture_output=True,
            text=True,
            timeout=timeout,
            **_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    try:
        prs = json.loads(r.stdout or "[]")
    except ValueError:
        return None
    if not isinstance(prs, list):
        return None
    return [
        {
            "branch": str(p.get("headRefName", "")),
            "url": str(p.get("url", "")),
            "title": str(p.get("title", "")),
        }
        for p in prs
        if isinstance(p, dict) and str(p.get("headRefName", "")).startswith(HORUS_BRANCH_PREFIX)
    ]


def pr_for_branch(
    root: str | Path, branch: str, *, head_sha: str | None = None, timeout: float = _PR_LIST_TIMEOUT
) -> dict[str, Any] | None:
    """Any PR (open, merged, or closed) whose head is ``branch``, or ``None`` when
    there is none or the answer is unknowable (no ``gh``, unauthenticated, no
    GitHub remote, timeout).

    Unlike :func:`open_horus_prs` this is not scoped to Horus-created branches —
    it backs the failed-but-delivered receipt, which needs to know about a PR a
    worker opened on ITS OWN branch before its `horus run` process died. A
    branch can carry more than one PR over its life (a killed attempt and its
    retry both pushing to the same branch, each opening their own PR) — when
    ``head_sha`` is given, the PR whose ``headRefOid`` matches it is preferred
    over the newest/first one, so an older PR isn't shadowed by a newer PR on
    the same branch. Never raises.
    """
    if not (Path(root) / ".git").exists():  # covers dirs and worktree files
        return None
    try:
        r = subprocess.run(  # noqa: S603
            ["gh", "pr", "list", "--head", branch, "--state", "all", "--json", "number,url,state,title,headRefOid"],
            cwd=str(Path(root)),
            capture_output=True,
            text=True,
            timeout=timeout,
            **_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    try:
        prs = json.loads(r.stdout or "[]")
    except ValueError:
        return None
    if not isinstance(prs, list) or not prs:
        return None
    pr = prs[0]
    if head_sha:
        matched = next((p for p in prs if isinstance(p, dict) and p.get("headRefOid") == head_sha), None)
        if matched is not None:
            pr = matched
    if not isinstance(pr, dict):
        return None
    number = pr.get("number")
    return {
        "number": number if isinstance(number, int) else None,
        "url": str(pr.get("url", "")),
        "state": str(pr.get("state", "")),
        "title": str(pr.get("title", "")),
    }


def continuity_pr_findings(root: str | Path) -> list[Finding]:
    """Doctor findings for Horus PRs sitting open — one warn per PR, nothing when
    there are none or the state is unknowable (gh absent is `doctor machine`'s
    signal, not this one's)."""
    prs = open_horus_prs(root)
    if not prs:
        return []
    return [
        Finding(
            "warn",
            f"Horus continuity PR still open: {pr['url']} ({pr['branch']}) — merge it "
            'or enable "Allow auto-merge" in the repo settings',
        )
        for pr in prs
    ]


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

        # Once the branch is on the remote, every exit path below returns the
        # clone to the base branch — leaving HEAD on horus/… strands the next
        # session there (seen live in agentic-gym-coach). A failed checkout
        # back is only a warning: the integration itself already succeeded or
        # failed on its own terms.
        def _done(*, pr_url: str | None, merged: bool, detail: str, ok: bool) -> IntegrationResult:
            back = _run(["git", "checkout", base], root)
            if back.returncode != 0:
                detail += f"; warning: could not return to {base}: {back.stderr.strip()}"
            return IntegrationResult(mode=mode, committed=committed, branch=effective_branch,
                                     pushed=True, pr_url=pr_url, merged=merged,
                                     detail=detail, ok=ok)

        pr_cmd = [
            "gh", "pr", "create",
            "--base", base,
            "--head", effective_branch,
            "--title", pr_title,
            "--body", pr_body,
        ]
        r = _run(pr_cmd, root)
        if r.returncode != 0:
            return _done(pr_url=None, merged=False,
                         detail=f"gh pr create failed: {r.stderr.strip()}", ok=False)
        pr_url = r.stdout.strip()

        if mode == "branch-pr-review":
            return _done(pr_url=pr_url, merged=False,
                         detail=f"PR created: {pr_url}", ok=True)

        # branch-pr-automerge: request auto-merge.
        merge_cmd = ["gh", "pr", "merge", "--auto", "--merge", pr_url or effective_branch]
        r = _run(merge_cmd, root)
        if r.returncode != 0:
            # Recurring class, not a misconfiguration: "Allow auto-merge" cannot even
            # be enabled on free-plan private repos (the settings API refuses
            # silently), so every private-repo onboard for a free-plan user lands
            # here. When the base branch demands no required checks, an immediate
            # merge is what auto-merge would have done anyway; otherwise leave the
            # PR open — doctor/dashboard nudge it (continuity_pr_findings).
            auto_err = r.stderr.strip()
            if _has_required_checks(root, base):
                return _done(pr_url=pr_url, merged=False,
                             detail=(f"auto-merge unavailable ({auto_err}); PR left open "
                                     f"for its required checks: {pr_url}"), ok=False)
            r2 = _run(["gh", "pr", "merge", "--merge", pr_url or effective_branch], root)
            if r2.returncode == 0:
                return _done(pr_url=pr_url, merged=True,
                             detail=f"auto-merge unavailable; merged PR directly: {pr_url}", ok=True)
            return _done(pr_url=pr_url, merged=False,
                         detail=(f"gh pr merge --auto failed: {auto_err}; direct merge "
                                 f"also failed: {r2.stderr.strip()}"), ok=False)
        # gh pr merge --auto schedules the merge for when checks pass; it is not
        # merged immediately in most cases.  We reflect success but merged=False
        # with a clear detail note.
        return _done(pr_url=pr_url, merged=False,
                     detail=f"auto-merge enabled for PR {pr_url}", ok=True)

    # Unknown mode — should not happen given validated config, but handle it.
    return IntegrationResult(mode=mode, committed=False, branch=None,
                             pushed=False, pr_url=None, merged=False,
                             detail=f"unknown integration mode: {mode!r}", ok=False)
