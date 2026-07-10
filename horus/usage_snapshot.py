"""Cached usage snapshot — the shared substrate for the usage-limit survival kit.

A tiny, best-effort helper that returns the freshest usage percents for a target
agent+account — both the fast *5-hour window* and the slower *weekly window* (claude's
seven-day limit / codex's secondary window) — backed by a short-lived file cache under
``~/.horus/cache/``. Two callers depend on it:

- ``horus run`` preflight (warn/refuse before launching into a closing window);
- the ``PreToolUse`` usage guard (so a single long turn can't sail past the
  advisory threshold, and so an emergency state-save can fire near the cutoff).

Contract, always: **never raise, never block.** A missing credential, an offline
machine, a slow endpoint, or schema drift all resolve to ``None`` (or a snapshot
whose ``percent`` is ``None``) — the caller then proceeds silently. The cache makes
the ``PreToolUse`` hot path a file read; a negative result is cached too, so a
machine with no usable usage signal does not pay the fetch timeout on every tool
call.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from horus import config

# Cache freshness: a snapshot younger than this is served without a live fetch.
CACHE_TTL = 60.0
# Live-fetch ceiling — the PreToolUse guard must stay fast, so cap the network wait.
FETCH_TIMEOUT = 5.0

# Threshold bands shared by the survival-kit callers (single source of truth).
PREFLIGHT_CLOSING = 50.0  # `horus run`: closing-window notice (surface percent + reset)
PREFLIGHT_WARN = 80.0     # `horus run`: warn, continue
PREFLIGHT_REFUSE = 95.0   # `horus run`: refuse (exit 2) unless --force
GUARD_ADVISORY = 90.0     # PreToolUse: inject an advisory (existing 90% semantics)
GUARD_EMERGENCY = 97.0    # PreToolUse: emergency state-save, once per window


class UsageSnapshot(NamedTuple):
    percent: float | None            # 5-hour window utilization percent (None = unknown)
    resets_at: str | None            # human-readable local reset time, or None
    # Second, slower window: claude's weekly (seven_day) limit, codex's secondary
    # window. Defaulted so every existing positional ``UsageSnapshot(pct, reset)``
    # caller keeps working; the ``PreToolUse`` guard reads only the 5h fields above.
    weekly_percent: float | None = None   # weekly/secondary window percent (None = unknown)
    weekly_resets_at: str | None = None   # weekly reset time, or None

    def has_expired_window(self, *, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return _window_expired(self.resets_at, now) or _window_expired(self.weekly_resets_at, now)

    def without_expired_windows(self, *, now: float | None = None) -> "UsageSnapshot":
        """Return a copy with any reset-past window marked unknown.

        The native apps report capacity by window. Once a window's reset time is in
        the past, its cached percent is no longer evidence of current capacity; the
        two windows expire independently.
        """
        now = time.time() if now is None else now
        percent = self.percent
        resets_at = self.resets_at
        weekly_percent = self.weekly_percent
        weekly_resets_at = self.weekly_resets_at
        if _window_expired(resets_at, now):
            percent = None
            resets_at = None
        if _window_expired(weekly_resets_at, now):
            weekly_percent = None
            weekly_resets_at = None
        return UsageSnapshot(percent, resets_at, weekly_percent, weekly_resets_at)

    def worst(self) -> tuple[float | None, str | None, str]:
        """The MORE-CONSTRAINING window as ``(percent, reset, label)``.

        A higher utilization percent is closer to that window's own limit, so it is
        the more constraining of (5h, weekly). Windows with no reading are ignored;
        ``(None, None, "5h")`` when neither window has a percent.
        """
        candidates = [
            c for c in (
                (self.percent, self.resets_at, "5h"),
                (self.weekly_percent, self.weekly_resets_at, "weekly"),
            ) if c[0] is not None
        ]
        if not candidates:
            return (None, None, "5h")
        return max(candidates, key=lambda c: c[0])


class _Cached(NamedTuple):
    """A fresh cache entry. ``snapshot`` is ``None`` for a cached negative result
    (distinguished from a cache miss, which is a plain ``None`` return)."""

    snapshot: UsageSnapshot | None


def cache_dir() -> Path:
    return config.config_dir() / "cache"


def _cache_key(agent: str, account: str | None) -> str:
    raw = f"{agent}-{account or 'default'}"
    return re.sub(r"[^A-Za-z0-9_.-]", "_", raw)[:80]


def _cache_path(agent: str, account: str | None) -> Path:
    return cache_dir() / f"usage-{_cache_key(agent, account)}.json"


# --------------------------------------------------------------------------- #
# Live reads (best-effort; any failure -> None)
# --------------------------------------------------------------------------- #

def _read_claude(account: str | None, *, timeout: float) -> UsageSnapshot | None:
    from horus import claude_usage

    cred_path: Path | None = None
    if account:
        cfg = config.load_account_config_dirs().get(account)
        if cfg:
            cred_path = Path(cfg) / ".credentials.json"
    report = claude_usage.latest_usage(cred_path=cred_path, timeout=timeout)
    if report is None:
        return None
    week_pct = report.seven_day_percent
    week_reset = claude_usage._fmt_reset(report.seven_day_resets_at) if week_pct is not None else None
    return UsageSnapshot(
        report.five_hour_percent,
        claude_usage._fmt_reset(report.five_hour_resets_at),
        week_pct,
        week_reset,
    )


def _read_codex(account: str | None) -> UsageSnapshot | None:
    from horus import codex_usage

    home: Path | None = None
    if account:
        h = config.load_account_codex_homes().get(account)
        if h:
            home = Path(h)
    report = codex_usage.latest_account_usage(home=home)
    if report is None:
        return None
    sec_pct = report.secondary_percent
    sec_reset = codex_usage._fmt_reset(report.secondary_resets_at) if sec_pct is not None else None
    return UsageSnapshot(
        report.primary_percent,
        codex_usage._fmt_reset(report.primary_resets_at),
        sec_pct,
        sec_reset,
    )


def _read_live(agent: str, account: str | None, *, timeout: float) -> UsageSnapshot | None:
    """A single live usage read for ``agent``+``account``. Never raises."""
    try:
        if agent == "claude":
            return _read_claude(account, timeout=timeout)
        if agent == "codex":
            return _read_codex(account)
    except Exception:  # noqa: BLE001 (best-effort: any failure is "no signal")
        return None
    return None


def refresh_usage(
    agent: str,
    account: str | None = None,
    *,
    timeout: float = FETCH_TIMEOUT,
    now: float | None = None,
) -> UsageSnapshot | None:
    """Best-effort live refresh used when a cached window is known expired.

    A failed refresh does not overwrite a previous positive cache entry; callers can
    still use any unexpired window from the cached snapshot.
    """
    now = time.time() if now is None else now
    snapshot = _read_live(agent, account, timeout=timeout)
    if snapshot is not None:
        _write_cache(_cache_path(agent, account), snapshot, now=now)
    return snapshot


# --------------------------------------------------------------------------- #
# Cache
# --------------------------------------------------------------------------- #

def _load_cache(path: Path, *, ttl: float, now: float) -> _Cached | None:
    """Return a fresh cache entry, or ``None`` for a miss/stale/corrupt file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    ts = data.get("ts")
    if not isinstance(ts, int | float):
        return None
    # Stale, or a clock that jumped backwards past the write — treat as a miss.
    if now - ts >= ttl or now < ts:
        return None
    if not data.get("ok"):
        return _Cached(None)
    pct = data.get("percent")
    percent = float(pct) if isinstance(pct, int | float) else None
    resets = data.get("resets_at")
    # Weekly fields absent in caches written before multi-window support -> None.
    wpct = data.get("weekly_percent")
    weekly_percent = float(wpct) if isinstance(wpct, int | float) else None
    wresets = data.get("weekly_resets_at")
    return _Cached(UsageSnapshot(
        percent,
        resets if isinstance(resets, str) else None,
        weekly_percent,
        wresets if isinstance(wresets, str) else None,
    ))


