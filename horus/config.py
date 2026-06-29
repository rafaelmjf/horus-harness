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

# ---------------------------------------------------------------------------
# Workflow policy constants
# ---------------------------------------------------------------------------

WORKFLOW_DEFAULTS: dict[str, str] = {
    "integration": "branch-pr-automerge",
    "commit": "auto",
    "merge": "auto",
}

WORKFLOW_CHOICES: dict[str, tuple[str, ...]] = {
    "integration": ("branch-pr-automerge", "branch-pr-review", "direct-push", "local-only"),
    "commit": ("auto", "manual"),
    "merge": ("auto", "review"),
}


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


def load_github_owners() -> list[str]:
    path = config_path()
    if not path.exists():
        return []
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    owners = data.get("github_owners", [])
    if not isinstance(owners, list):
        return []
    return [str(o) for o in owners]


def load_workspace_root() -> str:
    path = config_path()
    if not path.exists():
        return str((Path.home() / "projects").resolve())
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    root = data.get("workspace_root")
    if isinstance(root, str) and root.strip():
        return root
    return str((Path.home() / "projects").resolve())


def _as_key(path: Path) -> str:
    return path.resolve().as_posix()


def _write_projects(projects: list[str]) -> None:
    _write_config(projects, load_github_owners(), load_workspace_root())


def _write_config(
    projects: list[str],
    github_owners: list[str],
    workspace_root: str | None = None,
    workflow: dict[str, str] | None = None,
) -> None:
    config_dir().mkdir(parents=True, exist_ok=True)
    root = workspace_root or load_workspace_root()
    # Preserve the current workflow policy when the caller doesn't supply one.
    if workflow is None:
        workflow = load_workflow_policy()
    lines = ["# Horus user config", f'workspace_root = "{Path(root).expanduser().resolve().as_posix()}"', "", "projects = ["]
    lines += [f'  "{p}",' for p in projects]
    lines += ["]", "", "github_owners = ["]
    lines += [f'  "{o}",' for o in github_owners]
    lines.append("]")
    # [workflow] table goes at the end so it doesn't accidentally swallow the
    # top-level keys above it in a strict TOML parse (tables extend until the
    # next table header or EOF).
    lines += ["", "[workflow]"]
    lines += [f'{k} = "{v}"' for k, v in workflow.items()]
    config_path().write_text("\n".join(lines) + "\n", encoding="utf-8")


def register_github_owner(owner: str) -> bool:
    """Add a GitHub user/org to the remote catalog. Returns True if newly added."""
    key = owner.strip()
    if not key:
        return False
    existing = load_github_owners()
    if key in existing:
        return False
    existing.append(key)
    _write_config(load_projects(), existing, load_workspace_root())
    return True


def set_workspace_root(path: Path) -> str:
    """Set the machine-local root where remote projects should be cloned."""
    key = path.expanduser().resolve().as_posix()
    _write_config(load_projects(), load_github_owners(), key)
    return key


def load_workflow_policy() -> dict[str, str]:
    """Return the three workflow policy keys, falling back to defaults for any
    missing or invalid values.

    Keys: ``integration``, ``commit``, ``merge``.
    """
    path = config_path()
    if not path.exists():
        return dict(WORKFLOW_DEFAULTS)
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return dict(WORKFLOW_DEFAULTS)
    raw = data.get("workflow") or {}
    if not isinstance(raw, dict):
        return dict(WORKFLOW_DEFAULTS)
    policy: dict[str, str] = {}
    for key, default in WORKFLOW_DEFAULTS.items():
        value = raw.get(key, default)
        if not isinstance(value, str) or value not in WORKFLOW_CHOICES[key]:
            value = default
        policy[key] = value
    return policy


