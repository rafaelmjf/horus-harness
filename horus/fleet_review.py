"""Remote-authoritative, read-only fleet review.

The shared manifest says which repositories form the fleet. A local registry
says where clones live on this machine. Neither replaces the other: fetched
origin/default continuity is shipped truth, while checkout state remains a
separately labelled local projection.
"""

from __future__ import annotations

import base64
import json
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from horus import capabilities, fetchcheck, frontmatter, gitstate

SCHEMA_VERSION = 1
_INACTIVE_STATUSES = {"done", "folded-in", "retired", "shipped"}
_NO_WINDOW = (
    {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    if sys.platform == "win32"
    else {}
)


@dataclass(frozen=True)
class ManifestProject:
    id: str
    repo: str
    status: str


@dataclass
class RemoteTruth:
    available: bool = False
    source: str = ""
    ref: str = ""
    sha: str = ""
    status: str = ""
    current_focus: str = ""
    next_action: str = ""
    vision: str = ""
    capabilities: list[str] = field(default_factory=list)
    backlog: list[dict[str, str]] = field(default_factory=list)
    backlog_mode: str = "none"
    continuity_sha: str = ""
    source_commits_since_continuity: int | None = None
    note: str = ""


@dataclass
class LocalWorkingState:
    available: bool = False
    path: str = ""
    summary: str = "not cloned on this machine"
    fetch_status: str = ""


@dataclass
class ProjectReview:
    id: str
    repo: str
    manifest_status: str
    remote: RemoteTruth
    local: LocalWorkingState


@dataclass
class FleetReview:
    manifest: str
    projects: list[ProjectReview]
    schema_version: int = SCHEMA_VERSION


def _run(argv: list[str], *, timeout: float = 12.0) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            **_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _git(root: Path, *args: str) -> str | None:
    result = _run(["git", "-C", str(root), *args])
    if result is None or result.returncode != 0:
        return None
    return result.stdout


def _repo_slug(remote: str | None) -> str:
    value = (remote or "").strip().removesuffix(".git")
    if value.startswith("git@github.com:"):
        return value.split(":", 1)[1]
    marker = "github.com/"
    if marker in value:
        return value.split(marker, 1)[1]
    return ""


def _curator_manifest(project_paths: list[str]) -> Path | None:
    candidates: list[Path] = []
    for raw in project_paths:
        root = Path(raw)
        manifest = root / "fleet.toml"
        if not manifest.is_file():
            continue
        prd = frontmatter.parse_file(root / ".horus" / "PRD.md")
        if prd is not None and prd.front_matter.get("workspace_role") == "fleet-curator":
            return manifest
        candidates.append(manifest)
    return sorted(candidates)[0] if len(candidates) == 1 else None


def load_manifest(
    project_paths: list[str], manifest_path: Path | None = None
) -> tuple[Path, list[ManifestProject]]:
    path = manifest_path or _curator_manifest(project_paths)
    if path is None:
        raise ValueError(
            "No fleet curator manifest found. Register a project whose PRD has "
            "workspace_role: fleet-curator and a fleet.toml."
        )
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"Cannot read fleet manifest {path}: {exc}") from exc
    rows = raw.get("projects")
    if raw.get("version") != 1 or not isinstance(rows, list):
        raise ValueError(f"Unsupported fleet manifest schema in {path}")
    projects: list[ManifestProject] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"Invalid project entry in {path}")
        project = ManifestProject(
            id=str(row.get("id", "")).strip(),
            repo=str(row.get("repo", "")).strip(),
            status=str(row.get("status", "active")).strip() or "active",
        )
        if not project.id or "/" not in project.repo or project.id in seen:
            raise ValueError(f"Invalid or duplicate project entry in {path}: {project.id!r}")
        seen.add(project.id)
        projects.append(project)
    return path, sorted(projects, key=lambda item: item.id.casefold())


def _local_roots(project_paths: list[str]) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    for raw in project_paths:
        root = Path(raw)
        remote = _git(root, "remote", "get-url", "origin")
        slug = _repo_slug(remote)
        if slug:
            roots[slug.casefold()] = root
    return roots


