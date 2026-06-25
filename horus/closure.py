"""The closure routine.

Before ending a session, verify the work is captured in continuity: `.horus/`
health, instruction-block alignment, and git-aware signals (real-work commits
since the latest session summary, uncommitted continuity files). Optionally
commit the continuity files so durable state is persisted (and can sync).

This is the file-first, verify-first half of the hybrid closure decision: it
checks and reports; the actual summary is written by the in-loop agent following
the printed ritual. No agent is spawned here.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from horus import codex_usage
from horus.continuity import Finding, check_project, recent_sessions
from horus.instructions import check_drift

# Files Horus treats as "continuity" (committed durable state + instruction blocks).
_CONTINUITY_PATHSPEC = [".horus", "AGENTS.md", "CLAUDE.md"]


def _git(root: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def is_git_repo(root: Path) -> bool:
    return _git(root, "rev-parse", "--is-inside-work-tree") == "true"


def _work_commits_since(root: Path, mtime: float) -> int:
    """Commits newer than ``mtime`` that touched files OUTSIDE continuity paths
    (i.e. real work not yet reflected in a session summary)."""
    out = _git(
        root, "log", "--format=%ct", "--", ".",
        ":(exclude).horus", ":(exclude)AGENTS.md", ":(exclude)CLAUDE.md",
    )
    if not out:
        return 0
    return sum(1 for line in out.splitlines() if line.strip().isdigit() and int(line) > mtime)


def closure_status(root: Path, *, usage_threshold: float = 90.0) -> list[Finding]:
    """Compose continuity health + instruction drift + git-aware closure signals."""
    findings = list(check_project(root))
    findings.extend(codex_usage.usage_findings(root, threshold=usage_threshold))

    agents, claude = root / "AGENTS.md", root / "CLAUDE.md"
    if agents.is_file() and claude.is_file():
        report = check_drift(
            agents.read_text(encoding="utf-8"), "AGENTS.md",
            claude.read_text(encoding="utf-8"), "CLAUDE.md",
        )
        if report.status == "aligned":
            findings.append(Finding("ok", "AGENTS.md / CLAUDE.md blocks aligned"))
        else:
            findings.append(
                Finding("warn", f"instruction blocks {report.status}; run `horus reconcile instructions`")
            )

    if is_git_repo(root):
        recent = recent_sessions(root, limit=1)
        if recent:
            n = _work_commits_since(root, recent[0].stat().st_mtime)
            if n:
                findings.append(
                    Finding("warn", f"{n} work commit(s) since the latest session summary; summarize before closing")
                )
            else:
                findings.append(Finding("ok", "session summary is current with work commits"))

        status = _git(root, "status", "--porcelain", "--", *_CONTINUITY_PATHSPEC)
        changed = [line for line in (status or "").splitlines() if line.strip()]
        if changed:
            findings.append(
                Finding("warn", f"{len(changed)} uncommitted continuity file(s); use `horus close --commit`")
            )
        else:
            findings.append(Finding("ok", "continuity files committed"))

    return findings


def commit_continuity(root: Path, message: str | None = None, *, push: bool = False) -> tuple[bool, str]:
    """Stage and commit the continuity files. Returns (did_commit, detail)."""
    if not is_git_repo(root):
        return False, "not a git repository"
    _git(root, "add", "--", *_CONTINUITY_PATHSPEC)
    staged = _git(root, "diff", "--cached", "--name-only", "--", *_CONTINUITY_PATHSPEC)
    if not staged:
        return False, "nothing to commit (continuity already committed)"
    if _git(root, "commit", "-m", message or "Update Horus continuity (closure)") is None:
        return False, "commit failed"
    detail = f"committed {len(staged.splitlines())} file(s)"
    if push:
        branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
        pushed = _git(root, "push", "origin", branch or "HEAD")
        detail += "; pushed" if pushed is not None else "; push failed"
    return True, detail
