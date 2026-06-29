"""GitHub-backed remote Horus project catalog.

This is deliberately a lightweight bridge: GitHub stores durable `.horus/` files,
while the local machine still owns clones, account config, running sessions, and
launches. The module uses the authenticated `gh` CLI instead of managing tokens.
"""

from __future__ import annotations

import base64
import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from horus import config, frontmatter, gitstate


@dataclass(frozen=True)
class RemoteProject:
    owner: str
    name: str
    full_name: str
    url: str
    clone_url: str
    default_branch: str
    pushed_at: str
    current_focus: str = ""
    next_action: str = ""
    next_prompt: str = ""
    local_path: str | None = None

    @property
    def is_local(self) -> bool:
        return self.local_path is not None


@dataclass(frozen=True)
class UntrackedRepo:
    """A GitHub repo that does not have `.horus/project.md`."""

    owner: str
    name: str
    full_name: str
    url: str
    clone_url: str
    default_branch: str
    pushed_at: str
    description: str = ""
    local_path: str | None = None

    @property
    def is_local(self) -> bool:
        return self.local_path is not None


@dataclass(frozen=True)
class DiscoveryResult:
    """Return value of :func:`discover`."""

    projects: list[RemoteProject]
    untracked: list[UntrackedRepo]


@dataclass(frozen=True)
class CachedCatalog:
    owner: str
    projects: list[RemoteProject]
    fetched_at: str
    error: str = ""
    error_at: str = ""
    untracked: list[UntrackedRepo] = field(default_factory=list)


@dataclass(frozen=True)
class RefreshResult:
    owner: str
    ok: bool
    count: int = 0
    fetched_at: str = ""
    error: str = ""


def discover(
    owner: str,
    *,
    local_projects: list[str] | None = None,
    limit: int = 100,
    prior: dict[str, "RemoteProject"] | None = None,
    prior_untracked: dict[str, "UntrackedRepo"] | None = None,
) -> DiscoveryResult:
    """Return Horus-enabled and untracked GitHub repos for `owner`.

    A repo is considered Horus-enabled when `.horus/project.md` is readable. The
    roadmap file is optional; older Horus projects can still appear with just the
    project focus. Repos without `.horus/project.md` are classified as untracked and
    returned in ``DiscoveryResult.untracked``.

    When ``prior`` is supplied (a dict keyed by ``full_name``), any repo whose
    ``pushedAt`` matches the cached entry is returned from the cache without making
    the two ``gh api`` calls for ``.horus/`` files.  This dramatically reduces API
    calls on incremental refreshes.  Repos with a changed or absent ``pushedAt``
    always fall through to the full fetch path.

    When ``prior_untracked`` is supplied, any repo whose ``pushedAt`` matches a
    cached untracked entry is classified untracked immediately without any ``gh api``
    content call.
    """
    repos = _repo_list(owner, limit=limit)
    local_by_remote = _local_projects_by_remote(local_projects or [])
    out_projects: list[RemoteProject] = []
    out_untracked: list[UntrackedRepo] = []
    for repo in repos:
        full_name = str(repo.get("nameWithOwner") or "")
        if not full_name:
            continue
        branch = _default_branch(repo)
        live_pushed_at = str(repo.get("pushedAt") or "")
        clone_url = str(repo.get("sshUrl") or repo.get("url") or "")
        url = str(repo.get("url") or "")
        remote_keys = {_normalize_remote(url), _normalize_remote(clone_url)}
        remote_keys.discard("")
        local_path = next((local_by_remote[k] for k in remote_keys if k in local_by_remote), None)
        name = str(repo.get("name") or full_name.rsplit("/", 1)[-1])
        description = str(repo.get("description") or "")

        # Fast path (Horus project): reuse cached .horus/ content when pushedAt is unchanged.
        if prior is not None and full_name in prior:
            cached_entry = prior[full_name]
            if cached_entry.pushed_at and cached_entry.pushed_at == live_pushed_at:
                out_projects.append(
                    RemoteProject(
                        owner=owner,
                        name=name,
                        full_name=full_name,
                        url=url,
                        clone_url=clone_url or url,
                        default_branch=branch,
                        pushed_at=live_pushed_at,
                        current_focus=cached_entry.current_focus,
                        next_action=cached_entry.next_action,
                        next_prompt=cached_entry.next_prompt,
                        local_path=local_path,
                    )
                )
                continue

        # Fast path (untracked): reuse cached untracked verdict when pushedAt is unchanged.
        if prior_untracked is not None and full_name in prior_untracked:
            cached_untracked = prior_untracked[full_name]
            if cached_untracked.pushed_at and cached_untracked.pushed_at == live_pushed_at:
                out_untracked.append(
                    UntrackedRepo(
                        owner=owner,
                        name=cached_untracked.name,
                        full_name=full_name,
                        url=url,
                        clone_url=clone_url or url,
                        default_branch=cached_untracked.default_branch,
                        pushed_at=live_pushed_at,
                        description=cached_untracked.description,
                        local_path=local_path,
                    )
                )
                continue

        # Full fetch path: read .horus/ files from GitHub.
        project_text = _repo_file(full_name, ".horus/project.md", branch)
        if project_text is None:
            # Not a Horus project — classify as untracked.
            out_untracked.append(
                UntrackedRepo(
                    owner=owner,
                    name=name,
                    full_name=full_name,
                    url=url,
                    clone_url=clone_url or url,
                    default_branch=branch,
                    pushed_at=live_pushed_at,
                    description=description,
                    local_path=local_path,
                )
            )
            continue
        roadmap_text = _repo_file(full_name, ".horus/roadmap.md", branch) or ""
        project_doc = frontmatter.parse(project_text)
        roadmap_doc = frontmatter.parse(roadmap_text)
        out_projects.append(
            RemoteProject(
                owner=owner,
                name=name,
                full_name=full_name,
                url=url,
                clone_url=clone_url or url,
                default_branch=branch,
                pushed_at=live_pushed_at,
                current_focus=str(project_doc.front_matter.get("current_focus", "")),
                next_action=str(roadmap_doc.front_matter.get("next_action", "")),
                next_prompt=str(roadmap_doc.front_matter.get("next_prompt", "")),
                local_path=local_path,
            )
        )
    return DiscoveryResult(projects=out_projects, untracked=out_untracked)


