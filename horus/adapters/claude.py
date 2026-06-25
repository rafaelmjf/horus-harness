"""Claude Code adapter — drives the official ``claude`` CLI against the contract.

Thin by design: only the four pure methods are Claude-specific; spawn/resume,
subprocess streaming, and session tracking come from :class:`AgentAdapter`.

Built against Claude Code 2.1.191's headless surface:
- spawn:  ``claude -p <prompt> --output-format stream-json --verbose``
- resume: ``... --resume <session_id>`` (the id is echoed in the ``system/init`` event)
- per-account isolation: ``CLAUDE_CONFIG_DIR`` (a distinct config/home dir per account)

Subscription-auth only: it runs the user's own logged-in ``claude``; no API key.
"""

from __future__ import annotations

from pathlib import Path

import json

from horus.adapters.base import (
    AgentAdapter,
    AgentEvent,
    EventType,
    PermissionPosture,
    SpawnSpec,
)

# Normalized posture -> Claude Code --permission-mode value. Claude has no pure
# read-only mode, so READ_ONLY maps to "plan" (its no-side-effects stance).
_PERMISSION_MODE: dict[PermissionPosture, str] = {
    PermissionPosture.PLAN: "plan",
    PermissionPosture.READ_ONLY: "plan",
    PermissionPosture.DEFAULT: "default",
    PermissionPosture.AUTO_EDIT: "acceptEdits",
    PermissionPosture.FULL_AUTO: "bypassPermissions",
}


class ClaudeAdapter(AgentAdapter):
    name = "claude"

    def __init__(self, *, executable: str = "claude", config_dirs: dict[str, str] | None = None) -> None:
        """``config_dirs`` maps an account alias to its ``CLAUDE_CONFIG_DIR`` for
        multi-account isolation. Unmapped accounts use the ambient login."""
        self.executable = executable
        self.config_dirs = config_dirs or {}

    # --- contract -------------------------------------------------------------

    def permission_flags(self, posture: PermissionPosture) -> list[str]:
        return ["--permission-mode", _PERMISSION_MODE[posture]]

    def build_command(self, spec: SpawnSpec, *, resume_id: str | None = None) -> list[str]:
        # stream-json output requires --verbose under --print.
        argv = [self.executable, "-p", spec.prompt, "--output-format", "stream-json", "--verbose"]
        if resume_id:
            argv += ["--resume", resume_id]
        if spec.model:
            argv += ["--model", spec.model]
        argv += self.permission_flags(spec.posture)
        if spec.allowed_tools:
            argv += ["--allowedTools", ",".join(spec.allowed_tools)]
        if spec.disallowed_tools:
            argv += ["--disallowedTools", ",".join(spec.disallowed_tools)]
        argv += list(spec.extra_args)
        return argv

    def build_env(self, spec: SpawnSpec) -> dict[str, str]:
        cfg = self.config_dirs.get(spec.account) if spec.account else None
        return {"CLAUDE_CONFIG_DIR": str(Path(cfg))} if cfg else {}

    def parse_event(self, line: str) -> list[AgentEvent]:
        line = line.strip()
        if not line:
            return []
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            return [AgentEvent(EventType.RAW, text=line)]

        kind = obj.get("type")
        sid = obj.get("session_id")
        if kind == "system" and obj.get("subtype") == "init":
            return [AgentEvent(EventType.SESSION_STARTED, session_id=sid, raw=obj)]
        if kind == "assistant":
            return self._content_events(obj, sid, role="assistant")
        if kind == "user":
            return self._content_events(obj, sid, role="user")
        if kind == "result":
            return [AgentEvent(
                EventType.RESULT,
                text=obj.get("result"),
                session_id=sid,
                is_error=bool(obj.get("is_error")),
                raw=obj,
            )]
        # rate_limit_event, system/thinking_tokens, system/post_turn_summary, etc.
        return []

    @staticmethod
    def _content_events(obj: dict, sid: str | None, *, role: str) -> list[AgentEvent]:
        content = (obj.get("message") or {}).get("content") or []
        events: list[AgentEvent] = []
        for block in content:
            btype = block.get("type")
            if btype == "text":
                events.append(AgentEvent(EventType.ASSISTANT_TEXT, text=block.get("text"), session_id=sid, raw=block))
            elif btype == "tool_use":
                events.append(AgentEvent(EventType.TOOL_USE, tool=block.get("name"), session_id=sid, raw=block))
            elif btype == "tool_result":
                events.append(AgentEvent(
                    EventType.TOOL_RESULT, session_id=sid, is_error=bool(block.get("is_error")), raw=block
                ))
            # "thinking" blocks are intentionally not surfaced as normalized events.
        return events
