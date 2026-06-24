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


def register_project(project_path: Path) -> bool:
    """Add ``project_path`` to the user config. Returns True if newly added."""
    key = _as_key(project_path)
    existing = load_projects()
    if key in existing:
        return False

    existing.append(key)
    config_dir().mkdir(parents=True, exist_ok=True)
    lines = ["# Horus user config", "projects = ["]
    lines += [f'  "{p}",' for p in existing]
    lines.append("]")
    config_path().write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True
