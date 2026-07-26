"""Agent adapters: a uniform contract for driving official coding-agent CLIs.

The contract (``base.py``) is intentionally thin and tool-neutral: an adapter
turns a normalized :class:`SpawnSpec` into a concrete command + environment,
launches it, and parses its output stream into normalized :class:`AgentEvent`s.
Orchestration code (registry, oversight app, autonomous closure) speaks only the
contract, never a specific CLI.

``FakeAdapter`` implements the whole contract without any real CLI, so the
orchestration layer can be built and tested on any machine — including ones
without ``claude``/``codex`` installed. ``ClaudeAdapter`` drives the official
``claude`` CLI and only fills in the pure, adapter-specific methods.
"""

from __future__ import annotations

from horus.adapters.base import (
    AgentAdapter,
    AgentEvent,
    AgentRun,
    AgentSession,
    EFFORT_LEVELS,
    EventType,
    PermissionPosture,
    SpawnSpec,
)
from horus.adapters.claude import AccountMismatch, ClaudeAdapter, IdentityCheck
from horus.adapters.codex import CodexAdapter
from horus.adapters.fake import FakeAdapter

__all__ = [
    "AccountMismatch",
    "AgentAdapter",
    "AgentEvent",
    "AgentRun",
    "AgentSession",
    "ClaudeAdapter",
    "CodexAdapter",
    "EFFORT_LEVELS",
    "EventType",
    "FakeAdapter",
    "IdentityCheck",
    "PermissionPosture",
    "SpawnSpec",
    "account_dirs",
    "get_adapter",
]


def account_dirs(adapter: AgentAdapter) -> dict[str, str]:
    """The adapter's alias -> isolated-config-dir map, whatever it calls it.

    Claude exposes ``config_dirs`` (``CLAUDE_CONFIG_DIR``), Codex exposes
    ``codex_homes`` (``CODEX_HOME``). Every launch path gates its identity check on
    "is this alias mapped to an isolated dir", so it must ask through here rather
    than reaching for one adapter's attribute name: `getattr(adapter,
    "config_dirs", {})` silently returns ``{}`` for Codex, which skips the guard
    entirely instead of failing loudly. That was the `codex-identity-guard` defect,
    and fixing it in one launch path (#404, `launch.py`) left the PTY-hosted path
    still skipping it — hence one shared accessor.
    """
    dirs = getattr(adapter, "config_dirs", None)
    if dirs is None:
        dirs = getattr(adapter, "codex_homes", None)
    return dirs or {}


def get_adapter(name: str) -> AgentAdapter:
    """Return an adapter instance by name. Raises ``KeyError`` if unknown.

    ``fake`` is always available for tests/dry runs; ``claude`` drives the
    official ``claude`` CLI; ``codex`` drives the official ``codex`` CLI.
    """
    if name == "fake":
        return FakeAdapter()
    if name == "claude":
        return ClaudeAdapter()
    if name == "codex":
        return CodexAdapter()
    raise KeyError(f"unknown agent adapter: {name!r}")
