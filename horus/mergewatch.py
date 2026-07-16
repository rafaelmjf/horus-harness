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
    # True unless we positively learned the owning PR is closed/merged — a
    # currently-open PR's head sha still gets a genuine `pull_request` event,
    # so its required contexts are never filtered. Defaults permissive when
    # the PR state is unknown/unreported.
    is_open_pr: bool = True


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
        r = _run(["gh", "pr", "view", str(pr_number), "--json", "headRefOid,baseRefName,state"], root)
        if r.returncode != 0:
            raise MergeWatchError(f"gh pr view {pr_number} failed: {(r.stderr or r.stdout).strip()}")
        try:
            data = json.loads(r.stdout)
            sha = data["headRefOid"]
        except (ValueError, KeyError, TypeError) as exc:
            raise MergeWatchError(f"could not parse `gh pr view {pr_number}` output") from exc
        base = data.get("baseRefName") if isinstance(data, dict) else None
        is_open = _is_open_state(data.get("state") if isinstance(data, dict) else None)
        return Target(owner=owner, repo=repo, sha=sha, pr_number=pr_number, base_branch=base, is_open_pr=is_open)

    sha = ref
    r = _run(["gh", "api", f"repos/{owner}/{repo}/commits/{sha}/pulls"], root)
    found_pr: int | None = None
    base_branch: str | None = None
    is_open = True
    if r.returncode == 0:
        try:
            prs = json.loads(r.stdout)
            if isinstance(prs, list) and prs and isinstance(prs[0], dict):
                number = prs[0].get("number")
                found_pr = number if isinstance(number, int) else None
                base_branch = (prs[0].get("base") or {}).get("ref")
                is_open = _is_open_state(prs[0].get("state"))
        except (ValueError, AttributeError, TypeError):
            pass
    return Target(owner=owner, repo=repo, sha=sha, pr_number=found_pr, base_branch=base_branch, is_open_pr=is_open)


def _is_open_state(state: object) -> bool:
    """Permissive by default (``True``) — only a positively-reported
    non-"open" PR state (``gh pr view``'s ``OPEN/CLOSED/MERGED`` or the REST
    API's lowercase ``open/closed``) flips this to ``False``."""
    if not isinstance(state, str):
        return True
    return state.strip().lower() == "open"


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


_JOB_ID_RE = re.compile(r"^  ([A-Za-z0-9_.-]+):[ \t]*$", re.MULTILINE)
_JOB_NAME_RE = re.compile(r"^ {4,}name:[ \t]*(.+?)[ \t]*$", re.MULTILINE)
_ON_BLOCK_RE = re.compile(r"^on:[ \t]*(.*?)(?=^\S|\Z)", re.MULTILINE | re.DOTALL)
_JOBS_BLOCK_RE = re.compile(r"^jobs:[ \t]*\n(.*)", re.MULTILINE | re.DOTALL)


def _context_base(name: str) -> str:
    """Strip a matrix suffix like ``" (3.12)"`` so a required context (as
    reported by a check-run) can be matched back to the job that produces
    it."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()


def _parse_workflow(text: str) -> tuple[bool, bool, set[str]] | None:
    """``(has_push, has_pull_request, contexts)`` for one workflow file, or
    ``None`` when it can't be structurally parsed with confidence (no
    top-level ``on:`` or ``jobs:`` block found at all) — callers must treat
    that as "unknown", never silently as "no push trigger"."""
    on_match = _ON_BLOCK_RE.search(text)
    jobs_match = _JOBS_BLOCK_RE.search(text)
    if on_match is None or jobs_match is None:
        return None
    tokens = set(re.findall(r"[A-Za-z_]+", on_match.group(1)))
    has_push = "push" in tokens
    has_pr = "pull_request" in tokens
    return has_push, has_pr, _workflow_job_contexts(text)


def _workflow_job_contexts(text: str) -> set[str]:
    """Context-base names (job ids and any ``name:`` override) declared under
    a workflow's ``jobs:`` block."""
    jobs_match = _JOBS_BLOCK_RE.search(text)
    if not jobs_match:
        return set()
    body = jobs_match.group(1)
    contexts: set[str] = set()
    for job_match in _JOB_ID_RE.finditer(body):
        contexts.add(_context_base(job_match.group(1)))
        block_start = job_match.end()
        next_job = _JOB_ID_RE.search(body, block_start)
        block_end = next_job.start() if next_job else len(body)
        name_match = _JOB_NAME_RE.search(body, block_start, block_end)
        if name_match:
            contexts.add(_context_base(name_match.group(1).strip("'\"")))
    return contexts


