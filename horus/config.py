"""User-level Horus config: the list of project paths the dashboard knows about.

Stored at ``~/.horus/config.toml``. Read with stdlib ``tomllib``; written with a
tiny hand-rolled serializer (paths only) to stay dependency-free. Paths are
stored with forward slashes so they need no TOML escaping and work on Windows.
"""

from __future__ import annotations

import tomllib
from pathlib import Path


def config_dir() -> Path:
    return Path.home() / ".horus"


def config_path() -> Path:
    return config_dir() / "config.toml"


def load_projects() -> list[str]:
    path = config_path()
    if not path.exists():
        return []
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    projects = data.get("projects", [])
    if not isinstance(projects, list):
        return []
    return [str(p) for p in projects]


def _as_key(path: Path) -> str:
    return path.resolve().as_posix()


def _write_projects(projects: list[str]) -> None:
    config_dir().mkdir(parents=True, exist_ok=True)
    lines = ["# Horus user config", "projects = ["]
    lines += [f'  "{p}",' for p in projects]
    lines.append("]")
    config_path().write_text("\n".join(lines) + "\n", encoding="utf-8")


def register_project(project_path: Path) -> bool:
    """Add ``project_path`` to the user config. Returns True if newly added."""
    key = _as_key(project_path)
    existing = load_projects()
    if key in existing:
        return False
    existing.append(key)
    _write_projects(existing)
    return True


def unregister_project(project_path: Path) -> bool:
    """Remove ``project_path`` from the user config. Returns True if it was present."""
    key = _as_key(project_path)
    existing = load_projects()
    if key not in existing:
        return False
    _write_projects([p for p in existing if p != key])
    return True


def prune_projects() -> list[str]:
    """Drop registered projects whose path is gone or lacks a `.horus/` dir.

    Returns the list of removed paths.
    """
    existing = load_projects()
    kept, removed = [], []
    for p in existing:
        if (Path(p) / ".horus").is_dir():
            kept.append(p)
        else:
            removed.append(p)
    if removed:
        _write_projects(kept)
    return removed
