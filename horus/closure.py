"""The closure routine.

Before ending a session, verify the work is captured in durable continuity:
`.horus/` health, instruction-block alignment, and uncommitted continuity files.
Optional local recovery notes are harvested when present but are never required.
The routine can commit continuity files so durable state is persisted (and can sync).

This is the file-first, verify-first half of the hybrid closure decision: it
checks and reports; the actual summary is written by the in-loop agent following
the printed ritual. No agent is spawned here.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from horus import backlog, codex_usage, config, frontmatter, routines
from horus.continuity import Finding, check_project, recent_sessions
from horus.instructions import check_drift

# Checkpoint harvest: the commit message the agent already wrote IS the continuity
# delta, so a per-commit hook can append it to the session note for zero LLM tokens.
# The marker (last-harvested HEAD, local/gitignored like sessions) makes it
# idempotent — a commit is never harvested twice.
CHECKPOINT_MARKER = ".consolidated-to"
_GENERATED_STATE_PATHS = (f".horus/{CHECKPOINT_MARKER}",)
_HARVEST_HEADING = "## Checkpoints (auto-harvested)"

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

# What may reach the default branch on a DIRECT push (closure's no-PR path).
# Always safe: durable state and the instruction blocks — no CI check reads them as
# product, so skipping required checks costs nothing.
_DIRECT_PUSH_ALWAYS = (".horus", "AGENTS.md", "CLAUDE.md")

# The generator whose presence means projected artifacts are BUILD OUTPUT in this
# repo rather than vendored files. In a consumer project the projections have no
# in-repo source, so they are ordinary continuity; in the harness itself they are
# derived from `horus/skills.py` and must travel WITH their source through a PR, or
# a projection lands on the default branch out of sync with the code that generates
# it — exactly what the freshness check and projection-sync test exist to catch, and
# exactly what a direct push skips.
_PROJECTION_GENERATOR = "horus/skills.py"

_PRODUCT_LOG_EXCLUDES = (
    ":(exclude).horus",
    ":(exclude)AGENTS.md",
    ":(exclude)CLAUDE.md",
    ":(exclude).claude/settings.json",
    ":(exclude).claude/skills",
    ":(exclude).agents/skills",
    ":(exclude).codex/hooks.json",
)


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


def freshness_gate(root: Path) -> list[Finding]:
    """The dashboard-freshness subset, for `horus close --check` / a CI pre-merge gate:
    are the lanes the dashboard renders current with this session?

    It includes the reliable per-field freshness checks plus deterministic card
    lifecycle drift. Usage and instruction-drift signals stay in the full
    `horus close`; optional recovery notes never gate closure."""
    return routines.freshness_signals(root) + backlog.hygiene_findings(root)


def _canonical_continuity_paths(root: Path) -> tuple[str, ...]:
    if frontmatter.has_prd(root):
        return (".horus/PRD.md",)
    return (".horus/project.md", ".horus/roadmap.md", ".horus/features.md")


def _canonical_checkpoint(root: Path) -> str | None:
    """The latest commit that touched canonical continuity — the point everything
    after which is an as-yet-unconsolidated delivery."""
    return _git(
        root, "log", "-1", "--format=%H", "--", *_canonical_continuity_paths(root),
    ) or None


def pending_delivery_commits(root: Path) -> list[tuple[str, str]]:
    """Product commits after the latest canonical-continuity commit.

    Git history is the durable receipt: unlike the local ``.consolidated-to``
    marker this survives a new machine, and unlike a self-authored checkpoint
    SHA it remains valid after GitHub squash-merges a feature branch.  A commit
    touching both product and canonical continuity is covered because it is the
    checkpoint commit itself and therefore outside the queried range.
    """
    if not is_git_repo(root):
        return []
    checkpoint = _canonical_checkpoint(root)
    if not checkpoint:
        return []
    out = _git(
        root,
        "log",
        "--reverse",
        "--format=%H%x1f%s",
        f"{checkpoint}..HEAD",
        "--",
        ".",
        *_PRODUCT_LOG_EXCLUDES,
    )
    records: list[tuple[str, str]] = []
    for line in (out or "").splitlines():
        sha, separator, subject = line.partition("\x1f")
        if separator and sha:
            records.append((sha, subject))
    return records


def pending_delivery_findings(root: Path) -> list[Finding]:
    pending = pending_delivery_commits(root)
    if not pending:
        return [Finding("ok", "canonical continuity covers all product commits")]
    sample = ", ".join(f"{sha[:8]} {subject}" for sha, subject in pending[-3:])
    suffix = f" (+{len(pending) - 3} earlier)" if len(pending) > 3 else ""
    return [Finding(
        "warn",
        f"{len(pending)} delivery commit(s) pending the next continuity boundary: "
        f"{sample}{suffix}",
    )]


@dataclass(frozen=True)
class ParallelSignal:
    """One other writer that a closing/resuming session must not miss."""

    kind: str      # "live-session" | "open-pr" | "merged-pr"
    ref: str       # session id / PR number
    detail: str


def _is_ancestor(root: Path, commit: str, of: str) -> bool | None:
    """Is ``commit`` an ancestor of ``of``? None when it cannot be decided (unknown
    object) — the caller then fails quiet rather than raising a false alarm."""
    try:
        r = subprocess.run(
            ["git", "-C", str(root), "merge-base", "--is-ancestor", commit, of],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode == 0:
        return True
    if r.returncode == 1:
        return False
    return None  # 128/other: bad object, detached, etc.


def _gh_json(root: Path, *args: str) -> object | None:
    """A best-effort `gh ... --json` call. None on any failure (gh absent, offline,
    not a GitHub repo) so a machine without gh degrades silently — never a false
    'no parallel work' nor a crash."""
    import json as _json
    try:
        r = subprocess.run(
            ["gh", *args], cwd=str(root), capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    try:
        return _json.loads(r.stdout)
    except (ValueError, TypeError):
        return None


def parallel_deliveries(
    root: Path, *, self_session_id: str | None = None,
) -> tuple[list[ParallelSignal], bool]:
    """Detect other concurrent writers on this project. Returns (signals, pr_checked);
    ``pr_checked`` is False when gh could not be consulted, so callers avoid a false
    all-clear. Deterministic and best-effort — no locks, no mutation."""
    signals: list[ParallelSignal] = []

    # (a) Another live registered session/worker on this same project.
    from horus import registry
    try:
        records = registry.Registry.default().snapshot()
    except Exception:  # noqa: BLE001 - best-effort machine-local signal
        records = []
    # Exclude the current writer: a `horus run` worker knows its own id, and an
    # interactive Claude/Codex session is registered under CLAUDE_CODE_SESSION_ID —
    # flagging yourself as a parallel writer is noise, not a signal.
    self_ids = {
        self_session_id,
        os.environ.get("HORUS_RUN_SESSION_ID"),
        os.environ.get("CLAUDE_CODE_SESSION_ID"),
    }
    self_ids.discard(None)
    here = root.resolve().as_posix()
    for rec in records:
        if rec.status != "running" or rec.session_id in self_ids:
            continue
        try:
            same = Path(rec.project).resolve().as_posix() == here
        except (OSError, ValueError):
            same = rec.project == here
        if same:
            signals.append(ParallelSignal(
                "live-session", rec.session_id,
                f"live {rec.agent} session {rec.session_id[:8]} on this project",
            ))

    if not is_git_repo(root):
        return signals, False

    # (b) Sibling PRs on the same repo not yet folded into canonical continuity.
    current_branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    open_prs = _gh_json(root, "pr", "list", "--state", "open", "--json", "number,headRefName,title")
    merged_prs = _gh_json(
        root, "pr", "list", "--state", "merged", "--limit", "10",
        "--json", "number,mergeCommit,headRefName",
    )
    pr_checked = open_prs is not None or merged_prs is not None

    for pr in open_prs or []:
        if pr.get("headRefName") and pr.get("headRefName") != current_branch:
            signals.append(ParallelSignal(
                "open-pr", str(pr.get("number")),
                f"PR #{pr.get('number')} open on {pr.get('headRefName')} — {pr.get('title', '')}".rstrip(" —"),
            ))

    checkpoint = _canonical_checkpoint(root)
    for pr in merged_prs or []:
        sha = (pr.get("mergeCommit") or {}).get("oid") if isinstance(pr.get("mergeCommit"), dict) else None
        if not sha or not checkpoint:
            continue
        # Flag only merges NOT yet covered by the latest continuity commit. Unknown
        # objects (None) are skipped: better silent than a false alarm on old history.
        if _is_ancestor(root, sha, checkpoint) is False:
            signals.append(ParallelSignal(
                "merged-pr", str(pr.get("number")),
                f"PR #{pr.get('number')} merged ({sha[:8]}) not yet in canonical continuity",
            ))
    return signals, pr_checked


def parallel_delivery_findings(root: Path, *, self_session_id: str | None = None) -> list[Finding]:
    """Render :func:`parallel_deliveries` as gate findings. Empty (not a false
    'all clear') when gh is unavailable and no live co-session exists.

    Rendered at ``info`` level: a named sibling PR or co-session is advisory —
    it must be surfaced so it isn't missed, but a supervisor legitimately closes
    while siblings exist, so it must never flip a fresh verdict to stale (unlike
    ``warn``/``fail``, which every ``healthy``/gate computation aggregates)."""
    signals, pr_checked = parallel_deliveries(root, self_session_id=self_session_id)
    if signals:
        return [Finding("info", f"parallel delivery pending: {s.detail}") for s in signals]
    if pr_checked:
        return [Finding("ok", "no parallel deliveries detected")]
    return []


def boundary_freshness_gate(root: Path) -> list[Finding]:
    """A real pause/handoff close must fold every pending delivery."""
    return freshness_gate(root) + pending_delivery_findings(root) + parallel_delivery_findings(root)


def pr_diff_freshness(root: Path, base_ref: str) -> list[Finding]:
    """Report how this PR's diff stands against canonical continuity.

    One universal rule (2026-07-19): the git commit itself is the durable delivery
    receipt, and canonical `.horus/` prose is folded at the next real boundary —
    a pause, session end, agent/account/machine handoff, release, or dispatch that
    needs durable context. There is no per-project or per-machine granularity knob
    that can turn this into a merge-blocking gate; delivery safety lives in the
    branch/PR/CI evidence, not in prose freshness. Server-side; never mutates the
    checkout.
    """
    changed_text = _git(root, "diff", "--name-only", f"{base_ref}...HEAD")
    if changed_text is None:
        return [Finding("fail", f"cannot compare this PR with base ref {base_ref!r}")]
    changed = [line.strip().replace("\\", "/") for line in changed_text.splitlines() if line.strip()]
    if not changed:
        return [Finding("ok", f"no changes relative to {base_ref}")]

    def is_continuity(path: str) -> bool:
        return (
            path == ".horus"
            or path.startswith(".horus/")
            or path in {"AGENTS.md", "CLAUDE.md", ".claude/settings.json", ".codex/hooks.json"}
            or path.startswith(".claude/skills/")
            or path.startswith(".agents/skills/")
        )

    work = [path for path in changed if not is_continuity(path)]
    if not work:
        return [Finding("ok", "PR changes continuity only")]

    if frontmatter.has_prd(root):
        homes = {".horus/PRD.md"}
        label = ".horus/PRD.md"
    else:
        homes = {".horus/project.md", ".horus/roadmap.md", ".horus/features.md"}
        label = ".horus/{project,roadmap,features}.md"
    updated = sorted(homes.intersection(changed))
    if not updated:
        return [Finding(
            "ok",
            f"PR product/source changes are durable in git; canonical continuity "
            f"({label}) is folded at the next real boundary",
        )]
    return [Finding(
        "ok",
        f"PR product/source changes include canonical continuity ({', '.join(updated)})",
    )]


def pr_freshness_gate(root: Path, base_ref: str) -> list[Finding]:
    """PR-boundary continuity signals — informational, never a merge blocker.

    Card archival is canonical continuity too, so it batches to the next real
    boundary along with the rest of the prose. Dashboard field validity is still
    checked on every PR because a malformed field breaks a reader, not a ritual.
    """
    return routines.freshness_signals(root) + pr_diff_freshness(root, base_ref)


def _parse_frontmatter_date(value: object) -> date | None:
    """Coerce a frontmatter `last_updated`/`date` value to a date, tolerantly —
    a local twin of `routines._as_date` (same lenient ISO-prefix parse) so this
    one-act-acceptance probe doesn't need a cross-module private import."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None