def _card_record(name: str, text: str) -> dict[str, str] | None:
    meta = frontmatter.parse(text).front_matter
    status = meta.get("status", "open").strip().casefold()
    if status in _INACTIVE_STATUSES:
        return None
    return {
        "name": name.removesuffix(".md"),
        "title": meta.get("title", name.removesuffix(".md")),
        "status": status,
        "priority": meta.get("priority", ""),
        "type": meta.get("type", "task"),
    }


def _truth_from_prd(
    *,
    source: str,
    ref: str,
    sha: str,
    prd_text: str,
    cards: list[tuple[str, str]],
    continuity_sha: str = "",
    source_commits_since_continuity: int | None = None,
    note: str = "",
) -> RemoteTruth:
    document = frontmatter.parse(prd_text)
    body = document.body
    backlog = [
        card
        for name, text in cards
        if (card := _card_record(name, text)) is not None
    ]
    backlog.sort(key=lambda card: (card["priority"], card["name"]))
    backlog_mode = (
        "cards"
        if cards
        else "unstructured"
        if capabilities._section(body, "Backlog").strip()
        else "none"
    )
    return RemoteTruth(
        available=True,
        source=source,
        ref=ref,
        sha=sha,
        status=document.front_matter.get("status", ""),
        current_focus=document.front_matter.get("current_focus", ""),
        next_action=document.front_matter.get("next_action", ""),
        vision=capabilities.vision_lead(body) or "",
        capabilities=capabilities.shipped_lines(body),
        backlog=backlog,
        backlog_mode=backlog_mode,
        continuity_sha=continuity_sha,
        source_commits_since_continuity=source_commits_since_continuity,
        note=note,
    )


def _local_remote_truth(root: Path, state: dict[str, Any] | None) -> RemoteTruth:
    default = str((state or {}).get("default_branch") or "")
    if not default:
        return RemoteTruth(note="fetched remote default branch is unavailable")
    ref = f"origin/{default}"
    prd = _git(root, "show", f"{ref}:.horus/PRD.md")
    if prd is None:
        return RemoteTruth(source="git", ref=ref, note="remote PRD.md is unavailable")
    sha = (_git(root, "rev-parse", ref) or "").strip()
    names = (_git(root, "ls-tree", "--name-only", f"{ref}:.horus/backlog") or "").splitlines()
    cards: list[tuple[str, str]] = []
    for name in names:
        if not name.endswith(".md") or name.startswith("."):
            continue
        text = _git(root, "show", f"{ref}:.horus/backlog/{name}")
        if text is not None:
            cards.append((name, text))
    continuity_sha = (
        _git(root, "log", "-1", "--format=%H", ref, "--", ".horus/PRD.md") or ""
    ).strip()
    source_count: int | None = None
    if continuity_sha:
        count = _git(
            root,
            "rev-list",
            "--count",
            f"{continuity_sha}..{ref}",
            "--",
            ".",
            ":(exclude).horus/**",
        )
        if count is not None and count.strip().isdigit():
            source_count = int(count.strip())
    fetch_note = ""
    if str((state or {}).get("fetch_status") or "").endswith("failed"):
        fetch_note = "fetch failed; the remote-tracking ref may be stale"
    return _truth_from_prd(
        source="git",
        ref=ref,
        sha=sha,
        prd_text=prd,
        cards=cards,
        continuity_sha=continuity_sha,
        source_commits_since_continuity=source_count,
        note=fetch_note,
    )


def _gh_json(endpoint: str) -> Any | None:
    result = _run(["gh", "api", endpoint], timeout=20.0)
    if result is None or result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _gh_content(repo: str, path: str, ref: str) -> str | None:
    data = _gh_json(f"repos/{repo}/contents/{path}?ref={ref}")
    if not isinstance(data, dict) or data.get("encoding") != "base64":
        return None
    try:
        return base64.b64decode(str(data.get("content", ""))).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def _github_remote_truth(repo: str) -> RemoteTruth:
    metadata = _gh_json(f"repos/{repo}")
    if not isinstance(metadata, dict):
        return RemoteTruth(source="github", note="not cloned; authenticated GitHub read unavailable")
    default = str(metadata.get("default_branch") or "")
    prd = _gh_content(repo, ".horus/PRD.md", default) if default else None
    if not default or prd is None:
        return RemoteTruth(source="github", ref=default, note="GitHub PRD.md is unavailable")
    head = _gh_json(f"repos/{repo}/commits/{default}")
    sha = str(head.get("sha") or "") if isinstance(head, dict) else ""
    listing = _gh_json(f"repos/{repo}/contents/.horus/backlog?ref={default}")
    cards: list[tuple[str, str]] = []
    if isinstance(listing, list):
        for item in listing:
            if not isinstance(item, dict) or item.get("type") != "file":
                continue
            name = str(item.get("name") or "")
            if not name.endswith(".md") or name.startswith("."):
                continue
            text = _gh_content(repo, f".horus/backlog/{name}", default)
            if text is not None:
                cards.append((name, text))
    commits = _gh_json(f"repos/{repo}/commits?sha={default}&path=.horus/PRD.md&per_page=1")
    continuity_sha = ""
    if isinstance(commits, list) and commits and isinstance(commits[0], dict):
        continuity_sha = str(commits[0].get("sha") or "")
    return _truth_from_prd(
        source="github",
        ref=default,
        sha=sha,
        prd_text=prd,
        cards=cards,
        continuity_sha=continuity_sha,
        note="source-vs-continuity count requires a local clone",
    )