def _reset_timestamp(value: str | None) -> float | None:
    if not value:
        return None
    text = value.strip()
    if not text or text == "unknown reset":
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
        except ValueError:
            return None
    return dt.timestamp()


def _window_expired(reset: str | None, now: float) -> bool:
    ts = _reset_timestamp(reset)
    return ts is not None and ts <= now


def _write_cache(path: Path, snapshot: UsageSnapshot | None, *, now: float) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if snapshot is None:
            payload: dict[str, object] = {"ts": now, "ok": False}
        else:
            payload = {
                "ts": now,
                "ok": True,
                "percent": snapshot.percent,
                "resets_at": snapshot.resets_at,
                "weekly_percent": snapshot.weekly_percent,
                "weekly_resets_at": snapshot.weekly_resets_at,
            }
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass


def cached_usage(
    agent: str,
    account: str | None = None,
    *,
    ttl: float = CACHE_TTL,
    timeout: float = FETCH_TIMEOUT,
    now: float | None = None,
) -> UsageSnapshot | None:
    """Freshest usage snapshot for ``agent``+``account`` (5-hour window).

    Serves a cache entry younger than ``ttl`` without any network I/O (the hot
    path for the PreToolUse guard); otherwise does one live read, caches it
    (including a negative result), and returns it. Returns ``None`` when no usable
    signal exists; callers treat both ``None`` and ``percent is None`` as "unknown,
    proceed silently".
    """
    now = time.time() if now is None else now
    path = _cache_path(agent, account)
    cached = _load_cache(path, ttl=ttl, now=now)
    if cached is not None:
        return cached.snapshot
    snapshot = _read_live(agent, account, timeout=timeout)
    _write_cache(path, snapshot, now=now)
    return snapshot