def _workflow_paths_at_sha(root: Path, sha: str) -> list[str] | None:
    """Paths of ``.github/workflows/*.yml|*.yaml`` as they existed AT ``sha``
    (via ``git ls-tree``, never the working tree), or ``None`` when that
    can't be determined (sha not present locally, no git checkout, etc.)."""
    r = _run(["git", "ls-tree", "-r", "--name-only", sha, "--", ".github/workflows"], root)
    if r.returncode != 0:
        return None
    paths = [line.strip() for line in r.stdout.splitlines() if line.strip()]
    return [p for p in paths if p.endswith((".yml", ".yaml"))]


def _workflow_text_at_sha(root: Path, sha: str, path: str) -> str | None:
    """Content of ``path`` AT ``sha`` (via ``git show``), or ``None`` when
    unreadable."""
    r = _run(["git", "show", f"{sha}:{path}"], root)
    return r.stdout if r.returncode == 0 else None


def pr_only_contexts(root: Path, sha: str) -> set[str]:
    """Context-base names that ONLY ever trigger on a ``pull_request`` event,
    read from the workflow definitions as they existed AT the exact watched
    ``sha`` — never the current checkout, whose workflow triggers may have
    since changed. A required context in this set can never post a check on
    a plain push (e.g. a post-merge commit landing on main), so a watcher
    must stop waiting on it rather than sit pending forever.

    Fails safe ALL-OR-NOTHING: if any workflow path listed at this exact sha
    can't be read, or can't be structurally parsed with confidence, the
    whole result is empty (filters nothing) — a readable, confidently
    PR-only workflow must never drop a context just because some OTHER,
    unreadable-or-unparseable workflow might have made that same context
    push-capable. A required context is only ever dropped on complete,
    positive, exact-sha proof across every workflow in the tree, never on
    partial evidence. A context also produced by a push-triggering workflow
    is never included, even if another same-named job elsewhere is PR-only."""
    paths = _workflow_paths_at_sha(root, sha)
    if not paths:
        return set()
    pr_only: set[str] = set()
    push_triggered: set[str] = set()
    for path in paths:
        text = _workflow_text_at_sha(root, sha, path)
        if text is None:
            return set()
        parsed = _parse_workflow(text)
        if parsed is None:
            return set()
        has_push, has_pr, contexts = parsed
        if not has_pr:
            continue
        if has_push:
            push_triggered.update(contexts)
        else:
            pr_only.update(contexts)
    return pr_only - push_triggered


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
    if required and not target.is_open_pr:
        # A closed/merged owning PR means this sha only ever gets a push
        # event — required contexts that are exclusively pull_request-gated
        # (e.g. a PR-only continuity check) can never post here, so drop
        # them rather than wait on them forever. Anything still push-capable
        # stays required and pending until it actually reports.
        filtered = {c for c in required if _context_base(c) not in pr_only_contexts(root, target.sha)}
        required = filtered or None
    label = f"PR #{target.pr_number}" if target.pr_number else target.sha[:12]
    emit(f"merge-watch: watching {target.sha[:12]} ({label}) in {target.owner}/{target.repo}")

    prev_states: dict[str, str] = {}
    prev_overall: str | None = None
    deadline = now() + timeout
    while True:
        if target.pr_number is not None and target.is_open_pr:
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
