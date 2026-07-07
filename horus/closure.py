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

from horus import codex_usage, frontmatter, routines
from horus.continuity import Finding, check_project, recent_sessions
from horus.instructions import check_drift

# Projected agent artifacts (hooks + skills) are committed, not gitignored — they
# must reach every machine the repo does, and the missing-CLI hook guards make them
# safe on machines without Horus. Specific paths rather than whole directories, so
# user-local files (e.g. .claude/settings.local.json) are never staged.
PROJECTED_ARTIFACT_PATHS = [
    ".claude/settings.json",
    ".claude/skills",
    ".agents/skills",
    ".codex/hooks.json",
]

# Files Horus treats as "continuity" (committed durable state + instruction blocks
# + projected agent artifacts).
_CONTINUITY_PATHSPEC = [".horus", "AGENTS.md", "CLAUDE.md", *PROJECTED_ARTIFACT_PATHS]


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


def _summary_freshness(root: Path) -> list[Finding]:
    """Git signal: real-work commits made since the latest session summary (i.e. work
    not yet captured). Empty when not a repo or there are no sessions."""
    if not is_git_repo(root):
        return []
    recent = recent_sessions(root, limit=1)
    if not recent:
        return []
    n = _work_commits_since(root, recent[0].stat().st_mtime)
    if n:
        return [Finding("warn", f"{n} work commit(s) since the latest session summary; summarize before closing")]
    return [Finding("ok", "session summary is current with work commits")]


def freshness_gate(root: Path) -> list[Finding]:
    """The dashboard-freshness subset, for `horus close --check` / a CI pre-merge gate:
    are the lanes the dashboard renders current with this session?

    Deliberately just :func:`routines.freshness_signals` — the reliable per-field
    checks. The "work commits since summary" nudge (:func:`_summary_freshness`) and
    usage/drift signals stay in the full `horus close`; they're informational and the
    former mtime-nags within the very session being closed, so they don't gate."""
    return routines.freshness_signals(root)


def _enforce_push(root: Path) -> bool:
    """Whether the push half of the checkpoint applies to this repo.

    A repo that intentionally never pushes (local-only, or no write access to origin)
    opts out with ``enforce_push: false`` in its PRD.md (v3) or project.md (v2)
    frontmatter. Absent or unparseable → enforce (the default). The dirty-tree half of
    the checkpoint always applies — every repo wants its work committed."""
    hdir = root / ".horus"
    for name in (frontmatter.PRD_FILE, "project.md"):
        doc = frontmatter.parse_file(hdir / name)
        if doc is None:
            continue
        val = doc.front_matter.get("enforce_push")
        if isinstance(val, str) and val.strip():
            return val.strip().lower() not in ("false", "no", "off", "0")
        return True  # continuity file present, key unset → enforce
    return True


def checkpoint_gate(root: Path) -> list[Finding]:
    """Git-checkpoint signal for `close --check` / the Stop hook: is the working tree
    committed and are local commits pushed?

    This turns the working-discipline "bound each step to a committed-and-pushed
    checkpoint" from a remembered habit into an observed signal, so a session can't
    quietly end with a dirty tree or commits stranded only on this machine.

    - **Dirty tree** — any uncommitted change (broader than the continuity-only check
      in :func:`closure_status`); always checked.
    - **Unpushed commits** — local commits the branch's upstream doesn't have. Skipped
      when the repo opts out (``enforce_push: false``) or has no upstream to push to
      (nowhere to push, and no protected-branch footgun to guard against).

    Reports only — never pushes — so the branch-first rule is respected by construction
    (an agent decides whether to push to a protected default). Errs toward silence on
    any git trouble (a broken checker must never wedge a close)."""
    if not is_git_repo(root):
        return []
    findings: list[Finding] = []

    status = _git(root, "status", "--porcelain")
    if status is None:
        return findings  # git trouble → stay silent
    dirty = [line for line in status.splitlines() if line.strip()]
    if dirty:
        findings.append(Finding(
            "warn",
            f"{len(dirty)} uncommitted change(s) in the working tree; commit before "
            "closing (`horus close --commit` for continuity, or commit your work)",
        ))
    else:
        findings.append(Finding("ok", "working tree clean"))

    if _enforce_push(root):
        upstream = _git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
        if upstream:
            ahead = _git(root, "rev-list", "--count", "@{upstream}..HEAD")
            if ahead and ahead.isdigit() and int(ahead) > 0:
                findings.append(Finding(
                    "warn",
                    f"{ahead} local commit(s) not pushed to {upstream}; push before "
                    "closing (`git push`, or `horus close --commit --push` for continuity)",
                ))
            else:
                findings.append(Finding("ok", "local commits pushed to upstream"))
    return findings


def closure_status(root: Path, *, usage_threshold: float = 90.0) -> list[Finding]:
    """Compose continuity health + instruction drift + git-aware closure signals."""
    findings = list(check_project(root))
    # Dashboard-freshness gate: the lanes the dashboard renders must be current with
    # this session before closure is "done" (the drift that motivated this check).
    findings.extend(routines.freshness_signals(root))
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

    findings.extend(_summary_freshness(root))
    if is_git_repo(root):
        status = _git(root, "status", "--porcelain", "--", *_CONTINUITY_PATHSPEC)
        changed = [line for line in (status or "").splitlines() if line.strip()]
        if changed:
            findings.append(
                Finding("warn", f"{len(changed)} uncommitted continuity file(s); use `horus close --commit`")
            )
        else:
            findings.append(Finding("ok", "continuity files committed"))

    findings.extend(checkpoint_gate(root))
    return findings


def remote_lane_divergence(root: Path) -> int:
    """Fetch, then count upstream commits not present locally that touch continuity
    paths. The one-person-two-machines guard: closing here while another machine
    already pushed newer lanes would fork the continuity. Returns 0 when there is
    no upstream, the fetch fails (offline), or the remote isn't ahead on lanes —
    the guard errs toward allowing."""
    if _git(root, "fetch", "--quiet") is None:
        return 0
    if not _git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"):
        return 0
    out = _git(root, "log", "--format=%H", "HEAD..@{upstream}", "--", *_CONTINUITY_PATHSPEC)
    if not out:
        return 0
    return len([line for line in out.splitlines() if line.strip()])


def commit_continuity(root: Path, message: str | None = None, *, push: bool = False) -> tuple[bool, str]:
    """Stage and commit the continuity files. Returns (did_commit, detail).

    With ``push``, fetches first and refuses when the upstream already has newer
    continuity commits (see :func:`remote_lane_divergence`) so a stale machine
    pulls before overwriting cross-machine state."""
    if not is_git_repo(root):
        return False, "not a git repository"
    if push:
        n = remote_lane_divergence(root)
        if n:
            return False, (
                f"origin has {n} newer continuity commit(s) — run `git pull --ff-only` "
                "to fold them in, then re-run `horus close --commit --push`"
            )
    # Only add paths that exist: `git add` fails wholesale on a pathspec that
    # matches nothing (e.g. a repo without hooks/skills installed).
    present = [p for p in _CONTINUITY_PATHSPEC if (root / p).exists()]
    if present:
        _git(root, "add", "--", *present)
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
