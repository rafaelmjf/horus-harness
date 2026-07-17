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
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

from horus.continuity import Finding


# A rate-limit window describes its own length, so nothing here hardcodes which
# window Codex happens to serve today. Anything at or under this many minutes is
# a "fast" window (the 5-hour lane, 300); anything longer is a "slow" one (the
# weekly lane, 10080). Observed 2026-07-17: Codex temporarily dropped the 5-hour
# limit, so `primary` carried window_minutes=10080 — the weekly lane — while
# `secondary` was null. Reading the label off the position instead of the data
# reported "5h limit 92% (resets 2026-07-23)": a 5-hour window that resets in six
# days. Whichever way that policy settles, the data still says what it is.
FAST_WINDOW_MAX_MINUTES = 720


class RateWindow(NamedTuple):
    """One rate-limit lane as Codex reported it, able to name itself."""

    percent: float | None
    resets_at: int | None
    window_minutes: int | None
    # What to call this lane when Codex did not declare its length (a rollout
    # predating `window_minutes`): the historical positional assumption, kept so
    # older rollouts read exactly as they always did.
    fallback_label: str = "rate"

    def label(self) -> str:
        """What this window actually is, derived from its own declared length."""
        minutes = self.window_minutes
        if minutes is None:
            return self.fallback_label
        if minutes >= 10080 and minutes % 10080 == 0:
            weeks = minutes // 10080
            return "weekly" if weeks == 1 else f"{weeks}-week"
        if minutes >= 1440 and minutes % 1440 == 0:
            days = minutes // 1440
            return "daily" if days == 1 else f"{days}-day"
        if minutes >= 60 and minutes % 60 == 0:
            return f"{minutes // 60}h"
        return f"{minutes}min"


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
    # Window lengths as Codex reported them (None when a rollout predates the
    # field, or on schema drift) — the input to `windows()` below.
    primary_window_minutes: int | None = None
    secondary_window_minutes: int | None = None

    def windows(self) -> tuple[RateWindow | None, RateWindow | None]:
        """This report's (fast, slow) lanes, classified by their own declared
        length rather than by which slot Codex happened to put them in.

        When a lane does not declare its length, fall back to the historical
        positional convention (primary=fast, secondary=slow) so an older rollout
        reads exactly as it did before.
        """
        primary = RateWindow(
            self.primary_percent, self.primary_resets_at, self.primary_window_minutes, "5h"
        ) if self.primary_percent is not None else None
        secondary = RateWindow(
            self.secondary_percent, self.secondary_resets_at, self.secondary_window_minutes, "weekly"
        ) if self.secondary_percent is not None else None

        present = [w for w in (primary, secondary) if w is not None]
        if not present:
            return None, None
        if any(w.window_minutes is None for w in present):
            return primary, secondary  # undeclared length -> positional, as before

        fast = min(present, key=lambda w: w.window_minutes)
        slow = max(present, key=lambda w: w.window_minutes)
        return (
            fast if fast.window_minutes <= FAST_WINDOW_MAX_MINUTES else None,
            slow if slow.window_minutes > FAST_WINDOW_MAX_MINUTES else None,
        )


def codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def current_account(home: Path | None = None) -> str | None:
    """Return the ``account_id`` from ``$CODEX_HOME/auth.json``, or ``None`` if absent.

    Reads ``tokens.account_id`` from the auth file (chatgpt auth mode). Best-effort:
    missing file, wrong schema, or any read error returns ``None``.
    """
    try:
        auth = (home or codex_home()) / "auth.json"
        data = json.loads(auth.read_text(encoding="utf-8"))
        return data.get("tokens", {}).get("account_id") or None
    except Exception:
        return None


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
    primary_minutes = secondary_minutes = None
    if isinstance(rate_limits, dict):
        primary = rate_limits.get("primary")
        if isinstance(primary, dict):
            pct = primary.get("used_percent")
            primary_percent = float(pct) if isinstance(pct, int | float) else None
            reset = primary.get("resets_at")
            primary_resets_at = reset if isinstance(reset, int) else None
            mins = primary.get("window_minutes")
            primary_minutes = mins if isinstance(mins, int) else None
        secondary = rate_limits.get("secondary")
        if isinstance(secondary, dict):
            pct = secondary.get("used_percent")
            secondary_percent = float(pct) if isinstance(pct, int | float) else None
            reset = secondary.get("resets_at")
            secondary_resets_at = reset if isinstance(reset, int) else None
            mins = secondary.get("window_minutes")
            secondary_minutes = mins if isinstance(mins, int) else None

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
        primary_window_minutes=primary_minutes,
        secondary_window_minutes=secondary_minutes,
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


def latest_account_usage(home: Path | None = None) -> UsageReport | None:
    """Most recent Codex rate-limit snapshot for the account at ``home``.

    Unlike :func:`latest_usage`, this ignores the project: the 5h/weekly rate
    limits are account-global, so the newest ``token_count`` event carrying
    ``rate_limits`` (across every local rollout) is the best snapshot of the
    account's limits. ``None`` until some rollout has reported rate limits.

    This is the *last observed* state, not a live poll — Codex exposes no usage
    API, so it is only as fresh as the most recent Codex activity.
    """
    best: UsageReport | None = None
    best_ts = -1.0
    for path in _rollouts(home or codex_home()):
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
            report = _report_from_event(path, event)
            if report is None:
                continue
            if report.primary_percent is None and report.secondary_percent is None:
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
    """Report project context and account-global rate limits.

    Context usage belongs to the project's latest rollout, while Codex rate limits
    belong to the account and therefore come from its newest rollout of any
    project.  A reset in the past cannot describe a rolling window's current
    capacity, so it is explicitly marked stale and never drives a warning.
    """
    report = latest_usage(project_root, home=home)
    account_report = latest_account_usage(home=home)
    if report is None and account_report is None:
        return [Finding("ok", "no Codex usage signal found for this project")]

    parts: list[str] = []
    over = False
    if report is not None:
        parts.append(f"Codex context {report.context_percent:.1f}% ({report.context_tokens}/{report.context_window} tokens)")
        over = report.context_percent >= threshold

    def add_limit(window: "RateWindow | None") -> None:
        nonlocal over
        if window is None or window.percent is None:
            return
        reset = _fmt_reset(window.resets_at)
        if window.resets_at is not None and window.resets_at <= time.time():
            parts.append(f"{window.label()} limit snapshot stale (reset {reset})")
            return
        parts.append(f"{window.label()} limit {window.percent:.0f}% (resets {reset})")
        over = over or window.percent >= threshold

    if account_report is not None:
        fast, slow = account_report.windows()
        add_limit(fast)
        add_limit(slow)

    level = "warn" if over else "ok"
    suffix = "; run the closure ritual before starting another large turn" if over else ""
    return [Finding(level, "; ".join(parts) + suffix)]
