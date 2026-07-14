"""``horus merge-watch <sha|pr>`` — absorb the wait, not the observation.

The overseer/cockpit already knows the rule (see ``skills.py``'s "OBSERVE the
required CI check green on the merge SHA"): the deterministic gate is a
*required* CI check green on the EXACT commit, not a re-run of the suite. What
was still hand-rolled was the WAITING — a sleep-loop of ``gh pr checks``
re-invoked by the agent turn after turn. This module is that loop as a single
one-shot command: poll the commit's checks until the watched set settles green
or red, printing one line per state change (not a tail of CI logs), then exit
0/1 so a caller (script or agent) can branch on it without reading prose.

Pinned to the EXACT sha the caller named — if the PR moves to a new head while
this is running, that's surfaced as a warning (the checks below it now belong
to a different commit), never silently re-targeted.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

_NO_WINDOW = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if sys.platform == "win32" else {}

DEFAULT_INTERVAL = 15.0
DEFAULT_TIMEOUT = 1800.0  # 30 minutes — generous for a CI matrix, not unbounded

_PR_URL_RE = re.compile(r"/pull/(\d+)")

# GitHub check-run conclusions that count as a hard stop vs. a pass, mirroring
# what a required-status-check gate itself treats as blocking.
_FAILURE_CONCLUSIONS = {"failure", "cancelled", "timed_out", "action_required", "stale"}
_SUCCESS_CONCLUSIONS = {"success", "neutral", "skipped"}
_STATUS_STATE_MAP = {"success": "success", "failure": "failure", "error": "failure"}


class MergeWatchError(Exception):
    """The target ref (sha/PR) or owning repo could not be resolved."""


@dataclass(frozen=True)
class Target:
    owner: str
    repo: str
    sha: str
    pr_number: int | None
    base_branch: str | None


@dataclass(frozen=True)
class WatchOutcome:
    state: str  # "success" | "failure" | "timeout"
    sha: str
    checks: dict[str, str]


def _run(cmd: list[str], cwd: Path, *, timeout: float = 20.0) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, **_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise MergeWatchError(f"command failed: {' '.join(cmd)}: {exc}") from exc


def _repo_slug(root: Path) -> tuple[str, str]:
    r = _run(["gh", "repo", "view", "--json", "owner,name"], root)
    if r.returncode != 0:
        raise MergeWatchError(f"gh repo view failed: {(r.stderr or r.stdout).strip()}")
    try:
        data = json.loads(r.stdout)
        return data["owner"]["login"], data["name"]
    except (ValueError, KeyError, TypeError) as exc:
        raise MergeWatchError("could not parse `gh repo view` output") from exc


def resolve_target(root: Path, ref: str) -> Target:
    """Resolve ``<sha|pr>`` to the exact commit + owning repo (+ PR number/base
    when known). A bare number or a PR URL is treated as a PR (its current
    ``headRefOid`` becomes the pinned sha); anything else is treated as a
    literal commit sha, with its owning PR looked up (if any) so the base
    branch's required-check contexts can still be resolved."""
    owner, repo = _repo_slug(root)
    match = _PR_URL_RE.search(ref)
    pr_number = int(match.group(1)) if match else (int(ref) if ref.isdigit() else None)

    if pr_number is not None:
        r = _run(["gh", "pr", "view", str(pr_number), "--json", "headRefOid,baseRefName"], root)
        if r.returncode != 0:
            raise MergeWatchError(f"gh pr view {pr_number} failed: {(r.stderr or r.stdout).strip()}")
        try:
            data = json.loads(r.stdout)
            sha = data["headRefOid"]
        except (ValueError, KeyError, TypeError) as exc:
            raise MergeWatchError(f"could not parse `gh pr view {pr_number}` output") from exc
        base = data.get("baseRefName") if isinstance(data, dict) else None
        return Target(owner=owner, repo=repo, sha=sha, pr_number=pr_number, base_branch=base)

    sha = ref
    r = _run(["gh", "api", f"repos/{owner}/{repo}/commits/{sha}/pulls"], root)
    found_pr: int | None = None
    base_branch: str | None = None
    if r.returncode == 0:
        try:
            prs = json.loads(r.stdout)
            if isinstance(prs, list) and prs and isinstance(prs[0], dict):
                number = prs[0].get("number")
                found_pr = number if isinstance(number, int) else None
                base_branch = (prs[0].get("base") or {}).get("ref")
        except (ValueError, AttributeError, TypeError):
            pass
    return Target(owner=owner, repo=repo, sha=sha, pr_number=found_pr, base_branch=base_branch)


