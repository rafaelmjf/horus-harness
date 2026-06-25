"""A fully in-memory adapter that implements the whole contract without any CLI.

It lets the orchestration layer (registry, oversight, autonomous closure) be
built and tested anywhere — no ``claude``/``codex`` needed. The fake speaks a
small JSON-lines stream that mirrors the *shape* of a real stream-json output
(init -> text/tool -> result), so it exercises the same ``parse_event`` ->
:class:`AgentRun` path a real adapter will. spawn/resume produce that stream
in memory instead of from a subprocess.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

from horus.adapters.base import (
    AgentAdapter,
    AgentEvent,
    AgentRun,
    AgentSession,
    EventType,
    PermissionPosture,
    SpawnSpec,
)

# Illustrative posture -> flag mapping. Real adapters define their own; this one
# resembles Claude Code's so orchestration tests look like the real thing.
_POSTURE_FLAGS: dict[PermissionPosture, list[str]] = {
    PermissionPosture.PLAN: ["--permission-mode", "plan"],
    PermissionPosture.READ_ONLY: ["--permission-mode", "plan"],
    PermissionPosture.DEFAULT: ["--permission-mode", "default"],
    PermissionPosture.AUTO_EDIT: ["--permission-mode", "acceptEdits"],
    PermissionPosture.FULL_AUTO: ["--dangerously-skip-permissions"],
}


class FakeAdapter(AgentAdapter):
    name = "fake"

    def __init__(self, *, session_id: str = "fake-session", script: list[dict] | None = None) -> None:
        """``script`` overrides the default event stream with raw line payloads
        (each a dict, JSON-encoded then parsed back through ``parse_event``)."""
        self.session_id = session_id
        self._script = script

    # --- contract -------------------------------------------------------------

    def permission_flags(self, posture: PermissionPosture) -> list[str]:
        return list(_POSTURE_FLAGS[posture])

    def build_command(self, spec: SpawnSpec, *, resume_id: str | None = None) -> list[str]:
        argv = ["fake-agent", "-p", spec.prompt, "--output-format", "stream-json"]
        if resume_id:
            argv += ["--resume", resume_id]
        if spec.model:
            argv += ["--model", spec.model]
        argv += self.permission_flags(spec.posture)
        for tool in spec.allowed_tools:
            argv += ["--allow", tool]
        for tool in spec.disallowed_tools:
            argv += ["--deny", tool]
        argv += list(spec.extra_args)
        return argv

    def build_env(self, spec: SpawnSpec) -> dict[str, str]:
        # Stand-in for real per-account isolation (e.g. CLAUDE_CONFIG_DIR).
        return {"FAKE_AGENT_ACCOUNT": spec.account} if spec.account else {}

    def interactive_command(self, spec: SpawnSpec, *, session_id: str) -> list[str]:
        return ["fake-agent", "--session-id", session_id]

    def parse_event(self, line: str) -> list[AgentEvent]:
        line = line.strip()
        if not line:
            return []
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            return [AgentEvent(EventType.RAW, text=line)]
        kind = obj.get("event")
        if kind == "init":
            return [AgentEvent(EventType.SESSION_STARTED, session_id=obj.get("session_id"), raw=obj)]
        if kind == "text":
            return [AgentEvent(EventType.ASSISTANT_TEXT, text=obj.get("text"), raw=obj)]
        if kind == "tool":
            return [AgentEvent(EventType.TOOL_USE, tool=obj.get("tool"), raw=obj)]
        if kind == "permission":
            return [AgentEvent(EventType.PERMISSION_REQUEST, tool=obj.get("tool"), raw=obj)]
        if kind == "result":
            return [AgentEvent(EventType.RESULT, is_error=not bool(obj.get("ok", True)), raw=obj)]
        if kind == "error":
            return [AgentEvent(EventType.ERROR, text=obj.get("message"), is_error=True, raw=obj)]
        return [AgentEvent(EventType.RAW, text=line, raw=obj)]

    # --- orchestration: in-memory instead of a subprocess ---------------------

    def _launch(self, spec: SpawnSpec, *, resume_id: str | None) -> AgentRun:
        session = AgentSession(
            agent=self.name,
            project_dir=spec.project_dir,
            account=spec.account,
            environment=spec.environment,
            session_id=resume_id,
            pid=None,
        )
        return AgentRun(session, self._emit(spec, resume_id))

    def _emit(self, spec: SpawnSpec, resume_id: str | None) -> Iterator[AgentEvent]:
        for payload in self._script_lines(spec, resume_id):
            yield from self.parse_event(json.dumps(payload))

    def _script_lines(self, spec: SpawnSpec, resume_id: str | None) -> list[dict]:
        if self._script is not None:
            return list(self._script)
        return [
            {"event": "init", "session_id": resume_id or self.session_id},
            {"event": "text", "text": f"(fake) {spec.prompt}"},
            {"event": "result", "ok": True},
        ]