def target_continuity_staleness(root: Path, *, completed_at: str | None) -> str | None:
    """One-act-acceptance probe (`horus datum close --card`): is the TARGET
    project's own continuity (its `.horus/PRD.md` `last_updated`, or its latest
    session note date) at least as fresh as this run's completion?

    PRINT-only signal for the caller — this never writes anything (the frozen
    schema's hard boundary: surface staleness, never auto-fix it; a residual
    continuity close stays the worker's or overseer's own job). Returns a
    one-line warning, or ``None`` when fresh enough or there's nothing to probe
    (no completion timestamp, or no `.horus/PRD.md` at the target)."""
    if not completed_at:
        return None
    completed = _parse_frontmatter_date(completed_at)
    if completed is None:
        return None
    prd = frontmatter.parse_file(root / ".horus" / frontmatter.PRD_FILE)
    if prd is None:
        return None
    last_updated = _parse_frontmatter_date(prd.front_matter.get("last_updated"))
    sessions = recent_sessions(root, limit=1)
    session_date = None
    if sessions:
        session_date = _parse_frontmatter_date(
            frontmatter.parse(sessions[0].read_text(encoding="utf-8")).front_matter.get("date")
        )
    freshest = max((d for d in (last_updated, session_date) if d is not None), default=None)
    if freshest is not None and freshest >= completed:
        return None
    stamp = freshest.isoformat() if freshest else "unset"
    return (
        f"target continuity looks stale: {root}/.horus/{frontmatter.PRD_FILE} last_updated/latest "
        f"session ({stamp}) predates this run's completion ({completed.isoformat()}) — refresh "
        "continuity there (this probe only warns; it never auto-fixes)."
    )


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

    status = _git(
        root, "status", "--porcelain", "--", ".",
        *[f":(exclude){path}" for path in _GENERATED_STATE_PATHS],
    )
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


