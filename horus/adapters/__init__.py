"""Agent adapters: a uniform contract for driving official coding-agent CLIs.

The contract (``base.py``) is intentionally thin and tool-neutral: an adapter
turns a normalized :class:`SpawnSpec` into a concrete command + environment,
launches it, and parses its output stream into normalized :class:`AgentEvent`s.
Orchestration code (registry, oversight app, autonomous closure) speaks only the
contract, never a specific CLI.

``FakeAdapter`` implements the whole contract without any real CLI, so the
orchestration layer can be built and tested on any machine — including ones
without ``claude``/``codex`` installed. The real Claude Code adapter is the next
piece and only has to fill in the pure, adapter-specific methods.
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
from horus.adapters.fake import FakeAdapter

__all__ = [
    "AgentAdapter",
    "AgentEvent",
    "AgentRun",
    "AgentSession",
    "EventType",
    "FakeAdapter",
    "PermissionPosture",
    "SpawnSpec",
    "get_adapter",
]


def get_adapter(name: str) -> AgentAdapter:
    """Return an adapter instance by name. Raises ``KeyError`` if unknown.

    Real adapters register here as they land (e.g. ``claude``); ``fake`` is
    always available for tests and dry runs.
    """
    if name == "fake":
        return FakeAdapter()
    raise KeyError(f"unknown agent adapter: {name!r}")
