"""Codex adapter — drives the official ``codex`` CLI against the contract.

Thin by design: only the four pure methods are Codex-specific; spawn/resume,
subprocess streaming, and session tracking come from :class:`AgentAdapter`.

Built against the real Codex CLI's exec surface (probed directly):
- spawn:  ``codex exec --json <prompt>``
- resume: ``codex exec resume --json <session_id> [prompt]``
- per-account isolation: ``CODEX_HOME`` (a distinct config/home dir per account)
- reasoning effort: Codex's CLI has no dedicated ``--effort``/``--reasoning`` flag
  (probed via ``codex exec --help``); instead its generic config override,
  ``-c model_reasoning_effort=<value>``, is the documented mechanism (this machine's
  own ``~/.codex/config.toml`` already sets it), forwarded verbatim for both the
  spawn and resume argv shapes. Codex validates the value server-side, not client-side
  (a bogus value is accepted by the CLI and only fails once the request reaches the
  model) — so an unsupported level (e.g. ``xhigh``/``max`` on a model that only
  understands low/medium/high) surfaces as a real turn-failure from Codex, not a
  silently-ignored flag.

Event stream (JSONL under ``--json``):
  ``{"type":"thread.started","thread_id":"<uuid>"}``  → SESSION_STARTED
  ``{"type":"turn.started"}``                         → (ignored)
  ``{"type":"item.completed","item":{...}}``          → ASSISTANT_TEXT / TOOL_USE / …
  ``{"type":"turn.completed","usage":{...}}``         → RESULT

Subscription-auth only: it runs the user's own logged-in ``codex``; no API key.

Worker posture: Horus deliberately keeps ``--worker codex`` on the safe
``AUTO_EDIT`` / ``--sandbox workspace-write`` preset. That sandbox disables the
network/socket access needed for git fetch/push/PR and local-server or headless-
browser verification. Git-integrated or browser-verified dispatch must add
``--posture full-auto``, which bypasses both approvals and the sandbox.
"""

from __future__ import annotations

import json
from pathlib import Path

from horus import config
from horus.adapters.base import (
    AgentAdapter,
    AgentEvent,
    EventType,
    PermissionPosture,
    SpawnSpec,
)

# Normalized posture → codex exec sandbox/bypass flags (spawn only).
# ``exec resume`` does not accept ``--sandbox``; FULL_AUTO maps to the bypass flag
# for both paths (handled separately in build_command for resume).
_SANDBOX_FLAGS: dict[PermissionPosture, list[str]] = {
    PermissionPosture.PLAN: ["--sandbox", "read-only"],
    PermissionPosture.READ_ONLY: ["--sandbox", "read-only"],
    PermissionPosture.DEFAULT: [],   # workspace-write + interactive approval (Codex default)
    PermissionPosture.AUTO_EDIT: ["--sandbox", "workspace-write"],
    PermissionPosture.FULL_AUTO: ["--dangerously-bypass-approvals-and-sandbox"],
}