def _harvest_records(root: Path, since: str | None) -> list[tuple[str, str, str]]:
    """(short_sha, subject, body) for commits after ``since`` (exclusive), oldest
    first; just the tip commit when ``since`` is None or unknown (e.g. rebased away).
    Field/record separators (\\x1f/\\x1e) survive multi-line bodies."""
    fmt = "%h%x1f%s%x1f%b%x1e"
    args = ["log", "--reverse", f"--format={fmt}"]
    args.append(f"{since}..HEAD" if since else "-1")
    out = _git(root, *args)
    if out is None and since:  # unknown marker → fall back to the tip commit
        out = _git(root, "log", "--reverse", f"--format={fmt}", "-1")
    records: list[tuple[str, str, str]] = []
    for rec in (out or "").split("\x1e"):
        if not rec.strip():
            continue
        parts = rec.strip("\n").split("\x1f")
        if len(parts) >= 2 and parts[0].strip():
            body = parts[2].strip() if len(parts) > 2 else ""
            records.append((parts[0].strip(), parts[1].strip(), body))
    return records


def _latest_session_note(root: Path) -> Path | None:
    """Return the newest optional recovery note without creating one."""
    recent = recent_sessions(root, limit=1)
    return recent[0] if recent else None


_TRAILER_PREFIXES = ("co-authored-by:", "signed-off-by:", "co-committed-by:")


