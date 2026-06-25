"""Read-only Codex rollout usage signals.

Codex desktop/CLI records session events as JSONL rollouts under
``$CODEX_HOME/sessions``. The ``token_count`` events include the last request's
token usage, the model context window, and rate-limit percentages. Horus uses
that as an opportunistic closure signal: when a project session is near its
context or rate-limit budget, suggest running the closure ritual before the
thread becomes awkward to resume.

This is intentionally a read-only best-effort inspector. Missing Codex state,
schema drift, malformed lines, or absent token events simply produce no report.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

from horus.continuity import Finding


class UsageReport(NamedTuple):
    rollout: Path
    timestamp: str
    context_tokens: int
    context_window: int
    context_percent: float
    primary_percent: float | None
    primary_resets_at: int | None
    secondary_percent: float | None
    secondary_resets_at: int | None


def codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def _rollouts(home: Path) -> list[Path]:
    sessions = home / "sessions"
    if not sessions.is_dir():
        return []
    files = [p for p in sessions.rglob("rollout-*.jsonl") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def _matches_project(payload: dict[str, Any], project_root: Path) -> bool:
    root = project_root.resolve()
    candidates = []
    cwd = payload.get("cwd")
    if isinstance(cwd, str):
        candidates.append(Path(cwd))
    roots = payload.get("workspace_roots")
    if isinstance(roots, list):
        candidates.extend(Path(p) for p in roots if isinstance(p, str))
    for candidate in candidates:
        try:
            if candidate.resolve() == root:
                return True
        except OSError:
            continue
    return False


def _timestamp_key(value: str) -> float:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    return dt.timestamp()


def _report_from_event(path: Path, event: dict[str, Any]) -> UsageReport | None:
    payload = event.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "token_count":
        return None
    info = payload.get("info")
    if not isinstance(info, dict):
        return None
    last = info.get("last_token_usage")
    if not isinstance(last, dict):
        return None
    tokens = last.get("total_tokens")
    window = info.get("model_context_window")
    if not isinstance(tokens, int) or not isinstance(window, int) or window <= 0:
        return None

    rate_limits = payload.get("rate_limits")
    primary_percent = secondary_percent = None
    primary_resets_at = secondary_resets_at = None
    if isinstance(rate_limits, dict):
        primary = rate_limits.get("primary")
        if isinstance(primary, dict):
            pct = primary.get("used_percent")
            primary_percent = float(pct) if isinstance(pct, int | float) else None
            reset = primary.get("resets_at")
            primary_resets_at = reset if isinstance(reset, int) else None
        secondary = rate_limits.get("secondary")
        if isinstance(secondary, dict):
            pct = secondary.get("used_percent")
            secondary_percent = float(pct) if isinstance(pct, int | float) else None
            reset = secondary.get("resets_at")
            secondary_resets_at = reset if isinstance(reset, int) else None

    return UsageReport(
        rollout=path,
        timestamp=str(event.get("timestamp", "")),
        context_tokens=tokens,
        context_window=window,
        context_percent=round(tokens / window * 100, 1),
        primary_percent=primary_percent,
        primary_resets_at=primary_resets_at,
        secondary_percent=secondary_percent,
        secondary_resets_at=secondary_resets_at,
    )


def latest_usage(project_root: Path, *, home: Path | None = None) -> UsageReport | None:
    """Latest Codex token_count event for ``project_root`` across local rollouts."""
    best: UsageReport | None = None
    best_ts = -1.0
    for path in _rollouts(home or codex_home()):
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
                current_project = isinstance(payload, dict) and _matches_project(payload, project_root)
                continue
            if not current_project:
                continue
            report = _report_from_event(path, event)
            if report is None:
                continue
            ts = _timestamp_key(report.timestamp)
            if ts >= best_ts:
                best = report
                best_ts = ts
    return best


def _fmt_reset(ts: int | None) -> str:
    if ts is None:
        return "unknown reset"
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")


def usage_findings(project_root: Path, *, threshold: float = 90.0, home: Path | None = None) -> list[Finding]:
    report = latest_usage(project_root, home=home)
    if report is None:
        return [Finding("ok", "no Codex usage signal found for this project")]

    parts = [f"Codex context {report.context_percent:.1f}% ({report.context_tokens}/{report.context_window} tokens)"]
    over = report.context_percent >= threshold
    if report.primary_percent is not None:
        parts.append(f"5h limit {report.primary_percent:.0f}% (resets {_fmt_reset(report.primary_resets_at)})")
        over = over or report.primary_percent >= threshold
    if report.secondary_percent is not None:
        parts.append(f"weekly limit {report.secondary_percent:.0f}% (resets {_fmt_reset(report.secondary_resets_at)})")
        over = over or report.secondary_percent >= threshold

    level = "warn" if over else "ok"
    suffix = "; run the closure ritual before starting another large turn" if over else ""
    return [Finding(level, "; ".join(parts) + suffix)]
