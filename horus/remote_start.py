"""Clone/register/start helpers for remote catalog entries."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from horus import config, github_catalog, upgrade


@dataclass(frozen=True)
class StartResult:
    project: github_catalog.RemoteProject
    path: Path
    cloned: bool
    registered: bool
    upgrade_actions: list[upgrade.UpgradeAction]


def parse_github_target(target: str) -> tuple[str, str]:
    prefix = "github:"
    if not target.startswith(prefix):
        raise ValueError("target must look like github:<owner>/<repo>")
    value = target[len(prefix) :].strip()
    parts = [p for p in value.split("/") if p]
    if len(parts) != 2:
        raise ValueError("target must look like github:<owner>/<repo>")
    return parts[0], parts[1]


def start_github_project(target: str, *, workspace_root: Path | None = None, limit: int = 100) -> StartResult:
    owner, repo = parse_github_target(target)
    projects = github_catalog.discover(owner, local_projects=config.load_projects(), limit=limit)
    project = next((p for p in projects if p.full_name.lower() == f"{owner}/{repo}".lower()), None)
    if project is None:
        raise RuntimeError(f"no Horus-enabled GitHub repo found for {owner}/{repo}")

    if project.local_path:
        path = Path(project.local_path).resolve()
        cloned = False
    else:
        root = (workspace_root or Path(config.load_workspace_root())).expanduser().resolve()
        path = root / project.name
        cloned = _clone_project(project, path)

    if not (path / ".horus").is_dir():
        raise RuntimeError(f"cloned path does not contain .horus/: {path}")

    registered = config.register_project(path)
    actions = upgrade.upgrade_project(path, apply=True)
    return StartResult(project=project, path=path, cloned=cloned, registered=registered, upgrade_actions=actions)


def _clone_project(project: github_catalog.RemoteProject, path: Path) -> bool:
    if path.exists():
        if (path / ".git").is_dir():
            return False
        raise RuntimeError(f"destination already exists and is not a git clone: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["gh", "repo", "clone", project.full_name, str(path)],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise RuntimeError(f"gh repo clone failed: {exc}") from exc
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "gh repo clone failed").strip())
    return True