def build(project_paths: list[str], *, manifest_path: Path | None = None) -> FleetReview:
    manifest, entries = load_manifest(project_paths, manifest_path)
    local = _local_roots(project_paths)
    reviews: list[ProjectReview] = []
    for entry in entries:
        root = local.get(entry.repo.casefold())
        if root is None:
            reviews.append(
                ProjectReview(
                    entry.id,
                    entry.repo,
                    entry.status,
                    _github_remote_truth(entry.repo),
                    LocalWorkingState(),
                )
            )
            continue
        state = fetchcheck.fetch_and_state(root, ttl=0)
        reviews.append(
            ProjectReview(
                entry.id,
                entry.repo,
                entry.status,
                _local_remote_truth(root, state),
                LocalWorkingState(
                    available=True,
                    path=str(root),
                    summary=gitstate.summary(state) or "git state unavailable",
                    fetch_status=str((state or {}).get("fetch_status") or ""),
                ),
            )
        )
    return FleetReview(str(manifest), reviews)


def to_dict(review: FleetReview) -> dict[str, Any]:
    return asdict(review)


def render_json(review: FleetReview) -> str:
    return json.dumps(to_dict(review), indent=2) + "\n"


def _compact(value: str, fallback: str = "-") -> str:
    text = " ".join(value.split())
    return text or fallback


def render_text(review: FleetReview) -> str:
    lines = [f"Fleet review · manifest {review.manifest}", ""]
    for project in review.projects:
        remote = project.remote
        local = project.local
        lines.append(f"{project.id} [{project.manifest_status}] · {project.repo}")
        if remote.available:
            ref = f"{remote.ref}@{remote.sha[:8]}" if remote.sha else remote.ref
            lines.append(f"  REMOTE SHIPPED TRUTH ({remote.source} {ref})")
            lines.append(f"    focus: {_compact(remote.current_focus)}")
            lines.append(f"    next:  {_compact(remote.next_action)}")
            backlog_label = (
                str(len(remote.backlog))
                if remote.backlog_mode == "cards"
                else "unstructured (not projected)"
                if remote.backlog_mode == "unstructured"
                else "none"
            )
            lines.append(
                f"    capabilities: {len(remote.capabilities)} · active backlog: {backlog_label}"
            )
            if remote.source_commits_since_continuity:
                lines.append(
                    "    WARNING: "
                    f"{remote.source_commits_since_continuity} source commit(s) are newer "
                    "than the last remote PRD update"
                )
            elif remote.source_commits_since_continuity == 0:
                lines.append("    continuity: no newer source commits")
            if remote.backlog:
                labels = ", ".join(card["name"] for card in remote.backlog[:5])
                suffix = f" (+{len(remote.backlog) - 5} more)" if len(remote.backlog) > 5 else ""
                lines.append(f"    cards: {labels}{suffix}")
            if remote.note:
                lines.append(f"    note: {remote.note}")
        else:
            lines.append(f"  REMOTE SHIPPED TRUTH unavailable: {remote.note or 'unknown error'}")
        lines.append("  LOCAL WORKING STATE")
        if local.available:
            lines.append(f"    {local.summary} · fetch {local.fetch_status or 'unknown'}")
            lines.append(f"    path: {local.path}")
        else:
            lines.append(f"    {local.summary}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
