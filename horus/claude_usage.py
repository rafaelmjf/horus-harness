"""Read-only Claude Code subscription usage signals.

Claude Code does not expose subscription rate-limit usage to hooks or transcripts,
but its `/usage` panel reads it from the authenticated endpoint
``GET https://api.anthropic.com/api/oauth/usage``. Horus queries the same endpoint
with the OAuth token Claude Code already stores in ``~/.claude/.credentials.json``,
so it can use the 5-hour / weekly limits as a closure signal — the Claude-side peer
of the Codex rollout telemetry in ``codex_usage``.

Best-effort and read-only: a missing/expired token, an offline machine, or schema
drift simply produces no usable report (no exception escapes).
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple

from horus.continuity import Finding

USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
# Beta header Claude Code sends for OAuth-scoped endpoints (found in the CLI binary).
_OAUTH_BETA = "oauth-2025-04-20"


class UsageReport(NamedTuple):
    five_hour_percent: float | None
    five_hour_resets_at: str | None
    seven_day_percent: float | None
    seven_day_resets_at: str | None


def credentials_path() -> Path:
    return Path.home() / ".claude" / ".credentials.json"


def _oauth_token(path: Path | None = None) -> str | None:
    """The Claude Code OAuth access token, or None if absent/expired."""
    cred = path or credentials_path()
    try:
        data = json.loads(cred.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    oauth = data.get("claudeAiOauth")
    if not isinstance(oauth, dict):
        return None
    token = oauth.get("accessToken")
    if not isinstance(token, str) or not token:
        return None
    expires_at = oauth.get("expiresAt")
    if isinstance(expires_at, int | float):
        # expiresAt is epoch milliseconds; skip a call we know will 401.
        if expires_at / 1000.0 <= time.time():
            return None
    return token


def fetch_usage(*, token: str | None = None, timeout: float = 8.0, cred_path: Path | None = None) -> dict[str, Any] | None:
    """GET the OAuth usage payload. None on any auth/network/parse failure."""
    tok = token or _oauth_token(cred_path)
    if not tok:
        return None
    req = urllib.request.Request(
        USAGE_URL,
        headers={
            "Authorization": f"Bearer {tok}",
            "anthropic-beta": _OAUTH_BETA,
            "anthropic-version": "2023-06-01",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (fixed https host)
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _window(payload: dict[str, Any], key: str) -> tuple[float | None, str | None]:
    block = payload.get(key)
    if not isinstance(block, dict):
        return None, None
    pct = block.get("utilization")
    resets = block.get("resets_at")
    return (
        float(pct) if isinstance(pct, int | float) else None,
        resets if isinstance(resets, str) else None,
    )


def latest_usage(*, token: str | None = None, cred_path: Path | None = None, timeout: float = 8.0) -> UsageReport | None:
    payload = fetch_usage(token=token, cred_path=cred_path, timeout=timeout)
    if payload is None:
        return None
    five_pct, five_reset = _window(payload, "five_hour")
    week_pct, week_reset = _window(payload, "seven_day")
    if five_pct is None and week_pct is None:
        return None
    return UsageReport(five_pct, five_reset, week_pct, week_reset)


def _fmt_reset(value: str | None) -> str:
    if not value:
        return "unknown reset"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return dt.astimezone().strftime("%Y-%m-%d %H:%M")


def usage_findings(*, threshold: float = 90.0, report: UsageReport | None = None, **kwargs: Any) -> list[Finding]:
    """Findings for Claude subscription usage, parallel to ``codex_usage.usage_findings``."""
    report = report if report is not None else latest_usage(**kwargs)
    if report is None:
        return [Finding("ok", "no Claude usage signal available (token missing/expired or offline)")]

    parts: list[str] = []
    over = False
    if report.five_hour_percent is not None:
        parts.append(f"5h limit {report.five_hour_percent:.0f}% (resets {_fmt_reset(report.five_hour_resets_at)})")
        over = over or report.five_hour_percent >= threshold
    if report.seven_day_percent is not None:
        parts.append(f"weekly limit {report.seven_day_percent:.0f}% (resets {_fmt_reset(report.seven_day_resets_at)})")
        over = over or report.seven_day_percent >= threshold

    if not parts:
        return [Finding("ok", "no Claude usage signal available")]
    level = "warn" if over else "ok"
    suffix = "; run the closure ritual before continuing this session" if over else ""
    return [Finding(level, "Claude " + "; ".join(parts) + suffix)]


def is_over_threshold(threshold: float, report: UsageReport | None) -> bool:
    if report is None:
        return False
    return any(
        p is not None and p >= threshold
        for p in (report.five_hour_percent, report.seven_day_percent)
    )