def required_contexts(root: Path, owner: str, repo: str, base: str | None) -> set[str] | None:
    """Contexts the base branch's protection requires, or ``None`` when
    unknowable (no protection configured/visible — a free-plan private repo,
    or a repo with no branch protection at all). Callers fall back to
    watching every check present on the commit rather than gating on an
    empty/absent required set (mirrors ``integration._has_required_checks``'s
    err-toward-permissive stance)."""
    if not base:
        return None
    r = _run(["gh", "api", f"repos/{owner}/{repo}/branches/{base}/protection/required_status_checks"], root)
    if r.returncode != 0:
        return None
    try:
        data = json.loads(r.stdout)
        contexts = data.get("contexts") if isinstance(data, dict) else None
        return set(contexts) if isinstance(contexts, list) and contexts else None
    except (ValueError, AttributeError, TypeError):
        return None


def fetch_check_states(root: Path, owner: str, repo: str, sha: str) -> dict[str, str]:
    """Every check known for ``sha`` — GitHub Actions check-runs plus legacy
    commit statuses — normalized to pending/success/failure, keyed by
    name/context."""
    states: dict[str, str] = {}
    r = _run(["gh", "api", f"repos/{owner}/{repo}/commits/{sha}/check-runs", "--paginate"], root)
    if r.returncode == 0:
        try:
            data = json.loads(r.stdout)
            for run in data.get("check_runs", []) if isinstance(data, dict) else []:
                name = run.get("name")
                if not name:
                    continue
                if run.get("status") != "completed":
                    states[name] = "pending"
                else:
                    conclusion = run.get("conclusion")
                    states[name] = "failure" if conclusion in _FAILURE_CONCLUSIONS else "success"
        except (ValueError, AttributeError, TypeError):
            pass
    r = _run(["gh", "api", f"repos/{owner}/{repo}/commits/{sha}/status"], root)
    if r.returncode == 0:
        try:
            data = json.loads(r.stdout)
            for status in data.get("statuses", []) if isinstance(data, dict) else []:
                context = status.get("context")
                if not context:
                    continue
                states[context] = _STATUS_STATE_MAP.get(status.get("state"), "pending")
        except (ValueError, AttributeError, TypeError):
            pass
    return states


def overall_state(states: dict[str, str], required: set[str] | None) -> str:
    """``"pending" | "success" | "failure"`` across the watched set (required
    contexts when known, else every check present). Failure wins over
    pending; success only once every watched check reports success. An empty
    watched set (nothing reported yet, or a required context that hasn't
    posted a check at all) reads as pending, never a vacuous success."""
    watched = {name: state for name, state in states.items() if required is None or name in required}
    if required:
        missing = required - set(watched)
        if missing:
            return "pending"
    if not watched:
        return "pending"
    if any(state == "failure" for state in watched.values()):
        return "failure"
    if all(state == "success" for state in watched.values()):
        return "success"
    return "pending"


def watch(
    root: Path,
    ref: str,
    *,
    interval: float = DEFAULT_INTERVAL,
    timeout: float = DEFAULT_TIMEOUT,
    emit: Callable[[str], None] = print,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
) -> WatchOutcome:
    """Poll ``ref`` (a PR number/URL or a literal commit sha) until its
    watched checks settle green or red, or ``timeout`` elapses. Emits one line
    per state change — never a verbose CI-log tail — via ``emit``."""
    target = resolve_target(root, ref)
    required = required_contexts(root, target.owner, target.repo, target.base_branch)
    label = f"PR #{target.pr_number}" if target.pr_number else target.sha[:12]
    emit(f"merge-watch: watching {target.sha[:12]} ({label}) in {target.owner}/{target.repo}")

    prev_states: dict[str, str] = {}
    prev_overall: str | None = None
    deadline = now() + timeout
    while True:
        if target.pr_number is not None:
            r = _run(["gh", "pr", "view", str(target.pr_number), "--json", "headRefOid"], root)
            if r.returncode == 0:
                try:
                    live_head = json.loads(r.stdout).get("headRefOid")
                except (ValueError, AttributeError, TypeError):
                    live_head = None
                if live_head and live_head != target.sha:
                    emit(
                        f"merge-watch: WARNING PR #{target.pr_number} head moved to "
                        f"{live_head[:12]} — still watching the pinned {target.sha[:12]}"
                    )

        states = fetch_check_states(root, target.owner, target.repo, target.sha)
        for name in sorted(set(states) | set(prev_states)):
            new_state = states.get(name, "pending")
            old_state = prev_states.get(name)
            if new_state != old_state:
                emit(f"  {name}: {old_state or 'unseen'} -> {new_state}")
        prev_states = states

        overall = overall_state(states, required)
        if overall != prev_overall:
            emit(f"merge-watch: overall {prev_overall or 'unknown'} -> {overall}")
            prev_overall = overall

        if overall in ("success", "failure"):
            return WatchOutcome(state=overall, sha=target.sha, checks=states)
        if now() >= deadline:
            emit(f"merge-watch: timed out after {timeout:.0f}s waiting for checks to settle")
            return WatchOutcome(state="timeout", sha=target.sha, checks=states)
        sleep(interval)