def _append_checkpoints(note: Path, records: list[tuple[str, str, str]]) -> None:
    text = note.read_text(encoding="utf-8")
    chunk: list[str] = []
    if _HARVEST_HEADING not in text:
        chunk.append(f"\n{_HARVEST_HEADING}\n")
    for sha, subject, body in records:
        chunk.append(f"\n- `{sha}` {subject}")
        for line in body.splitlines():
            if line.strip() and not line.strip().lower().startswith(_TRAILER_PREFIXES):
                chunk.append(f"\n  {line.rstrip()}")
    with note.open("a", encoding="utf-8") as fh:
        fh.write("".join(chunk) + "\n")


def harvest_checkpoint(root: Path) -> tuple[int, Path | None]:
    """Append new commit messages to an existing optional recovery note and advance
    the marker. Never creates a note. Returns ``(n_harvested, note_path|None)``;
    a silent no-op when no note exists or there is nothing new."""
    if not is_git_repo(root) or not (root / ".horus").is_dir():
        return 0, None
    head = _git(root, "rev-parse", "HEAD")
    if not head:
        return 0, None
    marker = root / ".horus" / CHECKPOINT_MARKER
    since = marker.read_text(encoding="utf-8").strip() if marker.is_file() else None
    if since == head:
        return 0, None  # already harvested to HEAD
    records = _harvest_records(root, since)
    note: Path | None = None
    if records:
        note = _latest_session_note(root)
    if records and note is not None:
        _append_checkpoints(note, records)
    marker.write_text(head + "\n", encoding="utf-8")  # advance even if empty, to avoid rescan
    return (len(records), note) if note is not None else (0, None)


def closure_status(root: Path, *, usage_threshold: float = 90.0) -> list[Finding]:
    """Compose continuity health + instruction drift + git-aware closure signals."""
    findings = list(check_project(root))
    # Dashboard-freshness gate: the lanes the dashboard renders must be current with
    # this session before closure is "done" (the drift that motivated this check).
    findings.extend(routines.freshness_signals(root))
    findings.extend(pending_delivery_findings(root))
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
        status = _git(
            root, "status", "--porcelain", "--", *_CONTINUITY_PATHSPEC,
            *[f":(exclude){path}" for path in _GENERATED_STATE_PATHS],
        )
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


def continuity_dirty(root: Path) -> bool:
    """Whether any continuity file has uncommitted changes (staged or not)."""
    return bool(continuity_dirty_paths(root))


