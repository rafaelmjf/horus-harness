"""Prompt-cache freshness estimates from local native-agent telemetry.

The providers own the real cache state; Horus only sees local request logs after
a native CLI turn completes. This module therefore reports a conservative
freshness estimate: how long it has been since the last project turn, whether
that turn showed cached/cache-write token fields, and when a 60-minute cache
window would be considered stale.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from horus import codex_usage, overhead

LIKELY_COLD_AFTER_SECONDS = 5 * 60
EXPIRES_AFTER_SECONDS = 60 * 60


@dataclass(frozen=True)
class CacheStatus:
    agent: str
    timestamp: datetime
    source: Path
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    total_tokens: int = 0

    @property
    def cache_tokens(self) -> int:
        return self.cached_input_tokens + self.cache_creation_input_tokens + self.cache_read_input_tokens

    @property
    def had_cache_activity(self) -> bool:
        return self.cache_tokens > 0

    def age_seconds(self, *, now: datetime | None = None) -> float:
        current = now or datetime.now(timezone.utc)
        return max(0.0, (current - self.timestamp).total_seconds())

    def state(self, *, now: datetime | None = None) -> str:
        age = self.age_seconds(now=now)
        if age >= EXPIRES_AFTER_SECONDS:
            return "expired"
        if age >= LIKELY_COLD_AFTER_SECONDS:
            return "cold-risk"
        return "warm"

    def seconds_until_expiry(self, *, now: datetime | None = None) -> float:
        return max(0.0, EXPIRES_AFTER_SECONDS - self.age_seconds(now=now))


def project_cache_status(project_root: Path) -> list[CacheStatus]:
    """Return latest cache-freshness signals for Claude and Codex, newest first."""
    root = project_root.resolve()
    statuses = [
        status
        for status in (
            latest_codex_cache_status(root),
            latest_claude_cache_status(root),
        )
        if status is not None
    ]
    return sorted(statuses, key=lambda s: s.timestamp, reverse=True)


def latest_codex_cache_status(project_root: Path, *, home: Path | None = None) -> CacheStatus | None:
    best: CacheStatus | None = None
    best_ts = -1.0
    for path in codex_usage._rollouts(home or codex_usage.codex_home()):  # noqa: SLF001 - local telemetry helper
        current_project = False
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            if event.get("type") == "turn_context":
                payload = event.get("payload")
                current_project = isinstance(payload, dict) and codex_usage._matches_project(  # noqa: SLF001
                    payload, project_root
                )
                continue
            if not current_project:
                continue
            status = _codex_status_from_event(path, event)
            if status is None:
                continue
            ts = status.timestamp.timestamp()
            if ts >= best_ts:
                best = status
                best_ts = ts
    return best


def latest_claude_cache_status(project_root: Path, *, home: Path | None = None) -> CacheStatus | None:
    best: CacheStatus | None = None
    best_ts = -1.0
    for path in _claude_jsonl_files(home):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        fallback_ts = _mtime_datetime(path)
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict) or not overhead._event_matches_project(event, project_root):  # noqa: SLF001
                continue
            usage = _usage_from_claude_event(event)
            if usage is None:
                continue
            timestamp = _event_datetime(event) or fallback_ts
            status = CacheStatus(agent="claude", timestamp=timestamp, source=path, **usage)
            ts = status.timestamp.timestamp()
            if ts >= best_ts:
                best = status
                best_ts = ts
    return best


def _codex_status_from_event(path: Path, event: dict[str, Any]) -> CacheStatus | None:
    payload = event.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "token_count":
        return None
    info = payload.get("info")
    if not isinstance(info, dict):
        return None
    usage = info.get("last_token_usage")
    if not isinstance(usage, dict):
        return None
    timestamp = _event_datetime(event) or _mtime_datetime(path)
    return CacheStatus(agent="codex", timestamp=timestamp, source=path, **_usage_fields(usage))


def _usage_from_claude_event(event: dict[str, Any]) -> dict[str, int] | None:
    message = event.get("message")
    if not isinstance(message, dict):
        return None
    usage = message.get("usage")
    return _usage_fields(usage) if isinstance(usage, dict) else None


def _usage_fields(data: dict[str, Any]) -> dict[str, int]:
    input_tokens = _int(data.get("input_tokens"))
    cached_input_tokens = _int(data.get("cached_input_tokens"))
    cache_creation_input_tokens = _int(data.get("cache_creation_input_tokens"))
    cache_read_input_tokens = _int(data.get("cache_read_input_tokens"))
    total_tokens = _int(data.get("total_tokens"))
    if total_tokens == 0:
        total_tokens = (
            input_tokens
            + cached_input_tokens
            + cache_creation_input_tokens
            + cache_read_input_tokens
            + _int(data.get("output_tokens"))
            + _int(data.get("reasoning_output_tokens"))
        )
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "cache_creation_input_tokens": cache_creation_input_tokens,
        "cache_read_input_tokens": cache_read_input_tokens,
        "total_tokens": total_tokens,
    }


def _claude_jsonl_files(home: Path | None) -> list[Path]:
    base = home or Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
    projects = base / "projects"
    if not projects.is_dir():
        return []
    return sorted(p for p in projects.rglob("*.jsonl") if p.is_file())


def _event_datetime(event: dict[str, Any]) -> datetime | None:
    for key in ("timestamp", "createdAt", "created_at"):
        value = event.get(key)
        if isinstance(value, str):
            parsed = _parse_datetime(value)
            if parsed is not None:
                return parsed
        if isinstance(value, int | float):
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
    return None


def _parse_datetime(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _mtime_datetime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def _int(value: Any) -> int:
    return value if isinstance(value, int) and value > 0 else 0
