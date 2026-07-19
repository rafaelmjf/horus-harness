"""User-level Horus config: the list of project paths the dashboard knows about,
plus the account-alias map.

Stored under ``~/.horus/`` (``config.toml`` for projects, ``accounts.toml`` for
aliases). Read with stdlib ``tomllib``; written with tiny hand-rolled serializers
to stay dependency-free. Paths are stored with forward slashes so they need no
TOML escaping and work on Windows.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tomllib
from dataclasses import dataclass
from pathlib import Path


class ConfigError(ValueError):
    """Raised when a present-but-malformed config block should fail closed.

    Tolerant loaders (projects, owners) return empty on a missing/garbled file;
    the security-relevant ``[access]`` block is different — if it is present at
    all it must be complete and well-formed, or the dashboard must refuse to
    start rather than silently serve unguarded.
    """

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

# ---------------------------------------------------------------------------
# TUI launch defaults: the permission posture applied to new fresh/resume/
# card-resume launches from `horus tui`, until the owner changes it from the
# home-level Defaults screen. Mirrors adapters.base.PermissionPosture's values
# as plain strings (duplicated, not imported) to avoid a config<->adapters
# import cycle — dashboard.py's own posture picker already does the same.
# ---------------------------------------------------------------------------

LAUNCH_DEFAULTS: dict[str, str] = {"posture": "default", "window": "takeover"}

LAUNCH_POSTURE_CHOICES: tuple[str, ...] = ("plan", "read-only", "default", "auto-edit", "full-auto")

# How a TUI-launched session opens. ``takeover`` (the migration-safe default,
# byte-identical to today) hosts the session in the current terminal — you
# ``Ctrl-b d`` back to the TUI. ``new-window`` opens the session in its own
# terminal window on a real desktop, leaving the TUI live beside it; on mobile /
# SSH / no-display it falls back to ``takeover`` (see terminal_sessions.
# resolve_window_launch) so a phone never gets a broken new-window attempt.
LAUNCH_WINDOW_CHOICES: tuple[str, ...] = ("takeover", "new-window")

# Per-agent launch profile: the model / reasoning effort / permission posture the
# consolidated launch form comes up preselected with, so the common case ("claude
# opus high", "codex sol high") is one keypress and an unusual model stays a
# per-launch override. Saved only when the owner explicitly picks `Save as defaults`
# on the form — an occasional override never rewrites the profile.
LAUNCH_PROFILE_KEYS: tuple[str, ...] = ("model", "effort", "posture")

# ---------------------------------------------------------------------------
# TUI backlog fields: which card frontmatter keys the TUI's backlog list renders
# inline after each card title. A user-level preference (every project's backlog
# on this machine), because it expresses how the owner likes to read a list, not
# anything about one repo. Empty is the default and means "render the classic
# row untouched" — there is deliberately no built-in starter set.
#
# Values are frontmatter key names, not a fixed choice list: cards may carry any
# key, so the TUI picker offers what the cards in front of you actually have.
# ---------------------------------------------------------------------------

TUI_DEFAULTS: dict[str, list[str]] = {"backlog_fields": []}

# A frontmatter key as `horus.frontmatter` can parse one back: no whitespace, no
# ':', nothing needing TOML escaping. Anything else can't name a real field, so it
# is dropped on read and refused on write rather than persisted into the config.
_FIELD_KEY_RE = re.compile(r"[A-Za-z0-9_.-]+")


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
    # Forward-slashed for consistency with set_workspace_root / _write_config (which
    # store `.as_posix()`); otherwise the default and a round-tripped value differ by
    # separator on Windows. Path() reads either back fine.
    default = (Path.home() / "projects").resolve().as_posix()
    path = config_path()
    if not path.exists():
        return default
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    root = data.get("workspace_root")
    if isinstance(root, str) and root.strip():
        return root
    return default


def _as_key(path: Path) -> str:
    return path.resolve().as_posix()


def _write_projects(projects: list[str]) -> None:
    _write_config(projects, load_github_owners(), load_workspace_root())


# Top-level keys the hand-rolled serializer manages itself. Anything else in the
# file (notably the security-critical `[access]` table) MUST be round-tripped, or a
# routine write (register a project, set a policy) silently drops it — which took the
# exposed dashboard down mid-session (2026-07-10) when `[access]` vanished on a
# `register_project` write.
_MANAGED_KEYS = frozenset({
    "workspace_root", "projects", "github_owners", "ignored_repos", "workflow", "launch",
    "launch_profiles", "tui",
    # Retired 2026-07-19. Still listed so a rewrite DROPS a pre-existing `[continuity]`
    # table instead of round-tripping it forward as an unmanaged entry.
    "continuity",
})


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(v) for v in value) + "]"
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _load_table(name: str) -> dict[str, dict[str, str]]:
    """One managed table-of-tables (e.g. ``[launch_profiles.claude]``) as plain
    dicts, or {} when absent/malformed. Never raises — a hand-edited config must
    degrade to defaults rather than break every launch."""
    path = config_path()
    if not path.exists():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    raw = data.get(name)
    if not isinstance(raw, dict):
        return {}
    return {
        key: {k: v for k, v in val.items() if isinstance(v, str)}
        for key, val in raw.items()
        if isinstance(val, dict)
    }


def _unmanaged_entries() -> tuple[list[str], list[str]]:
    """(scalar_lines, table_lines) for top-level config entries the serializer doesn't
    own, read from the current file so a rewrite preserves them. Scalars belong above
    the tables; tables (e.g. ``[access]``) go last. Flat scalar/list values only —
    the shapes Horus configs actually use."""
    path = config_path()
    if not path.exists():
        return [], []
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return [], []
    scalars: list[str] = []
    tables: list[str] = []
    for key, val in data.items():
        if key in _MANAGED_KEYS:
            continue
        if isinstance(val, dict):
            tables += ["", f"[{key}]"]
            tables += [f"{k} = {_toml_value(v)}" for k, v in val.items()]
        else:
            scalars.append(f"{key} = {_toml_value(val)}")
    return scalars, tables


def _write_config(
    projects: list[str],
    github_owners: list[str],
    workspace_root: str | None = None,
    workflow: dict[str, str] | None = None,
    ignored_repos: list[str] | None = None,
    launch: dict[str, str] | None = None,
    launch_profiles: dict[str, dict[str, str]] | None = None,
    tui: dict[str, list[str]] | None = None,
) -> None:
    config_dir().mkdir(parents=True, exist_ok=True)
    root = workspace_root or load_workspace_root()
    # Preserve the current workflow policy when the caller doesn't supply one.
    if workflow is None:
        workflow = load_workflow_policy()
    # Preserve the current ignored-repos list when the caller doesn't supply one.
    if ignored_repos is None:
        ignored_repos = load_ignored_repos()
    # Preserve the current launch defaults when the caller doesn't supply them.
    if launch is None:
        launch = load_launch_defaults()
    if launch_profiles is None:
        launch_profiles = _load_table("launch_profiles")
    # Preserve the current TUI preferences when the caller doesn't supply them.
    if tui is None:
        tui = load_tui_defaults()
    # Round-trip any table/key we don't manage (e.g. [access]) — read before we write.
    extra_scalars, extra_tables = _unmanaged_entries()
    lines = ["# Horus user config", f'workspace_root = "{Path(root).expanduser().resolve().as_posix()}"']
    lines += extra_scalars
    lines += ["", "projects = ["]
    lines += [f'  "{p}",' for p in projects]
    lines += ["]", "", "github_owners = ["]
    lines += [f'  "{o}",' for o in github_owners]
    lines += ["]", "", "ignored_repos = ["]
    lines += [f'  "{r}",' for r in ignored_repos]
    lines.append("]")
    # [workflow]/[launch] go at the end so they don't accidentally swallow the
    # top-level keys above them in a strict TOML parse (tables extend until the
    # next table header or EOF). Preserved tables ([access]) follow them, still last.
    lines += ["", "[workflow]"]
    lines += [f'{k} = "{v}"' for k, v in workflow.items()]
    lines += ["", "[launch]"]
    lines += [f'{k} = "{v}"' for k, v in launch.items()]
    for agent, profile in sorted(launch_profiles.items()):
        lines += ["", f"[launch_profiles.{agent}]"]
        lines += [f'{k} = "{v}"' for k, v in sorted(profile.items())]
    lines += ["", "[tui]"]
    lines += [f"{k} = {_toml_value(v)}" for k, v in tui.items()]
    lines += extra_tables
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


def load_ignored_repos() -> list[str]:
    """Return the per-machine list of repo full-names (``owner/repo``) to hide."""
    path = config_path()
    if not path.exists():
        return []
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    repos = data.get("ignored_repos", [])
    if not isinstance(repos, list):
        return []
    return [str(r) for r in repos]


def _normalize_ignored_repo(full_name: str) -> str:
    """Strip whitespace and a leading ``github:`` prefix; return the normalized key."""
    key = full_name.strip()
    if key.lower().startswith("github:"):
        key = key[len("github:"):]
    return key


def ignore_repo(full_name: str) -> bool:
    """Add a repo full-name to the per-machine ignore list. Returns True if newly added."""
    key = _normalize_ignored_repo(full_name)
    if not key:
        return False
    existing = load_ignored_repos()
    if key in existing:
        return False
    existing.append(key)
    _write_config(load_projects(), load_github_owners(), load_workspace_root(), ignored_repos=existing)
    return True


def unignore_repo(full_name: str) -> bool:
    """Remove a repo full-name from the per-machine ignore list. Returns True if it was present."""
    key = _normalize_ignored_repo(full_name)
    existing = load_ignored_repos()
    if key not in existing:
        return False
    _write_config(load_projects(), load_github_owners(), load_workspace_root(), ignored_repos=[r for r in existing if r != key])
    return True


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


def load_launch_defaults() -> dict[str, str]:
    """Return the persisted TUI launch defaults, falling back to
    :data:`LAUNCH_DEFAULTS` for anything missing or invalid. Keys: ``posture``,
    ``window``.
    """
    path = config_path()
    if not path.exists():
        return dict(LAUNCH_DEFAULTS)
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return dict(LAUNCH_DEFAULTS)
    raw = data.get("launch") or {}
    if not isinstance(raw, dict):
        return dict(LAUNCH_DEFAULTS)
    posture = raw.get("posture", LAUNCH_DEFAULTS["posture"])
    if not isinstance(posture, str) or posture not in LAUNCH_POSTURE_CHOICES:
        posture = LAUNCH_DEFAULTS["posture"]
    window = raw.get("window", LAUNCH_DEFAULTS["window"])
    if not isinstance(window, str) or window not in LAUNCH_WINDOW_CHOICES:
        window = LAUNCH_DEFAULTS["window"]
    return {"posture": posture, "window": window}


def set_launch_default_posture(posture: str) -> str:
    """Persist the TUI's default launch permission posture (home-level Defaults
    screen, applied to new fresh/resume/card-resume launches). Raises
    ``ValueError`` for any value outside :data:`LAUNCH_POSTURE_CHOICES`.
    """
    if posture not in LAUNCH_POSTURE_CHOICES:
        allowed = ", ".join(LAUNCH_POSTURE_CHOICES)
        raise ValueError(f"Invalid launch posture {posture!r}. Allowed: {allowed}")
    # Merge, never replace — `_write_config` writes the whole [launch] table, so
    # passing posture alone would drop the sibling `window` key.
    launch = load_launch_defaults()
    launch["posture"] = posture
    _write_config(load_projects(), load_github_owners(), load_workspace_root(), launch=launch)
    return posture


def set_launch_default_window(window: str) -> str:
    """Persist how a TUI-launched session opens (``takeover`` | ``new-window``).
    Raises ``ValueError`` outside :data:`LAUNCH_WINDOW_CHOICES`.
    """
    if window not in LAUNCH_WINDOW_CHOICES:
        allowed = ", ".join(LAUNCH_WINDOW_CHOICES)
        raise ValueError(f"Invalid launch window mode {window!r}. Allowed: {allowed}")
    launch = load_launch_defaults()
    launch["window"] = window
    _write_config(load_projects(), load_github_owners(), load_workspace_root(), launch=launch)
    return window


def load_launch_profile(agent: str) -> dict[str, str]:
    """The saved launch profile for one agent, or {} when none was ever saved.

    Keys are a subset of :data:`LAUNCH_PROFILE_KEYS`; a missing key means "no
    saved preference", which the form resolves to the agent's own default rather
    than guessing. An unavailable saved model must fall back visibly at launch —
    this loader does not validate model names, which change with provider releases.
    """
    key = agent.strip()
    if not key:
        return {}
    raw = _load_table("launch_profiles").get(key)
    if not isinstance(raw, dict):
        return {}
    profile = {}
    for field in LAUNCH_PROFILE_KEYS:
        value = raw.get(field)
        if isinstance(value, str) and value:
            profile[field] = value
    return profile


def save_launch_profile(agent: str, profile: dict[str, str]) -> dict[str, str]:
    """Persist one agent's launch profile (owner pressed `Save as defaults`).

    Only :data:`LAUNCH_PROFILE_KEYS` are stored, and a ``None``/empty value drops
    the key so "agent default" round-trips as absence rather than a fake string.
    """
    key = agent.strip()
    if not key:
        raise ValueError("A launch profile needs an agent name.")
    if profile.get("posture") and profile["posture"] not in LAUNCH_POSTURE_CHOICES:
        allowed = ", ".join(LAUNCH_POSTURE_CHOICES)
        raise ValueError(f"Invalid launch posture {profile['posture']!r}. Allowed: {allowed}")
    cleaned = {
        field: profile[field]
        for field in LAUNCH_PROFILE_KEYS
        if isinstance(profile.get(field), str) and profile[field]
    }
    profiles = _load_table("launch_profiles")
    profiles[key] = cleaned
    _write_config(
        load_projects(), load_github_owners(), load_workspace_root(),
        launch_profiles=profiles,
    )
    return cleaned


def _clean_backlog_fields(raw: object) -> list[str]:
    """Normalize a backlog-fields value: keep well-formed key names, in order, once
    each. Anything else (non-list, non-string entry, a key that can't name a real
    frontmatter field) is dropped — a garbled preference degrades to the plain
    default row rather than breaking the backlog list."""
    if not isinstance(raw, list):
        return []
    cleaned: list[str] = []
    for entry in raw:
        if not isinstance(entry, str):
            continue
        key = entry.strip()
        if not _FIELD_KEY_RE.fullmatch(key) or key in cleaned:
            continue
        cleaned.append(key)
    return cleaned


def load_tui_defaults() -> dict[str, list[str]]:
    """Return the persisted user-level TUI preferences, falling back to
    :data:`TUI_DEFAULTS`. Keys: ``backlog_fields`` (card frontmatter keys the
    backlog list renders inline after the title, in render order).
    """
    path = config_path()
    if not path.exists():
        return {"backlog_fields": []}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {"backlog_fields": []}
    raw = data.get("tui") or {}
    if not isinstance(raw, dict):
        return {"backlog_fields": []}
    return {"backlog_fields": _clean_backlog_fields(raw.get("backlog_fields", []))}


def load_backlog_fields() -> list[str]:
    """The card frontmatter keys the TUI backlog list renders inline, in order."""
    return load_tui_defaults()["backlog_fields"]


def set_backlog_fields(fields: list[str]) -> list[str]:
    """Persist the inline backlog fields (global, every project). Returns the stored
    list. Raises ``ValueError`` for anything that cannot name a frontmatter field."""
    cleaned: list[str] = []
    for entry in fields:
        key = entry.strip()
        if not _FIELD_KEY_RE.fullmatch(key):
            raise ValueError(f"Invalid backlog field name {entry!r}.")
        if key not in cleaned:
            cleaned.append(key)
    _write_config(
        load_projects(), load_github_owners(), load_workspace_root(),
        tui={"backlog_fields": cleaned},
    )
    return cleaned


def toggle_backlog_field(field: str) -> list[str]:
    """Add ``field`` to the inline backlog fields, or drop it when already present.
    Persists immediately and returns the new list. New fields append, so the render
    order is the order they were picked."""
    current = load_backlog_fields()
    key = field.strip()
    if key in current:
        return set_backlog_fields([f for f in current if f != key])
    return set_backlog_fields([*current, key])


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


def rename_account_alias(old_alias: str, new_alias: str, *, identifier: str | None = None) -> None:
    """Rename a public alias and carry any isolated account mappings with it.

    ``identifier`` is optional because an isolated account may be configured before
    that account has logged in locally. When present, persist the identifier->alias
    mapping too so future local recovery notes use the friendly name.
    """
    accts = _load_accounts()
    if identifier:
        accts["aliases"][identifier] = new_alias
    for ident, alias in list(accts["aliases"].items()):
        if alias == old_alias:
            accts["aliases"][ident] = new_alias
    if old_alias in accts["config_dirs"]:
        accts["config_dirs"][new_alias] = accts["config_dirs"].pop(old_alias)
    if old_alias in accts["codex_homes"]:
        accts["codex_homes"][new_alias] = accts["codex_homes"].pop(old_alias)
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


# Auth/config files that define a login and must be copied when an account is
# relocated into its own isolated dir. The FIRST entry is the login-defining file
# whose presence proves a real login exists at a source dir.
_ACCOUNT_AUTH_FILES = {
    "claude": (".credentials.json", ".claude.json"),
    "codex": ("auth.json", "config.toml"),
}


def default_account_dir(agent: str, alias: str) -> Path:
    """The canonical isolated config dir for an account: ``~/.horus/accounts/<agent>-<alias>``.

    This is the per-account ``CLAUDE_CONFIG_DIR`` / ``CODEX_HOME`` that isolation uses by
    default, so every account has its own dir and none shares the ambient login."""
    tool = "codex" if agent == "codex" else "claude"
    return config_dir() / "accounts" / f"{tool}-{alias}"


def _ambient_account_dir(agent: str) -> Path:
    """Where ``agent``'s current (un-isolated) login lives: the env override if set,
    else the tool's default home."""
    if agent == "codex":
        return Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))


