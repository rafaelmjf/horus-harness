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
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from horus import codex_usage, config
from horus.adapters.base import (
    AgentRun,
    AgentAdapter,
    AgentEvent,
    EventType,
    PermissionPosture,
    SpawnSpec,
)
from horus.adapters.claude import AccountMismatch, IdentityCheck

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


def _rollout_meta(path: Path) -> dict | None:
    """The ``session_meta`` payload from a rollout file's first line, or ``None``.

    Only the first line is read: these files grow to megabytes, and the header is
    always line one (verified against codex 0.146.0 rollouts). Any unreadable or
    unexpected file is skipped rather than raising — a half-written rollout from a
    session starting right now is normal, not an error.
    """
    try:
        with path.open(encoding="utf-8") as handle:
            first = handle.readline()
    except OSError:
        return None
    try:
        record = json.loads(first)
    except json.JSONDecodeError:
        return None
    if not isinstance(record, dict) or record.get("type") != "session_meta":
        return None
    payload = record.get("payload")
    return payload if isinstance(payload, dict) else None


def _parse_iso(value: object) -> datetime | None:
    """Parse a rollout timestamp into an aware UTC datetime, or ``None``.

    Rollout headers carry a ``Z``-suffixed UTC stamp, which ``fromisoformat``
    only accepts natively from 3.11; normalising it keeps the comparison honest
    against a naive local time, which would otherwise be off by the UTC offset
    (observed: a header at 21:07Z inside a file named for 23-07 local).
    """
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class CodexAdapter(AgentAdapter):
    name = "codex"
    identity_label = "account id"
    # Codex mints its own thread id and writes it to a rollout file; it cannot be
    # pre-assigned, so ``interactive_command`` drops the id it is handed and the
    # real one is recovered afterwards by :func:`recover_interactive_thread_id`.
    assigns_interactive_thread_id = False
    # The GPT-5.6 family variants + the retained prior generation Horus tracks
    # today (mirrors `horus/datums.py`'s `PRIORS_SEED` roster). Edit alongside
    # that seed as the fleet's model roster grows — this is the TUI's per-
    # account model choice, not a routing table.
    KNOWN_MODELS = ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5")

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

    def interactive_command(
        self, spec: SpawnSpec, *, session_id: str, resume_id: str | None = None,
    ) -> list[str]:
        """Argv for an *attended* interactive Codex session (no ``exec``).

        ``session_id`` is Horus's internal tracking id; Codex does not support
        pre-assigning a thread id, so this argument is accepted (satisfying the
        pty_host contract) but not forwarded to the CLI. The session is tracked
        in the PTY terminal by Horus's own ``term_id``.
        A non-empty ``spec.prompt`` seeds the TUI as the positional initial prompt.

        ``resume_id`` is different: it is Codex's OWN thread id, which it will
        accept, so unlike ``session_id`` it is forwarded — as the ``resume``
        subcommand (``codex resume [OPTIONS] [SESSION_ID] [PROMPT]``). This is the
        attended twin of ``codex exec resume`` on the headless path.
        """
        argv = [self.executable]
        if resume_id:
            argv.append("resume")
        if spec.model:
            argv += ["-m", spec.model]
        if spec.effort:
            argv += ["-c", f"model_reasoning_effort={spec.effort}"]
        # Interactive mode surfaces approval prompts in the TUI; no sandbox flag needed.
        # FULL_AUTO is the only posture worth forcing headlessly (skips the interactive prompt).
        if spec.posture is PermissionPosture.FULL_AUTO:
            argv.append("--dangerously-bypass-approvals-and-sandbox")
        # Positional order is fixed by `codex resume [OPTIONS] [SESSION_ID] [PROMPT]`,
        # so the id goes after the options and before any prompt.
        if resume_id:
            argv.append(resume_id)
        if spec.prompt:
            argv.append(spec.prompt)
        return argv

    def recover_interactive_thread_id(
        self,
        *,
        project: Path | str,
        account: str | None,
        started_at: datetime,
        window: timedelta = timedelta(minutes=5),
    ) -> str | None:
        """The thread id Codex minted for an interactive session, read back afterwards.

        Codex cannot be told its thread id (see ``assigns_interactive_thread_id``), so
        the id only exists once Codex has written its rollout file. That file is the
        only place it appears — it is not on stdout, and an attended TUI session streams
        nothing back to Horus anyway.

        Correlation uses the three fields the rollout's ``session_meta`` header carries,
        because none of them is sufficient alone:

        - ``cwd`` must equal the project (the same account runs many projects),
        - ``originator`` must be ``codex-tui`` (an ``exec`` run is a different session
          that Horus already tracks by other means),
        - the header timestamp must fall within ``window`` of the launch.

        Returns ``None`` — never a guess — when no single file matches. A wrong id is
        far worse than a missing one: restoring on it would reopen somebody else's
        conversation.
        """
        home = self.codex_homes.get(account) if account else None
        root = Path(home) if home else Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
        sessions = root / "sessions"
        if not sessions.is_dir():
            return None
        want_cwd = Path(project).resolve().as_posix()
        matches: list[str] = []
        for path in sessions.rglob("rollout-*.jsonl"):
            meta = _rollout_meta(path)
            if not meta:
                continue
            if meta.get("cwd") != want_cwd or meta.get("originator") != "codex-tui":
                continue
            stamp = _parse_iso(meta.get("timestamp"))
            if stamp is None or abs(stamp - started_at) > window:
                continue
            thread_id = meta.get("session_id") or meta.get("id")
            if isinstance(thread_id, str) and thread_id:
                matches.append(thread_id)
        # Ambiguity is a failure, not a coin flip: two sessions in the same project
        # within the window are indistinguishable from here.
        return matches[0] if len(matches) == 1 else None

    # --- multi-account identity ----------------------------------------------

    def verify_account(self, account: str | None) -> IdentityCheck:
        """Confirm the CODEX_HOME for ``account`` is logged in as that account.

        Codex's ``auth.json`` identifies a ChatGPT login by ``tokens.account_id``.
        As with Claude, the first login into an account's mapped isolated home adopts
        that identity; an identity already mapped to a different alias refuses.
        """
        home = self.codex_homes.get(account) if account else None
        account_id = codex_usage.current_account(Path(home) if home else None)
        if account is None:
            ok = account_id is not None
        elif account_id is None:
            ok = False
        else:
            aliased = config.load_account_aliases().get(account_id)
            if aliased is None and home:
                config.set_account_alias(account_id, account)
                aliased = account
            ok = aliased == account
        return IdentityCheck(
            account=account,
            config_dir=str(home) if home else None,
            detected_identity=account_id,
            ok=ok,
        )

    def _launch(self, spec: SpawnSpec, *, resume_id: str | None) -> AgentRun:
        # Guard only when explicit per-account isolation is configured (a mapped home).
        # Ambient single-account runs are unaffected.
        if spec.account and spec.account in self.codex_homes:
            check = self.verify_account(spec.account)
            if not check.ok:
                raise AccountMismatch(
                    f"account {spec.account!r} maps to CODEX_HOME {check.config_dir!r}, but its "
                    f"{self.identity_label} is {check.detected_identity or 'absent'} "
                    f"(alias {config.alias_for(check.detected_identity)!r}) — refusing to spawn"
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
