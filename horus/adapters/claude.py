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

import json
from dataclasses import dataclass
from pathlib import Path

from horus import claude_usage, config
from horus.adapters.base import (
    AgentAdapter,
    AgentEvent,
    AgentRun,
    EventType,
    PermissionPosture,
    SpawnSpec,
)


class AccountMismatch(RuntimeError):
    """Raised when a per-account config dir's login doesn't match the requested account."""


@dataclass
class IdentityCheck:
    account: str | None
    config_dir: str | None
    detected_email: str | None
    ok: bool

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
        multi-account isolation. Defaults to the configured map in
        ``~/.horus/accounts.toml``; unmapped accounts use the ambient login."""
        self.executable = executable
        self.config_dirs = config_dirs if config_dirs is not None else config.load_account_config_dirs()

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

    def interactive_command(self, spec: SpawnSpec, *, session_id: str) -> list[str]:
        """Argv for an *attended* TUI session (no ``-p``): the user types in it.

        ``--session-id`` is pre-assigned so we can track the session before any
        output is parsed (interactive runs don't stream stream-json back to us).
        """
        argv = [self.executable, "--session-id", session_id]
        if spec.model:
            argv += ["--model", spec.model]
        if spec.posture is not PermissionPosture.DEFAULT:
            argv += self.permission_flags(spec.posture)
        argv += list(spec.extra_args)
        return argv

    # --- multi-account identity ----------------------------------------------

    def verify_account(self, account: str | None) -> IdentityCheck:
        """Confirm the config dir for ``account`` is actually logged in as that account.

        Reads ``<CLAUDE_CONFIG_DIR>/.claude.json`` (or the ambient ``~/.claude.json``
        when the account has no mapped dir) and checks its email aliases back to the
        requested account. Read-only; never exposes the email beyond this result.
        """
        cfg = self.config_dirs.get(account) if account else None
        claude_json = Path(cfg) / ".claude.json" if cfg else claude_usage.config_path()
        email = claude_usage.current_account(claude_json)
        if account is None:
            ok = email is not None  # ambient: just confirm *someone* is logged in
        else:
            ok = email is not None and config.alias_for(email) == account
        return IdentityCheck(account=account, config_dir=str(cfg) if cfg else None, detected_email=email, ok=ok)

    def _launch(self, spec: SpawnSpec, *, resume_id: str | None) -> AgentRun:
        # Guard only when explicit per-account isolation is configured (a mapped dir).
        # Ambient single-account runs are unaffected.
        if spec.account and spec.account in self.config_dirs:
            check = self.verify_account(spec.account)
            if not check.ok:
                raise AccountMismatch(
                    f"account {spec.account!r} maps to config dir {check.config_dir!r}, but its "
                    f"login is {check.detected_email or 'absent'} "
                    f"(alias {config.alias_for(check.detected_email)!r}) — refusing to spawn"
                )
        return super()._launch(spec, resume_id=resume_id)

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
