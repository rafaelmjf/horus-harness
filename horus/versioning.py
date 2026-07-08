"""Structure-version floor: the minimum horus-harness a repo's `.horus/` needs.

A project records the oldest CLI that can safely touch its continuity structure in
`.horus/PRD.md` frontmatter (`horus_min_version`). Two independent guards honor it:

- **Lever A (agent-enforced):** the shared managed block tells the session agent to
  compare `horus --version` against this floor *before* running any state-mutating
  `horus` command, and to stop and ask the user to upgrade if it is below. This is the
  only guard that binds an already-installed *old* CLI — an ancient binary predates
  every code check we could add, so the protection must live in text the agent reads.
- **Lever B (code-enforced):** `cli._enforce_version_floor` refuses to run a mutating
  command when the *running* CLI is below the repo's recorded floor. Forward-only (a
  CLI that predates this module has no gate), it stops a future structure break from
  being applied by a merely-stale-but-gate-aware CLI.

`MIN_CLI_VERSION` is the floor stamped into freshly scaffolded / upgraded repos: the
release that ships these safeguards and guarantees the PRD-native (v3) structure. Raise
it only on a genuine structure break that older CLIs would mishandle.
"""

from __future__ import annotations

from pathlib import Path

from horus import frontmatter

# The release that ships the version-floor safeguards + guarantees v3 structure.
# Bump only when a structure change would be corrupted by an older CLI.
MIN_CLI_VERSION = "0.0.26"

# Frontmatter key carrying the floor in `.horus/PRD.md`.
MIN_VERSION_KEY = "horus_min_version"


def version_tuple(version: str) -> tuple[int, ...]:
    """Parse a dotted version into a comparable integer tuple (``0.0.26`` ->
    ``(0, 0, 26)``). Each piece keeps its digits only, concatenated; a piece with no
    digits counts as 0. Horus ships plain ``X.Y.Z`` releases, so this is exact for
    them and merely deterministic (not semver-correct) for pre-release suffixes.
    Preserves ``selfupdate._version_tuple``'s long-standing behavior.
    """
    parts: list[int] = []
    for piece in version.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def is_at_least(installed: str, floor: str) -> bool:
    """True when ``installed`` is >= ``floor`` under tuple comparison."""
    return version_tuple(installed) >= version_tuple(floor)


def read_floor(project_root: Path) -> str | None:
    """The `horus_min_version` recorded in the project's PRD.md, or None when the
    project has no PRD.md or no floor stamped (a v2 project, or a v3 project that
    predates the stamp — both left ungated by Lever B)."""
    doc = frontmatter.parse_file(frontmatter.prd_path(project_root))
    if doc is None:
        return None
    floor = doc.front_matter.get(MIN_VERSION_KEY, "").strip()
    return floor or None


def enforce(project_root: Path, installed: str) -> str | None:
    """Return an error message when ``installed`` is below the project's recorded
    floor, else None. The message names both versions and the fix so callers can print
    it verbatim before refusing to mutate `.horus/`."""
    floor = read_floor(project_root)
    if floor is None or is_at_least(installed, floor):
        return None
    return (
        f"This project's .horus/ requires horus-harness >= {floor}, but the installed "
        f"CLI is {installed}. An older CLI can silently regress the continuity structure "
        f"(e.g. back to the retired six-lane layout). Upgrade first:\n"
        f"    uv tool install --force --python 3.12 horus-harness\n"
        f"then re-run. (Override with HORUS_IGNORE_VERSION_FLOOR=1 only if you know why.)"
    )
