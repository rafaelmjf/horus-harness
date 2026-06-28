"""GitHub-backed remote Horus project catalog.

This is deliberately a lightweight bridge: GitHub stores durable `.horus/` files,
while the local machine still owns clones, account config, running sessions, and
launches. The module uses the authenticated `gh` CLI instead of managing tokens.
"""

from __future__ import annotations

import base64
import json
import subprocess
from dataclasses import dataclass
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
class CachedCatalog:
    owner: str
    projects: list[RemoteProject]
    fetched_at: str
    error: str = ""
    error_at: str = ""


@dataclass(frozen=True)
class RefreshResult:
    owner: str
    ok: bool
    count: int = 0
    fetched_at: str = ""
    error: str = ""


def discover(owner: str, *, local_projects: list[str] | None = None, limit: int = 100) -> list[RemoteProject]:
    """Return Horus-enabled GitHub repos for `owner`.

    A repo is considered Horus-enabled when `.horus/project.md` is readable. The
    roadmap file is optional; older Horus projects can still appear with just the
    project focus.
    """
    repos = _repo_list(owner, limit=limit)
    local_by_remote = _local_projects_by_remote(local_projects or [])
    out: list[RemoteProject] = []
    for repo in repos:
        full_name = str(repo.get("nameWithOwner") or "")
        if not full_name:
            continue
        branch = _default_branch(repo)
        project_text = _repo_file(full_name, ".horus/project.md", branch)
        if project_text is None:
            continue
        roadmap_text = _repo_file(full_name, ".horus/roadmap.md", branch) or ""
        project_doc = frontmatter.parse(project_text)
        roadmap_doc = frontmatter.parse(roadmap_text)
        clone_url = str(repo.get("sshUrl") or repo.get("url") or "")
        url = str(repo.get("url") or "")
        remote_keys = {_normalize_remote(url), _normalize_remote(clone_url)}
        remote_keys.discard("")
        local_path = next((local_by_remote[k] for k in remote_keys if k in local_by_remote), None)
        name = str(repo.get("name") or full_name.rsplit("/", 1)[-1])
        out.append(
            RemoteProject(
                owner=owner,
                name=name,
                full_name=full_name,
                url=url,
                clone_url=clone_url or url,
                default_branch=branch,
                pushed_at=str(repo.get("pushedAt") or ""),
                current_focus=str(project_doc.front_matter.get("current_focus", "")),
                next_action=str(roadmap_doc.front_matter.get("next_action", "")),
                next_prompt=str(roadmap_doc.front_matter.get("next_prompt", "")),
                local_path=local_path,
            )
        )
    return out


def refresh_cache(owner: str, *, local_projects: list[str] | None = None, limit: int = 100) -> list[RemoteProject]:
    """Discover live projects and persist the last successful owner snapshot."""
    try:
        projects = discover(owner, local_projects=local_projects, limit=limit)
    except RuntimeError as exc:
        record_cache_error(owner, str(exc))
        raise
    save_cache(owner, projects)
    return projects


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
    return CachedCatalog(
        owner=owner,
        projects=projects,
        fetched_at=str(data.get("fetched_at") or ""),
        error=str(data.get("error") or ""),
        error_at=str(data.get("error_at") or ""),
    )


def save_cache(owner: str, projects: list[RemoteProject]) -> None:
    path = _cache_path(owner)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "owner": owner,
        "fetched_at": _now_iso(),
        "projects": [_project_to_cache(p) for p in projects],
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
                "name,nameWithOwner,url,sshUrl,defaultBranchRef,pushedAt",
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
