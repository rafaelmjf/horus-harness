"""The agent-adapter contract and the shared subprocess plumbing.

An adapter has four adapter-specific (pure, easily-tested) pieces — the contract:

- ``permission_flags(posture)`` — map a normalized posture to CLI flags.
- ``build_command(spec, resume_id=...)`` — the argv to spawn or resume.
- ``build_env(spec)`` — extra environment (e.g. a per-account config dir, for
  multi-account isolation).
- ``parse_event(line)`` — one line of the agent's output stream -> normalized
  :class:`AgentEvent` (or ``None`` to skip).

Everything else — launching the process, streaming/parsing its stdout, tracking
the session id and status — is shared here in :class:`AgentAdapter`, so a real
adapter stays thin. :class:`AgentRun` is the iterable handle returned by spawn /
resume; iterating it yields events and keeps the :class:`AgentSession` up to date.
"""

from __future__ import annotations

import os
import subprocess
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class PermissionPosture(str, Enum):
    """Normalized permission stance, mapped to per-CLI flags by each adapter."""

    PLAN = "plan"            # think/plan only, no edits or commands
    READ_ONLY = "read-only"  # may read/inspect, never write or run side-effecting tools
    DEFAULT = "default"      # prompt for sensitive actions (the interactive default)
    AUTO_EDIT = "auto-edit"  # auto-accept file edits, still gate other actions
    FULL_AUTO = "full-auto"  # bypass all permission prompts (dangerous; unattended)


class EventType(str, Enum):
    """Normalized event kinds parsed out of an agent's output stream."""

    SESSION_STARTED = "session_started"      # carries the session_id for resume
    ASSISTANT_TEXT = "assistant_text"        # model prose
    TOOL_USE = "tool_use"                    # the agent invoked a tool
    TOOL_RESULT = "tool_result"              # a tool returned
    PERMISSION_REQUEST = "permission_request"  # the agent is asking to do something
    RESULT = "result"                        # turn/run finished
    ERROR = "error"
    RAW = "raw"                              # recognized line we don't model yet


# Reasoning-effort levels accepted by `horus run --effort`. Matches Claude Code's
# own `--effort` enum exactly (probed live, Claude Code 2.1.206); Codex has no
# fixed enum of its own (`-c model_reasoning_effort=<value>` is a free-form TOML
# override validated server-side), so this is the canonical set both adapters share.
EFFORT_LEVELS: tuple[str, ...] = ("low", "medium", "high", "xhigh", "max")


@dataclass(frozen=True)
class SpawnSpec:
    """Everything an adapter needs to start (or resume) a session, tool-neutral."""

    prompt: str
    project_dir: Path
    account: str | None = None          # alias; the adapter maps it to a config/home dir
    environment: str = "host"
    posture: PermissionPosture = PermissionPosture.DEFAULT
    model: str | None = None
    effort: str | None = None           # reasoning effort (one of EFFORT_LEVELS); adapter-specific wiring
    allowed_tools: tuple[str, ...] = ()
    disallowed_tools: tuple[str, ...] = ()
    extra_args: tuple[str, ...] = ()
    worker: bool = False                # unattended worker run (--worker); exported to hooks
    run_session_id: str | None = None   # Horus run id, exported so hooks have a stable key
    proxied: bool = False               # route this launch through the CLIProxyAPI proxy (vision-branch-x4)
    remote_control: bool = False        # request Remote Control at spawn; honored only by adapters that support it (Claude)


@dataclass(frozen=True)
class AgentEvent:
    """A normalized event. ``raw`` keeps the original parsed payload for callers
    that need detail the contract doesn't model yet."""

    type: EventType
    text: str | None = None
    session_id: str | None = None
    tool: str | None = None
    is_error: bool = False
    raw: dict | None = None


@dataclass
class AgentSession:
    """Mutable handle to a running/finished session. Kept current by AgentRun.

    This is the shape the future registry persists:
    ``(agent, account, project, environment, pid, session_id, status)``.
    """

    agent: str
    project_dir: Path
    account: str | None = None
    environment: str = "host"
    session_id: str | None = None
    pid: int | None = None
    status: str = "running"             # running | exited | failed
    returncode: int | None = None