class CodexAdapter(AgentAdapter):
    name = "codex"

    def __init__(
        self,
        *,
        executable: str = "codex",
        codex_homes: dict[str, str] | None = None,
    ) -> None:
        """``codex_homes`` maps an account alias to its ``CODEX_HOME`` dir for
        multi-account isolation. Defaults to the configured map in
        ``~/.horus/accounts.toml``; unmapped accounts use the ambient login."""
        self.executable = executable
        self.codex_homes = codex_homes if codex_homes is not None else config.load_account_codex_homes()

    # --- contract -------------------------------------------------------------

    def permission_flags(self, posture: PermissionPosture) -> list[str]:
        """Sandbox/approval flags for ``codex exec`` (new session only)."""
        return list(_SANDBOX_FLAGS[posture])

    def build_command(self, spec: SpawnSpec, *, resume_id: str | None = None) -> list[str]:
        if resume_id:
            # codex exec resume [OPTIONS] [SESSION_ID] [PROMPT]
            # Note: exec resume does not accept --sandbox; only the full bypass is
            # available as a permission override, so other postures are inherited
            # from the original session.
            argv = [self.executable, "exec", "resume", "--json"]
            if spec.model:
                argv += ["-m", spec.model]
            if spec.effort:
                argv += ["-c", f"model_reasoning_effort={spec.effort}"]
            if spec.posture is PermissionPosture.FULL_AUTO:
                argv.append("--dangerously-bypass-approvals-and-sandbox")
            argv += list(spec.extra_args)
            argv.append(resume_id)
            if spec.prompt:
                argv.append(spec.prompt)
        else:
            # codex exec [OPTIONS] [PROMPT]
            argv = [self.executable, "exec", "--json"]
            if spec.model:
                argv += ["-m", spec.model]
            if spec.effort:
                argv += ["-c", f"model_reasoning_effort={spec.effort}"]
            argv += self.permission_flags(spec.posture)
            argv += list(spec.extra_args)
            argv.append(spec.prompt)
        return argv

    def build_env(self, spec: SpawnSpec) -> dict[str, str]:
        env: dict[str, str] = {}
        home = self.codex_homes.get(spec.account) if spec.account else None
        if home:
            env["CODEX_HOME"] = str(Path(home))
        # Deterministic worker signal for the PreToolUse usage guard's emergency
        # state-save (the linked-worktree check is the fallback).
        if spec.run_session_id:
            env["HORUS_RUN_SESSION_ID"] = spec.run_session_id
        if spec.worker:
            env["HORUS_RUN_WORKER"] = "1"
        return env

    def interactive_command(self, spec: SpawnSpec, *, session_id: str) -> list[str]:
        """Argv for an *attended* interactive Codex session (no ``exec``).

        ``session_id`` is Horus's internal tracking id; Codex does not support
        pre-assigning a thread id, so this argument is accepted (satisfying the
        pty_host contract) but not forwarded to the CLI. The session is tracked
        in the PTY terminal by Horus's own ``term_id``.
        A non-empty ``spec.prompt`` seeds the TUI as the positional initial prompt.
        """
        argv = [self.executable]
        if spec.model:
            argv += ["-m", spec.model]
        # Interactive mode surfaces approval prompts in the TUI; no sandbox flag needed.
        # FULL_AUTO is the only posture worth forcing headlessly (skips the interactive prompt).
        if spec.posture is PermissionPosture.FULL_AUTO:
            argv.append("--dangerously-bypass-approvals-and-sandbox")
        if spec.prompt:
            argv.append(spec.prompt)
        return argv

    def parse_event(self, line: str) -> list[AgentEvent]:
        line = line.strip()
        if not line:
            return []
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            return [AgentEvent(EventType.RAW, text=line)]

        kind = obj.get("type")
        if kind == "thread.started":
            return [AgentEvent(EventType.SESSION_STARTED, session_id=obj.get("thread_id"), raw=obj)]
        if kind == "item.completed":
            return self._item_events(obj)
        if kind == "turn.completed":
            return [AgentEvent(EventType.RESULT, raw=obj)]
        # turn.started, tool_call.delta, and other stream events are skipped.
        return []

    @staticmethod
    def _item_events(obj: dict) -> list[AgentEvent]:
        item = obj.get("item") or {}
        itype = item.get("type")
        if itype == "agent_message":
            return [AgentEvent(EventType.ASSISTANT_TEXT, text=item.get("text"), raw=item)]
        if itype == "tool_call":
            name = item.get("name") or item.get("function")
            return [AgentEvent(EventType.TOOL_USE, tool=name, raw=item)]
        if itype == "tool_output":
            return [AgentEvent(EventType.TOOL_RESULT, raw=item)]
        if itype == "approval_request":
            tool = item.get("tool") or item.get("command")
            return [AgentEvent(EventType.PERMISSION_REQUEST, tool=tool, raw=item)]
        return []
