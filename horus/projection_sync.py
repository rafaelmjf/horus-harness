"""Read-only projection-sync check: does each agent surface carry the current
generation of projected artifacts.

Design: compare each surface (Claude, Codex) to the *installed CLI*, never
surfaces to each other. `upgrade.upgrade_project(root, apply=False, ...)` is
already the single source of truth for staleness (see `dashboard.load_project`'s
`artifacts_stale`/`cli_outdated` flags); this module runs it once per surface and
summarizes the result for the dashboard's per-project sync badge.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from horus import upgrade

# Which instruction file belongs to which surface, for attributing the shared
# `_upgrade_instructions` pass (it always writes/checks BOTH files regardless of
# `targets` - that param only routes skills and hooks).
_OWN_FILE = {"claude": "CLAUDE.md", "codex": "AGENTS.md"}
_OTHER_FILE = {"claude": "AGENTS.md", "codex": "CLAUDE.md"}

_NEWER_MARKER = "newer than this CLI"


def sync_state(root: Path) -> dict[str, Any]:
    """Per-surface sync summary plus a project-level verdict.

    Never raises: a broken project (unreadable files, etc.) yields
    ``{"verdict": "unknown"}`` so the dashboard can render a muted state instead
    of failing the whole page.
    """
    try:
        claude = _surface_state(root, "claude")
        codex = _surface_state(root, "codex")
    except Exception:
        return {"verdict": "unknown"}
    return {"claude": claude, "codex": codex, "verdict": _verdict(claude, codex)}


def _surface_state(root: Path, surface: str) -> dict[str, Any]:
    actions = upgrade.upgrade_project(root, apply=False, targets=(surface,))
    own_file = _OWN_FILE[surface]
    other_file = _OTHER_FILE[surface]
    ahead = False
    pending = 0
    for action in actions:
        # Skip the other surface's instruction action so it isn't double-counted -
        # `_upgrade_instructions` always covers both AGENTS.md and CLAUDE.md.
        if other_file in action.message and own_file not in action.message:
            continue
        if _NEWER_MARKER in action.message:
            ahead = True
        elif action.status == "would-update":
            pending += 1
    if ahead:
        return {"status": "ahead", "pending": 0}
    return {"status": "behind" if pending else "current", "pending": pending}


def _verdict(claude: dict[str, Any], codex: dict[str, Any]) -> str:
    # Ahead wins: the remedy is upgrading the CLI, not refreshing the repo, and
    # that trumps any "behind" signal from the other surface.
    if claude["status"] == "ahead" or codex["status"] == "ahead":
        return "cli_outdated"
    claude_behind = claude["status"] == "behind"
    codex_behind = codex["status"] == "behind"
    if claude_behind and codex_behind:
        return "behind"
    if claude_behind:
        return "claude_behind"
    if codex_behind:
        return "codex_behind"
    return "in_sync"
