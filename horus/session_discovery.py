"""Read-only discovery of coding-agent sessions for a project.

Claude Code and Codex both write local transcripts of every session regardless of
whether Horus launched them — Claude Code as JSONL files under
``~/.claude/projects/<slug>/<uuid>.jsonl`` and Codex as JSONL rollouts under
``$CODEX_HOME/sessions/**/rollout-*.jsonl``. This module scans those transcripts to
answer "what sessions exist for this project" without Horus needing to have started
them — the session-visibility path that replaced the retired Control cockpit.

Privacy rule: Horus only ever surfaces counts and timestamps here, never transcript
content. ``SessionInfo`` intentionally has no field for prompts or message text —
do not add one.

This module reuses the file-location and project-matching conventions already
established in ``claude_usage``, ``codex_usage``, ``cache_status``, and ``overhead``:
Claude events are matched to a project via their ``cwd`` field, Codex rollouts via
``turn_context``/``session_meta`` payload ``cwd``/``workspace_roots``. Tolerant of
malformed lines, missing directories, and permission errors — never raises on garbage.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from horus import codex_usage
from horus.overhead import _event_matches_project, _matches_project


@dataclass(frozen=True)
class SessionInfo:
    agent: str  # "claude" | "codex"
    session_id: str
    started_at: str | None
    last_activity: str | None
    message_count: int
    source_path: Path


def _claude_home(claude_dir: Path | None) -> Path:
    if claude_dir is not None:
        return claude_dir
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(env) if env else Path.home() / ".claude"


def _claude_jsonl_files(claude_dir: Path | None) -> list[Path]:
    base = _claude_home(claude_dir)
    projects = base / "projects"
    if not projects.is_dir():
        return []
    try:
        return sorted(p for p in projects.rglob("*.jsonl") if p.is_file())
    except OSError:
        return []


def _claude_event_timestamp(event: dict[str, Any]) -> str | None:
    value = event.get("timestamp")
    return value if isinstance(value, str) and value else None


def discover_claude_sessions(project_root: Path, claude_dir: Path | None = None) -> list[SessionInfo]:
    """Sessions found in Claude Code transcripts touching ``project_root``.

    Each ``*.jsonl`` file under ``~/.claude/projects/**`` is one session; the
    filename stem is the session id (Claude Code's own uuid). Lines whose ``cwd``
    does not resolve to ``project_root`` are ignored, so a transcript that visited
    multiple directories only contributes the lines for this project.
    """
    root = project_root.resolve()
    sessions: list[SessionInfo] = []
    for path in _claude_jsonl_files(claude_dir):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue

        message_count = 0
        started_at: str | None = None
        last_activity: str | None = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            if not _event_matches_project(event, root):
                continue
            if event.get("type") not in ("user", "assistant"):
                continue
            message_count += 1
            ts = _claude_event_timestamp(event)
            if ts is not None:
                if started_at is None or ts < started_at:
                    started_at = ts
                if last_activity is None or ts > last_activity:
                    last_activity = ts

        if message_count == 0:
            continue
        sessions.append(
            SessionInfo(
                agent="claude",
                session_id=path.stem,
                started_at=started_at,
                last_activity=last_activity,
                message_count=message_count,
                source_path=path,
            )
        )
    return sessions


def _codex_rollouts(home: Path) -> list[Path]:
    sessions = home / "sessions"
    if not sessions.is_dir():
        return []
    try:
        return [p for p in sessions.rglob("rollout-*.jsonl") if p.is_file()]
    except OSError:
        return []


def _codex_session_id(path: Path, meta_payload: dict[str, Any] | None) -> str:
    if isinstance(meta_payload, dict):
        for key in ("session_id", "id"):
            value = meta_payload.get(key)
            if isinstance(value, str) and value:
                return value
    return path.stem


def _codex_event_timestamp(event: dict[str, Any]) -> str | None:
    value = event.get("timestamp")
    return value if isinstance(value, str) and value else None


def discover_codex_sessions(project_root: Path, codex_home: Path | None = None) -> list[SessionInfo]:
    """Sessions found in Codex rollouts touching ``project_root``.

    Each ``rollout-*.jsonl`` file under ``$CODEX_HOME/sessions/**`` is one session.
    A rollout is attributed to this project when any ``session_meta`` or
    ``turn_context`` payload's ``cwd``/``workspace_roots`` resolves to
    ``project_root`` (same matching rule as ``codex_usage``/``overhead``).
    """
    root = project_root.resolve()
    home = codex_home or codex_usage.codex_home()
    sessions: list[SessionInfo] = []
    for path in _codex_rollouts(home):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue

        matches_project = False
        message_count = 0
        started_at: str | None = None
        last_activity: str | None = None
        meta_payload: dict[str, Any] | None = None

        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue

            event_type = event.get("type")
            payload = event.get("payload")

            if event_type == "session_meta":
                if isinstance(payload, dict):
                    meta_payload = payload
                    if _matches_project(payload, root):
                        matches_project = True
                continue

            if event_type == "turn_context":
                if isinstance(payload, dict) and _matches_project(payload, root):
                    matches_project = True
                continue

            if event_type != "event_msg" or not isinstance(payload, dict):
                continue
            if payload.get("type") not in ("user_message", "agent_message"):
                continue

            message_count += 1
            ts = _codex_event_timestamp(event)
            if ts is not None:
                if started_at is None or ts < started_at:
                    started_at = ts
                if last_activity is None or ts > last_activity:
                    last_activity = ts

        if not matches_project or message_count == 0:
            continue
        sessions.append(
            SessionInfo(
                agent="codex",
                session_id=_codex_session_id(path, meta_payload),
                started_at=started_at,
                last_activity=last_activity,
                message_count=message_count,
                source_path=path,
            )
        )
    return sessions


def discover_sessions(
    project_root: Path,
    *,
    claude_dir: Path | None = None,
    codex_home: Path | None = None,
) -> list[SessionInfo]:
    """All known sessions for ``project_root`` across both agents, newest first.

    Sessions with no recorded ``last_activity`` (e.g. a transcript with messages
    but no parseable timestamps) sort last.
    """
    sessions = discover_claude_sessions(project_root, claude_dir) + discover_codex_sessions(
        project_root, codex_home
    )
    return sorted(sessions, key=lambda s: s.last_activity or "", reverse=True)