def refresh_cache(owner: str, *, local_projects: list[str] | None = None, limit: int = 100) -> list[RemoteProject]:
    """Discover live projects and persist the last successful owner snapshot.

    Builds ``prior`` and ``prior_untracked`` maps from the existing on-disk cache so
    that repos whose ``pushedAt`` has not changed since the last refresh skip the
    ``gh api`` content calls in :func:`discover`.

    Returns ``list[RemoteProject]`` (the Horus projects only) so existing callers
    (``force_refresh``, dashboard ``gather_remote_projects``) are unchanged.
    """
    existing = load_cache(owner)
    prior: dict[str, RemoteProject] | None = (
        {p.full_name: p for p in existing.projects} if existing is not None else None
    )
    prior_untracked: dict[str, UntrackedRepo] | None = (
        {u.full_name: u for u in existing.untracked} if existing is not None else None
    )
    try:
        result = discover(
            owner,
            local_projects=local_projects,
            limit=limit,
            prior=prior,
            prior_untracked=prior_untracked,
        )
    except RuntimeError as exc:
        record_cache_error(owner, str(exc))
        raise
    save_cache(owner, result.projects, result.untracked)
    return result.projects


def force_refresh(owner: str, *, local_projects: list[str] | None = None, limit: int = 100) -> RefreshResult:
    """Refresh one owner and return a user-facing status object."""
    try:
        projects = refresh_cache(owner, local_projects=local_projects, limit=limit)
    except RuntimeError as exc:
        cached = load_cache(owner, local_projects=local_projects)
        return RefreshResult(owner=owner, ok=False, count=len(cached.projects) if cached else 0, error=str(exc))
    cached = load_cache(owner, local_projects=local_projects)
    return RefreshResult(owner=owner, ok=True, count=len(projects), fetched_at=cached.fetched_at if cached else "")


def load_cache(owner: str, *, local_projects: list[str] | None = None) -> CachedCatalog | None:
    path = _cache_path(owner)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    raw_projects = data.get("projects")
    if not isinstance(raw_projects, list):
        return None
    local_by_remote = _local_projects_by_remote(local_projects or [])
    projects = [_project_from_cache(owner, item, local_by_remote) for item in raw_projects if isinstance(item, dict)]
    raw_untracked = data.get("untracked") or []
    untracked = [
        _untracked_from_cache(owner, item, local_by_remote)
        for item in raw_untracked
        if isinstance(item, dict)
    ]
    return CachedCatalog(
        owner=owner,
        projects=projects,
        fetched_at=str(data.get("fetched_at") or ""),
        error=str(data.get("error") or ""),
        error_at=str(data.get("error_at") or ""),
        untracked=untracked,
    )