def set_workflow_policy(
    *,
    integration: str | None = None,
    commit: str | None = None,
    merge: str | None = None,
) -> dict[str, str]:
    """Update the provided workflow policy keys, persist, and return the new
    full policy.

    Raises ``ValueError`` for any value that is not in the allowed set for its
    key.
    """
    updates = {"integration": integration, "commit": commit, "merge": merge}
    for key, value in updates.items():
        if value is not None and value not in WORKFLOW_CHOICES[key]:
            allowed = ", ".join(WORKFLOW_CHOICES[key])
            raise ValueError(f"Invalid workflow {key!r} value {value!r}. Allowed: {allowed}")
    current = load_workflow_policy()
    for key, value in updates.items():
        if value is not None:
            current[key] = value
    _write_config(load_projects(), load_github_owners(), load_workspace_root(), workflow=current)
    return current


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


# --- Accounts: aliases + per-account config dirs -----------------------------
#
# ``~/.horus/accounts.toml`` (local only, never in a repo) holds three maps:
#   [aliases]      email -> public alias   (keeps the real email out of commits)
#   [config_dirs]  alias -> CLAUDE_CONFIG_DIR  (per-account login isolation, Claude)
#   [codex_homes]  alias -> CODEX_HOME         (per-account login isolation, Codex)
# Its own file so the projects serializer never clobbers it; all sections are
# preserved on every write.


def _load_accounts() -> dict[str, dict[str, str]]:
    path = accounts_path()
    if not path.exists():
        return {"aliases": {}, "config_dirs": {}, "codex_homes": {}}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {"aliases": {}, "config_dirs": {}, "codex_homes": {}}
    return {
        "aliases": {str(k): str(v) for k, v in (data.get("aliases") or {}).items()},
        "config_dirs": {str(k): str(v) for k, v in (data.get("config_dirs") or {}).items()},
        "codex_homes": {str(k): str(v) for k, v in (data.get("codex_homes") or {}).items()},
    }


def _write_accounts(
    aliases: dict[str, str],
    config_dirs: dict[str, str],
    codex_homes: dict[str, str],
) -> None:
    config_dir().mkdir(parents=True, exist_ok=True)
    lines = ["# Horus accounts (local only — keeps real emails out of git)", "", "[aliases]"]
    # Quote both sides: emails contain '@' and '.', which are not bare-key safe.
    lines += [f'"{ident}" = "{alias}"' for ident, alias in sorted(aliases.items())]
    lines += ["", "[config_dirs]"]
    # Forward slashes so Windows paths need no TOML escaping (backslash is an escape
    # in a basic string); Path() reads them back fine on every platform.
    lines += [f'"{alias}" = "{path.replace(chr(92), "/")}"' for alias, path in sorted(config_dirs.items())]
    lines += ["", "[codex_homes]"]
    lines += [f'"{alias}" = "{path.replace(chr(92), "/")}"' for alias, path in sorted(codex_homes.items())]
    accounts_path().write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_account_aliases() -> dict[str, str]:
    """Map of real account identifier (e.g. email) -> public alias."""
    return _load_accounts()["aliases"]


def load_account_config_dirs() -> dict[str, str]:
    """Map of account alias -> ``CLAUDE_CONFIG_DIR`` for per-account login isolation."""
    return _load_accounts()["config_dirs"]


def load_account_codex_homes() -> dict[str, str]:
    """Map of account alias -> ``CODEX_HOME`` for per-account login isolation."""
    return _load_accounts()["codex_homes"]


def set_account_alias(identifier: str, alias: str) -> None:
    """Map a real account identifier to a public alias (persisted locally)."""
    accts = _load_accounts()
    accts["aliases"][identifier] = alias
    _write_accounts(accts["aliases"], accts["config_dirs"], accts["codex_homes"])


def set_account_config_dir(alias: str, config_dir_path: str) -> None:
    """Map an account alias to its ``CLAUDE_CONFIG_DIR`` (persisted locally)."""
    accts = _load_accounts()
    accts["config_dirs"][alias] = config_dir_path
    _write_accounts(accts["aliases"], accts["config_dirs"], accts["codex_homes"])


def set_account_codex_home(alias: str, codex_home_path: str) -> None:
    """Map an account alias to its ``CODEX_HOME`` (persisted locally)."""
    accts = _load_accounts()
    accts["codex_homes"][alias] = codex_home_path
    _write_accounts(accts["aliases"], accts["config_dirs"], accts["codex_homes"])


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