class AgentRun:
    """Iterable handle over a session's event stream.

    Iterating yields :class:`AgentEvent`s and, as a side effect, fills in the
    session id (from the first event that carries one) and flips the session to a
    terminal status when the run ends. Iterate at most once.
    """

    def __init__(self, session: AgentSession, events: Iterable[AgentEvent]) -> None:
        self.session = session
        self._events = events

    def __iter__(self) -> Iterator[AgentEvent]:
        result_error: bool | None = None
        saw_stream_error = False
        for ev in self._events:
            if ev.session_id and not self.session.session_id:
                self.session.session_id = ev.session_id
            if ev.type is EventType.RESULT:
                result_error = ev.is_error
            elif ev.type is EventType.ERROR:
                saw_stream_error = True
            yield ev
        if self.session.status == "running":
            # The terminal RESULT event is authoritative: a failing tool call
            # mid-run (a denied permission, a red test) is normal work, not a
            # failed run. Adapter-level ERROR events decide only when no RESULT
            # closed the stream.
            failed = result_error if result_error is not None else saw_stream_error
            self.session.status = "failed" if failed else "exited"

    def drain(self) -> list[AgentEvent]:
        """Consume the whole stream and return every event (convenience for tests)."""
        return list(self)


class AgentAdapter(ABC):
    """Base class for all adapters. Subclasses implement the four contract methods;
    spawn/resume/streaming are shared here so real adapters stay thin."""

    name: str = "agent"

    # The `--model`/`-m` selectors this adapter's CLI actually accepts, for
    # surfaces (like the TUI's launch flow) that need to offer a scoped choice
    # without hardcoding a model list of their own. Empty by default; a real
    # adapter overrides it with its own static roster.
    KNOWN_MODELS: tuple[str, ...] = ()

    # Whether this agent's CLI supports Remote Control (reach a live interactive
    # session from the native app). Only a capable adapter honors
    # ``SpawnSpec.remote_control``; others ignore the request. Claude-only today.
    supports_remote_control: bool = False

    # --- the contract: adapter-specific, pure, individually testable ---------

    @abstractmethod
    def permission_flags(self, posture: PermissionPosture) -> list[str]:
        """CLI flags realizing ``posture`` for this agent."""

    @abstractmethod
    def build_command(self, spec: SpawnSpec, *, resume_id: str | None = None) -> list[str]:
        """The argv to spawn a new session, or resume ``resume_id`` when given."""

    def build_env(self, spec: SpawnSpec) -> dict[str, str]:
        """Extra environment for the child (per-account isolation, etc.). Default: none."""
        return {}

    def validate_model(self, model: str | None) -> str | None:
        """Reject a ``model`` selector this adapter's CLI cannot execute.

        Returns an actionable error message, or ``None`` when `model` is
        unset or provider-valid. Purely local/static — never queries the
        provider or spends tokens to discover a selector. Default: no
        adapter-specific naming rules, so every selector passes through.
        """
        return None

    @abstractmethod
    def parse_event(self, line: str) -> list[AgentEvent]:
        """Parse one output line into zero or more events.

        A list (not a single event) because one stream line can carry several
        normalized events — e.g. a Claude ``assistant`` message whose content is
        both a text block and a tool_use block. Return ``[]`` to ignore a line.
        """

    # --- shared orchestration -------------------------------------------------

    def spawn(self, spec: SpawnSpec) -> AgentRun:
        return self._launch(spec, resume_id=None)

    def resume(self, session_id: str, spec: SpawnSpec) -> AgentRun:
        return self._launch(spec, resume_id=session_id)

    def _launch(self, spec: SpawnSpec, *, resume_id: str | None) -> AgentRun:
        argv = self.build_command(spec, resume_id=resume_id)
        env = {**os.environ, **self.build_env(spec)}
        proc = subprocess.Popen(  # noqa: S603 (argv built by the adapter, not shell)
            argv,
            cwd=str(spec.project_dir),
            env=env,
            stdin=subprocess.DEVNULL,  # the prompt is an arg; don't let the child wait on stdin
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        session = AgentSession(
            agent=self.name,
            project_dir=spec.project_dir,
            account=spec.account,
            environment=spec.environment,
            session_id=resume_id,
            pid=proc.pid,
        )
        return AgentRun(session, self._stream(proc, session))

    def _stream(self, proc: subprocess.Popen, session: AgentSession) -> Iterator[AgentEvent]:
        assert proc.stdout is not None
        for line in proc.stdout:
            yield from self.parse_event(line.rstrip("\n"))
        session.returncode = proc.wait()
        if session.returncode != 0:
            session.status = "failed"


__all__ = [
    "AgentAdapter",
    "AgentEvent",
    "AgentRun",
    "AgentSession",
    "EFFORT_LEVELS",
    "EventType",
    "PermissionPosture",
    "SpawnSpec",
]
