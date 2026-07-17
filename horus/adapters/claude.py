"""Claude Code adapter — drives the official ``claude`` CLI against the contract.

Thin by design: only the four pure methods are Claude-specific; spawn/resume,
subprocess streaming, and session tracking come from :class:`AgentAdapter`.

Built against Claude Code 2.1.191's headless surface:
- spawn:  ``claude -p <prompt> --output-format stream-json --verbose``
- resume: ``... --resume <session_id>`` (the id is echoed in the ``system/init`` event)
- per-account isolation: ``CLAUDE_CONFIG_DIR`` (a distinct config/home dir per account)
- reasoning effort: ``--effort <level>`` (probed live on 2.1.206 — Claude Code's own CLI
  help documents exactly ``low|medium|high|xhigh|max``, the same enum Horus exposes via
  ``horus run --effort``; forwarded verbatim, no translation needed)

Subscription-auth only: it runs the user's own logged-in ``claude``; no API key.
"""

from __future__ import annotations

import json
import re
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

# The bare family aliases Claude Code's `--model` accepts (probed live,
# Claude Code 2.1.206). Single-sourced here: the calibration-key rejection
# regex below and `KNOWN_MODELS` (the TUI's per-account model choice) both
# derive from this same tuple instead of duplicating the family list.
_MODEL_FAMILIES: tuple[str, ...] = ("opus", "sonnet", "haiku", "fable")

# Horus's canonical calibration key uses a dotted family-major[.minor] shape
# (`sonnet-5`, `haiku-4.5` — see `horus/datums.py`'s `ALIAS_TO_CANONICAL`) that
# names WHICH model ran for calibration history. It is never itself a valid
# Claude Code `--model` selector: the CLI accepts only a bare family alias
# (`sonnet`) or a full dash-separated selector (`claude-sonnet-5`,
# `claude-haiku-4-5`). Passing the calibration key straight through failed in
# five seconds with no delivery (2026-07-16, session 5e704890-...) because it
# looked exact but wasn't executable.
_CALIBRATION_ONLY_MODEL_RE = re.compile(rf"^(?:{'|'.join(_MODEL_FAMILIES)})-\d+(?:\.\d+)?$")


def _provider_selector_for(calibration_key: str) -> str:
    """Best-effort full-selector spelling for a calibration-only key, for the
    correction message only — never used to substitute a selector at launch."""
    family, _, version = calibration_key.partition("-")
    return f"claude-{family}-{version.replace('.', '-')}"


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
    KNOWN_MODELS = _MODEL_FAMILIES

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
        if spec.effort:
            argv += ["--effort", spec.effort]
        argv += self.permission_flags(spec.posture)
        if spec.allowed_tools:
            argv += ["--allowedTools", ",".join(spec.allowed_tools)]
        if spec.disallowed_tools:
            argv += ["--disallowedTools", ",".join(spec.disallowed_tools)]
        argv += list(spec.extra_args)
        return argv

    def build_env(self, spec: SpawnSpec) -> dict[str, str]:
        env: dict[str, str] = {}
        cfg = self.config_dirs.get(spec.account) if spec.account else None
        if cfg:
            env["CLAUDE_CONFIG_DIR"] = str(Path(cfg))
        # Deterministic worker signal for the PreToolUse usage guard's emergency
        # state-save (the linked-worktree check is the fallback).
        if spec.run_session_id:
            env["HORUS_RUN_SESSION_ID"] = spec.run_session_id
        if spec.worker:
            env["HORUS_RUN_WORKER"] = "1"
        return env

    def validate_model(self, model: str | None) -> str | None:
        """Reject a known calibration-only label before it reaches ``claude``.

        Static and local — matches the dotted family-major[.minor] shape of a
        Horus calibration key, never queries the provider. A bare alias
        (``sonnet``) or a full selector (``claude-sonnet-5``) both pass
        through unchanged; only the calibration-key spelling is rejected.
        """
        if model and _CALIBRATION_ONLY_MODEL_RE.match(model):
            return (
                f"{model!r} is a Horus calibration key, not a Claude Code --model "
                f"selector. Pass a bare alias (e.g. {model.split('-')[0]!r}) or the "
                f"full provider selector (e.g. {_provider_selector_for(model)!r}) instead."
            )
        return None

    def interactive_command(self, spec: SpawnSpec, *, session_id: str) -> list[str]:
        """Argv for an *attended* TUI session (no ``-p``): the user types in it.

        ``--session-id`` is pre-assigned so we can track the session before any
        output is parsed (interactive runs don't stream stream-json back to us).
        A non-empty ``spec.prompt`` is passed as Claude's positional initial prompt
        (``claude [options] [prompt]``) to seed the session — used to inject a
        project's continuity/resume prompt; empty means a fresh, unseeded session.
        """
        argv = [self.executable, "--session-id", session_id]
        if spec.model:
            argv += ["--model", spec.model]
        if spec.effort:
            argv += ["--effort", spec.effort]
        if spec.posture is not PermissionPosture.DEFAULT:
            argv += self.permission_flags(spec.posture)
        argv += list(spec.extra_args)
        if spec.prompt:
            argv.append(spec.prompt)  # positional initial prompt for the TUI
        return argv

    # --- multi-account identity ----------------------------------------------

    def verify_account(self, account: str | None) -> IdentityCheck:
        """Confirm the config dir for ``account`` is actually logged in as that account.

        Reads ``<CLAUDE_CONFIG_DIR>/.claude.json`` (or the ambient ``~/.claude.json``
        when the account has no mapped dir) and checks its email aliases back to the
        requested account. Never exposes the email beyond this result.

        Adoption (trust on first use): the account wizard maps alias→dir *before*
        the user signs in, and nothing else observes the login until a launch lands
        here — so a login in the account's own isolated dir whose email has no
        explicit alias yet IS this account's first login; persist email→alias
        instead of refusing a correctly-completed setup. A login already aliased to
        a *different* account still refuses (the real wrong-login case).
        """
        cfg = self.config_dirs.get(account) if account else None
        claude_json = Path(cfg) / ".claude.json" if cfg else claude_usage.config_path()
        email = claude_usage.current_account(claude_json)
        if account is None:
            ok = email is not None  # ambient: just confirm *someone* is logged in
        elif email is None:
            ok = False
        else:
            aliased = config.load_account_aliases().get(email)
            if aliased is None and cfg:
                config.set_account_alias(email, account)
                aliased = account
            ok = aliased == account
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