def continuity_dirty_paths(root: Path) -> list[str]:
    """Changed continuity pathspec entries, including tracked deletions.

    The porcelain payload is retained verbatim after its two-column status so
    quoted paths and rename arrows remain unambiguous in a warning.
    """
    if not is_git_repo(root):
        return []
    try:
        result = subprocess.run(
            [
                "git", "-C", str(root), "status", "--porcelain", "--",
                *_CONTINUITY_PATHSPEC,
                *[f":(exclude){path}" for path in _GENERATED_STATE_PATHS],
            ],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    # Do not route porcelain through `_git`: its `.strip()` intentionally
    # normalizes scalar output but would remove the first line's leading status
    # column (turning ` M .horus/PRD.md` into `M .horus/PRD.md`).
    return [line[3:].strip() for line in result.stdout.splitlines() if line.strip()]


def _seal_checkpoint_at_head(root: Path) -> bool:
    """Mark the closing commit harvested without appending it to its own note."""
    head = _git(root, "rev-parse", "HEAD")
    if not head:
        return False
    marker = root / ".horus" / CHECKPOINT_MARKER
    try:
        marker.write_text(head + "\n", encoding="utf-8")
    except OSError:
        return False
    return True


def default_branch(root: Path) -> str:
    """The remote's default branch name, or "" when it cannot be determined.

    Read from `origin/HEAD`; a repo whose remote HEAD is unset returns "" and every
    caller must then treat the branch as NOT the default (fail open — a guard that
    misfires on a feature branch is worse than one that misses)."""
    ref = _git(root, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if not ref:
        return ""
    return ref.rsplit("/", 1)[-1].strip()


def direct_push_violations(root: Path) -> list[str]:
    """Paths in the unpushed commits that may NOT reach the default branch directly.

    Closure deliberately does not go through a PR: `horus close --commit --push`
    writes only continuity, so skipping the required checks costs nothing — no CI
    check reads `.horus/` or the instruction blocks as product. That exemption is
    only sound while the pushed content really is continuity, and until now it was
    enforced by whoever was typing: a hand-rolled `git add -A && git push` on the
    default branch would carry source to main untested.

    Returns the offending paths (empty list = safe to push directly). Only meaningful
    on the default branch; returns [] everywhere else, and [] when anything cannot be
    determined, so this never wedges a normal feature-branch push.
    """
    if not is_git_repo(root):
        return []
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    default = default_branch(root)
    if not branch or not default or branch != default:
        return []
    changed = _git(root, "diff", "--name-only", f"origin/{default}...HEAD")
    if not changed:
        return []

    allowed = list(_DIRECT_PUSH_ALWAYS)
    if not (root / _PROJECTION_GENERATOR).exists():
        # Consumer project: projections are vendored artifacts with no in-repo source.
        allowed += PROJECTED_ARTIFACT_PATHS

    violations = []
    for line in changed.splitlines():
        path = line.strip().replace("\\", "/")
        if not path:
            continue
        if not any(path == a or path.startswith(f"{a}/") for a in allowed):
            violations.append(path)
    return sorted(set(violations))


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
    # Fold work commits into an existing optional recovery note BEFORE staging continuity.
    # After the close commit lands, its SHA is deliberately sealed in the local
    # marker rather than appended to the note inside that same commit (an
    # impossible self-reference that would dirty the tree forever).
    try:
        harvest_checkpoint(root)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"checkpoint harvest failed before commit: {exc}"
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
    if not _seal_checkpoint_at_head(root):
        return False, detail + "; checkpoint seal failed — push skipped"

    residual = continuity_dirty_paths(root)
    if residual:
        return True, (
            detail + "; WARNING: residual dirty continuity after commit — push skipped: "
            + ", ".join(residual)
        )
    if push:
        # The closure commit itself is pathspec-bounded, but an EARLIER unpushed commit
        # on this branch may not be — refuse rather than carry it past required checks.
        blocked = direct_push_violations(root)
        if blocked:
            sample = ", ".join(blocked[:3])
            suffix = f" (+{len(blocked) - 3} more)" if len(blocked) > 3 else ""
            return True, (
                detail + f"; push refused — non-continuity paths would reach the default "
                f"branch without required checks: {sample}{suffix}. Move them to a branch "
                "and open a PR."
            )
        branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
        pushed = _git(root, "push", "origin", branch or "HEAD")
        detail += "; pushed" if pushed is not None else "; push failed"
    residual = continuity_dirty_paths(root)
    if residual:
        detail += "; WARNING: residual dirty continuity: " + ", ".join(residual)
    return True, detail
