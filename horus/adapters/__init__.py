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
    EventType,
    PermissionPosture,
    SpawnSpec,
)
from horus.adapters.claude import ClaudeAdapter
from horus.adapters.fake import FakeAdapter

__all__ = [
    "AgentAdapter",
    "AgentEvent",
    "AgentRun",
    "AgentSession",
    "ClaudeAdapter",
    "EventType",
    "FakeAdapter",
    "PermissionPosture",
    "SpawnSpec",
    "get_adapter",
]


def get_adapter(name: str) -> AgentAdapter:
    """Return an adapter instance by name. Raises ``KeyError`` if unknown.

    ``fake`` is always available for tests/dry runs; ``claude`` drives the
    official ``claude`` CLI.
    """
    if name == "fake":
        return FakeAdapter()
    if name == "claude":
        return ClaudeAdapter()
    raise KeyError(f"unknown agent adapter: {name!r}")
