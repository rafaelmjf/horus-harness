"""User-level Horus config: the list of project paths the dashboard knows about,
plus the account-alias map.

Stored under ``~/.horus/`` (``config.toml`` for projects, ``accounts.toml`` for
aliases). Read with stdlib ``tomllib``; written with tiny hand-rolled serializers
to stay dependency-free. Paths are stored with forward slashes so they need no
TOML escaping and work on Windows.
"""

from __future__ import annotations

import hashlib
import re
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

LAUNCH_DEFAULTS: dict[str, str] = {"posture": "default"}

LAUNCH_POSTURE_CHOICES: tuple[str, ...] = ("plan", "read-only", "default", "auto-edit", "full-auto")

# Narrative continuity is intentionally independent from delivery safety.  Git
# commits/branches/PRs and the commit+push checkpoint remain mandatory in every
# mode; this setting controls only how often canonical `.horus/` prose is folded.
CONTINUITY_DEFAULTS: dict[str, str] = {"granularity": "handoff"}
CONTINUITY_GRANULARITY_CHOICES: tuple[str, ...] = ("handoff", "delivery", "manual")


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
    "workspace_root", "projects", "github_owners", "ignored_repos", "workflow", "launch", "continuity",
})


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(v) for v in value) + "]"
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


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
    continuity: dict[str, str] | None = None,
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
    if continuity is None:
        continuity = load_continuity_defaults()
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
    lines += ["", "[continuity]"]
    lines += [f'{k} = "{v}"' for k, v in continuity.items()]
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
    :data:`LAUNCH_DEFAULTS` for anything missing or invalid. Keys: ``posture``.
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
    value = raw.get("posture", LAUNCH_DEFAULTS["posture"])
    if not isinstance(value, str) or value not in LAUNCH_POSTURE_CHOICES:
        value = LAUNCH_DEFAULTS["posture"]
    return {"posture": value}


def set_launch_default_posture(posture: str) -> str:
    """Persist the TUI's default launch permission posture (home-level Defaults
    screen, applied to new fresh/resume/card-resume launches). Raises
    ``ValueError`` for any value outside :data:`LAUNCH_POSTURE_CHOICES`.
    """
    if posture not in LAUNCH_POSTURE_CHOICES:
        allowed = ", ".join(LAUNCH_POSTURE_CHOICES)
        raise ValueError(f"Invalid launch posture {posture!r}. Allowed: {allowed}")
    _write_config(load_projects(), load_github_owners(), load_workspace_root(), launch={"posture": posture})
    return posture


def load_continuity_defaults() -> dict[str, str]:
    """Return the local continuity policy used by CLI, hooks, and TUI.

    ``handoff`` is deliberately the compatibility fallback, including on a
    clean CI runner or a second machine with no user config yet.
    """
    path = config_path()
    if not path.exists():
        return dict(CONTINUITY_DEFAULTS)
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return dict(CONTINUITY_DEFAULTS)
    raw = data.get("continuity") or {}
    if not isinstance(raw, dict):
        return dict(CONTINUITY_DEFAULTS)
    value = raw.get("granularity", CONTINUITY_DEFAULTS["granularity"])
    if not isinstance(value, str) or value not in CONTINUITY_GRANULARITY_CHOICES:
        value = CONTINUITY_DEFAULTS["granularity"]
    return {"granularity": value}


def set_continuity_granularity(granularity: str) -> str:
    """Persist narrative checkpoint granularity without changing safety gates."""
    if granularity not in CONTINUITY_GRANULARITY_CHOICES:
        allowed = ", ".join(CONTINUITY_GRANULARITY_CHOICES)
        raise ValueError(f"Invalid continuity granularity {granularity!r}. Allowed: {allowed}")
    _write_config(
        load_projects(), load_github_owners(), load_workspace_root(),
        continuity={"granularity": granularity},
    )
    return granularity


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