# The portable, shipped status line: point each Claude account's settings.json at
# `horus statusline` (the `horus` console script is the only guaranteed spelling).
STATUSLINE_POINTER = {"type": "command", "command": "horus statusline"}


def write_statusline_pointer(config_dir_path: str | Path) -> bool:
    """Merge the ``statusLine`` pointer into an account's ``settings.json``.

    The SINGLE writer of the shipped status-line pointer (account-settings-sync,
    when it lands, subsumes this — do not add a second). Idempotent and
    non-destructive: it only sets the ``statusLine`` key, preserving every other
    setting; a no-op returns False. Best-effort — never raises."""
    settings_path = Path(config_dir_path) / "settings.json"
    try:
        data: dict = {}
        if settings_path.exists():
            loaded = json.loads(settings_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        if data.get("statusLine") == STATUSLINE_POINTER:
            return False
        data["statusLine"] = dict(STATUSLINE_POINTER)
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return True
    except (OSError, ValueError):
        return False


# The proxy integration (vision-branch-x4) NEVER writes these into a settings.json —
# a global rewrite poisons already-running sessions, so proxy env is injected per-launch
# (see horus/proxy.py). `clear_proxy_env` remains only to strip env that a pre-B build
# wrote, so disabling/upgrading cleans up. There is deliberately no writer counterpart.
PROXY_ENV_KEYS = (
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY",
)


def clear_proxy_env(config_dir_path: str | Path) -> bool:
    """Remove exactly the ``PROXY_ENV_KEYS`` from an account's ``settings.json`` `env`
    block, leaving every other env var and setting intact. Migration cleanup for env a
    pre-B build wrote; B injects proxy env at launch and never writes settings.json. A
    no-op (none present) returns False. Never raises."""
    settings_path = Path(config_dir_path) / "settings.json"
    try:
        if not settings_path.exists():
            return False
        loaded = json.loads(settings_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            return False
        env = loaded.get("env")
        if not isinstance(env, dict) or not any(k in env for k in PROXY_ENV_KEYS):
            return False
        for k in PROXY_ENV_KEYS:
            env.pop(k, None)
        if env:
            loaded["env"] = env
        else:
            loaded.pop("env", None)  # drop an emptied block rather than leave `{}`
        settings_path.write_text(json.dumps(loaded, indent=2) + "\n", encoding="utf-8")
        return True
    except (OSError, ValueError):
        return False


def isolate_account(agent: str, alias: str) -> tuple[bool, str]:
    """Give ``alias`` its own isolated config dir by default: copy the current login
    into ``~/.horus/accounts/<agent>-<alias>`` and map it there, so two accounts never
    share one config dir (two agent CLIs on one dir corrupt its JSON state).

    Idempotent and non-destructive: a no-op when the alias is already mapped, and it
    only ever *copies* the source login (the ambient login stays intact). Returns
    ``(isolated, message)`` — ``isolated`` is False when nothing could be done (unknown
    agent, or no login found at the source to copy)."""
    files = _ACCOUNT_AUTH_FILES.get(agent)
    if not files:
        return False, f"unknown agent {agent!r} — cannot isolate"
    dirs = load_account_codex_homes() if agent == "codex" else load_account_config_dirs()
    if alias in dirs:
        return True, f"account {alias!r} is already isolated at {dirs[alias]}"
    dest = default_account_dir(agent, alias)
    source = _ambient_account_dir(agent)
    record = set_account_codex_home if agent == "codex" else set_account_config_dir
    if source.resolve() == dest.resolve():
        # The login already physically lives in the canonical dir — just map it.
        record(alias, str(dest))
        if agent == "claude":
            write_statusline_pointer(dest)
        return True, f"mapped {agent} account {alias!r} to its existing dir {dest}"
    if not (source / files[0]).exists():
        return False, f"no {agent} login found at {source} to isolate — log in first, then retry"
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in files:
        src = source / name
        if src.exists():
            shutil.copy2(src, dest / name)
            copied.append(name)
    record(alias, str(dest))
    # Ship the portable status line by default: a freshly isolated Claude account
    # gets the `horus statusline` pointer, no hand-editing on any OS.
    if agent == "claude":
        write_statusline_pointer(dest)
    return True, f"isolated {agent} account {alias!r}: copied {', '.join(copied)} from {source} to {dest}"


def remove_account(alias: str) -> bool:
    """Forget an account from local config: drop its isolated dir mapping(s) and any
    identifier→alias entry. Returns True if anything was removed. The on-disk login
    directory is left intact (unmapping, not deleting)."""
    accts = _load_accounts()
    changed = False
    if alias in accts["config_dirs"]:
        del accts["config_dirs"][alias]
        changed = True
    if alias in accts["codex_homes"]:
        del accts["codex_homes"][alias]
        changed = True
    for ident, mapped in list(accts["aliases"].items()):
        if mapped == alias:
            del accts["aliases"][ident]
            changed = True
    if changed:
        _write_accounts(accts["aliases"], accts["config_dirs"], accts["codex_homes"])
    return changed


def account_login_dir(agent: str, alias: str) -> str:
    """Standard isolated login directory for ``agent``/``alias`` under ``~/.horus``.

    The account-setup wizard derives this instead of asking the user for a path: the
    directory is created and populated by the native CLI's own login flow. Returns a
    forward-slashed string for the same reason ``_write_accounts`` does (clean TOML on
    Windows; ``Path`` reads it back fine everywhere)."""
    safe = re.sub(r"[^A-Za-z0-9_-]", "-", alias.strip()) or "default"
    return (config_dir() / "accounts" / f"{agent}-{safe}").as_posix()


# ---------------------------------------------------------------------------
# Dashboard "exposed mode" — Cloudflare Access gate (opt-in via [access]).
#
# The local dashboard binds loopback and trusts its network. Hosting it behind
# a private hostname (Cloudflare Access + tunnel) requires an app-side gate as a
# second layer. When (and only when) an ``[access]`` block is present in
# ``config.toml``, every dashboard route except ``/health`` demands the owner's
# Access identity header AND a verified Access JWT. Absent block -> unchanged
# loopback-local behavior.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AccessConfig:
    """Cloudflare Access parameters for verifying an Access JWT."""

    team_domain: str
    aud: str
    jwks_url: str


@dataclass(frozen=True)
class DashboardAccess:
    """The dashboard's exposed-mode gate config: owner identity + Access params."""

    owner_email: str
    access: AccessConfig


def _require_str(table: dict, key: str, where: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{where}: missing or empty required string '{key}'.")
    return value.strip()


def load_dashboard_access() -> DashboardAccess | None:
    """Load the optional ``[access]`` block that arms dashboard exposed mode.

    Returns ``None`` when no ``[access]`` table is present (the common local
    case). When the table IS present it must be complete — a missing or empty
    field raises :class:`ConfigError` so the dashboard fails closed at startup
    instead of serving an unguarded control plane.
    """
    path = config_path()
    if not path.exists():
        return None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"config.toml unreadable: {exc}") from exc
    access_raw = data.get("access")
    if access_raw is None:
        return None
    if not isinstance(access_raw, dict):
        raise ConfigError("[access] must be a table.")
    owner_email = _require_str(access_raw, "owner_email", "[access]").lower()
    access = AccessConfig(
        team_domain=_require_str(access_raw, "team_domain", "[access]"),
        aud=_require_str(access_raw, "aud", "[access]"),
        jwks_url=_require_str(access_raw, "jwks_url", "[access]"),
    )
    return DashboardAccess(owner_email=owner_email, access=access)


# --------------------------------------------------------------------------- #
# Naming an account
#
# An account's real identity is (agent, alias): `personal` means one rate-limit
# pool under claude and a different one under codex. But the alias alone is what
# accounts.toml keys on, while the isolated dir it maps to is named
# ``<agent>-<alias>`` (see `default_account_dir`) — so every surface that shows a
# config dir path invites `claude-personal` as the name, when the alias is
# `personal`. That mismatch has produced real, silent damage: split usage caches
# on this machine (`usage-claude-claude-personal.json` beside
# `usage-claude-personal.json`), and an envelope created against a misspelled
# account would have authorized nothing at all while looking correct.
#
# So: resolve names instead of demanding one exact spelling. `<agent>-<alias>` is
# the canonical DISPLAY form *and* an accepted input — the "mistake" is arguably
# the better name, so it is adopted rather than fought. Whatever cannot be
# resolved unambiguously is refused with the real accounts named; nothing is ever
# guessed, because guessing an account routes work to the wrong pool.
# --------------------------------------------------------------------------- #

_AGENT_NAMES = ("claude", "codex")
# Words a human sprinkles when naming an account that carry no identity.
_ACCOUNT_NOISE = frozenset({
    "acc", "account", "accounts", "the", "my", "a", "an", "for", "on", "under", "s",
})


@dataclass(frozen=True)
class AccountRef:
    """One configured isolated account. ``label`` is both how it is displayed and a
    spelling `resolve_account` accepts back."""

    agent: str
    alias: str

    @property
    def label(self) -> str:
        return f"{self.agent}-{self.alias}"


@dataclass(frozen=True)
class AccountResolution:
    """The outcome of naming an account. Exactly one of ``ref`` / ``error`` is set."""

    ref: AccountRef | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.ref is not None


def known_accounts() -> list[AccountRef]:
    """Every configured isolated account, claude first then codex, alias-sorted."""
    refs = [AccountRef("claude", a) for a in sorted(load_account_config_dirs())]
    refs += [AccountRef("codex", a) for a in sorted(load_account_codex_homes())]
    return refs


def _name_tokens(text: str) -> tuple[str | None, list[str]]:
    """Split a human account name into (agent hint, identity tokens).

    "claude personal", "personal claude acc", "claude-personal", "personal acc
    (claude)" all reduce to ("claude", ["personal"]).
    """
    agent: str | None = None
    rest: list[str] = []
    for token in re.split(r"[^A-Za-z0-9]+", text.lower()):
        if not token:
            continue
        if token in _AGENT_NAMES and agent is None:
            agent = token
        elif token not in _ACCOUNT_NOISE:
            rest.append(token)
    return agent, rest


def _alias_tokens(alias: str) -> list[str]:
    return [t for t in re.split(r"[^A-Za-z0-9]+", alias.lower()) if t]


def _slug(text: str) -> str:
    """``Claude Work`` / ``claude_work`` / ``claude-work`` all -> ``claude-work``."""
    return "-".join(t for t in re.split(r"[^A-Za-z0-9]+", text.lower()) if t)


def resolve_account(text: str | None, *, agent: str | None = None) -> AccountResolution:
    """Resolve a human account name to exactly one configured account.

    ``agent`` is the caller's context (the adapter being run, the target being
    checked) and is used only when the name itself does not say. A name that
    matches nothing, or matches more than one account, is REFUSED with the real
    accounts named — never resolved to a best guess, because a wrong account sends
    work to a different rate-limit pool under someone else's subscription.

    Three strategies, most literal first, so an alias that happens to contain an
    agent's name (``work-codex``) still resolves as itself rather than having that
    word read as a hint and stripped:

    1. the alias exactly (``personal``, ``work-codex``);
    2. the canonical label (``claude-personal``) — what the isolated dir is called,
       so it is the name every surface suggests;
    3. tokens, agent word extracted and noise dropped (``personal claude acc``).
    """
    raw = (text or "").strip()
    if not raw:
        return AccountResolution(error="no account named")

    known = known_accounts()
    if not known:
        return AccountResolution(
            error=f"no isolated accounts are configured, so {raw!r} cannot be resolved. "
                  "Add one with `horus account --set <alias> --isolate`."
        )

    context = [ref for ref in known if agent not in _AGENT_NAMES or ref.agent == agent]
    slug = _slug(raw)

    def _resolve(matches: list[AccountRef]) -> AccountResolution | None:
        if len(matches) == 1:
            return AccountResolution(ref=matches[0])
        if len(matches) > 1:
            names = ", ".join(m.label for m in matches)
            return AccountResolution(
                error=f"{raw!r} is ambiguous — it matches {names}. Name the agent too "
                      f"(e.g. {matches[0].label!r})."
            )
        return None

    # 1. the alias, verbatim.
    found = _resolve([ref for ref in context if _slug(ref.alias) == slug])
    # 2. the canonical `<agent>-<alias>` label.
    found = found or _resolve([ref for ref in known if ref.label == slug])
    if found:
        return found

    # 3. tokens: pull the agent word out, drop noise, compare what identity is left.
    hinted_agent, tokens = _name_tokens(raw)
    agent_filter = hinted_agent or (agent if agent in _AGENT_NAMES else None)
    pool = [ref for ref in known if agent_filter is None or ref.agent == agent_filter]
    matches = [ref for ref in pool if _alias_tokens(ref.alias) == tokens]
    if not matches:
        # Order-insensitive pass: "phone work" still names `work-phone`.
        matches = [ref for ref in pool if sorted(_alias_tokens(ref.alias)) == sorted(tokens)]
    found = _resolve(matches)
    if found:
        return found

    return AccountResolution(
        error=f"unknown account {raw!r}. Configured accounts: "
              f"{', '.join(ref.label for ref in known)}."
    )


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
