"""User-level Horus config: the list of project paths the dashboard knows about,
plus the account-alias map.

Stored under ``~/.horus/`` (``config.toml`` for projects, ``accounts.toml`` for
aliases). Read with stdlib ``tomllib``; written with tiny hand-rolled serializers
to stay dependency-free. Paths are stored with forward slashes so they need no
TOML escaping and work on Windows.
"""

from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path


def config_dir() -> Path:
    return Path.home() / ".horus"


def config_path() -> Path:
    return config_dir() / "config.toml"


def accounts_path() -> Path:
    return config_dir() / "accounts.toml"


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


# --- Account aliases ---------------------------------------------------------
#
# A session summary records *which* account ran it, but the real identifier is an
# email (from the agent's auth) and session content is distilled upward into the
# committed lanes. To keep the email out of anything that can be committed, the
# email->alias map lives only in ``~/.horus/accounts.toml`` (never in the repo);
# summaries carry the alias. ``accounts.toml`` lives in its own file so the
# projects serializer never clobbers it.


def load_account_aliases() -> dict[str, str]:
    """Map of real account identifier (e.g. email) -> public alias."""
    path = accounts_path()
    if not path.exists():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    aliases = data.get("aliases")
    if not isinstance(aliases, dict):
        return {}
    return {str(k): str(v) for k, v in aliases.items()}


def _write_account_aliases(aliases: dict[str, str]) -> None:
    config_dir().mkdir(parents=True, exist_ok=True)
    lines = ["# Horus account aliases (local only — keeps real emails out of git)", "[aliases]"]
    # Quote both sides: emails contain '@' and '.', which are not bare-key safe.
    lines += [f'"{ident}" = "{alias}"' for ident, alias in sorted(aliases.items())]
    accounts_path().write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_account_alias(identifier: str, alias: str) -> None:
    """Map a real account identifier to a public alias (persisted locally)."""
    aliases = load_account_aliases()
    aliases[identifier] = alias
    _write_account_aliases(aliases)


def alias_for(identifier: str | None) -> str | None:
    """Public alias for a raw account identifier (email/uuid).

    Returns the configured alias if one exists; otherwise a stable, non-reversible
    short tag derived from the identifier (``acct-<sha6>``) so accounts stay
    distinguishable without ever exposing the email. ``None`` only when there is
    no identifier at all.
    """
    if not identifier:
        return None
    mapped = load_account_aliases().get(identifier)
    if mapped:
        return mapped
    digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:6]
    return f"acct-{digest}"
