"""Clone/register/start helpers for remote catalog entries."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from horus import closure, config, github_catalog, initialize, integration, upgrade


@dataclass(frozen=True)
class StartResult:
    project: github_catalog.RemoteProject
    path: Path
    cloned: bool
    registered: bool
    upgrade_actions: list[upgrade.UpgradeAction]


@dataclass(frozen=True)
class OnboardResult:
    repo: github_catalog.UntrackedRepo
    path: Path
    cloned: bool
    registered: bool
    init_actions: list
    integration: integration.IntegrationResult
    git_identity: str


@dataclass(frozen=True)
class GitIdentity:
    name: str
    email: str


def _git_config_value(root: Path, key: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "config", "--get", key],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def _read_git_identity(root: Path) -> GitIdentity | None:
    """Read the effective Git author identity, including repository-local config."""
    name = _git_config_value(root, "user.name")
    email = _git_config_value(root, "user.email")
    return GitIdentity(name, email) if name and email else None


def _configure_local_git_identity(root: Path, identity: GitIdentity) -> None:
    """Copy a known identity into the target repository without changing global config."""
    for key, value in (("user.name", identity.name), ("user.email", identity.email)):
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "config", "--local", key, value],
                text=True,
                capture_output=True,
                check=False,
            )
        except OSError as exc:
            raise RuntimeError(f"could not configure repository-local Git identity: {exc}") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "git config failed").strip()
            raise RuntimeError(f"could not configure repository-local Git identity: {detail}")


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
    result = github_catalog.discover(owner, local_projects=config.load_projects(), limit=limit)
    project = next((p for p in result.projects if p.full_name.lower() == f"{owner}/{repo}".lower()), None)
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


def _clone_repo(full_name: str, path: Path) -> bool:
    """Clone a GitHub repo by full_name into path.

    Returns True when a new clone was made, False when the destination already
    exists as a git clone (reuse). Raises RuntimeError on conflict or gh failure.
    """
    if path.exists():
        if (path / ".git").is_dir():
            return False
        raise RuntimeError(f"destination already exists and is not a git clone: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["gh", "repo", "clone", full_name, str(path)],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise RuntimeError(f"gh repo clone failed: {exc}") from exc
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "gh repo clone failed").strip())
    return True


# Paths that the onboard step might create inside a cloned repo — we only stage
# files that actually exist so we never sweep unrelated working-tree changes.
# Specific projected-artifact paths (not whole `.claude`/`.codex` dirs) so a
# pre-existing user-local file like .claude/settings.local.json is never staged.
_HORUS_MANAGED_PATHS = (
    ".horus",
    "AGENTS.md",
    "CLAUDE.md",
    *closure.PROJECTED_ARTIFACT_PATHS,
    ".gitignore",
)


def onboard_github_project(
    target: str,
    *,
    workspace_root: Path | None = None,
    limit: int = 100,
    policy: dict | None = None,
) -> OnboardResult:
    """Take an untracked GitHub repo and make it a Horus project in one step.

    Steps:
    1. Parse ``target`` (``github:owner/repo``).
    2. Run discovery; error if the repo is already a Horus project or not found.
    3. Preflight a complete Git author identity before clone/init; inherit the
       invoking repository's identity as target-local config when needed.
    4. Clone if the repo has no local path yet.
    5. Guard: error if ``.horus/`` already exists in the clone.
    6. Run ``horus init`` non-interactively.
    7. Register in the local config.
    8. Integrate via the workflow policy (branch-PR-automerge by default).

    A non-ok IntegrationResult is NOT a hard failure — clone + init + commit may
    already have succeeded. The caller surfaces integration failures as warnings.
    """
    owner, repo = parse_github_target(target)
    result = github_catalog.discover(owner, local_projects=config.load_projects(), limit=limit)

    full_name_lower = f"{owner}/{repo}".lower()

    # Already a Horus project?
    already = next((p for p in result.projects if p.full_name.lower() == full_name_lower), None)
    if already is not None:
        raise RuntimeError(
            f"{owner}/{repo} is already a Horus project; use `horus start github:{owner}/{repo}` instead"
        )

    # Find in untracked.
    untracked = next((u for u in result.untracked if u.full_name.lower() == full_name_lower), None)
    if untracked is None:
        raise RuntimeError(f"no GitHub repo found for {owner}/{repo}")

    invoking_identity = _read_git_identity(Path.cwd())

    # Determine path and whether to clone. A new clone requires identity before
    # any filesystem mutation, so onboarding never discovers the problem at commit.
    if untracked.local_path:
        path = Path(untracked.local_path).resolve()
        cloned = False
    else:
        if invoking_identity is None:
            raise RuntimeError(
                "no complete Git author identity is available; configure user.name "
                "and user.email in the invoking repository or globally before onboarding"
            )
        root = (workspace_root or Path(config.load_workspace_root())).expanduser().resolve()
        path = root / untracked.name
        cloned = _clone_repo(untracked.full_name, path)

    # Guard: don't overwrite an existing .horus/.
    if (path / ".horus").is_dir():
        raise RuntimeError(
            f"{path} already has .horus/; not overwriting (use `horus start` to register it)"
        )

    target_identity = _read_git_identity(path)
    if target_identity is not None:
        identity_detail = "using the target repository's effective Git author identity"
    elif invoking_identity is not None:
        _configure_local_git_identity(path, invoking_identity)
        identity_detail = "inherited the invoking Git author identity as repository-local config"
    else:
        raise RuntimeError(
            "no complete Git author identity is available; configure user.name "
            "and user.email in the target or invoking repository before onboarding"
        )

    # Register first so this call reports whether onboarding newly added the project
    # (init_project also registers internally, but that later call then returns False).
    registered = config.register_project(path)

    # Scaffold .horus/ + instruction blocks + skills.
    init_actions = initialize.init_project(path, assume_yes=True, no_input=True)

    # Build the file list: only include top-level Horus-managed items that now exist.
    files = [
        str(path / name) if (path / name).exists() else None
        for name in _HORUS_MANAGED_PATHS
    ]
    files_to_stage = [f for f in files if f is not None]

    # Integrate via the workflow policy.
    integ = integration.integrate(
        path,
        message="chore(horus): initialize Horus project continuity",
        files=files_to_stage if files_to_stage else None,
        title="Initialize Horus project continuity",
        body="Scaffolds .horus/ continuity lanes and agent instruction blocks via `horus onboard`.",
        policy=policy,
    )

    return OnboardResult(
        repo=untracked,
        path=path,
        cloned=cloned,
        registered=registered,
        init_actions=init_actions,
        integration=integ,
        git_identity=identity_detail,
    )