def save_cache(
    owner: str,
    projects: list[RemoteProject],
    untracked: list[UntrackedRepo] | None = None,
) -> None:
    path = _cache_path(owner)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "owner": owner,
        "fetched_at": _now_iso(),
        "projects": [_project_to_cache(p) for p in projects],
        "untracked": [_untracked_to_cache(u) for u in (untracked or [])],
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def record_cache_error(owner: str, message: str) -> None:
    path = _cache_path(owner)
    data: dict[str, Any] = {"owner": owner, "projects": [], "fetched_at": ""}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data.update(loaded)
        except (OSError, json.JSONDecodeError):
            pass
    data["error"] = message
    data["error_at"] = _now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _repo_list(owner: str, *, limit: int) -> list[dict[str, Any]]:
    try:
        result = subprocess.run(
            [
                "gh",
                "repo",
                "list",
                owner,
                "--limit",
                str(limit),
                "--json",
                "name,nameWithOwner,url,sshUrl,defaultBranchRef,pushedAt,description",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise RuntimeError(f"gh repo list failed: {exc}") from exc
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "gh repo list failed").strip())
    try:
        data = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gh repo list returned invalid JSON: {exc}") from exc
    return data if isinstance(data, list) else []


def _repo_file(full_name: str, path: str, branch: str) -> str | None:
    try:
        result = subprocess.run(
            ["gh", "api", "--method", "GET", f"repos/{full_name}/contents/{path}", "-f", f"ref={branch}"],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout or "{}")
        content = str(data.get("content") or "")
        encoding = data.get("encoding")
    except json.JSONDecodeError:
        return None
    if encoding != "base64" or not content:
        return None
    try:
        return base64.b64decode(content).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def _default_branch(repo: dict[str, Any]) -> str:
    ref = repo.get("defaultBranchRef")
    if isinstance(ref, dict):
        return str(ref.get("name") or "main")
    return "main"


def _local_projects_by_remote(projects: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for project in projects:
        state = gitstate.git_state(Path(project))
        if not state or not state.get("remote_url"):
            continue
        key = _normalize_remote(str(state["remote_url"]))
        if key:
            out[key] = project
    return out


def _normalize_remote(url: str) -> str:
    value = url.strip()
    if not value:
        return ""
    if value.startswith("git@github.com:"):
        value = "https://github.com/" + value[len("git@github.com:") :]
    if value.endswith(".git"):
        value = value[:-4]
    return value.rstrip("/")


def _cache_path(owner: str) -> Path:
    safe = "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in owner)
    return config.config_dir() / "github-cache" / f"{safe}.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _project_to_cache(project: RemoteProject) -> dict[str, str]:
    return {
        "owner": project.owner,
        "name": project.name,
        "full_name": project.full_name,
        "url": project.url,
        "clone_url": project.clone_url,
        "default_branch": project.default_branch,
        "pushed_at": project.pushed_at,
        "current_focus": project.current_focus,
        "next_action": project.next_action,
        "next_prompt": project.next_prompt,
    }


def _project_from_cache(owner: str, item: dict[str, Any], local_by_remote: dict[str, str]) -> RemoteProject:
    url = str(item.get("url") or "")
    clone_url = str(item.get("clone_url") or "")
    remote_keys = {_normalize_remote(url), _normalize_remote(clone_url)}
    remote_keys.discard("")
    local_path = next((local_by_remote[k] for k in remote_keys if k in local_by_remote), None)
    full_name = str(item.get("full_name") or "")
    return RemoteProject(
        owner=str(item.get("owner") or owner),
        name=str(item.get("name") or full_name.rsplit("/", 1)[-1]),
        full_name=full_name,
        url=url,
        clone_url=clone_url or url,
        default_branch=str(item.get("default_branch") or "main"),
        pushed_at=str(item.get("pushed_at") or ""),
        current_focus=str(item.get("current_focus") or ""),
        next_action=str(item.get("next_action") or ""),
        next_prompt=str(item.get("next_prompt") or ""),
        local_path=local_path,
    )


def _untracked_to_cache(repo: UntrackedRepo) -> dict[str, str]:
    return {
        "owner": repo.owner,
        "name": repo.name,
        "full_name": repo.full_name,
        "url": repo.url,
        "clone_url": repo.clone_url,
        "default_branch": repo.default_branch,
        "pushed_at": repo.pushed_at,
        "description": repo.description,
    }


def _untracked_from_cache(owner: str, item: dict[str, Any], local_by_remote: dict[str, str]) -> UntrackedRepo:
    url = str(item.get("url") or "")
    clone_url = str(item.get("clone_url") or "")
    remote_keys = {_normalize_remote(url), _normalize_remote(clone_url)}
    remote_keys.discard("")
    local_path = next((local_by_remote[k] for k in remote_keys if k in local_by_remote), None)
    full_name = str(item.get("full_name") or "")
    return UntrackedRepo(
        owner=str(item.get("owner") or owner),
        name=str(item.get("name") or full_name.rsplit("/", 1)[-1]),
        full_name=full_name,
        url=url,
        clone_url=clone_url or url,
        default_branch=str(item.get("default_branch") or "main"),
        pushed_at=str(item.get("pushed_at") or ""),
        description=str(item.get("description") or ""),
        local_path=local_path,
    )
